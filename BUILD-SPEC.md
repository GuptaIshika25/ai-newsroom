# AI Newsroom — Build Spec

The blueprint for building the agentic version. Drop this in the repo root, open **Claude Code**, and build section by section following the **Build Order (§10)**. Each step says what to build and how to verify it before moving on — don't build everything at once.

> Claude Code knows the current Claude Agent SDK API. This spec defines *what* each agent does, its contract, and its prompt — let Claude Code handle the exact SDK calls.

---

## 1. Overview & goal

A daily, self-running "AI newsroom": a team of agents that **scout, curate, write, fact-check, and narrate** a short AI-news podcast, delivered each morning as an mp3 + a text version by email.

- **Trigger:** GitHub Actions cron, every morning.
- **Output:** one mp3 (lead story + snippets, narrated in the "Ava" voice) and an HTML/text digest, emailed to the subscriber list.
- **Runtime cost:** pennies/day (Claude Haiku + free edge-tts + Resend free tier).

## 2. Tech stack (locked)

| Layer | Choice |
|---|---|
| Agent framework | **Claude Agent SDK** (Python) |
| Reasoning model | **Claude Haiku 4.5** (`claude-haiku-4-5-20251001`) |
| Sourcing | `feedparser` (RSS); optional Tavily later for the Scout |
| State | **SQLite** (`sqlite3`, stdlib) |
| TTS | **edge-tts**, voice "Ava" |
| Email | **Resend** |
| Schedule | **GitHub Actions** cron |
| Build tool | Claude Code (edit/review in Cursor) |

## 3. Repo structure

```
ai-newsroom/
  BUILD-SPEC.md            # this file
  README.md                # build-it-yourself guide (separate doc)
  requirements.txt
  config.yaml              # feeds, voice, format counts, model
  .env.example             # ANTHROPIC_API_KEY, RESEND_API_KEY
  .gitignore
  src/
    agents/
      scout.py             # find candidate stories
      editor.py            # rank, dedupe, pick lead + snippets
      writer.py            # draft lead segment + snippets
      factchecker.py       # verify vs source, approve/reject
      producer.py          # assemble script -> audio
    tools/
      feeds.py             # feedparser wrapper (RSS)
      search.py            # optional Tavily wrapper (stub for now)
      tts.py               # edge-tts (Ava) -> mp3
      mailer.py            # Resend send
    state.py               # SQLite store + the Story model
    orchestrator.py        # wires the agents + critique loop
    main.py                # entrypoint: python -m src.main [--dry-run]
  .github/workflows/
    daily.yml
  output/                  # generated mp3 + digest (gitignored)
  tests/
```

## 4. Data model

One **Story** object, advanced through a lifecycle by the agents. Persist in SQLite so a run is inspectable and idempotent.

**Story fields:**
`id` (sha1 of url, 12 chars) · `run_date` · `source` · `title` · `url` · `published` · `raw_summary` · `score` (int relevance) · `role` (`lead` | `snippet` | `dropped`) · `draft` (narration text) · `verified` (bool) · `verify_notes` · `revisions` (int) · `status` (`candidate` → `ranked` → `drafted` → `verified` → `produced`).

**SQLite schema (one table):**
```sql
CREATE TABLE stories (
  id TEXT, run_date TEXT, source TEXT, title TEXT, url TEXT,
  published TEXT, raw_summary TEXT, score INTEGER,
  role TEXT, draft TEXT, verified INTEGER DEFAULT 0,
  verify_notes TEXT, revisions INTEGER DEFAULT 0,
  status TEXT DEFAULT 'candidate',
  PRIMARY KEY (id, run_date)
);
```

## 5. The agents

Each is a Claude Agent SDK agent with a single responsibility, a typed input/output contract, and the tools it may call. Starter system prompts below — tune later.

### Scout
- **Owns:** "is this plausibly relevant AI news?"
- **In:** today's date + feed list. **Out:** list of candidate Stories (`status=candidate`).
- **Tools:** `feeds.fetch` (RSS). (Later: `search.query` via Tavily.)
- **Prompt:** *"You are the Scout for a daily AI-news brief. From the fetched items, keep only those genuinely about AI — model launches, research, policy/regulation, funding, layoffs, notable product moves. Drop off-topic, ads, and duplicates. Return each kept item's title, url, source, and a one-line why-relevant."*

### Editor
- **Owns:** "what's worth the listener's time, and what's the single biggest story?"
- **In:** candidate Stories. **Out:** exactly **one** `role=lead` + **10–15** `role=snippet` (rest `dropped`); `status=ranked`.
- **Tools:** none (pure judgment).
- **Prompt:** *"You are the Editor. Pick the ONE most significant story of the day as the lead — biggest impact on people building with AI. Then select 10–15 more as snippets, ordered by importance. Dedupe near-identical stories. Flex the count with the day's news quality. Output the lead id and the ordered snippet ids."*

### Writer
- **Owns:** voice and concision. Runs in **two modes**.
- **In:** the lead + snippets. **Out:** `draft` text per Story; `status=drafted`.
- **Tools:** none.
- **Lead mode prompt:** *"Write a 3–5 minute spoken segment (~450–750 words) on this lead story: what happened, the context a busy professional lacks, why it matters, and the implication. Conversational, sharp, no hype, no bullet points — it will be read aloud."*
- **Snippet mode prompt:** *"Write a ~1-minute spoken snippet (~120–150 words): the headline, the gist, and why a busy professional should care. One tight paragraph, read-aloud friendly."*

### Fact-checker
- **Owns:** "is every claim supported by the source?" The quality gate.
- **In:** a draft + its source (`raw_summary`/url). **Out:** `approved` OR `rejected + reasons`; sets `verified`, `verify_notes`.
- **Tools:** none (compares draft against the provided source text). (Later: `search.query` to corroborate.)
- **Prompt:** *"You are the Fact-checker. Compare the draft to its source. Flag any claim, number, name, or date not supported by the source, and anything that overstates. If all claims are supported, reply APPROVED. Otherwise reply REJECTED with a short list of fixes."*

### Producer
- **Owns:** turning approved drafts into the final audio. Mostly deterministic.
- **In:** approved lead + snippets. **Out:** assembled script → mp3; `status=produced`.
- **Tools:** `tts.synthesize` (edge-tts, Ava).
- **Logic:** assemble in order — intro line → lead segment → snippets → outro — then synthesize one mp3. (Assembly is code; no LLM needed.)

### Orchestrator
- Coordinates the run and owns the **critique loop** and failure handling. See §6.

## 6. Orchestration & control flow

Sequential stages, one cycle:

```
Scout → Editor → (for each story: Writer → Fact-checker)        ← critique loop
      → Producer → mailer.send
```

**Critique loop (Writer ↔ Fact-checker):**
- After Writer drafts a story, Fact-checker reviews it.
- On `REJECTED`: send it back to Writer with the reasons; increment `revisions`.
- **Hard cap:** `MAX_REVISIONS = 2`. On exceeding it, **drop that story** (`role=dropped`) rather than block the run — graceful degradation. If the *lead* is dropped, promote the top snippet to lead.

**Failure handling:**
- A dead feed → Scout proceeds with the rest (best-effort).
- Malformed agent output → validate against the contract, one retry, then skip the story.
- Whole run is idempotent and re-runnable from SQLite state.

## 7. Podcast format spec (v1 — keep configurable)

- **Lead:** 3–5 min, ~450–750 words. Deep but tight (AI-Daily-Brief style, shorter).
- **Snippets:** 10–15 items, ~1 min / ~120–150 words each. Count flexes with the day.
- **Assembly order:** short intro ("Good morning, this is AI Newsroom for [date]…") → lead → snippets → short outro.
- **Target runtime:** ~13–18 min. Narration pace ~150 wpm (use this to hit word counts).
- One combined mp3 per day.

## 8. Config (`config.yaml`)

```yaml
newsletter:
  name: "AI Newsroom"
  model: "claude-haiku-4-5-20251001"
  lookback_hours: 28
format:
  lead_count: 1
  snippet_min: 10
  snippet_max: 15
  lead_words: [450, 750]
  snippet_words: [120, 150]
audio:
  voice: "en-US-AvaMultilingualNeural"   # "Ava" — confirm exact id via: edge-tts --list-voices
  rate: "+0%"
email:
  from_address: "AI Newsroom <onboarding@resend.dev>"
  to_addresses: ["guptais6@msu.edu"]
feeds:
  - { name: "TechCrunch AI", url: "https://techcrunch.com/category/artificial-intelligence/feed/" }
  - { name: "The Verge AI", url: "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml" }
  - { name: "VentureBeat AI", url: "https://venturebeat.com/category/ai/feed/" }
  - { name: "MIT Tech Review", url: "https://www.technologyreview.com/feed/" }
  - { name: "OpenAI", url: "https://openai.com/news/rss.xml" }
  - { name: "Google DeepMind", url: "https://deepmind.google/blog/rss.xml" }
  - { name: "Hugging Face", url: "https://huggingface.co/blog/feed.xml" }
relevance_keywords: [ai, llm, gpt, claude, gemini, openai, anthropic, model, agent, regulation, funding, layoff, benchmark, chip, open source]
```

## 9. Deterministic components

- `tools/feeds.py` — feedparser wrapper: fetch each feed, parse title/url/summary/date, filter to `lookback_hours`, keyword-score. (Reuse logic from the existing pipeline `fetch.py`.)
- `state.py` — SQLite open/migrate, upsert Story, query by run_date/role/status.
- `tools/tts.py` — edge-tts with the Ava voice → mp3 (async; reuse the pipeline `audio.py`).
- `tools/mailer.py` — Resend: send html + text, attach the mp3.
- `.github/workflows/daily.yml` — cron + `workflow_dispatch`; secrets `ANTHROPIC_API_KEY`, `RESEND_API_KEY`; runs `python -m src.main`.

## 10. Build order (do these in sequence, verify each)

1. **Scaffold** — repo structure, `config.yaml`, `.env.example`, `requirements.txt`, `state.py` + SQLite schema. *Verify:* DB creates, a Story round-trips.
2. **Scout** — `feeds.py` + scout agent. *Verify (dry-run):* prints N candidate stories from live feeds.
3. **Editor** — pick lead + snippets. *Verify:* exactly 1 lead + 10–15 snippets, deduped.
4. **Writer** — both modes. *Verify:* lead draft hits word range; snippets ~120–150 words.
5. **Fact-checker + critique loop** — approve/reject with `MAX_REVISIONS=2` and drop-on-fail. *Verify:* a deliberately wrong draft gets rejected and revised or dropped.
6. **Producer** — assemble script + edge-tts (Ava). *Verify:* a real mp3 plays, correct order, Ava voice.
7. **Email** — Resend send with mp3 attached. *Verify:* email arrives with audio.
8. **Orchestrator end-to-end** — full run + `--dry-run`. *Verify:* one command produces mp3 + digest.
9. **Schedule** — `daily.yml`. *Verify:* manual "Run workflow" succeeds; secrets set.

## 11. Run & test

```bash
pip install -r requirements.txt
cp .env.example .env        # add ANTHROPIC_API_KEY + RESEND_API_KEY
python -m src.main --dry-run   # stubs LLM + skips send; writes output/
python -m src.main             # real run
```
`--dry-run` should require no keys: stub agent outputs, skip email, still write a sample script/mp3 where possible.

## 12. Definition of done

- [ ] One command produces a dated mp3 (Ava voice: lead + 10–15 snippets) and a text digest.
- [ ] Fact-checker rejects unsupported claims; loop is bounded and degrades gracefully.
- [ ] Email arrives with the mp3 attached.
- [ ] GitHub Actions runs it on schedule and on manual trigger.
- [ ] `--dry-run` works with no API keys.
