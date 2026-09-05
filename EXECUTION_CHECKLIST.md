# PolarOS: Tactical Execution Checklist

## 🎯 Day-by-Day Breakdown (28 Days to Demo Victory)

### PHASE 1: Foundation (Days 1–3)
**Owner:** Backend lead + 1  
**Goal:** Verify reference code runs, extract real numbers for deck

- [ ] **Day 1, Morning**
  - [ ] Copy `PolarOS_prompts_1-4/` to project repo root
  - [ ] `cd PolarOS_prompts_1-4 && python3 generate_season.py`
  - [ ] Wait for season.db, check `season_stats.txt`
  - [ ] Screenshot the summary (print it)

- [ ] **Day 1, Afternoon**
  - [ ] Run `bash run_queries.sh`
  - [ ] Screenshot: q_burnrate (RED alert date)
  - [ ] Screenshot: q_crate_trace (CR-0005, hazard flag)
  - [ ] Screenshot: q_open_parties (overdue field party)

- [ ] **Day 1, Evening**
  - [ ] Run `python3 check_gates.py`
  - [ ] Verify all 5 gates PASS
  - [ ] Create `ground_truth.md` with exact numbers:
    - Total events: 4,625
    - Alert fired: 29 March 2027
    - Diesel zero-date: 2 Oct 2027
    - Overdue party: FP-07, 6 hours late
    - Bandwidth: 2,321 B worst day, 16.6 kB whole season

- [ ] **Day 2: Repeat on Different Machines**
  - [ ] Fresh clone on teammate's laptop
  - [ ] Run the same steps
  - [ ] Confirm byte-identical results
  - [ ] Verify: "reference impl is reliable"

- [ ] **Day 3: Gate Review**
  - [ ] Team meeting: review all extracted numbers
  - [ ] Commit ground_truth.md to git
  - [ ] Update deck template with real numbers (not placeholders)
  - [ ] Decision: "This is what we're showing. Final."

---

### PHASE 2: Build the 5 Modules UI (Days 4–10)

**Owner:** UI lead + 4 developers (one per module)  
**Goal:** Interactive mockups reading from real season.db

#### Module 1: Expedition Planning (Dev A)
- [ ] Read from season.db: MANIFEST_CREATED + PLACED_ON_LEG events
- [ ] Show: "397 of 400 items placed"
- [ ] Cards: Ship (200,000 kg), Basler (6,400 kg total), Heli (5,000 kg)
  - [ ] Utilization % on each
  - [ ] Sum of weight + volume
- [ ] Red badge for 3 UNPLACED items with diagnoses
- [ ] Button "Re-run solver" (optional: actually calls solver, or just shows canned output)
- [ ] Mobile: 375px width, big buttons

#### Module 2: Cargo Tracking (Dev B)
- [ ] Search bar: type crate ID or auto-populate with CR-0005 (the hazard demo)
- [ ] Timeline of events: Goa → Mumbai → Cape Town → Ship → Maitri
  - [ ] Show dates, who scanned, when
- [ ] Hazardous flag: "🚨 Declared 23 hours after leaving Goa"
- [ ] Color-code: normal = blue, hazard = red
- [ ] Animation (optional): scan effect at each handover
- [ ] Test with at least 3 crates (one normal, one hazard, one that went to Bharati)

#### Module 3: Inventory Forecast (Dev C) ⭐ THE STAR
- [ ] Query q_burnrate, show results as cards
- [ ] **RED card:** "Maitri Diesel — 2 Oct 2027"
  - [ ] Burn-rate graph: consumption line + projection
  - [ ] Alert badge: "⚠️ Alert fired 29 Mar 2027 — 190 days lead time"
  - [ ] Explains: "Discovery 7 months early. Time to act."
- [ ] **GREEN card:** "Maitri Food — 12 Feb 2028" (safe)
- [ ] Slider test: "What if we reduce consumption 10%?" → forecast shifts to later date
- [ ] Show past vs forecast in different colors
- [ ] Make this the demo centerpiece

#### Module 4: Personnel & Field Parties (Dev D)
- [ ] Query: roster with status (Goa/Ship/Station/Field/Home)
- [ ] Show 35 members, highlight 7 at Maitri + 5 at Bharati
- [ ] Field parties list:
  - [ ] FP-07: "Departed 25 Jan 07:00Z, ETA 18:00Z"
  - [ ] Status: "🚨 OVERDUE by 6 hours, now 00:00Z"
- [ ] Countdown for open parties (if still in future, show time left)
- [ ] Sort by status (overdue first)

#### Module 5: Emergency Response (Dev E)
- [ ] Card deck: Fire, Medical, Vehicle Stuck, Fuel Leak, etc.
- [ ] Tap a card → show procedure (readable offline)
  - [ ] Procedures are plain text, not images
  - [ ] ~5–10 steps per procedure
- [ ] **Big red button:** "Can we evacuate NOW?"
  - [ ] Check: nearest airstrip, ship location, current station, weather OK (yes/no/risky)
  - [ ] Show answer: "Yes, 2-hour window" or "No, storm incoming"
  - [ ] Explanation: where info came from (ship location, airstrip, party location)

**Deliverable:**
- [ ] `/ui/modules/` folder with 5 HTML or React components
- [ ] Each reads season.db (either sql.js in browser or local JSON endpoint)
- [ ] Each shows data from run #1 (ground_truth.md numbers)
- [ ] All work at 375px, high contrast, big touch targets
- [ ] No fake data. Every number is from the code.
- [ ] Test on both desktop and mobile emulation

---

### PHASE 3: Demo Script & Rehearsal (Days 11–17)

**Owner:** Presenter + tech support  
**Goal:** 3-minute walk-through that tells the Antarctic story with all 5 modules

- [ ] **Day 11: Script Writing**
  - [ ] Write `demo_sequence.md` with exact steps:
    - Act 1: Problem (30s)
    - Act 2: What we can see (45s)
    - Act 3: Things go wrong (60s)
    - Act 4: Why it works (15s)
  - [ ] Keystroke-by-keystroke: what to click, what to say
  - [ ] Timing for each section
  - [ ] Speaker notes (what if this fails? say this)

- [ ] **Day 12–14: Rehearsal (5 full run-throughs each day)**
  - [ ] Day 12: Messy run, learn the order
  - [ ] Day 13: Time it, tighten pacing
  - [ ] Day 14: Smooth run, handle mistakes gracefully
  - [ ] Goal: 3 min ±10 sec, every time

- [ ] **Day 15: Record & Review**
  - [ ] Screen record one full run
  - [ ] Watch it back, identify stalls
  - [ ] Fix the biggest pain points

- [ ] **Day 16–17: Edge Cases**
  - [ ] Run on 3 different machines (different OS, screen size, network)
  - [ ] Simulate network issues: slow click, lag
  - [ ] Prepare fallback narratives for each module if it stalls
  - [ ] Example: "Inventory module is loading... while that catches up, let me explain why this forecast matters..."

**Deliverable:**
- [ ] `demo_sequence.md`: full script with times, keystrokes, notes
- [ ] Screen recording of one polished run (3 min, named `demo_recording.mp4`)
- [ ] Speaker notes printed (carry to presentation)
- [ ] Fallback narratives written (in case a module lags)

---

### PHASE 4: Offline Mode & Network Switching (Days 18–21)

**Owner:** Backend/frontend lead  
**Goal:** "Cut the cable" moment where app works offline, then syncs

- [ ] **Day 18: Offline Infrastructure**
  - [ ] Add `localStorage` queue in one module (pick Inventory)
  - [ ] When network offline: queue events locally
  - [ ] Show chip: "⚠️ OFFLINE — 3 events queued"
  - [ ] Network check on app load (or allow manual toggle)

- [ ] **Day 19: Sync Visualization**
  - [ ] Add sync button (or automatic on reconnect)
  - [ ] Show: "Sending 3 events..." → progress bar
  - [ ] On success: "✓ Synced. Forecast updated."
  - [ ] On failure: "Sync failed. Retry?" (never auto-retry without asking)

- [ ] **Day 20: Demo Sequence (Offline)**
  - [ ] In Inventory module:
    - Log diesel entry offline (queue grows to 1)
    - Log 5 more offline (queue = 6)
    - Restore network, sync, watch forecast recalculate
  - [ ] Make this the climax of the demo

- [ ] **Day 21: Test**
  - [ ] Kill network, add 10 events, restore network, verify all synced
  - [ ] Refresh browser while offline, verify events still in queue
  - [ ] Network fails mid-sync, confirm fallback
  - [ ] Verify: no crash, no data loss, user always knows status

**Deliverable:**
- [ ] `offline_mode.js/tsx`: event queue + sync + UI chip
- [ ] Network toggle (hidden or in dev menu) for demo
- [ ] Test suite: offline mode handles crashes, reconnects, etc.
- [ ] Demo script updated with exact offline steps + timing

---

### PHASE 5: Pitch Deck Polish (Days 22–25)

**Owner:** Presenter + designer  
**Goal:** 10–12 slide deck that supports the demo, doesn't repeat it

**Slides (in order):**

1. [ ] **Title Slide**
   - Title: "PolarOS: Antarctic Expedition Logistics, Offline-First"
   - Subtitle: "SIH 2026 | [Your college]"
   - Visual: ship on ice or station in darkness

2. [ ] **The Problem (2 bullets)**
   - "9 months isolation. No resupply Dec–Feb."
   - "Today: PDFs, memory, hope. Result: late discovery of shortages, missed handovers, zero traceability."

3. [ ] **Our Solution (1 sentence + diagram)**
   - "Append-only event log. Three nodes (Goa/Ship/Station) sync when internet appears."
   - Diagram: three boxes with arrows labeled "sync when online"

4. [ ] **Why This Works**
   - "No clocks needed" (each node counts its own events)
   - "No conflicts" (append-only, can't edit)
   - "Cheap syncing" (only send new events)

5. [ ] **The Schema**
   - Screenshot of `schema.sql` structure: 18 event types
   - One table: event_id, timestamp, node_id, type, payload

6. [ ] **Real Numbers**
   - "4,625 events in one simulated season"
   - "400 manifest items | 35 personnel | 3 stations"
   - "Zero conflicts across any sync"
   - (cite: season_stats.txt)

7. [ ] **Diesel Forecast (The Proof)**
   - Graph: consumption trend + projected line hitting zero on 2 Oct
   - Red badge: "Alert fired 29 March — 190 days before crisis"
   - Caption: "The discovery that saves the season"

8. [ ] **Crate Trace (Accountability)**
   - Show CR-0005 custody chain: Goa → Mumbai → Cape Town → Ship → Station
   - Red flag: "Declared hazardous 23 hours after leaving Goa"
   - Caption: "Every handover is a record, not an email thread"

9. [ ] **The 5 Modules (5 screenshots)**
   - One row: Planning | Tracking | Inventory | Personnel | Emergency
   - Each is a thumbnail showing real data

10. [ ] **Bandwidth Reality**
    - "Maitri's entire season: 16.6 kB gzipped"
    - "Fits in 2% of one 15-minute satellite window"
    - "Worst-case day: 2.3 kB, 12.9 seconds transmission"

11. [ ] **What We Didn't Do (& Why)**
    - ❌ No blockchain (we trust each other)
    - ❌ No drones (system needs only a laptop)
    - ❌ No AI chatbot (they need answers, not conversation)
    - Caption: "We chose boring things on purpose."

12. [ ] **Demo**
    - "Next: live demonstration."
    - No bullet points. Just one striking image (ship + laptop).

**Design Rules:**
- [ ] Black text, white background (or high-contrast dark mode)
- [ ] No animations
- [ ] One visual per slide max
- [ ] Every number sourced: "(season_stats.txt, line 14)"
- [ ] Font: sans-serif, 28pt min
- [ ] No gradients, no textures, no company logos

**Deliverable:**
- [ ] Deck saved as PDF (for backup) + native format (.pptx or .key)
- [ ] Every slide has speaker notes printed
- [ ] Proofread: all numbers match ground_truth.md
- [ ] Test projector: does it read? (don't discover tiny fonts on presentation day)

---

### PHASE 6: Dry Run & Q&A Mastery (Days 26–28)

**Owner:** Presenter + tech lead  
**Goal:** Run full presentation (deck + demo + Q&A). Record it. Fix.

- [ ] **Day 26: Hostile Dry Run**
  - [ ] Book a room with projector
  - [ ] Invite 3–4 people: professor, TA, teammate from another project (NOT your team)
  - [ ] Run full presentation as timed:
    - Deck: 5 min
    - Demo: 3 min
    - Q&A: 5 min
  - [ ] Record audio + screen
  - [ ] DO NOT INTERRUPT: let judges ask whatever they want
  - [ ] Debrief: what surprised you? Where did you stumble?

- [ ] **Day 27: Fix & Q&A Prep**
  - [ ] Watch recording, note rough spots
  - [ ] Fix top 3 issues
  - [ ] Memorize Q&A answers (see "Anticipated Q&A" section in main plan):
    - [ ] Why offline-first?
    - [ ] Why append-only?
    - [ ] Why not blockchain?
    - [ ] How does solver scale?
    - [ ] What about corruption?
    - [ ] Can people edit events?
  - [ ] Practice answers without reading from notes

- [ ] **Day 28: Final Rehearsal**
  - [ ] One more full run-through (deck + demo + Q&A)
  - [ ] Time it: 3–4 min under the total limit
  - [ ] Presenter should feel confident, not memorized
  - [ ] Tech support ready with backup laptop

**Deliverable:**
- [ ] Dry-run recording saved
- [ ] Q&A cheat sheet printed (carry to presentation)
- [ ] Backup: USB drive with slides + demo code (on you, not in backpack)
- [ ] Two machines ready (primary + backup)

---

## ✅ Pre-Presentation Checklist (Morning of)

- [ ] Projector works with presenter's laptop
- [ ] Demo code is pulled fresh (test on cold machine)
- [ ] season.db exists and is not corrupted (`sqlite3 season.db "PRAGMA integrity_check;"`)
- [ ] All three proof queries run in < 2s each
- [ ] Network toggle works (offline mode tested)
- [ ] Backup USB has: slides, demo code, season.db, demo script
- [ ] Presenter slept 8 hours
- [ ] Presenter has done this 20+ times (mentally rehearsed, not actual)
- [ ] Team has agreed on Q&A talking points
- [ ] No new code added to main branch in last 48 hours

---

## 🏆 The Moment That Wins

**The Offline Demo (Day 18–21, refined through Phase 6)**

Judges expect you to claim "offline-first works." You will SHOW them:

1. App running normally, synced with Goa
2. Network kills
3. Officer logs diesel consumption WHILE OFFLINE
4. Chip appears: "⚠️ OFFLINE — 1 event queued"
5. Officer logs 5 MORE consumptions, still offline, app never crashes
6. Chip: "OFFLINE — 6 events queued"
7. Network restores
8. Tap SYNC
9. Watch events drain in real time
10. Forecast recalculates with fresh data
11. No conflicts, no manual merge, no "which copy is right?" question
12. Chip disappears: "✓ SYNCED"

That is not a feature. That is a proof that your architecture works.

Do this, do it smooth, and you will win.

---

## 📞 Quick Links

- **Reference code:** `/PolarOS_prompts_1-4/`
- **Ground truth:** `ground_truth.md` (to be created Day 1)
- **Demo script:** `demo_sequence.md` (Days 11–14)
- **Q&A ammo:** Section 6 of the execution plan
- **Slack:** If blocked, post error + stack trace, tag the backend lead

---

**Last Updated:** 5 Sep 2026  
**Status:** Ready to execute  
**Confidence:** High (you have working reference code)
