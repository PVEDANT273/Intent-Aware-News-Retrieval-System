import os
from datetime import date, timedelta

from dotenv import load_dotenv
from newsapi import NewsApiClient

load_dotenv()

NEWSAPI_MAX_PAGE_SIZE = 100


class NewsApiFetcher:
    def __init__(self):
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY")
        if not self.NEWS_API_KEY:
            raise ValueError("API key not found. Set NEWS_API_KEY in your .env file.")

        self.npi = NewsApiClient(api_key=self.NEWS_API_KEY)

    @staticmethod
    def _clamp_page_size(page_size):
        return max(1, min(int(page_size), NEWSAPI_MAX_PAGE_SIZE))

    def get_top_headlines(
        self,
        topic: str,
        sources=None,
        category=None,
        language="en",
        country=None,
        page_size=20,
    ):
        # NewsAPI: 'sources' cannot be combined with 'country' or 'category'
        if sources and (country or category):
            raise ValueError(
                "Invalid parameters: 'sources' cannot be used with "
                "'country' or 'category' in get_top_headlines()"
            )

        self.top_headlines = self.npi.get_top_headlines(
            q=topic,
            sources=sources,
            category=category,
            language=language,
            country=country,
            page_size=self._clamp_page_size(page_size),
        )

        return self.top_headlines

    def get_all_articles(
        self,
        topic: str,
        sources=None,
        domains=None,
        start_date=None,
        end_date=None,
        language="en",
        page_size=20,
    ):
        # Dates are computed at call time instead of being hardcoded.
        # NewsAPI's free plan only covers roughly the last 30 days.
        if end_date is None:
            end_date = date.today().isoformat()
        if start_date is None:
            start_date = (date.today() - timedelta(days=30)).isoformat()

        self.all_articles = self.npi.get_everything(
            q=topic,
            sources=sources,
            domains=domains,
            from_param=start_date,
            to=end_date,
            language=language,
            sort_by="relevancy",
            page_size=self._clamp_page_size(page_size),
            page=1,
        )

        return self.all_articles