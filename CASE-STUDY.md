# AI Newsroom

**An agentic worksystem that produces a daily AI-news podcast for busy professionals — built from a customer need to a working MVP.**

A product case study by Ishika Gupta · [LinkedIn] · [GitHub] · [Live demo]

---

## TL;DR

AI moves faster than anyone can keep up with, and the people who most need to stay current have the least time to read. **AI Newsroom** is a team of AI agents that scout, curate, fact-check, and narrate a short daily AI brief — designed to be listened to on the commute, the one open slot in a busy professional's day.

I took this from a customer need to a working build: I framed the user and the job, mapped a crowded competitive field (including a Spotify feature that shipped the generic version of this idea in May 2026), named the single assumption most likely to kill it, designed a concierge test for that assumption, and built the system as a coordinated multi-agent "newsroom" rather than a one-shot script.

This document is the thinking. The [build-it-yourself guide](./README.md) is how you can run your own.

---

## The problem

AI moves faster than anyone can keep up with. A new model, a policy shift, another lab shipping something — every single day. Most professionals know exactly one thing about AI: that it's moving fast, and that they're behind.

The problem isn't *access* to news. It's time. Eight to ten hours of work, then home to family, kids, or the one hobby you protect. There's no slot left to read another newsletter — and the dozen AI newsletters already in the inbox are part of the overload, not the cure.

So the real question isn't "how do we summarize AI news?" It's: **when does a busy professional actually have room to absorb anything, and what fits in that window?**

## The insight: design around a context, not a topic

There's one slot left in the day that nobody is using productively. The average US commute is **27 minutes each way** ([Census ACS, 2024](https://www.census.gov/)). You can't read on the drive — but you can listen.

That single constraint — *eyes busy, hands busy, ~25 minutes, already in the habit of listening to something* — shapes the entire product. It tells you the format (audio), the length (short enough to leave room for music), the tone (conversational, not a wall of bullet points), and the moment of use (morning, before work). Designing from the **context of use** rather than the topic is what turns "another AI summarizer" into a product with a shape.

The pitch, in one line: *AI Newsroom turns half your commute into a brief on what actually happened in AI — so you walk into the day sounding like you read everything. The other half, you go back to your music.*

## The competitive landscape

A daily AI brief is a crowded, mature category. Being honest about that is part of the work — it kills the lazy version of the idea and forces a sharper one.

- **TLDR.tech** runs a family of byte-sized daily newsletters, including a dedicated AI edition, monetized through advertising. Text, breadth, skim-optimized.
- **The AI Daily Brief** is an established daily AI-news *podcast* (host Nathaniel Whittemore, ~10–25 min). But it's one host picking a theme and going deep — a headline survey plus his analysis and opinion — not a fast, comprehensive recap of *everything* that happened. So "AI news you listen to" exists, yet the "catch me up on the whole day in a few minutes" job is still wide open.
- **Spotify Studio** (launched May 2026) generates *personalized* daily audio briefings from a prompt, pulls live news, can tap your calendar and inbox, and syncs to your phone for the commute. That is the generic version of this exact idea, shipped by a platform with distribution no independent product can match.

The takeaway isn't "give up." It's the core product lesson: **once a platform commoditizes the generic version of a feature, you don't win on the generic version.** You win where a general tool structurally won't go — depth and trust inside a narrow segment, a distinct editorial point of view, or a workflow a horizontal tool ignores. A focused AI Newsroom competes by going *narrower and deeper* than a one-size-fits-all briefing generator ever will.

## Framing the bet

For this project I deliberately scoped to a **portfolio MVP, not a launch** — the goal is to demonstrate end-to-end product judgment and the ability to ship, not to win a market against Spotify. That framing changes what "good" means: the competitive landscape above isn't an obstacle to overcome, it's evidence that I understand the market I'd be entering.

The target user, stated narrowly: a **busy knowledge worker who commutes, already listens to podcasts, and feels behind on AI but has no reading time.** The job they're hiring AI Newsroom for: *keep me current enough to sound sharp in the room, without spending time I don't have.*

## The riskiest assumption — and how I'd test it

Every product rests on assumptions. The discipline is to find the one that is both **most uncertain** (no evidence either way) and **most fatal** (if it's false, nothing else matters), and aim your cheapest test there.

The assumption stack: the pain is real; the commute is a "stay-informed" moment; people will substitute our brief for what they listen to now; audio is the format they want for news; daily and personalized is the right shape; the content is trustworthy; the voice is pleasant for 25+ minutes.

The riskiest one:

> **Busy professionals will actually choose to spend their commute listening to a daily AI brief — substituting it for what they listen to today.**

Here's the uncomfortable insight behind it: for many people the commute is the one slice of the day that's *theirs* — decompression time, music, a fun podcast, deliberately *not* work. If that's true, a productivity-flavored AI brief loses to a comedy podcast every morning, no matter how good the summaries are. The entire product rests on the commute being a "stay sharp" window rather than a "leave me alone" window — and there is zero evidence for that yet.

**How I'd test it — cheaply, before building more:** a concierge MVP. Manually produce a real ~12-minute audio brief every weekday for two weeks and send it to ~20 recruited target users via a private feed. Then watch *revealed behavior*, not opinions:

- Do they actually listen, and how far through?
- Do they come back on multiple days without nagging?
- Do they notice or ask when it's late?
- The "very disappointed" test: at the end, what share would be *very disappointed* if it disappeared?

**Success and kill lines, set before the test starts** (so the goalposts can't move): *Success = at least 8 of 20 listening 3+ mornings a week by week two, and ≥40% "very disappointed" if it went away. Kill/pivot signal = enthusiastic signups followed by silence after day two* — which would mean the pain is real but not commute-shaped.

That last failure mode is the whole point: the test is designed to tell me I'm wrong as fast and as cheaply as possible.

## The solution, and why it's genuinely agentic

The naive build is a script: pull RSS, make one LLM call, send an email. That works, but it isn't a *worksystem* — and it can't make editorial judgments or catch its own mistakes.

AI Newsroom is instead modeled on a real newsroom: a team of specialized agents that use tools, make decisions, and hand off to each other.

- **Scout** — searches and pulls candidate stories across sources; decides what's potentially relevant.
- **Editor** — ranks, dedupes, and judges newsworthiness to set the day's lineup.
- **Writer** — drafts each TLDR and the intro in the brief's voice.
- **Fact-checker** — checks each draft against its source and flags unsupported or hallucinated claims, sending weak ones *back* to the Writer.
- **Producer** — turns the approved script into narrated audio.
- **Orchestrator** — coordinates the hand-offs and the revision loop.

What makes this *legitimately* agentic, not a pipeline wearing the label: the agents make decisions (the Editor judges what's worth including), they use tools (the Scout searches), and there's a **critique-and-revise loop** (the Fact-checker can reject the Writer's work and demand a second pass). That loop is the difference between automation and a worksystem — and it directly attacks the trust problem that sinks most auto-generated news.

## What I built

A working MVP of the newsroom: the end-to-end flow runs from source ingestion through summarization, rendering, and audio narration, and produces a real daily artifact — a formatted brief plus a narrated audio version. The system is built to run itself on a schedule, for free, with no server.

**Stack:** Python · Anthropic Claude (the agents' reasoning) · feedparser (sourcing) · edge-tts (no-key narration) · Resend (delivery) · GitHub Actions (free daily scheduling).

See the [build-it-yourself guide](./README.md) for the architecture, setup, and how to run your own — and the `/output` folder for a sample brief.

## Decisions and tradeoffs

- **Audio-first, not text-first** — the entire bet is the commute context. Text would have been easier and is what every incumbent already does well.
- **Short over comprehensive** — the brief is deliberately kept tight to leave room for music. The constraint *is* the product; padding to fill time would break it.
- **A multi-agent newsroom over a single LLM call** — more to build, but it's the only honest way to claim "agentic," and the critique loop materially improves trust in the output.
- **A fast, cheap model over a frontier one** — summarization and curation don't need the largest model; the cost discipline matters for something that runs every day.
- **Portfolio MVP over a launch** — scoped to demonstrate judgment and shipping, not to fight Spotify for distribution.

## What I learned, and what's next

The sharpest lesson was about *where* to be brave. The brave move in a crowded market isn't a flashier feature — it's narrowing hard enough that a horizontal tool can't follow, and being willing to let a cheap test kill the idea before I over-invest.

**Next steps if I carried this forward:**
1. Actually run the two-week concierge test and report what the revealed behavior says.
2. If it survives, pick one vertical (e.g., AI for a specific profession) and go deep enough that trust and context become the moat.
3. Add lightweight personalization to the Editor agent so the lineup reflects the listener's role.
4. Once it's live, **A/B test** the variables that drive listening — brief length, narration voice, and morning send time — to optimize completion rate and return listening. (A concierge test answers *"does anyone want this?"*; an A/B test answers *"which version works better?"* — different tools, different stages.)

---

*Want to build your own? Start with the [guide](./README.md).*
