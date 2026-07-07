# Contributing to AgentCrew

Thanks for considering a contribution! This is a young prototype, so there's
plenty of room to shape it.

## Ground rules

- Be kind — see [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).
- Open an issue before starting large changes, so we can align on approach.
- Keep PRs focused: one feature or fix per PR is easier to review and merge.

## Getting set up

Follow the Quickstart in [README.md](./README.md) to get the backend and
frontend running locally.

## Adding a new agent

Agents live in `backend/app/agents.py` as plain functions that take and
return the shared `GraphState` dict. To add one:

1. Write a `your_agent_node(state) -> state` function with a role-specific
   system prompt.
2. Append a step to `state["steps"]` so it shows up in the UI trace.
3. Wire it into the graph in `build_graph()` with `add_node` / `add_edge`.
4. Update the README's architecture diagram.

## Pull requests

- Include a short description of *why*, not just *what*.
- Note any manual testing you did (e.g. "ran a query end-to-end locally").
- Keep commits reasonably scoped; squash noisy WIP commits before opening.

## Reporting bugs / requesting features

Use GitHub issues. For bugs, include: what you ran, what you expected, what
happened instead, and relevant logs (redact your API key!).
