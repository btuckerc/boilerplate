#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import sqlite3
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

APPLE_EPOCH_OFFSET = 978307200
DEFAULT_OUTPUT_ROOT = "Resources/iMessage Agents"
LONGFORM_LENGTH = 140
PROMPT_GROUP_MIN_LENGTH = 80
URL_RE = re.compile(r"https?://[^\s<>\"]+")
TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "igsh",
    "s",
    "si",
    "t",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}
TIME_MARKER_RE = re.compile(
    r"\b(?:"
    r"\d{1,2}(?::\d{2})?\s*(?:am|pm)"
    r"|tomorrow|tmr|today|tonight|weekend|daily|weekly|monthly"
    r"|monday|tuesday|wednesday|thursday|friday|saturday|sunday"
    r"|later|next week|next month"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WorkstreamRule:
    slug: str
    title: str
    group: str
    description: str
    keywords: tuple[str, ...]
    weak_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class DirectiveRule:
    slug: str
    title: str
    description: str
    keywords: tuple[str, ...]


@dataclass(frozen=True)
class SourceThemeRule:
    slug: str
    title: str
    description: str
    keywords: tuple[str, ...]
    domains: tuple[str, ...] = ()


WORKSTREAM_RULES: tuple[WorkstreamRule, ...] = (
    WorkstreamRule(
        slug="agent-platform-orchestration",
        title="Agent Platform & Orchestration",
        group="Platform",
        description=(
            "Agent behavior, model routing, skills, MCP, subagents, memory, "
            "runtime health, and related operating conventions."
        ),
        keywords=(
            "openclaw",
            "clawdbot",
            "hermes",
            "codex",
            "cursor",
            "claude",
            "opus",
            "gemini",
            "openrouter",
            "subagent",
            "subagents",
            "agent mode",
            "mcp",
            "skill",
            "skills",
            "gateway",
            "manual routing",
            "tool call",
            "tool calls",
            "browser interaction",
            "heartbeat",
            "orchestrator",
        ),
        weak_keywords=(
            "claude",
            "opus",
            "gemini",
            "openrouter",
            "model default",
            "default model",
            "memory optimization",
            "metadata server",
            "coding agent",
            "agent history",
            "observability",
            "docker",
            "127.0.0.1",
            "local address",
            "google/default",
        ),
    ),
    WorkstreamRule(
        slug="imessage-interface-and-ux",
        title="iMessage Interface & UX",
        group="Platform",
        description=(
            "Transport and interaction details specific to the iMessage bridge, "
            "including formatting, code words, and reply style."
        ),
        keywords=(
            "imessage",
            "messages app",
            "plain text",
            "markdown",
            "markdown in imessage",
            "greeting message",
            "code word",
            "self-thread",
            "webui window closed",
            "/new",
        ),
        weak_keywords=(
            "plain text",
            "markdown",
            "emoji",
            "em dashes",
        ),
    ),
    WorkstreamRule(
        slug="credentials-auth-and-vaults",
        title="Credentials, Auth & Vaults",
        group="Access",
        description=(
            "Bitwarden/Vaultwarden, account access, API keys, credentials, "
            "and related authentication flows."
        ),
        keywords=(
            "bitwarden",
            "vaultwarden",
            "recovery code",
            "password management",
            "oauth",
            "api key",
            "credentials",
            "vault work",
            "bw login",
            "client id",
            "client secret",
            "cloudflare tunnel",
            "cloudflare api",
            "cloudflare token",
            "cloudflared",
        ),
        weak_keywords=(
            "google account",
            "google api",
            "password",
            "verification process",
            "access blocked",
        ),
    ),
    WorkstreamRule(
        slug="calendar-and-reminders",
        title="Calendar & Reminders",
        group="Assistant",
        description=(
            "Calendar access, event management, reminders, grocery-list style "
            "task tracking, and related assistant behaviors."
        ),
        keywords=(
            "calendar",
            "google calendar",
            "grocery list",
            "event",
            "calendar integration",
        ),
        weak_keywords=(
            "remind me",
            "reminder",
            "schedule",
        ),
    ),
    WorkstreamRule(
        slug="weather-and-forecasting",
        title="Weather & Forecasting",
        group="Assistant",
        description="Weather requests, forecast quality, and CARROT-style source parity.",
        keywords=("weather", "carrot", "forecast", "snow", "rain"),
    ),
    WorkstreamRule(
        slug="youtube-digest-and-transcripts",
        title="YouTube Digest & Transcripts",
        group="Assistant",
        description=(
            "Monitoring creators, fetching transcripts, and summarizing "
            "new YouTube uploads."
        ),
        keywords=(
            "youtube",
            "transcript",
            "video digest",
            "creators i follow",
        ),
        weak_keywords=("new videos", "video"),
    ),
    WorkstreamRule(
        slug="trivrdy-and-jeopardy",
        title="Trivrdy & Jeopardy",
        group="Project",
        description="Messages related to the Trivrdy Jeopardy training app and its usage.",
        keywords=("trivrdy", "jeopardy"),
    ),
    WorkstreamRule(
        slug="github-and-repo-ops",
        title="GitHub & Repo Ops",
        group="Code",
        description=(
            "Git repositories, commits, repo hygiene, GitHub workflows, and "
            "source-control related requests."
        ),
        keywords=(
            "github",
            "git repo",
            "repository",
            "commit",
            "branch",
            "pull request",
            "git changes",
        ),
        weak_keywords=("repo",),
    ),
)

WORKSTREAMS_BY_SLUG = {rule.slug: rule for rule in WORKSTREAM_RULES}
WORKSTREAM_RULE_LOOKUP = {rule.slug: rule for rule in WORKSTREAM_RULES}

DIRECTIVE_RULES: tuple[DirectiveRule, ...] = (
    DirectiveRule(
        slug="plain-text-imessage",
        title="Plain Text In iMessage",
        description="The user repeatedly insists on plain-text responses in iMessage, with no markdown, emojis, or em dashes unless explicitly requested.",
        keywords=("plain text", "markdown", "emoji", "em dashes", "/new"),
    ),
    DirectiveRule(
        slug="evidence-over-assumptions",
        title="Evidence Over Assumptions",
        description="The user explicitly rejects guesses and asks for proven information, careful research, and defensible claims.",
        keywords=("do not make assumptions", "proven information", "fix this", "do research"),
    ),
    DirectiveRule(
        slug="fresh-docs-and-current-info",
        title="Fresh Docs & Current Info",
        description="When implementation or research depends on external systems, the user expects current documentation and up-to-date information rather than stale recall.",
        keywords=("latest documentation", "latest docs", "latest information", "as of today", "today s date"),
    ),
    DirectiveRule(
        slug="status-and-explicit-reporting",
        title="Status & Explicit Reporting",
        description="The user expects status updates, explicit reports, and confirmation after changes or restarts.",
        keywords=("status update", "what’s the status", "what's the status", "tell me the status", "report back"),
    ),
    DirectiveRule(
        slug="scalable-safe-production-minded",
        title="Scalable, Safe, Production-Minded",
        description="The user repeatedly asks for scalable, repeatable approaches that avoid regressions and respect production constraints.",
        keywords=("in production", "no breaking changes", "scalable and repeatable", "thorough, scalable", "works. we’re in production"),
    ),
    DirectiveRule(
        slug="repo-hygiene-and-commits",
        title="Repo Hygiene & Commits",
        description="The user wants durable git hygiene, commit discipline, and change visibility for the agent system.",
        keywords=("git repo", "git changes be committed", "make a commit", "git changes"),
    ),
    DirectiveRule(
        slug="self-clearing-reminders",
        title="Self-Clearing Reminders",
        description="Reminder-style automations should clean themselves up rather than lingering and retriggering.",
        keywords=("delete itself", "clear that reminder"),
    ),
)

SOURCE_THEME_RULES: tuple[SourceThemeRule, ...] = (
    SourceThemeRule(
        slug="agentic-coding-and-frameworks",
        title="Agentic Coding & Frameworks",
        description="Agent runtimes, coding-agent workflows, skills, MCP patterns, evals, and orchestration ideas.",
        keywords=(
            "agent",
            "agents",
            "claude code",
            "codex",
            "openclaw",
            "skill",
            "skills",
            "mcp",
            "browser use",
            "paperclip",
            "superpowers",
            "pinchbench",
            "open swe",
            "autoresearch",
            "evals",
            "prompt engineering",
        ),
    ),
    SourceThemeRule(
        slug="models-and-infra",
        title="Models & Infra",
        description="Model launches, embeddings, inference infrastructure, GPUs, and related platform capabilities.",
        keywords=(
            "model",
            "models",
            "open source",
            "qwen",
            "embedding",
            "gpu",
            "colab",
            "fireworks",
            "kimi",
            "residual",
            "anthropic",
            "gemini",
            "persona",
            "voicebox",
        ),
    ),
    SourceThemeRule(
        slug="video-voice-and-media",
        title="Video, Voice & Media",
        description="YouTube, video editing, voice systems, transcripts, and media-processing workflows.",
        keywords=(
            "youtube",
            "video",
            "videos",
            "clips",
            "clip",
            "motion design",
            "voice",
            "audio",
            "transcribe",
            "transcript",
            "meeting copilot",
            "captioned",
            "vertical",
        ),
    ),
    SourceThemeRule(
        slug="quant-and-markets",
        title="Quant & Markets",
        description="Trading, quant research, prediction markets, arbitrage, and financial modeling references.",
        keywords=(
            "quant",
            "trading",
            "stock",
            "stocks",
            "option pricing",
            "arbitrage",
            "kalshi",
            "polymarket",
            "prediction market",
            "prediction markets",
            "returns",
            "market",
        ),
    ),
    SourceThemeRule(
        slug="career-and-communication",
        title="Career & Communication",
        description="Career materials, recruiting, networking, communication, and professional positioning.",
        keywords=(
            "linkedin",
            "recruiter",
            "recruiters",
            "cv",
            "resume",
            "job talks",
            "communication",
            "how to speak",
            "reply to your messages",
        ),
        domains=("docs.google.com",),
    ),
    SourceThemeRule(
        slug="books-reading-and-culture",
        title="Books, Reading & Culture",
        description="Books, reading lists, and cultural/media references that do not map to an active build project.",
        keywords=("book", "books", "reading", "paperback", "spider-man", "bookstagram", "novel"),
        domains=("barnesandnoble.com",),
    ),
    SourceThemeRule(
        slug="design-ui-and-frontend",
        title="Design, UI & Frontend",
        description="Frontend implementation, UI treatment, brand details, and visual design ideas.",
        keywords=("css", "ui", "brand", "button", "design", "website", "frontend"),
    ),
)

SOURCE_THEMES_BY_SLUG = {rule.slug: rule for rule in SOURCE_THEME_RULES}


def extract_attributed_body_text(raw_value: Any) -> str | None:
    if raw_value in (None, ""):
        return None
    if isinstance(raw_value, memoryview):
        payload = raw_value.tobytes()
    elif isinstance(raw_value, bytes):
        payload = raw_value
    else:
        return None

    candidates: list[str] = []
    for match in re.finditer(rb"[ -~]{4,}", payload):
        try:
            candidate = match.group(0).decode("utf-8", errors="ignore").strip()
        except Exception:
            continue
        if candidate:
            candidates.append(candidate)

    blacklist = {
        "streamtyped",
        "NSMutableAttributedString",
        "NSAttributedString",
        "NSMutableString",
        "NSString",
        "NSObject",
        "NSDictionary",
        "NSNumber",
    }

    metadata_prefixes = (
        "__k",
        "[",
        "bplist00",
        "DDScannerResult",
        "GMT",
        "NS.",
        "OlsonTimeZone",
        "RMS",
        "U$null",
        "Wversion",
        "X$",
        "Z20",
    )

    def normalize_candidate(value: str) -> str:
        stripped = value.strip()
        if re.match(r"^\+[0-9]{1,2}[A-Za-z]", stripped):
            stripped = re.sub(r"^\+[0-9]{1,2}", "", stripped, count=1)
        elif re.match(r"^\+[A-Z][A-Za-z]", stripped):
            stripped = stripped[2:]
        return stripped

    def is_human_text(value: str) -> bool:
        if not value:
            return False
        if value in blacklist or value.startswith("NS") or value.startswith(metadata_prefixes):
            return False
        if " " in value or value.startswith("- ") or value.endswith(("?", ".", "!", ":")):
            return True
        return False

    normalized = [normalize_candidate(candidate) for candidate in candidates]
    text_run: list[str] = []
    started = False
    for candidate in normalized:
        if is_human_text(candidate):
            text_run.append(candidate)
            started = True
            continue
        if started:
            break
    if not text_run:
        return None
    return "\n".join(text_run)


def apple_ns_to_datetime(ns: int) -> datetime:
    return datetime.fromtimestamp(ns / 1_000_000_000 + APPLE_EPOCH_OFFSET, tz=timezone.utc)


def iso_to_apple_ns(value: str) -> int:
    if value.endswith("Z"):
        dt = datetime.fromisoformat(value[:-1]).replace(tzinfo=timezone.utc)
    else:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    return int((dt.timestamp() - APPLE_EPOCH_OFFSET) * 1_000_000_000)


def open_sqlite_ro(path: Path) -> sqlite3.Connection:
    uri = f"file:{urllib.parse.quote(str(path))}?mode=ro&immutable=1"
    con = sqlite3.connect(uri, uri=True)
    con.row_factory = sqlite3.Row
    return con


def compact_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def redact_sensitive_preview(text: str | None) -> str:
    value = text or ""
    substitutions = (
        (r"(?i)(client secret\b[:\s\"'=]+)([A-Za-z0-9._-]{6,})", r"\1[redacted]"),
        (r"(?i)(client id\b[:\s\"'=]+)([A-Za-z0-9._-]{6,})", r"\1[redacted]"),
        (r"(?i)(client_secret\b[:\s\"'=]+)([A-Za-z0-9._-]{6,})", r"\1[redacted]"),
        (r"(?i)(client_id\b[:\s\"'=]+)([A-Za-z0-9._-]{6,})", r"\1[redacted]"),
        (r"(?i)(api key\b[:\s\"'=]+)([A-Za-z0-9._-]{8,})", r"\1[redacted]"),
        (r"(?i)(api_key\b[:\s\"'=]+)([A-Za-z0-9._-]{8,})", r"\1[redacted]"),
        (r"(?i)(bearer\s+)([A-Za-z0-9._-]{8,})", r"\1[redacted]"),
        (r"\bGOCSPX-[A-Za-z0-9_-]+\b", "GOCSPX-[redacted]"),
        (r"\bAIza[0-9A-Za-z_-]{12,}\b", "AIza[redacted]"),
        (r"\bgh[pousr]_[A-Za-z0-9]{12,}\b", "gh_[redacted]"),
    )
    for pattern, replacement in substitutions:
        value = re.sub(pattern, replacement, value)
    return value


def clean_message_text(text: str | None) -> str:
    return compact_whitespace((text or "").replace("\uFFFC", " ").replace("\uFFFD", " "))


def has_meaningful_text(text: str | None) -> bool:
    return bool(clean_message_text(text))


def contains_temporal_marker(text: str | None) -> bool:
    return bool(TIME_MARKER_RE.search(text or ""))


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def safe_slug(value: str, *, fallback: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"https?://", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return lowered[:80] or fallback


def obsidian_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{obsidian_quote(str(value))}"'


def yaml_lines(data: dict[str, Any]) -> list[str]:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            if not value:
                lines.append(f"{key}: []")
                continue
            lines.append(f"{key}:")
            for item in value:
                if isinstance(item, dict):
                    lines.append("  -")
                    for sub_key, sub_value in item.items():
                        lines.append(f"    {sub_key}: {yaml_scalar(sub_value)}")
                else:
                    lines.append(f"  - {yaml_scalar(item)}")
            continue
        lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return lines


def extract_urls(text: str | None) -> list[str]:
    if not text:
        return []
    seen: set[str] = set()
    results: list[str] = []
    for match in URL_RE.findall(text):
        url = match.rstrip(".,);]")
        if url not in seen:
            seen.add(url)
            results.append(url)
    return results


def strip_urls(text: str | None) -> str:
    if not text:
        return ""
    return compact_whitespace(URL_RE.sub(" ", text))


def uid_index(value: Any) -> int | None:
    if isinstance(value, plistlib.UID):
        return value.data
    return None


def resolve_nskeyed_value(objects: list[Any], value: Any, memo: dict[int, Any]) -> Any:
    index = uid_index(value)
    if index is not None:
        if index in memo:
            return memo[index]
        resolved = resolve_nskeyed_value(objects, objects[index], memo)
        memo[index] = resolved
        return resolved
    if isinstance(value, list):
        return [resolve_nskeyed_value(objects, item, memo) for item in value]
    if isinstance(value, dict):
        cleaned = {key: resolve_nskeyed_value(objects, item, memo) for key, item in value.items() if key != "$class"}
        if "NS.relative" in cleaned:
            relative = cleaned.get("NS.relative")
            base = cleaned.get("NS.base")
            if isinstance(relative, str) and isinstance(base, str):
                return urllib.parse.urljoin(base, relative)
            if isinstance(relative, str):
                return relative
        if "NS.objects" in cleaned and isinstance(cleaned["NS.objects"], list):
            return cleaned["NS.objects"]
        return cleaned
    return value


def extract_rich_link_metadata(payload: bytes | None) -> dict[str, Any] | None:
    if not payload:
        return None
    try:
        archive = plistlib.loads(payload)
    except Exception:
        return None
    objects = archive.get("$objects")
    top = archive.get("$top", {}).get("root")
    if not isinstance(objects, list) or top is None:
        return None

    root = resolve_nskeyed_value(objects, top, {})
    if not isinstance(root, dict):
        return None
    metadata = root.get("richLinkMetadata")
    if not isinstance(metadata, dict):
        return None

    link = {
        "canonical_url": metadata.get("URL"),
        "original_url": metadata.get("originalURL"),
        "title": compact_whitespace(str(metadata.get("title") or "")) or None,
        "summary": compact_whitespace(str(metadata.get("summary") or "")) or None,
        "site_name": compact_whitespace(str(metadata.get("siteName") or "")) or None,
        "item_type": compact_whitespace(str(metadata.get("itemType") or "")) or None,
        "icon_url": metadata.get("icon", {}).get("URL") if isinstance(metadata.get("icon"), dict) else None,
        "image_url": metadata.get("image", {}).get("URL") if isinstance(metadata.get("image"), dict) else None,
    }
    if not any(link.get(key) for key in ("canonical_url", "original_url", "title", "summary", "site_name")):
        return None
    return link


def rich_link_text(rich_link: dict[str, Any] | None) -> str:
    if not rich_link:
        return ""
    parts = [
        rich_link.get("site_name"),
        rich_link.get("title"),
        rich_link.get("summary"),
        rich_link.get("canonical_url"),
        rich_link.get("original_url"),
    ]
    return " ".join(str(part) for part in parts if part)


def source_heading_from_rich_link(rich_link: dict[str, Any] | None) -> str:
    if not rich_link:
        return ""
    site_name = compact_whitespace(redact_sensitive_preview(str(rich_link.get("site_name") or "")))
    title = clean_source_preview_text(
        redact_sensitive_preview(str(rich_link.get("title") or "")),
        site_name=site_name,
    )
    summary = clean_source_preview_text(
        redact_sensitive_preview(str(rich_link.get("summary") or "")),
        site_name=site_name,
    )
    if site_name in {"X (formerly Twitter)", "Instagram"} and summary:
        return summary
    if title:
        return title
    if summary:
        return summary
    if site_name:
        return site_name
    return ""


def is_source_candidate(message: dict[str, Any]) -> bool:
    if message.get("rich_link"):
        return True
    if not message.get("urls"):
        return False
    return not strip_urls(message.get("text"))


def message_has_non_preview_attachment(message: dict[str, Any]) -> bool:
    return any(attachment.get("kind") != "share-preview" for attachment in message.get("attachments") or [])


def category_for_text(text: str, urls: list[str], attachments: list[dict[str, Any]]) -> str:
    lowered = text.lower()
    if urls:
        domain = urllib.parse.urlparse(urls[0]).netloc.lower()
        domain = domain.removeprefix("www.")
        if domain in {"x.com", "twitter.com"}:
            return "Links/X"
        if domain == "instagram.com":
            return "Links/Instagram"
        if domain in {"youtube.com", "youtu.be"}:
            return "Links/YouTube"
        if domain == "barnesandnoble.com":
            return "Links/Books"
        return f"Links/{domain}"
    if "remind me" in lowered or "reminder" in lowered:
        return "Requests/Reminders"
    if any(token in lowered for token in ("movie tickets", "fandango", "showtimes", "best seats")):
        return "Requests/Movie Tickets"
    if any(token in lowered for token in ("weather", "calendar", "what time is it")):
        return "Requests/Personal Assistant"
    if len(text) >= LONGFORM_LENGTH:
        return "Ideas/Longform"
    if attachments:
        return "Attachments/Shared"
    return "Requests/Misc"


def title_for_item(
    timestamp_local: str,
    text: str,
    urls: list[str],
    rowid: int,
    *,
    rich_link: dict[str, Any] | None = None,
) -> str:
    context = compact_whitespace(redact_sensitive_preview(strip_urls(text)))[:48]
    if context:
        return f"{timestamp_local[:10]} {context} {rowid}"
    rich_heading = compact_whitespace(source_heading_from_rich_link(rich_link))[:48]
    if rich_heading:
        return f"{timestamp_local[:10]} {rich_heading} {rowid}"
    if urls:
        parsed = urllib.parse.urlparse(urls[0])
        domain = parsed.netloc.removeprefix("www.")
        tail = parsed.path.strip("/").split("/")[-1] or "link"
        return f"{timestamp_local[:10]} {domain} {tail} {rowid}"
    preview = compact_whitespace(redact_sensitive_preview(text))[:48]
    preview = preview if preview else "message"
    return f"{timestamp_local[:10]} {preview} {rowid}"


def canonicalize_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    if path != "/":
        path = path.rstrip("/")

    query_items = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered: list[tuple[str, str]] = []
    for key, value in query_items:
        lowered = key.lower()
        if netloc in {"x.com", "twitter.com"}:
            continue
        if lowered in TRACKING_QUERY_KEYS:
            continue
        if netloc == "instagram.com" and lowered == "igsh":
            continue
        if netloc in {"youtube.com", "m.youtube.com"} and lowered not in {"v", "list"}:
            continue
        filtered.append((key, value))

    query = urllib.parse.urlencode(filtered, doseq=True)
    rebuilt = urllib.parse.urlunparse((scheme, netloc, path, "", query, ""))
    return rebuilt.rstrip("/") if rebuilt.endswith("/") and path != "/" else rebuilt


def domain_for_url(url: str) -> str:
    return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")


def phrase_present(haystack: str, phrase: str) -> bool:
    escaped = re.escape(phrase.lower())
    return re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", haystack) is not None


def clean_source_preview_text(text: str | None, *, site_name: str = "") -> str:
    value = compact_whitespace(text or "")
    if not value:
        return ""
    if site_name == "Instagram":
        cleaned = re.sub(
            r"^\d[\d,\.KMB]*\s+\w+(?:,\s*\d[\d,\.KMB]*\s+\w+)?\s*(?:-|:)\s*",
            "",
            value,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(
            r"^[^:]+ on [A-Za-z]+ \d{1,2}, \d{4}:\s*",
            "",
            cleaned,
        )
        cleaned = compact_whitespace(cleaned).strip(" \"'“”")
        cleaned = re.sub(r"[\"'“”]\.?$", "", cleaned).strip()
        if cleaned:
            return cleaned
    return value


def score_keyword_hits(haystack: str, keywords: tuple[str, ...], weak_keywords: tuple[str, ...] = ()) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    for keyword in keywords:
        if phrase_present(haystack, keyword):
            score += 2
            reasons.append(keyword)
    for keyword in weak_keywords:
        if phrase_present(haystack, keyword):
            score += 1
            reasons.append(keyword)
    return score, sorted(set(reasons))


def score_workstream_rule(
    haystack: str,
    rule: WorkstreamRule,
    *,
    for_source: bool = False,
    domain: str = "",
) -> tuple[int, list[str]]:
    score, reasons = score_keyword_hits(haystack, rule.keywords, rule.weak_keywords)
    weather_present = any(
        phrase_present(haystack, keyword)
        for keyword in WORKSTREAM_RULE_LOOKUP["weather-and-forecasting"].keywords
    )

    if rule.slug == "calendar-and-reminders":
        direct_calendar = any(
            phrase_present(haystack, keyword)
            for keyword in ("calendar", "google calendar", "calendar integration", "grocery list", "event")
        )
        reminder_action = any(
            phrase_present(haystack, keyword)
            for keyword in ("delete itself", "clear that reminder", "move my", "set a reminder")
        )
        if phrase_present(haystack, "remind me") and (contains_temporal_marker(haystack) or reminder_action):
            score = max(score, 2)
            reasons.append("temporal reminder")
        if phrase_present(haystack, "reminder") and (contains_temporal_marker(haystack) or reminder_action):
            score = max(score, 2)
            reasons.append("reminder workflow")
        if (
            phrase_present(haystack, "schedule")
            and contains_temporal_marker(haystack)
            and not weather_present
            and not any(phrase_present(haystack, keyword) for keyword in ("youtube", "video", "clips"))
        ):
            score = max(score, 2)
            reasons.append("scheduled task")
        if for_source and not direct_calendar:
            return 0, []

    if rule.slug == "github-and-repo-ops" and for_source and domain == "github.com":
        score += 2
        reasons.append("github.com")

    return score, sorted(set(reasons))


def source_matching_text(source: dict[str, Any]) -> str:
    parts = [
        source.get("site_name"),
        source.get("label_preview"),
        source.get("summary_preview"),
        *source.get("context_previews", [])[:3],
    ]
    return " ".join(str(part) for part in parts if part).lower()


def detect_source_themes(source: dict[str, Any]) -> list[dict[str, Any]]:
    haystack = source_matching_text(source)
    domain = source.get("domain") or ""
    matches: list[dict[str, Any]] = []
    for rule in SOURCE_THEME_RULES:
        score, reasons = score_keyword_hits(haystack, rule.keywords)
        if domain in rule.domains:
            score += 2
            reasons.append(domain)
        if score >= 2:
            matches.append(
                {
                    "slug": rule.slug,
                    "title": rule.title,
                    "description": rule.description,
                    "reasons": sorted(set(reasons)),
                    "score": score,
                }
            )
    matches.sort(key=lambda entry: (-entry["score"], entry["title"]))
    return matches


def message_sort_key(message: dict[str, Any]) -> tuple[str, int]:
    return (message["timestamp_utc"], message["rowid"])


def message_preview(text: str | None, limit: int = 120) -> str:
    cleaned = compact_whitespace(redact_sensitive_preview(text or ""))
    return cleaned[:limit] if cleaned else "No recovered plain-text body"


def prompt_fingerprint(text: str) -> str:
    lowered = strip_urls(text).lower()
    lowered = re.sub(r"[\"'`“”‘’]", "", lowered)
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return compact_whitespace(lowered)


def attachment_kind(attachment: dict[str, Any]) -> str:
    filename = str(attachment.get("filename") or "")
    transfer_name = str(attachment.get("transfer_name") or "")
    combined = f"{filename} {transfer_name}".lower()
    if "pluginpayloadattachment" in combined:
        return "share-preview"
    mime_type = str(attachment.get("mime_type") or "").lower()
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("audio/"):
        return "audio"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type:
        return mime_type
    return "unknown"


def source_note_relpath(canonical_url: str) -> Path:
    parsed = urllib.parse.urlparse(canonical_url)
    domain = safe_slug(parsed.netloc.removeprefix("www."), fallback="source")
    tail = parsed.path.strip("/") or parsed.query or parsed.netloc
    digest = hashlib.sha1(canonical_url.encode("utf-8")).hexdigest()[:8]
    slug = safe_slug(tail, fallback="link")
    return Path("Corpus") / "Sources" / domain / f"{slug[:60]}-{digest}.md"


def source_title(source: dict[str, Any]) -> str:
    metadata = source.get("metadata") or {}
    rich_heading = compact_whitespace(source_heading_from_rich_link(metadata))
    if rich_heading:
        return f"{source['messages'][0]['timestamp_local'][:10]} {rich_heading[:72]}"
    for message in source["messages"]:
        context = redact_sensitive_preview(strip_urls(message["text"]))
        if context:
            return f"{message['timestamp_local'][:10]} {context[:72]}"
    parsed = urllib.parse.urlparse(source["canonical_url"])
    domain = parsed.netloc.removeprefix("www.")
    tail = parsed.path.strip("/").split("/")[-1] or "link"
    first = source["messages"][0]
    return f"{first['timestamp_local'][:10]} {domain} {tail}"


def message_link(message: dict[str, Any]) -> str:
    preview = message.get("content_preview") or message_preview(message["text"], limit=110)
    return (
        f"[[{message['note_path']}|{message['timestamp_local'][:16]} {message['title']}]] "
        f"| `{message['primary_agent']}` | `{message['confidence']}` | {preview}"
    )


def parse_since_value(raw: str) -> datetime:
    value = raw.strip()
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise SystemExit(f"Invalid --since value: {raw!r}") from exc
    if parsed.tzinfo is None:
        local_tz = datetime.now().astimezone().tzinfo or timezone.utc
        parsed = parsed.replace(tzinfo=local_tz)
    return parsed.astimezone(timezone.utc)


def normalize_message_record(message: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(message)
    normalized.setdefault("urls", [])
    normalized.setdefault("attachments", [])
    normalized.setdefault("signals", [])
    normalized.setdefault("evidence", [])
    normalized.setdefault("agents_seen", [])
    normalized.setdefault("rich_link", None)
    normalized.setdefault("thread_link", None)
    normalized.setdefault("content_preview", message_preview(normalized.get("text")))
    normalized.setdefault("is_link_share", False)
    normalized.setdefault("balloon_bundle_id", None)
    normalized.setdefault("note_path", "")
    normalized.setdefault("source_keys", [])
    normalized.setdefault("source_note_paths", [])
    normalized.setdefault("workstreams", [])
    normalized.setdefault("workstream_titles", [])
    normalized.setdefault("workstream_matches", [])
    normalized.setdefault("directives", [])
    normalized.setdefault("directive_matches", [])
    normalized.setdefault("workstream_note_paths", [])
    normalized.setdefault("is_longform", False)
    normalized.setdefault("is_substantive", False)
    normalized.setdefault("is_source_message", False)
    normalized.setdefault("has_non_preview_attachment", False)
    normalized.setdefault("is_opaque_media", False)
    return normalized


@dataclass
class Signal:
    agent: str
    kind: str
    source: str
    timestamp_utc: str | None = None
    detail: str | None = None
    payload_text: str | None = None


@dataclass
class MessageItem:
    rowid: int
    guid: str
    chat_rowid: int
    chat_guid: str
    chat_identifier: str | None
    sender_id: str | None
    date_ns: int
    is_from_me: int
    text_db: str | None
    text_attr: str | None
    subject: str | None
    balloon_bundle_id: str | None = None
    rich_link: dict[str, Any] | None = None
    attachments: list[dict[str, Any]] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)

    @property
    def dt_utc(self) -> datetime:
        return apple_ns_to_datetime(self.date_ns)

    @property
    def timestamp_utc(self) -> str:
        return self.dt_utc.isoformat().replace("+00:00", "Z")

    @property
    def timestamp_local(self) -> str:
        return self.dt_utc.astimezone().isoformat()

    @property
    def resolved_text(self) -> str:
        for value in (self.text_db, self.text_attr, self.subject):
            if value:
                return value.strip()
        for signal in self.signals:
            if signal.payload_text:
                return signal.payload_text.strip()
        return ""


class Importer:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.chat_db = Path(args.chat_db).expanduser()
        self.vault_root = Path(args.vault_root).expanduser()
        self.output_root = self.vault_root / args.output_root
        self.openclaw_root = Path(args.openclaw_root).expanduser()
        self.hermes_root = Path(args.hermes_root).expanduser()
        self.messages = open_sqlite_ro(self.chat_db)
        self.message_items: dict[int, MessageItem] = {}
        self.target_chat_ids: set[int] = set()
        self.sender_ids: set[str] = set()
        self.openclaw_delivery_reply_rows: set[int] = set()
        self.openclaw_cutoff_ns: int | None = None
        self.hermes_cutoff_ns: int | None = None
        self.write_counts: Counter[str] = Counter()

    def resolve_window_start(self) -> datetime | None:
        if self.args.full_history:
            return None
        if self.args.since:
            return parse_since_value(self.args.since)
        local_now = datetime.now().astimezone()
        local_tz = local_now.tzinfo or timezone.utc
        start_date = (local_now - timedelta(days=self.args.lookback_days)).date()
        return datetime.combine(start_date, datetime.min.time(), tzinfo=local_tz).astimezone(timezone.utc)

    def existing_export_path(self) -> Path:
        return self.output_root / "System" / "imsg-agent-export.json"

    def load_existing_messages(self) -> list[dict[str, Any]]:
        export_path = self.existing_export_path()
        if not export_path.exists():
            return []
        try:
            payload = json.loads(export_path.read_text())
        except json.JSONDecodeError:
            return []
        messages = payload.get("messages")
        if not isinstance(messages, list):
            return []
        return [normalize_message_record(message) for message in messages if isinstance(message, dict)]

    def smart_write_text(self, path: Path, content: str) -> None:
        existing = path.read_text() if path.exists() else None
        if existing == content:
            self.write_counts["unchanged"] += 1
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        if existing is None:
            self.write_counts["created"] += 1
        else:
            self.write_counts["updated"] += 1
        self.write_counts["written"] += 1

    def run(self) -> None:
        self.load_sender_ids()
        self.load_messages()
        self.apply_openclaw_artifacts()
        self.apply_hermes_artifacts()
        self.derive_cutoffs()
        window_start = self.resolve_window_start()
        existing_messages = [] if self.args.full_history else self.load_existing_messages()
        dataset = self.build_dataset(window_start_utc=window_start, existing_messages=existing_messages)
        if self.args.dry_run:
            print(json.dumps(dataset["stats"], indent=2))
            return
        self.write_output(dataset)

    def load_sender_ids(self) -> None:
        commands_log = self.openclaw_root / "logs/commands.log"
        if commands_log.exists():
            for raw_line in commands_log.read_text(errors="ignore").splitlines():
                raw_line = raw_line.strip()
                if not raw_line:
                    continue
                try:
                    payload = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if payload.get("source") != "imessage":
                    continue
                sender = str(payload.get("senderId") or "").strip()
                if sender and sender != "unknown":
                    self.sender_ids.add(sender)

        for path in sorted((self.openclaw_root / "workspace/memory").glob("*.md")):
            text = path.read_text(errors="ignore")
            for match in re.findall(r'"sender_id":\s*"([^"]+)"', text):
                if match:
                    self.sender_ids.add(match)

        for path in sorted((self.hermes_root / "sessions").glob("session_*.json")):
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            for message in data.get("messages", []):
                content = message.get("content", "")
                sender_match = re.search(r"- sender: ([^\n]+)", content)
                if sender_match:
                    self.sender_ids.add(sender_match.group(1).strip())

        if not self.sender_ids:
            raise SystemExit("No sender ids were found in OpenClaw or Hermes artifacts.")

    def load_messages(self) -> None:
        sender_list = tuple(sorted(self.sender_ids))
        placeholders = ",".join("?" for _ in sender_list)
        chats = self.messages.execute(
            f"""
            select distinct c.ROWID, c.guid, c.chat_identifier, c.last_addressed_handle
            from chat c
            where c.chat_identifier in ({placeholders})
               or c.last_addressed_handle in ({placeholders})
            """,
            sender_list + sender_list,
        ).fetchall()
        self.target_chat_ids = {int(row["ROWID"]) for row in chats}
        if not self.target_chat_ids:
            raise SystemExit("No target chats matched the recovered sender ids.")

        chat_placeholders = ",".join("?" for _ in self.target_chat_ids)
        rows = self.messages.execute(
            f"""
            select
                m.ROWID as message_rowid,
                m.guid as message_guid,
                cmj.chat_id as chat_rowid,
                c.guid as chat_guid,
                c.chat_identifier as chat_identifier,
                h.id as sender_id,
                coalesce(m.date, 0) as message_date,
                coalesce(m.is_from_me, 0) as is_from_me,
                m.text as text,
                m.subject as subject,
                m.attributedBody as attributed_body,
                m.balloon_bundle_id as balloon_bundle_id,
                m.payload_data as payload_data
            from message m
            join chat_message_join cmj on cmj.message_id = m.ROWID
            join chat c on c.ROWID = cmj.chat_id
            left join handle h on h.ROWID = m.handle_id
            where cmj.chat_id in ({chat_placeholders})
            order by m.date asc, m.ROWID asc
            """,
            tuple(self.target_chat_ids),
        ).fetchall()

        attachment_rows = self.messages.execute(
            f"""
            select
                maj.message_id as message_rowid,
                a.guid as attachment_guid,
                a.filename as filename,
                a.transfer_name as transfer_name,
                a.mime_type as mime_type,
                coalesce(a.total_bytes, 0) as total_bytes
            from message_attachment_join maj
            join attachment a on a.ROWID = maj.attachment_id
            where maj.message_id in (
                select m.ROWID
                from message m
                join chat_message_join cmj on cmj.message_id = m.ROWID
                where cmj.chat_id in ({chat_placeholders})
            )
            order by maj.message_id, a.ROWID
            """,
            tuple(self.target_chat_ids),
        ).fetchall()
        attachment_map: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in attachment_rows:
            attachment_map[int(row["message_rowid"])].append(
                {
                    "guid": row["attachment_guid"],
                    "filename": row["filename"],
                    "transfer_name": row["transfer_name"],
                    "mime_type": row["mime_type"],
                    "total_bytes": int(row["total_bytes"] or 0),
                    "kind": attachment_kind(
                        {
                            "filename": row["filename"],
                            "transfer_name": row["transfer_name"],
                            "mime_type": row["mime_type"],
                        }
                    ),
                }
            )

        for row in rows:
            item = MessageItem(
                rowid=int(row["message_rowid"]),
                guid=str(row["message_guid"]),
                chat_rowid=int(row["chat_rowid"]),
                chat_guid=str(row["chat_guid"]),
                chat_identifier=row["chat_identifier"],
                sender_id=row["sender_id"],
                date_ns=int(row["message_date"] or 0),
                is_from_me=int(row["is_from_me"] or 0),
                text_db=row["text"],
                text_attr=extract_attributed_body_text(row["attributed_body"]),
                subject=row["subject"],
                balloon_bundle_id=row["balloon_bundle_id"],
                rich_link=extract_rich_link_metadata(row["payload_data"]),
                attachments=attachment_map.get(int(row["message_rowid"]), []),
            )
            self.message_items[item.rowid] = item

    def apply_openclaw_artifacts(self) -> None:
        self.apply_openclaw_memory()
        self.apply_openclaw_commands()
        self.apply_openclaw_deliveries()

    def apply_openclaw_memory(self) -> None:
        memory_root = self.openclaw_root / "workspace/memory"
        for path in sorted(memory_root.glob("*.md")):
            text = path.read_text(errors="ignore")
            if "agent:main:imessage:direct:" not in text:
                continue
            for match in re.finditer(
                r'"message_id":\s*"?(?P<rowid>\d+)"?[\s\S]*?"sender_id":\s*"(?P<sender>[^"]+)"(?:[\s\S]*?"timestamp":\s*"(?P<timestamp>[^"]+)")?',
                text,
            ):
                rowid = int(match.group("rowid"))
                item = self.message_items.get(rowid)
                if item is None:
                    continue
                item.signals.append(
                    Signal(
                        agent="openclaw",
                        kind="memory_explicit",
                        source=str(path),
                        timestamp_utc=None,
                        detail=match.group("timestamp"),
                    )
                )

    def apply_openclaw_commands(self) -> None:
        commands_log = self.openclaw_root / "logs/commands.log"
        if not commands_log.exists():
            return
        for raw_line in commands_log.read_text(errors="ignore").splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
            except json.JSONDecodeError:
                continue
            if payload.get("source") != "imessage":
                continue
            ts = str(payload.get("timestamp") or "").strip()
            if not ts:
                continue
            item = self.match_user_message_by_time(ts, max_delta_seconds=120)
            if item is None:
                continue
            item.signals.append(
                Signal(
                    agent="openclaw",
                    kind="command_reset",
                    source=str(commands_log),
                    timestamp_utc=ts,
                    detail=str(payload.get("action") or ""),
                )
            )

    def apply_openclaw_deliveries(self) -> None:
        gateway_log = self.openclaw_root / "logs/gateway.log"
        if not gateway_log.exists():
            return
        pattern = re.compile(r"^(?P<ts>\S+)\s+\[imessage\] delivered reply to imessage:")
        for line in gateway_log.read_text(errors="ignore").splitlines():
            match = pattern.search(line)
            if not match:
                continue
            ts = match.group("ts")
            reply_item = self.match_reply_message_by_time(ts, max_delta_seconds=10)
            if reply_item is None:
                continue
            self.openclaw_delivery_reply_rows.add(reply_item.rowid)
            user_item = self.latest_user_before(reply_item)
            if user_item is None:
                continue
            user_item.signals.append(
                Signal(
                    agent="openclaw",
                    kind="reply_delivery",
                    source=str(gateway_log),
                    timestamp_utc=ts,
                    detail=f"reply_rowid={reply_item.rowid}",
                )
            )

    def apply_hermes_artifacts(self) -> None:
        sessions_root = self.hermes_root / "sessions"
        for path in sorted(sessions_root.glob("session_*.json")):
            try:
                data = json.loads(path.read_text())
            except json.JSONDecodeError:
                continue
            for message in data.get("messages", []):
                if message.get("role") != "user":
                    continue
                content = str(message.get("content") or "")
                if "Message metadata:" not in content or "User message:" not in content:
                    continue
                created_at_match = re.search(r"- created_at: ([^\n]+)", content)
                if not created_at_match:
                    continue
                created_at = created_at_match.group(1).strip()
                user_text = content.split("User message:\n", 1)[1].strip()
                item = self.match_user_message_by_time(created_at, max_delta_seconds=3)
                if item is None:
                    continue
                item.signals.append(
                    Signal(
                        agent="hermes",
                        kind="session_seen",
                        source=str(path),
                        timestamp_utc=created_at,
                        payload_text=user_text,
                    )
                )

    def match_user_message_by_time(self, timestamp_utc: str, *, max_delta_seconds: int) -> MessageItem | None:
        target_ns = iso_to_apple_ns(timestamp_utc)
        candidates = [
            item
            for item in self.message_items.values()
            if item.is_from_me == 0 and abs(item.date_ns - target_ns) <= max_delta_seconds * 1_000_000_000
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (abs(item.date_ns - target_ns), item.rowid))
        return candidates[0]

    def match_reply_message_by_time(self, timestamp_utc: str, *, max_delta_seconds: int) -> MessageItem | None:
        target_ns = iso_to_apple_ns(timestamp_utc)
        candidates = [
            item
            for item in self.message_items.values()
            if item.is_from_me == 1 and abs(item.date_ns - target_ns) <= max_delta_seconds * 1_000_000_000
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (abs(item.date_ns - target_ns), item.rowid))
        return candidates[0]

    def latest_user_before(self, reply_item: MessageItem) -> MessageItem | None:
        candidates = [
            item
            for item in self.message_items.values()
            if item.chat_rowid == reply_item.chat_rowid and item.is_from_me == 0 and item.date_ns < reply_item.date_ns
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item.date_ns, item.rowid))
        return candidates[-1]

    def derive_cutoffs(self) -> None:
        openclaw_reply_dates = [
            self.message_items[rowid].date_ns
            for rowid in self.openclaw_delivery_reply_rows
            if rowid in self.message_items
        ]
        if openclaw_reply_dates:
            self.openclaw_cutoff_ns = max(openclaw_reply_dates)

        hermes_rows = [
            item.date_ns
            for item in self.message_items.values()
            if any(signal.agent == "hermes" for signal in item.signals)
        ]
        if hermes_rows and self.openclaw_cutoff_ns is not None:
            future_rows = [ns for ns in hermes_rows if ns > self.openclaw_cutoff_ns]
            if future_rows:
                self.hermes_cutoff_ns = min(future_rows)
        if self.hermes_cutoff_ns is None and hermes_rows:
            self.hermes_cutoff_ns = min(hermes_rows)

    def classify_item(self, item: MessageItem) -> dict[str, Any]:
        unique_signals: list[Signal] = []
        seen_signal_keys: set[tuple[str, str, str | None, str | None, str | None]] = set()
        for signal in item.signals:
            key = (signal.agent, signal.kind, signal.timestamp_utc, signal.detail, signal.payload_text)
            if key in seen_signal_keys:
                continue
            seen_signal_keys.add(key)
            unique_signals.append(signal)

        openclaw_signals = [signal for signal in unique_signals if signal.agent == "openclaw"]
        hermes_signals = [signal for signal in unique_signals if signal.agent == "hermes"]
        agents_seen: list[str] = []
        if openclaw_signals:
            agents_seen.append("openclaw")
        if hermes_signals:
            agents_seen.append("hermes")

        if openclaw_signals and hermes_signals:
            if self.hermes_cutoff_ns is not None and item.date_ns < self.hermes_cutoff_ns:
                primary_agent = "openclaw"
                confidence = "high"
                attribution_note = "OpenClaw-era message later replayed into Hermes session history."
            else:
                primary_agent = "hermes"
                confidence = "high"
                attribution_note = "Seen in both agent traces."
        elif openclaw_signals:
            primary_agent = "openclaw"
            confidence = "high"
            attribution_note = "Matched directly from OpenClaw runtime artifacts."
        elif hermes_signals:
            if self.hermes_cutoff_ns is not None and item.date_ns >= self.hermes_cutoff_ns:
                primary_agent = "hermes"
                confidence = "high"
                attribution_note = "Matched directly from Hermes iMessage session history."
            else:
                primary_agent = "openclaw"
                confidence = "medium"
                attribution_note = "Seen in Hermes backfill, but timestamp falls in the OpenClaw era."
                if "openclaw" not in agents_seen:
                    agents_seen.insert(0, "openclaw")
        elif self.hermes_cutoff_ns is not None and item.date_ns >= self.hermes_cutoff_ns:
            primary_agent = "hermes"
            confidence = "low"
            attribution_note = "Post-OpenClaw self-thread message without a direct Hermes artifact."
            agents_seen = ["possible-hermes"]
        else:
            primary_agent = "openclaw"
            confidence = "low"
            attribution_note = "Self-thread message in the OpenClaw era without a surviving direct artifact."
            agents_seen = ["possible-openclaw"]

        text = item.resolved_text
        rich_link = item.rich_link
        urls = extract_urls(text)
        for signal in unique_signals:
            urls.extend(extract_urls(signal.payload_text))
        if rich_link:
            for value in (rich_link.get("original_url"), rich_link.get("canonical_url")):
                if isinstance(value, str) and value:
                    urls.append(value)
        urls = list(dict.fromkeys(urls))

        category = category_for_text(text, urls, item.attachments)
        sender = item.sender_id or item.chat_identifier or ""
        thread_link = ""
        if sender:
            thread_link = f"messages://open?addresses={urllib.parse.quote(sender, safe='')}"

        evidence = []
        for signal in unique_signals:
            bit = f"{signal.agent}:{signal.kind}"
            if signal.timestamp_utc:
                bit += f" @ {signal.timestamp_utc}"
            if signal.detail:
                bit += f" ({signal.detail})"
            evidence.append(bit)
        if attribution_note:
            evidence.append(attribution_note)

        title = title_for_item(item.timestamp_local, text, urls, item.rowid, rich_link=rich_link)
        slug = safe_slug(title, fallback=f"message-{item.rowid}")
        preview_base = strip_urls(text) or source_heading_from_rich_link(rich_link) or text

        return {
            "rowid": item.rowid,
            "guid": item.guid,
            "chat_rowid": item.chat_rowid,
            "chat_guid": item.chat_guid,
            "chat_identifier": item.chat_identifier,
            "sender_id": item.sender_id,
            "timestamp_utc": item.timestamp_utc,
            "timestamp_local": item.timestamp_local,
            "primary_agent": primary_agent,
            "agents_seen": agents_seen,
            "confidence": confidence,
            "category": category,
            "text": text,
            "content_preview": message_preview(preview_base, limit=180),
            "urls": urls,
            "attachments": item.attachments,
            "rich_link": rich_link,
            "is_link_share": bool(rich_link),
            "thread_link": thread_link,
            "signals": [
                {
                    "agent": signal.agent,
                    "kind": signal.kind,
                    "source": signal.source,
                    "timestamp_utc": signal.timestamp_utc,
                    "detail": signal.detail,
                }
                for signal in unique_signals
            ],
            "evidence": evidence,
            "title": title,
            "slug": slug,
        }

    def assign_note_paths(self, messages: list[dict[str, Any]]) -> None:
        for message in messages:
            local_dt = datetime.fromisoformat(message["timestamp_local"])
            year = f"{local_dt.year:04d}"
            month = f"{local_dt.month:02d}"
            rel_path = Path("Entries") / year / month / f"{message['slug']}.md"
            message["note_path"] = rel_path.as_posix()

    def ensure_note_paths(self, messages: list[dict[str, Any]]) -> None:
        for message in messages:
            if message.get("note_path"):
                continue
            local_dt = datetime.fromisoformat(message["timestamp_local"])
            year = f"{local_dt.year:04d}"
            month = f"{local_dt.month:02d}"
            rel_path = Path("Entries") / year / month / f"{message['slug']}.md"
            message["note_path"] = rel_path.as_posix()

    def detect_workstreams(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        haystack_parts = [
            message["text"] or "",
            rich_link_text(message.get("rich_link")),
            " ".join(message["urls"]),
            " ".join(str(attachment.get("transfer_name") or "") for attachment in message["attachments"]),
            " ".join(str(attachment.get("filename") or "") for attachment in message["attachments"]),
        ]
        haystack = " ".join(haystack_parts).lower()
        matches: list[dict[str, Any]] = []
        for rule in WORKSTREAM_RULES:
            score, reasons = score_workstream_rule(haystack, rule)
            if score >= 2:
                matches.append(
                    {
                        "slug": rule.slug,
                        "title": rule.title,
                        "group": rule.group,
                        "description": rule.description,
                        "reasons": sorted(set(reasons)),
                        "score": score,
                    }
                )
        return matches

    def detect_source_workstreams(self, source: dict[str, Any]) -> list[dict[str, Any]]:
        haystack = source_matching_text(source)
        matches: list[dict[str, Any]] = []
        for rule in WORKSTREAM_RULES:
            score, reasons = score_workstream_rule(
                haystack,
                rule,
                for_source=True,
                domain=source.get("domain") or "",
            )
            if score >= 2:
                matches.append(
                    {
                        "slug": rule.slug,
                        "title": rule.title,
                        "group": rule.group,
                        "description": rule.description,
                        "reasons": sorted(set(reasons)),
                        "score": score,
                    }
                )
        matches.sort(key=lambda entry: (-entry["score"], entry["title"]))
        return matches

    def detect_directives(self, message: dict[str, Any]) -> list[dict[str, Any]]:
        haystack = " ".join(
            [
                message.get("text") or "",
                strip_urls(message.get("text")),
                message.get("content_preview") or "",
            ]
        ).lower()
        matches: list[dict[str, Any]] = []
        for rule in DIRECTIVE_RULES:
            reasons = [keyword for keyword in rule.keywords if phrase_present(haystack, keyword)]
            if reasons:
                matches.append(
                    {
                        "slug": rule.slug,
                        "title": rule.title,
                        "description": rule.description,
                        "reasons": sorted(set(reasons)),
                    }
                )
        return matches

    def build_corpus(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        workstreams: dict[str, dict[str, Any]] = {}
        for rule in WORKSTREAM_RULES:
            workstreams[rule.slug] = {
                "slug": rule.slug,
                "title": rule.title,
                "group": rule.group,
                "description": rule.description,
                "messages": [],
                "matched_keywords": set(),
                "source_keys": set(),
            }

        directives: dict[str, dict[str, Any]] = {}
        for rule in DIRECTIVE_RULES:
            directives[rule.slug] = {
                "slug": rule.slug,
                "title": rule.title,
                "description": rule.description,
                "messages": [],
                "matched_keywords": set(),
                "note_path": (Path("Corpus") / "Compiled" / "Directives" / f"{rule.slug}.md").as_posix(),
            }

        themes: dict[str, dict[str, Any]] = {}
        for rule in SOURCE_THEME_RULES:
            themes[rule.slug] = {
                "slug": rule.slug,
                "title": rule.title,
                "description": rule.description,
                "sources": [],
                "matched_keywords": set(),
                "note_path": (Path("Corpus") / "Compiled" / "Themes" / f"{rule.slug}.md").as_posix(),
            }

        sources: dict[str, dict[str, Any]] = {}
        longform_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        collections: dict[str, list[dict[str, Any]]] = {
            "source_messages": [],
            "media_messages": [],
            "opaque_media_messages": [],
            "longform_messages": [],
            "unassigned_substantive": [],
            "unassigned_longform": [],
        }

        for message in messages:
            workstream_matches = self.detect_workstreams(message)
            directive_matches = self.detect_directives(message)
            message["workstream_matches"] = workstream_matches
            message["workstreams"] = [match["slug"] for match in workstream_matches]
            message["workstream_titles"] = [match["title"] for match in workstream_matches]
            message["directive_matches"] = directive_matches
            message["directives"] = [match["slug"] for match in directive_matches]

            is_longform = len(message["text"] or "") >= LONGFORM_LENGTH
            is_source_message = is_source_candidate(message)
            has_non_preview_attachment = message_has_non_preview_attachment(message)
            is_opaque_media = has_non_preview_attachment and not has_meaningful_text(strip_urls(message["text"]))
            is_substantive = is_source_message or has_non_preview_attachment or is_longform or bool(workstream_matches)

            message["is_longform"] = is_longform
            message["is_substantive"] = is_substantive
            message["is_source_message"] = is_source_message
            message["has_non_preview_attachment"] = has_non_preview_attachment
            message["is_opaque_media"] = is_opaque_media
            message["source_keys"] = []
            message["source_note_paths"] = []

            if is_source_message:
                collections["source_messages"].append(message)
            if has_non_preview_attachment:
                collections["media_messages"].append(message)
            if is_opaque_media:
                collections["opaque_media_messages"].append(message)
            if is_longform:
                collections["longform_messages"].append(message)
                fingerprint = prompt_fingerprint(message["text"])
                if len(fingerprint) >= PROMPT_GROUP_MIN_LENGTH:
                    longform_groups[fingerprint].append(message)
            if is_substantive and not workstream_matches and not is_source_message and not has_non_preview_attachment:
                collections["unassigned_substantive"].append(message)
            if is_longform and not workstream_matches:
                collections["unassigned_longform"].append(message)

            for match in workstream_matches:
                workstream = workstreams[match["slug"]]
                workstream["messages"].append(message)
                workstream["matched_keywords"].update(match["reasons"])

            for match in directive_matches:
                directive = directives[match["slug"]]
                directive["messages"].append(message)
                directive["matched_keywords"].update(match["reasons"])

            if is_source_message:
                source_urls: list[str] = []
                source_variants: set[str] = set(message["urls"])
                if message.get("rich_link"):
                    primary_rich_url = (
                        message["rich_link"].get("canonical_url")
                        or message["rich_link"].get("original_url")
                    )
                    if isinstance(primary_rich_url, str) and primary_rich_url:
                        source_urls.append(primary_rich_url)
                    for candidate in (
                        message["rich_link"].get("canonical_url"),
                        message["rich_link"].get("original_url"),
                    ):
                        if isinstance(candidate, str) and candidate:
                            source_variants.add(candidate)
                if not source_urls:
                    source_urls.extend(message["urls"])
                seen_canonical_urls: set[str] = set()
                for url in source_urls:
                    if not isinstance(url, str) or not url:
                        continue
                    canonical = canonicalize_url(url)
                    if canonical in seen_canonical_urls:
                        continue
                    seen_canonical_urls.add(canonical)
                    source = sources.setdefault(
                        canonical,
                        {
                            "canonical_url": canonical,
                            "domain": domain_for_url(canonical),
                            "messages": [],
                            "url_variants": set(),
                            "message_workstreams": set(),
                            "directives": set(),
                            "rich_links": [],
                        },
                    )
                    source["messages"].append(message)
                    source["url_variants"].update(source_variants or {url})
                    source["message_workstreams"].update(message["workstreams"])
                    source["directives"].update(message["directives"])
                    if message.get("rich_link"):
                        source["rich_links"].append(message["rich_link"])
                    message["source_keys"].append(canonical)

        for workstream in workstreams.values():
            workstream["messages"].sort(key=message_sort_key)
            workstream["matched_keywords"] = sorted(workstream["matched_keywords"])
            workstream["note_path"] = (Path("Corpus") / "Workstreams" / f"{workstream['slug']}.md").as_posix()
            periods: Counter[str] = Counter()
            for message in workstream["messages"]:
                periods[message["timestamp_local"][:7]] += 1
            workstream["periods"] = dict(sorted(periods.items()))
            workstream["longform_message_count"] = sum(1 for message in workstream["messages"] if message["is_longform"])
            workstream["attachment_message_count"] = sum(
                1 for message in workstream["messages"] if message["has_non_preview_attachment"]
            )
            workstream["source_message_count"] = sum(
                1 for message in workstream["messages"] if message["is_source_message"]
            )

        for directive in directives.values():
            directive["messages"].sort(key=message_sort_key)
            directive["matched_keywords"] = sorted(directive["matched_keywords"])
            periods: Counter[str] = Counter()
            for message in directive["messages"]:
                periods[message["timestamp_local"][:7]] += 1
            directive["periods"] = dict(sorted(periods.items()))

        for canonical, source in sources.items():
            source["messages"].sort(key=message_sort_key)
            source["message_count"] = len(source["messages"])
            source["message_workstreams"] = sorted(source["message_workstreams"])
            source["directives"] = sorted(source["directives"])
            source["url_variants"] = sorted(source["url_variants"])
            source["metadata"] = next(
                (
                    rich_link
                    for rich_link in source["rich_links"]
                    if any(rich_link.get(key) for key in ("title", "summary", "site_name"))
                ),
                None,
            )
            source["site_name"] = (
                compact_whitespace(str(source["metadata"].get("site_name") or ""))
                if isinstance(source.get("metadata"), dict)
                else ""
            ) or source["domain"]
            source["title"] = source_title(source)
            source["note_path"] = source_note_relpath(canonical).as_posix()
            source["first_shared"] = source["messages"][0]["timestamp_local"]
            source["last_shared"] = source["messages"][-1]["timestamp_local"]
            source["context_previews"] = [
                redact_sensitive_preview(strip_urls(message["text"]))
                for message in source["messages"]
                if strip_urls(message["text"])
            ][:5]
            source["summary_preview"] = clean_source_preview_text(
                compact_whitespace(
                    redact_sensitive_preview(
                        str((source["metadata"] or {}).get("summary") or "")
                    )
                ),
                site_name=source["site_name"],
            ) or None
            source["label_preview"] = clean_source_preview_text(
                compact_whitespace(
                    redact_sensitive_preview(
                        str((source["metadata"] or {}).get("title") or "")
                    )
                ),
                site_name=source["site_name"],
            ) or None
            source["content_preview"] = (
                source["summary_preview"]
                or source["label_preview"]
                or (source["context_previews"][0] if source["context_previews"] else None)
                or source["canonical_url"]
            )
            workstream_matches = self.detect_source_workstreams(source)
            source["workstream_matches"] = workstream_matches
            source["workstreams"] = [match["slug"] for match in workstream_matches]
            source["primary_workstream"] = source["workstreams"][0] if source["workstreams"] else None
            theme_matches = detect_source_themes(source)
            source["theme_matches"] = theme_matches
            source["themes"] = [match["slug"] for match in theme_matches]
            source["primary_theme"] = source["themes"][0] if source["themes"] else None

            for slug in source["workstreams"]:
                workstreams[slug]["source_keys"].add(canonical)
            for match in theme_matches:
                theme = themes[match["slug"]]
                theme["sources"].append(source)
                theme["matched_keywords"].update(match["reasons"])

        for workstream in workstreams.values():
            workstream["source_keys"] = sorted(workstream["source_keys"])

        for theme in themes.values():
            theme["sources"].sort(key=lambda entry: (entry["first_shared"], entry["title"]))
            theme["matched_keywords"] = sorted(theme["matched_keywords"])

        for message in messages:
            message["workstream_note_paths"] = [
                workstreams[slug]["note_path"] for slug in message["workstreams"] if slug in workstreams
            ]
            message["source_note_paths"] = [
                sources[key]["note_path"] for key in dict.fromkeys(message["source_keys"]) if key in sources
            ]

        longform_group_entries: list[dict[str, Any]] = []
        for fingerprint, grouped_messages in longform_groups.items():
            grouped_messages.sort(key=message_sort_key)
            workstream_slugs = sorted({slug for message in grouped_messages for slug in message["workstreams"]})
            longform_group_entries.append(
                {
                    "fingerprint": fingerprint,
                    "messages": grouped_messages,
                    "count": len(grouped_messages),
                    "first_seen": grouped_messages[0]["timestamp_local"],
                    "last_seen": grouped_messages[-1]["timestamp_local"],
                    "preview": message_preview(strip_urls(grouped_messages[0]["text"]), limit=180),
                    "workstreams": workstream_slugs,
                }
            )
        longform_group_entries.sort(key=lambda entry: (entry["first_seen"], entry["preview"]))

        return {
            "workstreams": workstreams,
            "directives": directives,
            "themes": themes,
            "sources": sources,
            "longform_groups": longform_group_entries,
            "collections": {
                **collections,
                "research_inbox_sources": [
                    source
                    for source in sorted(
                        sources.values(),
                        key=lambda entry: (entry["first_shared"], entry["title"]),
                    )
                    if not source["workstreams"]
                ],
            },
        }

    def build_dataset(
        self,
        *,
        window_start_utc: datetime | None,
        existing_messages: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        live_user_items = [
            self.classify_item(item)
            for item in sorted(self.message_items.values(), key=lambda item: (item.date_ns, item.rowid))
            if item.is_from_me == 0
            and (window_start_utc is None or item.dt_utc >= window_start_utc)
        ]
        self.assign_note_paths(live_user_items)

        merged_messages: dict[int, dict[str, Any]] = {}
        for message in existing_messages or []:
            rowid = message.get("rowid")
            if isinstance(rowid, int):
                merged_messages[rowid] = normalize_message_record(message)
        existing_rowids = set(merged_messages)
        refreshed_rowids: set[int] = set()
        for message in live_user_items:
            merged_messages[message["rowid"]] = normalize_message_record(message)
            refreshed_rowids.add(message["rowid"])

        reused_existing_count = len(existing_rowids - refreshed_rowids)

        user_items = sorted(merged_messages.values(), key=message_sort_key)
        self.ensure_note_paths(user_items)
        corpus = self.build_corpus(user_items)

        stats = {
            "total_user_messages": len(user_items),
            "live_import_message_count": len(live_user_items),
            "reused_existing_message_count": reused_existing_count,
            "counts_by_primary_agent": Counter(entry["primary_agent"] for entry in user_items),
            "counts_by_confidence": Counter(entry["confidence"] for entry in user_items),
            "counts_by_category": Counter(entry["category"] for entry in user_items),
            "counts_by_workstream": Counter(
                slug
                for entry in user_items
                for slug in entry["workstreams"]
            ),
            "sender_ids": sorted(self.sender_ids),
            "target_chat_ids": sorted(self.target_chat_ids),
            "openclaw_cutoff_utc": apple_ns_to_datetime(self.openclaw_cutoff_ns).isoformat().replace("+00:00", "Z")
            if self.openclaw_cutoff_ns
            else None,
            "hermes_cutoff_utc": apple_ns_to_datetime(self.hermes_cutoff_ns).isoformat().replace("+00:00", "Z")
            if self.hermes_cutoff_ns
            else None,
            "import_mode": "full-history" if window_start_utc is None else "incremental",
            "import_window_start_utc": window_start_utc.isoformat().replace("+00:00", "Z")
            if window_start_utc
            else None,
            "default_lookback_days": self.args.lookback_days,
            "substantive_message_count": sum(1 for entry in user_items if entry["is_substantive"]),
            "longform_message_count": len(corpus["collections"]["longform_messages"]),
            "longform_group_count": len(corpus["longform_groups"]),
            "source_post_count": len(corpus["sources"]),
            "source_message_count": len(corpus["collections"]["source_messages"]),
            "user_media_message_count": len(corpus["collections"]["media_messages"]),
            "opaque_media_message_count": len(corpus["collections"]["opaque_media_messages"]),
            "unassigned_substantive_count": len(corpus["collections"]["unassigned_substantive"]),
            "unassigned_longform_count": len(corpus["collections"]["unassigned_longform"]),
            "research_inbox_source_count": len(corpus["collections"]["research_inbox_sources"]),
            "source_theme_counts": Counter(
                slug
                for source in corpus["sources"].values()
                for slug in source["themes"]
            ),
            "directive_counts": Counter(
                slug
                for entry in user_items
                for slug in entry["directives"]
            ),
        }
        return {"stats": stats, "messages": user_items, "corpus": corpus}

    def write_output(self, dataset: dict[str, Any]) -> None:
        system_root = self.output_root / "System"
        entries_root = self.output_root / "Entries"
        agents_root = self.output_root / "Agents"
        categories_root = self.output_root / "Categories"
        timeline_root = self.output_root / "Timeline"
        corpus_root = self.output_root / "Corpus"
        workstreams_root = corpus_root / "Workstreams"
        sources_root = corpus_root / "Sources"
        collections_root = corpus_root / "Collections"
        compiled_root = corpus_root / "Compiled"
        compiled_directives_root = compiled_root / "Directives"
        compiled_themes_root = compiled_root / "Themes"

        for root in (
            system_root,
            entries_root,
            agents_root,
            categories_root,
            timeline_root,
            corpus_root,
            workstreams_root,
            sources_root,
            collections_root,
            compiled_root,
            compiled_directives_root,
            compiled_themes_root,
        ):
            root.mkdir(parents=True, exist_ok=True)

        export_path = system_root / "imsg-agent-export.json"
        self.write_counts = Counter()
        self.smart_write_text(export_path, json.dumps(dataset, indent=2) + "\n")
        self.smart_write_text(
            system_root / "imsg-corpus-summary.json",
            json.dumps(self.system_corpus_summary(dataset), indent=2) + "\n",
        )

        category_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
        agent_index: dict[str, list[dict[str, Any]]] = defaultdict(list)
        timeline_index: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for message in dataset["messages"]:
            abs_path = self.output_root / message["note_path"]
            self.smart_write_text(abs_path, self.render_message_note(message))
            category_index[message["category"]].append(message)
            agent_index[message["primary_agent"]].append(message)
            timeline_index[message["timestamp_local"][:7]].append(message)

        self.smart_write_text(self.output_root / "_Index.md", self.render_root_index(dataset))

        for category, messages in sorted(category_index.items()):
            out_path = categories_root / f"{safe_slug(category, fallback='category')}.md"
            self.smart_write_text(out_path, self.render_listing_page(f"Category: {category}", messages))

        for agent, messages in sorted(agent_index.items()):
            out_path = agents_root / f"{safe_slug(agent, fallback='agent')}.md"
            self.smart_write_text(out_path, self.render_listing_page(f"Agent: {agent}", messages))

        for period, messages in sorted(timeline_index.items()):
            out_path = timeline_root / f"{period}.md"
            self.smart_write_text(out_path, self.render_listing_page(f"Timeline: {period}", messages))

        self.smart_write_text(corpus_root / "_Overview.md", self.render_corpus_overview(dataset))
        self.smart_write_text(compiled_root / "_Overview.md", self.render_compiled_overview(dataset))
        self.smart_write_text(compiled_root / "project-map.md", self.render_project_map(dataset))
        self.smart_write_text(compiled_root / "standing-directives.md", self.render_standing_directives(dataset))
        self.smart_write_text(compiled_root / "research-themes.md", self.render_research_themes(dataset["corpus"]))
        self.smart_write_text(compiled_root / "research-inbox.md", self.render_research_inbox(dataset["corpus"]))

        for source in sorted(dataset["corpus"]["sources"].values(), key=lambda entry: (entry["first_shared"], entry["title"])):
            source_path = self.output_root / source["note_path"]
            self.smart_write_text(source_path, self.render_source_page(source))

        for directive in sorted(
            (entry for entry in dataset["corpus"]["directives"].values() if entry["messages"]),
            key=lambda entry: entry["title"],
        ):
            directive_path = self.output_root / directive["note_path"]
            self.smart_write_text(directive_path, self.render_directive_page(directive))

        for theme in sorted(
            (entry for entry in dataset["corpus"]["themes"].values() if entry["sources"]),
            key=lambda entry: entry["title"],
        ):
            theme_path = self.output_root / theme["note_path"]
            self.smart_write_text(theme_path, self.render_theme_page(theme))

        for workstream in sorted(
            (entry for entry in dataset["corpus"]["workstreams"].values() if entry["messages"]),
            key=lambda entry: (entry["group"], entry["title"]),
        ):
            out_path = workstreams_root / f"{workstream['slug']}.md"
            self.smart_write_text(out_path, self.render_workstream_page(workstream, dataset["corpus"]))
            monthly_root = workstreams_root / workstream["slug"]
            monthly_root.mkdir(parents=True, exist_ok=True)
            by_period: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for message in workstream["messages"]:
                by_period[message["timestamp_local"][:7]].append(message)
            for period, messages in sorted(by_period.items()):
                self.smart_write_text(
                    monthly_root / f"{period}.md",
                    self.render_listing_page(f"{workstream['title']}: {period}", messages),
                )

        self.smart_write_text(collections_root / "source-posts.md", self.render_source_collection(dataset["corpus"]))
        self.smart_write_text(
            collections_root / "longform-and-specs.md",
            self.render_longform_collection(dataset["corpus"]),
        )
        self.smart_write_text(
            collections_root / "attachments-and-media.md",
            self.render_attachments_collection(dataset["corpus"]),
        )
        self.smart_write_text(
            collections_root / "opaque-media.md",
            self.render_opaque_media_collection(dataset["corpus"]),
        )
        self.smart_write_text(
            collections_root / "unassigned-substantive.md",
            self.render_unassigned_substantive_collection(dataset["corpus"]),
        )
        self.smart_write_text(
            collections_root / "unassigned-longform.md",
            self.render_unassigned_longform_collection(dataset["corpus"]),
        )
        import_meta = {
            "ran_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "mode": dataset["stats"]["import_mode"],
            "window_start_utc": dataset["stats"]["import_window_start_utc"],
            "default_lookback_days": dataset["stats"]["default_lookback_days"],
            "live_import_message_count": dataset["stats"]["live_import_message_count"],
            "reused_existing_message_count": dataset["stats"]["reused_existing_message_count"],
            "written_files": self.write_counts["written"],
            "created_files": self.write_counts["created"],
            "updated_files": self.write_counts["updated"],
            "unchanged_files": self.write_counts["unchanged"],
        }
        self.smart_write_text(system_root / "imsg-import-meta.json", json.dumps(import_meta, indent=2) + "\n")

    def system_corpus_summary(self, dataset: dict[str, Any]) -> dict[str, Any]:
        corpus = dataset["corpus"]
        return {
            "workstreams": [
                {
                    "slug": workstream["slug"],
                    "title": workstream["title"],
                    "group": workstream["group"],
                    "message_count": len(workstream["messages"]),
                    "longform_message_count": workstream["longform_message_count"],
                    "attachment_message_count": workstream["attachment_message_count"],
                    "source_post_count": len(workstream["source_keys"]),
                    "matched_keywords": workstream["matched_keywords"],
                    "periods": workstream["periods"],
                    "message_rowids": [message["rowid"] for message in workstream["messages"]],
                }
                for workstream in sorted(
                    corpus["workstreams"].values(),
                    key=lambda entry: (entry["group"], entry["title"]),
                )
                if workstream["messages"]
            ],
            "sources": [
                {
                    "canonical_url": source["canonical_url"],
                    "domain": source["domain"],
                    "site_name": source["site_name"],
                    "message_count": source["message_count"],
                    "workstreams": source["workstreams"],
                    "message_workstreams": source["message_workstreams"],
                    "themes": source["themes"],
                    "message_rowids": [message["rowid"] for message in source["messages"]],
                }
                for source in sorted(
                    corpus["sources"].values(),
                    key=lambda entry: (entry["first_shared"], entry["canonical_url"]),
                )
            ],
            "themes": [
                {
                    "slug": theme["slug"],
                    "title": theme["title"],
                    "source_count": len(theme["sources"]),
                    "matched_keywords": theme["matched_keywords"],
                    "canonical_urls": [source["canonical_url"] for source in theme["sources"]],
                }
                for theme in sorted(
                    corpus["themes"].values(),
                    key=lambda entry: entry["title"],
                )
                if theme["sources"]
            ],
            "directives": [
                {
                    "slug": directive["slug"],
                    "title": directive["title"],
                    "message_count": len(directive["messages"]),
                    "matched_keywords": directive["matched_keywords"],
                    "periods": directive["periods"],
                    "message_rowids": [message["rowid"] for message in directive["messages"]],
                }
                for directive in sorted(
                    corpus["directives"].values(),
                    key=lambda entry: entry["title"],
                )
                if directive["messages"]
            ],
            "collections": {
                "longform_messages": [message["rowid"] for message in corpus["collections"]["longform_messages"]],
                "source_messages": [message["rowid"] for message in corpus["collections"]["source_messages"]],
                "media_messages": [message["rowid"] for message in corpus["collections"]["media_messages"]],
                "opaque_media_messages": [
                    message["rowid"] for message in corpus["collections"]["opaque_media_messages"]
                ],
                "unassigned_substantive": [
                    message["rowid"] for message in corpus["collections"]["unassigned_substantive"]
                ],
                "unassigned_longform": [
                    message["rowid"] for message in corpus["collections"]["unassigned_longform"]
                ],
                "research_inbox_sources": [
                    source["canonical_url"] for source in corpus["collections"]["research_inbox_sources"]
                ],
                "longform_groups": [
                    {
                        "count": group["count"],
                        "message_rowids": [message["rowid"] for message in group["messages"]],
                    }
                    for group in corpus["longform_groups"]
                ],
            },
        }

    def render_message_note(self, message: dict[str, Any]) -> str:
        frontmatter = yaml_lines(
            {
                "type": "imsg-agent-message",
                "message_rowid": message["rowid"],
                "message_guid": message["guid"],
                "chat_rowid": message["chat_rowid"],
                "chat_guid": message["chat_guid"],
                "chat_identifier": message["chat_identifier"],
                "sender_id": message["sender_id"],
                "timestamp_utc": message["timestamp_utc"],
                "timestamp_local": message["timestamp_local"],
                "primary_agent": message["primary_agent"],
                "agents_seen": message["agents_seen"],
                "attribution_confidence": message["confidence"],
                "category": message["category"],
                "workstreams": message["workstreams"],
                "directives": message["directives"],
                "source_urls": message["urls"],
                "source_notes": message["source_note_paths"],
                "is_longform": message["is_longform"],
                "is_substantive": message["is_substantive"],
                "is_source_message": message["is_source_message"],
            }
        )
        body: list[str] = []
        body.append(f"# {message['title']}")
        body.append("")
        body.append("## Message")
        if message["text"]:
            body.append(message["text"])
        else:
            body.append("No plain-text body was recoverable from the message record.")
        body.append("")
        body.append("## Corpus Routing")
        if message["workstream_matches"]:
            for match in message["workstream_matches"]:
                path = Path("Corpus") / "Workstreams" / f"{match['slug']}.md"
                reasons = ", ".join(f"`{reason}`" for reason in match["reasons"])
                body.append(f"- [[{path.as_posix()}|{match['title']}]] via {reasons}")
        else:
            body.append("- No explicit workstream keywords matched this message.")
        if message["source_note_paths"]:
            for path in message["source_note_paths"]:
                body.append(f"- [[{path}|Linked source note]]")
        if message["directive_matches"]:
            for match in message["directive_matches"]:
                directive_path = Path("Corpus") / "Compiled" / "Directives" / f"{match['slug']}.md"
                body.append(f"- [[{directive_path.as_posix()}|Directive: {match['title']}]]")
        body.append("")
        body.append("## Source")
        if message["rich_link"]:
            if message["rich_link"].get("site_name"):
                body.append(f"- Rich link site: `{message['rich_link']['site_name']}`")
            if message["rich_link"].get("title"):
                body.append(f"- Rich link title: {redact_sensitive_preview(message['rich_link']['title'])}")
            if message["rich_link"].get("summary"):
                body.append(f"- Rich link summary: {redact_sensitive_preview(message['rich_link']['summary'])}")
        if message["urls"]:
            for url in message["urls"]:
                body.append(f"- [Original link]({url})")
        else:
            body.append("- No external URL was recovered from this item.")
        if message["thread_link"]:
            body.append(f"- [Open Thread in Messages]({message['thread_link']})")
        body.append(f"- Message GUID: `{message['guid']}`")
        body.append(f"- Message Row ID: `{message['rowid']}`")
        body.append("")
        body.append("## Attribution")
        body.append(f"- Primary agent: `{message['primary_agent']}`")
        body.append(f"- Confidence: `{message['confidence']}`")
        body.append(f"- Also seen: `{', '.join(message['agents_seen']) or 'n/a'}`")
        for evidence in message["evidence"]:
            body.append(f"- Evidence: {evidence}")
        if message["attachments"]:
            body.append("")
            body.append("## Attachments")
            for attachment in message["attachments"]:
                label = attachment.get("transfer_name") or attachment.get("filename") or attachment.get("guid")
                body.append(
                    f"- `{label}` | `{attachment.get('mime_type') or 'unknown'}` | "
                    f"`{attachment.get('kind') or 'unknown'}` | {attachment.get('total_bytes', 0)} bytes"
                )
        return "\n".join(frontmatter + [""] + body + [""])

    def render_root_index(self, dataset: dict[str, Any]) -> str:
        stats = dataset["stats"]
        lines = [
            "# iMessage Agents",
            "",
            "Machine-generated reference export from the `macmini` self-thread used for OpenClaw and Hermes on iMessage.",
            "",
            "## Scope",
            f"- Total user messages: `{stats['total_user_messages']}`",
            f"- Substantive corpus messages: `{stats['substantive_message_count']}`",
            f"- Source posts: `{stats['source_post_count']}` from `{stats['source_message_count']}` shared-link messages",
            f"- Longform/spec messages: `{stats['longform_message_count']}`",
            f"- Longform prompt groups: `{stats['longform_group_count']}`",
            f"- User media messages: `{stats['user_media_message_count']}`",
            f"- Opaque media messages: `{stats['opaque_media_message_count']}`",
            f"- Unassigned substantive messages: `{stats['unassigned_substantive_count']}`",
            f"- Unassigned longform messages: `{stats['unassigned_longform_count']}`",
            f"- Research inbox sources: `{stats['research_inbox_source_count']}`",
            f"- Research themes surfaced: `{sum(1 for count in stats['source_theme_counts'].values() if count)}`",
            f"- Import mode: `{stats['import_mode']}`",
            f"- Live import window start: `{stats['import_window_start_utc'] or 'full-history'}`",
            f"- Live messages reclassified this run: `{stats['live_import_message_count']}`",
            f"- Older messages reused from prior export: `{stats['reused_existing_message_count']}`",
            f"- Target chats: `{', '.join(str(value) for value in stats['target_chat_ids'])}`",
            f"- Sender ids observed in agent artifacts: `{', '.join(stats['sender_ids'])}`",
            f"- OpenClaw cutoff (last matched reply): `{stats['openclaw_cutoff_utc']}`",
            f"- Hermes cutoff (first post-OpenClaw matched message): `{stats['hermes_cutoff_utc']}`",
            "",
            "## Curated Layer",
            "- [[Curated/_Overview|Curated Overview]]",
            "- [[Curated/Operating Canon|Operating Canon]]",
            "- [[Curated/Project Ledger|Project Ledger]]",
            "- [[Curated/Research Map|Research Map]]",
            "- [[Curated/Import Policy|Import Policy]]",
            "",
            "## Curated Corpus",
            "- [[Corpus/_Overview|Corpus Overview]]",
            "- [[Corpus/Compiled/_Overview|Compiled Overview]]",
            "- [[Corpus/Compiled/project-map|Project Map]]",
            "- [[Corpus/Compiled/standing-directives|Standing Directives]]",
            "- [[Corpus/Compiled/research-themes|Research Themes]]",
            "- [[Corpus/Compiled/research-inbox|Research Inbox]]",
            "- [[Corpus/Collections/source-posts|Source Posts]]",
            "- [[Corpus/Collections/longform-and-specs|Longform & Specs]]",
            "- [[Corpus/Collections/attachments-and-media|Attachments & Media]]",
            "- [[Corpus/Collections/opaque-media|Opaque Media]]",
            "- [[Corpus/Collections/unassigned-substantive|Unassigned Substantive]]",
            "- [[Corpus/Collections/unassigned-longform|Unassigned Longform]]",
            "",
            "## Workstreams",
        ]
        for slug, count in sorted(stats["counts_by_workstream"].items()):
            rule = WORKSTREAMS_BY_SLUG[slug]
            lines.append(f"- [[Corpus/Workstreams/{slug}|{rule.title}]]: `{count}`")
        lines.append("")
        lines.append("## Directives")
        for slug, count in sorted(stats["directive_counts"].items()):
            directive = next(rule for rule in DIRECTIVE_RULES if rule.slug == slug)
            lines.append(f"- [[Corpus/Compiled/Directives/{slug}|{directive.title}]]: `{count}`")
        lines.append("")
        lines.append("## Research Themes")
        for slug, count in sorted(stats["source_theme_counts"].items()):
            theme = SOURCE_THEMES_BY_SLUG[slug]
            lines.append(f"- [[Corpus/Compiled/Themes/{slug}|{theme.title}]]: `{count}`")
        lines.append("")
        lines.append("## Agents")
        for agent, count in sorted(stats["counts_by_primary_agent"].items()):
            link = safe_slug(agent, fallback="agent")
            lines.append(f"- [[Agents/{link}|{agent}]]: `{count}`")
        lines.append("")
        lines.append("## Categories")
        for category, count in sorted(stats["counts_by_category"].items()):
            link = safe_slug(category, fallback="category")
            lines.append(f"- [[Categories/{link}|{category}]]: `{count}`")
        lines.append("")
        lines.append("## Timeline")
        lines.append("- Browse monthly pages under `Timeline/`.")
        lines.append("")
        lines.append("## System")
        lines.append("- [[System/imsg-agent-export.json]]")
        lines.append("- [[System/imsg-corpus-summary.json]]")
        lines.append("- [[System/imsg-import-meta.json]]")
        lines.append("")
        return "\n".join(lines)

    def render_listing_page(self, title: str, messages: list[dict[str, Any]]) -> str:
        lines = [f"# {title}", ""]
        for message in sorted(messages, key=message_sort_key):
            lines.append(f"- {message_link(message)}")
        lines.append("")
        return "\n".join(lines)

    def render_corpus_overview(self, dataset: dict[str, Any]) -> str:
        stats = dataset["stats"]
        corpus = dataset["corpus"]
        grouped_workstreams: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for workstream in corpus["workstreams"].values():
            if workstream["messages"]:
                grouped_workstreams[workstream["group"]].append(workstream)

        lines = [
            "# Corpus Overview",
            "",
            "This layer sits on top of the raw message archive. It keeps every user message in `Entries/`, then adds evidence-based workstreams, decoded source metadata, compiled directives, and explicit inbox buckets for anything that should not be forced into a guessed project.",
            "",
            "## Guarantees",
            "- All user messages remain preserved under `Entries/`.",
            "- Only deliberate shared links become source notes; incidental inline URLs stay attached to their original messages.",
            "- Shared links use local iMessage rich-link metadata when available for titles and summaries.",
            "- Longform prompts are grouped by normalized text so repeats stay readable.",
            "- Opaque media and unmatched research sources are kept in explicit buckets instead of being mixed into project pages.",
            "- Any substantive item that does not hit an explicit workstream rule is listed in an unmatched collection instead of being guessed.",
            "",
            "## Corpus Totals",
            f"- Total user messages: `{stats['total_user_messages']}`",
            f"- Substantive corpus messages: `{stats['substantive_message_count']}`",
            f"- Source posts: `{stats['source_post_count']}`",
            f"- Longform prompt groups: `{stats['longform_group_count']}`",
            f"- User media messages: `{stats['user_media_message_count']}`",
            f"- Research inbox sources: `{stats['research_inbox_source_count']}`",
            f"- Research themes surfaced: `{sum(1 for count in stats['source_theme_counts'].values() if count)}`",
            f"- Import mode: `{stats['import_mode']}`",
            f"- Live import window start: `{stats['import_window_start_utc'] or 'full-history'}`",
            f"- Live messages reclassified this run: `{stats['live_import_message_count']}`",
            "",
            "## Curated Layer",
            "- [[Curated/_Overview|Curated Overview]]",
            "- [[Curated/Operating Canon|Operating Canon]]",
            "- [[Curated/Project Ledger|Project Ledger]]",
            "- [[Curated/Research Map|Research Map]]",
            "- [[Curated/Import Policy|Import Policy]]",
            "",
            "## Collections",
            "- [[Corpus/Compiled/_Overview|Compiled Overview]]",
            "- [[Corpus/Compiled/project-map|Project Map]]",
            "- [[Corpus/Compiled/standing-directives|Standing Directives]]",
            "- [[Corpus/Compiled/research-themes|Research Themes]]",
            "- [[Corpus/Compiled/research-inbox|Research Inbox]]",
            "- [[Corpus/Collections/source-posts|Source Posts]]",
            "- [[Corpus/Collections/longform-and-specs|Longform & Specs]]",
            "- [[Corpus/Collections/attachments-and-media|Attachments & Media]]",
            "- [[Corpus/Collections/opaque-media|Opaque Media]]",
            "- [[Corpus/Collections/unassigned-substantive|Unassigned Substantive]]",
            "- [[Corpus/Collections/unassigned-longform|Unassigned Longform]]",
            "",
            "## Workstreams",
        ]
        for group in sorted(grouped_workstreams):
            lines.append(f"### {group}")
            for workstream in sorted(grouped_workstreams[group], key=lambda entry: entry["title"]):
                lines.append(
                    f"- [[Corpus/Workstreams/{workstream['slug']}|{workstream['title']}]] "
                    f"| `{len(workstream['messages'])}` messages "
                    f"| `{len(workstream['source_keys'])}` source posts "
                    f"| `{workstream['longform_message_count']}` longform "
                    f"| `{workstream['source_message_count']}` source-linked messages"
                )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def render_compiled_overview(self, dataset: dict[str, Any]) -> str:
        stats = dataset["stats"]
        lines = [
            "# Compiled Overview",
            "",
            "This layer is the readable synthesis pass. It turns the exported corpus into project views, operating directives, and a research inbox so the vault can be used as a reference system instead of only as a raw archive.",
            "",
            "## Curated Layer",
            "- [[Curated/_Overview|Curated Overview]]",
            "- [[Curated/Operating Canon|Operating Canon]]",
            "- [[Curated/Project Ledger|Project Ledger]]",
            "- [[Curated/Research Map|Research Map]]",
            "- [[Curated/Import Policy|Import Policy]]",
            "",
            "## Pages",
            "- [[Corpus/Compiled/project-map|Project Map]]",
            "- [[Corpus/Compiled/standing-directives|Standing Directives]]",
            "- [[Corpus/Compiled/research-themes|Research Themes]]",
            "- [[Corpus/Compiled/research-inbox|Research Inbox]]",
            "",
            "## Totals",
            f"- Workstreams with messages: `{sum(1 for count in stats['counts_by_workstream'].values() if count)}`",
            f"- Standing directives surfaced: `{sum(1 for count in stats['directive_counts'].values() if count)}`",
            f"- Research themes surfaced: `{sum(1 for count in stats['source_theme_counts'].values() if count)}`",
            f"- Source posts: `{stats['source_post_count']}`",
            f"- User media messages: `{stats['user_media_message_count']}`",
            f"- Research inbox sources: `{stats['research_inbox_source_count']}`",
            f"- Import mode: `{stats['import_mode']}`",
            f"- Live import window start: `{stats['import_window_start_utc'] or 'full-history'}`",
            "",
        ]
        return "\n".join(lines)

    def render_project_map(self, dataset: dict[str, Any]) -> str:
        corpus = dataset["corpus"]
        lines = [
            "# Project Map",
            "",
            "High-level project compilation derived from the corpus. Each section points back to the underlying workstream page, representative message clusters, and routed source posts.",
            "",
        ]
        for workstream in sorted(
            (entry for entry in corpus["workstreams"].values() if entry["messages"]),
            key=lambda entry: (entry["group"], entry["title"]),
        ):
            peak_period, peak_count = max(workstream["periods"].items(), key=lambda item: item[1])
            directive_counts = Counter(
                slug for message in workstream["messages"] for slug in message["directives"]
            )
            relevant_groups = [
                group
                for group in corpus["longform_groups"]
                if any(workstream["slug"] in message["workstreams"] for message in group["messages"])
            ]
            relevant_groups.sort(key=lambda entry: (-entry["count"], entry["first_seen"]))
            lines.append(f"## {workstream['title']}")
            lines.append(f"- [[Corpus/Workstreams/{workstream['slug']}|Open workstream page]]")
            lines.append(f"- Group: `{workstream['group']}`")
            lines.append(f"- Messages: `{len(workstream['messages'])}`")
            lines.append(f"- Peak month: `{peak_period}` with `{peak_count}` messages")
            lines.append(f"- Source posts: `{len(workstream['source_keys'])}`")
            lines.append(f"- Longform/spec messages: `{workstream['longform_message_count']}`")
            if directive_counts:
                directive_labels = ", ".join(
                    f"`{next(rule.title for rule in DIRECTIVE_RULES if rule.slug == slug)}` ({count})"
                    for slug, count in directive_counts.most_common(3)
                )
                lines.append(f"- Overlapping directives: {directive_labels}")
            if relevant_groups:
                lines.append("- Representative clusters:")
                for group in relevant_groups[:3]:
                    lines.append(
                        f"  - `{group['count']}x` {group['preview']} | first `{group['first_seen']}` | last `{group['last_seen']}`"
                    )
            if workstream["source_keys"]:
                lines.append("- Seed sources:")
                for key in workstream["source_keys"][:5]:
                    source = corpus["sources"][key]
                    lines.append(
                        f"  - [[{source['note_path']}|{source['title']}]] | `{source['site_name']}` | {source['content_preview']}"
                    )
            lines.append("")
        return "\n".join(lines)

    def render_standing_directives(self, dataset: dict[str, Any]) -> str:
        corpus = dataset["corpus"]
        lines = [
            "# Standing Directives",
            "",
            "Cross-cutting operating expectations that recur across the corpus. These are grounded in repeated user messages and linked back to source notes rather than inferred from the agent configs.",
            "",
        ]
        for directive in sorted(
            (entry for entry in corpus["directives"].values() if entry["messages"]),
            key=lambda entry: entry["title"],
        ):
            lines.append(f"## {directive['title']}")
            lines.append(f"- [[{directive['note_path']}|Open directive page]]")
            lines.append(f"- Messages: `{len(directive['messages'])}`")
            if directive["matched_keywords"]:
                lines.append(
                    f"- Matched phrases: {', '.join(f'`{keyword}`' for keyword in directive['matched_keywords'])}"
                )
            lines.append(f"- {directive['description']}")
            for message in directive["messages"][:5]:
                lines.append(f"- {message_link(message)}")
            lines.append("")
        return "\n".join(lines)

    def render_directive_page(self, directive: dict[str, Any]) -> str:
        lines = [
            f"# {directive['title']}",
            "",
            directive["description"],
            "",
            "## Scope",
            f"- Message count: `{len(directive['messages'])}`",
        ]
        if directive["messages"]:
            lines.append(f"- First seen: `{directive['messages'][0]['timestamp_local']}`")
            lines.append(f"- Last seen: `{directive['messages'][-1]['timestamp_local']}`")
        if directive["matched_keywords"]:
            lines.append(
                f"- Matched phrases: {', '.join(f'`{keyword}`' for keyword in directive['matched_keywords'])}"
            )
        lines.extend(["", "## Timeline"])
        for period, count in directive["periods"].items():
            lines.append(f"- `{period}`: `{count}`")
        lines.extend(["", "## Referencing Messages"])
        for message in directive["messages"]:
            lines.append(f"- {message_link(message)}")
        lines.append("")
        return "\n".join(lines)

    def render_workstream_page(self, workstream: dict[str, Any], corpus: dict[str, Any]) -> str:
        peak_period, peak_count = max(workstream["periods"].items(), key=lambda item: item[1])
        directive_counts = Counter(
            slug for message in workstream["messages"] for slug in message["directives"]
        )
        relevant_groups = [
            group
            for group in corpus["longform_groups"]
            if any(workstream["slug"] in message["workstreams"] for message in group["messages"])
        ]
        relevant_groups.sort(key=lambda entry: (-entry["count"], entry["first_seen"]))
        source_posts = [corpus["sources"][key] for key in workstream["source_keys"]]

        lines = [
            f"# {workstream['title']}",
            "",
            workstream["description"],
            "",
            "## Scope",
            f"- Message count: `{len(workstream['messages'])}`",
            f"- Source posts: `{len(workstream['source_keys'])}`",
            f"- Longform/spec messages: `{workstream['longform_message_count']}`",
            f"- Source-linked messages: `{workstream['source_message_count']}`",
            f"- User media messages: `{workstream['attachment_message_count']}`",
        ]
        if workstream["messages"]:
            lines.append(f"- First mention: `{workstream['messages'][0]['timestamp_local']}`")
            lines.append(f"- Last mention: `{workstream['messages'][-1]['timestamp_local']}`")
        lines.append(f"- Peak month: `{peak_period}` with `{peak_count}` messages")
        if workstream["matched_keywords"]:
            lines.append(f"- Matched keywords: {', '.join(f'`{value}`' for value in workstream['matched_keywords'])}")
        if directive_counts:
            lines.append(
                "- Directive overlap: "
                + ", ".join(
                    f"`{next(rule.title for rule in DIRECTIVE_RULES if rule.slug == slug)}` ({count})"
                    for slug, count in directive_counts.most_common(5)
                )
            )
        lines.extend(["", "## Timeline"])
        for period, count in workstream["periods"].items():
            lines.append(
                f"- [[Corpus/Workstreams/{workstream['slug']}/{period}|{period}]]: `{count}`"
            )

        lines.extend(["", "## Recurring Message Clusters"])
        if relevant_groups:
            for group in relevant_groups[:12]:
                lines.append(
                    f"- `{group['count']}x` {group['preview']} "
                    f"| first `{group['first_seen']}` | last `{group['last_seen']}`"
                )
                for message in group["messages"][:3]:
                    if workstream["slug"] in message["workstreams"]:
                        lines.append(f"  - {message_link(message)}")
        else:
            lines.append("- No longform prompt groups were detected for this workstream.")

        lines.extend(["", "## Source Posts"])
        if source_posts:
            for source in source_posts:
                lines.append(
                    f"- [[{source['note_path']}|{source['title']}]] "
                    f"| `{source['site_name']}` | `{source['message_count']}` messages | {source['content_preview']}"
                )
        else:
            lines.append("- No linked source posts were routed into this workstream.")

        attachment_messages = [message for message in workstream["messages"] if message["has_non_preview_attachment"]]
        lines.extend(["", "## User Media"])
        if attachment_messages:
            for message in attachment_messages:
                lines.append(f"- {message_link(message)}")
        else:
            lines.append("- No user media messages were routed into this workstream.")

        return "\n".join(lines + [""])

    def render_source_page(self, source: dict[str, Any]) -> str:
        frontmatter = yaml_lines(
            {
                "type": "imsg-linked-source",
                "canonical_url": source["canonical_url"],
                "source_domain": source["domain"],
                "site_name": source["site_name"],
                "message_count": source["message_count"],
                "first_shared": source["first_shared"],
                "last_shared": source["last_shared"],
                "workstreams": source["workstreams"],
                "message_workstreams": source["message_workstreams"],
                "directives": source["directives"],
                "themes": source["themes"],
                "source_variants": source["url_variants"],
            }
        )
        lines = [
            f"# {source['title']}",
            "",
            "## Link Preview",
        ]
        if source["label_preview"]:
            lines.append(f"- Preview title: {source['label_preview']}")
        if source["summary_preview"]:
            lines.append(f"- Preview summary: {source['summary_preview']}")
        lines.extend(
            [
                f"- Site: `{source['site_name']}`",
                "",
                "## Original Post",
            ]
        )
        lines.extend(
            [
            f"- [Canonical link]({source['canonical_url']})",
            f"- Domain: `{source['domain']}`",
            f"- First shared: `{source['first_shared']}`",
            f"- Last shared: `{source['last_shared']}`",
            ]
        )
        if source["url_variants"]:
            lines.append("")
            lines.append("## Variants Seen")
            for url in source["url_variants"]:
                lines.append(f"- [Variant]({url})")
        lines.extend(["", "## Routed Workstreams"])
        if source["workstreams"]:
            for slug in source["workstreams"]:
                rule = WORKSTREAMS_BY_SLUG.get(slug)
                label = rule.title if rule else slug
                lines.append(f"- [[Corpus/Workstreams/{slug}|{label}]]")
        else:
            lines.append("- No explicit workstream match. See [[Corpus/Compiled/research-inbox|Research Inbox]].")
        if source["message_workstreams"]:
            lines.extend(["", "## Mentioned Alongside Workstreams"])
            for slug in source["message_workstreams"]:
                rule = WORKSTREAMS_BY_SLUG.get(slug)
                label = rule.title if rule else slug
                lines.append(f"- [[Corpus/Workstreams/{slug}|{label}]]")
        if source["themes"]:
            lines.extend(["", "## Research Themes"])
            for slug in source["themes"]:
                theme = SOURCE_THEMES_BY_SLUG.get(slug)
                if theme:
                    lines.append(f"- [[Corpus/Compiled/Themes/{slug}|{theme.title}]]")
        if source["directives"]:
            lines.extend(["", "## Related Directives"])
            for slug in source["directives"]:
                directive = next((rule for rule in DIRECTIVE_RULES if rule.slug == slug), None)
                if directive:
                    lines.append(f"- [[Corpus/Compiled/Directives/{slug}|{directive.title}]]")
        if source["context_previews"]:
            lines.extend(["", "## Context Captured In Messages"])
            for preview in source["context_previews"]:
                lines.append(f"- {preview}")
        lines.extend(["", "## Referencing Messages"])
        for message in source["messages"]:
            lines.append(f"- {message_link(message)}")
        return "\n".join(frontmatter + [""] + lines + [""])

    def render_source_collection(self, corpus: dict[str, Any]) -> str:
        lines = [
            "# Source Posts",
            "",
            "Deliberately shared links, broken out into source notes with original URLs, local iMessage rich-link metadata, and links back to the originating messages.",
            "",
            f"- Unique source notes: `{len(corpus['sources'])}`",
            f"- Research inbox sources: `{len(corpus['collections']['research_inbox_sources'])}`",
            "- Theme views: [[Corpus/Compiled/research-themes|Research Themes]]",
            "",
        ]
        lines.append("## Routed By Workstream")
        for workstream in sorted(
            (entry for entry in corpus["workstreams"].values() if entry["source_keys"]),
            key=lambda entry: (entry["group"], entry["title"]),
        ):
            lines.append(f"### {workstream['title']}")
            for key in workstream["source_keys"]:
                source = corpus["sources"][key]
                lines.append(
                    f"- [[{source['note_path']}|{source['title']}]] "
                    f"| `{source['site_name']}` | {source['content_preview']}"
                )
            lines.append("")
        if corpus["collections"]["research_inbox_sources"]:
            lines.append("## Research Inbox")
            for source in corpus["collections"]["research_inbox_sources"]:
                theme_slug = source.get("primary_theme")
                theme_label = SOURCE_THEMES_BY_SLUG[theme_slug].title if theme_slug in SOURCE_THEMES_BY_SLUG else "Unclassified"
                lines.append(
                    f"- [[{source['note_path']}|{source['title']}]] "
                    f"| `{source['site_name']}` | `{theme_label}` | {source['content_preview']}"
                )
            lines.append("")
        return "\n".join(lines)

    def render_longform_collection(self, corpus: dict[str, Any]) -> str:
        lines = [
            "# Longform & Specs",
            "",
            "Messages at or above the longform threshold, grouped by normalized text to collapse retransmissions and repeated directives.",
            "",
            f"- Longform messages: `{len(corpus['collections']['longform_messages'])}`",
            f"- Longform groups: `{len(corpus['longform_groups'])}`",
            "",
        ]
        for group in corpus["longform_groups"]:
            titles = [
                WORKSTREAMS_BY_SLUG[slug].title
                for slug in group["workstreams"]
                if slug in WORKSTREAMS_BY_SLUG
            ]
            lines.append(
                f"## {group['preview']}"
            )
            lines.append(f"- Occurrences: `{group['count']}`")
            lines.append(f"- First seen: `{group['first_seen']}`")
            lines.append(f"- Last seen: `{group['last_seen']}`")
            lines.append(
                f"- Workstreams: {', '.join(f'`{title}`' for title in titles) if titles else '`none`'}"
            )
            for message in group["messages"]:
                lines.append(f"- {message_link(message)}")
            lines.append("")
        return "\n".join(lines)

    def render_attachments_collection(self, corpus: dict[str, Any]) -> str:
        attachment_messages = corpus["collections"]["media_messages"]
        kind_counts: Counter[str] = Counter()
        for message in attachment_messages:
            for attachment in message["attachments"]:
                if attachment.get("kind") == "share-preview":
                    continue
                kind_counts[attachment.get("kind") or "unknown"] += 1

        lines = [
            "# Attachments & Media",
            "",
            "User-shared media and media requests. Share-preview attachments for URL balloons are excluded here and live on the relevant source notes instead.",
            "",
            f"- User media messages: `{len(attachment_messages)}`",
            f"- Opaque media messages: `{len(corpus['collections']['opaque_media_messages'])}`",
        ]
        for kind, count in sorted(kind_counts.items()):
            lines.append(f"- `{kind}` attachments: `{count}`")
        lines.append("")
        for message in attachment_messages:
            labels = [
                str(attachment.get("transfer_name") or attachment.get("filename") or attachment.get("guid"))
                for attachment in message["attachments"]
                if attachment.get("kind") != "share-preview"
            ]
            lines.append(f"- {message_link(message)} | {', '.join(f'`{label}`' for label in labels)}")
        lines.append("")
        return "\n".join(lines)

    def render_opaque_media_collection(self, corpus: dict[str, Any]) -> str:
        messages = corpus["collections"]["opaque_media_messages"]
        lines = [
            "# Opaque Media",
            "",
            "User-shared media messages where the text body is empty or effectively empty. These remain preserved here so they do not clutter project buckets.",
            "",
            f"- Message count: `{len(messages)}`",
            "",
        ]
        for message in messages:
            labels = [
                str(attachment.get("transfer_name") or attachment.get("filename") or attachment.get("guid"))
                for attachment in message["attachments"]
                if attachment.get("kind") != "share-preview"
            ]
            lines.append(f"- {message_link(message)} | {', '.join(f'`{label}`' for label in labels)}")
        lines.append("")
        return "\n".join(lines)

    def render_unassigned_substantive_collection(self, corpus: dict[str, Any]) -> str:
        messages = corpus["collections"]["unassigned_substantive"]
        lines = [
            "# Unassigned Substantive",
            "",
            "Substantive non-source, non-media items that were preserved in the corpus but did not hit any explicit workstream keyword. They are listed here instead of being forced into a guessed project bucket.",
            "",
            f"- Message count: `{len(messages)}`",
            "",
        ]
        for message in messages:
            lines.append(f"- {message_link(message)}")
        lines.append("")
        return "\n".join(lines)

    def render_unassigned_longform_collection(self, corpus: dict[str, Any]) -> str:
        messages = corpus["collections"]["unassigned_longform"]
        lines = [
            "# Unassigned Longform",
            "",
            "Longform messages that carry substantial intent but still do not cleanly map to an explicit workstream. This is the main manual-review bucket for future taxonomy changes.",
            "",
            f"- Message count: `{len(messages)}`",
            "",
        ]
        for message in messages:
            lines.append(f"- {message_link(message)}")
        lines.append("")
        return "\n".join(lines)

    def render_research_themes(self, corpus: dict[str, Any]) -> str:
        unique_themed_sources = {
            source["canonical_url"]
            for theme in corpus["themes"].values()
            for source in theme["sources"]
        }
        lines = [
            "# Research Themes",
            "",
            "Theme-based compilation of the linked-source corpus. This cuts across project workstreams so the vault also works as a reusable research reference.",
            "",
            f"- Themes with sources: `{sum(1 for theme in corpus['themes'].values() if theme['sources'])}`",
            f"- Unique themed sources: `{len(unique_themed_sources)}`",
            "",
        ]
        for theme in sorted(
            (entry for entry in corpus["themes"].values() if entry["sources"]),
            key=lambda entry: entry["title"],
        ):
            inbox_count = sum(1 for source in theme["sources"] if not source["workstreams"])
            lines.append(f"## {theme['title']}")
            lines.append(f"- [[{theme['note_path']}|Open theme page]]")
            lines.append(f"- Source count: `{len(theme['sources'])}`")
            lines.append(f"- Research inbox overlap: `{inbox_count}`")
            lines.append(f"- {theme['description']}")
            for source in theme["sources"][:5]:
                lines.append(
                    f"- [[{source['note_path']}|{source['title']}]] | `{source['site_name']}` | {source['content_preview']}"
                )
            lines.append("")
        return "\n".join(lines)

    def render_theme_page(self, theme: dict[str, Any]) -> str:
        lines = [
            f"# {theme['title']}",
            "",
            theme["description"],
            "",
            "## Scope",
            f"- Source count: `{len(theme['sources'])}`",
        ]
        if theme["matched_keywords"]:
            lines.append(
                f"- Matched phrases: {', '.join(f'`{keyword}`' for keyword in theme['matched_keywords'])}"
            )
        inbox_count = sum(1 for source in theme["sources"] if not source["workstreams"])
        lines.append(f"- Research inbox overlap: `{inbox_count}`")
        lines.extend(["", "## Sources"])
        for source in theme["sources"]:
            if source["workstreams"]:
                route_slug = source["workstreams"][0]
                route = WORKSTREAMS_BY_SLUG.get(route_slug).title if route_slug in WORKSTREAMS_BY_SLUG else route_slug
            else:
                route = "Research Inbox"
            lines.append(
                f"- [[{source['note_path']}|{source['title']}]] | `{source['site_name']}` | `{route}` | {source['content_preview']}"
            )
        lines.append("")
        return "\n".join(lines)

    def render_research_inbox(self, corpus: dict[str, Any]) -> str:
        lines = [
            "# Research Inbox",
            "",
            "Shared links that are preserved as source notes but do not yet cleanly map to an explicit project/workstream. This is the right place to revisit when new themes emerge.",
            "",
            f"- Source count: `{len(corpus['collections']['research_inbox_sources'])}`",
            "",
        ]
        grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        for source in corpus["collections"]["research_inbox_sources"]:
            theme_slug = source.get("primary_theme") or "unclassified"
            grouped[theme_slug][source["site_name"]].append(source)
        for theme_slug in sorted(grouped):
            if theme_slug == "unclassified":
                theme_title = "Unclassified"
            else:
                theme = SOURCE_THEMES_BY_SLUG.get(theme_slug)
                theme_title = theme.title if theme else theme_slug
            lines.append(f"## {theme_title}")
            if theme_slug != "unclassified" and theme_slug in SOURCE_THEMES_BY_SLUG:
                lines.append(f"- [[Corpus/Compiled/Themes/{theme_slug}|Open theme page]]")
            for site_name in sorted(grouped[theme_slug]):
                lines.append(f"### {site_name}")
                for source in grouped[theme_slug][site_name]:
                    lines.append(
                        f"- [[{source['note_path']}|{source['title']}]] "
                        f"| {source['content_preview']}"
                    )
            lines.append("")
        return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export OpenClaw/Hermes iMessage history into an Obsidian vault.")
    parser.add_argument("--chat-db", default="~/Library/Messages/chat.db")
    parser.add_argument("--vault-root", required=True)
    parser.add_argument("--output-root", default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--openclaw-root", default="~/.openclaw")
    parser.add_argument("--hermes-root", default="~/.hermes")
    parser.add_argument(
        "--since",
        help="Only reclassify live messages on or after this ISO date/timestamp. Older messages are reused from the prior export.",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=7,
        help="Default live import window when --since is omitted. Defaults to 7 days.",
    )
    parser.add_argument(
        "--full-history",
        action="store_true",
        help="Rebuild the entire corpus from all recoverable messages instead of using the gated live-import window.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.lookback_days < 0:
        raise SystemExit("--lookback-days must be >= 0")
    if args.full_history and args.since:
        raise SystemExit("--full-history and --since are mutually exclusive")
    return args


def main() -> None:
    Importer(parse_args()).run()


if __name__ == "__main__":
    main()
