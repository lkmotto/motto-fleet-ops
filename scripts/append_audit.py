#!/usr/bin/env python3
"""Append a single JSON line to audit/provision-log.jsonl."""
import json
import os
import pathlib
import time

entry = {
    "ts": int(time.time()),
    "request_id": os.environ.get("REQUEST_ID", ""),
    "target_repo": os.environ.get("TARGET_REPO", ""),
    "requested": os.environ.get("SECRET_NAMES", "").split(),
    "granted": os.environ.get("GRANTED", "").split(),
    "missing": os.environ.get("MISSING", "").split(),
    "reason": os.environ.get("REASON", ""),
    "status": os.environ.get("STATUS", ""),
}

p = pathlib.Path("audit/provision-log.jsonl")
p.parent.mkdir(parents=True, exist_ok=True)
with p.open("a", encoding="utf-8") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
print("appended", entry["request_id"])
