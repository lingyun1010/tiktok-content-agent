# Content Plan Schema

Phase 2 defines `outputs/demo/content_plan.json` as the stable boundary between
analytics, manual strategy generation, and future presentation layers.

## Top-level fields

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | text | Current schema version, `1.0` |
| `status` | text | Always `draft_for_human_review` in manual mode |
| `provider` | text | `manual` for the implemented offline provider |
| `llm_called` | boolean | Always `false` in manual mode |
| `human_review_required` | boolean | Always `true` |
| `analysis_basis` | object | Input count and post IDs behind each strategy rule |
| `strategy` | object | Repeat, pause, and retention decisions with reasons |
| `content_item` | object | One reviewable content draft |
| `limitations` | list of text | Interpretation and publishing limits |

## Analysis basis

`analysis_basis` records:

- `post_count`
- `top_post_id`
- `repeat_candidate_post_ids`
- `pause_candidate_post_ids`
- `weak_retention_post_ids`

These fields make the recommendation traceable to Phase 1 metrics and signals.

## Strategy rules

- Prefer the strongest `repeat_candidate`, ordered deterministically by
  engagement rate, watch ratio, views, and post ID.
- If no repeat candidate exists, use the highest-engagement post as a clearly
  labelled fallback.
- Add pause actions for every `pause_candidate`.
- Recommend a shorter, punchier edit when any post has an available watch ratio
  below 50%.

The rules describe the analysed sample. They do not prove causation or predict
future performance.

## Content item

The single `content_item` contains:

- stable ID and working title
- selected format, topic, and evidence post
- creative direction
- script hook, body, and call to action
- caption
- ordered hashtags
- mandatory review checks

`script.md`, `caption.txt`, and `hashtags.txt` are rendered from this object so
the text outputs remain consistent with the JSON plan.

## Human review

The plan is not approval to publish. A person must verify claims, brand voice,
visual context, accessibility, and platform compliance, then edit and approve
all text before publishing.
