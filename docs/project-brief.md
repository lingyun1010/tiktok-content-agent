# Project Brief

## Project name

TikTok Content Agent

## One-line summary

An offline-first, AI-ready content strategy pipeline that turns recent TikTok
performance data into structured insights and content recommendations for
small DTC brands.

## Product goal

Build a practical assistant that helps small brand teams move from raw TikTok
analytics to clearer creative decisions. The system should make recent
performance understandable today and provide a safe path toward optional
provider-generated scripts, captions, hashtags, and content plans later.

## Problem

Small brands often post on TikTok without a consistent feedback loop. They may
have access to views, likes, comments, shares, saves, duration, and watch time,
but lack the time or specialist knowledge to translate those signals into the
next content decision.

Analytics may also live in exports, spreadsheets, or Airtable while content
planning happens elsewhere, making the process fragmented and difficult to
repeat.

## Target user

The primary user is a small DTC brand owner, creator, marketer, or solo operator
who wants to improve the quality of content decisions without manually
analysing every recent post.

## Example use case

A premium herbal haircare brand publishes educational videos, product rituals,
founder stories, and behind-the-scenes content. The owner wants to review the
latest 10 posts, compare engagement and watch signals, identify themes worth
testing again, and create a structured starting point for the next content
cycle.

For the public repository, this scenario is represented only with fictional
sample data.

## MVP scope

The MVP:

- accepts a local CSV containing recent TikTok post records
- validates and normalises a canonical TikTok post schema
- limits analysis to the requested number of recent records
- calculates per-post engagement, watch, and optional region metrics
- compares formats and topics and assigns deterministic rule-based signals
- produces an LLM-ready Markdown metrics report
- produces a deterministic JSON content plan without an LLM
- produces a reviewable script, caption, and hashtag set from the same plan
- defines a clean boundary for manual, OpenAI, and Claude providers
- includes an intentionally minimal static frontend concept
- runs locally without credentials, network access, or external services

## User outcome

After running the sample command, a user receives:

- a concise overview of total views and average performance
- ranked post, format, topic, region, and rule-based signal summaries
- a deterministic content plan and text drafts for human review

The output is descriptive rather than predictive. It does not claim that a
particular creative element caused performance or guarantee future results.

## Success criteria

- The documented sample command succeeds on a clean Python 3.10+ installation.
- No third-party package, credential, or external API is required.
- The pipeline generates valid Markdown and JSON from synthetic data.
- Zero views and optional metric fields are handled safely.
- Generated outputs and real data paths remain ignored by Git.
- The code and documentation clearly distinguish implemented features from
  future plans.

## Future scope

Potential future iterations may include:

- Airtable ingestion through a data-source adapter
- authorised export ingestion from other sources
- richer trend and hook-level analysis
- further opt-in strategy providers
- image and video prompt generation
- a small backend API
- an interactive dashboard
- GitHub Actions for offline tests and security checks
- a separately designed, human-reviewed TikTok draft workflow

Future integrations must preserve the offline sample path and public-repository
security model.

## Non-goals

The MVP does not:

- authenticate with, scrape, schedule, or upload to TikTok
- call real Airtable or LLM APIs
- generate real images or videos
- store secrets or commit private analytics
- provide real-time analytics
- prove causation or predict guaranteed performance
- include a production database, user-account system, or polished application
- run as a long-lived autonomous coding-agent session
