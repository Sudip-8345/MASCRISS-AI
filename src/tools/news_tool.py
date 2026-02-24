import json
import os
import urllib.request
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class _NewsInput(BaseModel):
    query: str = Field(
        ...,
        description="Search query for supply-chain news, e.g. 'port strike Shanghai' or 'typhoon logistics Asia'.",
    )


class NewsScanTool(BaseTool):
    name: str = "search_supply_chain_news"
    description: str = (
        "Search recent global news for supply-chain disruptions — port closures, "
        "labor strikes, natural disasters, geopolitical tensions, and logistics threats. "
        "Returns relevant articles with title, snippet, source, and date."
    )
    args_schema: Type[BaseModel] = _NewsInput

    def _run(self, query: str) -> str:
        api_key = os.environ.get("SERPER_API_KEY")
        if api_key:
            return self._live_search(query, api_key)
        return self._simulated_news(query)

    # ------------------------------------------------------------------
    def _live_search(self, query: str, api_key: str) -> str:
        try:
            url = "https://google.serper.dev/news"
            body = json.dumps({"q": f"{query} supply chain logistics", "num": 5}).encode()
            req = urllib.request.Request(
                url,
                data=body,
                headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            articles = [
                {
                    "title": item.get("title"),
                    "snippet": item.get("snippet"),
                    "source": item.get("source"),
                    "date": item.get("date"),
                    "link": item.get("link"),
                }
                for item in data.get("news", [])[:5]
            ]
            return json.dumps({"query": query, "results": articles, "count": len(articles)})
        except Exception:
            return self._simulated_news(query)

    # ------------------------------------------------------------------
    @staticmethod
    def _simulated_news(query: str) -> str:
        alerts = [
            {
                "title": "Typhoon Melor Approaches Shanghai Port — Category 3 Storm Expected",
                "snippet": (
                    "Shanghai port authorities issue advisory as Typhoon Melor tracks toward "
                    "the East China Sea. Operations may be suspended for 48-72 hours starting March 3."
                ),
                "source": "Reuters Maritime",
                "date": "2026-02-23",
                "severity": "HIGH",
                "affected_region": "Shanghai, East China",
            },
            {
                "title": "Dockworkers Strike at Busan Port Enters Third Day",
                "snippet": (
                    "Labor negotiations at South Korea's largest port remain stalled. "
                    "200+ vessels at anchorage; container processing down 80 %."
                ),
                "source": "Lloyd's List",
                "date": "2026-02-22",
                "severity": "HIGH",
                "affected_region": "Busan, South Korea",
            },
            {
                "title": "Flooding in Ho Chi Minh City Disrupts Factory Output",
                "snippet": (
                    "Heavy monsoon rains cause severe flooding in industrial zones. "
                    "Several textile and electronics factories report production halts."
                ),
                "source": "Nikkei Asia",
                "date": "2026-02-21",
                "severity": "MEDIUM",
                "affected_region": "Ho Chi Minh City, Vietnam",
            },
            {
                "title": "Suez Canal Reports Increased Wait Times After Vessel Grounding",
                "snippet": (
                    "A container vessel ran aground in the southern section, "
                    "causing 12-24 hour delays for northbound traffic."
                ),
                "source": "Maritime Executive",
                "date": "2026-02-23",
                "severity": "MEDIUM",
                "affected_region": "Suez Canal, Egypt",
            },
            {
                "title": "India Port Workers Union Announces Planned Work Stoppage",
                "snippet": (
                    "Mumbai and Chennai port workers announce a 48-hour stoppage next week "
                    "over wage disputes. Cargo processing expected to slow significantly."
                ),
                "source": "Economic Times",
                "date": "2026-02-22",
                "severity": "MEDIUM",
                "affected_region": "Mumbai, India",
            },
        ]

        q_lower = query.lower()
        relevant = [
            a
            for a in alerts
            if any(
                w in a["title"].lower() or w in a["affected_region"].lower()
                for w in q_lower.split()
            )
        ]
        if not relevant:
            relevant = alerts

        return json.dumps(
            {
                "query": query,
                "results": relevant,
                "count": len(relevant),
                "note": "Simulated data — set SERPER_API_KEY for live results",
            }
        )