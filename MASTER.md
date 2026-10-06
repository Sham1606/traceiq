# TRACEIQ — MASTER BUILD PLAN

## Mission
Build TRACEIQ as a high-quality synthetic-data-driven collaborative AI incident investigation platform.

Core workflow:
Incident → Evidence → Historical Memory → Investigation → Correlation → Competing Hypotheses → Challenge → RCA → Recovery Recommendation → Human Approval → Simulation → Audit → Postmortem → Incident Memory.

Core principle:
> Deterministic code establishes evidence. AI reasons over evidence. Humans approve recovery.

## Delivery Constraint
Approximately 3 calendar days with fragmented work time. Prefer a smaller complete workflow over many incomplete features. Testing is part of every development phase.

## Synthetic Data Policy
No real production data is required. Data must be synthetic but production-plausible:
- internally consistent timestamps
- realistic baseline noise
- believable logs/metrics/deployments/configuration
- normal, incident and recovery periods
- supporting AND contradicting evidence
- plausible false leads
- causal relationships
- hidden ground truth for tests only
- no cartoonishly obvious root-cause clues
- no impossible metric combinations
- no random values without meaning

Ground truth MUST NOT be exposed through normal investigation APIs.

## Incident MVP
1. Bad deployment / application regression
2. Database degradation
3. External dependency failure
4. Configuration regression

First three are primary demo scenarios. Fourth can be live/hidden fault injection after the core workflow is stable.

## Incident Memory
Completed incidents become reusable organizational knowledge.

Store:
- incident fingerprint
- RCA
- evidence summary
- recovery recommendation
- actual recovery outcome

Retrieve similar incidents and compare historical evidence with current evidence.

Historical knowledge is supporting evidence, never automatic truth:
historical match → current evidence comparison → validation → recommendation → human approval.

## AI vs Deterministic Responsibilities
AI:
- investigation planning
- specialized investigation
- evidence explanation
- hypothesis generation
- correlation explanation
- challenge reasoning
- historical incident interpretation
- recovery explanation
- postmortem generation

Deterministic:
- metric/timeline/log calculations
- normalization
- change detection
- evidence scoring
- scenario ground truth
- hypothesis checks
- recovery simulation
- audit persistence
- historical fingerprints/similarity

LLM output must be structured and validated.

## Evidence
Every RCA claim must reference evidence.

Use labels:
- Strongly supported
- Supported
- Inconclusive
- Weakly supported
- Rejected

Avoid arbitrary probability percentages.

## Human Approval
Recovery is never autonomous:
recommendation → evidence → approval → simulation → recorded outcome.

## Testing
Every feature needs relevant tests:
- Unit: pure logic
- Integration: API/database/services
- AI: schemas, malformed output, missing evidence, contradictions, fallback
- Scenario: expected root cause/evidence/challenge/recovery
- E2E: complete investigation and recovery flow

## Quality Gates
A Foundation: app starts, health works, tests run.
B Data: all scenarios load; ground truth hidden.
C Evidence: deterministic engine works without LLM.
D Investigation: hypotheses + genuine challenge + structured AI output.
E Memory: historical retrieval works; no blind reuse.
F Recovery: approval + simulation + audit.
G UI: complete workflow works.
H Demo: primary scenarios, fallback, reset/reseed, no critical errors.

## Execution Order
1. Foundation
2. Data contracts
3. Synthetic scenarios
4. Deterministic evidence engine
5. Backend APIs
6. Incident memory
7. AI orchestration
8. Hypothesis/challenge
9. Recovery/audit
10. Frontend
11. Testing hardening
12. Demo hardening

## MVP Exclusions
Do not add unless the core workflow is complete:
real Kubernetes, Prometheus/Grafana, Elasticsearch/OpenSearch, Neo4j, MCP infrastructure, autonomous remediation, complex RBAC/SSO, multi-tenancy, fine-tuning, complex vector infrastructure, full compliance reporting, real-time collaboration.

## Definition of Done
A task is done only when implementation, relevant tests, passing results, failure handling, and required documentation are complete.

## Agent Rule
Before coding: read AGENTS.md → nearest TASKS.md → inspect existing code/tests → implement smallest correct change → run tests → report files/tests/risks/next task. Do not silently expand scope.
