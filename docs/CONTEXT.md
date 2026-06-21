# Project Context

## Background

This project is both a practical business-tool prototype and an AI engineering
portfolio project.

The practical goal is to help a small direct-to-consumer (DTC) brand improve
its TikTok content decisions using recent performance data rather than
intuition alone.

The engineering goal is to demonstrate a modular, privacy-aware workflow that
separates data ingestion, normalisation, metric calculation, LLM-ready
summarisation, strategy generation, presentation, and future publishing
integrations.

## Business use case

Small brands may publish frequently on TikTok without a structured feedback
loop. Platform analytics expose numbers such as views, likes, comments, shares,
saves, duration, and average watch time, but those numbers do not automatically
answer what the brand should test next.

The intended workflow helps a founder or marketer explore questions such as:

- Which recent posts produced the strongest engagement signals?
- Which hooks or content pillars may be worth testing again?
- Which formats or topics may need adjustment?
- What should the next content concept explore?
- What script, caption, and hashtags could support that concept?

The MVP answers the descriptive metrics portion, adds deterministic testing
signals, and produces a rule-based content plan with reviewable text drafts.
Provider-backed strategy and media generation remain future, optional
capabilities.

## Current MVP workflow

The implemented offline path is:

```text
Synthetic sample CSV
        |
        v
Record normalisation
        |
        v
Per-post metric calculation
        |
        +-------------------+
        |                   |
        v                   v
Markdown summary     Manual strategy rules
        |                   |
        +---------+---------+
                  v
             outputs/demo/
```

This path requires no credentials, third-party packages, network connection, or
external API calls.

## Future real-world workflow assumption

A possible future private deployment could use this path:

1. An authorised export tool collects TikTok post data.
2. Airtable or another private store holds recent records.
3. A backend adapter retrieves a limited set of records.
4. The analysis pipeline normalises data and calculates metrics.
5. An explicitly selected LLM provider receives a compact summary.
6. A human reviews and edits the resulting content plan.
7. A separate, consent-based workflow may prepare a draft for publishing.

Apify, Airtable, LLM calls, TikTok authentication, and publishing are not
implemented in the current repository. They are architecture possibilities,
not current dependencies.

## Why analyse the latest 10 posts?

The CLI defaults to a small recent sample because early-stage account
performance can change quickly as creative style, audience response, and
platform distribution evolve.

Ten posts are enough for a lightweight review while remaining easy to inspect
manually. The sample may reveal current signals around:

- audience response
- hooks worth retesting
- comparatively weak content formats
- content-pillar balance
- topic fatigue
- whether the next test should repeat, adjust, or pivot

The number 10 is a practical default, not a statistical guarantee. Results from
a small sample should be treated as hypotheses for future tests.

## Human-in-the-loop philosophy

The project is not intended to fully automate content publishing.

The preferred future workflow is:

1. Collect recent performance data.
2. Calculate transparent metrics.
3. Generate a concise performance summary.
4. Produce a recommendation or draft.
5. Let a human review facts, tone, visuals, compliance, and timing.
6. Optionally prepare assets or a platform draft.
7. Let a human make the final publishing decision.

Human review matters because content quality depends on context that analytics
alone cannot fully capture: visual judgement, brand voice, music, editing,
claims, cultural timing, and platform conventions.

## Role of Codex

Codex is used to develop and maintain the software. It can help create modules,
debug the pipeline, improve documentation, add tests, and evolve provider
adapters.

Codex is not the stable production runtime, scheduler, or long-running content
analyst. Production behaviour should remain ordinary, reviewable code that can
run locally, in CI, or in a future scheduled environment.

## Role of an LLM

An optional LLM acts as a strategy and generation layer rather than the source
of metric truth.

It may generate:

- a performance interpretation
- content concepts and testable hypotheses
- video scripts or carousel outlines
- captions and hashtags

The provider should receive a compact structured summary instead of unrestricted
raw files. Provider output must be validated and reviewed by a human.

The default `manual` provider uses deterministic rules so the complete local
pipeline remains testable without credentials. OpenAI and Claude calls are
explicitly opt-in and their returned plans are validated before export.

## Data source assumptions

The current MVP supports only a local CSV.

Potential future data sources include:

- authorised Airtable records
- authorised export files
- TikTok APIs, only if suitable access and permissions become available

New sources should be implemented behind adapters so normalisation and metrics
remain independent of the source.

## Input data assumptions

Each CSV row represents one published video and maps to the canonical schema in
[`canonical-schema.md`](canonical-schema.md). Required fields cover identity,
publication time, format, topic, hook, caption, duration, and core engagement
counts. Optional fields cover URL, saves, watch time, completion, audience
region, and notes.

Rates use views as the denominator. If views are zero, rate metrics are zero to
avoid division errors. Save rate is omitted when saves are unavailable.
Average watch ratio is calculated only when duration and average watch time are
available and duration is greater than zero.

When the top region, target region, and top-region share exist, the pipeline
also calculates a documented region-match proxy. Format and topic fields feed
group comparisons, and deterministic signals identify repeat, pause,
distribution, save, hook, and retention hypotheses.

## Interpretation limits

The generated report is descriptive, not causal. A high engagement rate does
not prove that a particular hook, format, or topic caused performance.

Small sample size, paid distribution, posting time, audience changes, account
growth, geography, and platform delivery can all affect results. The output
should guide creative experiments rather than be presented as a prediction.

## Public repository and local data policy

This repository is intended to be public.

It may contain:

- source code
- documentation
- synthetic sample data
- reviewed prompt templates

It must not contain:

- API keys, OAuth tokens, or `.env`
- real account analytics or private URLs
- real brand strategy or generated private plans
- customer data
- sensitive local logs

Real local data belongs only in ignored paths:

- `data/raw/`
- `data/processed/`
- `outputs/`
- `logs/`

## Portfolio value

The project demonstrates more than a single prompt. It shows:

- offline-first pipeline design
- data ingestion and normalisation
- transparent metric calculation
- LLM-ready structured summarisation
- provider abstraction
- privacy-aware public repository design
- backend/frontend separation
- human-in-the-loop workflow design
- testable boundaries for future automation and publishing

Together, these make the repository a focused AI engineering portfolio project
with a working local MVP and an intentionally staged path toward external
integrations.
