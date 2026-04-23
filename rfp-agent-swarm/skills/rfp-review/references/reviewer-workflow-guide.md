# Reviewer Workflow Guide

This guide is the mental model for a human reviewer working through an `rfp-review` queue. If you are that reviewer, read this once per quarter. If you are the skill author debugging triage, this is your source of truth for how the queue should feel.

## 1. The core mental model: only see items that need you

The single most important thing about this queue: **it does not show you every answer**. It shows you:

- items the compliance gates flagged,
- items the drafter was not confident about,
- items that touch sensitive categories (Security, Legal, Pricing, Compliance),
- items that significantly adapted a KB source rather than quoting it.

Everything else has been auto-approved and is available on demand if you want to spot-check — but it is not in your primary queue.

This is deliberate. The measure of success is not "reviewer read 100% of answers" — it is "every correction the reviewer made was logged, and the next RFP had fewer flags."

## 2. Queue sorting logic

The queue is ordered by the priority rank defined in `flagging-rules.md`:

1. Gate-rejected items first (they block the whole pipeline).
2. LOW-confidence or generated content.
3. MEDIUM-confidence with large delta-from-source.
4. Mandatory questions with no response.
5. Sensitive-category items (Security / Legal / Pricing / Compliance).
6. Gate warnings (non-blocking).

Within a rank, items are sorted by category (so you stay in one mental context at a time), then by question id.

## 3. Per-item decision tree

For every item the queue shows you, walk this tree:

```
Is the answer factually correct?
  +-- No.
  |    Is the source KB entry itself wrong for everyone?
  |      +-- Yes. => reason = OUTDATED_SOURCE  (replace)
  |      +-- No, it is correct for most buyers but wrong here.
  |           Is our company position actually changing?
  |             +-- Yes. => reason = POLICY_UPDATE  (retire + add-new)
  |             +-- No, just wrong this one time. => reason = FACTUAL_ERROR  (replace)
  +-- Yes, factually correct.
       Does it need rewording only?
         +-- Yes. => reason = TONE_OR_STYLE  (no-op, logged)
         +-- No, it is missing something.
              Is the missing piece buyer-specific?
                +-- Yes. => reason = MISSING_CONTEXT  (add-sibling)
                +-- No, it is jurisdiction-specific. => reason = COMPLIANCE_NUANCE
```

If the question never existed in the KB at all: `UNANSWERABLE_FROM_KB` and pull an SME in.

If the question was routed to the wrong team (e.g. a security question ended up with product): `CATEGORY_MISCLASSIFICATION` — the correction re-routes future instances.

## 4. Approval shortcuts

You will spend most of your time hitting one of these:

| Key  | Action                                   | When to use                                              |
|------|------------------------------------------|----------------------------------------------------------|
| a    | approve-as-is                            | Answer is fine as drafted                                |
| t    | approve-with-minor-tone-edit             | You changed < 120 chars, no facts altered                |
| r    | rewrite with reason                      | Substantive change — picks a taxonomy reason             |
| s    | reject-and-flag-for-SME                  | Out of your depth; moves to SME queue                    |
| ?    | defer                                    | Come back later, preserves status                        |

If you press `t` but your edit exceeds 120 characters, the system auto-reclassifies as `FACTUAL_ERROR` and asks you to confirm. This exists because "I just tweaked the wording" is the most common way a silent factual edit enters the system. The prompt is friction on purpose.

## 5. Batching and reviewer fatigue

The queue caps at 50 items per reviewer per session by default. If the batch is larger, the script shards by category so each reviewer sees their domain contiguously. Rules of thumb:

- If you have more than 50 items, batch them. Fatigue shows up around item 40.
- Do not mix Security and Pricing in one session; the mental context switch is expensive.
- Target SLA: a LOW-confidence item takes 90 seconds; a gate-rejected item takes 5 minutes; a policy update takes 20 minutes plus an SME ping.
- A healthy batch completes in 45 minutes. If it is taking more than 90 minutes, go back to `rfp-respond` — the drafter is under-confident and the fix is there, not here.

## 6. When to pull in an SME

Pull in an SME when:

- Reason is `UNANSWERABLE_FROM_KB` — there is no KB entry at all.
- Reason is `POLICY_UPDATE` — a company position is changing; legal or exec needs to sign off.
- The answer touches a regulated jurisdiction you do not personally own.

Do not pull in an SME for `TONE_OR_STYLE` or `MISSING_CONTEXT` — those are the reviewer's job.

## 7. What the reviewer is NOT responsible for

- Running the gates. They already ran. Your queue is what is left over.
- Deciding whether the KB entry gets replaced or a sibling added — the taxonomy reason decides that at merge time.
- Formatting the final deliverable. `rfp-assemble` does that.
- Catching every possible issue. HIGH-confidence auto-approved items are the drafter's and the answer bank's responsibility.

## 8. Audit trail

Every action you take writes to `working/corrections.jsonl` (for rewrites and tone edits) or updates `review_status` on the response (for approvals). You can verify your own session with:

```bash
python scripts/export_corrections.py \
  --input working/corrections.jsonl \
  --output /tmp/mine.json \
  --since 2026-04-22
```

and grep for your email. Every correction you make is visible, timestamped, and reversible via a `supersedes` entry.

## 9. Closing a batch

When the queue is empty (or you are stopping for the session), run `export_corrections.py`. This produces the payload that `rfp-answer-bank.merge_corrections` will consume at the next bank refresh. Without this export, your corrections stay in the JSONL and the next RFP does not improve. Do not skip it.

## 10. Quality signals to watch

A healthy reviewer session has these shapes. If yours looks different, something upstream is wrong:

| Signal                                            | Healthy                              | Unhealthy (investigate)                          |
|---------------------------------------------------|--------------------------------------|--------------------------------------------------|
| Ratio of LOW-confidence items in queue            | 20-40% of queue                      | > 60% — drafter undertrained or KB stale         |
| Ratio of TONE_OR_STYLE corrections                | 10-25%                               | > 50% — drafter voice model drifting             |
| Ratio of FACTUAL_ERROR corrections                | 5-15%                                | > 30% — KB factual audit overdue                 |
| Ratio of UNANSWERABLE_FROM_KB                     | < 5%                                 | > 15% — RFP domain outside coverage              |
| Batch completion time                             | 30-75 minutes                        | > 120 minutes — reviewer fatigue or bad triage   |
| Deferred items carried over                       | < 10%                                | > 25% — SLAs slipping                            |

These are *reviewer-visible* signals. Deeper KB-health signals are reported by `rfp-answer-bank`, not here.

## 11. The reviewer's compact with the system

You are not the last line of defence — the drafter, the gates, and the answer bank all did work before you saw these items. You are the *learning edge*. Every correction you log is a lesson the system keeps. Over a quarter, your queue should get smaller, your batches faster, and the flag rate on new RFPs lower. If that curve flattens, something in the loop is broken; report it to the RFP ops owner. Do not just power through.

## 12. What to do when something looks off

- **A gate-rejected item looks obviously fine.** Do not override quietly. Flag back to `rfp-gates` — the rule probably needs updating. Use `reject-and-flag-for-SME` with a note.
- **A HIGH-confidence auto-approved item was wrong.** You will not see this in your queue, but if you spot-check and find one, log a correction anyway. The script accepts corrections for auto-approved items; the record is flagged `was_auto_approved: true` and the answer bank will tighten its confidence thresholds.
- **Two corrections contradict each other.** Log both; the later one supersedes via `supersedes: <prior_id>`. Do not silently overwrite the JSONL.
- **You are unsure of the right reason.** Log the closest reason and add a `--tag needs-review` so the rollup surfaces it for a second opinion. Do not skip logging.
