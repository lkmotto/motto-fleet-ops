"""Tests for burn-rate/agent/agent.py — MaritimeFleetAgent and report_action fallback."""

import os
import sys
import logging
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Set required env vars BEFORE any import of agent.agent. The module reads
# env vars at import time and stores them as module-level globals, so they
# must be available when the module is first loaded.
# ---------------------------------------------------------------------------

os.environ.setdefault("SUPABASE_URL", "https://fake-supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "fake-service-key")
os.environ.setdefault("MOTTO_FINANCE_API_KEY", "fake-finance-key")
os.environ.setdefault("OPENAI_API_KEY", "fake-openai-key")
os.environ.setdefault("MAX_COST_PER_RUN", "100.0")

# ---------------------------------------------------------------------------
# Module-level mocking: prevent the agent module from importing real supabase,
# langchain, etc. These MUST be set before any test imports agent.agent.
# ---------------------------------------------------------------------------

# Prevent dotenv from reading real .env files
sys.modules["dotenv"] = MagicMock()
sys.modules["dotenv"].load_dotenv = MagicMock()

# Fake supabase (needed for: import supabase; from supabase import create_client, Client)
fake_supabase = MagicMock()
fake_supabase.create_client = MagicMock()
fake_supabase.Client = MagicMock()
sys.modules["supabase"] = fake_supabase

# Do NOT mock fleet_reporter — we want the ImportError to trigger the
# fallback report_action function defined in agent.py itself.

# Fake langchain_openai (needed for: from langchain_openai import ChatOpenAI)
fake_lc = MagicMock()
fake_lc.ChatOpenAI = MagicMock()
sys.modules["langchain_openai"] = fake_lc

# Fake langchain.prompts (needed for: from langchain.prompts import PromptTemplate)
fake_lp = MagicMock()
fake_lp.PromptTemplate = MagicMock()
sys.modules["langchain.prompts"] = fake_lp
sys.modules["langchain"] = MagicMock()
sys.modules["langchain"].prompts = fake_lp


# ---------------------------------------------------------------------------
# Per-test fixture: prevent /app/logs creation.
# NOTE: We mock logging.FileHandler (not basicConfig) because FileHandler's
# constructor is evaluated as an argument BEFORE basicConfig is called.
# Mocking the class prevents it from trying to open C:\app\logs\...
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_os_and_filehandler(monkeypatch):
    """Prevent the agent module from writing to /app/logs on disk."""
    monkeypatch.setattr(os, "makedirs", MagicMock())
    monkeypatch.setattr(logging, "FileHandler", MagicMock())


# ---------------------------------------------------------------------------
# Helper: build a minimal MaritimeFleetAgent with all constructor deps mocked.
# ---------------------------------------------------------------------------


def _make_agent():
    """Construct a MaritimeFleetAgent with all external services mocked out."""
    burn_rate_dir = os.path.join(os.path.dirname(__file__), "..", "burn-rate")
    sys.path.insert(0, burn_rate_dir)
    from agent.agent import MaritimeFleetAgent

    agent = MaritimeFleetAgent()
    # Replace the supabase client and llm with mocks so no real connections
    agent.supabase = MagicMock()
    agent.llm = MagicMock()
    agent.cost_tracker = 0.0
    return agent


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReportActionFallback:
    """Tests for the module-level report_action fallback defined when
    fleet_reporter is not importable."""

    def test_report_action_is_callable(self):
        """The fallback report_action should exist and be callable."""
        burn_rate_dir = os.path.join(os.path.dirname(__file__), "..", "burn-rate")
        sys.path.insert(0, burn_rate_dir)
        import agent.agent as agent_module

        assert callable(agent_module.report_action)

    def test_report_action_runs_without_error(self):
        """report_action should accept a float cost_usd and not raise any error."""
        burn_rate_dir = os.path.join(os.path.dirname(__file__), "..", "burn-rate")
        sys.path.insert(0, burn_rate_dir)
        import agent.agent as agent_module

        # report_action calls logging.info. It should not raise.
        result = agent_module.report_action(12.34)
        assert result is None


class TestAggregateCosts:
    """Tests for MaritimeFleetAgent._aggregate_costs — the core cost-aggregation logic."""

    def test_empty_dataframe_returns_defaults(self):
        """An empty DataFrame should produce a structured zero/default result."""
        agent = _make_agent()
        result = agent._aggregate_costs(pd.DataFrame())

        assert isinstance(result, dict), "result should be a dict"
        assert result["total_daily_spend"] == 0
        assert result["burn_rate"] == 0
        assert result["anomalies"] == []
        # When the df is empty, the method returns "vessels" key (not "active_vessels")
        assert result.get("vessels", {}) == {}

    def test_dataframe_with_cost_data_aggregates_correctly(self):
        """A DataFrame with cost entries should produce correct aggregations."""
        agent = _make_agent()
        df = pd.DataFrame(
            [
                {"cost_usd": 10.0, "vessel_name": "alpha", "category": "compute"},
                {"cost_usd": 20.0, "vessel_name": "beta", "category": "storage"},
                {"cost_usd": 5.0, "vessel_name": "alpha", "category": "compute"},
            ]
        )
        result = agent._aggregate_costs(df)

        assert result["total_daily_spend"] == 35.0
        assert result["total_transactions"] == 3
        assert result["active_vessels"] == 2
        assert result["burn_rate"] == 35.0 / 2
        assert "vessel_metrics" in result
        assert "category_breakdown" in result

    def test_dataframe_without_cost_column_raises_keyerror(self):
        """When cost_usd column is absent, _aggregate_costs raises KeyError
        because it accesses df['cost_usd'] directly. The guard for this
        lives in _query_previous_day_costs, not _aggregate_costs itself."""
        agent = _make_agent()
        df = pd.DataFrame([{"other_col": 1, "vessel_name": "ghost"}])

        with pytest.raises(KeyError):
            agent._aggregate_costs(df)
