"""Investigation graph execution runner with failure recovery and audit tracking.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from .builder import build_investigation_graph
from ..providers.base import AIProvider, AIProviderError
from ..schemas import AIExecutionError
from ..state import InvestigationState

logger = logging.getLogger("traceiq.ai")


def run_investigation_graph(
    initial_state: InvestigationState,
    provider: AIProvider | None = None,
) -> InvestigationState:
    """Execute the LangGraph investigation workflow with safe failure handling."""
    started_at = datetime.now(timezone.utc)
    inv_id = initial_state.get("incident", {}).get("id", "unknown")

    try:
        graph = build_investigation_graph(provider=provider)
        final_state: InvestigationState = graph.invoke(initial_state)
        return final_state

    except Exception as exc:
        logger.warning(
            "AI investigation graph execution failed for incident %s: %s. Initiating fallback.",
            inv_id,
            exc,
        )
        # Create safe fallback state
        fallback_state = dict(initial_state)
        errors = list(fallback_state.get("errors", []))
        errors.append({
            "node_name": "graph_runner",
            "error_type": type(exc).__name__,
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recovered": True,
        })
        fallback_state["errors"] = errors

        metadata = dict(fallback_state.get("metadata", {}))
        metadata["deterministic_fallback"] = True
        metadata["completed_at"] = datetime.now(timezone.utc).isoformat()
        fallback_state["metadata"] = metadata

        return fallback_state  # type: ignore[return-value]
