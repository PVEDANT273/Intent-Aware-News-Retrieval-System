import os
from ollama import Client, ResponseError
import re
import json

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")


def pick_representative_article(articles):
            return max(
                articles,
                key=lambda a: len((a.get("content") or "") + (a.get("description") or ""))
                )

class Reasoner:
    def __init__(self, list_of_groups, topic, intent):
        self.list_of_groups = list_of_groups
        self.topic = topic
        self.intent = intent

    def extract(self):
        groups_data = []
        for i, groups in enumerate(self.list_of_groups):
            titles = []
            sources = []

            for article in groups:
                titles.append(article.get("title", ""))
                sources.append(article.get("source", ""))

            groups_data.append({
                "group_id": i,
                "number_of_articles" : len(groups),
                "titles" : titles,
                "sources": sources 
            })            
        return groups_data
    
    
    def rank(self):
        articles = self.extract()
        prompt = f"""
            You are a JSON-only ranking engine.

            Topic: {self.topic}
            Intent: {self.intent}

            Below are groups of articles:
            {articles}

            TASK:
            Select ONLY the groups relevant to the intent and rank them.

            OUTPUT RULES:
            - Output MUST be valid JSON
            - Output MUST be a JSON array
            - Do NOT include explanations, analysis, markdown, or text outside JSON
            - Do NOT include groups that are irrelevant

            OUTPUT FORMAT:
            [
            {{
                "group_id": <number>,
                "rank": <number>,
                "reason": "<short explanation>"
            }}
            ]

            If you violate these rules, the output is invalid.
            """


        client = Client(host=OLLAMA_HOST)

        max_attempts = 2
        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = client.chat(
                    model=OLLAMA_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.3}
                )
            except ConnectionError as e:
                raise RuntimeError(
                    f"Could not reach Ollama at {OLLAMA_HOST}. "
                    "Is 'ollama serve' running?"
                ) from e
            except ResponseError as e:
                raise RuntimeError(
                    f"Ollama model '{OLLAMA_MODEL}' failed to respond "
                    f"(is it pulled? try 'ollama pull {OLLAMA_MODEL}'): {e}"
                ) from e

            raw = response["message"]["content"].strip()

            pattern = r"```json\s*(.*?)\s*```"
            match = re.search(pattern, raw, re.DOTALL)

            if match:
                json_str = match.group(1).strip()
            else:
                # fallback to bracket extraction
                start = raw.find("[")
                end = raw.rfind("]") + 1
                if start == -1 or end == -1:
                    last_error = ValueError("No JSON found in LLM output")
                    continue
                json_str = raw[start:end]

                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e:
                    last_error = e
                    continue

        raise ValueError(
            f"LLM did not return valid JSON after {max_attempts} attempt(s): {last_error}"
        )
    
    
    def build(self, ranked_groups, grouped_articles):
        
        results = []

        for item in ranked_groups:
            group_id = item["group_id"]
            articles = grouped_articles[group_id]

            representative = pick_representative_article(articles)

            results.append({
                "group_id": group_id,
                "rank": item["rank"],
                "reason": item["reason"], 
                "representative_article": representative,
                "all_articles": articles
            })

        return results

