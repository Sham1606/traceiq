# AI Tasks
- [x] A001 Phase 5.1: AI Foundation, provider abstraction, investigation state, LangGraph orchestration skeleton, evidence-reference validation, ground-truth protection, and deterministic fallback.
- [x] A002 Phase 5.2: Investigation Planner + Specialized investigators (Application, Database, Deployment, Dependency) with evidence-driven planning, domain-filtered evidence views, failure isolation, and real evidence ID grounding.
- [x] A003 Phase 5.3: Cross-investigator evidence correlation engine (CorrelationFinding, false-lead detection, causal sequence, shared signal detection).
- [x] A004 Phase 5.3: Adversarial Challenge Agent capable of REJECTED status. Deterministic falsification logic: contradictions > support → REJECTED, zero evidence + no timeline → REJECTED, weak + no cross-domain signals + false leads → REJECTED.
- [x] A005 Phase 5.3: Historical incident reasoning — fingerprint-based similarity, annotation-only enrichment (never overrides hypothesis strength or evidence IDs), historical_override=False enforced.
- [ ] A006 Phase 5.4: Recovery advisor and simulation validator.
- [ ] A007 Phase 5.4: Postmortem draft generation.


## Test Coverage
- Schemas & Pydantic models (validation, forbidden extra fields, evidence references)
- State creation, serialization, transitions, missing optional fields
- Provider abstraction (MockAIProvider: success, timeout, rate limit, error, empty, malformed, domain-aware fixtures, investigator-level failure injection)
- Planner reasoning & validation (evidence-grounded steps, non-empty reasons, priority 1-10, cycle detection, duplicate rejection)
- Specialized investigators (filtered domain boundaries, valid evidence IDs, missing evidence handling)
- LangGraph orchestration & failure isolation (single investigator failure doesn't break pipeline, errors recorded with recovered=True)
- Four-scenario verification (bad-deployment, database-degradation, external-dependency, configuration-regression executed and verified)
- Ground truth isolation (strict firewall ensures no hidden answer keys enter state or findings)
- Deterministic fallback (service continues seamlessly when AI is disabled or fails)


