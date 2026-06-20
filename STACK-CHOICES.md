# AI Newsroom — Stack choices & alternatives

A decision guide for every tool/technology in the build. For each category: the top options, what each is best for, free vs paid, **integration effort** (a proxy for how many Cursor AI tokens/iterations it takes to wire up — Low = a few prompts, High = many), and my recommendation with reasoning.

*Pricing current as of June 2026; sources at the bottom. "Integration effort" assumes you're building in Cursor.*

---

## 1. LLM / reasoning (the agents' brain)

The model that powers Scout/Editor/Writer/Fact-checker.

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **Anthropic Claude** *(selected)* | Writing quality, instruction-following, summarization | Paid, pay-as-you-go. Haiku 4.5 **$1/$5** per Mtok (in/out), Sonnet 4.6 $3/$15, Opus 4.8 $5/$25. Batch −50%, caching −90% | Low — one SDK, clean API |
| **OpenAI (GPT)** | Largest ecosystem, lots of examples | Paid; similar tiering, small models cheap | Low |
| **Google Gemini** | Best free tier for prototyping | Generous free tier via AI Studio + paid | Low |
| **Open models** (Llama/DeepSeek via Groq/Together) | Lowest cost, no vendor lock-in | Some free tiers; very cheap paid | Medium — pick a host, less polished |

**Recommendation: Claude Haiku 4.5.** Summarizing and curating don't need a frontier model, and this runs daily — Haiku is the cost-discipline choice at $1/$5 per million tokens (a daily brief costs pennies). It's also on-brand for an AI-product portfolio, and the writing quality is strong where it matters (the Writer). Reserve Sonnet only if the Fact-checker needs more reasoning muscle. Cost is tiny at this volume, so I optimized for write quality + simplicity over chasing the absolute cheapest open model.

## 2. RSS parsing (the "known outlets" source)

Reading feeds into structured stories.

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **feedparser** *(selected)* | The default Python RSS/Atom parser | Free, open-source | Low — `pip install`, handles every feed format |
| **atoma** | Modern, typed alternative | Free, open-source | Low |
| **requests + lxml/BeautifulSoup** | Full control / scraping non-feed pages | Free | High — you handle every format edge case yourself |
| **Hosted feed API** (Feedbin, Superfeedr) | Managed, push updates | Paid | Medium — external account + webhooks |

**Recommendation: feedparser.** It's the boring, correct choice — 15+ years of handling the messy reality of real-world feeds (malformed XML, weird date formats) so you don't. Zero cost, near-zero integration effort. Rolling your own with lxml would burn time and Cursor tokens re-solving solved problems.

## 3. Search API (the Scout's "reporter" layer)

Lets the Scout *find* stories beyond known feeds. Optional but it's what makes the Scout genuinely agentic.

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **Tavily** *(recommended)* | Built for LLMs/agents — ranked, citation-ready results | Paid, ~$0.008/query; small free tier | Low — designed for exactly this |
| **Exa** | Semantic/neural search | Paid, ~$0.001/result (+ content add-ons) | Low–Medium |
| **Brave Search API** | General web, privacy-first | Paid, $5–9/1k requests (perpetual free tier retired Feb 2026) | Low |
| **NewsAPI** | News-specific headlines | Free dev tier (100 req/day, non-commercial, delayed); paid for real use | Low |

**Recommendation: start RSS-only, add Tavily when you build the Scout.** For the MVP, feeds alone produce a real brief. When you make the Scout a true agent, Tavily is purpose-built for LLM agents (returns clean, ranked, cited snippets instead of raw HTML), which means far less parsing code — the lowest integration effort for the agentic upgrade. Exa is great but its content add-ons get pricey; Brave lost its free tier; NewsAPI's free tier is too restrictive for production.

## 4. State storage (the evolving story objects)

Where the run keeps its working data.

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **SQLite** *(selected)* | One-file DB, queryable, keeps history | Free, built into Python (`sqlite3`) | Low |
| **JSON files** | Dead-simple, git-diffable | Free | Lowest — but no querying |
| **TinyDB** | Document-style on top of JSON | Free | Low |
| **Hosted Postgres** (Supabase/Neon) | Multi-user, scale, dashboards | Free tiers + paid | High — overkill here |

**Recommendation: SQLite.** It's zero-ops (a single file, no server, ships with Python) but gives you real queries and a natural archive of past briefs — useful if you later add a "browse previous editions" page to the portfolio. JSON is fine if you never want history; Postgres is over-engineering for a daily batch job and adds infra you'd have to explain away.

## 5. Text-to-speech (the voice — this *is* the product)

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **edge-tts** *(selected for MVP)* | Free, no key, decent neural voices | Free (unofficial Edge endpoint) | Low — `pip install`, no account |
| **ElevenLabs** | Best-in-class, podcast-grade voices | Paid, credit-based from $5/mo | Medium — key + credit management |
| **OpenAI TTS** | Good quality/price balance | Paid, $15 / 1M characters | Low |
| **Google Cloud TTS** | Most generous free tier | $4 / 1M chars + 4M free/month | Medium — GCP setup |

**Recommendation: ship on edge-tts, upgrade to ElevenLabs for the demo reel.** Since the entire bet is the commute audio experience, voice quality matters — but for a free, zero-friction MVP that proves the pipeline, edge-tts is genuinely good enough and needs no account. When you want a *showcase* clip for the portfolio/pitch, generate one episode on ElevenLabs (its voices are noticeably more human) so the sample a recruiter hears sounds premium. Best of both: free to run, premium where it's seen.

## 6. Email delivery

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **Resend** *(selected)* | Best developer experience, modern API | **3,000 emails/mo free (permanent)**, Pro $20/mo | Low — cleanest API |
| **Brevo** | Highest permanent free volume | 300/day free (permanent) | Low–Medium |
| **Postmark** | Best deliverability | 100/mo trial, then $15/10k | Low |
| **SendGrid** | Big incumbent | Free tier gone (May 2025); 60-day trial then $19.95/mo | Medium |
| **Amazon SES** | Cheapest at scale | Very cheap, 12-mo intro tier | High — AWS setup |

**Recommendation: Resend.** Best-in-class developer experience, a clean API (lowest integration effort), and a *permanent* 3,000/month free tier that comfortably covers a personal/demo newsletter. Postmark wins on deliverability but its free tier is trivial; SendGrid killed its free tier; SES is cheap but AWS setup is a tax you don't need here.

## 7. Audio hosting / podcast distribution

How the mp3 reaches the listener. This is the one "is it a real podcast?" decision.

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **Email the mp3** *(simplest MVP)* | Fastest path, no hosting | Free (via Resend) | Lowest |
| **Object storage + self-made RSS** (Cloudflare R2 / GitHub Releases) | A real subscribable feed, full control | Free / near-free | High — you generate the podcast RSS spec |
| **Podcast host** (Transistor, Buzzsprout) | Turnkey real podcast + analytics | Paid (~$19/mo) | Medium |
| **Spotify for Creators** | Free real podcast hosting | Free | Medium — manual-ish uploads |

**Recommendation: email the mp3 for the MVP; add a generated RSS feed on R2 only if you want it subscribable.** For a portfolio piece, an emailed audio brief fully demonstrates the product and costs nothing. A true podcast feed is more authentic to the pitch but is real infra (generating a spec-compliant podcast RSS, hosting, submitting to directories) — worth it only if "subscribable in Spotify" is a goal you'll actually show. Start simple; upgrade if it earns its keep.

## 8. Scheduling / hosting (what runs it daily)

| Option | Best for | Free / paid | Integration effort |
|---|---|---|---|
| **GitHub Actions** *(selected)* | Lives in your repo, zero server | Free (generous; unlimited for public repos) | Low — one YAML file |
| **Render Cron Jobs** | Simple managed cron | Free tier + paid | Low–Medium |
| **Railway** | Nice DX, always-on option | Usage-based, small free credit | Medium |
| **Cloud functions** (AWS Lambda / Cloud Run) | Scale, full control | Free tiers + paid | High — more setup |

**Recommendation: GitHub Actions.** Since your code already lives on GitHub (and it's linked to Cursor), a scheduled workflow is one YAML file, free, with secrets management and a manual "run now" button built in — nothing else to provision or explain. The others only make sense if you outgrow a daily batch job, which a portfolio piece won't.

## 9. Dev editor (where you build it)

You've chosen the editor path — here's the landscape.

| Option | Best for | Free / paid | Notes |
|---|---|---|---|
| **Cursor** *(your pick)* | Most polished AI editor, strong multi-file edits | $20/mo (free tier exists; heavy use needs credits) | VS Code-based — familiar, GitHub-linked |
| **Windsurf** | Beginners; unlimited free autocomplete | $20/mo Pro (free tier) | VS Code-based |
| **GitHub Copilot + VS Code** | GitHub-ecosystem value | Free 2k completions; Pro $10/mo (new signups paused Apr 2026) | Most mainstream |
| **Zed** | Speed; native (non-VS Code) | Free + $8/mo | Fast, lighter AI |

**Recommendation: Cursor — and you already landed here for the right reasons.** It's the strongest AI editor for multi-file work (it built a test component in fewer prompt rounds than Windsurf or Copilot in head-to-head tests), it's VS Code-based so the environment is familiar, and your GitHub is already linked. The $20/mo is justified for a real build; if you want to trial free first, Windsurf's free tier is the closest substitute.

---

## Deferred: the agent framework

The framework the newsroom runs on (CrewAI vs LangGraph vs Claude Agent SDK) is its own decision — we set the agentic layer aside on purpose. When you're ready, I'll give it the same treatment. Short version: **CrewAI** = fastest, reads like a newsroom; **LangGraph** = most control + best critique-loop handling + strongest engineering signal; **Claude Agent SDK** = lightest, on-brand with Claude.

## My recommended default stack (one line)

Claude Haiku · feedparser (+ Tavily later) · SQLite · edge-tts (ElevenLabs for the demo clip) · Resend · email-the-mp3 to start · GitHub Actions · Cursor.

---

### Sources
- [Anthropic API pricing 2026 (CloudZero)](https://www.cloudzero.com/blog/claude-api-pricing/) · [MetaCTO breakdown](https://www.metacto.com/blogs/anthropic-api-pricing-a-full-breakdown-of-costs-and-integration)
- [TTS API comparison 2026 (TokenMix)](https://tokenmix.ai/blog/tts-api-comparison) · [AssemblyAI: top TTS APIs](https://www.assemblyai.com/blog/top-text-to-speech-apis)
- [Search API pricing compared 2026](https://awesomeagents.ai/pricing/search-api-pricing/) · [Best web search APIs for AI (Brave)](https://brave.com/learn/best-search-api-2026/)
- [Email service pricing: Resend/SendGrid/Postmark](https://www.buildmvpfast.com/api-costs/email) · [Transactional email compared (Mailtrap)](https://mailtrap.io/blog/transactional-email-services/)
- [Best AI code editors 2026 (NxCode)](https://www.nxcode.io/resources/news/best-ai-code-editor-2026-cursor-windsurf-copilot-zed-compared)
