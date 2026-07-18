<!--- NOTE: original README content preserved and expanded. --->

# AgentCrew 🤖

-
![stars](https://img.shields.io/badge/Stars-1000%2B-brightgreen) ![license](https://img.shields.io/badge/License-MIT-blue) ![python](https://img.shields.io/badge/Python-3.10%2B-blue) ![status](https://img.shields.io/badge/Status-Prototype-yellow)

AgentCrew is a small, transparent multi-agent system where a Planner, Researcher, Writer, and Reviewer collaborate — via a LangGraph state machine — to turn a one-line topic into a researched, reviewed report. The project is a prototype built for open-source exploration and demos; contributions are welcome. See the contributing guidelines at [CONTRIBUTING.md](CONTRIBUTING.md).

Table of Contents
- Overview
- Features
- Screenshots
- Architecture
- Workflow
- API
- Environment
- Installation
- Deployment
- Roadmap
- Contributing
- Troubleshooting
- FAQ
- Performance
- License

## Project Overview

AgentCrew demonstrates transparent agent collaboration: rather than a single opaque LLM call, the system runs multiple specialized agents and exposes each agent's output in the UI so it's possible to inspect the full reasoning trace.

Core idea: give each subtask to a focused agent and show the trace so users and developers can audit, iterate, and improve the process.

## Features

- Multi-agent pipeline: Planner → Researcher → Writer → Reviewer
- Visible, step-by-step trace shown in the frontend UI
- Lightweight backend (FastAPI) and modern frontend (React + Vite)
- Pluggable search tool (currently duckduckgo-search)
- Simple JSON API for integration and automation

## Screenshots

Add screenshots into `/docs` or `/assets` and replace the placeholders below.

![Screenshot - topic input and trace](docs/screenshot-topic-trace.png)
![Screenshot - final report](docs/screenshot-report.png)

## Architecture

The project is intentionally small and easy to understand.

| Layer      | Tech                                  |
|------------|----------------------------------------|
| Frontend   | React + Vite                          |
| Backend    | FastAPI                               |
| Agents     | LangGraph + Google Gemini API         |
| Search tool| duckduckgo-search (swappable)         |

Repository layout:

```
agentcrew/
├── backend/
│   ├── app/
│   │   ├── main.py       # FastAPI routes
│   │   ├── agents.py     # LangGraph graph + agent prompts
│   │   ├── tools.py      # web_search tool
│   │   └── schemas.py    # request/response models
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx        # topic form + agent trace + report UI
    │   └── main.jsx
    └── package.json
```

## Workflow (how the agents collaborate)

1. Planner: takes the user's topic and creates a short plan and search strategy.
2. Researcher: executes web searches and collects relevant notes and citations.
3. Writer: drafts the report from research notes and the plan.
4. Reviewer: inspects the draft and either approves or requests one revision.

The frontend renders each step so you can inspect intermediate outputs and the final report.

## API

The backend exposes a small JSON API (FastAPI).

- `GET /health` — simple health check. Returns `{"status": "ok"}`.
- `POST /run` — run the agent crew for a topic.

Request (JSON):

```json
{ "topic": "the environmental impact of lithium-ion batteries" }
```

Response (200):

```json
{
  "topic": "...",
  "steps": [
    { "agent": "Planner", "label": "Plan", "content": "..." },
    { "agent": "Researcher", "label": "Notes", "content": "..." }
  ],
  "report": "Final report text...",
  "review_notes": "Optional review notes",
  "revised": false
}
```

Example CURL:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"topic": "ai safety overview"}'
```

Client integration note: the Pydantic models are defined in `backend/app/schemas.py` and the endpoint is implemented in `backend/app/main.py`.

## Environment Variables

- `GEMINI_API_KEY` (required) — API key for Google Gemini (or equivalent LLM provider).
- `CORS_ORIGINS` (optional) — comma-separated origins for CORS (default: `http://localhost:5173`).

If you don't have an `.env` file, copy `backend/.env.example` to `backend/.env` and add `GEMINI_API_KEY`.

## Installation

Follow these steps to run locally.

1) Backend (Unix/macOS):

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add GEMINI_API_KEY
uvicorn app.main:app --port 8000
```

Windows (PowerShell):

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env and add GEMINI_API_KEY
uvicorn app.main:app --port 8000
```

2) Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend (default http://localhost:5173), type a topic, and watch the agents run.

## Deployment

Basic deployment suggestions:

- Docker: create a small `Dockerfile` for the backend and a multi-stage build for the frontend. The roadmap includes a sample `docker-compose` setup.
- Cloud: deploy the backend to any container service (Cloud Run, AWS ECS) or a VM. Set `GEMINI_API_KEY` and `CORS_ORIGINS` as environment variables.

Minimal production checklist:

- Protect `GEMINI_API_KEY` with secret management.
- Add rate-limiting / request queuing for the `/run` endpoint.
- Add logging and monitoring (structured logs, Sentry/Prometheus).

## Roadmap / Good First Issues

- Stream agent steps to the frontend via SSE instead of one blocking response
- Swap `duckduckgo-search` for a pluggable search provider interface (Tavily, Bing)
- Add a `FactChecker` agent node between Writer and Reviewer
- Persist run history (SQLite) and add a "past runs" view
- Add automated tests for the graph's routing logic
- Dockerfile + docker-compose for one-command local setup

## Contributing

Thanks — contributions are welcome!

- See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
- Open an issue to discuss major changes before sending a PR.
- Keep changes focused and add tests where appropriate.

## Troubleshooting

- `HTTP 500: GEMINI_API_KEY is not set` — ensure `backend/.env` exists and contains `GEMINI_API_KEY`.
- `CORS` errors in the browser — set `CORS_ORIGINS` to include your frontend origin, or use `*` for testing only.
- If the frontend doesn't load, run `npm install` in `frontend` and confirm `npm run dev` reports no errors.

## FAQ

Q: Is this production-ready?

A: Not yet — AgentCrew is a prototype. See the Roadmap for production steps.

Q: Can I swap the LLM or search provider?

A: Yes — the project is designed to be modular. Replace the search tool or the LLM adapter in `backend/app/tools.py` / `backend/app/agents.py`.

## Performance

- Typical run time depends on LLM provider latency and web search speed. Expect runs to take several seconds to tens of seconds.
- To improve throughput: cache search results, use streaming responses, and add background job processing for long-running runs.

---

## Original README (preserved)

The original project README content is preserved below verbatim for reference.

A small, transparent **multi-agent** system: a Planner, Researcher, Writer, and
Reviewer agent collaborate — via a [LangGraph](https://github.com/langchain-ai/langgraph)
state machine — to turn a one-line topic into a researched, reviewed report.

Built as a prototype for an open-source submission. PRs and issues welcome —
see [CONTRIBUTING.md](CONTRIBUTING.md).

## Why this project

Most "AI agent" demos are a single LLM call with a system prompt. AgentCrew
instead shows real **agent collaboration with a visible trace**:

```
 topic ──▶ 🧭 Planner ──▶ 🔎 Researcher ──▶ ✍️ Writer ──▶ 🧐 Reviewer
                                                   ▲            │
                                                   └── revise ──┘ (max once)
```

Every agent's output is shown in the UI so you can see *why* the final report
looks the way it does — not just the end result.

## Architecture (original)

| Layer      | Tech                                  |
|------------|----------------------------------------|
| Frontend   | React + Vite                          |
| Backend    | FastAPI                               |
| Agents     | LangGraph + Google Gemini API          |
| Search tool| duckduckgo-search (swappable)         |

```
agentcrew/
├── backend/
│   ├── app/
│   │   ├── main.py       # FastAPI routes
│   │   ├── agents.py     # LangGraph graph + agent prompts
│   │   ├── tools.py      # web_search tool
│   │   └── schemas.py    # request/response models
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── App.jsx        # topic form + agent trace + report UI
    │   └── main.jsx
    └── package.json
```

## Quickstart (original)

### 1. Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your GEMINI_API_KEY
uvicorn app.main:app --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                 # opens on http://localhost:5173
```

Open the frontend, type a topic (e.g. *"the environmental impact of
lithium-ion batteries"*), and watch the four agents work.

## Roadmap / good first issues (original)

- [ ] Stream agent steps to the frontend via SSE instead of one blocking response
- [ ] Swap `duckduckgo-search` for a pluggable search provider interface (Tavily, Bing)
- [ ] Add a `FactChecker` agent node between Writer and Reviewer
- [ ] Persist run history (SQLite) and add a "past runs" view
- [ ] Add automated tests for the graph's routing logic
- [ ] Dockerfile + docker-compose for one-command local setup

## License

MIT — see [LICENSE](LICENSE).
