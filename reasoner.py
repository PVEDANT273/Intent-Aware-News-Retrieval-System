import json
import re

from ollama import Client

MAX_RETRIES = 3


def pick_representative_article(articles):
    return max(
        articles,
        key=lambda a: len((a.get("content") or "") + (a.get("description") or "")),
    )


class Reasoner:
    def __init__(
        self,
        list_of_groups,
        topic,
        intent,
        model="llama3.1:8b",
        host="http://localhost:11434",
    ):
        self.list_of_groups = list_of_groups
        self.topic = topic
        self.intent = intent
        self.model = model
        self.client = Client(host=host)

    def extract(self):
        groups_data = []
        for i, group in enumerate(self.list_of_groups):
            groups_data.append({
                "group_id": i,
                "number_of_articles": len(group),
                "titles": [a.get("title") or "" for a in group],
                "sources": [a.get("source") or "" for a in group],
            })
        return groups_data

    def _build_prompt(self):
        articles = json.dumps(self.extract(), indent=2)
        return f"""
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

    @staticmethod
    def _parse_json(raw):
        raw = raw.strip()

        # Prefer a ```json fenced block if the model added one
        match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
        if match:
            raw = match.group(1).strip()

        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end < start:
            raise ValueError("No JSON array found in LLM output")

        return json.loads(raw[start:end + 1])

    def _validate(self, ranked):
        """Keep only well-formed items with a real group_id, no duplicates."""
        if not isinstance(ranked, list):
            raise ValueError("LLM output is not a JSON array")

        valid = []
        seen = set()
        for item in ranked:
            try:
                group_id = int(item["group_id"])
                rank = int(item["rank"])
            except (KeyError, TypeError, ValueError):
                continue

            if not 0 <= group_id < len(self.list_of_groups) or group_id in seen:
                continue

            seen.add(group_id)
            valid.append({
                "group_id": group_id,
                "rank": rank,
                "reason": str(item.get("reason", "")),
            })

        return sorted(valid, key=lambda x: x["rank"])

    def rank(self):
        prompt = self._build_prompt()
        last_error = None

        for _ in range(MAX_RETRIES):
            try:
                response = self.client.chat(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.3},
                )
                raw = response["message"]["content"]
                return self._validate(self._parse_json(raw))
            except (ValueError, json.JSONDecodeError) as e:
                last_error = e  # malformed output, try again

        raise RuntimeError(
            f"LLM did not return valid JSON after {MAX_RETRIES} attempts: {last_error}"
        )

    def build(self, ranked_groups, grouped_articles, top_n=None):
        if top_n is not None:
            ranked_groups = ranked_groups[:top_n]

        results = []
        for item in ranked_groups:
            articles = grouped_articles[item["group_id"]]

            results.append({
                "group_id": item["group_id"],
                "rank": item["rank"],
                "reason": item["reason"],
                "representative_article": pick_representative_article(articles),
                "all_articles": articles,
            })

        return results