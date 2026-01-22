from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


class SemanticGrouper:
    def __init__(self, similarity_threshold=0.8):
        self.similarity_threshold = similarity_threshold
        self.embeddings = OllamaEmbeddings(
            model="mxbai-embed-large"
        )

    def _build_representation(self, article):
        parts = [
            article.get("title") or "",
            article.get("description") or "",
            (article.get("content") or "")[:200]
        ]
        return " ".join(p for p in parts if p)


    def group(self, articles) ->list:

        texts = [self._build_representation(a) for a in articles]

        vectors = self.embeddings.embed_documents(texts)
        vectors = np.array(vectors)

        similarity_matrix = cosine_similarity(vectors)

        visited = set()
        groups = []

        for i in range(len(articles)):
            if i in visited:
                continue

            group = [articles[i]]
            visited.add(i)

            for j in range(i + 1, len(articles)):
                if j in visited:
                    continue

                if similarity_matrix[i][j] >= self.similarity_threshold:
                    group.append(articles[j])
                    visited.add(j)

            groups.append(group)

        return groups
