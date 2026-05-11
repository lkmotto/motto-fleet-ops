#!/usr/bin/env python3
"""Parse a provision request from one of three triggers and emit GITHUB_OUTPUT lines."""
import sys as _sys, pathlib as _pathlib  # noqa: E402
_sys.path.insert(0, str(_pathlib.Path(__file__).resolve().parent.parent))
import sentry_init  # noqa: E402,F401

import json
import os
import re
import sys
import uuid


def emit(key: str, val: str) -> None:
    # Use the multi-line GITHUB_OUTPUT delimiter for safety.
    delim = uuid.uuid4().hex
    print(f"{key}<<{delim}\n{val}\n{delim}")


def parse_body(body: str):
    """Body format:
    secrets:
      - KEY1
      - KEY2
    reason: free text
    """
    secrets = []
    reason = ""
    in_secrets = False
    for line in (body or "").splitlines():
        s = line.strip()
        if s.lower().startswith("secrets:"):
            in_secrets = True
            continue
        if s.lower().startswith("reason:"):
            in_secrets = False
            reason = s.split(":", 1)[1].strip()
            continue
        if in_secrets:
            m = re.match(r"^-\s*([A-Za-z0-9_]+)\s*$", s)
            if m:
                secrets.append(m.group(1))
    return secrets, reason


def main() -> int:
    event = os.environ.get("EVENT_NAME", "")
    request_id = uuid.uuid4().hex[:12]
    target_repo = ""
    secret_names: list[str] = []
    reason = ""
    issue_repo = ""
    issue_number = ""

    if event == "workflow_dispatch":
        target_repo = os.environ.get("INPUT_TARGET", "").strip()
        secret_names = [s.strip() for s in os.environ.get("INPUT_SECRETS", "").split(",") if s.strip()]
        reason = os.environ.get("INPUT_REASON", "manual dispatch")

    elif event == "repository_dispatch":
        payload_raw = os.environ.get("DISPATCH_PAYLOAD", "{}")
        try:
            payload = json.loads(payload_raw)
        except Exception:
            payload = {}
        target_repo = payload.get("target_repo", "")
        secret_names = payload.get("secrets", [])
        reason = payload.get("reason", "")
        issue_repo = payload.get("issue_repo", "")
        issue_number = str(payload.get("issue_number", ""))

    elif event == "issues":
        issue_title = os.environ.get("ISSUE_TITLE", "")
        body = os.environ.get("ISSUE_BODY", "")
        issue_repo = os.environ.get("ISSUE_REPO", "")
        issue_number = os.environ.get("ISSUE_NUMBER", "")
        # Title format: [provision] <repo-name> needs <reason>
        m = re.match(r"^\[provision\]\s+(\S+)", issue_title)
        if m:
            target_repo = m.group(1)
            if "/" not in target_repo:
                target_repo = f"lkmotto/{target_repo}"
        secret_names, reason = parse_body(body)

    if not target_repo or not secret_names:
        sys.stderr.write(f"could not parse request: target_repo={target_repo!r} secrets={secret_names!r}\n")
        sys.exit(1)

    emit("request_id", request_id)
    emit("target_repo", target_repo)
    emit("secret_names", " ".join(secret_names))
    emit("reason", reason)
    emit("issue_repo", issue_repo)
    emit("issue_number", issue_number)
    return 0


if __name__ == "__main__":
    import sentry_sdk as _sentry_sdk
    try:
        sys.exit(main())
    except Exception as _exc:
        _sentry_sdk.capture_exception(_exc)
        raise

