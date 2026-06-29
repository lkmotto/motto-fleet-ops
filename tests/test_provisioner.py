"""Tests for provisioner/scripts — parse_request.py and append_audit.py."""

import io
import json
import os
import sys
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Module-level mocking for motto_common and sentry_sdk (needed by parse_request.py)
# ---------------------------------------------------------------------------

fake_motto = MagicMock()
fake_motto.sentry_init = MagicMock()
fake_motto.sentry_init.init_sentry = MagicMock()
sys.modules["motto_common"] = fake_motto
sys.modules["motto_common.sentry_init"] = fake_motto.sentry_init

fake_sentry = MagicMock()
sys.modules["sentry_sdk"] = fake_sentry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCRIPTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "provisioner", "scripts"
)


def _get_parse_body():
    """Import and return parse_request.parse_body."""
    sys.path.insert(0, SCRIPTS_DIR)
    import parse_request

    return parse_request.parse_body


# ---------------------------------------------------------------------------
# parse_body tests
# ---------------------------------------------------------------------------


class TestParseBody:
    """Tests for parse_request.parse_body — the issue body parser."""

    def test_parses_secrets_and_reason(self):
        """Standard body with secrets and reason should be parsed correctly."""
        parse_body = _get_parse_body()
        body = """secrets:
  - OPENAI_API_KEY
  - SUPABASE_URL
reason: provisioning for burn-rate agent
"""
        secrets, reason = parse_body(body)

        assert secrets == ["OPENAI_API_KEY", "SUPABASE_URL"]
        assert reason == "provisioning for burn-rate agent"

    def test_empty_body_returns_empty_lists(self):
        """An empty or None body should return empty secrets and reason."""
        parse_body = _get_parse_body()
        secrets, reason = parse_body("")

        assert secrets == []
        assert reason == ""

        secrets2, reason2 = parse_body(None)

        assert secrets2 == []
        assert reason2 == ""

    def test_body_with_no_secrets_section(self):
        """Body with no 'secrets:' line should yield empty secrets."""
        parse_body = _get_parse_body()
        body = "just some text\nno structured data here"
        secrets, reason = parse_body(body)

        assert secrets == []

    def test_body_with_only_secrets_section(self):
        """Body with only a secrets section (no reason) should parse secrets, empty reason."""
        parse_body = _get_parse_body()
        body = """secrets:
  - KEY_ONE
  - KEY_TWO
"""
        secrets, reason = parse_body(body)

        assert secrets == ["KEY_ONE", "KEY_TWO"]
        assert reason == ""

    def test_reason_without_secrets(self):
        """Body with reason but no secrets should return empty secrets and the reason."""
        parse_body = _get_parse_body()
        body = "reason: just testing something"
        secrets, reason = parse_body(body)

        assert secrets == []
        assert reason == "just testing something"


# ---------------------------------------------------------------------------
# emit tests
# ---------------------------------------------------------------------------


class TestEmit:
    """Tests for parse_request.emit — GITHUB_OUTPUT multi-line emitter."""

    def test_emit_produces_delimited_output(self):
        """emit should print a key with a multi-line delimiter."""
        sys.path.insert(0, SCRIPTS_DIR)
        import parse_request

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            parse_request.emit("request_id", "abc123")

        output = captured.getvalue()
        assert "request_id" in output
        assert "abc123" in output
        # Should have 3 lines: key<<delim, value, delim
        lines = [line for line in output.strip().split("\n") if line]
        assert len(lines) >= 2  # At minimum key+delim and value


# ---------------------------------------------------------------------------
# append_audit tests
# ---------------------------------------------------------------------------


class TestAppendAudit:
    """Tests for append_audit.py — audit log appender."""

    def test_appends_json_line_to_audit_log(self, monkeypatch, tmp_path):
        """Running append_audit.py with env vars set should create an audit entry."""
        # Change working directory to tmp_path so the script creates audit/ there
        monkeypatch.chdir(tmp_path)

        test_env = {
            "REQUEST_ID": "req-001",
            "TARGET_REPO": "lkmotto/test-repo",
            "SECRET_NAMES": "KEY_A KEY_B",
            "GRANTED": "KEY_A",
            "MISSING": "KEY_B",
            "REASON": "need keys for agent",
            "STATUS": "partial",
        }

        with patch.dict(os.environ, test_env, clear=True):
            script_path = os.path.join(SCRIPTS_DIR, "append_audit.py")
            with open(script_path) as f:
                code = compile(f.read(), script_path, "exec")
                exec(code, {"__name__": "__main__"})

        # Verify the audit file was created and contains valid JSON
        audit_file = tmp_path / "audit" / "provision-log.jsonl"
        assert audit_file.exists(), f"Audit file not found at {audit_file}"

        line = audit_file.read_text(encoding="utf-8").strip()
        entry = json.loads(line)

        assert entry["request_id"] == "req-001"
        assert entry["target_repo"] == "lkmotto/test-repo"
        assert entry["requested"] == ["KEY_A", "KEY_B"]
        assert entry["granted"] == ["KEY_A"]
        assert entry["missing"] == ["KEY_B"]
        assert entry["status"] == "partial"
        assert isinstance(entry["ts"], int)
