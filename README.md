# Lab 17 - Multi-Memory Agent với LangGraph

**Sinh viên:** Lê Duy Anh - MSSV: 2A202600094  
**Ngày cập nhật:** 24/04/2026

## 1. Mục tiêu bài lab

Xây dựng một agent có **đủ 4 loại memory** và có thể:

- Nhớ user preferences qua nhiều phiên làm việc.
- Recall lại episodic memory khi user gặp lỗi hoặc đã có trải nghiệm trước đó.
- Truy hồi semantic knowledge để tăng độ chính xác của câu trả lời.
- So sánh agent **có memory** và **không có memory** trên **10 multi-turn conversations**.

Deliverable của bài gồm source code + benchmark report + reflection về privacy/limitations.

## 2. Kiến trúc triển khai

Hệ thống hiện tại dùng 4 memory backends riêng biệt:

| Memory type | Backend | Vai trò |
|---|---|---|
| Short-term | `ConversationBufferMemory` tự cài đặt | Giữ lịch sử hội thoại gần đây trong session |
| Long-term profile | `fakeredis` + JSON snapshot | Lưu preference/fact bền hơn giữa các lần khởi tạo agent |
| Episodic | JSON log | Lưu các episode như confusion, debug, outcome |
| Semantic | TF-IDF + cosine similarity | Truy hồi kiến thức liên quan từ knowledge base nội bộ |

Luồng xử lý:

1. User gửi query.
2. `MemoryRouter` phân tích intent để chọn memory phù hợp.
3. `ContextWindowManager` gộp context và trim theo priority:
   `semantic > episodic > long_term > short_term`
4. Agent bơm memory vào prompt theo từng section rõ ràng:
   profile, episodic, semantic, recent conversation.
5. LangGraph chạy chuỗi node:
   `retrieve_memory -> generate_response -> store_memory`
6. Câu trả lời và dữ liệu mới được ghi lại vào các backend liên quan.

## 3. Thành phần chính

```text
Lab17_LeDuyAnh_2A202600094/
├── agent/
│   ├── context_manager.py
│   ├── memory_router.py
│   └── multi_memory_agent.py
├── benchmark/
│   ├── conversations.py
│   └── evaluator.py
├── demand/
├── logs/
├── memory/
│   ├── episodic.py
│   ├── long_term.py
│   ├── semantic.py
│   └── short_term.py
├── BENCHMARK.md
├── main.py
├── README.md
└── requirements.txt
```

## 4. Các điểm bám sát rubric

### Full memory stack

- Có đủ 4 loại memory riêng biệt.
- Mỗi loại có interface lưu và truy hồi độc lập.
- Có unified `retrieve(query, types=["all"])` để gom context từ nhiều backend.

### LangGraph state/router + prompt injection

- Dùng `AgentState` kiểu `TypedDict`.
- Có node `retrieve_memory`, `generate_response`, `store_memory`.
- Prompt được tách section rõ ràng thay vì nhét toàn bộ memory vào một blob.
- Có token budget và context breakdown để giải thích vì sao phần nào được giữ lại.

### Save/update memory + conflict handling

- Long-term profile có overwrite khi user sửa fact cũ.
- Case bắt buộc của rubric:
  `sữa bò -> đậu nành` được cập nhật đúng.
- Episodic memory lưu được confusion/debug/outcome có ý nghĩa.

### Benchmark

- Có 10 hội thoại nhiều lượt.
- Bao phủ đủ: profile recall, conflict update, episodic recall, semantic retrieval, token budget.
- So sánh `with_memory` và `no_memory`, sinh `BENCHMARK.md` và raw JSON.

### Reflection

- Báo cáo có mục privacy/PII risk.
- Có nêu limitation kỹ thuật và hướng cải tiến.

## 5. Cài đặt

### Tạo môi trường ảo

```bash
python -m venv venv
venv\Scripts\activate
```

### Cài dependencies

```bash
pip install -r requirements.txt
```

### Cấu hình API key

Tạo file `.env`:

```env
OPENAI_API_KEY=sk-...
```

Nếu không có API key, chương trình vẫn chạy được ở chế độ fallback nội bộ để demo kiến trúc và benchmark cục bộ.

## 6. Cách chạy

### Demo 3 sessions

```bash
python main.py
```

Demo bám theo slide:

1. Session 1: user nói thích Python, không thích Java -> agent ghi long-term profile.
2. Session 2: agent khởi tạo lại -> vẫn nhớ preference và chủ động gợi ý Python.
3. Session 3: agent recall episode user từng confused với async/await -> giải thích chi tiết hơn.

### Chạy benchmark

```bash
python main.py benchmark
```

### Chạy cả demo và benchmark

```bash
python main.py both
```

## 7. Kết quả đầu ra

- `BENCHMARK.md`: báo cáo benchmark tiếng Việt có dấu.
- `logs/benchmark_raw_<timestamp>.json`: dữ liệu thô từng turn.
- `logs/long_term_profile_<session_id>.json`: snapshot long-term profile.
- `logs/episodic_log_<session_id>.json`: episodic memory theo session.

## 8. Hạn chế hiện tại

- Semantic retrieval dùng TF-IDF nên chưa mạnh bằng embeddings/vector DB thật.
- Token count vẫn là heuristic, chưa dùng tokenizer thật như `tiktoken`.
- Fallback responder chỉ phục vụ demo/offline, chất lượng không thay thế được GPT-4o-mini.
- Chưa có consent flow và TTL đầy đủ cho dữ liệu nhạy cảm.
