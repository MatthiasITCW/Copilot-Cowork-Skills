# Flagging Rules

These rules decide which responses enter the review queue and which are auto-approved. They are applied by `scripts/build_review_queue.py`. Change them here before changing the script — the script is the implementation, this doc is the contract.

## 1. Entry matrix

A response enters the queue if **any** row in this matrix matches:

| Confidence | Category                  | Source    | Gate verdict | Freshness  | In queue?   | Priority |
|------------|---------------------------|-----------|--------------|------------|-------------|----------|
| any        | any                       | any       | FAIL         | any        | yes         | 1        |
| LOW        | any                       | any       | any          | any        | yes         | 2        |
| any        | any                       | GENERATED | any          | any        | yes         | 2        |
| MEDIUM     | any                       | KB        | any          | any        | yes if delta > 0.35 | 3 |
| any        | any, mandatory            | NONE      | any          | any        | yes         | 4        |
| any        | Security/Legal/Pricing/Compliance | any | any       | any        | yes         | 5        |
| any        | any                       | any       | WARN         | any        | yes         | 6        |

## 2. Skip matrix (auto-approved)

A response skips the queue and is tagged `review_status: auto-approved` if **all** conditions hold:

| Dimension      | Required for skip                                             |
|----------------|---------------------------------------------------------------|
| Confidence     | HIGH                                                          |
| Category       | NOT in {Security, Legal, Pricing, Compliance}                 |
| Source         | KB (not GENERATED)                                            |
| Gate verdict   | PASS (no WARN or FAIL)                                        |
| Freshness      | bank_freshness ≤ 90 days                                      |
| Mandatory      | Either answered, or not a mandatory                           |

If any single condition fails, the response goes into the queue at the appropriate priority.

## 3. Delta-from-source (MEDIUM tier)

The `delta` score is how much the drafter adapted the KB source:

- `delta = 0.0` — verbatim quote from KB.
- `delta = 1.0` — nothing in common with KB source (should not happen in MEDIUM tier).
- `delta > 0.35` — significant adaptation; enters queue at priority 3.

This threshold is a config value (`review.medium_tier_delta_threshold`, default `0.35`). Lower it if you want more MEDIUM items reviewed; raise it if reviewers report too many "this looks fine" items at priority 3.

## 4. Auto-escalation rules

These rules modify a reviewer's classification during correction capture:

| Trigger                                                 | Action                                          |
|---------------------------------------------------------|-------------------------------------------------|
| Reviewer picks TONE_OR_STYLE with edit > 120 chars      | Auto-reclassify to FACTUAL_ERROR, confirm prompt|
| Reviewer picks FACTUAL_ERROR on a POLICY_UPDATE pattern | Warn: "is this a policy change?" — reviewer decides |
| Reviewer edits a Security/Legal/Pricing answer          | Require confirmation checkbox before commit     |
| Reviewer picks UNANSWERABLE_FROM_KB without an SME tag  | Block until SME email is attached               |

The 120-character threshold exists because empirically, silent factual edits disguised as "tone" is the most common failure mode of correction capture.

## 5. Audit rule

Every response object in the final `responses_for_assembly.json` must carry `review_status` set to one of:

| Status          | Meaning                                                        |
|-----------------|----------------------------------------------------------------|
| reviewed        | A human reviewer saw this item and took an action              |
| auto-approved   | Skipped the queue per the skip matrix                          |
| skipped         | Reviewer explicitly deferred; item not touched                 |

`rfp-assemble` MUST reject any response missing this field. This is the forcing function: without it, the pipeline ships unreviewed answers silently. With it, every answer has a traceable disposition.

## 6. Freshness lookup

`bank_freshness` is the number of days since the KB entry was last validated. It comes from `answer_bank_freshness.json` emitted by `rfp-answer-bank`. If that file is missing, `build_review_queue.py` assumes freshness = `null` and treats every item as failing the skip matrix (fail-closed).

## 7. Configuration knobs

| Knob                                       | Default | Effect                                              |
|--------------------------------------------|---------|-----------------------------------------------------|
| `review.medium_tier_delta_threshold`       | 0.35    | Lower = more MEDIUM items reviewed                  |
| `review.freshness_max_days`                | 90      | Raise if KB is updated less frequently              |
| `review.sensitive_categories`              | S/L/P/C | Add categories that should never auto-approve       |
| `review.tone_edit_char_cap`                | 120     | Raise if false-positive reclassifications annoy reviewers |
| `review.batch_cap_per_reviewer`            | 50      | Lower if reviewer fatigue is a recurring complaint  |

These live in the repo config, not in the script itself.
