# TraceMind 

A small, transparent **multi-agent** system: a Planner, Researcher, Writer, and
Reviewer agent collaborate — via a [LangGraph](https://github.com/langchain-ai/langgraph)
state machine — to turn a one-line topic into a researched, reviewed report.

Built as a prototype for an open-source submission. PRs and issues welcome —
see [CONTRIBUTING.md](./CONTRIBUTING.md).

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

## Architecture

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

## Quickstart

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

## Roadmap / good first issues

- [ ] Stream agent steps to the frontend via SSE instead of one blocking response
- [ ] Swap `duckduckgo-search` for a pluggable search provider interface (Tavily, Bing)
- [ ] Add a `FactChecker` agent node between Writer and Reviewer
- [ ] Persist run history (SQLite) and add a "past runs" view
- [ ] Add automated tests for the graph's routing logic
- [ ] Dockerfile + docker-compose for one-command local setup

## License

MIT — see [LICENSE](./LICENSE).
