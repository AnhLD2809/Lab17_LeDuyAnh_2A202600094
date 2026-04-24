import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple


class SemanticMemory:
    """Semantic memory using TF-IDF cosine similarity (no GPU needed)."""

    def __init__(self):
        self.documents: List[Dict] = []
        self.vectorizer = TfidfVectorizer()
        self._matrix = None
        self._fitted = False

    def add_document(self, content: str, metadata: Dict = None):
        self.documents.append({"content": content, "metadata": metadata or {}})
        self._refit()

    def _refit(self):
        if not self.documents:
            self._matrix = None
            self._fitted = False
            return
        texts = [d["content"] for d in self.documents]
        self._matrix = self.vectorizer.fit_transform(texts)
        self._fitted = True

    def clear(self):
        self.documents = []
        self._refit()

    def search(self, query: str, top_k: int = 3) -> List[Tuple[float, Dict]]:
        if not self._fitted:
            return []
        query_vec = self.vectorizer.transform([query])
        scores = cosine_similarity(query_vec, self._matrix)[0]
        top_indices = np.argsort(scores)[::-1][:top_k]
        return [(float(scores[i]), self.documents[i]) for i in top_indices if scores[i] > 0.01]

    def to_context_string(self, query: str) -> str:
        results = self.search(query)
        if not results:
            return ""
        lines = ["[Kiến thức liên quan | Semantic memory]"]
        for score, doc in results:
            lines.append(f"  - (relevance {score:.2f}) {doc['content']}")
        return "\n".join(lines)
