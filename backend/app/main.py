import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import RunRequest, RunResponse, AgentStep
from .agents import run_crew

app = FastAPI(title="AgentCrew API", version="0.1.0")

origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/run", response_model=RunResponse)
def run(req: RunRequest):
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic must not be empty")

    if not os.environ.get("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is not set on the server. Copy .env.example to .env and add your key.",
        )

    try:
        state = run_crew(req.topic.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent crew failed: {e}")

    return RunResponse(
        topic=req.topic,
        steps=[AgentStep(**s) for s in state["steps"]],
        report=state["draft"],
        review_notes=state.get("review_notes") or None,
        revised=state.get("revised", False),
    )
