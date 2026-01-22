
class ArticleCleaner:
    def normalize(self, api_response: dict) -> list:
        articles = api_response.get("articles", [])
        normalized = []

        for a in articles:
            normalized.append({
                "title": a.get("title"),
                "description": a.get("description"),
                "content": a.get("content"),
                "source": a.get("source", {}).get("name"),
                "url": a.get("url"),
                "published_at": a.get("publishedAt")
            })

        return normalized
    

