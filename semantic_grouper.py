import hashlib
from diskcache import Cache


class SemanticGrouper:
    def __init__(self, similarity_threshold=0.8):
        ...
        self.cache = Cache(".embedding_cache")

    def _embed_cached(self, texts):
        vectors = []
        to_embed, to_embed_idx = [], []

        for i, t in enumerate(texts):
            key = hashlib.sha256(t.encode()).hexdigest()
            cached = self.cache.get(key)

            if cached is not None:
                vectors.append(cached)
            else:
                vectors.append(None)
                to_embed.append(t)
                to_embed_idx.append(i)

        if to_embed:
            new_vecs = self.embeddings.embed_documents(to_embed)

            for idx, vec in zip(to_embed_idx, new_vecs):
                vectors[idx] = vec
                key = hashlib.sha256(
                    texts[idx].encode()
                ).hexdigest()
                self.cache.set(key, vec)

        return vectors