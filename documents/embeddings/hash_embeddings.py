import hashlib
import math
import re


class HashEmbeddingProvider:
    """Deterministic local embeddings for the foundation RAG pipeline."""

    dimension = 256

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        terms = re.findall(r"[a-z0-9]+", text.lower())
        for term in terms:
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        magnitude = math.sqrt(sum(value * value for value in vector))
        return [value / magnitude for value in vector] if magnitude else vector
