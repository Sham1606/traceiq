# AI Tasks
- [x] A001 Phase 5.1: AI Foundation, provider abstraction, investigation state, LangGraph orchestration skeleton, evidence-reference validation, ground-truth protection, and deterministic fallback.
- [ ] A002 Phase 5.2: Specialized investigators (Application, Database, Dependency).
- [ ] A003 Phase 5.2: Evidence correlation and competing hypothesis generator.
- [ ] A004 Phase 5.3: Challenge agent capable of REJECTED status.
- [ ] A005 Phase 5.3: Historical incident reasoning without blind reuse.
- [ ] A006 Phase 5.4: Recovery advisor and simulation validator.
- [ ] A007 Phase 5.4: Postmortem draft generation.

## Test Coverage
- Schemas & Pydantic models (validation, forbidden extra fields, evidence references)
- State creation, serialization, transitions, missing optional fields
- Provider abstraction (MockAIProvider: success, timeout, rate limit, error, empty, malformed)
- Ground truth isolation (assert no hidden answers leak into AI state/prompts)
- Deterministic fallback (service continues when AI is disabled or fails)

