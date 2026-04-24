# BENCHMARK - Lab #17: Multi-Memory Agent voi LangGraph

> Sinh vien: Le Duy Anh - MSSV: 2A202600094 | Generated: 2026-04-24 12:07:50
> 10 multi-turn conversations x avg 5 turns/conv | LLM: GPT-4o-mini
> Avg Quality: With Memory = **0.485** | No Memory = 0.372 | Delta = **+0.113**

---

## Benchmark: 10 Multi-turn Conversations

Bao phu 5 nhom test: Profile Recall | Conflict Update | Episodic Recall | Semantic Retrieval | Token Budget

| # | Scenario | Category | No-memory result | With-memory result | Pass? |
|---|----------|----------|------------------|--------------------|-------|
| 1 | Recall language preference after 6 turns | Profile Recall | Khong biet user thich ngon ngu nao | Goi y Python (nho tu turn 1) | Pass |
| 2 | Allergy conflict update (sua bo -> dau nanh) | Conflict Update | Van nho sua bo (khong biet da sua) | Dau nanh (overwrite thanh cong) | Pass |
| 3 | Recall previous async/await confusion | Episodic Recall | Khong nhac lai loi da gap truoc | Lien ket 2 loi asyncio da gap | Pass |
| 4 | Retrieve FastAPI knowledge from semantic store | Semantic Retrieval | Tra loi chung chung, thieu chi tiet | Trich dan FastAPI facts tu knowledge base | Pass |
| 5 | Token budget: long ML pipeline (6 turns) | Token Budget | Mat context pipeline o turn cuoi | Giu du context pipeline nho priority trim | Pass |
| 6 | Retrieve DB pagination knowledge | Semantic Retrieval | Khong nho da chon DB o turn truoc | De xuat cursor-based pagination dung ngu canh | Pass |
| 7 | Recall senior dev level for learning path | Profile Recall | Khong biet level cua user | Tailored learning path cho senior developer | Pass |
| 8 | Token budget: microservices (5 turns) | Token Budget | Thieu context microservices o turn cuoi | Giu du context, goi y API versioning | Pass |
| 9 | Recall mock/patch confusion episode | Episodic Recall | Khong nhac confusion ve mock/patch | Nho confusion, giai thich mock dung cho | Pass |
| 10 | Token budget: cloud scale (6 turns) | Token Budget | Mat context scale requirement o turn cuoi | De xuat observability stack phu hop scale | Pass |
| C | Allergy conflict update | Conflict Update | Sua bo (giu nguyen, khong overwrite) | Dau nanh (fact moi ghi de fact cu) | Pass |

> Ket qua tong: **11/11 scenarios Pass**

---

## Conflict Handling Test

```
Turn 1: User: "Toi di ung sua bo."
        Profile: { allergy: 'sua bo' }

Turn 2: User: "A nham, toi di ung dau nanh chu khong phai sua bo."
        Profile: { allergy: 'dau nanh' }  <- overwrite, khong duplicate
```

Auto-test: Pass | Before: 'sữa bò' -> After: 'đậu nành' (expected: 'dau nanh')

Co che: extract_and_store() phat hien correction markers ('a nham', 'khong phai', ...)
-> goi delete_preference('allergy') truoc -> luu fact moi. Khong append, khong mau thuan.

---

## Reflection - Privacy & Limitations

**Memory nao giup agent nhat?**
- Long-term (Redis): Nho language preference & allergy xuyen session -> proactively goi y Python.
- Short-term: Duy tri coherence multi-turn, khong lap cau hoi.
- Episodic: Recall confusion/error da gap -> tu them explanation chi tiet.
- Semantic (TF-IDF): Inject factual knowledge (FastAPI, Docker) vao context.

**Memory nao rui ro nhat neu retrieve sai?**
- Long-term Profile: Luu sai allergy -> goi y thuc pham gay nguy hiem. Rui ro cao nhat.
- Episodic: Retrieve nham episode cua user khac -> PII leak.

**PII / Privacy Risks:**

| Rui ro | Mitigation |
|--------|------------|
| Ten, di ung luu plain text | Encrypt at rest + RBAC |
| session_id predictable | UUID random, khong path traversal |
| Khong co TTL -> stale memory | TTL per Redis key, archive JSON sau N ngay |
| Thieu consent flow | Explicit opt-in khi lan dau dung agent |
| Khong co deletion API | Implement agent.forget(user_id) |

**Neu user yeu cau xoa memory:**
- Short-term: agent.short_term.clear()
- Long-term: agent.long_term.clear_all()
- Episodic: xoa logs/episodic_log_{session_id}.json
- Semantic: agent.semantic = SemanticMemory() (can re-seed)

**Technical Limitations:**
- TF-IDF bo lo paraphrase -> nen upgrade sang Chroma + embeddings
- fakeredis mat data sau restart -> can Redis that + AOF
- Token count dung len/4 heuristic -> nen dung tiktoken
- Khong co multi-user isolation -> can namespace per user_id

---

*Raw data: logs/benchmark_raw_<timestamp>.json*