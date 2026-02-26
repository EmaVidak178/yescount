from __future__ import annotations

from typing import Any


def generate_invite(
    session_name: str, connector_name: str, session_url: str, top_event: dict[str, Any] | None
) -> str:
    lines = [
        f"{connector_name} invited you to plan: {session_name}",
        f"Join here: {session_url}",
    ]
    if top_event:
        lines.append(
            f"Current top pick: {top_event.get('title', 'TBD')} "
            f"({top_event.get('date_start', 'date TBD')})"
        )
    lines.append("Vote on events and add your availability to finalize the plan.")
    return "\n".join(lines)
