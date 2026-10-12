from rapidfuzz import fuzz

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
    
    
    def remove_duplicates(self, normalized_articles, title_threshold=90):
        seen_urls = set()
        kept_titles = []
        unique_articles = []

        for article in normalized_articles:
            url = (article["url"] or "").lower().strip()
            title = (article["title"] or "").lower().strip()

            if url and url in seen_urls:
                continue

            is_dup = any(
                fuzz.token_sort_ratio(title, kept) >= title_threshold
                for kept in kept_titles
            )

            if is_dup:
                continue

            unique_articles.append(article)

            if url:
                seen_urls.add(url)

            if title:
                kept_titles.append(title)

        return unique_articles
    

