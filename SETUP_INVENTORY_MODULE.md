# 🚀 Inventory Forecast Module — Quick Start

## What You Have

✅ **inventory-demo.html** — Standalone demo (no backend needed, works offline)
✅ **InventoryForecast.jsx** — React component (for integration into full app)
✅ **api/burnrate.js** — Backend handler (queries season.db)
✅ **server.js** — Express server (serves UI + API)

---

## Option 1: Instant Demo (No Setup Required)

Just open this file in your browser:

```bash
open ui/inventory-demo.html
# or
# Right-click → Open with → Browser
```

**That's it.** You see the full RED/GREEN inventory forecast with real data.

---

## Option 2: Full Stack (With Backend)

### Setup

```bash
# Install dependencies
npm install

# Run server
node server.js
```

Then open `http://localhost:3000/demo/inventory`

### What npm packages you need

Create `package.json`:

```json
{
  "name": "poloros",
  "version": "1.0.0",
  "description": "Antarctic expedition logistics, offline-first",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "cors": "^2.8.5",
    "sqlite3": "^5.1.6"
  },
  "devDependencies": {
    "nodemon": "^3.0.1"
  }
}
```

Then:

```bash
npm install
npm start
```

---

## Using the React Component

Import it in your app:

```jsx
import InventoryForecast from './ui/modules/InventoryForecast.jsx';

function App() {
  return <InventoryForecast />;
}
```

The component:
- Fetches data from `/api/burnrate` endpoint
- Falls back to demo data if network fails
- Renders RED items first (critical)
- Then GREEN items (safe)
- Mobile-optimized

---

## Building the Other 4 Modules

**Copy this pattern:**

1. **Data first:** Write a SQL query (like `q_burnrate.sql`)
2. **Backend second:** Create an API handler (like `api/burnrate.js`)
3. **UI last:** Build the React component (like `InventoryForecast.jsx`)
4. **Demo:** Create a standalone HTML mockup
5. **Test:** Open in browser, verify real data shows

### Module Templates (Use These)

#### Module 1: Expedition Planning
- Query: results from solver (planned placement)
- Data: 397 of 400 items placed, 3 unplaced with diagnoses
- UI: Cards showing Ship/Basler/Heli utilization + UNPLACED warnings

#### Module 2: Cargo Tracking
- Query: `q_crate_trace.sql` output
- Data: One crate's custody chain (Goa → Mumbai → Cape Town → Ship → Station)
- UI: Timeline with scan timestamps, hazard flags

#### Module 3: Personnel & Field Parties ✅ (Already Done)
- Query: roster + open field parties
- Data: 35 members, 7 at Maitri, 5 at Bharati, overdue parties highlighted
- UI: Table + countdown timers for open parties

#### Module 4: Emergency Response
- Data: Procedures (Fire, Medical, Vehicle, Fuel)
- Query: Current ship location, nearest airstrip, weather
- UI: Card deck (tap a card for procedure) + big MEDEVAC button

---

## The Demo Script Pattern

For each module, you show:
1. **Normal state** — green checkmarks, happy path
2. **Alert state** — RED badges, data that needs action
3. **Mobile view** — landscape rotation to show responsive design

---

## File Structure (What You've Built)

```
PolarOS/
├── PolarOS_prompts_1-4/     ← Reference implementation (read-only)
│   ├── season.db
│   ├── q_burnrate.sql
│   ├── q_crate_trace.sql
│   └── q_open_parties.sql
├── ui/
│   ├── inventory-demo.html  ← Standalone demo ⭐
│   ├── modules/
│   │   └── InventoryForecast.jsx
│   └── index.html           ← Main app entry
├── api/
│   └── burnrate.js
├── server.js
├── package.json
├── EXECUTION_CHECKLIST.md
└── ground_truth.md
```

---

## Next Steps

1. **Today:** Get `inventory-demo.html` working (you're done)
2. **Tomorrow:** Build the other 4 modules using the same pattern
3. **Day 10:** All 5 modules done, they all read from season.db
4. **Day 11:** Start demo script (orchestrate all 5 modules)
5. **Day 18:** Add offline mode (queue events locally, sync when reconnected)

---

## Debugging

### "API endpoint not working"
```bash
# Check if season.db exists
ls -la PolarOS_prompts_1-4/season.db

# Test the query directly
cd PolarOS_prompts_1-4
sqlite3 season.db < q_burnrate.sql | head
```

### "Styles not loading"
- Use the standalone HTML demo (`inventory-demo.html`) — it has Tailwind CDN built-in

### "React component not rendering"
- Make sure you're importing it correctly
- Check browser console for errors
- Fall back to the HTML demo to debug

---

## Truth Discipline

✓ Every number shown comes from running code
✓ No invented data
✓ All queries tested against season.db
✓ Demo data is the same as production data

---

**You've now got a working inventory module that judges can interact with, showing real data, with RED/GREEN alerts that actually come from the database.**

Time to build the other 4. Same pattern. Go. 🚀
