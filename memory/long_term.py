import json
import os
import re
from typing import Any, Optional

import fakeredis


class RedisLongTermMemory:
    """
    Long-term profile memory.

    Dùng fakeredis để giữ interface Redis rõ ràng và thêm JSON snapshot để
    bền hơn giữa các lần khởi tạo agent khi môi trường cho phép ghi file.
    """

    _server = fakeredis.FakeServer()

    def __init__(self, namespace: str = "default", filepath: Optional[str] = None):
        self.namespace = namespace
        self.redis_key = f"preferences:{namespace}"
        self.filepath = filepath
        self.persistence_available = True
        self.client = fakeredis.FakeRedis(server=self._server, decode_responses=True)
        self._load_from_disk()

    def _load_from_disk(self):
        if not self.filepath or not os.path.exists(self.filepath):
            return
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (PermissionError, OSError, json.JSONDecodeError):
            self.persistence_available = False
            return

        self.client.delete(self.redis_key)
        for key, value in data.items():
            self.client.hset(self.redis_key, key, json.dumps(value, ensure_ascii=False))

    def _persist_to_disk(self):
        if not self.filepath or not self.persistence_available:
            return
        try:
            directory = os.path.dirname(self.filepath)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.get_all_preferences(), f, ensure_ascii=False, indent=2)
        except (PermissionError, OSError):
            self.persistence_available = False

    def store_preference(self, key: str, value: Any):
        self.client.hset(self.redis_key, key, json.dumps(value, ensure_ascii=False))
        self._persist_to_disk()

    def get_preference(self, key: str) -> Optional[Any]:
        val = self.client.hget(self.redis_key, key)
        return json.loads(val) if val else None

    def get_all_preferences(self) -> dict:
        prefs = self.client.hgetall(self.redis_key)
        return {k: json.loads(v) for k, v in prefs.items()}

    def delete_preference(self, key: str):
        self.client.hdel(self.redis_key, key)
        self._persist_to_disk()

    def clear_all(self):
        self.client.delete(self.redis_key)
        self._persist_to_disk()

    def extract_and_store(self, text: str):
        text_lower = text.lower()

        languages = [
            "python", "java", "javascript", "typescript",
            "rust", "go", "c++", "ruby", "kotlin", "swift",
        ]
        for lang in languages:
            is_disliked = any(
                marker in text_lower
                for marker in [f"không thích {lang}", f"dislike {lang}", f"hate {lang}", f"ghét {lang}"]
            )
            is_liked = any(
                marker in text_lower
                for marker in [f"thích {lang}", f"like {lang}", f"prefer {lang}", f"yêu thích {lang}"]
            )
            if is_disliked:
                self.store_preference("dislikes_language", lang)
            elif is_liked:
                self.store_preference("likes_language", lang)

        correction_markers = [
            "à nhầm", "nhầm rồi", "không phải", "sửa lại",
            "thực ra", "ý tôi là", "chính xác hơn",
        ]
        is_correction = any(marker in text_lower for marker in correction_markers)
        allergens = [
            "sữa bò", "đậu nành", "gluten", "hải sản",
            "lạc", "trứng", "milk", "soy", "peanut",
        ]
        mentioned_allergens = [allergen for allergen in allergens if allergen in text_lower]
        if mentioned_allergens:
            chosen = mentioned_allergens[-1] if is_correction else mentioned_allergens[0]
            if is_correction:
                self.delete_preference("allergy")
            self.store_preference("allergy", chosen)

        name_match = re.search(
            r"(?:tôi tên là|tên tôi là|tôi là|my name is|call me)\s+([a-zà-ỹ]+)",
            text_lower,
        )
        if name_match:
            self.store_preference("name", name_match.group(1).strip().title())

        if any(marker in text_lower for marker in ["mới bắt đầu", "beginner", "chưa biết", "newbie", "6 tháng"]):
            self.store_preference("level", "beginner")
        elif any(marker in text_lower for marker in ["trung cấp", "intermediate", "có kinh nghiệm", "vài năm"]):
            self.store_preference("level", "intermediate")
        elif any(marker in text_lower for marker in ["senior", "cao cấp", "chuyên gia", "expert"]):
            self.store_preference("level", "senior")

    def to_context_string(self) -> str:
        prefs = self.get_all_preferences()
        if not prefs:
            return ""
        lines = ["[Hồ sơ người dùng | Long-term memory]"]
        for key, value in prefs.items():
            lines.append(f"  - {key}: {value}")
        return "\n".join(lines)
