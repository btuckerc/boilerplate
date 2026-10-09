"""Wake Grok Bot when an agent it started (name prefix `gb-`) settles.

Hook for pane.agent_status_changed. Fires on the event's own `done` or
`blocked` status (herdr's `done` = completed work not yet seen; startup and
restore idles never report it). One POST per transition, deduped on
completion_seq, falling back to state_change_seq (herdr 0.9.1 exposes only
the latter). Sends a short email (subject `herdr <agent> <status>`, JSON
body) over SMTP. Config: ~/.config/herdr-grokbot/mail.env with SMTP_HOST,
SMTP_PORT (465 = implicit TLS, else STARTTLS when offered), SMTP_USER,
SMTP_PASS, MAIL_FROM, MAIL_TO. Missing file or keys: quiet no-op.
"""

import fcntl
import json
import os
import smtplib
import subprocess
from email.message import EmailMessage

ENV_FILE = os.path.expanduser(
    os.environ.get("HERDR_GROKBOT_ENV", "~/.config/herdr-grokbot/mail.env")
)
HERDR = os.environ.get("HERDR_BIN_PATH", "herdr")
PREFIX = "gb-"


def load_env():
    env = {}
    try:
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip().removeprefix("export ").strip()] = v.strip().strip("'\"")
    except FileNotFoundError:
        pass
    return env


def find(obj, key):
    """First value for `key` anywhere in the event JSON."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        obj = list(obj.values())
    if isinstance(obj, list):
        for v in obj:
            r = find(v, key)
            if r is not None:
                return r
    return None


def main():
    event = json.loads(os.environ.get("HERDR_PLUGIN_EVENT_JSON") or "{}")
    status = find(event, "agent_status")
    if status not in ("done", "blocked"):
        return
    pane = find(event, "pane_id")
    env = load_env()
    if not pane or not all(env.get(k) for k in ("SMTP_HOST", "MAIL_FROM", "MAIL_TO")):
        return
    got = subprocess.run([HERDR, "agent", "get", pane], capture_output=True, text=True)
    if got.returncode:
        return
    agent = json.loads(got.stdout)["result"]["agent"]
    name = agent.get("name") or ""
    if not name.startswith(PREFIX):
        return
    seq = agent.get("completion_seq") or agent.get("state_change_seq")

    state_dir = os.environ.get("HERDR_PLUGIN_STATE_DIR", "/tmp")
    os.makedirs(state_dir, exist_ok=True)
    mark = os.path.join(state_dir, f"sent-{name}")
    tag = f"{status}:{seq}"
    with open(os.path.join(state_dir, "notify.lock"), "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(mark) as f:
                if f.read() == tag:
                    return
        except FileNotFoundError:
            pass
        msg = EmailMessage()
        msg["Subject"] = f"herdr {name} {status}"
        msg["From"], msg["To"] = env["MAIL_FROM"], env["MAIL_TO"]
        msg.set_content(json.dumps({
            "agent": name,
            "status": status,
            "workspace": agent.get("workspace_id"),
            "tab": agent.get("tab_id"),
            "completion_seq": seq,
        }, indent=1))  # short lines keep the body 7bit, not quoted-printable
        try:
            send(env, msg)
        except Exception as e:  # never echo credentials, only the error type
            print(f"{name} {tag} -> send failed: {type(e).__name__}")
            return
        with open(mark, "w") as f:
            f.write(tag)
        print(f"{name} {tag} -> sent")


def send(env, msg):
    host, port = env["SMTP_HOST"], int(env.get("SMTP_PORT") or 465)
    if port == 465:
        smtp = smtplib.SMTP_SSL(host, port, timeout=10)
    else:
        smtp = smtplib.SMTP(host, port, timeout=10)
        smtp.ehlo()
        if smtp.has_extn("starttls"):
            smtp.starttls()
    with smtp:
        if env.get("SMTP_USER"):
            smtp.login(env["SMTP_USER"], env.get("SMTP_PASS", ""))
        smtp.send_message(msg)


if __name__ == "__main__":
    main()
