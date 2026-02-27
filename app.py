from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from typing import Any

import openai
import streamlit as st
from openai import OpenAI

from src.config.settings import ensure_runtime_dirs, load_settings, validate_settings
from src.db.chroma_client import get_client as get_chroma_client
from src.db.chroma_client import get_collection as get_chroma_collection
from src.db.sqlite_client import (
    get_connection,
    get_events,
    get_participants,
    init_schema,
)
from src.engine.admin_rules import load_preferences
from src.engine.availability import get_group_availability, set_availability
from src.engine.recommender import compute_recommendations
from src.engine.voting import cast_vote, get_session_vote_tallies
from src.ingestion.run_ingestion import run_ingestion
from src.rag.llm_chain import summarize_events
from src.rag.retriever import retrieve_events
from src.sessions.manager import (
    create_new_session,
    get_session_preview,
    get_session_url,
    is_session_valid,
    join_session,
    lock_session,
)
from src.utils.health import readiness
from src.utils.invite_text import generate_invite

TIME_SLOTS = [("17:00", "19:00"), ("19:00", "21:00"), ("21:00", "23:00")]


def _format_date_for_ui(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)[:10]


@st.cache_resource
def get_runtime() -> dict[str, Any]:
    settings = load_settings()
    ensure_runtime_dirs(settings)
    errors = validate_settings(settings)
    warnings: list[str] = []
    conn: Any | None = None
    try:
        conn = get_connection(settings.sqlite_db_path)
        init_schema(conn)
    except Exception as exc:
        errors.append(f"Database initialization failed: {exc}")

    client: OpenAI | None = None
    chroma_collection = None
    if conn is not None and not errors:
        try:
            client = OpenAI(api_key=settings.openai_api_key, timeout=20.0, max_retries=3)
        except Exception as exc:
            errors.append(f"OpenAI client initialization failed: {exc}")
        try:
            chroma_client = get_chroma_client(settings.chroma_persist_dir)
            chroma_collection = get_chroma_collection(chroma_client)
        except Exception as exc:
            # Chroma is optional for core app usage; expose as degraded dependency instead.
            warnings.append(f"Chroma initialization degraded: {exc}")
    return {
        "settings": settings,
        "conn": conn,
        "client": client,
        "collection": chroma_collection,
        "errors": errors,
        "warnings": warnings,
    }


@st.cache_data(ttl=300)
def cached_retrieve(
    query: str,
    date_start: str | None,
    date_end: str | None,
    price_max: float | None,
    vibe_tags: tuple[str, ...],
) -> list[dict[str, Any]]:
    runtime = get_runtime()
    return retrieve_events(
        conn=runtime["conn"],
        collection=runtime["collection"],
        client=runtime["client"],
        query=query,
        date_start=date_start,
        date_end=date_end,
        price_max=price_max,
        vibe_tags=list(vibe_tags),
    )


def init_state() -> None:
    defaults = {
        "current_view": "landing",
        "session_id": None,
        "session_name": "",
        "connector_name": "",
        "participant_name": "",
        "participant_id": None,
        "event_stack": [],
        "swipe_index": 0,
        "calendar_week_offset": 0,
        "admin_preferences": {
            "budget_cap": 50.0,
            "vibe_tags": [],
            "min_attendees": 2,
            "blackout_dates": [],
            "date_range_start": None,
            "date_range_end": None,
        },
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def title_and_breadcrumb() -> None:
    st.title("YesCount")
    mapping = {
        "landing": "Landing",
        "welcome": "Welcome",
        "swipe": "Swipe",
        "calendar": "Availability",
        "results": "Results",
    }
    st.caption(
        f"Flow: Landing > Swipe > Availability > Results | Current: {mapping[st.session_state.current_view]}"
    )


def seed_sample_events_if_empty(conn: Any) -> None:
    if get_events(conn):
        return
    sample = [
        {
            "title": "Rooftop Jazz Night",
            "description": "Live jazz with skyline views.",
            "date_start": (datetime.now(UTC) + timedelta(days=2)).isoformat(),
            "date_end": None,
            "location": "Midtown",
            "price_min": 25.0,
            "price_max": 35.0,
            "url": "https://example.com/jazz",
            "source": "scraped",
            "source_id": "sample-1",
            "raw_json": {"sample": True},
            "vibe_tags": ["nightlife", "artsy"],
        },
        {
            "title": "Brooklyn Outdoor Film",
            "description": "Classic films in the park.",
            "date_start": (datetime.now(UTC) + timedelta(days=3)).isoformat(),
            "date_end": None,
            "location": "Brooklyn",
            "price_min": 0.0,
            "price_max": 0.0,
            "url": "https://example.com/film",
            "source": "scraped",
            "source_id": "sample-2",
            "raw_json": {"sample": True},
            "vibe_tags": ["outdoor", "artsy"],
        },
    ]
    for event in sample:
        runtime = get_runtime()
        runtime["conn"].execute(
            """
            INSERT OR IGNORE INTO events
            (title, description, date_start, date_end, location, price_min, price_max, url, source, source_id, raw_json, vibe_tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["title"],
                event["description"],
                event["date_start"],
                event["date_end"],
                event["location"],
                event["price_min"],
                event["price_max"],
                event["url"],
                event["source"],
                event["source_id"],
                json.dumps(event["raw_json"]),
                json.dumps(event["vibe_tags"]),
            ),
        )
    runtime["conn"].commit()


def maybe_refresh_events() -> dict[str, Any] | None:
    runtime = get_runtime()
    settings = runtime["settings"]
    if not settings.ingestion_auto_refresh or runtime.get("conn") is None:
        return None
    try:
        return run_ingestion(
            conn=runtime["conn"],
            settings=settings,
            collection=runtime.get("collection"),
            client=runtime.get("client"),
            force=False,
        )
    except Exception as exc:
        return {"status": "failed", "errors": [str(exc)], "events_upserted": 0}


def render_landing() -> None:
    runtime = get_runtime()
    conn = runtime["conn"]
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Create Plan")
        plan_name = st.text_input("Plan Name", key="create_plan_name")
        connector_name = st.text_input("Your Name", key="create_connector_name")
        with st.expander("Admin preferences"):
            budget = st.number_input("Budget cap", min_value=0.0, value=50.0, step=5.0)
            vibes = st.multiselect(
                "Vibe tags",
                ["immersive", "artsy", "outdoor", "nightlife", "family"],
                default=[],
            )
            min_attendees = st.number_input("Minimum attendees", min_value=1, value=2, step=1)
            date_start = st.date_input("Date range start", value=date.today())
            date_end = st.date_input("Date range end", value=date.today() + timedelta(days=7))
            st.session_state.admin_preferences = {
                "budget_cap": float(budget),
                "vibe_tags": vibes,
                "min_attendees": int(min_attendees),
                "blackout_dates": [],
                "date_range_start": str(date_start),
                "date_range_end": str(date_end),
            }
        if st.button("Create Session"):
            if not plan_name.strip() or not connector_name.strip():
                st.error("Plan name and connector name are required.")
            else:
                session_id = create_new_session(
                    conn,
                    name=plan_name.strip(),
                    created_by=connector_name.strip(),
                    admin_preferences=st.session_state.admin_preferences,
                    expiry_days=runtime["settings"].session_expiry_days,
                )
                participant_id = join_session(conn, session_id, connector_name.strip())
                st.session_state.session_id = session_id
                st.session_state.session_name = plan_name.strip()
                st.session_state.connector_name = connector_name.strip()
                st.session_state.participant_name = connector_name.strip()
                st.session_state.participant_id = participant_id
                st.query_params["session"] = session_id
                st.session_state.current_view = "swipe"
                st.rerun()

    with col_b:
        st.subheader("Join Plan")
        session_input = st.text_input("Session URL or ID", key="join_session_input")
        join_name = st.text_input("Your Name", key="join_name")
        if st.button("Join Session"):
            session_id = session_input.split("session=")[-1].strip()
            if not is_session_valid(conn, session_id):
                st.error("Session is invalid or expired.")
            else:
                try:
                    participant_id = join_session(conn, session_id, join_name)
                    preview = get_session_preview(conn, session_id)
                    st.session_state.session_id = session_id
                    st.session_state.session_name = (
                        preview["session"]["name"] if preview else "Session"
                    )
                    st.session_state.participant_name = join_name.strip()
                    st.session_state.participant_id = participant_id
                    st.query_params["session"] = session_id
                    st.session_state.current_view = "swipe"
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))


def render_welcome() -> None:
    runtime = get_runtime()
    conn = runtime["conn"]
    session_id = st.query_params.get("session")
    if not session_id:
        st.session_state.current_view = "landing"
        st.rerun()
    preview = get_session_preview(conn, session_id)
    if not preview:
        st.error("Session not found.")
        return
    st.subheader(f"Join {preview['session']['created_by']}'s {preview['session']['name']}")
    st.write("Participants:", ", ".join(preview["participants"]) or "No participants yet")
    if preview["top_events"]:
        st.write("What's hot:")
        for row in preview["top_events"]:
            st.write(f"- {row['title']} ({row['vote_count']} votes)")
    join_name = st.text_input("Your name", key="welcome_join_name")
    if st.button("Join this session"):
        try:
            participant_id = join_session(conn, session_id, join_name)
            st.session_state.session_id = session_id
            st.session_state.session_name = preview["session"]["name"]
            st.session_state.participant_name = join_name.strip()
            st.session_state.participant_id = participant_id
            st.session_state.current_view = "swipe"
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))


def render_swipe() -> None:
    runtime = get_runtime()
    conn = runtime["conn"]
    ingestion = maybe_refresh_events()
    if ingestion and ingestion.get("status") in {"failed", "degraded"}:
        st.warning("Event refresh is degraded. Showing most recent available data.")
    if not get_events(conn):
        seed_sample_events_if_empty(conn)
    st.subheader("Swipe Events")
    search = st.text_input("Search events", max_chars=500, key="search_query")
    col1, col2, col3 = st.columns(3)
    with col1:
        date_start = str(st.date_input("Start date", value=date.today(), key="filter_start"))
    with col2:
        date_end = str(
            st.date_input("End date", value=date.today() + timedelta(days=14), key="filter_end")
        )
    with col3:
        price_max = st.number_input("Max price", min_value=0.0, value=100.0, step=5.0)
    vibes = st.multiselect(
        "Vibes",
        ["immersive", "artsy", "outdoor", "nightlife", "family"],
        default=[],
    )
    events = cached_retrieve(search, date_start, date_end, float(price_max), tuple(vibes))
    st.session_state.event_stack = events
    if not events:
        st.info("No events found for this search and filter set.")
        return
    idx = min(st.session_state.swipe_index, len(events) - 1)
    event = events[idx]
    st.caption(f"Card {idx + 1} of {len(events)}")
    st.markdown(f"### {event['title']}")
    st.write(event.get("description", ""))
    date_label = _format_date_for_ui(event.get("date_start"))
    st.write(
        f"Date: {date_label} | "
        f"Location: {event.get('location', '')} | "
        f"Price: {event.get('price_min', '?')} - {event.get('price_max', '?')}"
    )
    c_yes, c_skip, c_done = st.columns(3)
    with c_yes:
        if st.button("Yes"):
            try:
                cast_vote(
                    conn,
                    st.session_state.session_id,
                    st.session_state.participant_id,
                    event["id"],
                    True,
                )
                st.session_state.swipe_index = min(
                    st.session_state.swipe_index + 1, len(events) - 1
                )
                cached_retrieve.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"Vote failed: {exc}")
    with c_skip:
        if st.button("Skip"):
            try:
                cast_vote(
                    conn,
                    st.session_state.session_id,
                    st.session_state.participant_id,
                    event["id"],
                    False,
                )
                st.session_state.swipe_index = min(
                    st.session_state.swipe_index + 1, len(events) - 1
                )
                cached_retrieve.clear()
                st.rerun()
            except Exception as exc:
                st.error(f"Vote failed: {exc}")
    with c_done:
        if st.button("Done with Swipe"):
            st.session_state.current_view = "calendar"
            st.rerun()


def _date_range_for_session() -> list[date]:
    prefs = load_preferences(st.session_state.admin_preferences)
    if prefs.date_range_start and prefs.date_range_end:
        start = date.fromisoformat(prefs.date_range_start)
        end = date.fromisoformat(prefs.date_range_end)
    else:
        start = date.today()
        end = date.today() + timedelta(days=13)
    out: list[date] = []
    cur = start
    while cur <= end:
        out.append(cur)
        cur += timedelta(days=1)
    return out


def render_calendar() -> None:
    runtime = get_runtime()
    conn = runtime["conn"]
    st.subheader("Mark Availability")
    participants = get_participants(conn, st.session_state.session_id)
    if not participants:
        st.warning("No participants found.")
        return
    date_window = _date_range_for_session()
    week_start = st.session_state.calendar_week_offset * 7
    week_days = date_window[week_start : week_start + 7]
    if not week_days:
        st.info("No more weeks in date range.")
        return
    selected: list[tuple[str, str, str]] = []
    for day in week_days:
        st.markdown(f"**{day.isoformat()}**")
        cols = st.columns(3)
        for i, (start, end) in enumerate(TIME_SLOTS):
            key = f"slot_{day.isoformat()}_{start}_{end}"
            checked = cols[i].checkbox(f"{start}-{end}", key=key)
            if checked:
                selected.append((day.isoformat(), start, end))
    b_prev, b_submit, b_next, b_results = st.columns(4)
    with b_prev:
        if st.button("Prev week"):
            st.session_state.calendar_week_offset = max(
                0, st.session_state.calendar_week_offset - 1
            )
            st.rerun()
    with b_submit:
        if st.button("Submit availability"):
            set_availability(
                conn,
                st.session_state.session_id,
                st.session_state.participant_id,
                selected,
            )
            st.success("Availability saved.")
    with b_next:
        if st.button("Next week"):
            st.session_state.calendar_week_offset += 1
            st.rerun()
    with b_results:
        if st.button("See results"):
            st.session_state.current_view = "results"
            st.rerun()


def render_results() -> None:
    runtime = get_runtime()
    conn = runtime["conn"]
    st.subheader("Group Results")
    events = get_events(conn)
    tallies = get_session_vote_tallies(conn, st.session_state.session_id)
    group_availability = get_group_availability(conn, st.session_state.session_id)
    overlap_default = max(
        (slot["overlap_score"] for slot in group_availability["slots"]), default=0.0
    )
    overlap_by_event_id = {int(event["id"]): overlap_default for event in events}
    recs = compute_recommendations(
        events=events,
        vote_tallies=tallies,
        overlap_by_event_id=overlap_by_event_id,
        prefs=load_preferences(st.session_state.admin_preferences),
        top_n=5,
    )
    if not recs:
        st.info("No recommendations yet.")
        return
    for idx, rec in enumerate(recs, start=1):
        st.markdown(
            f"**#{idx} {rec['title']}** | score={rec['composite_score']:.2f} | "
            f"overlap={rec['overlap_score']:.2f}"
        )
    session_url = get_session_url(runtime["settings"].base_url, st.session_state.session_id)
    invite = generate_invite(
        st.session_state.session_name or "Plan",
        st.session_state.connector_name or st.session_state.participant_name,
        session_url,
        recs[0],
    )
    st.text_area("Invite text", value=invite, height=120)
    if st.button("Lock session"):
        actor = st.session_state.connector_name or st.session_state.participant_name
        if lock_session(conn, st.session_state.session_id, actor):
            st.success("Session locked.")
        else:
            st.warning("Only the connector can lock an open session.")
    if runtime["client"] is not None and st.button("Summarize recommendations"):
        try:
            summary = summarize_events(runtime["client"], recs)
            st.write(summary)
        except openai.APIError as exc:
            st.error(f"Summary failed: {exc}")


def main() -> None:
    st.set_page_config(
        page_title="YesCount",
        page_icon=":calendar:",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_state()
    runtime = get_runtime()
    if runtime["errors"]:
        st.error("Startup validation failed.")
        for error in runtime["errors"]:
            st.write(f"- {error}")
        return
    for warning in runtime.get("warnings", []):
        st.warning(warning)
    status = readiness(runtime["conn"], runtime.get("collection"))
    if not status["ok"]:
        st.error("Readiness check failed.")
        st.json(status)
        return
    chroma_status = status["dependencies"].get("chroma", "")
    if chroma_status.startswith("degraded"):
        st.warning("Search embeddings are degraded. Core planning features remain available.")
    startup_ingestion = maybe_refresh_events()
    if startup_ingestion and startup_ingestion.get("status") in {"failed", "degraded"}:
        st.warning("Automatic startup ingestion is degraded. Showing most recent available data.")

    if st.query_params.get("session") and st.session_state.current_view == "landing":
        st.session_state.current_view = "welcome"
    title_and_breadcrumb()
    if st.session_state.current_view == "landing":
        render_landing()
    elif st.session_state.current_view == "welcome":
        render_welcome()
    elif st.session_state.current_view == "swipe":
        render_swipe()
    elif st.session_state.current_view == "calendar":
        render_calendar()
    else:
        render_results()


if __name__ == "__main__":
    main()
