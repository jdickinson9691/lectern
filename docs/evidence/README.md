# Lectern Acceptance Evidence

This directory stores sanitized, durable evidence used by agent contracts and
release decisions.

## Categories

- [`fantasy-grounds/`](fantasy-grounds/) — sanitized event fragments, expected
  imports, and live-test summaries.
- [`narrative/`](narrative/) — representative structured inputs and expected
  prose characteristics.
- [`acceptance/`](acceptance/) — test matrices, release checks, and summarized
  manual results.

## Evidence rules

- Never store runtime databases, full campaign exports, personal data, portraits,
  copyrighted PDFs, or commercial module text.
- Prefer the smallest sanitized fixture that proves the behavior.
- Record source version, application version, schema/contract version, date, and
  related contract ID.
- Screenshots should be cropped and sanitized before entering the repository.
- A narrative screenshot is supporting evidence, not the authoritative combat log.
- Raw evidence and expected interpretation must be clearly separated.
