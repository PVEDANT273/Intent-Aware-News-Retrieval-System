
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
        duplicate = False

        for article in normalized_articles:
            if article['url']:
                if article['url'].lower().strip() in seen_urls:
                    duplicate = True

            if article['title']:
                if article['title'].lower().strip() in seen_titles:
                    duplicate = True

            if not duplicate:
                unique_articles.append(article)
                if article['url']:
                    seen_urls.add(article['url'].lower().strip())
                if article['title']:
                    seen_titles.add(article['title'].lower().strip())
            
            duplicate = False
        
        return unique_articles
    

