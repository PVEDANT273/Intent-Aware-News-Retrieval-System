from ollama import Client
import re
import json

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
            Topic: {self.topic}
            Intent: {self.intent}

            Here are several groups of articles:
            {articles}

            Task : Rank the groups by how well they satisfy the intent and summarize why
            Output Format(strict Json):
            [
                {{
                    "group_id": <number>,
                    "rank": <number>,
                    "reason": "<one or two short sentences>"
                }}
            ]

        """

        client = Client(host="http://localhost:11434")

        response = client.chat(
            model="llama3.1:8b",
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.3}
        )

        raw = response["message"]["content"].strip()

        raw = re.sub(r"```json|```", "", raw).strip()

        start = raw.find("[")
        end = raw.rfind("]") + 1

        if start == -1 or end == -1:
            raise ValueError("No JSON found in LLM response")

        json_str = raw[start:end]

        return json.loads(json_str)
    
    
    def get_original_articles(self, llm_json : list, original_grouped : list):
        results = []

        for item in llm_json:
            group_id = item["group_id"]

        results.append({
            "group_id": group_id,
            "rank": item["rank"],
            "reason": item["reason"],
            "articles": original_grouped[group_id]
        })

        return results

