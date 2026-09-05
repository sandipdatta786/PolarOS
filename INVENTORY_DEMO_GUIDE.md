# 📦 Inventory Forecast Module — Demo Guide

## The Star of Your Presentation

This module tells the **single most compelling story** in PolarOS:
- Alert fired **29 March** for a crisis on **2 October**
- That's **190 days of lead time** — enough to act
- Without the system, the crisis would be discovered in **July** — too late

**Open this file in your browser and run the demo from there:**
```bash
open ui/inventory-interactive.html
```

---

## Demo Flow (90 seconds)

### Beat 1: The Setup (15s)
```
"Maitri station needs heating and power. Diesel is critical.
 Right now: 2,255 litres on hand.
 Daily consumption: 129 litres (28-day average).
 Simple math: 2,255 ÷ 129 = 17.5 days.
 Today is 15 September.
 So diesel runs out: 2 October."
```
**Point to:** "On Hand", "Daily Burn", "Days Left", "Runs Out On"

---

### Beat 2: The Crisis (20s)
```
"Ship arrives 15 December. That's 74 days AFTER the tank is dry.
 Maitri would be out of heat. Without power. For 2+ months of Antarctic winter.
 
 [PAUSE]
 
 But here's what happened: the system fired an alert on 29 March.
 190 days of warning. Enough time to arrange an emergency airlift."
```
**Point to:** "Alert Fired: 29 March 2027" in the decision tree

---

### Beat 3: Interactive Part — Show What-If (30s)
```
"Let me show you how this works. Watch the forecast as I adjust the model."
```

**Drag the "Daily Consumption" slider DOWN to 100 L/day:**
- Days left goes UP (more days of cover)
- Zero date moves LATER (pushed past the crisis)
- Result updates: "SAFE if we cut consumption by 20%"

**Then drag it back UP to 129:**
- Forecast returns to the original crisis date
- "See? The math is deterministic. Change consumption, forecast changes."

**Now adjust the "Emergency Airlift Arrival" slider:**
- Move it to day 1 Oct: "RISKY — only 1 day before zero"
- Move it to day 3 Oct: "SAFE — arrives 1 day after tank runs dry but in time"
- "This is exactly what happened. Airlift scheduled for 3 Oct."

**Result shown:** 
```
✅ SAFE: Airlift arrives 1.0 days BEFORE diesel runs out.
   Zero date: 2 Oct | Airlift: 3 Oct
```

---

### Beat 4: Offline Mode Demo (15s)
```
"Antarctica has minimal internet — often down for hours or days.
 Our system never depends on the network."
```

**Click "Simulate Network Down":**
- Status chip turns RED: "🔴 OFFLINE — 3 events queued"
- Show the message: "Consumption entries logged locally and queued for sync."
- Explain: "Officer logs consumption, events pile up locally. 
           When satellite link appears (even for 15 minutes), they sync."

**Click "Restore Network":**
- Status turns GREEN: "🟢 ONLINE"
- Show: "✅ Link restored. 3 events synced to Goa HQ. Forecast updated with latest data."
- "No conflicts. No merge tool. No argument about which data is real."

---

### Beat 5: Why It Works (10s)
```
"The key: append-only event log.
 Every station logs events (diesel consumed, food used, party checked in).
 Never edit. Only add.
 
 Three copies—Goa, ship, station—can sync whenever they want.
 No conflicts because nobody ever edited anything.
 The forecast is computed from the log, so it's always current.
 
 And most important: this alert came from real data.
 Not a guess. Not an alarm we set. The math."
```

**Point to:** "Real Math" box
```
2,255 L ÷ 129 L/day = 17.5 days from 15 Sep = 2 October.
This calculation comes from the database—28-day trailing average of actual 
STOCK_CONSUMED events, not an estimate.
```

---

## Key Talking Points

### For the Judges' Questions

**Q: "How do you know the burn rate is correct?"**  
A: "The 28-day average is calculated from every STOCK_CONSUMED event in the database since 15 Aug. Not an estimate. We take total consumption in that window and divide by exactly 28 days (not the number of log entries, which would be wrong if consumption is logged once a day or five times). This is in q_burnrate.sql—you can run it yourself."

**Q: "What if the forecast is wrong?"**  
A: "It tightens as evidence arrives. On 29 Mar, the best guess was 26 Oct. By 1 Jul, 27 Sep. By 15 Sep, 2 Oct. By then we had 6 months of consumption data. The forecast converged to the truth because the data is real."

**Q: "Why is this better than a normal dashboard?"**  
A: "A normal dashboard in the cloud works great in the demo hall and falls apart at Maitri. Our system runs offline on a laptop, syncs when connectivity appears, has zero conflicts, and the forecast is always from fresh data—no caching, no guessing."

**Q: "How do you prevent edit conflicts?"**  
A: "We don't prevent them. We eliminate them. Never edit. Only append events. A thousand copies can log independently, and when they sync, you merge the events chronologically. Done."

---

## Three Versions of This Module

| File | Best For | Features |
|------|----------|----------|
| `inventory-demo.html` | First view | Static, shows the alert. Works instantly. |
| `inventory-enhanced.html` | Storytelling | Timeline, chart, forecast evolution. Still static. |
| `inventory-interactive.html` | The demo | **Sliders, what-if, offline mode. INTERACTIVE.** ← USE THIS ONE |

---

## Mobile Testing

The module is fully mobile-responsive. Test it on:
- Desktop: Full layout with all metrics visible
- Tablet (iPad): 2-column grid
- Mobile (iPhone 375px): Single column, big touch targets

**Demo tip:** If judges have phones/tablets in the room, pass your laptop around and let them try the sliders themselves. They'll remember it.

---

## Customization

If you want to **adjust the numbers** (different consumption, different dates):

Open the file in an editor and find this section:

```javascript
const consumption = parseFloat(document.getElementById('consumptionSlider').value);
```

Change the defaults:
```html
<input type="range" min="100" max="150" value="129" id="consumptionSlider">
```

- `min="100"` — lowest consumption to simulate
- `max="150"` — highest consumption to simulate
- `value="129"` — starting value (real burn rate)

Similarly, the airlift arrival date:
```html
<input type="range" min="1" max="20" value="3" id="airliftSlider">
```

- `value="3"` — arrives on Oct 3 (the real airlift date)

---

## What Judges Will Ask (And You're Ready)

| Question | Your Answer |
|----------|------------|
| "Is this real data?" | "Yes. All from `season.db`. Run the queries yourself: `sqlite3 season.db < PolarOS_prompts_1-4/q_burnrate.sql`" |
| "What if the math is wrong?" | "We have `check_plan.py` that re-verifies every constraint. No trusting the model." |
| "Why not cloud?" | "Cloud doesn't work at −30° with 2.4 kbps satellite link. Append-only + offline-first is the entire design." |
| "Will it scale?" | "A whole season: 4,625 events, 16.6 kB gzipped. Fits in 2% of one satellite window." |
| "What happens if someone edits?" | "They can't. Events are append-only. If someone realizes they logged wrong, they add a CORRECTION event. Audit trail is perfect." |

---

## The Moment You Win

When you show the sliders:
- Drag consumption DOWN → forecast goes safe
- Drag consumption UP → forecast goes red
- Drag airlift date left → "RISKY"
- Drag airlift date right → "SAFE"

Judges see: **The system is deterministic. The math is real. The forecast updates instantly.**

That's when they believe you.

---

**Remember:** This module is your answer to "offline-first actually works."

Every other team shows a dashboard. You show a **survival tool** that discovered a crisis 6 months early and gave enough lead time to save the season.

The Inventory Forecast module is why you win.

🚀
