from typing import Dict, List


class ContextWindowManager:
    """
    Manages context window with auto-trim and priority-based eviction.

    Priority hierarchy (highest → lowest):
      4. Semantic memory
      3. Episodic memory
      2. Long-term preferences
      1. Short-term buffer
    """

    def __init__(self, max_tokens: int = 3000):
        self.max_tokens = max_tokens

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough estimate: ~4 chars per token."""
        return max(1, len(text) // 4)

    def build_context(
        self,
        short_term: str = "",
        long_term: str = "",
        episodic: str = "",
        semantic: str = "",
    ) -> str:
        """
        Build final context string, evicting lowest-priority content first
        when the token budget is exceeded.
        """
        # Highest priority first; short_term last (lowest priority)
        components = [
            ("semantic", semantic, 4),
            ("episodic", episodic, 3),
            ("long_term", long_term, 2),
            ("short_term", short_term, 1),
        ]

        included: List[str] = []
        total = 0

        for name, content, _priority in components:
            if not content:
                continue
            tokens = self.estimate_tokens(content)
            if total + tokens <= self.max_tokens:
                included.append(content)
                total += tokens
            elif name == "short_term":
                # Trim short-term to fit remaining budget
                remaining_chars = (self.max_tokens - total) * 4
                if remaining_chars > 100:
                    included.append("[Lịch sử cũ đã được rút gọn để giữ token budget]\n" + content[-remaining_chars:])
            # Higher-priority items that don't fit are skipped (shouldn't happen normally)

        return "\n\n".join(included)

    def build_context_breakdown(
        self,
        short_term: str = "",
        long_term: str = "",
        episodic: str = "",
        semantic: str = "",
    ) -> List[Dict[str, int]]:
        parts = [
            ("semantic", semantic, 4),
            ("episodic", episodic, 3),
            ("long_term", long_term, 2),
            ("short_term", short_term, 1),
        ]
        return [
            {
                "memory_type": name,
                "priority": priority,
                "tokens_estimate": self.estimate_tokens(content),
                "chars": len(content),
            }
            for name, content, priority in parts
            if content
        ]

    @staticmethod
    def auto_trim_history(history: List[Dict], max_turns: int = 8) -> List[Dict]:
        """Keep only the most recent max_turns exchanges."""
        cutoff = max_turns * 2
        return history[-cutoff:] if len(history) > cutoff else history
