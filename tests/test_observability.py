"""Tests for burn-rate/observability.py — OpenTelemetry + Langfuse scaffolding."""

import os
import sys
from unittest.mock import patch


def test_init_observability_returns_tracer():
    """init_observability should return a tracer with the given service name."""
    # Ensure no pre-existing TracerProvider confuses the idempotency check
    from opentelemetry import trace

    # Reset global tracer provider to ensure clean state
    trace._TRACER_PROVIDER = None

    # Add burn-rate to path so we can import observability
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "burn-rate"))
    from observability import init_observability

    tracer = init_observability("test-service")

    # Should return a tracer — not None, not a string
    assert tracer is not None
    assert hasattr(tracer, "start_span") or hasattr(tracer, "start_as_current_span")


def test_init_observability_idempotent():
    """Calling init_observability twice should not crash and should return a tracer."""
    from opentelemetry import trace

    trace._TRACER_PROVIDER = None

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "burn-rate"))
    from observability import init_observability

    t1 = init_observability("svc-a")
    t2 = init_observability("svc-a")

    assert t1 is not None
    assert t2 is not None
    # Both should be tracer objects (even if different instances after idempotency)
    assert hasattr(t1, "start_span") or hasattr(t1, "start_as_current_span")
    assert hasattr(t2, "start_span") or hasattr(t2, "start_as_current_span")
