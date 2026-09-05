# PolarOS — 5-minute pitch script (StoryBrand opening)

**Spoken length: 669 words — 4 min 53 s at a deliberate pitch pace (~135 wpm),**
leaving room for the two pauses marked below. Do not speed up to fit more in — the pause on beat 1 is
doing real work.

**Every number here comes out of `season.db`.** Nothing is rounded for effect and
nothing is invented. If a judge asks where a figure comes from, the answer is
`season_stats.txt` or one of the three proof queries.

---

## How StoryBrand is applied — and where it deliberately stops

The opening (beats 1–3) and the close (beat 9) run the SB7 frame. Beats 4–8 do
not, on purpose. A jury that includes a distributed-systems academic will punish
marketing cadence applied to a technical claim; the frame is there to earn you
the room, and the evidence is there to keep it. **If you feel the story voice
creeping back in around the chart, you have lost the beat.**

| SB7 element | Where it lives | What it actually says |
|---|---|---|
| **A character** | Beat 1 | The Maitri station leader — not PolarOS. You are the guide, never the hero. |
| **…who wants something** | Beat 1 | *"Bring all seven of us home in November."* This is the line the old draft was missing, and it is the whole reason the fuel number lands. |
| **has a problem** — external | Beat 1 | Six weeks of diesel, four months to the ship. |
| — internal | Beat 2 | *"You are not frightened of the cold. You are frightened that you did not see this coming."* |
| — philosophical | Beat 2 | Nobody running a national programme should be deciding this off a spreadsheet that stopped updating in March. |
| **and meets a guide** — empathy | Beat 3 | *"We are not here to tell you to plan better — you did plan."* |
| — authority | Beats 4, 8 | 4,625 events, seeded and reproducible; and a frank list of what is not built. |
| **who gives them a plan** | Beat 3 | Log it · swap it · ask it. Three steps, said as three steps. |
| **and calls them to action** | Beat 9 | One real season of NCPOR records. Direct, specific, small enough to say yes to. |
| **that helps them avoid failure** | Beats 6, 2 | Finding out in August. Two days of margin even when you *do* see it coming. |
| **and ends in success** | Beats 5, 9 | The alert on 29 March. A Basler on the ice on 3 October. |

**The one thing not to get wrong.** The hero is the station leader, and behind
them NCPOR. PolarOS is Gandalf, not Frodo. Every time you are tempted to say
"our system does X", say "you would have known X" instead. That single swap is
most of StoryBrand.

**Delivery notes**

- Beats 1–3 are second person, present tense, unhurried. This is the only part of
  the talk that is a story.
- From beat 4, switch to plain declarative and stay there. The contrast between
  the two registers *is* the effect.
- The most important moment is the chart on beat 5. Say the four dates, then stop
  talking while they read it.
- Beat 8 is not padding. Volunteering what you have not built is what separates a
  team that has done the work from a team that has done a deck.

---

## BEAT 1 — The character, and what she wants  ·  0:00–0:45  ·  [CLICK to open]

> It is the fifteenth of August, 2027. You are the station leader at Maitri.
>
> Six people are here because you signed for them. Your job this winter is one
> sentence long — bring all seven of us home in November.
>
> This morning your storeman dipped the tanks. Six thousand two hundred and
> ninety-one litres. You burn a hundred and forty-seven a day. Six weeks.
>
> The ship comes on the fifteenth of December. Four months.

**[PAUSE — three full seconds. Let them do the subtraction.]**

---

## BEAT 2 — What is actually wrong  ·  0:45–1:20  ·  [CLICK]

> You are not frightened of the cold. You are frightened that you did not see this
> coming — which means you do not know what else you cannot see.
>
> Every one of those litres was counted. Written down. Filed. In five places — a
> manifest in Goa, a tally on the ship, a register in the store, a spreadsheet in
> Delhi — and no two have spoken since March.
>
> Nobody should be making a call like this on a spreadsheet seven months out of
> date.
>
> The data existed. The answer didn't.

---

## BEAT 3 — The guide, and the plan  ·  1:20–2:00  ·  [CLICK]

> We are PolarOS. We are not here to tell you to plan better — you did plan. We are
> here to change what you can see. Three steps.
>
> One. Log what happened, not what you think is true. One line per event,
> appended, never edited. Eighteen kinds of event; that is the whole vocabulary.
>
> Two. When a link opens, swap the lines you are missing. Nothing to reconcile,
> because nobody ever overwrote anything.
>
> Three. Ask the log — as of any date you name.

---

## BEAT 4 — What we built  ·  2:00–2:30  ·  [CLICK]

> We built a full expedition season and ran it. Four thousand six hundred and
> twenty-five events. Five nodes, four hundred crates, thirty-five people, nine
> months of winter.
>
> Then we planted your failure. Goa requisitioned at a hundred and thirty litres a
> day. Maitri burns a hundred and forty-five. And the load sailed fifteen percent
> short of even that.
>
> Two ordinary mistakes, compounding. That is how every fuel emergency happens.
> Never one.

---

## BEAT 5 — The forecast  ·  2:30–3:20  ·  [CLICK — the chart]

> Here is what you would have seen.
>
> On the twenty-ninth of March — the first day the trailing average had enough
> winter data to trust — one alert. Projected zero: twenty-sixth of October.
>
> Then watch it tighten. May, twenty-eighth of October. July, twenty-seventh of
> September. Mid-September, second of October.
>
> The tank would actually have run dry on the fifth of October.

**[Stop. Let them read the chart for two seconds.]**

> A hundred and ninety days of warning, from a forecast that got more accurate the
> longer it ran.

---

## BEAT 6 — Two days  ·  3:20–3:45  ·  [CLICK]

> And here is the part I want you to sit with.
>
> Even with a hundred and ninety days of warning, the relief flight landed on the
> third of October. Two days of margin.
>
> That is how thin this is. Which is why finding out in August is not a near miss.
> It is a disaster you have not had yet.

---

## BEAT 7 — The other story  ·  3:45–4:10  ·  [CLICK]

> Twenty-fifth of January. Two people leave Bharati for the ridge, due back at six.
> At half past six the log raises the alert and triggers the search-and-rescue
> procedure. They walk in six hours late — everyone fine.
>
> That whole event is three hundred and forty-five bytes. Under two seconds of
> satellite time. Safety never queues behind tinned fish, because priority is a
> column in our schema, not a promise in our slide.

---

## BEAT 8 — What we have not built  ·  4:10–4:35  ·  [CLICK]

> What we have not built, before you ask.
>
> The sync protocol itself — we have the schema and we have measured what it would
> send, but no two nodes have exchanged a delta yet. Conflict resolution is
> deterministic by construction, and untested against divergent replicas. Our
> consumption model is plausible, not sourced from NCPOR.
>
> Those are the next three things we build, in that order.

---

## BEAT 9 — The ask, and the close  ·  4:35–5:00  ·  [CLICK]

> So here is what we are asking for.
>
> Give us one real season of NCPOR's records, and we will show you every shortfall
> the programme is carrying right now — the way we just showed you this one.
>
> Antarctic logistics does not fail because someone made a mistake. It fails
> because the mistake stays invisible until the ice closes.
>
> PolarOS does not add a screen. It changes when you find out.
>
> Thank you.

---

## If they cut you off at three minutes

Drop beats 7 and 8 and go from beat 6 straight to the close. Never drop beat 8
*and* keep beat 7 — the honesty beat is worth more to a jury than the second
story. Never drop beat 1: without the want, every number that follows is just a
number.

## The four numbers you must not get wrong

| | |
|---|---|
| Events in the simulated season | **4,625** |
| Date the alert fired | **29 March 2027** |
| Days of warning | **190** |
| Margin when the flight landed | **2 days** |

## Likely questions, and the one-line answer

**"Couldn't a spreadsheet do this?"** Not across a broken link. A spreadsheet
stores the answer, so two copies edited apart have to be reconciled by a human.
We store the events, so two copies merge by set union with no human in the loop.

**"How do you know your forecast isn't just noise?"** Because it refuses to run
across a headcount change. The 28-day average is only computed once the whole
window sits inside the winter-over — otherwise it averages twenty-two people
against seven. That guard is why the season produced one alert and not two hundred.

**"Isn't your data made up?"** It is simulated, and the generator is seeded, so
anyone can reproduce it byte for byte. What is not made up is the arithmetic: the
same query run on the fifteenth of September genuinely cannot see the relief
flight that arrives on the third of October, because an append-only log cannot see
its own future.

**"What happens when two stations disagree?"** They cannot. Neither one ever
changed a value — they only added lines. Ordering is last-writer-wins on
timestamp then event id, which is deterministic, so both replicas compute the
identical answer. We have not stress-tested that against divergent replicas yet,
and that is the honest limit of the claim.

**"Is the station leader in your opening a real person?"** No, and say so plainly
if asked. She is a composite of a real role, standing in a real season we
simulated. Every figure she reads off the tank is out of the database. The person
is illustrative; the arithmetic is not.
