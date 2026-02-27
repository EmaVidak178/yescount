from __future__ import annotations

import html
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import openai
import streamlit as st
from openai import OpenAI

from src.config.settings import ensure_runtime_dirs, load_settings, validate_settings
from src.db.chroma_client import get_client as get_chroma_client
from src.db.chroma_client import get_collection as get_chroma_collection
from src.db.sqlite_client import (
    get_availability,
    get_connection,
    get_events,
    get_participants,
    init_schema,
)
from src.engine.admin_rules import load_preferences
from src.engine.availability import get_group_availability, set_availability
from src.engine.curation import curate_voting_events
from src.engine.recommender import compute_recommendations
from src.engine.voting import (
    cast_vote,
    get_session_interested_participants_by_event,
    get_session_vote_tallies,
)
from src.ingestion.run_ingestion import run_ingestion
from src.rag.llm_chain import generate_event_titles_batch, summarize_events
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
from src.utils.voting_window import get_voting_window


def _format_date_for_ui(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    return str(value)[:10]


def _format_datetime_for_ui(value: Any) -> str:
    """Format date_start for display: 'Mon, Feb 26 at 7:00 PM' or 'Mon, Feb 26'."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.strftime("%a, %b %d at %I:%M %p")
        date_part = s[:10]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime("%a, %b %d")
    except (ValueError, TypeError):
        return s[:16] if len(s) >= 16 else s


def _format_price_for_ui(price_max: Any) -> str:
    """Return price string only when available; no N/A placeholders."""
    if price_max is None:
        return ""
    try:
        p = float(price_max)
        return "Free" if p == 0 else f"${p:.0f}"
    except (TypeError, ValueError):
        return ""


def _parse_event_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _looks_like_recurring_event(event: dict[str, Any]) -> bool:
    text = f"{event.get('title', '')} {event.get('description', '')}".lower()
    recurring_hints = [
        "multiple dates",
        "various dates",
        "select dates",
        "every ",
        "daily",
        "weekly",
        "recurring",
        "runs through",
        "through ",
    ]
    return any(hint in text for hint in recurring_hints)


def _event_image_url(event: dict[str, Any]) -> str | None:
    """Extract image URL from event raw_json if present."""
    raw = event.get("raw_json")
    if raw is None:
        return None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    if not isinstance(raw, dict):
        return None
    for key in ("image_url", "image", "imageUrl", "thumbnail_url", "thumbnail"):
        val = raw.get(key)
        if val and isinstance(val, str) and val.startswith(("http://", "https://")):
            return val
    return None


def _inject_swipe_styles() -> None:
    st.markdown(
        """
        <style>
        .yc-swipe-card {
            border-radius: 14px;
            padding: 1rem 1.25rem;
            margin-bottom: 1rem;
            background: linear-gradient(135deg, rgba(109,40,217,0.06) 0%, rgba(2,132,199,0.06) 100%);
            border: 1px solid rgba(109,40,217,0.25);
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        }
        .yc-swipe-card-img {
            width: 100%;
            height: 140px;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 0.75rem;
            background: linear-gradient(135deg, rgba(109,40,217,0.15) 0%, rgba(219,39,119,0.1) 100%);
        }
        .yc-swipe-card-img img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .yc-swipe-card-body h4 { margin: 0 0 0.4rem 0; font-size: 1.05rem; }
        .yc-swipe-card-body .yc-swipe-meta { font-size: 0.88rem; opacity: 0.9; margin: 0.25rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _event_schedule_label(event: dict[str, Any], *, month_label: str) -> str:
    """Return user-facing schedule text for event cards."""
    raw = event.get("raw_json")
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            raw = {}
    if not isinstance(raw, dict):
        raw = {}
    date_status = str(raw.get("date_status") or "").strip().lower()
    if date_status in {"multiple", "unclear"}:
        return "Multiple dates"

    start_dt = _parse_event_datetime(event.get("date_start"))
    end_dt = _parse_event_datetime(event.get("date_end"))
    if start_dt and end_dt:
        if start_dt.date() == end_dt.date():
            return start_dt.strftime("%b %d, %Y")
        return f"{start_dt.strftime('%b %d')} - {end_dt.strftime('%b %d')}"
    if start_dt:
        return start_dt.strftime("%b %d, %Y")
    if end_dt:
        return end_dt.strftime("%b %d, %Y")
    if _looks_like_recurring_event(event):
        return "Multiple dates"
    return ""


def _inject_landing_styles() -> None:
    st.markdown(
        """
        <style>
        .yc-hero-wrap {
            border-radius: 16px;
            overflow: hidden;
            margin-bottom: 1rem;
            border: 1px solid rgba(255,255,255,0.10);
            background: linear-gradient(135deg, #6d28d9 0%, #db2777 45%, #0284c7 100%);
            color: white;
        }
        .yc-hero-fallback {
            padding: 2rem 1.5rem;
        }
        .yc-hero-title {
            font-size: 2rem;
            font-weight: 800;
            margin: 0;
        }
        .yc-hero-tagline {
            margin-top: 0.35rem;
            font-size: 1.05rem;
            opacity: 0.95;
        }
        .yc-card {
            border: 1px solid rgba(128,128,128,0.35);
            border-radius: 14px;
            padding: 0.85rem;
            margin-bottom: 0.75rem;
            background: rgba(255,255,255,0.02);
        }
        .yc-card h4 {
            margin: 0 0 0.35rem 0;
        }
        .yc-muted {
            font-size: 0.9rem;
            opacity: 0.8;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_landing_hero() -> None:
    hero_path = Path(__file__).resolve().parent / "assets" / "yescount-hero.png"
    _, center, _ = st.columns([1, 2, 1])
    with center:
        st.markdown('<div class="yc-hero-wrap">', unsafe_allow_html=True)
        if hero_path.exists():
            st.image(str(hero_path), use_container_width=True)
        else:
            st.markdown(
                """
                <div class="yc-hero-fallback">
                    <p class="yc-hero-title">YesCount</p>
                    <p class="yc-hero-tagline">Live your social life to the fullest.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)


def _render_top_banner() -> None:
    assets_dir = Path(__file__).resolve().parent / "assets"
    candidates = [
        assets_dir / "yescount-banner.png",
        assets_dir / "yescount_banner.png",
    ]
    banner_path = next((path for path in candidates if path.exists()), None)
    _, center, _ = st.columns([1, 2, 1])
    with center:
        if banner_path is not None:
            st.image(str(banner_path), use_container_width=True)
        else:
            st.markdown(
                """
                <div class="yc-hero-wrap">
                    <div class="yc-hero-fallback">
                        <p class="yc-hero-title">YesCount</p>
                        <p class="yc-hero-tagline">Less texting. More going.</p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _voting_context() -> dict[str, Any]:
    window = get_voting_window(datetime.now(UTC))
    month_label = datetime(window.target_year, window.target_month, 1).strftime("%B %Y")
    return {
        "target_year": window.target_year,
        "target_month": window.target_month,
        "month_label": month_label,
        "deadline_label": window.deadline_label,
        "is_open": window.is_open,
    }


def _event_title(event: dict[str, Any], max_len: int = 60) -> str:
    """Return display title, truncated at word boundary."""
    raw = str(event.get("title", "")).strip()
    if not raw:
        return "NYC event"
    if len(raw) <= max_len:
        return raw
    cut = raw[: max_len + 1].rfind(" ")
    return (raw[:cut] + "...") if cut > max_len // 2 else (raw[:max_len] + "...")


def _inject_mosaic_styles() -> None:
    st.markdown(
        """
        <style>
        [data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] {
            background: linear-gradient(135deg, rgba(109,40,217,0.08) 0%, rgba(2,132,199,0.06) 100%);
            border: 1px solid rgba(109,40,217,0.3);
            border-radius: 12px;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _get_event_display_titles(events: list[dict[str, Any]]) -> dict[int, str]:
    """Fetch LLM-generated titles for events; cache in session_state; fallback to truncated."""
    cache_key = "swipe_display_titles"
    event_ids = tuple(int(e.get("id") or 0) for e in events)
    if cache_key not in st.session_state:
        st.session_state[cache_key] = {}
    cached = st.session_state[cache_key]
    if cached.get("_ids") == event_ids and cached.get("titles"):
        return cached["titles"]
    runtime = get_runtime()
    client = runtime.get("client")
    if client is not None:
        titles = generate_event_titles_batch(client, events)
        if titles:
            st.session_state[cache_key] = {"_ids": event_ids, "titles": titles}
            return titles
    return {}


def _render_event_card(
    event: dict[str, Any],
    *,
    idx: int,
    voting: dict[str, Any],
    selected_ids: list[int],
    display_titles: dict[int, str] | None = None,
) -> None:
    """Render one event card for mosaic (image, title, desc, date, checkbox)."""
    eid = int(event.get("id") or 0)
    title = (display_titles or {}).get(eid) or _event_title(event)
    img_url = _event_image_url(event)
    desc = str(event.get("description", "")).strip()
    if len(desc) > 180:
        cut = desc[:181].rfind(" ")
        desc_snippet = (desc[:cut] + "...") if cut > 90 else (desc[:180] + "...")
    else:
        desc_snippet = desc
    meta_parts: list[str] = []
    schedule_label = _event_schedule_label(event, month_label=voting["month_label"])
    if schedule_label:
        meta_parts.append(f"When: {schedule_label}")
    location = str(event.get("location", "")).strip()
    if location:
        meta_parts.append(f"Where: {location}")
    price_str = _format_price_for_ui(event.get("price_max"))
    if price_str:
        meta_parts.append(f"Price: {price_str}")
    meta_str = " | ".join(meta_parts) if meta_parts else ""
    with st.container(border=True):
        if img_url:
            st.image(img_url, use_container_width=True)
        st.markdown(f"**{idx}. {title}**")
        if desc_snippet:
            st.caption(desc_snippet)
        if meta_str:
            st.write(meta_str)
        if st.checkbox("Interested", key=f"vote_event_{event['id']}"):
            selected_ids.append(int(event["id"]))


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
    _inject_landing_styles()
    _render_landing_hero()
    runtime = get_runtime()
    conn = runtime["conn"]
    voting = _voting_context()
    st.info(f"Now voting for {voting['month_label']}. Deadline: {voting['deadline_label']}.")
    if not voting["is_open"]:
        st.warning("Voting is currently closed. You can still create/join sessions.")
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(
            """
            <div class="yc-card">
                <h4>Lead A Plan For Your Crew</h4>
                <p class="yc-muted">Create a plan, invite your crew, and coordinate in one place.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
            max_end = date_start + timedelta(days=31)
            date_end = st.date_input(
                "Date range end (max 1 month ahead)",
                value=min(date.today() + timedelta(days=7), max_end),
                min_value=date_start,
                max_value=max_end,
            )
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
                prefs = st.session_state.admin_preferences
                start_date = date.fromisoformat(str(prefs["date_range_start"]))
                end_date = date.fromisoformat(str(prefs["date_range_end"]))
                if end_date > (start_date + timedelta(days=31)):
                    st.error("Date range end cannot be more than 1 month after start date.")
                    return
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
        st.markdown(
            """
            <div class="yc-card">
                <h4>Join Your Crew's Plan</h4>
                <p class="yc-muted">Open a shared session and vote on what sounds fun this month.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
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
    if not st.session_state.session_id or st.session_state.participant_id is None:
        st.warning("Create or join a plan first.")
        return
    ingestion = maybe_refresh_events()
    if ingestion and ingestion.get("status") in {"failed", "degraded"}:
        st.warning("Event refresh is degraded. Showing most recent available data.")
    if not get_events(conn):
        seed_sample_events_if_empty(conn)
    voting = _voting_context()
    st.subheader("Select Your Favorites")
    st.info(
        f"**Monthly voting:** {voting['month_label']} | **Deadline:** {voting['deadline_label']}"
    )
    st.caption("Websites-only curation enabled.")
    if not voting["is_open"]:
        st.info("Voting is closed right now. Please come back during the monthly voting window.")
        if st.button("Go to availability"):
            st.session_state.current_view = "calendar"
            st.rerun()
        return

    events = curate_voting_events(
        get_events(conn),
        target_year=voting["target_year"],
        target_month=voting["target_month"],
        websites_only=True,
        top_n=30,
    )
    st.session_state.event_stack = events
    if not events:
        st.info(
            "No curated events are available for this voting month yet. "
            "Try running ingestion again."
        )
        return

    st.markdown(f"### {len(events)}/30: Select Your Favorites!")
    _inject_mosaic_styles()
    display_titles = _get_event_display_titles(events)
    selected_ids: list[int] = []
    with st.form("vote_form"):
        for row_start in range(0, len(events), 3):
            row_events = events[row_start : row_start + 3]
            cols = st.columns(3)
            for col_idx, event in enumerate(row_events):
                with cols[col_idx]:
                    _render_event_card(
                        event,
                        idx=row_start + col_idx + 1,
                        voting=voting,
                        selected_ids=selected_ids,
                        display_titles=display_titles,
                    )
        submitted = st.form_submit_button("Save votes and continue")

    if submitted:
        try:
            event_ids = [int(event["id"]) for event in events]
            for event_id in event_ids:
                cast_vote(
                    conn,
                    st.session_state.session_id,
                    st.session_state.participant_id,
                    event_id,
                    event_id in selected_ids,
                )
            cached_retrieve.clear()
            st.success("Votes saved.")
            st.session_state.current_view = "calendar"
            st.rerun()
        except Exception as exc:
            st.error(f"Vote save failed: {exc}")


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


def _render_calendar_month_grid(
    date_window: list[date],
    existing_available: set[str],
) -> list[tuple[str, str, str]]:
    """Full month grid: 4-5 rows (weeks), 7 cols (days). Green=available, red=unavailable, white=no response."""
    if "calendar_slot_state" not in st.session_state:
        st.session_state.calendar_slot_state = {
            d.isoformat(): "available" if d.isoformat() in existing_available else "no_response"
            for d in date_window
        }
    state = st.session_state.calendar_slot_state
    _inject_calendar_styles()
    weekday_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    header_cols = st.columns(7)
    for i, name in enumerate(weekday_names):
        with header_cols[i]:
            st.markdown(f"**{name}**")
    # Pad first week so day 1 aligns with correct weekday (Mon=0)
    first = date_window[0]
    pad = (first.weekday()) % 7  # Monday=0
    padded: list[date | None] = [None] * pad + list(date_window)
    # Build rows of 7
    selected: list[tuple[str, str, str]] = []
    for row_start in range(0, len(padded), 7):
        row_days = padded[row_start : row_start + 7]
        row_cols = st.columns(7)
        for col_idx, day in enumerate(row_days):
            with row_cols[col_idx]:
                if day is None:
                    st.markdown("")
                    continue
                day_str = day.isoformat()
                current = state.get(day_str, "no_response")
                cycle = {
                    "no_response": "available",
                    "available": "unavailable",
                    "unavailable": "no_response",
                }
                colors = {
                    "no_response": "#f0f0f0",
                    "available": "#22c55e",
                    "unavailable": "#ef4444",
                }
                btn_label = day.strftime("%d")
                if st.button(
                    btn_label,
                    key=f"cal_btn_{day_str}",
                    type="secondary",
                ):
                    state[day_str] = cycle[current]
                    st.rerun()
                st.markdown(
                    f'<div style="width:100%;height:4px;background:{colors[current]};'
                    f'border-radius:2px;margin-top:2px;"></div>',
                    unsafe_allow_html=True,
                )
                if current == "available":
                    selected.append((day_str, "19:00", "22:00"))
    return selected


def _inject_calendar_styles() -> None:
    st.markdown(
        "<style>.stButton > button { min-width: 2.5rem; }</style>",
        unsafe_allow_html=True,
    )


def render_calendar() -> None:
    runtime = get_runtime()
    conn = runtime["conn"]
    st.subheader("Mark Availability")
    participants = get_participants(conn, st.session_state.session_id)
    if not participants:
        st.warning("No participants found.")
        return
    date_window = _date_range_for_session()
    if not date_window:
        st.info("No dates in range.")
        return
    # Load existing availability
    slots = get_availability(conn, st.session_state.session_id)
    existing = {
        row["date"]
        for row in slots
        if int(row.get("participant_id", 0)) == st.session_state.participant_id
    }
    selected = _render_calendar_month_grid(date_window, existing)
    st.caption("Click a date to cycle: No response → Available (green) → Unavailable (red)")
    b_submit, b_results = st.columns(2)
    with b_submit:
        if st.button("Submit availability"):
            set_availability(
                conn,
                st.session_state.session_id,
                st.session_state.participant_id,
                selected,
            )
            if "calendar_slot_state" in st.session_state:
                del st.session_state.calendar_slot_state
            st.success("Availability saved.")
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
    interested_by_event = get_session_interested_participants_by_event(
        conn, st.session_state.session_id
    )
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
        names = interested_by_event.get(int(rec["id"]), [])
        if names:
            badges_html = " ".join(
                f'<span style="display:inline-block;background:#6d28d9;color:white;'
                f'padding:2px 8px;border-radius:12px;margin:2px;font-size:0.85em;">'
                f"{html.escape(n)}</span>"
                for n in names
            )
            st.markdown(
                f'**Interested:** <span style="display:flex;flex-wrap:wrap;gap:4px;'
                f'align-items:center;">{badges_html}</span>',
                unsafe_allow_html=True,
            )
    if group_availability["slots"]:
        top_slots = sorted(
            group_availability["slots"],
            key=lambda slot: slot["overlap_score"],
            reverse=True,
        )[:3]
        st.markdown("### Best dates to gather your crew")
        for slot in top_slots:
            st.write(
                f"{slot['date']} {slot['time_start']}-{slot['time_end']} "
                f"({len(slot['participant_ids'])} participants)"
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
        db_status = str(status.get("dependencies", {}).get("database", "")).lower()
        if "connection is closed" in db_status and not st.session_state.get(
            "_db_reconnect_attempted"
        ):
            st.session_state._db_reconnect_attempted = True
            get_runtime.clear()
            st.rerun()
        st.error("Readiness check failed.")
        st.json(status)
        return
    st.session_state._db_reconnect_attempted = False
    chroma_status = status["dependencies"].get("chroma", "")
    if chroma_status.startswith("degraded"):
        st.warning("Search embeddings are degraded. Core planning features remain available.")
    startup_ingestion = maybe_refresh_events()
    if startup_ingestion and startup_ingestion.get("status") in {"failed", "degraded"}:
        st.warning("Automatic startup ingestion is degraded. Showing most recent available data.")

    if st.query_params.get("session") and st.session_state.current_view == "landing":
        st.session_state.current_view = "welcome"
    _inject_landing_styles()
    _render_top_banner()
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
