import gradio as gr

from article_cleaner import ArticleCleaner
from news_api_fetcher import NewsApiFetcher
from reasoner import Reasoner
from semantic_grouper import SemanticGrouper

npi = NewsApiFetcher()
cleaner = ArticleCleaner()
sg = SemanticGrouper()


def run_pipeline(topic, intent, num_fetch, num_results):
    raw = npi.get_top_headlines(topic=topic, country="us", page_size=num_fetch)
    cleaned = cleaner.normalize(raw)
    unique = cleaner.remove_duplicates(cleaned)

    if not unique:
        return []

    grouped = sg.group(unique)

    reasoner = Reasoner(grouped, topic, intent)
    ranked = reasoner.rank()
    return reasoner.build(ranked, grouped, top_n=num_results)


def format_results(results):
    if not results:
        return (
            "No relevant articles found. "
            "Try a broader topic or increase **Articles to fetch**."
        )

    blocks = []
    for res in results:
        art = res["representative_article"]
        blocks.append("\n".join([
            f"### Rank {res['rank']}",
            f"**Why relevant:** {res['reason']}",
            "",
            f"**Title:** {art['title']}",
            "",
            f"**Source:** {art['source']}",
            "",
            f"**URL:** {art['url']}",
            "",
            f"**Articles covering this story:** {len(res['all_articles'])}",
            "",
            "---",
        ]))

    return "\n\n".join(blocks)


def gradio_app(topic, intent, num_fetch, num_results):
    topic = (topic or "").strip()
    intent = (intent or "").strip()
    if not topic or not intent:
        raise gr.Error("Please enter both a topic and an intent.")

    try:
        results = run_pipeline(topic, intent, int(num_fetch), int(num_results))
    except Exception as e:
        raise gr.Error(f"Something went wrong: {e}")

    return format_results(results)


dashboard = gr.Interface(
    fn=gradio_app,
    inputs=[
        gr.Textbox(label="Topic", placeholder="AI"),
        gr.Textbox(label="Intent", placeholder="Effects on RAM prices"),
        gr.Slider(
            minimum=10, maximum=100, value=30, step=5,
            label="Articles to fetch",
            info="How many headlines to pull from NewsAPI (max 100).",
        ),
        gr.Slider(
            minimum=1, maximum=10, value=5, step=1,
            label="Results to show",
            info="How many top-ranked stories to display.",
        ),
    ],
    outputs=gr.Markdown(),
    title="Intent-Aware News Retrieval",
    description="Fetches and ranks news articles based on topic and user intent.",
)

if __name__ == "__main__":
    dashboard.launch(theme=gr.themes.Ocean())