# AI TLDR — your 5-minute AI morning brief

An automated daily newsletter that scans the AI news cycle overnight, summarizes
what actually matters with Claude, and delivers it to your inbox as a clean HTML
email **plus a podcast-style audio version** — so you can read it over coffee or
listen on your commute. Built to run itself, for free, on a schedule.

> Built as a portfolio project to demonstrate end-to-end AI product building:
> sourcing, LLM summarization, multi-format delivery, and zero-ops scheduling.

## What it does

1. **Fetches** the last ~24h of stories from reputable AI feeds (TechCrunch,
   The Verge, VentureBeat, MIT Tech Review, OpenAI, DeepMind, Hugging Face…).
2. **Ranks** them for AI relevance — launches, model releases, policy, funding,
   layoffs, benchmarks — and keeps the top stories.
3. **Summarizes** each into a one-or-two-sentence TLDR with Claude, plus a short
   editor's intro tying the day together.
4. **Renders** a responsive HTML email, a plain-text version, and an audio script.
5. **Narrates** the brief to an MP3 (free, no API key, via edge-tts).
6. **Sends** the email with the audio attached, via Resend.
7. **Runs daily** on GitHub Actions — no server, no cost.

## Architecture

```
config.yaml ──▶ src/main.py ──▶ fetch.py     (RSS → ranked stories)
                              ├▶ summarize.py (Claude → TLDRs + intro)
                              ├▶ render.py    (HTML / text / audio script)
                              ├▶ audio.py     (edge-tts → MP3)
                              └▶ email_send.py(Resend → inbox)
.github/workflows/daily.yml   (cron: runs the whole thing every morning)
```

## What you need to sign up for

Two free accounts. That's it.

| Service | Why | Cost | Where |
|---|---|---|---|
| **Anthropic API** | Powers the summaries (Claude) | Pay-as-you-go; ~$0.01–0.05/day on Haiku | console.anthropic.com → API Keys |
| **Resend** | Sends the email | Free: 100 emails/day, 3k/month | resend.com → API Keys |

Audio (edge-tts) needs **no account or key**. To send *from your own domain*
instead of the shared `onboarding@resend.dev` sender, verify a domain in Resend
(optional) and update `from_address` in `config.yaml`.

## Run it locally

```bash
pip install -r requirements.txt
cp .env.example .env          # then paste your two keys into .env

# 1) Dry run — no keys needed. Stubs summaries, skips email, writes output/.
python src/main.py --dry-run

# 2) Real run — fetches, summarizes with Claude, builds audio, sends the email.
set -a && source .env && set +a
python src/main.py
```

Generated files land in `output/`: the HTML digest, plain text, audio script,
and the MP3.

## Deploy the daily schedule (free)

1. Push this folder to a new GitHub repo.
2. Repo → **Settings → Secrets and variables → Actions** → add two secrets:
   `ANTHROPIC_API_KEY` and `RESEND_API_KEY`.
3. The workflow in `.github/workflows/daily.yml` runs every morning at 11:00 UTC
   (7 AM ET — edit the cron to your timezone). Trigger it manually any time from
   the **Actions** tab → *Daily AI TLDR* → *Run workflow*.

## Customize

Everything lives in `config.yaml`: add/remove feeds, tune `relevance_keywords`,
change `max_stories`, swap the audio `voice` (run `edge-tts --list-voices`), or
edit recipients. Switch the Claude model via the `ANTHROPIC_MODEL` env var.

## Tech

Python · feedparser · Anthropic Claude · edge-tts · Resend · GitHub Actions
