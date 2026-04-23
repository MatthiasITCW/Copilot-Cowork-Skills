# Batch Skill Creation — Completion Report Template

Use this template verbatim when reporting back to the user after a batch skill-creation run. Replace `[PLACEHOLDERS]` with actual values.

---

## Summary Message Template

> I've created **[SKILL_COUNT] new skill[S]** in your personal library. They'll appear in OneDrive under `Cowork/Skills/` within about 35 seconds.

## Per-Skill Line Format

For each skill in the batch, one bullet:

> - **[skill-name]** ([TIER]) — [one-line description]. Trigger it with phrases like "[example trigger 1]" or "[example trigger 2]".

## Verification Line

> All packages verified: [FILE_COUNT] files written, every cross-link resolves.

## Next-Step Prompt

> Want me to run a validation pass on any of them, or start on another batch?

---

## Example Filled Template

> I've created **3 new skills** in your personal library. They'll appear in OneDrive under `Cowork/Skills/` within about 35 seconds.
>
> - **project-retrospective** (Full Package) — Structured retrospective analysis using 4Ls and Start-Stop-Continue frameworks. Trigger it with "run a retrospective" or "what went well last sprint".
> - **executive-brief** (Enhanced) — One-page executive summaries with Pyramid Principle structure. Trigger it with "draft an exec brief" or "summarize this for leadership".
> - **quarterly-planning** (Enhanced) — OKR-based quarterly planning with cascade templates. Trigger it with "plan next quarter" or "draft our Q-objectives".
>
> All packages verified: 11 files written, every cross-link resolves.
>
> Want me to run a validation pass on any of them, or start on another batch?

---

## Placeholder Reference

| Placeholder | Fill with |
|-------------|-----------|
| `[SKILL_COUNT]` | Integer count of skills created in this batch |
| `[S]` | "s" if plural, empty string if 1 |
| `[TIER]` | Standard / Enhanced / Full Package |
| `[FILE_COUNT]` | Total files written across the batch (SKILL.md + supporting) |
| `[skill-name]` | kebab-case skill name exactly matching the directory |
