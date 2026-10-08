"""Service topology definitions for TRACEIQ synthetic environment.

Provides deterministic dependency graph models to calculate blast radius,
upstream caller chains, and downstream dependencies without LLM hallucination.
"""
from __future__ import annotations

# All valid services in the synthetic microservices architecture
ALL_SERVICES: frozenset[str] = frozenset({
    "api-gateway",
    "order-service",
    "payment-service",
    "orders-db",
    "payments-db",
    "redis-cache",
    "payment-provider-api",
})

# Direct downstream dependencies (service -> what it depends on)
DOWNSTREAM_DEPENDENCIES: dict[str, list[str]] = {
    "api-gateway": ["order-service", "payment-service"],
    "order-service": ["orders-db", "redis-cache"],
    "payment-service": ["payments-db", "payment-provider-api"],
    "orders-db": [],
    "payments-db": [],
    "redis-cache": [],
    "payment-provider-api": [],
}

# Direct upstream callers (service -> what calls it)
UPSTREAM_CALLERS: dict[str, list[str]] = {
    "api-gateway": [],
    "order-service": ["api-gateway"],
    "payment-service": ["api-gateway"],
    "orders-db": ["order-service"],
    "payments-db": ["payment-service"],
    "redis-cache": ["order-service"],
    "payment-provider-api": ["payment-service"],
}

# Critical tier classifications
CRITICAL_SERVICES: frozenset[str] = frozenset({
    "api-gateway",
    "orders-db",
    "payments-db",
})


def get_all_upstream_callers(service: str) -> list[str]:
    """Recursively discover all upstream callers up to the edge gateway."""
    visited: set[str] = set()
    queue = list(UPSTREAM_CALLERS.get(service, []))
    while queue:
        curr = queue.pop(0)
        if curr not in visited and curr in ALL_SERVICES:
            visited.add(curr)
            for caller in UPSTREAM_CALLERS.get(curr, []):
                if caller not in visited:
                    queue.append(caller)
    return sorted(list(visited))


def get_all_downstream_dependencies(service: str) -> list[str]:
    """Recursively discover all downstream dependencies."""
    visited: set[str] = set()
    queue = list(DOWNSTREAM_DEPENDENCIES.get(service, []))
    while queue:
        curr = queue.pop(0)
        if curr not in visited and curr in ALL_SERVICES:
            visited.add(curr)
            for dep in DOWNSTREAM_DEPENDENCIES.get(curr, []):
                if dep not in visited:
                    queue.append(dep)
    return sorted(list(visited))
