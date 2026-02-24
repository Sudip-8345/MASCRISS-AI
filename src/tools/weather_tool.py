import json
import os
import urllib.parse
import urllib.request
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class _WeatherInput(BaseModel):
    location: str = Field(
        ...,
        description="City or port name, e.g. 'Shanghai', 'Mumbai', 'Busan'.",
    )


class WeatherAlertTool(BaseTool):
    name: str = "check_weather_alerts"
    description: str = (
        "Check current weather conditions and severe-weather alerts for a port city "
        "or logistics hub. Returns temperature, wind, humidity, and active warnings "
        "that could disrupt shipping operations."
    )
    args_schema: Type[BaseModel] = _WeatherInput

    def _run(self, location: str) -> str:
        api_key = os.environ.get("OPENWEATHER_API_KEY")
        if api_key:
            return self._live_weather(location, api_key)
        return self._simulated_weather(location)

    # ------------------------------------------------------------------
    def _live_weather(self, location: str, api_key: str) -> str:
        try:
            params = urllib.parse.urlencode({"q": location, "appid": api_key, "units": "metric"})
            url = f"https://api.openweathermap.org/data/2.5/weather?{params}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())

            alerts: list[str] = []
            wind = data["wind"]["speed"]
            wid = data["weather"][0]["id"]

            if wind > 20:
                alerts.append(f"HIGH WIND WARNING: {wind} m/s — port ops may be affected")
            if wid < 300:
                alerts.append("THUNDERSTORM WARNING: Active thunderstorms")
            elif wid < 600:
                alerts.append("HEAVY RAIN WARNING: Possible flooding risk")

            return json.dumps(
                {
                    "location": location,
                    "temperature_celsius": data["main"]["temp"],
                    "conditions": data["weather"][0]["description"],
                    "wind_speed_ms": wind,
                    "humidity": data["main"]["humidity"],
                    "alerts": alerts or ["No severe weather alerts"],
                }
            )
        except Exception:
            return self._simulated_weather(location)

    # ------------------------------------------------------------------
    @staticmethod
    def _simulated_weather(location: str) -> str:
        catalog = {
            "shanghai": {
                "location": "Shanghai",
                "temperature_celsius": 8,
                "conditions": "Tropical storm approaching",
                "wind_speed_kmh": 95,
                "humidity_pct": 92,
                "alerts": [
                    "TYPHOON WARNING: Typhoon Melor — Cat-3 expected within 48 h",
                    "STORM SURGE WARNING: 2-3 m surge expected at port",
                    "PORT CLOSURE ADVISORY: Ops likely halted March 3-5",
                ],
                "risk_level": "CRITICAL",
            },
            "busan": {
                "location": "Busan",
                "temperature_celsius": 4,
                "conditions": "Overcast, light rain",
                "wind_speed_kmh": 25,
                "humidity_pct": 78,
                "alerts": [
                    "WEATHER CLEAR — disruptions are labor-related, not weather",
                ],
                "risk_level": "LOW",
            },
            "ho chi minh city": {
                "location": "Ho Chi Minh City",
                "temperature_celsius": 31,
                "conditions": "Heavy monsoon rain",
                "wind_speed_kmh": 40,
                "humidity_pct": 95,
                "alerts": [
                    "FLOOD WARNING: 200 mm rainfall in last 24 h",
                    "ROAD DISRUPTION: Industrial-zone access roads partially flooded",
                    "LOGISTICS ADVISORY: Truck deliveries to port delayed 6-12 h",
                ],
                "risk_level": "HIGH",
            },
            "mumbai": {
                "location": "Mumbai",
                "temperature_celsius": 28,
                "conditions": "Partly cloudy",
                "wind_speed_kmh": 15,
                "humidity_pct": 65,
                "alerts": [
                    "WEATHER CLEAR — port disruptions are labor-related (planned stoppage)",
                ],
                "risk_level": "LOW",
            },
        }

        entry = catalog.get(location.lower())
        if entry:
            return json.dumps(entry)

        return json.dumps(
            {
                "location": location,
                "temperature_celsius": 20,
                "conditions": "Clear skies",
                "wind_speed_kmh": 10,
                "humidity_pct": 55,
                "alerts": ["No severe weather alerts"],
                "risk_level": "LOW",
                "note": "Simulated — set OPENWEATHER_API_KEY for live data",
            }
        )