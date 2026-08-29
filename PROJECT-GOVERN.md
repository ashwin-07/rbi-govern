# Project GOVERN — Regulatory Change Copilot
### Lane 1 · Buckets A (Building) + B (Assurance) + D (FDSE)
*Weeks 1–6, 14–17 · ~62 hours + 12h FDSE lane*

---

## What you're building

> A mid-size Indian bank's compliance team of nine fields questions like *"what is the current KYC requirement for video-based customer identification?"* Answering correctly means tracing a chain of RBI amendments across several years. It takes a senior analyst half a day and the answer is sometimes stale. Getting it wrong carries regulatory penalties.

You're building the system that answers those questions correctly, proves it's correct, and can show a regulator exactly how it got there.

## Why this project earns its place

**The technical centrepiece:** RBI instructions form an *amendment graph over time*. A 2016 Master Direction is amended in 2018, partially superseded in 2021, a clause withdrawn in 2023. A vector search for "video KYC" will confidently return the 2016 text — **correctly cited, and wrong.**

Naive RAG demonstrably fails here. That gives you a before/after story instead of "it works."

## Definition of done (whole project)

- [ ] Point-in-time retrieval answering "what was in force on date X?"
- [ ] Measured accuracy improvement, naive baseline vs amendment-aware
- [ ] Agent completing a 6+ step task with a human approval gate
- [ ] MCP server exposing the tools
- [ ] CI-gated eval suite with a judge validated against your own labels
- [ ] OpenTelemetry traces of agent runs with per-span cost
- [ ] Audit trail reconstructable months later
- [ ] Governance pack: model card, EU AI Act classification, failure-mode register
- [ ] Thin React frontend you can screenshare
- [ ] Three written case studies, rehearsed aloud

---

## Read before Week 1 (~1h, counts against Week 1)

- [ ] ⭐⭐ [Hamel Husain — Your AI Product Needs Evals](https://hamel.dev/blog/posts/evals/)

> Read this *first*, not in Week 14. It changes how you build the golden set in Week 2, and a badly-built golden set poisons everything downstream. Note his correction: use precision/recall, not raw agreement, when classes are imbalanced.

- [ ] ⭐⭐ [Anthropic — Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — skim now, re-read properly in Week 5. **Appendix 2 on tool design** is the part to remember.

---

# Week 1 — LLM APIs + corpus ingestion (7h)

### Learn (2.5h)

- [ ] 📄 [Claude docs](https://platform.claude.com/docs) — Messages API, **tool calling**, **structured outputs**, streaming, prompt caching, token counting
- [ ] 📄 [OpenAI docs](https://developers.openai.com/) — enough to compare API surfaces; you should be able to speak to both
- [ ] ⭐ [Anthropic Prompt Engineering](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/overview)
- [ ] ⭐ [Anthropic Cookbook](https://github.com/anthropics/anthropic-cookbook) — run two notebooks, don't just read
- [ ] ⭐ [Simon Willison — prompt injection](https://simonwillison.net/tags/prompt-injection/) — skim the archive for failure-mode intuition

### Build (4.5h)

- [ ] Scrape RBI KYC/AML circulars — [Master Directions](https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx) and [Notifications](https://www.rbi.org.in/Scripts/NotificationUser.aspx)
- [ ] Extract text — [PyMuPDF](https://pymupdf.readthedocs.io/) for bulk, [pdfplumber](https://github.com/jsvine/pdfplumber) for tables
- [ ] Normalise into Postgres: `circular_number`, `issue_date`, `title`, `category`, `raw_text`, `source_url`
- [ ] Write a cost-tracking wrapper around your LLM client — logs tokens and cost per call to Postgres

> ⚠️ **RBI has no API and nobody has written a guide.** That's deliberate — figuring out the site structure is the data-wrangling skill these roles test. **Hard-stop at 5h.** Sixty documents is enough for everything downstream.

### Done when

- [ ] `documents` table with 60–100 real records
- [ ] `DATA-NOTES.md` logging every mess: scanned pages, inconsistent numbering, tables that broke extraction
- [ ] Every LLM call you make from here is cost-tracked

---

# Week 2 — Retrieval + the golden set (7h)

### Learn (2h)

- [ ] ⭐ [Anthropic — Contextual Retrieval](https://www.anthropic.com/engineering/contextual-retrieval) — **the best free production-RAG writeup.** Hybrid BM25+embeddings, why chunking destroys context, reranking. Real numbers: 49% and 67% reductions in retrieval failure.
- [ ] ⭐ [Contextual Embeddings cookbook](https://platform.claude.com/cookbook/capabilities-contextual-embeddings-guide)
- [ ] 📄 [pgvector README](https://github.com/pgvector/pgvector) — HNSW vs IVFFlat, distance operators
- [ ] 📄 [rank_bm25](https://github.com/dorianbrown/rank_bm25)
- [ ] ⭐ [Eugene Yan — LLM Patterns](https://eugeneyan.com/writing/llm-patterns/) — retrieval and eval sections

> ⚠️ **Chunking-strategy comparisons have no canonical source** — vendor blogs each conclude their product wins. Your own benchmark on your own corpus is the point, and it's more credible in an interview than citing anyone.

### Build (5h)

- [ ] pgvector with an HNSW index
- [ ] Three chunking strategies, switchable: fixed-size, recursive-semantic, **clause-hierarchy-aware** (RBI docs are numbered hierarchically — that hierarchy carries meaning)
- [ ] Hybrid BM25 + dense retrieval
- [ ] Reranking pass
- [ ] **Hand-build a 40-question golden set** with known-correct source clauses

> The golden set is tedious and you'll want to skip it. Don't. **Include at least 10 questions where the correct answer differs from what naive search returns** — those ten are your Week 4 demo.

### Done when

- [ ] Benchmark table: three chunking strategies × recall@5, recall@20, MRR
- [ ] Golden set committed to git as versioned data
- [ ] `RESULTS.md` created, first numbers in it

### Record

`RESULTS.md`: recall@5 and @20 per strategy · which strategy won and your hypothesis for why

---

# Week 3 — The amendment graph (7h)

### Learn (1.5h)

- [ ] 📄 Structured extraction via tool-calling / JSON schema — [Claude docs](https://platform.claude.com/docs), and read [Instructor](https://github.com/567-labs/instructor) for its design even if you don't use it
- [ ] 📄 [Martin Fowler — Patterns for Things That Change With Time](https://martinfowler.com/eaaDev/timeNarrative.html) — effective dating, bitemporal modelling
- [ ] 📄 [PostgreSQL recursive CTEs](https://www.postgresql.org/docs/current/queries-with.html)

> ⚠️ **The supersession problem has no literature.** Regulatory amendment-graph modelling for RAG isn't a written-up problem — commercial products keep it private. **That's why this project is distinctive.** Design it from the temporal-modelling primitives yourself.

### Build (5.5h)

- [ ] LLM extraction of amendment references from circular preambles ("this partially supersedes circular X dated Y") into typed records
- [ ] Directed graph in Postgres: `amends`, `supersedes`, `withdraws` edges
- [ ] `effective_from` / `effective_until` per clause
- [ ] **Measure extraction accuracy** against a hand-checked sample — this is a sub-eval and a good one

### Done when

- [ ] Amendment graph populated and queryable
- [ ] Extraction accuracy number recorded
- [ ] You can traverse "what amended this clause?" in SQL

---

# Week 4 — Point-in-time retrieval + your headline number (7h)

### Build (7h)

- [ ] Point-in-time filtering — retrieve only what was in force on a given date
- [ ] Graph traversal during synthesis: a retrieved clause surfaces what later amended it
- [ ] Confidence flagging where the amendment chain is ambiguous — **flag for human review rather than guessing**
- [ ] **Run naive baseline vs amendment-aware on the full golden set**, especially those 10 stale-answer questions

### Done when

- [ ] Before/after accuracy table in `RESULTS.md`
- [ ] You can demo a question where naive returns 2016 text and yours returns the current position

### The interview claim this produces

> *"Naive retrieval was 68% accurate — and worse, its errors were confidently-worded stale regulations, which is the worst failure mode for a compliance user. Modelling the amendment graph and adding point-in-time filtering took it to 91%. The remaining failures are cases where the RBI text itself is genuinely ambiguous, so the system flags them for human review instead of guessing."*

Fill in your real numbers. **This is the single most valuable sentence in your portfolio.**

---

# Week 5 — Hand-rolled agent (7h)

### Learn (1.5h)

- [ ] ⭐⭐ [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents) — properly this time. Workflows vs agents, the five patterns, **Appendix 2 on tool design**.
- [ ] 🔬 [ReAct paper](https://arxiv.org/abs/2210.03629) — sections 1–3
- [ ] ⭐ [Agent patterns cookbook](https://platform.claude.com/cookbook/patterns-agents-basic-workflows)

### Build (5.5h)

**Hand-roll ReAct. ~150 lines. No framework.**

Task: *"Assess this KYC policy document against RBI instructions in force today and list the gaps with citations."*

Tools to build:

- [ ] `lookup_regulation(query, as_of_date)`
- [ ] `traverse_amendments(clause_id)`
- [ ] `parse_policy_document(file)`
- [ ] `generate_gap_report(findings)`

Tool design — where your backend experience is the edge:

- [ ] Idempotent tool calls
- [ ] Explicit timeouts
- [ ] Structured error surfaces the model can actually recover from
- [ ] Loop termination and max-iteration cap
- [ ] Hard cost ceiling per task

### Done when

- [ ] Agent completes the task in 6+ steps unaided
- [ ] It recovers from at least one deliberately-injected tool failure
- [ ] Cost per run recorded

---

# Week 6 — MCP, approval gate, frontend (7h + 2h FDSE)

### Learn (1.5h)

- [ ] ⭐ [MCP docs](https://modelcontextprotocol.io/) — intro, Build Servers, Architecture
- [ ] 📄 [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [ ] 📄 [LangGraph](https://langchain-ai.github.io/langgraph/)

### Build (5.5h)

- [ ] **Human approval gate** — agent pauses, surfaces its plan and evidence, waits for sign-off, then proceeds
- [ ] MCP server exposing your four tools, with per-tenant scoping on tool access
- [ ] Rebuild the same task on LangGraph
- [ ] Write `FRAMEWORK-COMPARISON.md` — what the framework buys you, what it costs

### Build — FDSE lane (+2h)

- [ ] Thin React frontend: gap report rendered with **resolvable citations**, approval gate as actual UI not a CLI prompt

> Deliberately plain. This closes FDSE requirement R2 (full-stack) *and* makes every other bucket's demo screenshare-able. Cheapest item in the plan by value.

### Done when

- [ ] MCP server running, tools callable from an MCP client
- [ ] Approval gate working in the UI
- [ ] Framework comparison written — this doc is itself an interview asset

---

> ## ⏸ Weeks 7–13 — switch to `PROJECT-SERVE.md`
>
> Come back at Week 14. Don't touch GOVERN in between — context-switching weekly kills both projects.

---

# Week 14 — Eval harness (7h + 2h FDSE)

### Learn (2h)

- [ ] ⭐⭐ Re-read [Hamel's evals post](https://hamel.dev/blog/posts/evals/) now that you have a system to evaluate
- [ ] 📄 [promptfoo](https://www.promptfoo.dev/) — decide: adopt or hand-roll
- [ ] 📄 [Cohen's kappa](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html)

### Build (5h)

- [ ] Expand golden set to 60–80 cases, versioned in git
- [ ] LLM-as-judge with a **written rubric**
- [ ] **Validate the judge against your own labels — report the agreement figure**
- [ ] Metrics: task success, groundedness, **citation validity** (did it cite something actually in force?), p95 latency, cost/task
- [ ] Wire into GitHub Actions — runs on every prompt or model change
- [ ] **Deliberately break something** — downgrade a model, corrupt a chunking parameter — and let the suite catch it. Screenshot it.

### Build — FDSE lane (+2h)

- [ ] **Case study #1 — Project GOVERN itself**

Structure: vague opening ask as an executive would phrase it → 12–15 discovery questions and why each matters → current-state workflow map with quantified pain → success criteria the customer would agree → 6-week POC scope with explicit non-goals → production architecture with the 2–3 decisions that could go either way → what you'd expect to go wrong.

> Written now, deliberately — the numbers and failure modes are fresh from the eval work. **This is your strongest case study because you actually built it and can answer "what broke?" with truth.**

### Done when

- [ ] CI blocks a PR that regresses quality
- [ ] Judge-agreement figure recorded
- [ ] Screenshot of a caught regression
- [ ] Case study #1 written

### The interview claim this produces

> *"I built a 60-case eval harness with an LLM judge validated against my own labels at κ = X, wired into CI so prompt changes are gated. It caught N regressions before release."*

Treating prompts as code that must pass CI is a genuinely senior instinct almost no candidate demonstrates. Say it in those words.

---

# Week 15 — OpenTelemetry spine, GOVERN side (7h + 3h FDSE)

> **Shared week.** The SERVE half is in `PROJECT-SERVE.md`. Build one instrumentation layer and use it on both — that's what converts two side projects into one thesis.

### Learn (2h)

- [ ] ⭐ [OTel GenAI semantic conventions](https://github.com/open-telemetry/semantic-conventions-genai) — **note: moved out of the main semconv repo**, older links redirect
- [ ] 📄 [GenAI attributes registry](https://opentelemetry.io/docs/specs/semconv/registry/attributes/gen-ai/) · [MCP attributes](https://opentelemetry.io/docs/specs/semconv/registry/attributes/mcp/)
- [ ] 📄 [OpenLLMetry](https://github.com/traceloop/openllmetry) — read the source to see how they map spans
- [ ] 📄 [Jaeger quickstart](https://www.jaegertracing.io/docs/latest/getting-started/) — one Docker command

### Build (5h)

- [ ] Instrument agent runs: spans for model calls, tool invocations, retrieval steps, planning turns
- [ ] Token and **cost attribution per span**, aggregating to per-task and per-tenant
- [ ] Failure taxonomy as span statuses: model error / tool error / timeout / budget exceeded / guardrail triggered
- [ ] View a full agent run as a trace tree in Jaeger

### Build — FDSE lane (+3h)

- [ ] **Case study #2 — a retail bank.** Adjacent to your corpus; you'll write it fast.

### Done when

- [ ] Screenshot: full agent run as a span tree with cost per span
- [ ] You can point at a slow span and explain why

> **This is your signature artifact.** You wrote a distributed-tracing library extending OpenTelemetry at Target. Almost no AI candidate has prior art in observability. This makes that bullet load-bearing rather than historical.

---

# Week 16 — Governance layer (7h + 3h FDSE)

*Where your Google Responsible AI experience becomes the centrepiece.*

### Learn (2h)

- [ ] ⭐ [EU AI Act high-level summary](https://artificialintelligenceact.eu/high-level-summary/) — ten minutes
- [ ] 📄 [AI Act Explorer](https://artificialintelligenceact.eu/ai-act-explorer/) · [Compliance Checker](https://artificialintelligenceact.eu/assessment/eu-ai-act-compliance-checker/) — **run your own project through it; that's your risk classification done**
- [ ] 📄 [Postgres Row Security Policies](https://www.postgresql.org/docs/current/ddl-rowsecurity.html)
- [ ] 📄 [Presidio](https://data-privacy-stack.github.io/presidio/) *(docs moved from microsoft.github.io)*
- [ ] 🔬 [Model Cards paper](https://arxiv.org/abs/1810.03993)
- [ ] 📄 [OWASP LLM Top 10](https://owasp.org/www-project-top-10-for-large-language-model-applications/) — properly now

> ⚠️ **Permission-aware retrieval has thin public material.** Reason it from first principles: *if a document you can't see changes the ranking or latency of results you can see, you've leaked.* That reasoning is the whiteboard answer.

### Build (5h)

- [ ] **Permission-aware retrieval** — authorisation enforced *inside* the retrieval path via Postgres RLS, not post-filtering
- [ ] Per-tenant isolation
- [ ] **Audit log** — every model call, retrieval, tool invocation, approval decision, and the exact context used. Reconstructable months later.
- [ ] PII redaction with Presidio, reversible on the response path
- [ ] `DEPLOYMENT-TOPOLOGY.md` — one page: Bedrock vs Azure OpenAI vs Vertex, EU/UK residency implications
- [ ] **Governance pack**: model card · EU AI Act risk classification with reasoning · human-oversight controls · failure-mode register

### Build — FDSE lane (+3h)

- [ ] **Case study #3 — a hospital group.** Deliberately outside your domain, because the round tests scoping in unfamiliar territory.

### Done when

- [ ] A query as tenant A cannot influence results for tenant B, and you can explain the side channels you closed
- [ ] Audit trail queryable: "show me exactly what produced this output on date X"
- [ ] Governance pack exported as PDF

> Almost no candidate brings a governance pack. You built the real version of this at Google for Vertex AI, Imagen, and Gemini launches — producing your own makes the claim demonstrable rather than assertable.

---

# Week 17 — Package (shared with SERVE, ~4h here + 2h FDSE)

### Build

- [ ] README as an engagement summary: problem → approach → **results table** → what you'd do differently. Assume 90 seconds of reviewer attention.
- [ ] `DECISIONS.md` tidied — this is your interview script for "why did you pick X?"
- [ ] `RESULTS.md` final: all numbers in one place
- [ ] Resume Projects entry — business problem, architecture decision that mattered, eval methodology, hard numbers

### FDSE lane (+2h)

- [ ] **Rehearse all three case studies aloud on a 45-minute timer.** Record one.

> The customer round is verbal and time-boxed. Practising in prose trains the wrong muscle.

---

## Numbers to have by the end

| Metric | Where from |
|---|---|
| Recall@5 / @20 per chunking strategy | Week 2 |
| Amendment-extraction accuracy | Week 3 |
| **Naive vs amendment-aware accuracy** | Week 4 — your headline |
| Agent task success rate, steps-to-completion, cost/run | Weeks 5, 14 |
| Judge-vs-human agreement (κ) | Week 14 |
| Regressions caught by CI | Week 14 |
| p95 latency, cost per task | Week 14 |

---

## What this project qualifies you for

| Bucket | What to lead with |
|---|---|
| **A — AI/Agent Engineer** | The agent, the approval gate, the eval suite — in that order. Most candidates show a demo; you show a measured system. |
| **B — Evals/Safety/Governance** | Google Responsible AI tooling first, then the eval harness with judge validation, then the governance pack. |
| **D — FDSE** | The project *as a customer engagement*: "a compliance team needed to know what was currently in force — here's how I scoped it, what I measured, and what I got wrong." |

---

*Companion: `PROJECT-SERVE.md` (Weeks 7–13) · `4-month-two-track-plan.md` (strategy, targeting, resume variants)*
