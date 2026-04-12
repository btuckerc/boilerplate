#!/usr/bin/env python3

from __future__ import annotations

import argparse
from contextlib import contextmanager
import errno
import fcntl
import hashlib
import json
import os
import re
import shlex
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APPLE_EPOCH_UNIX = 978307200
DEFAULT_CONFIG_FILE = Path.home() / ".config/decent-angl/imsg.env"
DEFAULT_SERVER_MACHINE_ID = "macmini"
DEFAULT_SERVER_SSH_DEST = "admin@macmini"
DEFAULT_REMOTE_COMMAND = "~/.local/bin/imsgd"
DEFAULT_LIMIT = 40
DEFAULT_BACKFILL_ROWS = 4000
DEFAULT_SYNC_LOCK_NAME = "sync.lock"
DEFAULT_SYNC_BUSY_TIMEOUT_MS = 5000
DEFAULT_SEND_WAIT_SECONDS = 60
DEFAULT_SEND_POLL_INTERVAL_SECONDS = 1.0
SEND_WORKER_LABEL = "com.decentangl.imsg.send-worker"

REACTION_LABELS = {
    2000: "Loved",
    2001: "Liked",
    2002: "Disliked",
    2003: "Laughed",
    2004: "Emphasized",
    2005: "Questioned",
    3000: "Removed love",
    3001: "Removed like",
    3002: "Removed dislike",
    3003: "Removed laugh",
    3004: "Removed emphasis",
    3005: "Removed question",
}

SERVICE_TYPE_MAP = {
    "imessage": "iMessage",
    "sms": "SMS",
    "auto": "iMessage",
}

KNOWN_MACHINE_IDS = {
    "omarchy": "omarchy",
    "btct14": "omarchy",
    "macbook": "macbook",
    "btc-mbp14": "macbook",
    "macmini": "macmini",
    "webweaver": "macmini",
}


@dataclass
class Config:
    machine_id: str
    server_machine_id: str
    server_ssh_dest: str
    server_ssh_identity_file: str
    remote_command: str
    chat_db: Path | None
    attachments_root: Path | None
    state_root: Path
    index_db: Path
    default_limit: int
    sync_backfill_rows: int
    sync_on_read: bool
    account_hint: str
    phone_account_hint: str
    provider_send_bin: Path | None
    duplicate_window_seconds: int
    quiet_hours_start: str
    quiet_hours_end: str


class LockBusyError(RuntimeError):
    pass


def load_env_file(path: Path) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return
    except OSError as exc:
        raise SystemExit(f"Unable to read imsg config: {path}: {exc}") from exc

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = os.path.expandvars(value)


def expand_optional_path(raw: str | None) -> Path | None:
    if raw in (None, ""):
        return None
    return Path(os.path.expandvars(raw)).expanduser()


def expand_required_path(raw: str | None, default: Path) -> Path:
    if raw in (None, ""):
        return default
    return Path(os.path.expandvars(raw)).expanduser()


def normalize_machine_id(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    value = raw_value.strip().lower()
    if not value:
        return None
    if value in KNOWN_MACHINE_IDS:
        return KNOWN_MACHINE_IDS[value]
    if value.startswith("btc-mbp14"):
        return "macbook"
    if value.startswith("btct14"):
        return "omarchy"
    if value.startswith("webweaver"):
        return "macmini"
    return value


def command_output(command: list[str]) -> str | None:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout


def detect_machine_id() -> str:
    for env_key in ("IMSG_MACHINE_ID",):
        machine_id = normalize_machine_id(os.environ.get(env_key))
        if machine_id:
            return machine_id

    chezmoi_data = command_output(["chezmoi", "data"])
    if chezmoi_data:
        try:
            parsed = json.loads(chezmoi_data)
            machine_id = normalize_machine_id(
                parsed.get("decentangl", {}).get("machine_id")
            )
            if machine_id:
                return machine_id
        except Exception:
            pass

    host_name = socket.gethostname()
    machine_id = normalize_machine_id(host_name)
    if machine_id:
        return machine_id
    return host_name


def load_config() -> Config:
    load_env_file(DEFAULT_CONFIG_FILE)
    machine_id = detect_machine_id()
    state_root_default = Path.home() / ".local/state/imsg"
    index_db_default = state_root_default / "imsg.sqlite"

    default_limit = parse_positive_int(
        os.environ.get("IMSG_DEFAULT_LIMIT"),
        DEFAULT_LIMIT,
    )
    sync_backfill_rows = parse_positive_int(
        os.environ.get("IMSG_SYNC_BACKFILL_ROWS"),
        DEFAULT_BACKFILL_ROWS,
    )

    return Config(
        machine_id=machine_id,
        server_machine_id=normalize_machine_id(
            os.environ.get("IMSG_SERVER_MACHINE_ID")
        )
        or DEFAULT_SERVER_MACHINE_ID,
        server_ssh_dest=os.environ.get("IMSG_SERVER_SSH_DEST", DEFAULT_SERVER_SSH_DEST),
        server_ssh_identity_file=os.environ.get("IMSG_SERVER_SSH_IDENTITY_FILE", ""),
        remote_command=os.environ.get("IMSG_REMOTE_COMMAND", DEFAULT_REMOTE_COMMAND),
        chat_db=expand_optional_path(os.environ.get("IMSG_CHAT_DB")),
        attachments_root=expand_optional_path(os.environ.get("IMSG_ATTACHMENTS_ROOT")),
        state_root=expand_required_path(os.environ.get("IMSG_STATE_ROOT"), state_root_default),
        index_db=expand_required_path(os.environ.get("IMSG_INDEX_DB"), index_db_default),
        default_limit=default_limit,
        sync_backfill_rows=sync_backfill_rows,
        sync_on_read=os.environ.get("IMSG_SYNC_ON_READ", "1").strip() not in {"0", "false", "False"},
        account_hint=os.environ.get("IMSG_ACCOUNT_HINT", ""),
        phone_account_hint=os.environ.get("IMSG_PHONE_ACCOUNT_HINT", ""),
        provider_send_bin=expand_optional_path(os.environ.get("IMSG_PROVIDER_SEND_BIN")),
        duplicate_window_seconds=parse_positive_int(
            os.environ.get("IMSG_DUPLICATE_WINDOW_SECONDS"),
            300,
        ),
        quiet_hours_start=os.environ.get("IMSG_QUIET_HOURS_START", "").strip(),
        quiet_hours_end=os.environ.get("IMSG_QUIET_HOURS_END", "").strip(),
    )


def parse_positive_int(raw_value: str | None, default: int) -> int:
    try:
        value = int(str(raw_value))
    except Exception:
        return default
    if value <= 0:
        return default
    return value


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def state_lock_path(cfg: Config, name: str) -> Path:
    return cfg.state_root / name


@contextmanager
def exclusive_lock(path: Path, *, blocking: bool) -> Any:
    ensure_parent(path)
    with path.open("a+", encoding="utf-8") as handle:
        flags = fcntl.LOCK_EX
        if not blocking:
            flags |= fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), flags)
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EAGAIN}:
                raise LockBusyError(str(path)) from exc
            raise
        try:
            yield handle
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def now_utc_epoch() -> int:
    return int(time.time())


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_guid_reference(value: str | None) -> str | None:
    if value in (None, ""):
        return None
    if "/" in value:
        return value.rsplit("/", 1)[-1]
    return value


def apple_ns_to_unix_seconds(raw_value: Any) -> float | None:
    if raw_value in (None, ""):
        return None
    try:
        value = int(raw_value)
    except Exception:
        return None
    return (value / 1_000_000_000) + APPLE_EPOCH_UNIX


def apple_ns_to_iso(raw_value: Any) -> str | None:
    seconds = apple_ns_to_unix_seconds(raw_value)
    if seconds is None:
        return None
    return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat()


def display_timestamp(raw_value: Any) -> str:
    seconds = apple_ns_to_unix_seconds(raw_value)
    if seconds is None:
        return "unknown"
    return datetime.fromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S")


def compact_text(value: str | None, limit: int = 120) -> str:
    if value in (None, ""):
        return ""
    collapsed = " ".join(str(value).split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


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
        if not candidate:
            continue
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


def row_value(row: sqlite3.Row | dict[str, Any], key: str, default: Any = None) -> Any:
    try:
        return row[key]
    except Exception:
        return default


def sqlite_connect_ro(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(
        f"file:{path}?mode=ro",
        uri=True,
        timeout=DEFAULT_SYNC_BUSY_TIMEOUT_MS / 1000,
    )
    con.row_factory = sqlite3.Row
    con.execute(f"pragma busy_timeout = {DEFAULT_SYNC_BUSY_TIMEOUT_MS}")
    con.execute("pragma query_only = on")
    return con


def sqlite_connect_rw(path: Path) -> sqlite3.Connection:
    ensure_parent(path)
    con = sqlite3.connect(path, timeout=DEFAULT_SYNC_BUSY_TIMEOUT_MS / 1000)
    con.row_factory = sqlite3.Row
    con.execute(f"pragma busy_timeout = {DEFAULT_SYNC_BUSY_TIMEOUT_MS}")
    con.execute("pragma journal_mode = wal")
    con.execute("pragma foreign_keys = on")
    return con


def initialize_index_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        pragma journal_mode = wal;
        pragma foreign_keys = on;

        create table if not exists meta (
            key text primary key,
            value text not null
        );

        create table if not exists handles (
            rowid integer primary key,
            handle_id text not null,
            country text,
            service text,
            uncanonicalized_id text,
            person_centric_id text,
            contact_name text not null default '',
            message_count integer not null default 0,
            last_message_date integer not null default 0
        );
        create index if not exists idx_handles_handle_id on handles(handle_id);

        create table if not exists chats (
            rowid integer primary key,
            guid text not null unique,
            chat_identifier text,
            service_name text,
            room_name text,
            display_name text,
            account_login text,
            account_id text,
            last_addressed_handle text,
            last_read_message_timestamp integer not null default 0,
            style integer not null default 0,
            is_archived integer not null default 0,
            participant_summary text,
            participant_count integer not null default 0,
            message_count integer not null default 0,
            unread_count integer not null default 0,
            last_message_rowid integer,
            last_message_date integer not null default 0
        );
        create index if not exists idx_chats_guid on chats(guid);
        create index if not exists idx_chats_last_message_date on chats(last_message_date desc);

        create table if not exists chat_handles (
            chat_rowid integer not null,
            handle_rowid integer not null,
            primary key (chat_rowid, handle_rowid)
        );
        create index if not exists idx_chat_handles_handle on chat_handles(handle_rowid);

        create table if not exists messages (
            rowid integer primary key,
            guid text not null unique,
            text text,
            subject text,
            handle_rowid integer,
            service text,
            account text,
            date integer not null default 0,
            date_read integer not null default 0,
            date_delivered integer not null default 0,
            is_delivered integer not null default 0,
            is_finished integer not null default 0,
            is_from_me integer not null default 0,
            is_read integer not null default 0,
            is_system_message integer not null default 0,
            is_sent integer not null default 0,
            has_attachments integer not null default 0,
            associated_message_guid text,
            associated_message_guid_normalized text,
            associated_message_type integer not null default 0,
            associated_message_emoji text,
            reply_to_guid text,
            thread_originator_guid text,
            thread_originator_part text,
            date_edited integer not null default 0,
            date_retracted integer not null default 0,
            expressive_send_style_id text,
            item_type integer not null default 0,
            group_action_type integer not null default 0,
            message_action_type integer not null default 0
        );
        create index if not exists idx_messages_guid on messages(guid);
        create index if not exists idx_messages_date on messages(date desc);
        create index if not exists idx_messages_handle on messages(handle_rowid);
        create index if not exists idx_messages_reply on messages(reply_to_guid);
        create index if not exists idx_messages_associated on messages(associated_message_guid_normalized);

        create table if not exists chat_messages (
            chat_rowid integer not null,
            message_rowid integer not null,
            message_date integer not null default 0,
            primary key (chat_rowid, message_rowid)
        );
        create index if not exists idx_chat_messages_chat_date on chat_messages(chat_rowid, message_date desc);
        create index if not exists idx_chat_messages_message on chat_messages(message_rowid);

        create table if not exists attachments (
            rowid integer primary key,
            guid text not null unique,
            filename text,
            mime_type text,
            uti text,
            transfer_name text,
            total_bytes integer not null default 0,
            is_sticker integer not null default 0,
            created_date integer not null default 0,
            path_exists integer not null default 0
        );
        create index if not exists idx_attachments_guid on attachments(guid);

        create table if not exists message_attachments (
            message_rowid integer not null,
            attachment_rowid integer not null,
            primary key (message_rowid, attachment_rowid)
        );
        create index if not exists idx_message_attachments_message on message_attachments(message_rowid);

        create table if not exists send_jobs (
            rowid integer primary key autoincrement,
            created_at integer not null,
            updated_at integer not null,
            requested_by_machine_id text not null,
            recipient_input text,
            resolved_recipient text,
            destination_chat_rowid integer,
            destination_chat_guid text,
            service_type text not null,
            message_text text not null,
            idempotency_key text,
            duplicate_key text not null,
            status text not null,
            attempt_count integer not null default 0,
            dry_run integer not null default 0,
            parent_message_rowid integer,
            parent_message_guid text,
            parent_preview text,
            provider_status text,
            provider_detail text,
            blocked_reason text,
            sent_at integer not null default 0
        );
        create unique index if not exists idx_send_jobs_idempotency
            on send_jobs(idempotency_key)
            where idempotency_key is not null and idempotency_key != '';
        create index if not exists idx_send_jobs_duplicate on send_jobs(duplicate_key, created_at desc);
        create index if not exists idx_send_jobs_status on send_jobs(status, created_at desc);
        """
    )
    ensure_index_schema_migrations(con)
    con.commit()


def ensure_column_exists(
    con: sqlite3.Connection,
    table_name: str,
    column_name: str,
    column_sql: str,
) -> None:
    rows = con.execute(f"pragma table_info({table_name})").fetchall()
    existing_columns = {str(row["name"]).lower() for row in rows}
    if column_name.lower() not in existing_columns:
        con.execute(f"alter table {table_name} add column {column_name} {column_sql}")


def ensure_index_schema_migrations(con: sqlite3.Connection) -> None:
    ensure_column_exists(con, "handles", "contact_name", "text not null default ''")
    con.execute("create index if not exists idx_handles_contact_name on handles(contact_name)")


def source_latest_message_rowid(source: sqlite3.Connection) -> int:
    row = source.execute("select coalesce(max(ROWID), 0) as value from message").fetchone()
    return int(row["value"] or 0)


def source_latest_message_date(source: sqlite3.Connection) -> int:
    row = source.execute("select coalesce(max(date), 0) as value from message").fetchone()
    return int(row["value"] or 0)


def meta_get(con: sqlite3.Connection, key: str, default: str = "") -> str:
    row = con.execute("select value from meta where key = ?", (key,)).fetchone()
    if row is None:
        return default
    return str(row["value"])


def meta_set(con: sqlite3.Connection, key: str, value: str) -> None:
    con.execute(
        """
        insert into meta (key, value)
        values (?, ?)
        on conflict(key) do update set value = excluded.value
        """,
        (key, value),
    )


def requesting_machine_id(cfg: Config) -> str:
    raw_value = os.environ.get("IMSG_REQUESTING_MACHINE_ID", "")
    return normalize_machine_id(raw_value) or cfg.machine_id


def normalize_phone_like(value: str) -> str:
    digits = "".join(character for character in str(value) if character.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def default_addressbook_db() -> Path | None:
    path = Path.home() / "Library/Application Support/AddressBook/AddressBook-v22.abcddb"
    if path.exists():
        return path
    return None


def contact_display_name(row: sqlite3.Row | dict[str, Any]) -> str:
    first_name = str(row_value(row, "first_name", "") or "").strip()
    last_name = str(row_value(row, "last_name", "") or "").strip()
    combined = " ".join(part for part in (first_name, last_name) if part).strip()
    if combined:
        return combined
    for key in ("full_name", "organization", "nickname"):
        value = str(row_value(row, key, "") or "").strip()
        if value:
            return value
    return ""


def load_addressbook_contact_maps() -> tuple[dict[str, str], dict[str, str]]:
    path = default_addressbook_db()
    if path is None:
        return {}, {}

    try:
        with sqlite_connect_ro(path) as con:
            phone_rows = con.execute(
                """
                select
                    p.ZFULLNUMBER as value,
                    p.ZISPRIMARY as is_primary,
                    p.ZORDERINGINDEX as ordering_index,
                    r.ZFIRSTNAME as first_name,
                    r.ZLASTNAME as last_name,
                    r.ZNAME as full_name,
                    r.ZORGANIZATION as organization,
                    r.ZNICKNAME as nickname
                from ZABCDPHONENUMBER p
                left join ZABCDRECORD r on r.Z_PK = coalesce(p.ZOWNER, p.Z22_OWNER)
                where p.ZFULLNUMBER is not null and p.ZFULLNUMBER != ''
                order by p.ZISPRIMARY desc, p.ZORDERINGINDEX asc, p.Z_PK asc
                """
            ).fetchall()
            email_rows = con.execute(
                """
                select
                    lower(trim(e.ZADDRESS)) as value,
                    e.ZISPRIMARY as is_primary,
                    e.ZORDERINGINDEX as ordering_index,
                    r.ZFIRSTNAME as first_name,
                    r.ZLASTNAME as last_name,
                    r.ZNAME as full_name,
                    r.ZORGANIZATION as organization,
                    r.ZNICKNAME as nickname
                from ZABCDEMAILADDRESS e
                left join ZABCDRECORD r on r.Z_PK = coalesce(e.ZOWNER, e.Z22_OWNER)
                where e.ZADDRESS is not null and e.ZADDRESS != ''
                order by e.ZISPRIMARY desc, e.ZORDERINGINDEX asc, e.Z_PK asc
                """
            ).fetchall()
    except Exception:
        return {}, {}

    phone_map: dict[str, str] = {}
    for row in phone_rows:
        normalized = normalize_phone_like(str(row["value"]))
        display_name = contact_display_name(row)
        if normalized and display_name and normalized not in phone_map:
            phone_map[normalized] = display_name

    email_map: dict[str, str] = {}
    for row in email_rows:
        normalized = str(row["value"] or "").strip().lower()
        display_name = contact_display_name(row)
        if normalized and display_name and normalized not in email_map:
            email_map[normalized] = display_name

    return email_map, phone_map


def lookup_contact_name(
    handle_id: str,
    email_map: dict[str, str],
    phone_map: dict[str, str],
) -> str:
    normalized_handle = str(handle_id or "").strip()
    if not normalized_handle:
        return ""
    if "@" in normalized_handle:
        return email_map.get(normalized_handle.lower(), "")
    digits = normalize_phone_like(normalized_handle)
    if digits:
        return phone_map.get(digits, "")
    return ""


def enrich_handles_from_addressbook(index: sqlite3.Connection) -> None:
    email_map, phone_map = load_addressbook_contact_maps()
    if not email_map and not phone_map:
        index.execute("update handles set contact_name = ''")
        return

    rows = index.execute("select rowid, handle_id from handles").fetchall()
    updates = [
        (
            lookup_contact_name(str(row["handle_id"] or ""), email_map, phone_map),
            int(row["rowid"]),
        )
        for row in rows
    ]
    if updates:
        index.executemany(
            "update handles set contact_name = ? where rowid = ?",
            updates,
        )


def duplicate_key_for_destination(destination_key: str, message_text: str, service_type: str) -> str:
    payload = "\n".join(
        [
            destination_key.strip().lower(),
            service_type.strip().lower(),
            message_text.strip(),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_clock(value: str) -> tuple[int, int] | None:
    match = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", value or "")
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2))
    if hours > 23 or minutes > 59:
        return None
    return hours, minutes


def in_quiet_hours(cfg: Config) -> bool:
    start = parse_clock(cfg.quiet_hours_start)
    end = parse_clock(cfg.quiet_hours_end)
    if not start or not end:
        return False
    now = datetime.now().astimezone()
    current_minutes = (now.hour * 60) + now.minute
    start_minutes = (start[0] * 60) + start[1]
    end_minutes = (end[0] * 60) + end[1]
    if start_minutes == end_minutes:
        return True
    if start_minutes < end_minutes:
        return start_minutes <= current_minutes < end_minutes
    return current_minutes >= start_minutes or current_minutes < end_minutes


def recent_duplicate_job(
    con: sqlite3.Connection,
    duplicate_key: str,
    window_seconds: int,
) -> sqlite3.Row | None:
    earliest = max(0, now_utc_epoch() - window_seconds)
    return con.execute(
        """
        select *
        from send_jobs
        where duplicate_key = ?
          and status = 'sent'
          and created_at >= ?
        order by created_at desc, rowid desc
        limit 1
        """,
        (duplicate_key, earliest),
    ).fetchone()


def lookup_send_job_by_idempotency(
    con: sqlite3.Connection,
    idempotency_key: str,
) -> sqlite3.Row | None:
    if not idempotency_key:
        return None
    return con.execute(
        """
        select *
        from send_jobs
        where idempotency_key = ?
        order by rowid desc
        limit 1
        """,
        (idempotency_key,),
    ).fetchone()


def insert_send_job(
    con: sqlite3.Connection,
    *,
    requested_by_machine_id: str,
    recipient_input: str | None,
    resolved_recipient: str | None,
    destination_chat_rowid: int | None,
    destination_chat_guid: str | None,
    service_type: str,
    message_text: str,
    idempotency_key: str,
    duplicate_key: str,
    dry_run: bool,
    parent_message_rowid: int | None,
    parent_message_guid: str | None,
    parent_preview: str | None,
    status: str,
    provider_status: str | None = None,
    provider_detail: str | None = None,
    blocked_reason: str | None = None,
) -> int:
    timestamp = now_utc_epoch()
    try:
        cursor = con.execute(
            """
            insert into send_jobs (
                created_at, updated_at, requested_by_machine_id,
                recipient_input, resolved_recipient,
                destination_chat_rowid, destination_chat_guid,
                service_type, message_text, idempotency_key, duplicate_key,
                status, dry_run, parent_message_rowid, parent_message_guid, parent_preview,
                provider_status, provider_detail, blocked_reason
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                timestamp,
                requested_by_machine_id,
                recipient_input,
                resolved_recipient,
                destination_chat_rowid,
                destination_chat_guid,
                service_type,
                message_text,
                idempotency_key or None,
                duplicate_key,
                status,
                1 if dry_run else 0,
                parent_message_rowid,
                parent_message_guid,
                parent_preview,
                provider_status,
                provider_detail,
                blocked_reason,
            ),
        )
    except sqlite3.IntegrityError:
        if idempotency_key:
            existing = lookup_send_job_by_idempotency(con, idempotency_key)
            if existing is not None:
                return int(existing["rowid"])
        raise
    return int(cursor.lastrowid)


def update_send_job(
    con: sqlite3.Connection,
    job_rowid: int,
    *,
    status: str,
    provider_status: str | None = None,
    provider_detail: str | None = None,
    blocked_reason: str | None = None,
    increment_attempt: bool = False,
    sent_at: int | None = None,
) -> None:
    con.execute(
        """
        update send_jobs
        set status = ?,
            provider_status = ?,
            provider_detail = ?,
            blocked_reason = ?,
            updated_at = ?,
            attempt_count = attempt_count + ?,
            sent_at = case when ? > 0 then ? else sent_at end
        where rowid = ?
        """,
        (
            status,
            provider_status,
            provider_detail,
            blocked_reason,
            now_utc_epoch(),
            1 if increment_attempt else 0,
            sent_at or 0,
            sent_at or 0,
            job_rowid,
        ),
    )


def format_send_job(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "job_rowid": int(row["rowid"]),
        "created_at": datetime.fromtimestamp(int(row["created_at"] or 0), tz=timezone.utc).isoformat()
        if int(row["created_at"] or 0) > 0
        else None,
        "updated_at": datetime.fromtimestamp(int(row["updated_at"] or 0), tz=timezone.utc).isoformat()
        if int(row["updated_at"] or 0) > 0
        else None,
        "sent_at": datetime.fromtimestamp(int(row["sent_at"] or 0), tz=timezone.utc).isoformat()
        if int(row["sent_at"] or 0) > 0
        else None,
        "requested_by_machine_id": row["requested_by_machine_id"],
        "recipient_input": row["recipient_input"],
        "resolved_recipient": row["resolved_recipient"],
        "destination_chat_rowid": int(row["destination_chat_rowid"]) if row["destination_chat_rowid"] not in (None, "") else None,
        "destination_chat_guid": row["destination_chat_guid"],
        "service_type": row["service_type"],
        "message_text": row["message_text"],
        "idempotency_key": row["idempotency_key"] or "",
        "status": row["status"],
        "attempt_count": int(row["attempt_count"] or 0),
        "dry_run": bool(int(row["dry_run"] or 0)),
        "provider_status": row["provider_status"] or "",
        "provider_detail": row["provider_detail"] or "",
        "blocked_reason": row["blocked_reason"] or "",
        "parent_message_rowid": int(row["parent_message_rowid"]) if row["parent_message_rowid"] not in (None, "") else None,
        "parent_message_guid": row["parent_message_guid"] or "",
        "parent_preview": row["parent_preview"] or "",
    }


def exact_handle_match(con: sqlite3.Connection, recipient: str) -> sqlite3.Row | None:
    lowered = recipient.strip().lower()
    row = con.execute(
        """
        select *
        from handles
        where lower(handle_id) = ?
           or lower(coalesce(contact_name, '')) = ?
        order by last_message_date desc, rowid desc
        limit 1
        """,
        (lowered, lowered),
    ).fetchone()
    if row is not None:
        return row
    digits = normalize_phone_like(recipient)
    if not digits:
        return None
    rows = con.execute(
        """
        select *
        from handles
        where handle_id like ?
        order by last_message_date desc, rowid desc
        limit 20
        """,
        (f"%{digits}%",),
    ).fetchall()
    matches = [row for row in rows if normalize_phone_like(row["handle_id"]) == digits]
    if len(matches) == 1:
        return matches[0]
    return None


def chats_for_handle(con: sqlite3.Connection, handle_rowid: int) -> list[sqlite3.Row]:
    return con.execute(
        """
        select c.*
        from chats c
        join chat_handles ch on ch.chat_rowid = c.rowid
        where ch.handle_rowid = ?
        order by c.last_message_date desc, c.rowid desc
        """,
        (handle_rowid,),
    ).fetchall()


def direct_recipient_for_chat(
    con: sqlite3.Connection,
    chat_row: sqlite3.Row,
) -> str | None:
    rows = con.execute(
        """
        select distinct h.handle_id
        from handles h
        join chat_handles ch on ch.handle_rowid = h.rowid
        where ch.chat_rowid = ?
          and coalesce(h.handle_id, '') <> ''
        order by h.rowid
        """,
        (int(chat_row["rowid"]),),
    ).fetchall()
    handles = [str(row["handle_id"]).strip() for row in rows if str(row["handle_id"]).strip()]
    if len(handles) == 1:
        return handles[0]
    guid = row_value(chat_row, "guid", "").strip()
    if guid.startswith("any;") and ";" in guid:
        candidate = guid.rsplit(";", 1)[-1].strip()
        if candidate and candidate != guid:
            return candidate
    return None


def resolve_send_target(
    con: sqlite3.Connection,
    *,
    recipient_input: str | None,
    chat_query: str | None,
) -> dict[str, Any]:
    if chat_query:
        chat_row = resolve_single_chat(con, chat_query)
        direct_recipient = direct_recipient_for_chat(con, chat_row)
        return {
            "mode": "chat",
            "recipient_input": recipient_input or "",
            "resolved_recipient": direct_recipient or chat_title(chat_row),
            "chat_rowid": int(chat_row["rowid"]),
            "chat_guid": chat_row["guid"],
            "chat_title": chat_title(chat_row),
            "participant_summary": row_value(chat_row, "participant_summary", "") or "",
            "known_contact": True,
            "ambiguous_candidates": [],
            "direct_recipient": direct_recipient,
        }

    if not recipient_input:
        raise SystemExit("A recipient or chat is required.")

    exact = exact_handle_match(con, recipient_input)
    if exact is not None:
        related_chats = chats_for_handle(con, int(exact["rowid"]))
        chat_row = related_chats[0] if related_chats else None
        return {
            "mode": "handle",
            "recipient_input": recipient_input,
            "resolved_recipient": exact["handle_id"],
            "chat_rowid": int(chat_row["rowid"]) if chat_row is not None else None,
            "chat_guid": chat_row["guid"] if chat_row is not None else None,
            "chat_title": chat_title(chat_row) if chat_row is not None else exact["handle_id"],
            "participant_summary": row_value(chat_row, "participant_summary", "") if chat_row is not None else exact["handle_id"],
            "known_contact": int(exact["message_count"] or 0) > 0,
            "ambiguous_candidates": [],
            "direct_recipient": exact["handle_id"],
        }

    candidates = query_contacts(con, recipient_input, 5)
    if len(candidates) > 1:
        return {
            "mode": "ambiguous",
            "recipient_input": recipient_input,
            "resolved_recipient": "",
            "chat_rowid": None,
            "chat_guid": None,
            "chat_title": "",
            "participant_summary": "",
            "known_contact": False,
            "ambiguous_candidates": candidates,
            "direct_recipient": None,
        }
    if len(candidates) == 1:
        resolved = candidates[0]["handle_id"]
        exact = exact_handle_match(con, resolved)
        if exact is not None:
            related_chats = chats_for_handle(con, int(exact["rowid"]))
            chat_row = related_chats[0] if related_chats else None
            return {
                "mode": "handle",
                "recipient_input": recipient_input,
                "resolved_recipient": resolved,
                "chat_rowid": int(chat_row["rowid"]) if chat_row is not None else None,
                "chat_guid": chat_row["guid"] if chat_row is not None else None,
                "chat_title": chat_title(chat_row) if chat_row is not None else resolved,
                "participant_summary": row_value(chat_row, "participant_summary", "") if chat_row is not None else resolved,
                "known_contact": int(exact["message_count"] or 0) > 0,
                "ambiguous_candidates": [],
                "direct_recipient": resolved,
            }

    return {
        "mode": "raw",
        "recipient_input": recipient_input,
        "resolved_recipient": recipient_input,
        "chat_rowid": None,
        "chat_guid": None,
        "chat_title": recipient_input,
        "participant_summary": recipient_input,
        "known_contact": False,
        "ambiguous_candidates": [],
        "direct_recipient": recipient_input,
    }


def refresh_handles(source: sqlite3.Connection, index: sqlite3.Connection) -> None:
    rows = source.execute(
        """
        select ROWID, id, country, service, uncanonicalized_id, person_centric_id
        from handle
        """
    ).fetchall()
    index.execute("delete from handles")
    index.executemany(
        """
        insert into handles (
            rowid, handle_id, country, service, uncanonicalized_id, person_centric_id
        ) values (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                int(row["ROWID"]),
                row["id"],
                row["country"],
                row["service"],
                row["uncanonicalized_id"],
                row["person_centric_id"],
            )
            for row in rows
        ],
    )


def refresh_chats(source: sqlite3.Connection, index: sqlite3.Connection) -> None:
    rows = source.execute(
        """
        select
            ROWID, guid, chat_identifier, service_name, room_name, display_name,
            account_login, account_id, last_addressed_handle,
            coalesce(last_read_message_timestamp, 0) as last_read_message_timestamp,
            coalesce(style, 0) as style,
            coalesce(is_archived, 0) as is_archived
        from chat
        """
    ).fetchall()
    index.execute("delete from chats")
    index.executemany(
        """
        insert into chats (
            rowid, guid, chat_identifier, service_name, room_name, display_name,
            account_login, account_id, last_addressed_handle,
            last_read_message_timestamp, style, is_archived
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                int(row["ROWID"]),
                row["guid"],
                row["chat_identifier"],
                row["service_name"],
                row["room_name"],
                row["display_name"],
                row["account_login"],
                row["account_id"],
                row["last_addressed_handle"],
                int(row["last_read_message_timestamp"] or 0),
                int(row["style"] or 0),
                int(row["is_archived"] or 0),
            )
            for row in rows
        ],
    )


def refresh_chat_handles(source: sqlite3.Connection, index: sqlite3.Connection) -> None:
    rows = source.execute(
        "select chat_id, handle_id from chat_handle_join"
    ).fetchall()
    index.execute("delete from chat_handles")
    index.executemany(
        "insert into chat_handles (chat_rowid, handle_rowid) values (?, ?)",
        [(int(row["chat_id"]), int(row["handle_id"])) for row in rows],
    )


def attachment_path_exists(attachments_root: Path | None, raw_filename: str | None) -> int:
    if attachments_root is None or raw_filename in (None, ""):
        return 0
    filename = str(raw_filename)
    if filename.startswith("file://"):
        candidate = Path(filename.removeprefix("file://"))
    else:
        candidate = Path(os.path.expandvars(filename)).expanduser()
    if not candidate.is_absolute():
        candidate = attachments_root / candidate
    return 1 if candidate.exists() else 0


def refresh_messages_and_attachments(
    source: sqlite3.Connection,
    index: sqlite3.Connection,
    attachments_root: Path | None,
    anchor_rowid: int,
) -> dict[str, int]:
    message_rows = source.execute(
        """
        select
            ROWID, guid, text, subject, attributedBody, handle_id, service, account,
            coalesce(date, 0) as date,
            coalesce(date_read, 0) as date_read,
            coalesce(date_delivered, 0) as date_delivered,
            coalesce(is_delivered, 0) as is_delivered,
            coalesce(is_finished, 0) as is_finished,
            coalesce(is_from_me, 0) as is_from_me,
            coalesce(is_read, 0) as is_read,
            coalesce(is_system_message, 0) as is_system_message,
            coalesce(is_sent, 0) as is_sent,
            coalesce(cache_has_attachments, 0) as cache_has_attachments,
            associated_message_guid,
            coalesce(associated_message_type, 0) as associated_message_type,
            associated_message_emoji,
            reply_to_guid,
            thread_originator_guid,
            thread_originator_part,
            coalesce(date_edited, 0) as date_edited,
            coalesce(date_retracted, 0) as date_retracted,
            expressive_send_style_id,
            coalesce(item_type, 0) as item_type,
            coalesce(group_action_type, 0) as group_action_type,
            coalesce(message_action_type, 0) as message_action_type
        from message
        where ROWID >= ?
        order by ROWID
        """,
        (anchor_rowid,),
    ).fetchall()

    index.execute("delete from chat_messages where message_rowid >= ?", (anchor_rowid,))
    index.execute("delete from message_attachments where message_rowid >= ?", (anchor_rowid,))

    index.executemany(
        """
        insert into messages (
            rowid, guid, text, subject, handle_rowid, service, account,
            date, date_read, date_delivered, is_delivered, is_finished,
            is_from_me, is_read, is_system_message, is_sent, has_attachments,
            associated_message_guid, associated_message_guid_normalized,
            associated_message_type, associated_message_emoji,
            reply_to_guid, thread_originator_guid, thread_originator_part,
            date_edited, date_retracted, expressive_send_style_id,
            item_type, group_action_type, message_action_type
        ) values (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        on conflict(rowid) do update set
            guid = excluded.guid,
            text = excluded.text,
            subject = excluded.subject,
            handle_rowid = excluded.handle_rowid,
            service = excluded.service,
            account = excluded.account,
            date = excluded.date,
            date_read = excluded.date_read,
            date_delivered = excluded.date_delivered,
            is_delivered = excluded.is_delivered,
            is_finished = excluded.is_finished,
            is_from_me = excluded.is_from_me,
            is_read = excluded.is_read,
            is_system_message = excluded.is_system_message,
            is_sent = excluded.is_sent,
            has_attachments = excluded.has_attachments,
            associated_message_guid = excluded.associated_message_guid,
            associated_message_guid_normalized = excluded.associated_message_guid_normalized,
            associated_message_type = excluded.associated_message_type,
            associated_message_emoji = excluded.associated_message_emoji,
            reply_to_guid = excluded.reply_to_guid,
            thread_originator_guid = excluded.thread_originator_guid,
            thread_originator_part = excluded.thread_originator_part,
            date_edited = excluded.date_edited,
            date_retracted = excluded.date_retracted,
            expressive_send_style_id = excluded.expressive_send_style_id,
            item_type = excluded.item_type,
            group_action_type = excluded.group_action_type,
            message_action_type = excluded.message_action_type
        """,
        [
            (
                int(row["ROWID"]),
                row["guid"],
                row["text"] or extract_attributed_body_text(row["attributedBody"]),
                row["subject"],
                int(row["handle_id"]) if row["handle_id"] not in (None, "") else None,
                row["service"],
                row["account"],
                int(row["date"] or 0),
                int(row["date_read"] or 0),
                int(row["date_delivered"] or 0),
                int(row["is_delivered"] or 0),
                int(row["is_finished"] or 0),
                int(row["is_from_me"] or 0),
                int(row["is_read"] or 0),
                int(row["is_system_message"] or 0),
                int(row["is_sent"] or 0),
                int(row["cache_has_attachments"] or 0),
                row["associated_message_guid"],
                normalize_guid_reference(row["associated_message_guid"]),
                int(row["associated_message_type"] or 0),
                row["associated_message_emoji"],
                normalize_guid_reference(row["reply_to_guid"]),
                normalize_guid_reference(row["thread_originator_guid"]),
                row["thread_originator_part"],
                int(row["date_edited"] or 0),
                int(row["date_retracted"] or 0),
                row["expressive_send_style_id"],
                int(row["item_type"] or 0),
                int(row["group_action_type"] or 0),
                int(row["message_action_type"] or 0),
            )
            for row in message_rows
        ],
    )

    chat_message_rows = source.execute(
        """
        select chat_id, message_id, coalesce(message_date, 0) as message_date
        from chat_message_join
        where message_id >= ?
        """,
        (anchor_rowid,),
    ).fetchall()
    index.executemany(
        """
        insert into chat_messages (chat_rowid, message_rowid, message_date)
        values (?, ?, ?)
        """,
        [
            (
                int(row["chat_id"]),
                int(row["message_id"]),
                int(row["message_date"] or 0),
            )
            for row in chat_message_rows
        ],
    )

    attachment_rows = source.execute(
        """
        select
            maj.message_id,
            a.ROWID as attachment_rowid,
            a.guid,
            a.filename,
            a.mime_type,
            a.uti,
            a.transfer_name,
            coalesce(a.total_bytes, 0) as total_bytes,
            coalesce(a.is_sticker, 0) as is_sticker,
            coalesce(a.created_date, 0) as created_date
        from message_attachment_join maj
        join attachment a on a.ROWID = maj.attachment_id
        where maj.message_id >= ?
        """,
        (anchor_rowid,),
    ).fetchall()
    unique_attachments: dict[int, tuple[Any, ...]] = {}
    message_attachments: list[tuple[int, int]] = []
    for row in attachment_rows:
        attachment_rowid = int(row["attachment_rowid"])
        unique_attachments[attachment_rowid] = (
            attachment_rowid,
            row["guid"],
            row["filename"],
            row["mime_type"],
            row["uti"],
            row["transfer_name"],
            int(row["total_bytes"] or 0),
            int(row["is_sticker"] or 0),
            int(row["created_date"] or 0),
            attachment_path_exists(attachments_root, row["filename"]),
        )
        message_attachments.append((int(row["message_id"]), attachment_rowid))

    if unique_attachments:
        index.executemany(
            """
            insert into attachments (
                rowid, guid, filename, mime_type, uti, transfer_name,
                total_bytes, is_sticker, created_date, path_exists
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            on conflict(rowid) do update set
                guid = excluded.guid,
                filename = excluded.filename,
                mime_type = excluded.mime_type,
                uti = excluded.uti,
                transfer_name = excluded.transfer_name,
                total_bytes = excluded.total_bytes,
                is_sticker = excluded.is_sticker,
                created_date = excluded.created_date,
                path_exists = excluded.path_exists
            """,
            list(unique_attachments.values()),
        )
    if message_attachments:
        index.executemany(
            """
            insert into message_attachments (message_rowid, attachment_rowid)
            values (?, ?)
            """,
            message_attachments,
        )

    return {
        "messages_refreshed": len(message_rows),
        "chat_message_joins_refreshed": len(chat_message_rows),
        "attachments_refreshed": len(unique_attachments),
    }


def refresh_derived_fields(index: sqlite3.Connection) -> None:
    index.execute(
        """
        update handles set
            message_count = (
                select count(*)
                from messages m
                where m.handle_rowid = handles.rowid
            ),
            last_message_date = coalesce((
                select max(date)
                from messages m
                where m.handle_rowid = handles.rowid
            ), 0)
        """
    )
    index.execute(
        """
        update chats set
            participant_summary = coalesce((
                select group_concat(h.handle_id, ', ')
                from (
                    select distinct coalesce(nullif(h.contact_name, ''), h.handle_id) as handle_id
                    from chat_handles ch
                    join handles h on h.rowid = ch.handle_rowid
                    where ch.chat_rowid = chats.rowid
                    order by handle_id
                ) h
            ), ''),
            participant_count = coalesce((
                select count(*)
                from chat_handles ch
                where ch.chat_rowid = chats.rowid
            ), 0),
            message_count = coalesce((
                select count(*)
                from chat_messages cm
                where cm.chat_rowid = chats.rowid
            ), 0),
            last_message_rowid = (
                select max(cm.message_rowid)
                from chat_messages cm
                where cm.chat_rowid = chats.rowid
            ),
            last_message_date = coalesce((
                select max(cm.message_date)
                from chat_messages cm
                where cm.chat_rowid = chats.rowid
            ), 0),
            unread_count = coalesce((
                select count(*)
                from chat_messages cm
                join messages m on m.rowid = cm.message_rowid
                where cm.chat_rowid = chats.rowid
                  and m.is_from_me = 0
                  and m.date > coalesce(chats.last_read_message_timestamp, 0)
            ), 0)
        """
    )


def sync_index(
    cfg: Config,
    rebuild: bool = False,
    quiet: bool = False,
    *,
    nonblocking: bool = False,
) -> dict[str, Any]:
    if cfg.chat_db is None:
        raise SystemExit("IMSG_CHAT_DB is not configured on this machine.")
    if not cfg.chat_db.exists():
        raise SystemExit(f"Messages database does not exist: {cfg.chat_db}")

    cfg.state_root.mkdir(parents=True, exist_ok=True)
    state_dir = cfg.index_db.parent
    state_dir.mkdir(parents=True, exist_ok=True)

    with exclusive_lock(
        state_lock_path(cfg, DEFAULT_SYNC_LOCK_NAME),
        blocking=not nonblocking,
    ):
        with sqlite_connect_ro(cfg.chat_db) as source:
            with sqlite_connect_rw(cfg.index_db) as index:
                initialize_index_schema(index)
                if rebuild:
                    index.executescript(
                        """
                        delete from chat_messages;
                        delete from message_attachments;
                        delete from attachments;
                        delete from messages;
                        delete from chat_handles;
                        delete from chats;
                        delete from handles;
                        """
                    )
                    meta_set(index, "last_message_rowid", "0")

                source_rowid = source_latest_message_rowid(source)
                source_date = source_latest_message_date(source)
                previous_rowid = int(meta_get(index, "last_message_rowid", "0") or "0")
                anchor_rowid = 1 if rebuild else max(1, previous_rowid - cfg.sync_backfill_rows)

                started_at = datetime.now(timezone.utc).isoformat()

                refresh_handles(source, index)
                enrich_handles_from_addressbook(index)
                refresh_chats(source, index)
                refresh_chat_handles(source, index)
                message_summary = refresh_messages_and_attachments(
                    source,
                    index,
                    cfg.attachments_root,
                    anchor_rowid,
                )
                refresh_derived_fields(index)

                meta_set(index, "last_message_rowid", str(source_rowid))
                meta_set(index, "last_source_message_date", str(source_date))
                meta_set(index, "last_sync_started_at", started_at)
                meta_set(index, "last_sync_completed_at", datetime.now(timezone.utc).isoformat())
                meta_set(index, "chat_db_path", str(cfg.chat_db))
                meta_set(index, "account_hint", cfg.account_hint)
                meta_set(index, "phone_account_hint", cfg.phone_account_hint)
                index.commit()

    summary = {
        "chat_db": str(cfg.chat_db),
        "index_db": str(cfg.index_db),
        "source_latest_message_rowid": source_rowid,
        "source_latest_message_at": apple_ns_to_iso(source_date),
        "anchor_rowid": anchor_rowid,
        "rebuild": rebuild,
        **message_summary,
    }
    if not quiet:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def sync_index_safe(
    cfg: Config,
    *,
    rebuild: bool = False,
    quiet: bool = False,
    nonblocking: bool = False,
) -> dict[str, Any] | None:
    try:
        return sync_index(
            cfg,
            rebuild=rebuild,
            quiet=quiet,
            nonblocking=nonblocking,
        )
    except LockBusyError:
        return None
    except sqlite3.OperationalError as exc:
        if "database is locked" in str(exc).lower():
            return None
        raise


def local_execable_exists(path_string: str) -> bool:
    expanded = Path(os.path.expandvars(path_string)).expanduser()
    return expanded.exists() and os.access(expanded, os.X_OK)


def build_ssh_command(cfg: Config, remote_args: list[str]) -> list[str]:
    command = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "PubkeyAuthentication=yes",
        "-o",
        "PasswordAuthentication=no",
        "-o",
        "KbdInteractiveAuthentication=no",
        "-o",
        "PreferredAuthentications=publickey",
        "-o",
        "StrictHostKeyChecking=yes",
        "-o",
        "IdentitiesOnly=yes",
        "-o",
        "ForwardAgent=no",
        "-o",
        "ClearAllForwardings=yes",
    ]
    if cfg.server_ssh_identity_file:
        identity_path = Path(os.path.expandvars(cfg.server_ssh_identity_file)).expanduser()
        if identity_path.exists():
            command.extend(["-i", str(identity_path)])
    remote_parts = [cfg.remote_command, *remote_args]
    rendered_parts: list[str] = []
    for index, part in enumerate(remote_parts):
        if index == 0 and part.startswith("~/"):
            rendered_parts.append(f"$HOME/{shlex.quote(part[2:])}")
            continue
        rendered_parts.append(shlex.quote(part))
    remote_command = " ".join(rendered_parts)
    command.extend(
        [
            cfg.server_ssh_dest,
            f"IMSG_REQUESTING_MACHINE_ID={shlex.quote(cfg.machine_id)} {remote_command}",
        ]
    )
    return command


def forward_client_to_server(cfg: Config, argv: list[str]) -> int:
    command = build_ssh_command(cfg, argv)
    completed = subprocess.run(command)
    return int(completed.returncode)


def open_index_for_query(cfg: Config, sync_first: bool) -> sqlite3.Connection:
    if sync_first:
        sync_index_safe(cfg, quiet=True, nonblocking=True)
    if not cfg.index_db.exists():
        raise SystemExit(f"Index database does not exist: {cfg.index_db}. Run imsgd sync first.")
    con = sqlite_connect_ro(cfg.index_db)
    return con


def reaction_label(associated_type: int, emoji: str | None) -> str | None:
    if associated_type == 0:
        return None
    if emoji not in (None, ""):
        return str(emoji)
    return REACTION_LABELS.get(associated_type, f"reaction_{associated_type}")


def is_threaded_reply(row: sqlite3.Row | dict[str, Any]) -> bool:
    return bool(
        normalize_guid_reference(row_value(row, "thread_originator_guid"))
        or row_value(row, "thread_originator_part")
    )


def message_kind(row: sqlite3.Row | dict[str, Any]) -> str:
    associated_type = int(row_value(row, "associated_message_type", 0) or 0)
    if associated_type != 0:
        return "reaction"
    if is_threaded_reply(row):
        return "reply"
    if int(row_value(row, "date_retracted", 0) or 0) > 0:
        return "retracted"
    if (
        int(row_value(row, "is_system_message", 0) or 0)
        or int(row_value(row, "group_action_type", 0) or 0)
        or int(row_value(row, "message_action_type", 0) or 0)
    ):
        return "system"
    return "message"


def message_preview(row: sqlite3.Row | dict[str, Any]) -> str:
    text = compact_text(row_value(row, "text") or row_value(row, "subject") or "")
    if text:
        return text
    associated_type = int(row_value(row, "associated_message_type", 0) or 0)
    if associated_type != 0:
        label = reaction_label(associated_type, row_value(row, "associated_message_emoji"))
        return f"[{label}]"
    if int(row_value(row, "has_attachments", 0) or 0):
        return "[attachment]"
    if int(row_value(row, "date_retracted", 0) or 0) > 0:
        return "[retracted]"
    if int(row_value(row, "date_edited", 0) or 0) > 0:
        return "[edited]"
    if (
        int(row_value(row, "is_system_message", 0) or 0)
        or int(row_value(row, "group_action_type", 0) or 0)
        or int(row_value(row, "message_action_type", 0) or 0)
    ):
        return "[system]"
    return "[empty]"


def message_preview_rank(preview: str) -> int:
    if preview == "[empty]":
        return 0
    if preview in {"[system]", "[edited]", "[retracted]"}:
        return 1
    if preview in {"[attachment]"} or preview.startswith("[") and preview.endswith("]"):
        return 2
    return 3


def best_chat_preview(rows: list[sqlite3.Row]) -> str:
    best_preview = "[empty]"
    best_rank = -1
    for row in rows:
        preview = message_preview(row)
        rank = message_preview_rank(preview)
        if rank > best_rank:
            best_preview = preview
            best_rank = rank
            if rank >= 3:
                break
    return best_preview


def chat_title(row: sqlite3.Row | dict[str, Any]) -> str:
    for key in (
        "display_name",
        "room_name",
        "participant_summary",
        "last_addressed_handle",
        "chat_identifier",
        "guid",
    ):
        value = row_value(row, key)
        if value not in (None, ""):
            return str(value)
    return "untitled-chat"


def resolve_chat_rows(
    con: sqlite3.Connection,
    chat_query: str,
    limit: int = 20,
) -> list[sqlite3.Row]:
    query = chat_query.strip()
    exact_numeric = query.isdigit()
    pattern = f"%{query.lower()}%"
    sql = """
        select
            c.*,
            coalesce(c.display_name, '') as display_name_norm,
            coalesce(c.chat_identifier, '') as chat_identifier_norm,
            coalesce(c.participant_summary, '') as participant_summary_norm
        from chats c
        where
            (? = 1 and c.rowid = ?)
            or lower(c.guid) = lower(?)
            or lower(coalesce(c.display_name, '')) = lower(?)
            or lower(coalesce(c.chat_identifier, '')) = lower(?)
            or lower(coalesce(c.participant_summary, '')) = lower(?)
            or lower(coalesce(c.display_name, '')) like ?
            or lower(coalesce(c.chat_identifier, '')) like ?
            or lower(coalesce(c.participant_summary, '')) like ?
            or lower(coalesce(c.guid, '')) like ?
        order by
            case
                when (? = 1 and c.rowid = ?) then 0
                when lower(c.guid) = lower(?) then 1
                when lower(coalesce(c.display_name, '')) = lower(?) then 2
                when lower(coalesce(c.chat_identifier, '')) = lower(?) then 3
                when lower(coalesce(c.participant_summary, '')) = lower(?) then 4
                else 10
            end,
            c.unread_count desc,
            c.last_message_date desc
        limit ?
    """
    return con.execute(
        sql,
        (
            1 if exact_numeric else 0,
            int(query) if exact_numeric else -1,
            query,
            query,
            query,
            query,
            pattern,
            pattern,
            pattern,
            pattern,
            1 if exact_numeric else 0,
            int(query) if exact_numeric else -1,
            query,
            query,
            query,
            query,
            limit,
        ),
    ).fetchall()


def resolve_single_chat(con: sqlite3.Connection, chat_query: str) -> sqlite3.Row:
    rows = resolve_chat_rows(con, chat_query, limit=10)
    if not rows:
        raise SystemExit(f"No chat matched: {chat_query}")
    if chat_query.strip().isdigit():
        target_rowid = int(chat_query.strip())
        for row in rows:
            if int(row["rowid"]) == target_rowid:
                return row
    if len(rows) > 1:
        first = rows[0]
        if chat_title(first).lower() == chat_query.lower() or str(first["guid"]).lower() == chat_query.lower():
            return first
        lines = ["Multiple chats matched. Use a more specific query or a numeric chat id:"]
        for row in rows:
            lines.append(
                f"- {row['rowid']}: {chat_title(row)} | participants={row['participant_summary'] or 'n/a'}"
            )
        raise SystemExit("\n".join(lines))
    return rows[0]


def attachment_map_for_messages(con: sqlite3.Connection, message_ids: list[int]) -> dict[int, list[dict[str, Any]]]:
    if not message_ids:
        return {}
    placeholders = ",".join("?" for _ in message_ids)
    rows = con.execute(
        f"""
        select
            ma.message_rowid,
            a.rowid as attachment_rowid,
            a.guid,
            a.filename,
            a.mime_type,
            a.transfer_name,
            a.total_bytes,
            a.path_exists
        from message_attachments ma
        join attachments a on a.rowid = ma.attachment_rowid
        where ma.message_rowid in ({placeholders})
        order by ma.message_rowid, a.rowid
        """,
        tuple(message_ids),
    ).fetchall()
    result: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        result.setdefault(int(row["message_rowid"]), []).append(
            {
                "attachment_rowid": int(row["attachment_rowid"]),
                "guid": row["guid"],
                "filename": row["filename"],
                "mime_type": row["mime_type"],
                "transfer_name": row["transfer_name"],
                "total_bytes": int(row["total_bytes"] or 0),
                "path_exists": int(row["path_exists"] or 0),
            }
        )
    return result


def query_contacts(con: sqlite3.Connection, query: str | None, limit: int) -> list[dict[str, Any]]:
    if query:
        pattern = f"%{query.lower()}%"
        rows = con.execute(
            """
            select
                h.rowid,
                h.handle_id,
                h.contact_name,
                h.service,
                h.uncanonicalized_id,
                h.person_centric_id,
                h.message_count,
                h.last_message_date
            from handles h
            where
                lower(h.handle_id) like ?
                or lower(coalesce(h.contact_name, '')) like ?
                or lower(coalesce(h.uncanonicalized_id, '')) like ?
                or lower(coalesce(h.person_centric_id, '')) like ?
            order by h.last_message_date desc, h.message_count desc, lower(coalesce(h.contact_name, h.handle_id)) asc
            limit ?
            """,
            (pattern, pattern, pattern, pattern, limit),
        ).fetchall()
    else:
        rows = con.execute(
            """
            select
                h.rowid,
                h.handle_id,
                h.contact_name,
                h.service,
                h.uncanonicalized_id,
                h.person_centric_id,
                h.message_count,
                h.last_message_date
            from handles h
            order by h.last_message_date desc, h.message_count desc, lower(coalesce(h.contact_name, h.handle_id)) asc
            limit ?
            """,
            (limit,),
        ).fetchall()
    return [
        {
            "handle_rowid": int(row["rowid"]),
            "handle_id": row["handle_id"],
            "contact_name": row["contact_name"] or "",
            "display_name": row["contact_name"] or row["handle_id"],
            "service": row["service"],
            "uncanonicalized_id": row["uncanonicalized_id"],
            "person_centric_id": row["person_centric_id"],
            "message_count": int(row["message_count"] or 0),
            "last_message_at": apple_ns_to_iso(row["last_message_date"]),
        }
        for row in rows
    ]


def query_chats(con: sqlite3.Connection, query: str | None, limit: int, unread_only: bool) -> list[dict[str, Any]]:
    where_sql = ""
    params: list[Any] = []
    if unread_only:
        where_sql = "where c.unread_count > 0"
    if query:
        pattern = f"%{query.lower()}%"
        clause = """
            lower(coalesce(c.display_name, '')) like ?
            or lower(coalesce(c.chat_identifier, '')) like ?
            or lower(coalesce(c.participant_summary, '')) like ?
            or lower(coalesce(c.guid, '')) like ?
        """
        if where_sql:
            where_sql += f" and ({clause})"
        else:
            where_sql = f"where ({clause})"
        params.extend([pattern, pattern, pattern, pattern])
    params.append(limit)
    rows = con.execute(
        f"""
        select c.*
        from chats c
        {where_sql}
        order by c.last_message_date desc, c.unread_count desc, c.rowid desc
        limit ?
        """,
        tuple(params),
    ).fetchall()
    if not rows:
        return []
    chat_ids = [int(row["rowid"]) for row in rows]
    preview_rows_by_chat: dict[int, list[sqlite3.Row]] = {}
    if chat_ids:
        placeholders = ",".join("?" for _ in chat_ids)
        preview_rows = con.execute(
            f"""
            with ranked as (
                select
                    cm.chat_rowid,
                    m.rowid,
                    m.text,
                    m.subject,
                    m.has_attachments,
                    m.associated_message_type,
                    m.associated_message_emoji,
                    m.date_edited,
                    m.date_retracted,
                    m.is_system_message,
                    m.group_action_type,
                    m.message_action_type,
                    row_number() over (
                        partition by cm.chat_rowid
                        order by m.date desc, m.rowid desc
                    ) as rank_in_chat
                from chat_messages cm
                join messages m on m.rowid = cm.message_rowid
                where cm.chat_rowid in ({placeholders})
            )
            select *
            from ranked
            where rank_in_chat <= 8
            order by chat_rowid, rank_in_chat asc
            """,
            tuple(chat_ids),
        ).fetchall()
        for row in preview_rows:
            preview_rows_by_chat.setdefault(int(row["chat_rowid"]), []).append(row)

    result = []
    for row in rows:
        chat_rowid = int(row["rowid"])
        last_rowid = int(row["last_message_rowid"] or 0)
        result.append(
            {
                "chat_rowid": chat_rowid,
                "guid": row["guid"],
                "title": chat_title(row),
                "participants": row["participant_summary"] or "",
                "service_name": row["service_name"],
                "account_login": row["account_login"],
                "message_count": int(row["message_count"] or 0),
                "unread_count": int(row["unread_count"] or 0),
                "last_message_rowid": last_rowid or None,
                "last_message_at": apple_ns_to_iso(row["last_message_date"]),
                "last_message_preview": best_chat_preview(preview_rows_by_chat.get(chat_rowid, [])),
            }
        )
    return result


def chat_payload_from_row(con: sqlite3.Connection, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    last_rowid = int(row_value(row, "last_message_rowid", 0) or 0)
    preview_row: sqlite3.Row | dict[str, Any] = {}
    if last_rowid:
        fetched = con.execute(
            """
            select rowid, text, subject, has_attachments, associated_message_type,
                   associated_message_emoji, date_edited, date_retracted,
                   is_system_message, group_action_type, message_action_type
            from messages
            where rowid = ?
            """,
            (last_rowid,),
        ).fetchone()
        if fetched is not None:
            preview_row = fetched
    return {
        "chat_rowid": int(row_value(row, "rowid", 0) or 0),
        "guid": row_value(row, "guid"),
        "title": chat_title(row),
        "participants": row_value(row, "participant_summary", "") or "",
        "service_name": row_value(row, "service_name"),
        "account_login": row_value(row, "account_login"),
        "message_count": int(row_value(row, "message_count", 0) or 0),
        "unread_count": int(row_value(row, "unread_count", 0) or 0),
        "last_message_rowid": last_rowid or None,
        "last_message_at": apple_ns_to_iso(row_value(row, "last_message_date", 0)),
        "last_message_preview": message_preview(preview_row),
    }


def query_messages_for_chat(
    con: sqlite3.Connection,
    chat_rowid: int,
    limit: int,
    newer_than_date: int | None = None,
    before_date: int | None = None,
    before_rowid: int | None = None,
) -> list[dict[str, Any]]:
    where_new = ""
    where_before = ""
    params: list[Any] = [chat_rowid]
    if newer_than_date is not None:
        where_new = "and m.date > ?"
        params.append(newer_than_date)
    if before_date is not None:
        if before_rowid is not None:
            where_before = "and (m.date < ? or (m.date = ? and m.rowid < ?))"
            params.extend([before_date, before_date, before_rowid])
        else:
            where_before = "and m.date < ?"
            params.append(before_date)
    params.append(limit)
    rows = con.execute(
        f"""
        select
            m.rowid,
            m.guid,
            m.text,
            m.subject,
            m.service,
            m.account,
            m.date,
            m.date_read,
            m.date_delivered,
            m.is_delivered,
            m.is_finished,
            m.is_from_me,
            m.is_read,
            m.is_system_message,
            m.is_sent,
            m.has_attachments,
            m.associated_message_guid,
            m.associated_message_guid_normalized,
            m.associated_message_type,
            m.associated_message_emoji,
            m.reply_to_guid,
            m.thread_originator_guid,
            m.thread_originator_part,
            m.date_edited,
            m.date_retracted,
            m.expressive_send_style_id,
            m.item_type,
            m.group_action_type,
            m.message_action_type,
            h.handle_id,
            h.contact_name,
            coalesce(nullif(h.contact_name, ''), h.handle_id) as handle_display
        from chat_messages cm
        join messages m on m.rowid = cm.message_rowid
        left join handles h on h.rowid = m.handle_rowid
        where cm.chat_rowid = ?
        {where_new}
        {where_before}
        order by m.date desc, m.rowid desc
        limit ?
        """,
        tuple(params),
    ).fetchall()
    message_ids = [int(row["rowid"]) for row in rows]
    attachments = attachment_map_for_messages(con, message_ids)
    parent_guids: set[str] = set()
    for row in rows:
        if is_threaded_reply(row):
            reply_target = normalize_guid_reference(row["thread_originator_guid"])
            if reply_target:
                parent_guids.add(reply_target)
        associated_type = int(row["associated_message_type"] or 0)
        if associated_type != 0:
            reaction_target = normalize_guid_reference(row["associated_message_guid_normalized"])
            if reaction_target:
                parent_guids.add(reaction_target)
    parent_map: dict[str, dict[str, Any]] = {}
    if parent_guids:
        placeholders = ",".join("?" for _ in parent_guids)
        parent_rows = con.execute(
            f"""
            select guid, text, subject, has_attachments, associated_message_type,
                   associated_message_emoji, date_retracted, date_edited,
                   is_system_message, group_action_type, message_action_type
            from messages
            where guid in ({placeholders})
            """,
            tuple(parent_guids),
        ).fetchall()
        parent_map = {
            str(row["guid"]): {
                "guid": row["guid"],
                "preview": message_preview(row),
            }
            for row in parent_rows
        }
    result: list[dict[str, Any]] = []
    for row in reversed(rows):
        associated_type = int(row["associated_message_type"] or 0)
        reply_target = (
            normalize_guid_reference(row["thread_originator_guid"])
            if is_threaded_reply(row)
            else None
        )
        result.append(
            {
                "message_rowid": int(row["rowid"]),
                "guid": row["guid"],
                "handle_id": row["handle_id"],
                "handle_display": row["handle_display"] or row["handle_id"] or "",
                "service": row["service"],
                "account": row["account"],
                "date": int(row["date"] or 0),
                "date_read": int(row["date_read"] or 0),
                "date_delivered": int(row["date_delivered"] or 0),
                "is_from_me": int(row["is_from_me"] or 0),
                "is_delivered": int(row["is_delivered"] or 0),
                "is_read": int(row["is_read"] or 0),
                "is_sent": int(row["is_sent"] or 0),
                "text": row["text"],
                "subject": row["subject"],
                "has_attachments": int(row["has_attachments"] or 0),
                "associated_message_type": associated_type,
                "associated_message_emoji": row["associated_message_emoji"],
                "reply_to_guid": normalize_guid_reference(row["reply_to_guid"]),
                "thread_originator_guid": normalize_guid_reference(row["thread_originator_guid"]),
                "associated_message_guid": normalize_guid_reference(row["associated_message_guid_normalized"]),
                "date_edited": int(row["date_edited"] or 0),
                "date_retracted": int(row["date_retracted"] or 0),
                "is_system_message": int(row["is_system_message"] or 0),
                "group_action_type": int(row["group_action_type"] or 0),
                "message_action_type": int(row["message_action_type"] or 0),
                "kind": message_kind(row),
                "preview": message_preview(row),
                "reaction_label": reaction_label(associated_type, row["associated_message_emoji"]),
                "attachments": attachments.get(int(row["rowid"]), []),
                "reply_target_guid": reply_target,
                "reply_target_preview": parent_map.get(reply_target or "", {}).get("preview"),
                "timestamp": apple_ns_to_iso(row["date"]),
            }
        )
    return result


def resolve_message_row(
    con: sqlite3.Connection,
    message_query: str,
) -> sqlite3.Row:
    query = message_query.strip()
    if query.isdigit():
        row = con.execute(
            """
            select
                m.*,
                h.handle_id,
                cm.chat_rowid
            from messages m
            join chat_messages cm on cm.message_rowid = m.rowid
            left join handles h on h.rowid = m.handle_rowid
            where m.rowid = ?
            order by cm.message_date desc, cm.chat_rowid desc
            limit 1
            """,
            (int(query),),
        ).fetchone()
        if row is not None:
            return row
    row = con.execute(
        """
        select
            m.*,
            h.handle_id,
            cm.chat_rowid
        from messages m
        join chat_messages cm on cm.message_rowid = m.rowid
        left join handles h on h.rowid = m.handle_rowid
        where m.guid = ?
        order by cm.message_date desc, cm.chat_rowid desc
        limit 1
        """,
        (query,),
    ).fetchone()
    if row is None:
        raise SystemExit(f"No message matched: {message_query}")
    return row


def query_attachments_for_chat(
    con: sqlite3.Connection,
    chat_rowid: int,
    limit: int,
) -> list[dict[str, Any]]:
    rows = con.execute(
        """
        select
            m.rowid as message_rowid,
            m.guid as message_guid,
            m.date,
            m.is_from_me,
            h.handle_id,
            coalesce(nullif(h.contact_name, ''), h.handle_id) as handle_display,
            a.rowid as attachment_rowid,
            a.guid as attachment_guid,
            a.filename,
            a.transfer_name,
            a.mime_type,
            a.uti,
            a.total_bytes,
            a.path_exists
        from chat_messages cm
        join messages m on m.rowid = cm.message_rowid
        join message_attachments ma on ma.message_rowid = m.rowid
        join attachments a on a.rowid = ma.attachment_rowid
        left join handles h on h.rowid = m.handle_rowid
        where cm.chat_rowid = ?
        order by m.date desc, m.rowid desc, a.rowid desc
        limit ?
        """,
        (chat_rowid, limit),
    ).fetchall()
    return [
        {
            "message_rowid": int(row["message_rowid"]),
            "message_guid": row["message_guid"],
            "timestamp": apple_ns_to_iso(row["date"]),
            "sender": "me"
            if int(row["is_from_me"] or 0)
            else (row["handle_display"] or row["handle_id"] or "unknown"),
            "attachment_rowid": int(row["attachment_rowid"]),
            "attachment_guid": row["attachment_guid"],
            "filename": row["filename"] or "",
            "transfer_name": row["transfer_name"] or "",
            "mime_type": row["mime_type"] or "",
            "uti": row["uti"] or "",
            "total_bytes": int(row["total_bytes"] or 0),
            "path_exists": bool(int(row["path_exists"] or 0)),
        }
        for row in rows
    ]


def query_send_jobs(
    con: sqlite3.Connection,
    *,
    limit: int,
    status: str = "",
) -> list[dict[str, Any]]:
    rows = con.execute(
        f"""
        select *
        from send_jobs
        {"where status = ?" if status else ""}
        order by created_at desc, rowid desc
        limit ?
        """,
        ((status, limit) if status else (limit,)),
    ).fetchall()
    return [format_send_job(row) for row in rows]


def query_search(con: sqlite3.Connection, query: str, limit: int) -> list[dict[str, Any]]:
    pattern = f"%{query.lower()}%"
    rows = con.execute(
        """
        select
            c.rowid as chat_rowid,
            c.guid as chat_guid,
            c.display_name,
            c.chat_identifier,
            c.participant_summary,
            m.rowid as message_rowid,
            m.guid as message_guid,
            m.text,
            m.subject,
            m.date,
            m.is_from_me,
            m.has_attachments,
            m.associated_message_type,
            m.associated_message_emoji,
            m.reply_to_guid,
            m.thread_originator_guid,
            h.handle_id,
            coalesce(nullif(h.contact_name, ''), h.handle_id) as handle_display
        from messages m
        join chat_messages cm on cm.message_rowid = m.rowid
        join chats c on c.rowid = cm.chat_rowid
        left join handles h on h.rowid = m.handle_rowid
        where
            lower(coalesce(m.text, '')) like ?
            or lower(coalesce(m.subject, '')) like ?
            or lower(coalesce(h.handle_id, '')) like ?
            or lower(coalesce(h.contact_name, '')) like ?
            or lower(coalesce(c.display_name, '')) like ?
            or lower(coalesce(c.chat_identifier, '')) like ?
            or lower(coalesce(c.participant_summary, '')) like ?
        order by m.date desc, m.rowid desc
        limit ?
        """,
        (pattern, pattern, pattern, pattern, pattern, pattern, pattern, limit),
    ).fetchall()
    return [
        {
            "chat_rowid": int(row["chat_rowid"]),
            "chat_guid": row["chat_guid"],
            "chat_title": chat_title(row),
            "participants": row["participant_summary"] or "",
            "message_rowid": int(row["message_rowid"]),
            "message_guid": row["message_guid"],
            "handle_id": row["handle_id"],
            "handle_display": row["handle_display"] or row["handle_id"] or "",
            "is_from_me": int(row["is_from_me"] or 0),
            "timestamp": apple_ns_to_iso(row["date"]),
            "preview": message_preview(row),
            "kind": message_kind(row),
        }
        for row in rows
    ]


def distinct_accounts(source: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = source.execute(
        """
        select coalesce(account, '') as account,
               coalesce(service, '') as service,
               count(*) as message_count,
               max(date) as latest_date
        from message
        group by account, service
        order by latest_date desc
        """
    ).fetchall()
    return [
        {
            "account": row["account"],
            "service": row["service"],
            "message_count": int(row["message_count"] or 0),
            "latest_at": apple_ns_to_iso(row["latest_date"]),
        }
        for row in rows
    ]


def probe_messages_automation() -> dict[str, Any]:
    script = 'tell application "Messages" to get count of chats'
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "detail": "osascript timed out after 5 seconds"}
    except FileNotFoundError:
        return {"status": "unavailable", "detail": "osascript not found"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    if result.returncode == 0:
        return {
            "status": "ok",
            "detail": compact_text(result.stdout.strip(), 80),
        }
    return {
        "status": "error",
        "detail": compact_text(result.stderr.strip() or result.stdout.strip(), 200),
        "returncode": result.returncode,
    }


def run_send_applescript(recipient: str, message: str, service_type: str) -> dict[str, Any]:
    service_enum = SERVICE_TYPE_MAP.get(service_type.lower(), "iMessage")
    script = """
on run argv
    set targetHandle to item 1 of argv
    set targetMessage to item 2 of argv
    tell application "Messages"
        set targetService to 1st service whose service type = %s
        set targetBuddy to buddy targetHandle of targetService
        send targetMessage to targetBuddy
    end tell
    return "sent"
end run
""" % (
        service_enum
    )
    try:
        result = subprocess.run(
            ["osascript", "-e", script, "--", recipient, message],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "status": "timeout", "detail": "osascript send timed out after 20 seconds"}
    except FileNotFoundError:
        return {"ok": False, "status": "unavailable", "detail": "osascript not found"}
    except Exception as exc:
        return {"ok": False, "status": "error", "detail": str(exc)}
    if result.returncode == 0:
        return {
            "ok": True,
            "status": "sent",
            "detail": compact_text(result.stdout.strip() or "sent", 80),
        }
    return {
        "ok": False,
        "status": "error",
        "detail": compact_text(result.stderr.strip() or result.stdout.strip(), 240),
        "returncode": result.returncode,
    }


def parse_send_result(stdout_text: str, stderr_text: str, returncode: int) -> dict[str, Any]:
    clean_stdout = stdout_text.strip()
    clean_stderr = stderr_text.strip()
    payload: dict[str, Any] = {}
    if clean_stdout:
        try:
            decoded = json.loads(clean_stdout)
            if isinstance(decoded, dict):
                payload.update(decoded)
        except json.JSONDecodeError:
            payload["detail"] = compact_text(clean_stdout, 240)
    combined_detail = "\n".join(
        value for value in (clean_stderr, clean_stdout) if value
    ).lower()
    if "appleevent timed out" in combined_detail:
        return {
            "ok": False,
            "status": "timeout",
            "detail": compact_text(clean_stderr or clean_stdout or "AppleEvent timed out", 240),
            "returncode": returncode,
        }
    if returncode == 0:
        payload.setdefault("ok", True)
        payload.setdefault("status", "sent")
        payload.setdefault("detail", compact_text(clean_stdout or "sent", 240))
        return payload
    payload.setdefault("ok", False)
    payload.setdefault("status", "error")
    payload.setdefault("detail", compact_text(clean_stderr or clean_stdout or "send failed", 240))
    payload["returncode"] = returncode
    return payload


def provider_command_name(provider_send_bin: Path) -> str:
    return provider_send_bin.name.strip().lower()


def provider_supports_native_reply(cfg: Config) -> bool:
    provider_send_bin = cfg.provider_send_bin
    if not provider_send_bin:
        return False
    provider_name = provider_command_name(provider_send_bin)
    return provider_name == "openclaw"


def build_provider_send_command(
    provider_send_bin: Path,
    recipient: str | None,
    message: str,
    service_type: str,
    *,
    chat_rowid: int | None = None,
    reply_to_id: str | None = None,
) -> list[str]:
    provider_name = provider_command_name(provider_send_bin)
    if provider_name == "openclaw":
        if chat_rowid is not None:
            target = f"chat_id:{chat_rowid}"
        elif recipient:
            target = recipient
        else:
            raise ValueError("recipient or chat rowid is required")
        command = [
            str(provider_send_bin),
            "message",
            "send",
            "--channel",
            "imessage",
            "--target",
            target,
            "--message",
            message,
            "--json",
        ]
        if reply_to_id:
            command.extend(["--reply-to", reply_to_id])
        return command

    command = [str(provider_send_bin), "send"]
    if chat_rowid is not None:
        command.extend(["--chat-id", str(chat_rowid)])
    elif recipient:
        command.extend(["--to", recipient])
    else:
        raise ValueError("recipient or chat rowid is required")
    command.extend(
        [
            "--text",
            message,
            "--service",
            service_type,
            "--json",
        ]
    )
    return command


def run_send_provider_direct(
    provider_send_bin: Path,
    recipient: str | None,
    message: str,
    service_type: str,
    *,
    chat_rowid: int | None = None,
    reply_to_id: str | None = None,
) -> dict[str, Any]:
    try:
        command = build_provider_send_command(
            provider_send_bin,
            recipient,
            message,
            service_type,
            chat_rowid=chat_rowid,
            reply_to_id=reply_to_id,
        )
    except ValueError as exc:
        return {"ok": False, "status": "error", "detail": str(exc)}
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return {"ok": False, "status": "timeout", "detail": "provider send timed out after 30 seconds"}
    except FileNotFoundError:
        return {"ok": False, "status": "unavailable", "detail": f"provider send binary not found: {provider_send_bin}"}
    except Exception as exc:
        return {"ok": False, "status": "error", "detail": str(exc)}
    return parse_send_result(result.stdout, result.stderr, result.returncode)


def run_send_provider_via_terminal(
    provider_send_bin: Path,
    recipient: str | None,
    message: str,
    service_type: str,
    *,
    chat_rowid: int | None = None,
    reply_to_id: str | None = None,
) -> dict[str, Any]:
    job_dir = Path(tempfile.mkdtemp(prefix="imsg-send-", dir="/tmp"))
    script_path = job_dir / "send.sh"
    runner_path = job_dir / "runner.py"
    out_path = job_dir / "stdout.json"
    err_path = job_dir / "stderr.txt"
    status_path = job_dir / "status.txt"
    try:
        command = build_provider_send_command(
            provider_send_bin,
            recipient,
            message,
            service_type,
            chat_rowid=chat_rowid,
            reply_to_id=reply_to_id,
        )
    except ValueError as exc:
        return {"ok": False, "status": "error", "detail": str(exc)}
    runner_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "import subprocess",
                "from pathlib import Path",
                f"command = {json.dumps(command)}",
                f"out_path = Path({json.dumps(str(out_path))})",
                f"err_path = Path({json.dumps(str(err_path))})",
                f"status_path = Path({json.dumps(str(status_path))})",
                "timeout_seconds = 40",
                "stdout_text = ''",
                "stderr_text = ''",
                "returncode = 1",
                "try:",
                "    process = subprocess.Popen(",
                "        command,",
                "        stdout=subprocess.PIPE,",
                "        stderr=subprocess.PIPE,",
                "        text=True,",
                "    )",
                "    try:",
                "        stdout_text, stderr_text = process.communicate(timeout=timeout_seconds)",
                "        returncode = process.returncode",
                "    except subprocess.TimeoutExpired:",
                "        process.terminate()",
                "        try:",
                "            stdout_text, stderr_text = process.communicate(timeout=3)",
                "        except subprocess.TimeoutExpired:",
                "            process.kill()",
                "            stdout_text, stderr_text = process.communicate()",
                "        timeout_note = f'provider send timed out after {timeout_seconds} seconds'",
                "        stderr_text = (stderr_text.strip() + '\\n' + timeout_note).strip() if stderr_text else timeout_note",
                "        returncode = 124",
                "except Exception as exc:",
                "    stderr_text = str(exc)",
                "out_path.write_text(stdout_text or '', encoding='utf-8')",
                "err_path.write_text(stderr_text or '', encoding='utf-8')",
                "status_path.write_text(str(returncode), encoding='utf-8')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    runner_path.chmod(0o700)
    script_path.write_text(
        "\n".join(
            [
                "#!/bin/bash",
                "set -u",
                f"{shlex.quote(sys.executable)} {shlex.quote(str(runner_path))}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    script_path.chmod(0o700)
    terminal_command = f"bash {shlex.quote(str(script_path))}"
    escaped_terminal_command = terminal_command.replace("\\", "\\\\").replace('"', '\\"')
    apple_script = f'tell application "Terminal" to do script "{escaped_terminal_command}"'
    try:
        open_result = subprocess.run(
            ["osascript", "-e", apple_script],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "status": "timeout",
            "detail": f"launching Terminal send timed out; inspect {job_dir}",
        }
    except FileNotFoundError:
        return {"ok": False, "status": "unavailable", "detail": "osascript not found"}
    except Exception as exc:
        return {"ok": False, "status": "error", "detail": str(exc)}
    if open_result.returncode != 0:
        return {
            "ok": False,
            "status": "error",
            "detail": compact_text(open_result.stderr.strip() or open_result.stdout.strip(), 240),
            "returncode": open_result.returncode,
        }

    deadline = time.time() + 55
    while time.time() < deadline:
        if status_path.exists():
            try:
                returncode = int(status_path.read_text(encoding="utf-8").strip() or "1")
            except Exception:
                returncode = 1
            stdout_text = out_path.read_text(encoding="utf-8") if out_path.exists() else ""
            stderr_text = err_path.read_text(encoding="utf-8") if err_path.exists() else ""
            if returncode == 124:
                return {
                    "ok": False,
                    "status": "timeout",
                    "detail": compact_text(stderr_text or "provider send timed out", 240),
                }
            payload = parse_send_result(stdout_text, stderr_text, returncode)
            payload.setdefault("detail", compact_text(payload.get("detail", ""), 240))
            return payload
        time.sleep(0.5)

    return {
        "ok": False,
        "status": "timeout",
        "detail": f"provider send did not finish within 55 seconds; inspect {job_dir}",
    }


def run_send(
    cfg: Config,
    recipient: str | None,
    message: str,
    service_type: str,
    *,
    chat_rowid: int | None = None,
    reply_to_id: str | None = None,
) -> dict[str, Any]:
    provider_send_bin = cfg.provider_send_bin
    if provider_send_bin and provider_send_bin.exists():
        direct_result = run_send_provider_direct(
            provider_send_bin,
            recipient,
            message,
            service_type,
            chat_rowid=chat_rowid,
            reply_to_id=reply_to_id,
        )
        if direct_result.get("ok"):
            return direct_result
        direct_detail = str(direct_result.get("detail", "") or "").lower()
        worker_should_retry_via_terminal = os.environ.get("IMSG_SEND_WORKER") == "1" and (
            "permissiondenied" in direct_detail
            or "authorization denied" in direct_detail
            or direct_result.get("status") in {"timeout", "unavailable"}
        )
        if not worker_should_retry_via_terminal and (
            os.environ.get("IMSG_SEND_WORKER") == "1"
            or os.environ.get("TERM_PROGRAM") == "Apple_Terminal"
        ):
            return direct_result
        terminal_result = run_send_provider_via_terminal(
            provider_send_bin,
            recipient,
            message,
            service_type,
            chat_rowid=chat_rowid,
            reply_to_id=reply_to_id,
        )
        if terminal_result.get("ok"):
            return terminal_result
        if recipient and not reply_to_id:
            applescript_result = run_send_applescript(recipient, message, service_type)
            if applescript_result.get("ok"):
                return applescript_result
            if applescript_result.get("status") not in {"unavailable", ""}:
                return applescript_result
        if terminal_result.get("status") not in {"unavailable", ""}:
            return terminal_result
        return direct_result
    if not recipient:
        return {
            "ok": False,
            "status": "error",
            "detail": "recipient resolution is required when provider chat-id sending is unavailable",
        }
    if reply_to_id:
        return {
            "ok": False,
            "status": "blocked",
            "detail": "native threaded replies are not supported without a reply-capable provider backend",
            "blocked_reason": "native-threaded-reply-unsupported",
        }
    return run_send_applescript(recipient, message, service_type)


def build_send_payload_from_job(row: sqlite3.Row) -> dict[str, Any]:
    payload = format_send_job(row)
    payload.update(
        {
            "recipient": row["resolved_recipient"] or row["recipient_input"] or "",
            "service": row["service_type"],
            "text": row["message_text"],
            "dry_run": bool(int(row["dry_run"] or 0)),
            "ok": row["status"] in {"sent", "dry-run"},
            "status": row["status"],
            "detail": row["provider_detail"] or row["blocked_reason"] or "",
        }
    )
    return payload


def send_should_run_inline(cfg: Config) -> bool:
    if os.environ.get("IMSG_SEND_WORKER") == "1":
        return True
    if cfg.machine_id != cfg.server_machine_id:
        return False
    return os.environ.get("TERM_PROGRAM") == "Apple_Terminal"


def fetch_send_job_row(con: sqlite3.Connection, job_rowid: int) -> sqlite3.Row | None:
    return con.execute("select * from send_jobs where rowid = ?", (job_rowid,)).fetchone()


def claim_send_job(con: sqlite3.Connection, job_rowid: int) -> sqlite3.Row | None:
    con.execute("begin immediate")
    row = fetch_send_job_row(con, job_rowid)
    if row is None:
        con.rollback()
        return None
    if row["status"] != "queued":
        con.commit()
        return row
    cursor = con.execute(
        """
        update send_jobs
        set status = 'sending',
            updated_at = ?,
            attempt_count = attempt_count + 1
        where rowid = ?
          and status = 'queued'
        """,
        (now_utc_epoch(), job_rowid),
    )
    con.commit()
    if cursor.rowcount != 1:
        return fetch_send_job_row(con, job_rowid)
    return fetch_send_job_row(con, job_rowid)


def claim_next_queued_send_job(con: sqlite3.Connection) -> sqlite3.Row | None:
    con.execute("begin immediate")
    row = con.execute(
        """
        select rowid
        from send_jobs
        where status = 'queued'
        order by created_at asc, rowid asc
        limit 1
        """
    ).fetchone()
    if row is None:
        con.rollback()
        return None
    job_rowid = int(row["rowid"])
    cursor = con.execute(
        """
        update send_jobs
        set status = 'sending',
            updated_at = ?,
            attempt_count = attempt_count + 1
        where rowid = ?
          and status = 'queued'
        """,
        (now_utc_epoch(), job_rowid),
    )
    con.commit()
    if cursor.rowcount != 1:
        return None
    return fetch_send_job_row(con, job_rowid)


def execute_claimed_send_job(cfg: Config, row: sqlite3.Row) -> sqlite3.Row:
    job_rowid = int(row["rowid"])
    chat_rowid = int(row["destination_chat_rowid"]) if row["destination_chat_rowid"] not in (None, "") else None
    recipient = row["resolved_recipient"] or row["recipient_input"] or None
    reply_to_id = row["parent_message_guid"] or None
    send_result = run_send(
        cfg,
        recipient,
        row["message_text"],
        row["service_type"],
        chat_rowid=chat_rowid,
        reply_to_id=reply_to_id,
    )

    blocked_reason = str(send_result.get("blocked_reason", "") or "")
    provider_status = str(send_result.get("status", "") or "")
    provider_detail = str(send_result.get("detail", "") or "")
    if send_result.get("ok"):
        final_status = "sent"
    elif blocked_reason or provider_status == "blocked":
        final_status = "blocked"
    else:
        final_status = "failed"
    sent_at = now_utc_epoch() if final_status == "sent" else 0

    with sqlite_connect_rw(cfg.index_db) as index:
        initialize_index_schema(index)
        update_send_job(
            index,
            job_rowid,
            status=final_status,
            provider_status=provider_status,
            provider_detail=provider_detail,
            blocked_reason=blocked_reason,
            increment_attempt=False,
            sent_at=sent_at,
        )
        updated_row = fetch_send_job_row(index, job_rowid)
        index.commit()

    if final_status == "sent":
        sync_index_safe(cfg, quiet=True)
    if updated_row is None:
        raise SystemExit(f"Send job disappeared after processing: {job_rowid}")
    return updated_row


def execute_send_job(cfg: Config, job_rowid: int) -> sqlite3.Row:
    with sqlite_connect_rw(cfg.index_db) as index:
        initialize_index_schema(index)
        row = claim_send_job(index, job_rowid)
        index.commit()
    if row is None:
        raise SystemExit(f"No send job matched: {job_rowid}")
    if row["status"] != "sending":
        return row
    return execute_claimed_send_job(cfg, row)


def wait_for_send_job(
    cfg: Config,
    job_rowid: int,
    *,
    timeout_seconds: int = DEFAULT_SEND_WAIT_SECONDS,
) -> sqlite3.Row | None:
    deadline = time.time() + max(1, timeout_seconds)
    latest_row: sqlite3.Row | None = None
    while time.time() < deadline:
        with sqlite_connect_ro(cfg.index_db) as index:
            latest_row = fetch_send_job_row(index, job_rowid)
        if latest_row is None:
            return None
        if latest_row["status"] not in {"queued", "sending"}:
            return latest_row
        time.sleep(DEFAULT_SEND_POLL_INTERVAL_SECONDS)
    return latest_row


def run_send_worker(cfg: Config, *, loop: bool, poll_interval: float) -> int:
    if cfg.machine_id != cfg.server_machine_id:
        raise SystemExit("send-worker is only valid on the bridge host.")

    sleep_seconds = max(0.2, float(poll_interval))
    while True:
        with sqlite_connect_rw(cfg.index_db) as index:
            initialize_index_schema(index)
            row = claim_next_queued_send_job(index)
            index.commit()
        if row is None:
            if not loop:
                return 0
            time.sleep(sleep_seconds)
            continue

        final_row = execute_claimed_send_job(cfg, row)
        print(
            json.dumps(
                {
                    "job_rowid": int(final_row["rowid"]),
                    "status": final_row["status"],
                    "provider_status": final_row["provider_status"] or "",
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
        if not loop:
            return 0


def perform_send_request(
    cfg: Config,
    *,
    recipient_input: str | None,
    chat_query: str | None,
    parent_message_query: str | None,
    message_text: str,
    service_type: str,
    dry_run: bool,
    idempotency_key: str,
    allow_duplicate: bool,
    allow_first_contact: bool,
    ignore_quiet_hours: bool,
) -> tuple[dict[str, Any], int]:
    sync_index_safe(cfg, quiet=True)
    requested_by = requesting_machine_id(cfg)

    with sqlite_connect_rw(cfg.index_db) as index:
        initialize_index_schema(index)

        parent_row: sqlite3.Row | None = None
        parent_preview: str | None = None
        if parent_message_query:
            parent_row = resolve_message_row(index, parent_message_query)
            parent_preview = message_preview(parent_row)
            if not chat_query:
                chat_query = str(parent_row["chat_rowid"])

        resolved = resolve_send_target(
            index,
            recipient_input=recipient_input,
            chat_query=chat_query,
        )

        resolved_recipient = resolved["resolved_recipient"] or recipient_input or ""
        destination_chat_rowid = resolved["chat_rowid"]
        destination_chat_guid = resolved["chat_guid"]
        destination_key = destination_chat_guid or resolved_recipient or (recipient_input or "")
        duplicate_key = duplicate_key_for_destination(destination_key, message_text, service_type)
        provider_reply_supported = provider_supports_native_reply(cfg)

        if idempotency_key:
            existing = lookup_send_job_by_idempotency(index, idempotency_key)
            if existing is not None:
                payload = build_send_payload_from_job(existing)
                payload["idempotent_replay"] = True
                index.commit()
                return payload, 0 if payload.get("ok") else 1

        if resolved["mode"] == "ambiguous":
            job_rowid = insert_send_job(
                index,
                requested_by_machine_id=requested_by,
                recipient_input=recipient_input,
                resolved_recipient="",
                destination_chat_rowid=None,
                destination_chat_guid=None,
                service_type=service_type,
                message_text=message_text,
                idempotency_key=idempotency_key,
                duplicate_key=duplicate_key,
                dry_run=dry_run,
                parent_message_rowid=int(parent_row["rowid"]) if parent_row is not None else None,
                parent_message_guid=parent_row["guid"] if parent_row is not None else None,
                parent_preview=parent_preview,
                status="blocked",
                blocked_reason="ambiguous-recipient",
            )
            index.commit()
            return (
                {
                    "job_rowid": job_rowid,
                    "ok": False,
                    "status": "blocked",
                    "blocked_reason": "ambiguous-recipient",
                    "candidates": resolved["ambiguous_candidates"],
                },
                1,
            )

        if parent_row is not None and not provider_reply_supported:
            blocked_reason = "native-threaded-reply-unsupported"
            provider_detail = "current send backend does not support native iMessage threaded replies"
            job_rowid = insert_send_job(
                index,
                requested_by_machine_id=requested_by,
                recipient_input=recipient_input,
                resolved_recipient=resolved_recipient,
                destination_chat_rowid=destination_chat_rowid,
                destination_chat_guid=destination_chat_guid,
                service_type=service_type,
                message_text=message_text,
                idempotency_key=idempotency_key,
                duplicate_key=duplicate_key,
                dry_run=dry_run,
                parent_message_rowid=int(parent_row["rowid"]),
                parent_message_guid=parent_row["guid"],
                parent_preview=parent_preview,
                status="blocked",
                blocked_reason=blocked_reason,
                provider_detail=provider_detail,
            )
            index.commit()
            return (
                {
                    "job_rowid": job_rowid,
                    "ok": False,
                    "status": "blocked",
                    "blocked_reason": blocked_reason,
                    "detail": provider_detail,
                    "recipient": resolved_recipient,
                    "destination_chat_rowid": destination_chat_rowid,
                    "parent_message_rowid": int(parent_row["rowid"]),
                    "parent_message_guid": parent_row["guid"],
                    "parent_preview": parent_preview or "",
                },
                1,
            )

        if not allow_first_contact and not resolved["known_contact"]:
            job_rowid = insert_send_job(
                index,
                requested_by_machine_id=requested_by,
                recipient_input=recipient_input,
                resolved_recipient=resolved_recipient,
                destination_chat_rowid=destination_chat_rowid,
                destination_chat_guid=destination_chat_guid,
                service_type=service_type,
                message_text=message_text,
                idempotency_key=idempotency_key,
                duplicate_key=duplicate_key,
                dry_run=dry_run,
                parent_message_rowid=int(parent_row["rowid"]) if parent_row is not None else None,
                parent_message_guid=parent_row["guid"] if parent_row is not None else None,
                parent_preview=parent_preview,
                status="blocked",
                blocked_reason="first-contact-confirmation-required",
            )
            index.commit()
            return (
                {
                    "job_rowid": job_rowid,
                    "ok": False,
                    "status": "blocked",
                    "blocked_reason": "first-contact-confirmation-required",
                    "recipient": resolved_recipient,
                },
                1,
            )

        if not ignore_quiet_hours and in_quiet_hours(cfg):
            job_rowid = insert_send_job(
                index,
                requested_by_machine_id=requested_by,
                recipient_input=recipient_input,
                resolved_recipient=resolved_recipient,
                destination_chat_rowid=destination_chat_rowid,
                destination_chat_guid=destination_chat_guid,
                service_type=service_type,
                message_text=message_text,
                idempotency_key=idempotency_key,
                duplicate_key=duplicate_key,
                dry_run=dry_run,
                parent_message_rowid=int(parent_row["rowid"]) if parent_row is not None else None,
                parent_message_guid=parent_row["guid"] if parent_row is not None else None,
                parent_preview=parent_preview,
                status="blocked",
                blocked_reason="quiet-hours",
            )
            index.commit()
            return (
                {
                    "job_rowid": job_rowid,
                    "ok": False,
                    "status": "blocked",
                    "blocked_reason": "quiet-hours",
                },
                1,
            )

        if not allow_duplicate:
            duplicate = recent_duplicate_job(index, duplicate_key, cfg.duplicate_window_seconds)
            if duplicate is not None:
                job_rowid = insert_send_job(
                    index,
                    requested_by_machine_id=requested_by,
                    recipient_input=recipient_input,
                    resolved_recipient=resolved_recipient,
                    destination_chat_rowid=destination_chat_rowid,
                    destination_chat_guid=destination_chat_guid,
                    service_type=service_type,
                    message_text=message_text,
                    idempotency_key=idempotency_key,
                    duplicate_key=duplicate_key,
                    dry_run=dry_run,
                    parent_message_rowid=int(parent_row["rowid"]) if parent_row is not None else None,
                    parent_message_guid=parent_row["guid"] if parent_row is not None else None,
                    parent_preview=parent_preview,
                    status="blocked",
                    blocked_reason="duplicate-send-protection",
                )
                index.commit()
                return (
                    {
                        "job_rowid": job_rowid,
                        "ok": False,
                        "status": "blocked",
                        "blocked_reason": "duplicate-send-protection",
                        "duplicate_of_job_rowid": int(duplicate["rowid"]),
                    },
                    1,
                )

        initial_status = "dry-run" if dry_run else "queued"
        job_rowid = insert_send_job(
            index,
            requested_by_machine_id=requested_by,
            recipient_input=recipient_input,
            resolved_recipient=resolved_recipient,
            destination_chat_rowid=destination_chat_rowid,
            destination_chat_guid=destination_chat_guid,
            service_type=service_type,
            message_text=message_text,
            idempotency_key=idempotency_key,
            duplicate_key=duplicate_key,
            dry_run=dry_run,
            parent_message_rowid=int(parent_row["rowid"]) if parent_row is not None else None,
            parent_message_guid=parent_row["guid"] if parent_row is not None else None,
            parent_preview=parent_preview,
            status=initial_status,
        )
        if dry_run:
            update_send_job(
                index,
                job_rowid,
                status="dry-run",
                provider_status="dry-run",
                provider_detail="send skipped by --dry-run",
            )
            row = index.execute("select * from send_jobs where rowid = ?", (job_rowid,)).fetchone()
            index.commit()
            payload = build_send_payload_from_job(row)
            payload["recipient"] = resolved_recipient
            payload["service"] = service_type
            payload["text"] = message_text
            payload["parent_message_rowid"] = int(parent_row["rowid"]) if parent_row is not None else None
            payload["parent_preview"] = parent_preview or ""
            return payload, 0

        index.commit()

    if send_should_run_inline(cfg):
        row = execute_send_job(cfg, job_rowid)
    else:
        row = wait_for_send_job(cfg, job_rowid)
        if row is None:
            raise SystemExit(f"Send job disappeared while waiting: {job_rowid}")

    payload = build_send_payload_from_job(row)
    payload.update(
        {
            "recipient": resolved_recipient or recipient_input or "",
            "service": service_type,
            "text": message_text,
            "destination_chat_rowid": destination_chat_rowid,
            "destination_chat_guid": destination_chat_guid,
            "destination_chat_title": resolved["chat_title"],
            "parent_message_rowid": int(parent_row["rowid"]) if parent_row is not None else None,
            "parent_message_guid": parent_row["guid"] if parent_row is not None else "",
            "parent_preview": parent_preview or "",
        }
    )
    if row["status"] == "queued":
        payload["detail"] = payload.get("detail") or "waiting for send worker"
        return payload, 1
    return payload, 0 if payload.get("ok") else 1


def retry_send_job(
    cfg: Config,
    job_rowid: int,
    *,
    allow_duplicate: bool,
    allow_first_contact: bool,
    ignore_quiet_hours: bool,
) -> tuple[dict[str, Any], int]:
    with sqlite_connect_ro(cfg.index_db) as index:
        row = index.execute("select * from send_jobs where rowid = ?", (job_rowid,)).fetchone()
        if row is None:
            raise SystemExit(f"No send job matched: {job_rowid}")
        if row["status"] == "sent":
            payload = build_send_payload_from_job(row)
            payload["retry_skipped"] = True
            return payload, 0
        recipient_input = row["recipient_input"] or row["resolved_recipient"] or None
        chat_query = str(row["destination_chat_rowid"]) if row["destination_chat_rowid"] not in (None, "") else None
        parent_message_query = row["parent_message_guid"] or None
        service_type = row["service_type"]
        message_text = row["message_text"]
        original_idempotency_key = row["idempotency_key"] or ""
        retry_idempotency_key = (
            f"{original_idempotency_key}:retry:{uuid.uuid4()}"
            if original_idempotency_key
            else str(uuid.uuid4())
        )
    return perform_send_request(
        cfg,
        recipient_input=recipient_input,
        chat_query=chat_query,
        parent_message_query=parent_message_query,
        message_text=message_text,
        service_type=service_type,
        dry_run=False,
        idempotency_key=retry_idempotency_key,
        allow_duplicate=allow_duplicate,
        allow_first_contact=allow_first_contact,
        ignore_quiet_hours=ignore_quiet_hours,
    )


def probe_send_worker(cfg: Config) -> dict[str, Any]:
    if cfg.machine_id != cfg.server_machine_id or sys.platform != "darwin":
        return {"status": "not-applicable"}

    label = SEND_WORKER_LABEL
    domain = f"gui/{os.getuid()}/{label}"
    try:
        result = subprocess.run(
            ["launchctl", "print", domain],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "detail": "launchctl print timed out after 5 seconds"}
    except FileNotFoundError:
        return {"status": "unavailable", "detail": "launchctl not found"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
    if result.returncode != 0:
        detail = compact_text(result.stderr.strip() or result.stdout.strip(), 240)
        return {"status": "missing", "label": label, "detail": detail}

    stdout = result.stdout
    status = "loaded"
    if "state = running" in stdout:
        status = "running"
    elif "state = waiting" in stdout:
        status = "waiting"
    return {"status": status, "label": label}


def doctor_payload(cfg: Config) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "machine_id": cfg.machine_id,
        "server_machine_id": cfg.server_machine_id,
        "chat_db": str(cfg.chat_db) if cfg.chat_db else "",
        "chat_db_exists": bool(cfg.chat_db and cfg.chat_db.exists()),
        "attachments_root": str(cfg.attachments_root) if cfg.attachments_root else "",
        "attachments_root_exists": bool(cfg.attachments_root and cfg.attachments_root.exists()),
        "state_root": str(cfg.state_root),
        "index_db": str(cfg.index_db),
        "index_db_exists": cfg.index_db.exists(),
        "account_hint": cfg.account_hint,
        "phone_account_hint": cfg.phone_account_hint,
        "automation": probe_messages_automation() if cfg.machine_id == cfg.server_machine_id else {"status": "remote-only"},
        "send_worker": probe_send_worker(cfg),
    }
    if cfg.chat_db and cfg.chat_db.exists():
        with sqlite_connect_ro(cfg.chat_db) as source:
            payload["source_latest_message_rowid"] = source_latest_message_rowid(source)
            payload["source_latest_message_at"] = apple_ns_to_iso(source_latest_message_date(source))
            payload["accounts"] = distinct_accounts(source)
    if cfg.index_db.exists():
        with sqlite_connect_ro(cfg.index_db) as index:
            payload["indexed_latest_message_rowid"] = int(meta_get(index, "last_message_rowid", "0") or "0")
            payload["indexed_latest_message_at"] = apple_ns_to_iso(meta_get(index, "last_source_message_date", "0"))
            payload["last_sync_completed_at"] = meta_get(index, "last_sync_completed_at", "")
            row = index.execute("select count(*) as value from chats").fetchone()
            payload["indexed_chat_count"] = int(row["value"] or 0)
            row = index.execute("select count(*) as value from messages").fetchone()
            payload["indexed_message_count"] = int(row["value"] or 0)
    return payload


def render_contacts(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No contacts matched."
    lines = []
    for row in rows:
        label = row["display_name"]
        if label != row["handle_id"]:
            label = f"{label} ({row['handle_id']})"
        lines.append(
            f"{row['handle_rowid']}: {label} | service={row['service'] or 'unknown'} "
            f"| messages={row['message_count']} | latest={row['last_message_at'] or 'unknown'}"
        )
    return "\n".join(lines)


def render_chats(rows: list[dict[str, Any]], unread_only: bool = False) -> str:
    if not rows:
        return "No chats matched."
    lines = []
    for row in rows:
        unread_part = f" unread={row['unread_count']}" if unread_only or row["unread_count"] else ""
        lines.append(
            f"{row['chat_rowid']}: {row['title']} | latest={row['last_message_at'] or 'unknown'}"
            f" | messages={row['message_count']}{unread_part}"
        )
        if row["participants"]:
            lines.append(f"  participants: {row['participants']}")
        if row["last_message_preview"]:
            lines.append(f"  last: {row['last_message_preview']}")
    return "\n".join(lines)


def render_messages(chat: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"chat {chat['chat_rowid']}: {chat['title']}",
        f"participants: {chat['participants'] or 'n/a'}",
        f"messages: {chat['message_count']} | unread: {chat['unread_count']} | latest: {chat['last_message_at'] or 'unknown'}",
        "",
    ]
    if not rows:
        lines.append("No messages.")
        return "\n".join(lines)
    for row in rows:
        actor = "me" if row["is_from_me"] else (row["handle_display"] or row["handle_id"] or "unknown")
        prefix = row["kind"]
        preview = row["preview"]
        if prefix == "reaction" and row.get("reaction_label"):
            preview = f"[{row['reaction_label']}]"
        segments = [display_timestamp(row["date"]), actor]
        if prefix != "message":
            segments.append(prefix)
        segments.append(preview)
        lines.append(" | ".join(segments))
        if row["reply_target_guid"]:
            target_preview = row["reply_target_preview"] or row["reply_target_guid"]
            lines.append(f"  parent: {target_preview}")
        if row["attachments"]:
            attachment_bits = [
                attachment["transfer_name"]
                or attachment["filename"]
                or attachment["guid"]
                for attachment in row["attachments"]
            ]
            lines.append(f"  attachments: {', '.join(attachment_bits)}")
    return "\n".join(lines)


def render_search(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No messages matched."
    lines = []
    for row in rows:
        actor = "me" if row["is_from_me"] else (row["handle_display"] or row["handle_id"] or "unknown")
        lines.append(
            f"{row['message_rowid']}: {row['chat_title']} | {row['timestamp'] or 'unknown'} | {actor} | {row['kind']} | {row['preview']}"
        )
    return "\n".join(lines)


def render_attachments(chat: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        f"chat {chat['chat_rowid']}: {chat['title']}",
        f"participants: {chat['participants'] or 'n/a'}",
        "",
    ]
    if not rows:
        lines.append("No attachments.")
        return "\n".join(lines)
    for row in rows:
        name = row["transfer_name"] or row["filename"] or row["attachment_guid"]
        lines.append(
            f"{row['attachment_rowid']}: {row['timestamp'] or 'unknown'} | {row['sender']} | "
            f"{name} | mime={row['mime_type'] or 'unknown'} | bytes={row['total_bytes']} | "
            f"path_exists={str(row['path_exists']).lower()}"
        )
    return "\n".join(lines)


def render_outbox(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No send jobs."
    lines = []
    for row in rows:
        lines.append(
            f"{row['job_rowid']}: {row['status']} | {row['created_at'] or 'unknown'} | "
            f"{row['requested_by_machine_id']} -> {row['resolved_recipient'] or row['recipient_input'] or '[unknown]'} | "
            f"attempts={row['attempt_count']} | {compact_text(row['message_text'], 90)}"
        )
        if row["blocked_reason"]:
            lines.append(f"  blocked: {row['blocked_reason']}")
        elif row["provider_detail"]:
            lines.append(f"  detail: {row['provider_detail']}")
    return "\n".join(lines)


def render_doctor(payload: dict[str, Any]) -> str:
    lines = [
        f"machine={payload['machine_id']}",
        f"server_machine={payload['server_machine_id']}",
        f"chat_db={payload['chat_db']}",
        f"chat_db_exists={payload['chat_db_exists']}",
        f"attachments_root={payload['attachments_root']}",
        f"attachments_root_exists={payload['attachments_root_exists']}",
        f"index_db={payload['index_db']}",
        f"index_db_exists={payload['index_db_exists']}",
    ]
    if "source_latest_message_rowid" in payload:
        lines.append(f"source_latest_message_rowid={payload['source_latest_message_rowid']}")
        lines.append(f"source_latest_message_at={payload['source_latest_message_at']}")
    if "indexed_latest_message_rowid" in payload:
        lines.append(f"indexed_latest_message_rowid={payload['indexed_latest_message_rowid']}")
        lines.append(f"indexed_latest_message_at={payload['indexed_latest_message_at']}")
        lines.append(f"last_sync_completed_at={payload['last_sync_completed_at']}")
    automation = payload.get("automation", {})
    if automation:
        lines.append(f"automation_status={automation.get('status', 'unknown')}")
        detail = automation.get("detail")
        if detail:
            lines.append(f"automation_detail={detail}")
    send_worker = payload.get("send_worker", {})
    if send_worker:
        lines.append(f"send_worker_status={send_worker.get('status', 'unknown')}")
        label = send_worker.get("label")
        if label:
            lines.append(f"send_worker_label={label}")
        detail = send_worker.get("detail")
        if detail:
            lines.append(f"send_worker_detail={detail}")
    accounts = payload.get("accounts", [])
    if accounts:
        lines.append("accounts:")
        for row in accounts:
            lines.append(
                f"  {row['account'] or '[none]'} | service={row['service'] or '[none]'} | "
                f"messages={row['message_count']} | latest={row['latest_at'] or 'unknown'}"
            )
    return "\n".join(lines)


def emit_payload(payload: Any, json_mode: bool, renderer) -> None:
    if json_mode:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(renderer(payload))


def emit_rows(rows: list[dict[str, Any]], json_mode: bool, renderer) -> None:
    if json_mode:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    print(renderer(rows))


def run_server(argv: list[str]) -> int:
    cfg = load_config()
    parser = argparse.ArgumentParser(
        prog="imsgd",
        description="Local Messages bridge and indexed read model.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="Refresh the local imsg index from chat.db.")
    sync_parser.add_argument("--rebuild", action="store_true", help="Rebuild the index from scratch.")
    sync_parser.add_argument("--quiet", action="store_true", help="Suppress human-readable sync output.")
    sync_parser.add_argument("--json", action="store_true", help="Print JSON sync output.")

    doctor_parser = subparsers.add_parser("doctor", help="Inspect bridge health and local paths.")
    doctor_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    contacts_parser = subparsers.add_parser("contacts", help="Search known handles and contacts in the index.")
    contacts_parser.add_argument("query", nargs="?", help="Optional search query.")
    contacts_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Result limit.")
    contacts_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    contacts_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    chats_parser = subparsers.add_parser("chats", help="List known chats.")
    chats_parser.add_argument("query", nargs="?", help="Optional chat search query.")
    chats_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Result limit.")
    chats_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    chats_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    unreads_parser = subparsers.add_parser("unreads", help="List chats with unread messages.")
    unreads_parser.add_argument("query", nargs="?", help="Optional chat search query.")
    unreads_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Result limit.")
    unreads_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    unreads_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    show_parser = subparsers.add_parser("show", help="Show the latest messages in a chat.")
    show_parser.add_argument("chat", help="Chat id, guid, title, or participant query.")
    show_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Message limit.")
    show_parser.add_argument("--before-date", type=int, help="Only return messages older than this Apple nanoseconds timestamp.")
    show_parser.add_argument("--before-rowid", type=int, help="When paired with --before-date, page older than this message rowid.")
    show_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    show_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    tail_parser = subparsers.add_parser("tail", help="Tail a chat.")
    tail_parser.add_argument("chat", help="Chat id, guid, title, or participant query.")
    tail_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Message limit.")
    tail_parser.add_argument("--follow", action="store_true", help="Poll for new messages.")
    tail_parser.add_argument("--interval", type=int, default=5, help="Poll interval in seconds.")
    tail_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    tail_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    search_parser = subparsers.add_parser("search", help="Search indexed messages.")
    search_parser.add_argument("query", help="Search term.")
    search_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Result limit.")
    search_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    search_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    attachments_parser = subparsers.add_parser("attachments", help="List recent attachments for a chat.")
    attachments_parser.add_argument("chat", help="Chat id, guid, title, or participant query.")
    attachments_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Attachment limit.")
    attachments_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    attachments_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    outbox_parser = subparsers.add_parser("outbox", help="List recent send jobs.")
    outbox_parser.add_argument(
        "--status",
        choices=("queued", "sending", "sent", "failed", "blocked", "dry-run"),
        default="",
        help="Optional job-status filter.",
    )
    outbox_parser.add_argument("--limit", type=int, default=cfg.default_limit, help="Result limit.")
    outbox_parser.add_argument("--no-sync", action="store_true", help="Use the current index without refreshing it first.")
    outbox_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    retry_parser = subparsers.add_parser("retry", help="Retry a previous send job.")
    retry_parser.add_argument("job_id", type=int, help="Send job rowid from imsg outbox.")
    retry_parser.add_argument("--allow-duplicate", action="store_true", help="Bypass duplicate-send protection.")
    retry_parser.add_argument("--allow-first-contact", action="store_true", help="Allow send even without prior contact history.")
    retry_parser.add_argument("--ignore-quiet-hours", action="store_true", help="Bypass quiet-hours blocking for this retry.")
    retry_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    send_parser = subparsers.add_parser("send", help="Send a message via Messages.app.")
    send_parser.add_argument("--to", help="Recipient phone number or email.")
    send_parser.add_argument("--chat", help="Chat id, guid, title, or participant query.")
    send_parser.add_argument("--text", required=True, help="Message text.")
    send_parser.add_argument(
        "--service",
        default="imessage",
        choices=("auto", "imessage", "sms"),
        help="Service type hint.",
    )
    send_parser.add_argument("--idempotency-key", default="", help="Stable key to prevent double-send on retries.")
    send_parser.add_argument("--allow-duplicate", action="store_true", help="Bypass duplicate-send protection.")
    send_parser.add_argument("--allow-first-contact", action="store_true", help="Allow send even without prior contact history.")
    send_parser.add_argument("--ignore-quiet-hours", action="store_true", help="Bypass quiet-hours blocking for this send.")
    send_parser.add_argument("--dry-run", action="store_true", help="Print what would be sent without sending.")
    send_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    reply_parser = subparsers.add_parser("reply", help="Reply in the same chat as a message or explicit chat.")
    reply_target_group = reply_parser.add_mutually_exclusive_group(required=True)
    reply_target_group.add_argument("--message", help="Parent message rowid or guid.")
    reply_target_group.add_argument("--chat", help="Chat id, guid, title, or participant query.")
    reply_parser.add_argument("--text", required=True, help="Message text.")
    reply_parser.add_argument(
        "--service",
        default="imessage",
        choices=("auto", "imessage", "sms"),
        help="Service type hint.",
    )
    reply_parser.add_argument("--idempotency-key", default="", help="Stable key to prevent double-send on retries.")
    reply_parser.add_argument("--allow-duplicate", action="store_true", help="Bypass duplicate-send protection.")
    reply_parser.add_argument("--allow-first-contact", action="store_true", help="Allow send even without prior contact history.")
    reply_parser.add_argument("--ignore-quiet-hours", action="store_true", help="Bypass quiet-hours blocking for this reply.")
    reply_parser.add_argument("--dry-run", action="store_true", help="Print what would be sent without sending.")
    reply_parser.add_argument("--json", action="store_true", help="Print JSON output.")

    send_worker_parser = subparsers.add_parser("send-worker", help="Run the queued-send worker on the bridge host.")
    send_worker_parser.add_argument("--loop", action="store_true", help="Keep polling for queued work.")
    send_worker_parser.add_argument("--poll-interval", type=float, default=DEFAULT_SEND_POLL_INTERVAL_SECONDS, help="Seconds to sleep between queue polls.")

    args = parser.parse_args(argv)

    if args.command == "sync":
        payload = sync_index(cfg, rebuild=args.rebuild, quiet=True)
        emit_payload(payload, args.json, lambda value: json.dumps(value, ensure_ascii=False, indent=2))
        return 0

    if args.command == "doctor":
        payload = doctor_payload(cfg)
        emit_payload(payload, args.json, render_doctor)
        return 0

    if args.command == "send-worker":
        return run_send_worker(
            cfg,
            loop=bool(args.loop),
            poll_interval=float(args.poll_interval),
        )

    sync_first = (
        cfg.sync_on_read
        and args.command in {"contacts", "chats", "unreads", "show", "tail", "search", "attachments", "outbox"}
        and not bool(getattr(args, "no_sync", False))
    )
    with open_index_for_query(cfg, sync_first=sync_first) as con:
        if args.command == "contacts":
            rows = query_contacts(con, args.query, args.limit)
            emit_rows(rows, args.json, render_contacts)
            return 0

        if args.command in {"chats", "unreads"}:
            rows = query_chats(con, args.query, args.limit, unread_only=args.command == "unreads")
            emit_rows(rows, args.json, lambda value: render_chats(value, unread_only=args.command == "unreads"))
            return 0

        if args.command == "show":
            chat_row = resolve_single_chat(con, args.chat)
            chat_payload = chat_payload_from_row(con, chat_row)
            rows = query_messages_for_chat(
                con,
                int(chat_row["rowid"]),
                args.limit,
                before_date=args.before_date,
                before_rowid=args.before_rowid,
            )
            payload = {"chat": chat_payload, "messages": rows}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(render_messages(chat_payload, rows))
            return 0

        if args.command == "tail":
            chat_row = resolve_single_chat(con, args.chat)
            chat_payload = chat_payload_from_row(con, chat_row)
            if not args.follow:
                rows = query_messages_for_chat(con, int(chat_row["rowid"]), args.limit)
                payload = {"chat": chat_payload, "messages": rows}
                if args.json:
                    print(json.dumps(payload, ensure_ascii=False, indent=2))
                else:
                    print(render_messages(chat_payload, rows))
                return 0

            last_seen_date = 0
            first_pass = True
            while True:
                with open_index_for_query(cfg, sync_first=not bool(args.no_sync)) as follow_con:
                    chat_row = resolve_single_chat(follow_con, str(chat_row["rowid"]))
                    chat_payload = chat_payload_from_row(follow_con, chat_row)
                    rows = query_messages_for_chat(
                        follow_con,
                        int(chat_row["rowid"]),
                        args.limit,
                        None if first_pass else last_seen_date,
                    )
                if rows:
                    last_seen_date = max(int(row["date"]) for row in rows)
                    payload = {"chat": chat_payload, "messages": rows}
                    if args.json:
                        print(json.dumps(payload, ensure_ascii=False, indent=2))
                    else:
                        print(render_messages(chat_payload, rows))
                    print("")
                    sys.stdout.flush()
                    first_pass = False
                time.sleep(max(1, args.interval))

        if args.command == "search":
            rows = query_search(con, args.query, args.limit)
            emit_rows(rows, args.json, render_search)
            return 0

        if args.command == "attachments":
            chat_row = resolve_single_chat(con, args.chat)
            chat_payload = chat_payload_from_row(con, chat_row)
            rows = query_attachments_for_chat(con, int(chat_row["rowid"]), args.limit)
            payload = {"chat": chat_payload, "attachments": rows}
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(render_attachments(chat_payload, rows))
            return 0

        if args.command == "outbox":
            rows = query_send_jobs(con, limit=args.limit, status=args.status)
            emit_rows(rows, args.json, render_outbox)
            return 0

    if args.command == "send":
        if not args.to and not args.chat:
            raise SystemExit("send requires --to or --chat")
        payload, exit_code = perform_send_request(
            cfg,
            recipient_input=args.to,
            chat_query=args.chat,
            parent_message_query=None,
            message_text=args.text,
            service_type=args.service,
            dry_run=bool(args.dry_run),
            idempotency_key=args.idempotency_key,
            allow_duplicate=bool(args.allow_duplicate),
            allow_first_contact=bool(args.allow_first_contact),
            ignore_quiet_hours=bool(args.ignore_quiet_hours),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return exit_code

    if args.command == "reply":
        payload, exit_code = perform_send_request(
            cfg,
            recipient_input=None,
            chat_query=args.chat,
            parent_message_query=args.message,
            message_text=args.text,
            service_type=args.service,
            dry_run=bool(args.dry_run),
            idempotency_key=args.idempotency_key,
            allow_duplicate=bool(args.allow_duplicate),
            allow_first_contact=bool(args.allow_first_contact),
            ignore_quiet_hours=bool(args.ignore_quiet_hours),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return exit_code

    if args.command == "retry":
        payload, exit_code = retry_send_job(
            cfg,
            args.job_id,
            allow_duplicate=bool(args.allow_duplicate),
            allow_first_contact=bool(args.allow_first_contact),
            ignore_quiet_hours=bool(args.ignore_quiet_hours),
        )
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return exit_code

    raise SystemExit(f"Unhandled command: {args.command}")


def run_client(argv: list[str]) -> int:
    cfg = load_config()
    local = False
    forwarded = list(argv)
    while forwarded and forwarded[0] == "--local":
        local = True
        forwarded = forwarded[1:]
    if cfg.machine_id == cfg.server_machine_id or local:
        return run_server(forwarded)
    return forward_client_to_server(cfg, forwarded)


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: imsg_app.py <client|server> ...", file=sys.stderr)
        return 1
    mode = sys.argv[1]
    argv = sys.argv[2:]
    if mode == "client":
        return run_client(argv)
    if mode == "server":
        return run_server(argv)
    print(f"unknown mode: {mode}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
