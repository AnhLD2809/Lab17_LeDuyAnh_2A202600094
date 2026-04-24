"""
Entry point cho Lab 17 - Multi-Memory Agent với LangGraph.

Hỗ trợ:
  - Demo 3 sessions theo đúng slide
  - Benchmark 10 multi-turn conversations
  - Chạy được cả khi thiếu OPENAI_API_KEY bằng fallback cục bộ
"""

import io
import os
import sys

from dotenv import load_dotenv


def ensure_utf8_console():
    if sys.stdout.encoding != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if sys.stderr.encoding != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


ensure_utf8_console()
load_dotenv()


def divider(title: str):
    print(f"\n{'=' * 78}")
    print(title)
    print(f"{'=' * 78}")


def run_demo():
    from agent.multi_memory_agent import MultiMemoryAgent

    if not os.getenv("OPENAI_API_KEY"):
        print("Không tìm thấy OPENAI_API_KEY, chương trình sẽ dùng fallback responder cục bộ.")

    divider("SESSION 1 - User bày tỏ preferences")
    agent1 = MultiMemoryAgent(session_id="shared_demo", use_memory=True)
    for query in [
        "Tôi thích Python, không thích Java. Bạn có thể tư vấn cho tôi học lập trình không?",
        "Tôi muốn xây dựng một backend API.",
    ]:
        result = agent1.chat(query)
        print(f"\n[User]  {query}")
        print(f"[Agent] {result['response']}")
        print(f"Memory used: {result['memory_types_used']}")

    divider("SESSION 2 - Agent khởi tạo lại và nhớ long-term profile")
    agent2 = MultiMemoryAgent(session_id="shared_demo", use_memory=True)
    for query in [
        "Tôi muốn viết web scraper để thu thập dữ liệu từ website.",
        "Bạn khuyên tôi dùng thư viện nào?",
    ]:
        result = agent2.chat(query)
        print(f"\n[User]  {query}")
        print(f"[Agent] {result['response']}")
        print(f"Memory used: {result['memory_types_used']}")

    divider("SESSION 3 - Agent recall episodic memory")
    agent3 = MultiMemoryAgent(session_id="shared_demo", use_memory=True)
    agent3.episodic.store_episode(
        title="User confused about async/await",
        content="User chưa hiểu sự khác nhau giữa sync và async trong Python.",
        tags=["async", "await", "confusion"],
    )
    for query in [
        "Tôi muốn dùng asyncio để crawl nhiều trang cùng lúc.",
        "async/await hoạt động như thế nào?",
    ]:
        result = agent3.chat(query)
        print(f"\n[User]  {query}")
        print(f"[Agent] {result['response']}")
        print(f"Memory used: {result['memory_types_used']}")

    divider("TÓM TẮT DEMO")
    print(f"Long-term profile: {agent3.long_term.get_all_preferences()}")
    print(f"Số episodic memories: {len(agent3.episodic.get_all())}")


def run_benchmark():
    from benchmark.evaluator import run_benchmark as _run_benchmark

    divider("BENCHMARK - 10 MULTI-TURN CONVERSATIONS")
    report = _run_benchmark()
    preview = report[:1200]
    print(preview)
    if len(report) > len(preview):
        print("\n[Đã rút gọn preview. Xem toàn bộ trong BENCHMARK.md]")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "demo"
    if mode == "benchmark":
        run_benchmark()
    elif mode == "both":
        run_demo()
        run_benchmark()
    else:
        run_demo()
