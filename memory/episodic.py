import json
import os
from datetime import datetime
from typing import List, Dict


class EpisodicMemory:
    """Episodic memory stored as JSON file for cross-session persistence."""

    def __init__(self, filepath: str = "episodic_log.json"):
        self.filepath = filepath
        self.episodes: List[Dict] = []
        self.persistence_available = True
        self._load()

    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.episodes = json.load(f)
            except (PermissionError, OSError, json.JSONDecodeError):
                self.persistence_available = False

    def _save(self):
        if not self.persistence_available:
            return
        directory = os.path.dirname(self.filepath)
        try:
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.episodes, f, ensure_ascii=False, indent=2)
        except (PermissionError, OSError):
            self.persistence_available = False

    def store_episode(self, title: str, content: str, tags: List[str] = None):
        episode = {
            "id": len(self.episodes),
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "content": content,
            "tags": tags or [],
        }
        self.episodes.append(episode)
        self._save()
        return episode

    def search_episodes(self, query: str, top_k: int = 3) -> List[Dict]:
        query_lower = query.lower()
        scored = []
        for ep in self.episodes:
            text = (ep["title"] + " " + ep["content"] + " " + " ".join(ep["tags"])).lower()
            score = sum(1 for word in query_lower.split() if word in text)
            if score > 0:
                scored.append((score, ep))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [ep for _, ep in scored[:top_k]]

    def get_all(self) -> List[Dict]:
        """Return all episodes."""
        return list(self.episodes)

    def clear(self):
        self.episodes = []
        self._save()

    def to_context_string(self, query: str = "") -> str:
        episodes = self.search_episodes(query) if query else self.episodes[-3:]
        if not episodes:
            return ""
        lines = ["[Ký ức trải nghiệm | Episodic memory]"]
        for ep in episodes:
            lines.append(f"  - [{ep['timestamp'][:10]}] {ep['title']}: {ep['content'][:120]}")
        return "\n".join(lines)
