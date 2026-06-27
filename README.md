# AI Newsroom

A small team of AI agents that writes and narrates a daily AI news podcast on its own. It scouts the day's stories, fact-checks its own drafts, narrates an episode and emails it. It runs free, on a schedule, with no server to manage.

Live podcast: it auto-publishes to my portfolio every day at [guptaishika25.github.io](https://guptaishika25.github.io).

---

## What this is, in plain words

Most "AI" projects are one prompt sent to one model. This is not that.

AI Newsroom is an **agentic AI system**, which means the work is split across several specialized agents that each do one job, hand work to each other, and check each other before anything ships. Think of a real newsroom. A scout finds stories, an editor decides what runs, a writer drafts it, a fact-checker pushes back, and a producer turns the final script into audio. Here, each of those roles is its own AI agent, and an orchestrator runs the handoffs.

The point of the design is trust. A single model asked to "summarize the news" will sometimes make things up or read a refusal out loud. By giving the fact-checker the power to reject the writer's draft and send it back for a second pass, the system catches most of those problems before they reach your inbox.

---

## How it works

Six agents, built on the **Claude Agent SDK**, with **Claude Haiku** as the reasoning model to keep the daily cost near zero.

| Agent | What it does |
|---|---|
| **Scout** | Pulls candidate stories from RSS feeds and decides what is relevant for today. |
| **Editor** | Ranks the stories, removes duplicates and sets the lineup in priority order. |
| **Writer** | Drafts each summary and the episode intro in a consistent voice. |
| **Fact-checker** | Checks every draft against its source. It can reject the writer's work and demand a rewrite. This is the loop that makes the output safe to send. |
| **Producer** | Turns the approved script into a narrated audio episode using Gemini text to speech. |
| **Orchestrator** | Runs the whole pipeline and coordinates every handoff and revision. |

The flow:

```
Scout  ->  Editor  ->  Writer  ->  Fact-checker  ->  Producer  ->  Podcast + email
                          ^              |
                          |   reject and revise
                          +--------------+

         Orchestrator coordinates every handoff
```

A draft that fails fact-checking twice is dropped instead of shipped, and if the lead story does not survive, the producer promotes the next strongest story so the episode never aborts. The result every morning is a real artifact: a short narrated episode plus an email brief.

---

## The stack

| Piece | Tool | Why |
|---|---|---|
| Agents | Claude Agent SDK | Runs the six agents and the critique loop. |
| Reasoning model | Claude Haiku | Fast and cheap enough for a daily run. |
| Story sourcing | feedparser (RSS) | Free, no API needed. |
| Memory | SQLite | Remembers what already ran so stories do not repeat. |
| Narration | Gemini text to speech (Zephyr voice) | Free and works from the cloud. |
| Email | Resend | Sends the brief, free tier is plenty. |
| Schedule | GitHub Actions (cron) | Runs every day, no server. |

---

## What it costs: $0 a day

The agents run on the **Claude Agent SDK credit included with a Claude Pro plan**, so there is no paid API bill. Narration uses Gemini's free tier, email uses Resend's free tier, and scheduling runs on GitHub Actions' free minutes. Sourcing is plain RSS. Nothing here requires a paid account.

---

## Run it yourself

You need Python 3.11 or newer, a Claude Pro plan, a free Resend account and a free Google AI Studio key for Gemini text to speech.

**1. Install**

```bash
git clone https://github.com/GuptaIshika25/ai-newsroom.git
cd ai-newsroom
pip install -r requirements.txt
```

**2. Sign in to Claude (one time)**

The Agent SDK uses your Claude Pro login, not a paid API key.

```bash
claude login
```

**3. Add your other keys**

Copy `.env.example` to `.env` and paste in your Resend and Gemini keys.

```bash
cp .env.example .env
```

**4. Run a day**

```bash
python -m src.main
```

This scouts, drafts, fact-checks, narrates and emails a single episode. Generated files land in the output folder.

---

## Deploy the daily schedule (free)

1. Push the repo to your own GitHub account.
2. Create a token for CI so GitHub can sign in to Claude on your behalf:

   ```bash
   claude setup-token
   ```

3. In your repo, go to **Settings -> Secrets and variables -> Actions** and add these secrets:
   - `CLAUDE_CODE_OAUTH_TOKEN` (from the command above)
   - `RESEND_API_KEY`
   - `GEMINI_API_KEY`
4. The workflow in `.github/workflows/daily.yml` runs every morning at 11:00 UTC. You can also trigger it any time from the **Actions** tab with **Run workflow**.

---

## Configure

Everything tunable lives in `config.yaml`:

- `feeds`: add or remove RSS sources.
- `relevance_keywords`: tune what counts as on-topic.
- `format.audio_stories`: how many stories make the audio and email (default 5, one lead plus four shorter items).
- `max_per_source`: cap stories from any single outlet so one site cannot flood the brief.

---

## How the code is organized

```
src/
  agents/        the six roles (scout, editor, writer, fact-checker, producer)
  tools/         feeds, fact-check, narration and a validation guard
  orchestrator   wires the agents together and runs the critique loop
config.yaml      feeds, keywords and format settings
.github/workflows/daily.yml   the daily cron job
```

The validation guard is worth a note. It catches the case where a model returns a refusal or a meta comment ("I could not access the article") instead of real narration, and drops it before it can be read aloud.

---

## The honest part

The agents were the easy part. They worked early. Every real fight was in the glue around the model: a free voice that worked on my laptop but got blocked from the cloud, a run that reported success while silently sending nothing, an audio file that came out as the wrong format. The full write-up of what broke and the product thinking behind the project is here:

[Read the case study](https://guptaishika25.github.io/newsroom.html)

---

Built solo by **Ishika Gupta**.
[Portfolio](https://guptaishika25.github.io) · [LinkedIn](https://www.linkedin.com/in/ishika-gupta/) · [GitHub](https://github.com/GuptaIshika25)
