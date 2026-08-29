# Project GOVERN — RBI Regulatory Change Copilot

A compliance copilot for Indian banks that answers questions about RBI regulations correctly — including tracing amendment chains across years — and can prove every answer.

## The problem

A compliance team fields questions like *"what is the current KYC requirement for video-based customer identification?"* Answering correctly means tracing a chain of RBI amendments across several years. Naive vector search confidently returns stale text: correctly cited, and wrong.

## What this builds

| Component | Purpose |
|---|---|
| Amendment graph | Models RBI circulars as a directed graph of `amends`, `supersedes`, `withdraws` edges |
| Point-in-time retrieval | Answers "what was in force on date X?" — not just "what's relevant?" |
| ReAct agent | Completes multi-step compliance gap assessments with a human approval gate |
| MCP server | Exposes retrieval and graph-traversal tools to any MCP client |
| Eval harness | LLM-as-judge with human-validated rubric, wired into CI |
| Observability | OpenTelemetry traces with per-span token cost |
| Governance pack | Model card, EU AI Act classification, failure-mode register, audit trail |

## Results (updated as built)

See [RESULTS.md](RESULTS.md).

## Stack

- **LLM**: Claude (Anthropic) + cost-tracking wrapper
- **DB**: PostgreSQL + pgvector (HNSW index)
- **Retrieval**: Hybrid BM25 + dense embeddings, reranking pass
- **Agent**: Hand-rolled ReAct (~150 lines, no framework), then LangGraph for comparison
- **Serving**: MCP server + thin React frontend
- **Observability**: OpenTelemetry + Jaeger

## Project structure

```
rbi-govern/
├── data/           # Scraped and extracted RBI circulars
├── src/
│   ├── ingest/     # Scraping, PDF extraction, Postgres normalisation
│   ├── retrieval/  # Chunking strategies, embeddings, BM25, reranking
│   ├── graph/      # Amendment graph construction and traversal
│   ├── agent/      # ReAct loop, tools, approval gate
│   └── server/     # MCP server
├── evals/          # Golden set, judge, CI harness
├── frontend/       # React gap-report UI
├── docs/           # Governance pack, case studies, decisions
├── PROJECT-GOVERN.md
└── README.md
```

## Weekly plan

- **Week 1** — LLM APIs + corpus ingestion (RBI circulars → Postgres)
- **Week 2** — Retrieval pipeline + 40-question golden set
- **Week 3** — Amendment graph (extraction + directed graph in Postgres)
- **Week 4** — Point-in-time retrieval + headline accuracy comparison
- **Week 5** — Hand-rolled ReAct agent
- **Week 6** — MCP server, approval gate, React frontend
- **Weeks 14–17** — Eval harness, observability, governance, packaging

## Key claim (to be filled in with real numbers)

> *"Naive retrieval was X% accurate — and its errors were confidently-worded stale regulations. Modelling the amendment graph and adding point-in-time filtering took it to Y%. Remaining failures are genuinely ambiguous RBI text, flagged for human review."*
