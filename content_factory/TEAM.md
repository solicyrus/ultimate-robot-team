# 🏭 The Content Factory — 20-Robot Super Team

A dedicated production line inside the Ultimate Robot Team whose ONLY job is
creating the best possible short-form content starring the Cyrus AI channel's
**AI host — the red-haired woman presenter** — built HOOK-first (تکنیک قلاب:
a scroll-stopping hook in the first 2 seconds) plus the other proven
short-form techniques: curiosity gap, pattern interrupt, series/ritual
formats, comment-bait questions, and trending formats.

**Iron rule: the factory only PREPARES and queues. Nothing is ever
published — Cyrus approves every piece in `approve.py` first.**

## 🔒 Locked posting cadence (Cyrus's decision, 2026-10-25)

- **1 strong content piece per day on EVERY platform** — YouTube Shorts,
  Instagram Reels, the WhatsApp channel, and Telegram.
- Quality over volume: every piece must pass the quality gate (≥ 8/10)
  before it can be queued at all.
- **YouTube may rise to 2/day only later** — after 2–3 weeks of good watch
  metrics — and only by flipping the `youtube_phase2` flag in
  `content_factory/scheduler.py` (OFF by default; nothing turns it on
  automatically).
- Strategy: build a **2-week content bank first**, then publish daily
  without gaps.

This cadence is encoded as constants in `scheduler.py`
(`DAILY_PER_PLATFORM = 1`, `CADENCE_TEXT`, `daily_volume()`) — the AI
chooses only the time of day, never the volume.

## The 20 robots

| # | Robot | File | Job |
|---|-------|------|-----|
| 1 | trend_scout | `trend_scout.py` | Finds trending travel / short-form angles |
| 2 | idea_generator | `idea_generator.py` | Content concepts starring the AI host |
| 3 | hook_master | `hook_master.py` | First-2-seconds hooks (the قلاب specialist) |
| 4 | scriptwriter | `scriptwriter.py` | 10–30s spoken scripts for the host |
| 5 | storyboarder | `storyboarder.py` | Shot-by-shot scene breakdowns |
| 6 | video_prompt_engineer | `video_prompt_engineer.py` | Ready-to-paste AI video prompts (host-consistent: red curly hair, warm smile, location wardrobe) |
| 7 | series_planner | `series_planner.py` | Recurring series formats (e.g. "One Minute Victoria") |
| 8 | title_writer | `title_writer.py` | YouTube / Reels titles |
| 9 | caption_writer | `caption_writer.py` | Post captions |
| 10 | hashtag_researcher | `hashtag_researcher.py` | Hashtag sets |
| 11 | cover_designer | `cover_designer.py` | Cover / first-frame text + frame-choice brief |
| 12 | editor | `editor.py` | Assembly brief: overlays, hook-text timing, logo, end card |
| 13 | music_picker | `music_picker.py` | Music / sound mood brief per piece |
| 14 | adapter | `adapter.py` | Per-platform versions (YouTube Shorts, Instagram Reels, WhatsApp, Telegram) |
| 15 | engagement_writer | `engagement_writer.py` | Pinned comment + reply starters + a question to spark comments |
| 16 | hook_critic | `hook_critic.py` | Scores hook strength 0–10 with reasons |
| 17 | fact_critic | `fact_critic.py` | Honesty check — only approved facts; flags any invented price / hour / place fact |
| 18 | quality_gatekeeper | `quality_gatekeeper.py` | Combines the scores; passes only ≥ 8/10, else sends back with fix notes |
| 19 | scheduler | `scheduler.py` | Best posting slot + the locked cadence (above) |
| 20 | librarian | `librarian.py` | Tracks produced concepts in `ledger.jsonl` — prevents repeats, records lessons |

Shared helpers live in `common.py` (the host's fixed identity, the
approved-facts block, the technique list, and the `ask_json` wrapper over
`brain/llm.py`).

**Approved facts — the only product facts any robot may state:** Cyrus AI
trip planning costs **CA$10 for 14 days** at victoriatourandadventure.com,
and the app **Cyrus AI Tour Guide** is on Google Play. No invented prices,
hours, phone numbers, or place facts — ever (robot 17 enforces this).

## The pipeline — `content_super_robot.py`

```
librarian (avoid-list + rejection lessons)
  → trend_scout → idea_generator → hook_master → scriptwriter
  → storyboarder → title_writer / caption_writer / hashtag_researcher /
    video_prompt_engineer / series_planner / cover_designer / editor /
    music_picker / adapter / engagement_writer / scheduler
  → hook_critic + fact_critic → quality_gatekeeper
      PASS (≥ 8/10, zero fact flags) → ApprovalQueue (awaiting approval)
      FAIL → hook_master gets ONE retry with the gate's fix notes
             → still failing: recorded in the ledger, NOTHING is queued
  → librarian records the outcome in ledger.jsonl either way
```

Each queued package carries: concept, hook, script, storyboard, title,
description/caption, hashtags, the critics' scores, the video-generation
prompt, cover + edit + music briefs, per-platform versions, the
engagement kit, the schedule suggestion, `ai_generated: true`, and the
channel cross-promotion from `brain/channels.py`.

## Run it

```bash
cd ~/workspace/ultimate-robot-team
./venv/bin/python -m content_factory.content_super_robot
./venv/bin/python -m content_factory.content_super_robot "Tofino storm watching"
```

Needs `OPENAI_API_KEY` in the environment (the team's standing source is
`~/workspace/factory/.env`). One run = one concept = at most one queued
package.

## How the factory fits the team's day

The team's existing daily entry points are unchanged: `robots/runner.py`
(`prepare` / `publish` / `status`) drives the daily prepare-and-publish
loop, and `main.py` is the original SuperRobot mission orchestrator. The
Content Factory is a standalone production line feeding the SAME
`approval_queue.json` — it is not wired into any cron, and no cron was
edited to add it.
