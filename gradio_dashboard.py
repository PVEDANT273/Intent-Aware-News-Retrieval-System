from article_cleaner import ArticleCleaner
from news_api_fetcher import NewsApiFetcher
from semantic_grouper import SemanticGrouper
from reasoner import Reasoner

import gradio as gr

npi = NewsApiFetcher()
cleaner = ArticleCleaner()
sg = SemanticGrouper()

def run_pipeline(topic, intent):
    raw = npi.get_top_headlines(topic=topic, country="us")
    cleaned = cleaner.normalize(raw)
    unique = cleaner.remove_duplicates(cleaned)
    grouped = sg.group(unique)

    reasoner = Reasoner(grouped, topic, intent)
    ranked = reasoner.rank()
    final_results = reasoner.build(ranked, grouped)

    return final_results


def format_results(results):
    output = ""
    for res in results:
        art = res["representative_article"]
        output += f"""
            ### Rank {res['rank']}
            **Why relevant:** {res['reason']}

            **Title:** {art['title']}
            **Source:** {art['source']}
            **URL:** {art['url']}

            ---
            """
        return output

def gradio_app(topic, intent):
    results = run_pipeline(topic, intent)
    return format_results(results)



dashboard = gr.Interface(
    fn=gradio_app,
    inputs=[
        gr.Textbox(label="Topic", placeholder="AI"),
        gr.Textbox(label="Intent", placeholder="Effects on RAM prices")
    ],
    outputs=gr.Markdown(),
    title="Intent-Aware News Retrieval",
    description="Fetches and ranks news articles based on topic and user intent."
)

if __name__ == "__main__":
    dashboard.launch(theme=gr.themes.Ocean())
