from __future__ import annotations

from typing import Any

from openai import OpenAI


def summarize_events(client: OpenAI, events: list[dict[str, Any]]) -> str:
    if not events:
        return "No events found."
    prompt = "Summarize these events in 5 concise bullets:\n\n"
    for event in events[:10]:
        prompt += (
            f"- {event.get('title', 'Untitled')} | {event.get('date_start', '')} | "
            f"{event.get('location', '')}\n"
        )
    response = client.responses.create(model="gpt-4.1-mini", input=prompt)
    return response.output_text


def generate_event_card(client: OpenAI, event: dict[str, Any]) -> str:
    prompt = (
        "Write a short friendly event tagline in one sentence:\n"
        f"Title: {event.get('title')}\nDescription: {event.get('description')}"
    )
    response = client.responses.create(model="gpt-4.1-mini", input=prompt)
    return response.output_text.strip()


def generate_event_titles_batch(
    client: OpenAI, events: list[dict[str, Any]], max_len: int = 50
) -> dict[int, str]:
    """Generate catchy display titles for events in one batch call. Returns {event_id: title}."""
    if not events:
        return {}
    lines = []
    for ev in events:
        eid = int(ev.get("id") or 0)
        title = str(ev.get("title") or "")[:200]
        desc = str(ev.get("description") or "")[:300]
        lines.append(f"ID{eid}: {title}\n{desc}")
    prompt = (
        "For each event below, write ONE catchy short title (max 50 chars). "
        "Output format: one line per event, 'ID<id>: <title>'\n\n"
        + "\n---\n".join(lines)
    )
    try:
        response = client.responses.create(model="gpt-4.1-mini", input=prompt)
        out: dict[int, str] = {}
        for line in response.output_text.strip().split("\n"):
            line = line.strip()
            if line.startswith("ID") and ": " in line:
                idx = line.find(": ")
                try:
                    eid = int(line[2:idx])
                    title = line[idx + 2 :].strip()
                    if len(title) > max_len:
                        title = title[: max_len - 3] + "..."
                    out[eid] = title or "NYC event"
                except ValueError:
                    continue
        return out
    except Exception:
        return {}
