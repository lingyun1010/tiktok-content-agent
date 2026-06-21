# TikTok Metrics Summary

> Deterministic offline analysis. Observations describe this dataset; recommendations are test hypotheses, not causal findings.

## Dataset overview

- Source: `examples/sample_recent_posts.csv`
- Posts analysed: 10
- Total views: 138,000
- Average views per post: 13,800
- Average engagement rate: 11.03%
- Average watch ratio: 66.91%
- Posts with comparable region fields: 10 of 10

## Top performing posts

| Post | Format | Topic | Hook | Views | Engagement | Watch | Signals |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| demo-004 | Talking head | Scalp oil education | You may be using too much | 22,100 | 12.62% | 82.96% | repeat_candidate |
| demo-009 | Talking head | Cleansing education | Foam is not the same thing as clean | 20,400 | 12.47% | 83.85% | repeat_candidate |
| demo-001 | Talking head | Wash day education | Wash day should not take your whole afternoon | 12,500 | 11.74% | 72.92% | low_view_high_save, repeat_candidate |

## Weak performing posts

| Post | Format | Topic | Hook | Views | Engagement | Watch | Signals |
| --- | --- | --- | --- | ---: | ---: | ---: | --- |
| demo-005 | Behind the scenes | Fulfilment | Come pack today's first order with us | 6,400 | 8.75% | 60.50% | none |
| demo-006 | Product demo | Routine building | Your routine should match your week | 15,100 | 10.01% | 70.57% | high_view_low_engagement |
| demo-010 | Behind the scenes | Manufacturing | This bottle starts here | 13,400 | 10.23% | 41.25% | pause_candidate |

## Format performance

| Format | Posts | Avg views | Avg engagement | Avg watch | Repeat candidates |
| --- | ---: | ---: | ---: | ---: | ---: |
| Talking head | 3 | 18,333 | 12.28% | 79.91% | 3 |
| Lifestyle montage | 1 | 11,200 | 11.24% | 41.82% | 0 |
| Reply video | 1 | 9,700 | 11.10% | 71.03% | 0 |
| Product demo | 2 | 16,700 | 10.84% | 76.40% | 1 |
| Founder story | 1 | 8,900 | 10.44% | 61.94% | 0 |
| Behind the scenes | 2 | 9,900 | 9.49% | 50.88% | 0 |

## Recommended signals for next content

- `high_view_low_engagement` (1): Keep the distribution lesson, but test a clearer value proposition or CTA. Posts: `demo-006`.
- `low_view_high_save` (1): Retest the useful premise with a stronger opening and packaging. Posts: `demo-001`.
- `good_hook_weak_retention` (1): Keep the hook idea and tighten the middle or shorten the edit. Posts: `demo-008`.
- `wrong_region_distribution` (1): Review language, references, posting time, and audience targeting cues. Posts: `demo-007`.
- `repeat_candidate` (4): Create a controlled follow-up that preserves the premise and changes one variable. Posts: `demo-001`, `demo-003`, `demo-004`, `demo-009`.
- `pause_candidate` (1): Pause direct repetition until the hook, retention, or regional fit is revised. Posts: `demo-010`.

### Signal rules used

- High/low views, likes, saves, engagement, and repeat thresholds use dataset averages.
- Weak retention means `average_watch_ratio < 50%`.
- Wrong-region distribution means `region_match_score < 50%`.
- A repeat candidate has at-or-above-average engagement, supported retention, and no wrong-region flag.
- A pause candidate has below-average engagement plus weak retention or a wrong-region flag.

This committed summary is a public-safe excerpt of the complete generated
report. Run the offline pipeline to regenerate the full per-topic, audience,
and per-post appendices under the ignored `outputs/` directory.
