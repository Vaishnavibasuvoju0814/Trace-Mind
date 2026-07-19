"""
Multi-agent research crew built with LangGraph.

Flow:
    planner -> researcher -> writer -> reviewer -> (writer again, once) -> END

Each node calls Gemini with a role-specific system prompt. State is a plain
TypedDict passed between nodes, which keeps the graph easy to read and easy
for contributors to extend with new agents (e.g. a "fact_checker" node).
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict, List, Optional

from google import genai
from google.genai import types
from google.genai.errors import APIError, ServerError
from langgraph.graph import StateGraph, END

from .tools import web_search, format_search_results
from .config import settings

logger = logging.getLogger(__name__)

MODEL = settings.gemini_model
TRANSIENT_HTTP_CODES = frozenset({429, 500, 502, 503, 504})
_client = None


def _get_client():
    """Lazily initialize and return a singleton Gemini client."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


def _is_retryable(exc: Exception) -> bool:
    """Return True if an API exception is transient and worth retrying."""
    if isinstance(exc, ServerError):
        return exc.code in TRANSIENT_HTTP_CODES
    if isinstance(exc, APIError):
        return exc.code in TRANSIENT_HTTP_CODES
    return isinstance(exc, (TimeoutError, ConnectionError, OSError))


def call_llm(system: str, user: str, max_tokens: int = 1200) -> str:
    """Generate a response from the LLM with retry and timeout logic.

    Retries transient failures using exponential backoff. Raises
    RuntimeError if all attempts fail.

    Args:
        system: System prompt defining the agent's role.
        user: User prompt or aggregated context.
        max_tokens: Maximum tokens for the model output.

    Returns:
        The generated text, or an empty string if the model returns no content.

    Raises:
        RuntimeError: If the maximum number of retry attempts is exhausted.
    """
    last_exc = None
    for attempt in range(1, settings.gemini_retry_attempts + 1):
        try:
            logger.info("Gemini request started attempt=%d", attempt)
            executor = ThreadPoolExecutor(max_workers=1)
            try:
                future = executor.submit(
                    _get_client().models.generate_content,
                    model=MODEL,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        max_output_tokens=max_tokens,
                    ),
                )
                resp = future.result(timeout=settings.gemini_request_timeout)
            finally:
                executor.shutdown(wait=False)
            logger.info("Gemini request succeeded attempt=%d", attempt)
            return resp.text or ""
        except Exception as exc:
            last_exc = exc
            logger.error(
                "Gemini request failed attempt=%d error=%s",
                attempt,
                exc,
                exc_info=True,
            )
            if not _is_retryable(exc) or attempt >= settings.gemini_retry_attempts:
                break
            backoff = min(
                settings.gemini_backoff_base * (2 ** (attempt - 1)),
                settings.gemini_backoff_max,
            )
            logger.info("Retrying Gemini request in %.3f seconds", backoff)
            time.sleep(backoff)

    raise RuntimeError(
        f"Gemini API call failed after {settings.gemini_retry_attempts} attempts: {last_exc}"
    )


def _format_note(question: str, content: str) -> str:
    """Format a sub-question result for inclusion in the research summary."""
    return f"Sub-question: {question}\n{content}"


class GraphState(TypedDict):
    """Shared state passed between graph nodes."""

    topic: str
    sub_questions: List[str]
    research_notes: str
    draft: str
    review_notes: str
    approved: bool
    revised: bool
    steps: List[dict]


def planner_node(state: GraphState) -> GraphState:
    """Decompose the topic into 3-4 focused sub-questions for deeper research."""
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
    """Run concurrent web searches for each sub-question and summarize results.

    Deterministic ordering is preserved regardless of completion order.
    Partial failures are logged and included as error notes.
    """
    sub_questions = state.get("sub_questions", [])
    notes: List[str] = []

    if sub_questions:
        logger.info("Starting %d concurrent research task(s)", len(sub_questions))
        ordered_results: List[Optional[str]] = [None] * len(sub_questions)

        with ThreadPoolExecutor(max_workers=min(8, len(sub_questions))) as executor:
            future_to_index = {}
            for index, question in enumerate(sub_questions):
                logger.debug("Submitting search for: %s", question)
                future = executor.submit(web_search, question)
                future_to_index[future] = index

            for future in as_completed(future_to_index):
                index = future_to_index[future]
                question = sub_questions[index]
                try:
                    start = time.perf_counter()
                    results = future.result()
                    duration = time.perf_counter() - start
                    logger.info(
                        "Search completed for '%s' in %.3f seconds (%d results)",
                        question,
                        duration,
                        len(results),
                    )
                    ordered_results[index] = _format_note(
                        question, format_search_results(results)
                    )
                except Exception as exc:
                    logger.error(
                        "Search failed for '%s': %s",
                        question,
                        exc,
                        exc_info=True,
                    )
                    ordered_results[index] = _format_note(
                        question, f"Search failed: {exc}"
                    )

        # All indices are populated; filter Nones only as a safeguard.
        notes = [note for note in ordered_results if note is not None]

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
    """Draft or revise the report based on research notes and prior feedback."""
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
    """Critically evaluate the draft and approve or request revisions."""
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
    """Return the next node after review based on approval status.

    Only one revision cycle is allowed to ensure the graph terminates.
    """
    if state["approved"] or state.get("revised"):
        return "end"
    state["revised"] = True
    return "revise"


def build_graph():
    """Construct and compile the LangGraph state graph."""
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
    """Return the compiled graph, initializing it on first access."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_crew(topic: str) -> GraphState:
    """Run the research crew end-to-end for the given topic.

    Args:
        topic: The subject or question to research.

    Returns:
        The final graph state containing the draft, notes, and execution history.
    """
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