import json
import os
import urllib.parse
import urllib.request

from fastmcp import FastMCP

server = FastMCP(name="MapsRouter")

@server.tool()
def get_alternative_routes(origin_port: str, destination_port: str) -> str:
    """
    Suggest 2-3 alternative shipping routes between two ports when the
    primary route is disrupted.

    Args:
        origin_port:      Current port of origin (e.g. "Shanghai").
        destination_port: Final destination port (e.g. "Los Angeles").

    Returns:
        JSON with alternative routes, extra transit days, cost impact, and risk.
    """
    api_key = os.environ.get("SERPAPI_API_KEY")
    if api_key:
        return _serpapi_route(origin_port, destination_port, api_key)
    return _simulated_routes(origin_port, destination_port)


@server.tool()
def estimate_delay_impact(shipment_id: str, delay_days: int) -> str:
    """
    Estimate business impact of a shipment delay.

    Args:
        shipment_id: ID of the delayed shipment (e.g. "SH-001").
        delay_days:  Expected delay in calendar days.
    """
    if delay_days <= 2:
        urgency, impact = "LOW", "Minimal — within safety buffer"
    elif delay_days <= 5:
        urgency, impact = "MEDIUM", "Moderate — may affect production schedule"
    elif delay_days <= 10:
        urgency, impact = "HIGH", "Significant — production-line disruption likely"
    else:
        urgency, impact = "CRITICAL", "Severe — activate backup supplier immediately"

    return json.dumps(
        {
            "shipment_id": shipment_id,
            "delay_days": delay_days,
            "urgency_level": urgency,
            "impact_assessment": impact,
            "recommended_action": (
                "Activate backup supplier" if delay_days > 5 else "Monitor and prepare contingency"
            ),
        }
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _serpapi_route(origin: str, destination: str, api_key: str) -> str:
    """Fetch directions via SerpAPI's Google Maps Directions engine."""
    try:
        params = urllib.parse.urlencode(
            {
                "engine": "google_maps_directions",
                "start_addr": f"{origin} Port",
                "end_addr": f"{destination} Port",
                "api_key": api_key,
            }
        )
        url = f"https://serpapi.com/search.json?{params}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())

        directions = data.get("directions", [])
        if not directions:
            return _simulated_routes(origin, destination)

        routes = []
        for i, d in enumerate(directions):
            trips = d.get("trips", [])
            route_name = trips[0].get("title", f"Route {i + 1}") if trips else f"Route {i + 1}"
            routes.append(
                {
                    "route": route_name,
                    "distance": d.get("distance", "N/A"),
                    "duration": d.get("duration", "N/A"),
                    "via": d.get("via", ""),
                }
            )
        return json.dumps({"origin": origin, "destination": destination, "routes": routes})
    except Exception:
        return _simulated_routes(origin, destination)


def _simulated_routes(origin: str, destination: str) -> str:
    alternatives = [
        {
            "route": f"{origin} → Singapore Hub → {destination}",
            "extra_transit_days": 4,
            "risk_level": "Low",
            "cost_increase_pct": 12,
            "notes": "Via Singapore transshipment — most reliable alternative",
        },
        {
            "route": f"{origin} → Colombo → Suez Canal → {destination}",
            "extra_transit_days": 7,
            "risk_level": "Medium",
            "cost_increase_pct": 22,
            "notes": "Indian-Ocean route — avoids Pacific disruptions entirely",
        },
        {
            "route": f"{origin} → Busan → Panama Canal → {destination}",
            "extra_transit_days": 5,
            "risk_level": "Low",
            "cost_increase_pct": 18,
            "notes": "Busan transshipment + Panama Canal crossing",
        },
    ]

    return json.dumps(
        {
            "origin": origin,
            "destination": destination,
            "primary_route_status": "DISRUPTED",
            "alternative_routes": alternatives,
            "recommendation": alternatives[0]["route"],
        }
    )


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    server.run(transport="stdio")