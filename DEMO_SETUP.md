# 🚀 PolarOS Demo Setup Guide

## For Presentation Day

### Quick Start (60 seconds)

```bash
# On any machine with a browser:
cd /Users/user/Downloads/PolarOS
open ui/index.html
```

That's it. Demo is live.

---

## What You're Showing

**Five modules in one dashboard.**

Tab order = demo flow:

1. **Inventory Forecast** — Drag the consumption slider, watch forecast change
2. **Cargo Tracking** — Show the custody chain, point out the 223-hour hazard declaration gap
3. **Personnel & Parties** — Tap "Field Parties" tab, show FP-07 overdue 6 hours
4. **Expedition Planning** — Show 397/400 items placed, why the 3 can't make it
5. **Emergency Response** — Tap the MEDEVAC button, show the decision tree

---

## The 3-Minute Demo Script

### Setup (15 seconds)
```
"Antarctica. 35 people. 400 items. 9 months offline.

This system answers five questions."
```

### Tab 1: Inventory (45 seconds)
```
[CLICK Inventory Forecast tab]

"Question 1: Stock. 

Maitri needs diesel for heating and power.
On hand: 2,255 litres.
Daily burn: 129 litres.
Ship arrives: 15 December.

Math: 2,255 ÷ 129 = 17.5 days from today.
Result: Diesel runs out 2 October.

But here's the important part:
Alert fired 29 March—190 days before the crisis.
That's SIX MONTHS to act.

[DRAG SLIDER LEFT to 100 L/day]
Watch the forecast go safe.

[DRAG SLIDER RIGHT to 150 L/day]
Watch it go critical.

Interactive. Real data. Live math."
```

### Tab 2: Cargo (30 seconds)
```
[CLICK Cargo Tracking tab]

"Question 2: Cargo. Where is it, who touched it.

This crate was packed 10 October.
Hazardous materials inside.
By IMDG law, paperwork must travel with it from day one.

It wasn't declared until 19 October.
223 hours late.
By then, the crate was already in transit.

System caught it. Automatically. 

No email chains. No paperwork. No guessing.
The audit is built in."
```

### Tab 3: Personnel (30 seconds)
```
[CLICK Personnel & Field Parties tab]
[CLICK on 'Field Parties' tab within the page]

"Question 3: People. Are they safe.

Field party FP-07 left at 7 AM.
Expected back at 6 PM.
Didn't return until midnight.
6 hours overdue.

System raised an alert automatically.

Without this system, someone at the radio has to remember to check.
With 5 field parties active, that's error-prone.
This system never forgets."
```

### Tab 4: Expedition (30 seconds)
```
[CLICK Expedition Planning tab]

"Question 4: Logistics. What fits?

400 items to send.
Three ways to send them: ship (huge), flights (fast), helicopter (emergency).

The solver assigns each item without breaking any rule:
- Weight limits
- Hazmat restrictions
- Deadlines
- Destination

Result: 397 items placed.
3 items can't make it—and we KNOW why, in September.
Five months to arrange alternatives.

Not discovered in January on the ice.
Discovered now, when there's time to fix it."
```

### Tab 5: Emergency (30 seconds)
```
[CLICK Emergency Response tab]

"Question 5: Emergency. Can we evacuate NOW?

Worst case: someone critical at Maitri.

[CLICK MEDEVAC BUTTON]

The system checks:
- Where is the ship?
- Where is the nearest airstrip?
- What's the weather window?
- Can the helicopter launch?

Answer: YES, 2-hour window.

One button. Four questions answered. One decision.
Under pressure. In seconds. Every time.

Offline. Readable. Always current."
```

### Closer (15 seconds)
```
"Five screens. One event log.

Append-only. No clocks needed. No conflicts.
Three copies—Goa, ship, station—sync when they can.

Offline first. That's the design.

Because in Antarctica, you can't depend on the internet.
You depend on the system."
```

---

## Rehearsal Checklist

- [ ] Run through script 10 times (time yourself—must be 3 min ±10 sec)
- [ ] Practice on 2 different machines (different OS if possible)
- [ ] Verify all modules load (sometimes iframes load slow on first run)
- [ ] Time each tab click—make sure it's <1 second
- [ ] Test the sliders (drag them smoothly, let the chart re-render)
- [ ] Click MEDEVAC button—verify modal pops up
- [ ] Test on mobile (375px width) to ensure responsive
- [ ] Backup on USB stick: entire `/ui` folder
- [ ] Backup git repo: `git clone` URL on USB or separate laptop

---

## On Presentation Day

### 30 Minutes Before

```bash
# Fresh test on presentation machine
cd /Users/user/Downloads/PolarOS
git pull  # or git clone if fresh
open ui/index.html
```

- [ ] All 5 modules load
- [ ] Sliders work
- [ ] MEDEVAC button works
- [ ] No lag on tab switches
- [ ] Run 1-minute version of script (just the hits)

### During Demo

- Keep script handy (printed, not on screen)
- Move slowly between tabs (let judges see each one)
- Read the script naturally—don't memorize word-for-word
- Pause after each big moment for effect
- Make eye contact, not at screen
- Let the demo do the talking (your job is to narrate, not explain)

### If Something Breaks

**Fallback 1: Tap "Overview" tab**
- Shows all 5 modules as cards
- You can click each card manually
- Works even if iframes are slow

**Fallback 2: Open modules as separate tabs**
- Close the dashboard
- Manually open each HTML file:
  - `inventory-interactive.html`
  - `cargo-tracking.html`
  - `personnel-parties.html`
  - `expedition-planning.html`
  - `emergency-response.html`
- Flow through them in that order

**Fallback 3: Screenshot backup**
- Print screenshots of each module
- Have them ready (PDF on laptop)
- If network dies, you've got visuals

---

## Demo Talking Points (Memorize These)

**If judge asks "Why offline-first?"**
> "Antarctica's satellite link is 2.4 kbps and fails for hours. We can't depend on the internet, so we built a system that doesn't. Offline-first means three copies go months without talking, then sync when a link appears. No conflicts because we never edit—only append events."

**If judge asks "How do you know the forecast is right?"**
> "The 28-day burn rate is calculated from actual STOCK_CONSUMED events in the database. It's not an estimate. We divide total consumption in the window by exactly 28 days. The math is shown on the screen."

**If judge asks "Isn't this just a dashboard?"**
> "It's more than that. Every screen you see is reading from an immutable event log. The forecast updates live because new events are constantly being appended. The UI is the smallest part—the architecture is the win."

**If judge asks "Can you show offline mode?"**
> "Yes. [Open browser dev tools → offline mode] The app keeps working. Events queue locally. When we restore network, they sync. No data loss, no conflicts."

---

## Files You'll Need (On USB Stick)

```
├── ui/
│   ├── index.html                    (main dashboard)
│   ├── inventory-interactive.html    (module 1)
│   ├── cargo-tracking.html          (module 2)
│   ├── personnel-parties.html       (module 3)
│   ├── expedition-planning.html     (module 4)
│   └── emergency-response.html      (module 5)
├── PolarOS_prompts_1-4/             (reference data)
│   └── season.db                    (the real database)
└── DEMO_SCRIPT_FINAL.txt            (this script, printed)
```

---

## Success Criteria

✅ All 5 modules load  
✅ Demo runs 3 min ±10 sec  
✅ Every judge question has a 1-sentence answer  
✅ You can run it on any fresh laptop  
✅ You've rehearsed 10+ times  
✅ You're confident  

---

## You've Got This

You built:
- 5 fully working modules
- 1 unified dashboard
- A complete story
- Real data backing everything

You're ready.

🚀

---

**Last check before walking in:**
- [ ] Laptop charged
- [ ] USB stick in pocket
- [ ] Script printed and in pocket
- [ ] Rehearsed one last time this morning
- [ ] You feel ready

Go win.
