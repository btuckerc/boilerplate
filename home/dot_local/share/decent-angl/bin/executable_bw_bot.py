#!/usr/bin/env python3
"""Grok Bots secrets: op-secret pinned to the "Grok Bots" vault and its token.

Kept under its old name because bot instructions call it. Same interface as
op-secret (status, field, write-env, exec, ref); see `op-secret --help`.
Token: ~/.local/share/decent-angl/secrets/op-grok-bots.env (read-only service
account grok-bots-agents), overridable with GROK_BOTS_OP_ENV; the vault with
GROK_BOTS_VAULT.
"""
import os
import sys

home = os.path.expanduser("~")
os.environ["OP_SECRET_ENV"] = os.environ.get(
    "GROK_BOTS_OP_ENV", os.path.join(home, ".local/share/decent-angl/secrets/op-grok-bots.env"))
os.environ["OP_SECRET_VAULTS"] = os.environ.get("GROK_BOTS_VAULT", "Grok Bots")
helper = os.path.join(home, ".local/bin/op-secret")
if sys.argv[1:2] in (["add"], ["enroll"]):
    sys.stderr.write("bw_bot.py is read-only; add Grok Bots items in 1Password directly.\n")
    raise SystemExit(2)
os.execv(sys.executable, [sys.executable, helper] + sys.argv[1:])
