# PolarOS — Solver Worksheet + Prompts (Owner: A)
**Module:** Expedition Planning — the capacity solver | **Tool:** Google OR-Tools **CP-SAT** (Python)
**Prerequisite:** Gate 1 passed — `season.db` exists and you can query the manifest out of it.
**Deck promise this module must keep:** *"assigns every manifest line to ship / Basler / heli within real weight limits; flags what cannot make the season"* and *"an infeasible season must be flagged, not fudged."*

Read this whole sheet before touching the prompts. The solver is the one module where a badly-guided AI will produce **plausible-looking nonsense** — code that runs, prints a plan, and is silently wrong. Your defense is this worksheet: it fixes the contract *before* any code exists, so you can test the AI's output against it.

---

## 1. What you are building, in one sentence

A program that reads the ~400 manifest lines and the season's transport capacity, and either returns a **complete legal assignment** (every item → one transport leg, no rule broken) or a **named refusal** (exactly which items cannot make it, and why, and what would fix it).

Not a suggestion engine. Not a ranking. A yes-with-proof or a no-with-reasons.

## 2. The input contract (write this file BEFORE the solver)

Two inputs, both plain and inspectable:

**(a) Items** — pulled from `season.db` (the MANIFEST_CREATED events):
```
item_id, weight_kg, volume_m3, hazard (0/1), destination (MAITRI/BHARATI/SANDHI), needed_by (date)
```

**(b) Transport legs** — a hand-written `legs.json` you author from our sourced facts. Each leg:
```
leg_id, mode (SHIP/BASLER/HELI), arrives_at (station), arrival_date,
payload_kg (capacity), payload_m3, hazard_ok (true/false), pax_kg_reserved
```
Season one, keep it small and honest:
- SHIP-M: arrives MAITRI late Dec — huge capacity (e.g. 200,000 kg), hazard_ok = true
- SHIP-B: arrives BHARATI mid-Jan — same ship, second anchorage
- FLT-1..FLT-4: Basler legs Novo→Zenit→BHARATI, ~Nov–Jan dates, **payload_kg = 1800 minus pax_kg_reserved for that leg**, hazard_ok = false
- HELI-1..HELI-2: only within the ship's anchorage windows, small payload, hazard_ok = false (keep fuel on the ship's own crane path)
- Optionally LAND-M: Novo→Maitri surface transfer for light urgent items, tied to intercontinental flight dates

Why hand-written? Because every number in `legs.json` must trace to an NCPOR-published fact or be labelled an assumption. This file IS your defense in Q&A — a judge asks "where does 1,800 come from?" and you point at the line and the notice.

## 3. The rules (constraints) — the complete list

Number them. In code, in comments, and in your head, they keep these numbers:

- **C1 — One home:** every item is assigned to exactly one leg (or to the explicit set UNPLACED — see §5).
- **C2 — Weight:** sum of item weights on a leg ≤ that leg's payload_kg.
- **C3 — Volume:** same for volume.
- **C4 — Hazard:** hazard items only on legs with hazard_ok = true. (This encodes "hazardous cargo cannot fly.")
- **C5 — Destination:** an item may only ride a leg that arrives at its destination station. (Version 1 keeps it this simple — no transshipment modelling. Say so out loud; it's an honest scope cut.)
- **C6 — Deadline:** leg.arrival_date ≤ item.needed_by.
- **C7 — Heavy = ship:** items above a threshold (e.g. weight > 500 kg or volume > 2 m³) may only take SHIP legs, even if a flight could technically lift them (door/handling limits).

That's all of version 1. Resist adding more. Every extra constraint is another thing to defend.

## 4. The objective — what "best" means

CP-SAT first finds *feasible*; the objective picks among feasible plans. Ours, in priority order:
1. **Maximize placed items** (equivalently: minimize UNPLACED count) — weighted so that placing items always beats everything else;
2. then **prefer earlier arrival slack** (arrive well before needed_by, not on the last day);
3. then **prefer ship over flights** for anything that can wait (flights are the scarce, costly resource).

Implement as one weighted sum with big/medium/small weights (e.g. 10,000 / 10 / 1) and write the weights as named constants with comments. A judge may ask "why does the solver put X on the ship?" — the answer must be readable in the objective, not shrugged at.

## 5. The refusal spec — the feature that wins the marks

When the full problem is infeasible (or items end up UNPLACED), the output must NOT be a stack trace or a bare "INFEASIBLE". Required behavior:

1. Model UNPLACED as an allowed (but heavily penalized) assignment — so the solver always returns, and the "impossible" items surface as the UNPLACED set. (This is the standard soft-constraint trick; it turns infeasibility into information.)
2. For each UNPLACED item, print a **diagnosis** by checking its constraints against the legs: *"OZN-114 (300 kg, needed 5 Jan, BHARATI): ship arrives 15 Jan — too late (C6); flights 1–2 full by 240 kg (C2). Fix: +1 flight before 5 Jan, or relax needed_by to 16 Jan, or shed 240 kg from FLT-1/2."*
3. End with the one-line summary the screen will show: **"397 of 400 placed. 3 items cannot make the season — details above."**

This section is the deck's "flagged, not fudged" made real. Spend a third of your effort here; it is the demo's talking point.

## 6. Acceptance tests (run all five before you believe anything)

- **T1 Happy path:** default season → 100% placed; every leg's totals within capacity (verify with an independent checking script that re-adds the weights — never trust the solver's own claim).
- **T2 Planted overload:** shrink FLT capacities until some items can't fly → solver returns with a small UNPLACED set + diagnoses naming C2/C6.
- **T3 Hazard trap:** give a hazard item a deadline only a flight could meet → it must go UNPLACED with a C4/C6 diagnosis, NEVER onto a flight.
- **T4 Determinism:** same inputs, two runs → same plan (fix random seed / use a single worker if needed).
- **T5 Speed:** full 400-item season solves in < 30 s on a laptop (expect < 2 s).

**Truth discipline, as always:** whatever T1's real placement numbers are, they become the deck/demo numbers. And the checking script from T1 is not optional — it's your proof that the plan is legal, independent of the library.

## 7. What NOT to build (say why, in one line each)
- No multi-hop transshipment (ship→station→heli chains): version 2; C5 keeps v1 honest and small.
- No weather modelling: legs.json dates are planning assumptions; re-running with changed legs IS our weather response.
- No cost optimization in rupees: we don't have sourced cost data; placement + slack is defensible, invented prices are not.
- No fancy UI: output is a table + the refusal text; the mockup screen consumes it later.

---

## PROMPT PACK (run in order, fresh chats, paste context in)

### PROMPT S1 — Model design review (no code yet)
> I'm building a cargo-assignment solver with Google OR-Tools CP-SAT for a student hackathon project (Antarctic expedition logistics). Before writing code, review my model design:
> [paste §2 input contract, §3 constraints C1–C7, §4 objective, §5 refusal spec from my worksheet]
> Questions: (1) Is x[item, leg] as Boolean assignment variables with C1 as exactly-one (plus an UNPLACED pseudo-leg) the right CP-SAT formulation? (2) Weights and volumes are floats — how should I scale them to integers for CP-SAT, and what rounding rule is safe for capacity constraints? (3) Any constraint here that's redundant, or any interaction between C4/C6/C7 that could surprise me? (4) How do I make the solve deterministic across runs?
> Do NOT write the solver yet. Answer the questions and show me only tiny illustrative snippets.

**Accept when:** you can restate its answers in your own words — especially the integer-scaling rule (kg stay integers; round capacities DOWN, demands UP so rounding never creates fake capacity).

### PROMPT S2 — legs.json + loader
> Same project. Here is my transport-legs spec: [paste §2(b)]. Write (1) a `legs.json` with the legs I listed, every number as a named field, and a "source" string on each leg ("NCPOR notice: Basler ≤1800 kg incl pax" or "ASSUMPTION: 2 heli days per anchorage"); (2) `load_inputs.py` that reads items from my SQLite `season.db` (MANIFEST_CREATED events — schema: [paste]) and legs from the json, validates both (positive weights, dates parse, destinations known), and prints a one-screen summary: item count, total kg by destination, leg capacities. Python stdlib + sqlite3 only.

**Accept when:** the summary's totals match a hand-check of 5 random items against the DB.

### PROMPT S3 — the solver itself
> Same project. Context: [paste worksheet §3, §4, §5 + the S1 conclusions + load_inputs.py]. Write `solve_season.py` using OR-Tools CP-SAT:
> - Boolean x[i,l] incl. an UNPLACED pseudo-leg; exactly-one per item (C1); capacity constraints C2/C3 with the integer scaling we agreed; hazard C4, destination C5, deadline C6, heavy-item C7 as variable eliminations (don't even create illegal x[i,l] — smaller model, faster solve).
> - Objective per my §4 with named weight constants.
> - Deterministic: fixed seed, num_search_workers=1.
> - Output: (a) `plan.csv` (item_id, leg_id, arrival_date, slack_days); (b) per-leg utilization table (used/capacity kg and m³); (c) the §5 refusal block for UNPLACED items with constraint-named diagnoses and suggested fixes; (d) the one-line summary.
> - Then a SEPARATE `check_plan.py` that re-verifies every constraint from plan.csv + inputs with plain Python (no OR-Tools) and prints PASS/FAIL per constraint.
> Comment heavily — a 3rd-year student must defend every block to a jury.

**Accept when:** all five tests T1–T5 from my worksheet pass, and `check_plan.py` says PASS on T1 and correctly FAILs if I hand-corrupt one line of plan.csv.

### PROMPT S4 — the diagnosis polish
> Here is my working solver [paste solve_season.py] and a T2 run's output [paste]. The refusal block is the demo's key feature. Improve ONLY the diagnosis function: for each UNPLACED item, test it against every leg and report the FIRST failing constraint per leg in a compact table (leg × reason), then derive the top-2 concrete fixes (add a leg before date D / relax needed_by to the earliest feasible leg date / free N kg on leg L). Keep it under 60 lines, pure Python, no solver re-runs inside diagnosis.

**Accept when:** the T2 and T3 outputs read like something a logistics officer could act on without knowing what CP-SAT is.

### PROMPT S5 — red-team the solver (final week, with F)
> Act as a hostile jury member who knows operations research. Here is my solver [paste code + a T1 and T2 output]. Ask me the 8 hardest questions about modelling choices, integer scaling, determinism, the UNPLACED trick, greedy-vs-exact, and what happens when weather cancels FLT-2. Don't answer them; after I reply, grade my answers and show stronger versions.

---

## Q&A ammunition (learn these cold)
- *"Why CP-SAT and not writing your own algorithm?"* → "The rules interact — deadline × hazard × capacity. Exhaustive search with pruning is a solved problem; our contribution is the faithful model of NCPOR's rules, and the independent checker that proves the plan legal."
- *"How do we know the solver is right?"* → "We don't trust it — `check_plan.py` re-verifies every constraint with 30 lines of plain Python. The solver proposes; arithmetic disposes."
- *"What's the UNPLACED trick?"* → "A pseudo-leg with a huge penalty. It converts 'INFEASIBLE' from a dead end into a list: exactly which items, exactly which rule blocks them, exactly what would fix it. The refusal is the feature."
- *"Weather cancels a flight?"* → "Delete the leg from legs.json, re-run, 2 seconds. The plan is cheap; the model is the asset."

**Definition of done:** legs.json (with sources), load_inputs.py, solve_season.py, check_plan.py, the five test outputs committed, and the real placement numbers handed to the mentor for the deck. Then you own the "engineering choices" card *"OR-Tools ILP over greedy heuristics"* in every Q&A for the rest of the season.
