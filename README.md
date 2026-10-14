# Freight cost watchdog

Flags routes whose cost per tonne-km is rising unusually, then checks the context notes for a
**real, applicable** reason. If none exists, the row is `Yes` (unexplained) and says so.

```
pip install -r requirements.txt
python run.py                          # -> outputs/output.csv (the deliverable)
python eval/run_eval.py                # labelled-set eval + guardrail checks
python -m unittest discover tests      # gate unit tests
./repro_check.sh                       # 3 runs, byte-identical diff
python ask.py "why did Chennai-Bangalore get pricier in March 2025?"   # stretch goal
```

## How it works
1. **Group & weekly cost** (`metrics.py`): group by route (origin-destination, which also fixes `route_type`);
   week = Monday-Sunday, `week_of` = Monday. Weekly cost/tonne-km = sum(cost) / sum(tonnes x km).
   Every route has shipments in all 104 weeks (min 3/week), so there are no gaps.
2. **Baselines, exactly as specified**
   - *Own history*: mean of the route's weekly values over the up-to-8 weeks strictly before the week.
     Weeks 2-8 of a route's life use fewer than 8 prior weeks (all available, no padding); week 1 has no
     baseline and is not evaluated.
   - *Similar routes*: mean of the other routes with the same `route_type` in that week (self excluded).
     Short and Long have only two routes each, so their "peer average" is the one other route.
3. **Candidates** (`flagging.py`): cost rising >= 8% vs own history AND (z-score vs own window >= 3 OR >= 15% above peers).
   Peer premium alone is not enough, because some routes are structurally pricier (Mumbai-Pune is always above Delhi-Jaipur-type peers);
   rising is mandatory. Threshold choice: `eval/sensitivity.py` shows the candidate set sits on a plateau (7-10 rows) for rise 8-10%,
   and jumps to 16-24 rows below 8% (normal weekly noise), so 8% is the edge of the noise.
4. **Retrieve & verify** (`notes.py`): TF-IDF retrieval over the 10 notes ranks notes for a route (in-memory index; I chose
   this over a hosted vector DB because there are only 10 notes: deterministic, free, no downloads). Retrieval only
   proposes; three **hard gates** decide. A note may justify a row only if it is (1) **in scope** (route or "All Routes"),
   (2) **in window** (parsed from text: explicit "from Feb 24 to Mar 8"; one week for single events; 8 weeks for
   "starting this week" level shifts, because after 8 weeks the trailing baseline has absorbed the shift),
   and (3) **cost-raising** (says costs went up, and none of "not affected / normal / no rate change / not in dataset").
5. **Explain** (`explain.py`): templates that quote the matched note and its dates. No LLM, so nothing can be invented.
   Unexplained rows name the closest in-scope note (within 90 days) and why it was rejected.

## Results (10 rows)
| Verdict | Rows |
|---|---|
| Justified | Ahmedabad-Mumbai 2025-01-20 (N002); Chennai-Bangalore 2025-02-24, 03-03 (N001); Mumbai-Delhi 2025-05-12 (N003) |
| Unexplained | Delhi-Jaipur 2024-11-11, 11-18; Chennai-Bangalore 2025-03-10 (after the flood window), 03-17 (N009 says back to normal); Mumbai-Pune 2025-09-15, 2025-11-17 (slow creep) |

Traps handled: N004/N005/N006/N008/N009/N010 say costs were *not* affected, and none is ever cited as justification;
N001 is wrong-window for 03-10; N003 (diesel) is too old to explain Mumbai-Pune in Nov 2025; N002 is not used for other routes.
N003 caveat: it says 5-7% but Mumbai-Delhi is up 11.6% vs its own history (6.7% vs peers), so the reason text says the note may explain only part.

## How I convinced myself it is right
- `eval/run_eval.py`: scores detection (precision/recall over all 721 route-weeks), verdict, and cited note against `eval/labels.csv`
  -> 10/10 detected, 0 false alarms, 10/10 verdicts, 10/10 notes. **Honest limit:** I wrote those labels after reading the data and notes, so this
  checks the code does what I intended, not that my intent is perfect. The labels carry a reason for each row so a reviewer can disagree.
- Independent check: my numbers match the three numeric rows in the provided sample file exactly (cost, own %, peer %).
- Guardrail audit in the eval: every justified row's note is re-verified as in-scope + in-window + cost-raising (0 violations).
  `tests/` covers wrong route, wrong window, expired diesel effect, and negated notes.

## Reproducibility
Nothing is random and no LLM is called; ties in retrieval break on note_id; rows are sorted. `repro_check.sh`: 3 runs, identical SHA-256
(`outputs/repro_check.txt`).

## Cost of one full run
0 LLM calls, 0 input tokens, 0 output tokens, cost 0 (see `outputs/token_cost_log.md`). This is a deliberate trade-off: with 10 notes and strict
verification gates, an LLM would add cost and fabrication risk. Where an LLM would help: messy or many notes (extracting windows/effects from free text).
If I added one, I would use temperature 0 *after* the gates, only to paraphrase an already-verified note, and never to decide the verdict.

## Limitations
- Note parsing uses regex/lexicon tuned to this note style; new phrasing needs new rules (or an LLM extractor behind the same gates).
- Window assumptions (one week for single-day notes, 8 weeks for level shifts) are judgment calls.
- Weekly cost is a ratio of totals, so heavy shipments weigh more than light ones; mix changes can move it slightly.
- Retrieval is TF-IDF, not semantic embeddings; fine for 10 notes, would need embeddings + a vector DB at scale.
