import json
import re

from ollama import Client
from datetime import datetime, timezone

MAX_RETRIES = 3


def pick_representative_article(articles):
    return max(
        articles,
        key=lambda a: len(
            (a.get("content") or "") + (a.get("description") or "")
        ),
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

    def build(
        self,
        ranked_groups,
        grouped_articles,
        top_n=None,
        recency_weight=0.2,
    ):
        scored = []

        for item in ranked_groups:
            articles = grouped_articles[item["group_id"]]

            llm_score = 1 / item["rank"]

            blended = (
                (1 - recency_weight) * llm_score
                + recency_weight * self._recency_score(articles)
            )

            scored.append((blended, item, articles))

        scored.sort(key=lambda x: x[0], reverse=True)

        scored = self._diversify(scored)

        if top_n is not None:
            scored = scored[:top_n]

        results = []

        for rank, (score, item, articles) in enumerate(scored, start=1):
            results.append({
                "group_id": item["group_id"],
                "rank": rank,
                "reason": item["reason"],
                "representative_article": pick_representative_article(articles),
                "all_articles": articles,
                "summary": self.summarize_group(articles),
            })

        return results

    def summarize_group(self, group_articles):
        texts = "\n".join(
            f"- {a.get('title', '')}: {a.get('description', '')}"
            for a in group_articles
        )

        prompt = f"""Summarize the following news coverage of the same
                    story in 2-3 sentences. Be neutral and factual.

                    {texts}

                    Summary:"""

        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0.2},
        )

        return response["message"]["content"].strip()

    def _recency_score(self, group_articles):
        dates = [
            a.get("published_at")
            for a in group_articles
            if a.get("published_at")
        ]

        if not dates:
            return 0.0

        newest = max(
            datetime.fromisoformat(d.replace("Z", "+00:00"))
            for d in dates
        )

        hours_old = (
            datetime.now(timezone.utc) - newest
        ).total_seconds() / 3600

        return max(0.0, 1 - hours_old / 168)

    def _diversify(self, scored, max_per_source=2):
        from collections import defaultdict

        source_counts = defaultdict(int)
        ordered, deferred = [], []

        for entry in scored:
            _, item, articles = entry

            source = pick_representative_article(articles).get("source") or "unknown"

            if source_counts[source] < max_per_source:
                ordered.append(entry)
                source_counts[source] += 1
            else:
                deferred.append(entry)

        return ordered + deferred