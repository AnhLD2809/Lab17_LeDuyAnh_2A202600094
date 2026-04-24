"""
Benchmark evaluator cho Lab 17.

Output:
  - logs/benchmark_raw_<timestamp>.json
  - BENCHMARK.md
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, List, Tuple

from agent.multi_memory_agent import MultiMemoryAgent
from benchmark.conversations import TEST_CONVERSATIONS

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

_STOP_WORDS = {
    "tôi", "ban", "bạn", "và", "hoặc", "là", "có", "không", "thể", "nào",
    "làm", "để", "cho", "với", "từ", "của", "một", "các", "như", "nên",
    "thì", "được", "khi", "nếu", "vì", "đã", "đang", "sẽ", "cần", "trên",
    "the", "is", "in", "to", "of", "and", "or", "that", "for",
}


def score_relevance(query: str, response: str) -> float:
    q_words = {w.strip(".,:;!?()[]") for w in query.lower().split()} - _STOP_WORDS
    r_words = {w.strip(".,:;!?()[]") for w in response.lower().split()} - _STOP_WORDS
    q_words = {w for w in q_words if w}
    if not q_words:
        return 0.0
    return round(min(1.0, len(q_words & r_words) / len(q_words)), 3)


def score_context_carry(history: List[str], response: str) -> float:
    prior_words = {
        w.strip(".,:;!?()[]")
        for w in " ".join(history[-2:]).lower().split()
        if len(w) > 3
    } - _STOP_WORDS
    prior_words = {w for w in prior_words if w}
    if not prior_words:
        return 0.0
    response_words = {w.strip(".,:;!?()[]") for w in response.lower().split()}
    return round(min(1.0, len(prior_words & response_words) / len(prior_words)), 3)


def score_length(response: str) -> float:
    return round(min(1.0, len(response) / 220), 3)


def score_memory_diversity(memory_types: List[str]) -> float:
    unique = {memory_type.replace("_proactive", "") for memory_type in memory_types}
    return round(len(unique) / 4, 3)


def composite_score(rel: float, ctx: float, lng: float, div: float) -> float:
    return round(rel * 0.35 + ctx * 0.25 + lng * 0.20 + div * 0.20, 3)


def run_conflict_test() -> Tuple[bool, str]:
    agent = MultiMemoryAgent(session_id="conflict_test_rubric", use_memory=True)
    agent.long_term.extract_and_store("Tôi dị ứng sữa bò.")
    before = agent.long_term.get_preference("allergy")
    agent.long_term.extract_and_store("À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò.")
    after = agent.long_term.get_preference("allergy")
    passed = after == "đậu nành"
    detail = f"Trước: '{before}' -> Sau: '{after}' | kỳ vọng: 'đậu nành'"
    return passed, detail


def run_variant(use_memory: bool) -> List[Dict]:
    label = "WITH_MEMORY" if use_memory else "NO_MEMORY"
    print(f"\n{'=' * 72}")
    print(f"Chạy biến thể: {label}")
    print(f"{'=' * 72}")

    results: List[Dict] = []
    for conv in TEST_CONVERSATIONS:
        agent = MultiMemoryAgent(
            session_id=f"bench_{label}_{conv['id']}",
            use_memory=use_memory,
        )
        conv_result = {
            "conversation_id": conv["id"],
            "topic": conv["topic"],
            "category": conv["category"],
            "num_turns": len(conv["turns"]),
            "turns": [],
            "avg_quality": 0.0,
            "avg_context_carry": 0.0,
            "memory_hit_rate": 0.0,
            "avg_latency": 0.0,
        }
        query_history: List[str] = []
        memory_hits = 0

        for idx, query in enumerate(conv["turns"], start=1):
            start = time.time()
            out = agent.chat(query)
            latency = round(time.time() - start, 3)

            rel = score_relevance(query, out["response"])
            ctx = score_context_carry(query_history, out["response"])
            lng = score_length(out["response"])
            div = score_memory_diversity(out["memory_types_used"])
            quality = composite_score(rel, ctx, lng, div)
            if out["memory_types_used"]:
                memory_hits += 1

            conv_result["turns"].append(
                {
                    "turn": idx,
                    "query": query,
                    "response": out["response"],
                    "response_length": len(out["response"]),
                    "memory_types_used": out["memory_types_used"],
                    "context_breakdown": out.get("context_breakdown", []),
                    "memory_budget_remaining": out.get("memory_budget", 0),
                    "relevance_score": rel,
                    "context_carry_score": ctx,
                    "length_score": lng,
                    "memory_diversity": div,
                    "quality_score": quality,
                    "latency_seconds": latency,
                    "user_profile_at_turn": out.get("user_profile", {}),
                }
            )
            query_history.append(query)

        turns = conv_result["turns"]
        n_turns = len(turns)
        conv_result["avg_quality"] = round(sum(t["quality_score"] for t in turns) / n_turns, 3)
        conv_result["avg_context_carry"] = round(sum(t["context_carry_score"] for t in turns) / n_turns, 3)
        conv_result["memory_hit_rate"] = round(memory_hits / n_turns, 3)
        conv_result["avg_latency"] = round(sum(t["latency_seconds"] for t in turns) / n_turns, 3)

        print(
            f"Conv {conv['id']:02d} | {conv['category']:<15} | "
            f"quality={conv_result['avg_quality']:.3f} | "
            f"carry={conv_result['avg_context_carry']:.3f} | "
            f"hit={conv_result['memory_hit_rate']:.0%}"
        )
        results.append(conv_result)

    return results


_SCENARIOS = [
    (1, "Nhớ preference ngôn ngữ sau nhiều lượt", "Profile Recall", "python"),
    (2, "Ghi đè đúng fact dị ứng mới", "Conflict Update", "đậu nành"),
    (3, "Liên hệ lại episode async/await đã nhắc trước đó", "Episodic Recall", "async"),
    (4, "Bơm kiến thức FastAPI vào câu trả lời", "Semantic Retrieval", "fastapi"),
    (5, "Giữ ngữ cảnh pipeline ML khi hội thoại dài", "Token Budget", "model"),
    (6, "Truy hồi gợi ý cursor-based pagination", "Semantic Retrieval", "cursor"),
    (7, "Cá nhân hóa theo level senior", "Profile Recall", "senior"),
    (8, "Giữ được context microservices ở lượt cuối", "Token Budget", "version"),
    (9, "Nhớ confusion về mock/patch", "Episodic Recall", "mock"),
    (10, "Giữ được ngữ cảnh observability ở cloud scale", "Token Budget", "prometheus"),
]


def aggregate_metrics(items: List[Dict]) -> Dict[str, float]:
    return {
        "avg_quality": round(sum(item["avg_quality"] for item in items) / len(items), 3),
        "avg_context_carry": round(sum(item["avg_context_carry"] for item in items) / len(items), 3),
        "avg_memory_hit_rate": round(sum(item["memory_hit_rate"] for item in items) / len(items), 3),
        "avg_latency": round(sum(item["avg_latency"] for item in items) / len(items), 3),
    }


def category_breakdown(items: List[Dict]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[Dict]] = {}
    for item in items:
        grouped.setdefault(item["category"], []).append(item)
    return {category: aggregate_metrics(rows) for category, rows in grouped.items()}


def generate_benchmark_md(with_mem: List[Dict], no_mem: List[Dict], conflict_pass: bool, conflict_detail: str) -> str:
    wm_by_id = {item["conversation_id"]: item for item in with_mem}
    nm_by_id = {item["conversation_id"]: item for item in no_mem}
    summary_mem = aggregate_metrics(with_mem)
    summary_no = aggregate_metrics(no_mem)
    delta_quality = round(summary_mem["avg_quality"] - summary_no["avg_quality"], 3)
    delta_carry = round(summary_mem["avg_context_carry"] - summary_no["avg_context_carry"], 3)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    scenario_lines = []
    pass_count = 0
    for conv_id, scenario, category, keyword in _SCENARIOS:
        with_conv = wm_by_id[conv_id]
        no_conv = nm_by_id[conv_id]
        combined_response = " ".join(turn["response"].lower() for turn in with_conv["turns"])
        keyword_hit = keyword in combined_response
        memory_hit = with_conv["memory_hit_rate"] > 0
        passed = keyword_hit and memory_hit
        if passed:
            pass_count += 1
        scenario_lines.append(
            f"| {conv_id} | {scenario} | {category} | "
            f"{no_conv['avg_quality']:.3f} | {with_conv['avg_quality']:.3f} | "
            f"{with_conv['memory_hit_rate']:.0%} | {'Đạt' if passed else 'Cần xem lại'} |"
        )

    if conflict_pass:
        pass_count += 1

    mem_breakdown = category_breakdown(with_mem)
    no_breakdown = category_breakdown(no_mem)
    category_lines = []
    for category in sorted(mem_breakdown.keys()):
        category_lines.append(
            f"| {category} | {no_breakdown[category]['avg_quality']:.3f} | "
            f"{mem_breakdown[category]['avg_quality']:.3f} | "
            f"{mem_breakdown[category]['avg_memory_hit_rate']:.0%} |"
        )

    token_rows = []
    for item in with_mem[:3]:
        last_turn = item["turns"][-1]
        token_rows.append(
            f"| Conv {item['conversation_id']} | {item['category']} | "
            f"{last_turn['memory_budget_remaining']} | "
            f"{', '.join(part['memory_type'] for part in last_turn['context_breakdown']) or 'Không có'} |"
        )

    lines = [
        "# BENCHMARK - Lab 17: Multi-Memory Agent với LangGraph",
        "",
        f"> Sinh viên: Lê Duy Anh - MSSV: 2A202600094",
        f"> Thời điểm sinh báo cáo: {now}",
        "> Thiết lập: 10 hội thoại nhiều lượt, so sánh `with_memory` và `no_memory`",
        "",
        "## 1. Kết luận nhanh",
        "",
        f"- Điểm chất lượng trung bình tăng từ **{summary_no['avg_quality']:.3f}** lên **{summary_mem['avg_quality']:.3f}** (delta **{delta_quality:+.3f}**).",
        f"- Khả năng carry context tăng từ **{summary_no['avg_context_carry']:.3f}** lên **{summary_mem['avg_context_carry']:.3f}** (delta **{delta_carry:+.3f}**).",
        f"- Memory hit rate trung bình của biến thể có memory là **{summary_mem['avg_memory_hit_rate']:.0%}**.",
        f"- Conflict test bắt buộc: **{'Đạt' if conflict_pass else 'Chưa đạt'}**.",
        "",
        "## 2. Bảng so sánh tổng hợp",
        "",
        "| Biến thể | Avg Quality | Avg Context Carry | Avg Memory Hit Rate | Avg Latency (s) |",
        "|---|---:|---:|---:|---:|",
        f"| No Memory | {summary_no['avg_quality']:.3f} | {summary_no['avg_context_carry']:.3f} | {summary_no['avg_memory_hit_rate']:.0%} | {summary_no['avg_latency']:.3f} |",
        f"| With Memory | {summary_mem['avg_quality']:.3f} | {summary_mem['avg_context_carry']:.3f} | {summary_mem['avg_memory_hit_rate']:.0%} | {summary_mem['avg_latency']:.3f} |",
        "",
        "## 3. Kết quả theo 10 kịch bản rubric",
        "",
        "| # | Scenario | Nhóm test | Avg Quality No-Memory | Avg Quality With-Memory | Memory Hit Rate | Kết quả |",
        "|---|---|---|---:|---:|---:|---|",
        *scenario_lines,
        f"| C | Conflict update bắt buộc | Conflict Update | - | - | - | {'Đạt' if conflict_pass else 'Chưa đạt'} |",
        "",
        f"> Tổng cộng: **{pass_count}/11** kịch bản đạt.",
        "",
        "## 4. Phân rã theo nhóm test",
        "",
        "| Nhóm test | Avg Quality No-Memory | Avg Quality With-Memory | Memory Hit Rate |",
        "|---|---:|---:|---:|",
        *category_lines,
        "",
        "## 5. Token budget breakdown",
        "",
        "| Hội thoại | Category | Memory budget còn lại ở lượt cuối | Memory sections được giữ lại |",
        "|---|---|---:|---|",
        *token_rows,
        "",
        "Priority eviction đang được áp dụng theo thứ tự: `semantic > episodic > long_term > short_term`.",
        "",
        "## 6. Conflict handling test",
        "",
        "```text",
        'Turn 1: "Tôi dị ứng sữa bò."',
        "Profile => allergy = sữa bò",
        "",
        'Turn 2: "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò."',
        "Profile => allergy = đậu nành",
        "```",
        "",
        f"Kết quả tự động: {conflict_detail}",
        "",
        "## 7. Reflection về privacy và limitations",
        "",
        "**Memory giúp agent nhiều nhất**",
        "- Long-term profile giúp agent nhớ preference, level và dị ứng xuyên phiên làm việc.",
        "- Episodic memory giúp agent nối lại các lỗi/confusion mà user đã gặp trước đó.",
        "- Semantic memory giúp bơm kiến thức nền vào prompt thay vì phụ thuộc hoàn toàn vào short-term chat.",
        "",
        "**Memory rủi ro nhất nếu retrieve sai**",
        "- Long-term profile là nhạy cảm nhất vì chứa thông tin cá nhân như tên hoặc dị ứng.",
        "- Episodic log cũng rủi ro nếu trộn nhầm dữ liệu của user khác hoặc chứa log lỗi có PII.",
        "",
        "**Biện pháp nên có khi triển khai thực tế**",
        "- TTL cho profile cũ và chính sách xóa dữ liệu theo yêu cầu người dùng.",
        "- Tách namespace theo `user_id/session_id` để tránh lẫn memory.",
        "- Consent rõ ràng trước khi lưu thông tin cá nhân.",
        "- Mã hóa dữ liệu nhạy cảm khi lưu trên đĩa hoặc backend thật.",
        "",
        "**Giới hạn kỹ thuật hiện tại**",
        "- Semantic retrieval đang dùng TF-IDF nên còn yếu với paraphrase phức tạp.",
        "- Token counting mới ước lượng bằng heuristic, chưa dùng tokenizer thật.",
        "- Fallback responder cục bộ hữu ích cho demo/offline nhưng không thay thế chất lượng LLM thật.",
        "",
        "## 8. Tệp sinh ra",
        "",
        "- `BENCHMARK.md`: báo cáo benchmark tiếng Việt có dấu.",
        "- `logs/benchmark_raw_<timestamp>.json`: dữ liệu thô để đối chiếu.",
    ]
    return "\n".join(lines)


def run_benchmark():
    total_turns = sum(len(conv["turns"]) for conv in TEST_CONVERSATIONS)
    print("\n" + "=" * 72)
    print("Lab 17 - Benchmark Multi-Memory Agent")
    print(f"10 conversations | tổng số lượt mỗi biến thể: {total_turns}")
    print("=" * 72)

    print("\n[1/4] Chạy conflict handling test...")
    conflict_pass, conflict_detail = run_conflict_test()
    print(f"-> {'PASS' if conflict_pass else 'FAIL'} | {conflict_detail}")

    print("\n[2/4] Chạy biến thể WITH_MEMORY...")
    with_mem = run_variant(use_memory=True)

    print("\n[3/4] Chạy biến thể NO_MEMORY...")
    no_mem = run_variant(use_memory=False)

    print("\n[4/4] Ghi kết quả ra file...")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = os.path.join(LOGS_DIR, f"benchmark_raw_{ts}.json")
    raw_data = {
        "generated_at": datetime.now().isoformat(),
        "conflict_test": {"pass": conflict_pass, "detail": conflict_detail},
        "with_memory": with_mem,
        "without_memory": no_mem,
    }
    try:
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, ensure_ascii=False, indent=2)
        print(f"Đã lưu raw data vào: {raw_path}")
    except (PermissionError, OSError):
        print("Không thể ghi raw data ra logs trong môi trường hiện tại, bỏ qua bước này.")

    report = generate_benchmark_md(with_mem, no_mem, conflict_pass, conflict_detail)
    try:
        with open("BENCHMARK.md", "w", encoding="utf-8") as f:
            f.write(report)
        print("Đã cập nhật báo cáo: BENCHMARK.md")
    except (PermissionError, OSError):
        print("Không thể ghi BENCHMARK.md bằng Python trong môi trường hiện tại, nhưng nội dung báo cáo vẫn được sinh thành công.")

    return report


if __name__ == "__main__":
    run_benchmark()
