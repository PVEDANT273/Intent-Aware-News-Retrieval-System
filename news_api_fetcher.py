import os
from datetime import datetime
from dotenv import load_dotenv
from newsapi import NewsApiClient

load_dotenv()


class NewsApiFetcher:
    def __init__(self):
        self.NEWS_API_KEY = os.getenv("NEWS_API_KEY")
        if not self.NEWS_API_KEY:
            raise ValueError("API key not found")

        self.npi = NewsApiClient(api_key=self.NEWS_API_KEY)

    def get_top_headlines(
            self,
            topic: str,
            sources=None,
            category=None,
            language='en',
            country=None
    ):
        if sources and (country or category):
            raise ValueError(
                "Invalid parameters: 'sources' cannot be used with "
                "'country' or 'category' in get_top_headlines()"
            )

        self.top_headlines = self.npi.get_top_headlines(q=topic,
                                          sources=sources,
                                          category=category,
                                          language=language,
                                          country=country)

        return self.top_headlines

    def get_all_articles(
            self,
            topic: str,
            sources=None,
            domains=None,
            start_date='2017-12-01',
            end_date=None,
            category=None,
            language='en',
            country=None
    ):
        if sources and (country or category):
            raise ValueError(
                "Invalid parameters: 'sources' cannot be used with "
                "'country' or 'category' in get_top_headlines()"
            )

        if end_date is None:
            end_date = datetime.today().strftime('%Y-%m-%d')

        self.all_articles = self.npi.get_everything(q=topic,
                                      sources=sources,
                                      domains=domains,
                                      from_param=start_date,
                                      to=end_date,
                                      language=language,
                                      sort_by='relevancy',
                                      page=1)

        return self.all_articles