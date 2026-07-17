"""
Multi-agent research crew built with LangGraph.

Flow:
    planner -> researcher -> writer -> reviewer -> (writer again, once) -> END

Each node calls Gemini with a role-specific system prompt. State is a plain
TypedDict passed between nodes, which keeps the graph easy to read and easy
for contributors to extend with new agents (e.g. a "fact_checker" node).
"""
import os
from typing import TypedDict, List

from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END

from .tools import web_search, format_search_results

MODEL = os.environ.get("AGENT_MODEL", "gemini-2.5-flash")


def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY must be set to call the Google AI API.")
    return genai.Client(api_key=api_key)


def call_llm(system: str, user: str, max_tokens: int = 1200) -> str:
    client = get_client()
    resp = client.models.generate_content(
        model=MODEL,
        contents=user,
        config=types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )
    return resp.text or ""


class GraphState(TypedDict):
    topic: str
    sub_questions: List[str]
    research_notes: str
    draft: str
    review_notes: str
    approved: bool
    revised: bool
    steps: List[dict]


def planner_node(state: GraphState) -> GraphState:
    system = (
        "You are the Planner agent in a research crew. Break the user's topic "
        "into 3-4 focused sub-questions that, if answered, would let a writer "
        "produce a well-rounded short report. Return ONLY a numbered list, no preamble."
    )
    raw = call_llm(system, state["topic"])
    questions = [
        line.split(".", 1)[-1].strip(" -")
        for line in raw.splitlines()
        if line.strip() and any(c.isalpha() for c in line)
    ][:4]
    state["sub_questions"] = questions or [state["topic"]]
    state["steps"].append(
        {"agent": "planner", "label": "Broke topic into sub-questions", "content": raw}
    )
    return state


def researcher_node(state: GraphState) -> GraphState:
    notes = []
    for q in state["sub_questions"]:
        results = web_search(q)
        notes.append(f"Sub-question: {q}\n{format_search_results(results)}")
    combined = "\n\n".join(notes)

    system = (
        "You are the Researcher agent. You are given raw web search snippets "
        "for several sub-questions. Summarize the key facts relevant to each "
        "sub-question in concise bullet points. Note any sub-question where "
        "the search results were weak or contradictory."
    )
    summary = call_llm(system, combined, max_tokens=1500)
    state["research_notes"] = summary
    state["steps"].append(
        {"agent": "researcher", "label": "Gathered and summarized research", "content": summary}
    )
    return state


def writer_node(state: GraphState) -> GraphState:
    system = (
        "You are the Writer agent. Using the research notes provided, write a "
        "clear, well-structured short report (use markdown headings) answering "
        "the original topic. If review notes are included, revise the previous "
        "draft to address them directly."
    )
    user = f"Topic: {state['topic']}\n\nResearch notes:\n{state['research_notes']}"
    if state.get("review_notes"):
        user += f"\n\nPrevious draft:\n{state['draft']}\n\nReviewer feedback to address:\n{state['review_notes']}"

    draft = call_llm(system, user, max_tokens=1800)
    state["draft"] = draft
    label = "Revised the report based on feedback" if state.get("revised") else "Drafted the report"
    state["steps"].append({"agent": "writer", "label": label, "content": draft})
    return state


def reviewer_node(state: GraphState) -> GraphState:
    system = (
        "You are the Reviewer agent, a critical editor. Check the draft for "
        "factual gaps, unclear structure, or unsupported claims. "
        "Reply with 'APPROVED' on the first line if it is good enough to ship, "
        "otherwise reply with 'REVISE' on the first line followed by specific, "
        "actionable feedback."
    )
    verdict = call_llm(system, state["draft"], max_tokens=600)
    approved = verdict.strip().upper().startswith("APPROVED")
    state["approved"] = approved
    state["review_notes"] = "" if approved else verdict
    state["steps"].append(
        {
            "agent": "reviewer",
            "label": "Approved the report" if approved else "Requested revisions",
            "content": verdict,
        }
    )
    return state


def route_after_review(state: GraphState) -> str:
    # Only allow a single revision cycle so the graph always terminates quickly.
    if state["approved"] or state.get("revised"):
        return "end"
    state["revised"] = True
    return "revise"


def build_graph():
    graph = StateGraph(GraphState)
    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("writer", writer_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "researcher")
    graph.add_edge("researcher", "writer")
    graph.add_edge("writer", "reviewer")
    graph.add_conditional_edges(
        "reviewer", route_after_review, {"revise": "writer", "end": END}
    )
    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_crew(topic: str) -> GraphState:
    initial_state: GraphState = {
        "topic": topic,
        "sub_questions": [],
        "research_notes": "",
        "draft": "",
        "review_notes": "",
        "approved": False,
        "revised": False,
        "steps": [],
    }
    graph = get_graph()
    final_state = graph.invoke(initial_state)
    return final_state
