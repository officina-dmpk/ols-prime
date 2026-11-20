# Brief — the two definitions of a constant miss

- **Agent:** `ml-engineer` (opus, high). Read the code, run on synthetic data or on the saved JSON only. No new contact with the real bars.
- **Files:** `python/olsprime/bench/adversary.py`, `python/olsprime/bench/twins.py`, the runs `runs/2026-10-29-h1-adversary/` and `runs/2026-10-30-twins/`, `docs/RESULTS.md` (rows "H1 (adversary, descriptive)" and "H1 (blind spots, descriptive)").

## Why

The paper will cite the adversary's misses. `docs/RESULTS.md` gives two counts that look contradictory:
- the adversary row says that 163 of the 205 leaks caught at no cut are constant at the compared rows;
- the twins row says that 193 of the same 205 are constant at the compared rows.

The likely cause, from `twins.py` lines 33–37 and 229–230: `constant` compares H1's 16 cuts only, while the adversary's own flag (`constant_every`) compares both of its schedules, H1's cuts and the long schedule of 128 cuts. More compared rows leave fewer constant leaks.

## Do

1. Confirm or refute that cause from the code and from the two runs' JSON, leak by leak. Give the 30 leaks constant under one definition and not the other, with their family.
2. Write one paragraph, for `docs/RESULTS.md` and the paper, that states both definitions and both counts side by side. The orchestrator appends it as a dated correction row; rows are never edited.
3. If the cause is anything else, stop and report it before changing anything.

## Done when

The cause is shown leak by leak, the paragraph is written, and no code has changed (or a change is proposed with a test, for audit pass 5b).
