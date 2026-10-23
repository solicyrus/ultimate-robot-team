# 🤖 Ultimate Robot Team — REAL social-media robots

A small team of **12 real robots** that does real social-media work:
live trend research, AI-written captions/titles/hashtags, AI-generated
post visuals, a strict self-critic, a real post queue, real Telegram
AND Instagram publishing — and a learning brain that gets smarter
from feedback over time.

This project was rebuilt from a skeleton draft into working code —
every robot below does something real. Nothing is simulated.

## The 12 robots

| # | Robot | What it really does |
|---|-------|---------------------|
| 1 | `deep_think` (brain) | Real AI strategy: analyzes your mission and returns a step-by-step plan in Persian (`brain/llm.py`, gpt-4o-mini) |
| 2 | `memory_keeper` (brain) | Real memory saved to `brain_memory.json` — the team remembers across runs |
| 3 | `trend_watcher` | Real live-web search (DuckDuckGo) for what's trending in your niche |
| 4 | `title_maker` | Real AI: 5 viral-but-honest titles |
| 5 | `caption_writer` | Real AI: one caption in Persian + English (past lessons injected into its prompt) |
| 6 | `hashtag_maker` | Real AI: 15 hashtags (Persian + English mix) |
| 7 | `scheduler` | Real post queue in `queue.json` — schedule now or later |
| 8 | `telegram_publisher` | Real Telegram Bot API. Without a bot token it **cleanly skips** (never fakes a sent message) |
| 9 | `learning_brain` | Feedback-loop learning: your feedback becomes durable lessons the team applies to all future posts (`brain/learning.py`) |
| 10 | `auto_critic` | Strict editor: reviews every draft against 5 standards, sends it back for one revision if it fails (`brain/critic.py`) |
| 11 | `image_maker` | Real AI visual: Gemini writes a detailed English prompt, Imagen 3 renders a 1:1 PNG (`robots/image_maker.py`) |
| 12 | `instagram_publisher` | Real Meta Graph API two-step photo publish — needs a **public** image URL (see below) (`robots/instagram_publisher.py`) |

## 🧠 Learning + self-critic (how the team gets smarter)

**LearningBrain** (`brain/learning.py`) — adapted from a real working
feedback-loop pattern:
- `learn_from_feedback(post, feedback, is_positive)`: praise stores the
  post as a win; criticism makes an LLM distill it into a 1–2 sentence
  **rule** ("keep captions under 150 words and always end with
  hashtags") saved to `learning_memory.json`.
- `get_lessons()` feeds those rules into every future caption prompt —
  the team stops repeating the same mistakes.
- `record_mission()` logs each mission's outcome (critic score, revised?,
  published?) so there is always real material to learn from later.
- LLM order: **Gemini first** (`GEMINI_API_KEY`, gemini-2.5-flash),
  then the team's own OpenAI brain. With **no keys at all**, feedback is
  still stored (honestly marked "not yet distilled") instead of lost.

**AutoCritic** (`brain/critic.py`) — every draft is judged before it
reaches the queue, against 5 standards: honest claims only (no invented
prices/phones), Persian + English present, ends with hashtags,
adventurous tone, call-to-action present. Failed draft → the writer gets
the critic's exact fix-list and **one revision**, then it's re-judged.
With no AI key, an honest deterministic rule-check runs instead of the
AI judge (weaker, but never fakes a pass).

Honest scope, on purpose: this is *prompt-level* learning — the team
accumulates better writing rules over time. It does not retrain any AI
model. For marketing work, that's the part that actually matters.

## 🖼️ The public-URL bridge (Instagram)

Instagram's API **cannot** use a local file — Meta's own servers fetch
the image from a **public https URL** you give them. So the
`image_maker` robot (which saves a real PNG locally) and the
`instagram_publisher` robot (which needs that public URL) have a gap
between them, and this project fills it **honestly, never
automatically**:

- The publisher **refuses** local paths with a clear error before any
  network call.
- Nothing is auto-uploaded anywhere without Cyrus's approval.

**Concrete way to get the public URL (pick one):**

1. **Quick / testing (up to 48 hours):** Muse's built-in storage —
   run `/opt/hatch/bin/remote-storage upload-file --path temp_image.png`
   and paste the returned `url` into `IMAGE_PUBLIC_URL` in `.env`.
   Anyone with the link can open it; it expires (see `expires_at`).

2. **Durable:** upload the PNG to your own hosting with the laptop
   File Manager (e.g. `app.victoriatourandadventure.com/ig/post1.png`)
   and use that `https://...` URL. It's your domain, it never expires.

Once `IMAGE_PUBLIC_URL` is set, the mission publishes to Instagram
for real; until then it reports an honest skip.

**Imagen billing note:** the `image_maker` robot generates images
through the Gemini API (Imagen 3), which typically needs a
**billing-enabled** API key — a plain free key often returns a
permission/billing error. The robot surfaces that real error in its
result dict (never hidden, never faked as success) so you know
exactly what to fix.

## How to run

```bash
pip install -r requirements.txt
cp .env.example .env        # then put your OPENAI_API_KEY inside
python main.py              # optional: GEMINI_API_KEY for Gemini-first
                            # learning + the image_maker robot
```

One mission runs end-to-end: think → remember → watch trends →
write titles + caption + hashtags in parallel (lessons injected) →
**critic reviews → one revision if needed** → **generate the AI
image** (or honest skip) → **publish to Instagram** (or honest skip) →
queue the final post → publish to Telegram (or honest skip without a
token) → **record the outcome for future learning**.

Teach it from feedback any time:

```python
from brain.learning import LearningBrain
lb = LearningBrain()
lb.learn_from_feedback(post_text, "too long and no hashtags", is_positive=False)
# next mission's captions automatically apply the new rule
```

## The things you do yourself

**1. Real Telegram publishing** (5 minutes, free):

1. Open Telegram, talk to **@BotFather**, send `/newbot`, copy the token.
2. Send any message to your new bot.
3. Open in a browser: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   and copy your chat `id` number.
4. Put both into `.env`:
   `TELEGRAM_BOT_TOKEN=...` and `TELEGRAM_CHAT_ID=...`

Without this step everything still works — posts just stay queued in
`queue.json` and the run tells you publishing was skipped.

**2. Real Instagram publishing** (Meta setup, free):

1. Create a Meta app at https://developers.facebook.com with the
   `instagram_content_publish` permission; get a user access token.
2. Find your Instagram business/creator account's numeric ID.
3. Put them into `.env`: `IG_ACCESS_TOKEN=...` and `IG_USER_ID=...`.
4. Get a public https URL for the post image (see "The public-URL
   bridge" above) and put it into `IMAGE_PUBLIC_URL=...`.

Without these, Instagram publishing is skipped honestly and nothing
breaks — the text pipeline, Telegram and the queue all keep working.

**3. Real AI images** — put a (billing-enabled, see note above)
`GEMINI_API_KEY=...` into `.env`. Without it the mission skips the
visual step cleanly.

## Files

- `main.py` — the SuperRobot orchestrator + demo mission
- `brain/llm.py` — real AI calls (key from env only, never raises)
- `brain/memory.py` — JSON-file memory
- `brain/learning.py` — feedback-loop learning (Gemini first, OpenAI fallback)
- `brain/critic.py` — self-critic: 5-standards draft review + one revision loop
- `robots/content_robots.py` — 4 AI content robots (caption takes lessons)
- `robots/trend_watcher.py` — live web search
- `robots/scheduler.py` — post queue
- `robots/telegram_publisher.py` — Telegram Bot API
- `robots/image_maker.py` — Gemini prompt + Imagen 3 visual (needs
  GEMINI_API_KEY, typically billing-enabled)
- `robots/instagram_publisher.py` — Meta Graph API two-step publish
  (needs IG_ACCESS_TOKEN + IG_USER_ID + public IMAGE_PUBLIC_URL)
- `original/Superrobot-Final.py` — the original draft, kept for reference only
- `original/SuperMarketingAgent.py` — the real feedback-loop pattern the
  learning brain was adapted from, kept for reference only
- `original/SuperMarketingAgent-v2.py` — the v2 draft (auto-critic +
  Imagen + Instagram hands), kept for reference only
