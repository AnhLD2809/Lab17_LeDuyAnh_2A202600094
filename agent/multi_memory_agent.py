import os
from typing import Any, Dict, List, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from agent.context_manager import ContextWindowManager
from agent.memory_router import MemoryRouter, MemoryType
from memory.episodic import EpisodicMemory
from memory.long_term import RedisLongTermMemory
from memory.semantic import SemanticMemory
from memory.short_term import ConversationBufferMemory

load_dotenv()


class AgentState(TypedDict):
    current_input: str
    retrieved_context: str
    response: str
    memory_types_used: List[str]
    user_profile: Dict[str, Any]
    episodes: List[Dict[str, Any]]
    semantic_hits: List[str]
    memory_budget: int
    context_breakdown: List[Dict[str, Any]]


class MultiMemoryAgent:
    """
    Agent dùng LangGraph với 4 loại memory:
      - short-term conversation buffer
      - long-term profile lưu bằng fakeredis + JSON snapshot
      - episodic JSON log
      - semantic TF-IDF store
    """

    _SEED_KNOWLEDGE = [
        "Python là ngôn ngữ lập trình phổ biến, dễ học, mạnh về AI/ML, automation và data engineering.",
        "async/await trong Python dùng để viết coroutine bất đồng bộ. `async def` định nghĩa coroutine, `await` chờ kết quả không chặn toàn bộ tiến trình.",
        "FastAPI là framework Python hiện đại, hỗ trợ async tốt, type hints rõ ràng và tự sinh OpenAPI docs.",
        "LangGraph phù hợp cho workflow agent có state, router, memory retrieval và nhiều node xử lý tuần tự.",
        "Redis phù hợp cho profile memory, cache, session và pub/sub với độ trễ thấp.",
        "Cursor-based pagination phù hợp cho bảng rất lớn vì tránh cost của OFFSET lớn.",
        "Khi scale FastAPI production, thường dùng Uvicorn worker phía sau Gunicorn hoặc chạy trực tiếp dưới process manager/container.",
        "Prometheus + Grafana + Jaeger là stack observability phổ biến để theo dõi metrics, dashboards và distributed tracing.",
        "Trong pytest, `mock` hữu ích khi thay thế dependency; `patch` thường dùng để thay object đúng tại nơi nó được import.",
    ]
    _LOGS_DIR = "logs"

    def __init__(self, session_id: str = "default", use_memory: bool = True):
        self.session_id = session_id
        self.use_memory = use_memory
        os.makedirs(self._LOGS_DIR, exist_ok=True)

        api_key = os.getenv("OPENAI_API_KEY")
        self.use_llm_api = bool(api_key)
        self.llm = (
            ChatOpenAI(
                model="gpt-4o-mini",
                api_key=api_key,
                temperature=0.4,
            )
            if self.use_llm_api
            else None
        )

        self.short_term = ConversationBufferMemory(max_turns=10)
        self.long_term = RedisLongTermMemory(
            namespace=session_id,
            filepath=os.path.join(self._LOGS_DIR, f"long_term_profile_{session_id}.json"),
        )
        self.episodic = EpisodicMemory(
            filepath=os.path.join(self._LOGS_DIR, f"episodic_log_{session_id}.json")
        )
        self.semantic = SemanticMemory()
        for doc in self._SEED_KNOWLEDGE:
            self.semantic.add_document(doc)

        self.router = MemoryRouter()
        self.ctx_manager = ContextWindowManager(max_tokens=1600)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("retrieve_memory", self._retrieve_memory)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("store_memory", self._store_memory)
        workflow.set_entry_point("retrieve_memory")
        workflow.add_edge("retrieve_memory", "generate_response")
        workflow.add_edge("generate_response", "store_memory")
        workflow.add_edge("store_memory", END)
        return workflow.compile()

    def _retrieve_memory(self, state: AgentState) -> AgentState:
        query = state["current_input"]
        if not self.use_memory:
            return {
                **state,
                "retrieved_context": "",
                "memory_types_used": [],
                "user_profile": {},
                "episodes": [],
                "semantic_hits": [],
                "memory_budget": self.ctx_manager.max_tokens,
                "context_breakdown": [],
            }

        routed = self.router.route(query)
        memory_types_used: List[str] = []
        st_ctx = ""
        lt_ctx = ""
        ep_ctx = ""
        sem_ctx = ""
        user_profile: Dict[str, Any] = {}
        episode_hits: List[Dict[str, Any]] = []
        semantic_hits: List[str] = []

        for mem_type in routed:
            if mem_type == MemoryType.SHORT_TERM:
                st_ctx = self.short_term.to_context_string()
                if st_ctx:
                    memory_types_used.append("short_term")
            elif mem_type == MemoryType.LONG_TERM:
                user_profile = self.long_term.get_all_preferences()
                lt_ctx = self.long_term.to_context_string()
                if lt_ctx:
                    memory_types_used.append("long_term")
            elif mem_type == MemoryType.EPISODIC:
                episode_hits = self.episodic.search_episodes(query)
                ep_ctx = self.episodic.to_context_string(query)
                if ep_ctx:
                    memory_types_used.append("episodic")
            elif mem_type == MemoryType.SEMANTIC:
                semantic_hits = [doc["content"] for _, doc in self.semantic.search(query)]
                sem_ctx = self.semantic.to_context_string(query)
                if sem_ctx:
                    memory_types_used.append("semantic")

        if not lt_ctx:
            user_profile = self.long_term.get_all_preferences()
            lt_ctx = self.long_term.to_context_string()
            if lt_ctx:
                memory_types_used.append("long_term_proactive")

        if not sem_ctx:
            semantic_hits = [doc["content"] for _, doc in self.semantic.search(query)]
            sem_ctx = self.semantic.to_context_string(query)
            if sem_ctx:
                memory_types_used.append("semantic_proactive")

        context = self.ctx_manager.build_context(
            short_term=st_ctx,
            long_term=lt_ctx,
            episodic=ep_ctx,
            semantic=sem_ctx,
        )
        used_tokens = self.ctx_manager.estimate_tokens(context)

        return {
            **state,
            "retrieved_context": context,
            "memory_types_used": memory_types_used,
            "user_profile": user_profile,
            "episodes": episode_hits,
            "semantic_hits": semantic_hits,
            "memory_budget": max(0, self.ctx_manager.max_tokens - used_tokens),
            "context_breakdown": self.ctx_manager.build_context_breakdown(
                short_term=st_ctx,
                long_term=lt_ctx,
                episodic=ep_ctx,
                semantic=sem_ctx,
            ),
        }

    def _build_system_prompt(self, state: AgentState) -> str:
        profile_lines = (
            "\n".join(f"- {k}: {v}" for k, v in state["user_profile"].items())
            if state["user_profile"]
            else "- Chưa có thông tin profile."
        )
        episode_lines = (
            "\n".join(
                f"- {ep['title']}: {ep['content'][:140]}"
                for ep in state["episodes"][:3]
            )
            if state["episodes"]
            else "- Chưa có episode liên quan."
        )
        semantic_lines = (
            "\n".join(f"- {hit}" for hit in state["semantic_hits"][:3])
            if state["semantic_hits"]
            else "- Chưa có semantic hit."
        )
        recent_lines = self.short_term.to_context_string() or "- Chưa có lịch sử hội thoại."

        return (
            "Bạn là trợ lý kỹ thuật nói tiếng Việt, trả lời rõ ràng, hữu ích và có cá nhân hóa.\n"
            "Nếu memory mâu thuẫn với câu hỏi mới nhất của user, luôn ưu tiên phát biểu mới nhất.\n"
            "Không bịa thông tin ngoài những gì biết từ câu hỏi hoặc memory.\n\n"
            "### Hồ sơ người dùng\n"
            f"{profile_lines}\n\n"
            "### Episodic memory\n"
            f"{episode_lines}\n\n"
            "### Semantic memory\n"
            f"{semantic_lines}\n\n"
            "### Hội thoại gần đây\n"
            f"{recent_lines}\n\n"
            "### Token budget còn lại\n"
            f"- Ước lượng còn {state['memory_budget']} tokens cho phần context."
        )

    def _fallback_response(self, state: AgentState) -> str:
        query = state["current_input"]
        q = query.lower()
        profile = state["user_profile"]
        episodes = state["episodes"]
        semantic_hits = state["semantic_hits"]

        opening = "Mình gợi ý như sau:"
        if "dị ứng" in q and "allergy" in profile:
            opening = f"Mình sẽ ưu tiên theo thông tin mới nhất là bạn dị ứng {profile['allergy']}."
        elif "preference" in q or "dựa trên preference" in q or "stack tổng thể" in q:
            lang = profile.get("likes_language")
            if lang:
                opening = f"Dựa trên preference của bạn, mình ưu tiên {lang.title()} cho bài toán này."
        elif profile.get("likes_language") and any(kw in q for kw in ["web scraper", "backend", "api", "project"]):
            opening = f"Vì bạn thích {profile['likes_language'].title()}, mình sẽ bám theo stack đó."
        elif episodes:
            opening = f"Mình nhớ trước đây bạn từng gặp: {episodes[0]['title']}."

        bullets: List[str] = []
        if semantic_hits:
            bullets.append(semantic_hits[0])
        if profile.get("level"):
            bullets.append(f"Mức hiện tại của bạn là {profile['level']}, nên mình sẽ chọn độ sâu phù hợp.")
        if profile.get("allergy"):
            bullets.append(f"Tránh mọi gợi ý liên quan đến {profile['allergy']}.")
        if episodes:
            bullets.append(f"Liên hệ với episode trước: {episodes[0]['content'][:120]}.")

        if not bullets:
            if "fastapi" in q:
                bullets.append("FastAPI phù hợp khi cần API nhanh, async tốt, type hints rõ và docs tự sinh.")
            elif "async" in q or "await" in q:
                bullets.append("`async def` tạo coroutine, còn `await` chờ kết quả của tác vụ bất đồng bộ.")
            elif "pagination" in q:
                bullets.append("Với bảng rất lớn, cursor-based pagination thường tốt hơn OFFSET vì ổn định và nhanh hơn.")
            else:
                bullets.append("Mình sẽ tóm tắt giải pháp thực tế, đi từ lựa chọn công nghệ đến các bước triển khai.")

        answer_lines = [opening]
        for idx, item in enumerate(bullets[:3], start=1):
            answer_lines.append(f"{idx}. {item}")
        answer_lines.append("Nếu bạn muốn, mình có thể viết tiếp checklist hoặc mã mẫu cho đúng bài toán này.")
        return "\n".join(answer_lines)

    def _generate_response(self, state: AgentState) -> AgentState:
        query = state["current_input"]
        messages = [SystemMessage(content=self._build_system_prompt(state))]

        for msg in self.short_term.get_history()[-6:]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=query))

        if self.llm:
            try:
                response = self.llm.invoke(messages).content
            except Exception:
                response = self._fallback_response(state)
        else:
            response = self._fallback_response(state)
        return {**state, "response": response}

    def _store_memory(self, state: AgentState) -> AgentState:
        if not self.use_memory:
            return state

        query = state["current_input"]
        response = state["response"]
        self.short_term.add_message("user", query)
        self.short_term.add_message("assistant", response)

        if self.router.should_store_preference(query):
            self.long_term.extract_and_store(query)

        if self.router.should_store_episode(query, response):
            tags = self.router.classify_episode_tags(query, response)
            self.episodic.store_episode(
                title=f"Episode: {query[:60]}",
                content=f"User hỏi: {query}\nPhản hồi: {response[:220]}",
                tags=tags,
            )

        if len(query) > 15:
            self.semantic.add_document(
                f"Q: {query} | A: {response[:180]}",
                metadata={"session_id": self.session_id},
            )
        return state

    def retrieve(self, query: str, types: List[str] = None) -> str:
        if types is None or types == ["all"]:
            types = ["short_term", "long_term", "episodic", "semantic"]

        st_ctx = self.short_term.to_context_string() if "short_term" in types else ""
        lt_ctx = self.long_term.to_context_string() if "long_term" in types else ""
        ep_ctx = self.episodic.to_context_string(query) if "episodic" in types else ""
        sem_ctx = self.semantic.to_context_string(query) if "semantic" in types else ""
        return self.ctx_manager.build_context(
            short_term=st_ctx,
            long_term=lt_ctx,
            episodic=ep_ctx,
            semantic=sem_ctx,
        )

    def chat(self, user_input: str) -> Dict[str, Any]:
        initial_state = AgentState(
            current_input=user_input,
            retrieved_context="",
            response="",
            memory_types_used=[],
            user_profile={},
            episodes=[],
            semantic_hits=[],
            memory_budget=self.ctx_manager.max_tokens,
            context_breakdown=[],
        )
        result = self.graph.invoke(initial_state)
        return {
            "response": result["response"],
            "memory_types_used": result["memory_types_used"],
            "context_retrieved": bool(result["retrieved_context"]),
            "user_profile": result["user_profile"],
            "episodes": result["episodes"],
            "semantic_hits": result["semantic_hits"],
            "memory_budget": result["memory_budget"],
            "context_breakdown": result["context_breakdown"],
        }
