
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
    
    
    def remove_duplicates(self, normalized_articles):
        seen_urls = set()
        seen_titles = set()
        unique_articles = []

        for article in normalized_articles:
            url = article['url'].lower().strip() if article['url'] else None
            title = article['title'].lower().strip() if article['title'] else None

            is_dup = (url is not None and url in seen_urls) or \
                    (title is not None and title in seen_titles)

            if not is_dup:
                unique_articles.append(article)
                if url:
                    seen_urls.add(url)
                if title:
                    seen_titles.add(title)

        return unique_articles
    

