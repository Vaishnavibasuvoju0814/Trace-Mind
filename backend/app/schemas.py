from typing import List, Optional
from pydantic import BaseModel


class RunRequest(BaseModel):
    topic: str


class AgentStep(BaseModel):
    agent: str
    label: str
    content: str


class RunResponse(BaseModel):
    topic: str
    steps: List[AgentStep]
    report: str
    review_notes: Optional[str] = None
    revised: bool = False
