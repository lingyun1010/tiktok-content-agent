# Canonical TikTok Post Schema

Phase 1 defines one canonical record shape for the CSV source and future
authorised source adapters. Every adapter must map its source-specific fields
into this shape before metrics are calculated.

## Required fields

| Field | Type | Meaning |
| --- | --- | --- |
| `post_id` | text | Unique post identifier within the dataset |
| `platform` | text | Must be `tiktok` |
| `published_at` | ISO 8601 datetime | Publication time |
| `format` | text | Creative format, such as `Talking head` |
| `caption` | text | Published caption or synthetic equivalent |
| `duration_seconds` | number greater than zero | Video duration |
| `views` | non-negative integer | View count |
| `likes` | non-negative integer | Like count |
| `comments` | non-negative integer | Comment count |
| `shares` | non-negative integer | Share count |

## Optional fields

| Field | Type | Meaning |
| --- | --- | --- |
| `post_url` | absolute HTTP(S) URL | Public post URL when safe to process |
| `topic` | text | Human-supplied primary subject or content theme |
| `hook` | text | Human-supplied opening premise or first-line hook |
| `saves` | non-negative integer | Save or favourite count |
| `average_watch_time_seconds` | non-negative number | Average watch time |
| `completion_rate` | number from 0 to 1 | Source-provided completion rate |
| `top_region` | text | Region with the largest observed view share |
| `target_region` | text | Intended primary audience region |
| `top_region_view_percentage` | number from 0 to 1 | Share of views from `top_region` |
| `notes` | text | Optional reviewed context |

Blank optional values remain `None`; the pipeline does not invent them.
Missing topics are excluded from topic grouping, and reports state when topic
coverage limits that analysis. Missing hooks use neutral wording only in the
deterministic draft output; they are not inferred or backfilled into the
canonical record.
Duplicate post IDs, invalid timestamps, fractional count fields, invalid URLs,
and out-of-range percentages are rejected.

## Airtable field setup

The selected Airtable view must expose field names exactly as written above.
Airtable's own record ID is not used as `post_id`; create a `post_id` field in
the table.

Recommended Airtable field types:

- Single line text: `post_id`, `platform`, `format`, `topic`, `hook`,
  `caption`, `topic`, `hook`, `top_region`, `target_region`, `notes`
- URL: `post_url`
- Date with time: `published_at`
- Number: `duration_seconds`, `views`, `likes`, `comments`, `shares`, `saves`,
  `average_watch_time_seconds`, `completion_rate`,
  `top_region_view_percentage`

Use decimal fractions from 0 to 1 for percentage fields, for example `0.75`
rather than `75`. Required numeric fields must not be blank. Every record
returned by the configured view is validated, so use a filtered view if draft
or incomplete rows exist in the same table.

## Calculated fields

Rates use views as their denominator:

```text
like_rate           = likes / views
comment_rate        = comments / views
share_rate          = shares / views
save_rate           = saves / views
engagement_rate     = (likes + comments + shares + available saves) / views
average_watch_ratio = average_watch_time_seconds / duration_seconds
```

Zero-view posts receive zero-valued rate metrics. Save rate and average watch
ratio remain unavailable when their source fields are missing.

`region_match_score` is calculated only when `top_region`, `target_region`, and
`top_region_view_percentage` are all available:

- matching regions: `top_region_view_percentage`
- different regions: `1 - top_region_view_percentage`

The mismatch calculation is a conservative proxy, not a full audience-region
distribution. A future source with complete regional shares can replace this
calculation behind the same canonical boundary.

## Rule-based signals

Dataset averages provide the high/low thresholds for views, like rate, save
rate, engagement rate, and repeat-candidate retention.

- `high_view_low_engagement`: views are at or above average and engagement is
  below average.
- `low_view_high_save`: views are below average and save rate is at or above
  average.
- `good_hook_weak_retention`: like rate is at or above average and average
  watch ratio is below 50%.
- `wrong_region_distribution`: region match score is below 50%.
- `repeat_candidate`: engagement is at or above average, retention is
  supported, and there is no wrong-region signal.
- `pause_candidate`: engagement is below average and retention or regional fit
  is weak.

These classifications are descriptive prompts for controlled testing. They do
not establish why a post performed as it did.
