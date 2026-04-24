from typing import List, Dict


class ConversationBufferMemory:
    """Short-term in-session conversation history."""

    def __init__(self, max_turns: int = 10):
        self.history: List[Dict[str, str]] = []
        self.max_turns = max_turns

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_turns * 2:
            self.history = self.history[-(self.max_turns * 2):]

    def get_history(self) -> List[Dict[str, str]]:
        return self.history.copy()

    def clear(self):
        self.history = []

    def to_context_string(self) -> str:
        if not self.history:
            return ""
        lines = ["[Hội thoại gần đây | Short-term memory]"]
        for msg in self.history[-6:]:
            role = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{role}: {msg['content']}")
        return "\n".join(lines)
