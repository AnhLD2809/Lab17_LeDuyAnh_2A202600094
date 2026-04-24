# BENCHMARK - Lab 17: Multi-Memory Agent với LangGraph

> Sinh viên: Lê Duy Anh - MSSV: 2A202600094
> Thời điểm sinh báo cáo: 24/04/2026 12:45:48
> Thiết lập: 10 hội thoại nhiều lượt, so sánh `with_memory` và `no_memory`

## 1. Kết luận nhanh

- Điểm chất lượng trung bình tăng từ **0.461** lên **0.603** (delta **+0.142**).
- Khả năng carry context tăng từ **0.151** lên **0.235** (delta **+0.084**).
- Memory hit rate trung bình của biến thể có memory là **98%**.
- Conflict test bắt buộc: **Đạt**.

## 2. Bảng so sánh tổng hợp

| Biến thể | Avg Quality | Avg Context Carry | Avg Memory Hit Rate | Avg Latency (s) |
|---|---:|---:|---:|---:|
| No Memory | 0.461 | 0.151 | 0% | 8.427 |
| With Memory | 0.603 | 0.235 | 98% | 8.534 |

## 3. Kết quả theo 10 kịch bản rubric

| # | Scenario | Nhóm test | Avg Quality No-Memory | Avg Quality With-Memory | Memory Hit Rate | Kết quả |
|---|---|---|---:|---:|---:|---|
| 1 | Nhớ preference ngôn ngữ sau nhiều lượt | Profile Recall | 0.466 | 0.619 | 100% | Đạt |
| 2 | Ghi đè đúng fact dị ứng mới | Conflict Update | 0.505 | 0.704 | 100% | Đạt |
| 3 | Liên hệ lại episode async/await đã nhắc trước đó | Episodic Recall | 0.447 | 0.587 | 100% | Đạt |
| 4 | Bơm kiến thức FastAPI vào câu trả lời | Semantic Retrieval | 0.517 | 0.646 | 100% | Đạt |
| 5 | Giữ ngữ cảnh pipeline ML khi hội thoại dài | Token Budget | 0.460 | 0.569 | 83% | Đạt |
| 6 | Truy hồi gợi ý cursor-based pagination | Semantic Retrieval | 0.431 | 0.523 | 100% | Đạt |
| 7 | Cá nhân hóa theo level senior | Profile Recall | 0.451 | 0.616 | 100% | Đạt |
| 8 | Giữ được context microservices ở lượt cuối | Token Budget | 0.437 | 0.604 | 100% | Đạt |
| 9 | Nhớ confusion về mock/patch | Episodic Recall | 0.448 | 0.598 | 100% | Đạt |
| 10 | Giữ được ngữ cảnh observability ở cloud scale | Token Budget | 0.452 | 0.565 | 100% | Đạt |
| C | Conflict update bắt buộc | Conflict Update | - | - | - | Đạt |

> Tổng cộng: **11/11** kịch bản đạt.

## 4. Phân rã theo nhóm test

| Nhóm test | Avg Quality No-Memory | Avg Quality With-Memory | Memory Hit Rate |
|---|---:|---:|---:|
| conflict_update | 0.505 | 0.704 | 100% |
| episodic | 0.448 | 0.593 | 100% |
| profile_recall | 0.459 | 0.617 | 100% |
| semantic | 0.474 | 0.585 | 100% |
| token_budget | 0.450 | 0.579 | 94% |

## 5. Token budget breakdown

| Hội thoại | Category | Memory budget còn lại ở lượt cuối | Memory sections được giữ lại |
|---|---|---:|---|
| Conv 1 | profile_recall | 0 | semantic, long_term, short_term |
| Conv 2 | conflict_update | 841 | semantic, long_term, short_term |
| Conv 3 | episodic | 471 | semantic, episodic, short_term |

Priority eviction đang được áp dụng theo thứ tự: `semantic > episodic > long_term > short_term`.

## 6. Conflict handling test

```text
Turn 1: "Tôi dị ứng sữa bò."
Profile => allergy = sữa bò

Turn 2: "À nhầm, tôi dị ứng đậu nành chứ không phải sữa bò."
Profile => allergy = đậu nành
```

Kết quả tự động: Trước: 'sữa bò' -> Sau: 'đậu nành' | kỳ vọng: 'đậu nành'

## 7. Reflection về privacy và limitations

**Memory giúp agent nhiều nhất**
- Long-term profile giúp agent nhớ preference, level và dị ứng xuyên phiên làm việc.
- Episodic memory giúp agent nối lại các lỗi/confusion mà user đã gặp trước đó.
- Semantic memory giúp bơm kiến thức nền vào prompt thay vì phụ thuộc hoàn toàn vào short-term chat.

**Memory rủi ro nhất nếu retrieve sai**
- Long-term profile là nhạy cảm nhất vì chứa thông tin cá nhân như tên hoặc dị ứng.
- Episodic log cũng rủi ro nếu trộn nhầm dữ liệu của user khác hoặc chứa log lỗi có PII.

**Biện pháp nên có khi triển khai thực tế**
- TTL cho profile cũ và chính sách xóa dữ liệu theo yêu cầu người dùng.
- Tách namespace theo `user_id/session_id` để tránh lẫn memory.
- Consent rõ ràng trước khi lưu thông tin cá nhân.
- Mã hóa dữ liệu nhạy cảm khi lưu trên đĩa hoặc backend thật.

**Giới hạn kỹ thuật hiện tại**
- Semantic retrieval đang dùng TF-IDF nên còn yếu với paraphrase phức tạp.
- Token counting mới ước lượng bằng heuristic, chưa dùng tokenizer thật.
- Fallback responder cục bộ hữu ích cho demo/offline nhưng không thay thế chất lượng LLM thật.

## 8. Tệp sinh ra

- `BENCHMARK.md`: báo cáo benchmark tiếng Việt có dấu.
- `logs/benchmark_raw_<timestamp>.json`: dữ liệu thô để đối chiếu.