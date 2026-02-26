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
