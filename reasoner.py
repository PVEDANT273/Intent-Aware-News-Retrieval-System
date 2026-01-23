from ollama import Client
import re
import json

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


        client = Client(host="http://localhost:11434")

        response = client.chat(
            model="llama3.1:8b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3}
        )

        raw = response["message"]["content"].strip()

        pattern = r"```json\s*(.*?)\s*```"
        match = re.search(pattern, raw, re.DOTALL)

        if not match:
            # fallback to bracket extraction
            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start == -1 or end == -1:
                raise ValueError("No JSON found in LLM output")
            return json.loads(raw[start:end])

        json_str = match.group(1).strip()
        return json.loads(json_str)
    
    
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

