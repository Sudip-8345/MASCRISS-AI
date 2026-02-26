
![CI](https://github.com/your-username/MASCRISS-AI/actions/workflows/ci.yml/badge.svg)
# MASCRISS-AI
## Required API Keys

MASCRISS-AI uses several APIs for live data. You can run with simulated data, but for best results, add your own keys:

| Variable              | Purpose                | Where to get it                |
|-----------------------|------------------------|--------------------------------|
| OPENROUTER_API_KEY    | LLM (DeepSeek V3)      | https://openrouter.ai/         |
| SERPER_API_KEY        | News (Serper)          | https://serper.dev/            |
| OPENWEATHER_API_KEY   | Weather                | https://openweathermap.org/api |
| SERPAPI_API_KEY       | Maps/routing           | https://serpapi.com/           |
| EMAIL                 | Gmail (auto-mail)      | https://gmail.com/             |
| EMAIL_PASSWORD        | Gmail app password     | Google Account > Security      |

You can enter/update these in the Streamlit sidebar UI. They are also read from `.env`.

**Multi-Agent Supply Chain Risk Intelligence and Surveillance Sentinel AI**

A proactive multi-agent system that monitors global events (news, weather, port activity) and automatically generates crisis mitigation plans for supply chain disruptions. Built with CrewAI and the Model Context Protocol (MCP).


## Problem

Global logistics are volatile. A port strike, typhoon, or canal blockage can cost companies millions. Most supply chain systems are reactive -- they report problems after they happen.

MASCRISS-AI is proactive. It detects weak signals early, maps the impact to your shipments, and generates rerouting plans and supplier emails before the disruption hits.


## How It Works

Three AI agents run in sequence:

1. **Global Sentinel** -- Scans news APIs and weather data for disruption signals (storms, strikes, infrastructure failures). Classifies each threat by location, severity, and time-to-impact.

2. **Inventory Analyst** -- Queries the company shipment database (via MCP stdio server) to identify exactly which shipments, suppliers, and routes are exposed to each threat.

3. **Mitigation Strategist** -- Generates alternative shipping routes (via MCP stdio server) and drafts professional supplier communication emails for every at-risk shipment.

The final output is a complete Crisis Response Report saved to `output/crisis_report.md`.


## Project Structure

```
MASCRISS-AI/
  main.py                          # CLI entry point
  app.py                           # Streamlit dashboard (streaming + auto-mail)
  pyproject.toml                   # Dependencies and build config
  Dockerfile                       # Container build
  src/
    crew.py                        # Agent and task orchestration
    config/
      agents.yaml                  # Agent role, goal, backstory
      tasks.yaml                   # Task descriptions and expected output
    tools/
      news_tool.py                 # News scanning tool (Serper API / simulated)
      weather_tool.py              # Weather alert tool (OpenWeather API / simulated)
    mcp_servers/
      logistics_db_server.py       # SQLite shipment DB exposed via MCP stdio
      maps_server.py               # Route alternatives via MCP stdio (SerpAPI / simulated)
  output/
    crisis_report.md               # Generated crisis response report
```


## Tech Stack

| Layer              | Technology                                      |
|--------------------|--------------------------------------------------|
| Agent Framework    | CrewAI 1.9.x                                    |
| Tool Protocol      | Model Context Protocol (MCP) via FastMCP (stdio) |
| LLM                | DeepSeek V3 via OpenRouter (free tier)           |
| Database           | SQLite (shipments table, seeded automatically)   |
| News API           | Serper (Google News search)                      |
| Weather API        | OpenWeatherMap                                   |
| Maps/Routing API   | SerpAPI (Google Maps Directions)                 |
| Language           | Python 3.10+                                    |
| Container          | Docker                                           |


## Shipments Database Schema

```sql
shipments (
  shipment_id       TEXT PRIMARY KEY,
  supplier_name     TEXT,
  origin_port       TEXT,
  destination_port  TEXT,
  status            TEXT,   -- In Transit / Loading / Delayed
  eta               TEXT
)
```

The database is auto-seeded with 12 sample shipments across Shanghai, Busan, Ho Chi Minh City, Mumbai, Yokohama, Kaohsiung, and Ningbo.


## Setup

### 1. Clone and create virtual environment

```bash
git clone https://github.com/your-username/MASCRISS-AI.git
cd MASCRISS-AI
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### 2. Install dependencies

```bash
pip install -e .
pip install litellm
```

### 3. Configure environment variables

Add your keys in `.env`

```
OPENROUTER_API_KEY=your_openrouter_api_key    # Required (free at openrouter.ai)

SERPER_API_KEY=your_serper_key                 # Optional (live news)
OPENWEATHER_API_KEY=your_openweather_key       # Optional (live weather)
SERPAPI_API_KEY=your_serpapi_key                # Optional (live routing)
```

All external APIs are optional. Without them, the system uses realistic simulated data.

### 4. Run

```bash
python main.py
```

Output is saved to `output/crisis_report.md`.


### Streamlit Dashboard

```bash
streamlit run app.py
```

Features:
- **Streaming output** — watch each agent think in real-time
- **Auto-email** — enter a recipient address in the sidebar; the crisis report is sent automatically via Gmail SMTP after generation
- **Download** — export the report as a `.md` file
- **API key entry** — update your API keys live in the sidebar if agent fails

### Docker

```bash
docker build -t mascriss-ai .
docker run --env-file .env mascriss-ai
```


## Challenges Faced

- **LLM rate limits**: Groq's free tier (6,000 TPM) was too restrictive for multi-agent pipelines where each agent makes several LLM calls. Switched to DeepSeek V3 via OpenRouter which has far more generous free-tier limits.

- **Dependency conflicts**: CrewAI 1.9.x pins `openai~=1.83.0` while the latest `litellm` requires `openai>=2.x`. Required careful version pinning to resolve.

- **MCP server crashes killing the pipeline**: A broken top-level import in any MCP server causes the stdio process to exit immediately. CrewAI's MCP client then fails with a cryptic "cannot access local variable `tools_list`" error instead of a clear message. Learned to keep MCP server files import-safe with no third-party library imports at module level.

- **Async event loop conflicts**: CrewAI internally manages its own event loop during `kickoff()`. MCP stdio connections also need an event loop. CrewAI handles this by spawning a thread with `asyncio.run()`, but this is fragile and version-sensitive.

- **API fallback design**: Every external tool (news, weather, routing) needed a simulated fallback so the full pipeline works end-to-end without any paid API keys during development and demos.
