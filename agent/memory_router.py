from enum import Enum
from typing import List


class MemoryType(Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"


class MemoryRouter:
    """Route truy vấn đến các memory backend phù hợp."""

    PREFERENCE_KW = [
        "thích", "không thích", "prefer", "like", "dislike",
        "hate", "yêu thích", "ghét", "favorite", "tôi tên là",
        "tên tôi là", "dị ứng", "beginner", "senior", "intermediate",
        "mới bắt đầu", "có kinh nghiệm",
    ]
    EPISODIC_KW = [
        "nhớ", "remember", "recall", "lần trước", "hôm qua", "trước đây",
        "đã từng", "lịch sử", "history", "confused", "bị confused",
        "gặp vấn đề", "đã hỏi", "trải nghiệm", "debug", "lỗi", "error",
        "bài học", "lesson learned",
    ]
    SEMANTIC_KW = [
        "giải thích", "explain", "là gì", "what is", "how does",
        "tại sao", "why", "khái niệm", "concept", "định nghĩa", "definition",
        "so sánh", "checklist", "best practice", "trade-off",
    ]

    def route(self, query: str) -> List[MemoryType]:
        q = query.lower()
        types: List[MemoryType] = []
        if any(kw in q for kw in self.PREFERENCE_KW):
            types.append(MemoryType.LONG_TERM)
        if any(kw in q for kw in self.EPISODIC_KW):
            types.append(MemoryType.EPISODIC)
        if any(kw in q for kw in self.SEMANTIC_KW):
            types.append(MemoryType.SEMANTIC)
        if MemoryType.SHORT_TERM not in types:
            types.append(MemoryType.SHORT_TERM)
        return types

    def should_store_preference(self, text: str) -> bool:
        return any(kw in text.lower() for kw in self.PREFERENCE_KW)

    def should_store_episode(self, text: str, response: str) -> bool:
        combined = (text + " " + response).lower()
        keywords = [
            "confused", "bị confused", "khó hiểu", "không hiểu",
            "lỗi", "error", "fix", "debug", "task hoàn thành",
            "xong rồi", "kết quả", "bài học", "lesson learned",
        ]
        return any(kw in combined for kw in keywords)

    def classify_episode_tags(self, text: str, response: str) -> List[str]:
        combined = (text + " " + response).lower()
        tags: List[str] = []
        if any(kw in combined for kw in ["confused", "khó hiểu", "không hiểu"]):
            tags.append("confusion")
        if any(kw in combined for kw in ["lỗi", "error", "debug", "fix"]):
            tags.append("debug")
        if any(kw in combined for kw in ["xong rồi", "kết quả", "hoàn thành"]):
            tags.append("outcome")
        if not tags:
            tags.append("general")
        return tags
