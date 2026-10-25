"""ULTIMATE ROBOT TEAM — content_factory/content_super_robot.py

The Content Factory's SUPER ROBOT: orchestrates all 20 factory
robots into one production line and enqueues ONE finished package
per concept — only if it passes the quality gate.

Pipeline:
    librarian (avoid-list + rejection lessons)
      -> trend_scout -> idea_generator -> hook_master -> scriptwriter
      -> storyboarder -> title_writer / caption_writer /
         hashtag_researcher / video_prompt_engineer / series_planner /
         cover_designer / editor / music_picker / adapter /
         engagement_writer / scheduler
      -> hook_critic + fact_critic -> quality_gatekeeper
         (PASS only at >= 8/10 with zero fact flags; on a fail the
          hook master gets ONE retry with the gate's fix notes)
      -> ApprovalQueue (robots/runner.py — the team's shared queue)
      -> librarian records the outcome in ledger.jsonl either way.

IRON RULE: this robot only PREPARES and queues. It never publishes,
never sends anything anywhere. A human approves in approve.py first.
On any critical AI failure it reports honestly and queues NOTHING.

Run (from the project root):
    python -m content_factory.content_super_robot
    python -m content_factory.content_super_robot "Tofino storm watching"
Needs: OPENAI_API_KEY in the environment (same as every AI robot).
"""

import os
import sys
import uuid
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.channels import channels_text          # noqa: E402
from brain.learning import LearningBrain          # noqa: E402
from content_factory import (                     # noqa: E402
    adapter, caption_writer, cover_designer, editor, engagement_writer,
    fact_critic, hashtag_researcher, hook_critic, hook_master,
    idea_generator, librarian, music_picker, quality_gatekeeper,
    scheduler, scriptwriter, series_planner, storyboarder,
    title_writer, trend_scout, video_prompt_engineer)
from content_factory.common import HOST_LABEL     # noqa: E402
from robots.runner import AWAITING, ApprovalQueue  # noqa: E402

_CTA = ("Plan your trip with Cyrus AI — CA$10 for 14 days at "
        "victoriatourandadventure.com, or get the Cyrus AI Tour "
        "Guide app on Google Play.")
_FALLBACK_TAGS = ["#Shorts", "#TravelCanada", "#VictoriaBC",
                  "#VancouverIsland", "#TravelTips"]


def _fail(reason, **extra):
    out = {"ok": False, "ai_used": False, "queued": False,
           "error": reason}
    out.update(extra)
    return out


def _opt(result, notes, label):
    """Optional stage: return its payload dict, or {} + a note."""
    if result.get("ok"):
        for key in ("video_prompt", "series", "cover", "edit_brief",
                    "music", "engagement", "schedule"):
            if key in result:
                return result[key]
        return result
    notes.append(f"{label} unavailable: {result.get('error', '?')}")
    return {}


def build_package(focus=None):
    """Run the full pipeline for ONE concept.

    Returns {"ok": True, "queued": True, "id":..., "package": {...},
    "scores": {...}, "attempts": n} when a package passed the gate
    and was queued; an honest _fail(...) otherwise (nothing queued).
    """
    notes = []
    try:
        lessons = LearningBrain().get_lessons()
    except Exception:
        lessons = []
    lessons = list(lessons or []) + librarian.rejection_lessons()
    avoid = librarian.seen_concepts()

    # -- scout + idea (idea is critical) ------------------------------
    trend = None
    scout = trend_scout.find_trends(
        focus or "Vancouver Island and Pacific Northwest travel")
    if scout.get("ok") and scout["trends"]:
        trend = scout["trends"][0]
    else:
        notes.append("trend_scout unavailable — working from the "
                     "focus/niche alone")
    got = idea_generator.generate_idea(focus=focus, trend=trend,
                                       lessons=lessons, avoid=avoid)
    if not got.get("ok"):
        return _fail(f"idea_generator: {got.get('error')}", notes=notes)
    idea = got["idea"]
    concept, location = idea["concept"], idea["location"]

    # -- hook + script + storyboard (critical) -------------------------
    hooks = hook_master.write_hooks(concept, location)
    if not hooks.get("ok"):
        return _fail(f"hook_master: {hooks.get('error')}", notes=notes)
    hook = hooks["best_hook"]
    script_r = scriptwriter.write_script(concept, hook, location)
    if not script_r.get("ok"):
        return _fail(f"scriptwriter: {script_r.get('error')}",
                     notes=notes)
    script = script_r["script"]
    board_r = storyboarder.make_storyboard(concept, script, hook)
    if not board_r.get("ok"):
        return _fail(f"storyboarder: {board_r.get('error')}",
                     notes=notes)
    storyboard = board_r["storyboard"]

    # -- writing stages (fallbacks keep the package honest) ------------
    titles_r = title_writer.write_titles(concept, hook, location)
    if titles_r.get("ok"):
        title = titles_r["best_title"]
        alt_titles = titles_r["titles"]
    else:
        notes.append(f"title_writer unavailable: {titles_r.get('error')}")
        title, alt_titles = hook, [hook]

    caption_r = caption_writer.write_caption(concept, hook, location,
                                             lessons=lessons)
    if caption_r.get("ok"):
        caption = caption_r["caption"]
    else:
        notes.append(f"caption_writer unavailable: "
                     f"{caption_r.get('error')}")
        caption = (f"{hook}\n\n{concept}\n\n{_CTA}")

    tags_r = hashtag_researcher.research_hashtags(concept, location)
    if tags_r.get("ok"):
        hashtags = tags_r["hashtags"]
    else:
        notes.append(f"hashtag_researcher unavailable: "
                     f"{tags_r.get('error')}")
        hashtags = list(_FALLBACK_TAGS)

    # -- production stages (optional, noted when missing) --------------
    video_prompt = _opt(video_prompt_engineer.make_video_prompt(
        concept, location, idea.get("setting", ""), storyboard),
        notes, "video_prompt_engineer")
    series = _opt(series_planner.plan_series(concept, location),
                  notes, "series_planner")
    cover = _opt(cover_designer.design_cover(concept, hook, storyboard),
                 notes, "cover_designer")
    edit_brief = _opt(editor.make_edit_brief(concept, hook, storyboard,
                                             series), notes, "editor")
    music = _opt(music_picker.pick_music(concept, idea.get("setting", "")),
                 notes, "music_picker")
    engagement = _opt(engagement_writer.write_engagement(
        concept, hook, location), notes, "engagement_writer")
    schedule = _opt(scheduler.suggest_slot(concept), notes, "scheduler")

    adapt_r = adapter.adapt_package(title, caption, hook, hashtags)
    if adapt_r.get("ok"):
        platforms = adapt_r["platforms"]
        primary = adapt_r["primary_platform"]
        title = platforms["youtube"]["title"] or title
        description = platforms["youtube"]["description"]
    else:
        notes.append(f"adapter unavailable: {adapt_r.get('error')}")
        primary = "youtube"
        platforms = {}
        description = (caption + "\n\n" + channels_text() + "\n"
                       + " ".join(hashtags))

    # -- critics + the gate (ONE hook retry with fix notes) ------------
    attempts = 0
    gate = None
    hook_scores = None
    fact_result = None
    while attempts < 2:
        attempts += 1
        hook_scores = hook_critic.score_hook(hook, concept)
        if not hook_scores.get("ok"):
            return _fail(f"hook_critic: {hook_scores.get('error')}",
                         notes=notes)
        fact_result = fact_critic.check_facts({
            "hook": hook, "title": title, "caption": caption,
            "description": description,
            "script": script.get("spoken_text", ""),
        })
        gate = quality_gatekeeper.judge(
            hook_scores["score"], fact_result,
            hook_fix=hook_scores.get("fix", ""))
        if gate["passed"]:
            break
        if attempts == 1:
            retry = hook_master.write_hooks(
                concept, location, fix_notes=gate["fix_notes"])
            if retry.get("ok"):
                old_hook = hook
                hook = retry["best_hook"]
                # keep the script coherent: line 1 IS the hook
                if script.get("lines"):
                    script["lines"][0]["text"] = hook
                script["spoken_text"] = script.get(
                    "spoken_text", "").replace(old_hook, hook, 1)
                notes.append("gate rejected attempt 1 "
                             f"({gate['final_score']}/10) — hook "
                             "rewritten with the fix notes")
            else:
                notes.append("hook retry unavailable: "
                             f"{retry.get('error')}")
                break

    scores = {"hook": hook_scores["score"],
              "final": gate["final_score"],
              "gate_min": quality_gatekeeper.GATE_MIN,
              "fact_passed": bool(fact_result.get("passed")),
              "fact_flags": fact_result.get("flags", []),
              "hook_reasons": hook_scores.get("reasons", [])}

    if not gate["passed"]:
        librarian.record({
            "status": "rejected_by_gate", "concept": concept,
            "location": location, "title": title, "hook": hook,
            "scores": scores, "fix_notes": gate["fix_notes"],
            "attempts": attempts,
        })
        return _fail(
            f"quality gate rejected the package after {attempts} "
            f"attempt(s): final {gate['final_score']}/10 "
            f"(needs {quality_gatekeeper.GATE_MIN}/10)",
            notes=notes, scores=scores, gate=gate, concept=concept)

    # -- queue the finished package ------------------------------------
    package = {
        "concept": concept, "location": location,
        "setting": idea.get("setting", ""),
        "host_moment": idea.get("host_moment", ""),
        "technique": idea.get("technique", ""),
        "hook": hook, "hook_candidates": hooks["hooks"],
        "script": script, "storyboard": storyboard,
        "title": title, "alt_titles": alt_titles,
        "caption": caption, "description": description,
        "hashtags": hashtags, "cta": _CTA,
        "video_prompt": video_prompt, "series": series,
        "cover": cover, "edit_brief": edit_brief, "music": music,
        "engagement": engagement, "platforms": platforms,
        "schedule_suggestion": schedule,
        "scores": scores, "attempts": attempts, "notes": notes,
    }
    pid = uuid.uuid4().hex[:8]
    now = datetime.now().isoformat()
    preview = (
        f"🏭 Content Factory package — {title}\n"
        f"🪝 Hook (first 2 seconds): \"{hook}\"\n"
        f"Concept: {concept}\n"
        f"⭐ Quality gate: hook {scores['hook']}/10, final "
        f"{scores['final']}/10 (min {quality_gatekeeper.GATE_MIN})\n"
        f"🎬 Series: {series.get('series_name', '—')} | "
        f"Location: {location}\n"
        f"CTA: {_CTA}"
    )
    entry = {
        "id": pid,
        "source_id": None,
        "caption": preview,
        "image_path": None,
        "image_note": ("content factory package — the video is "
                       "produced from the video_prompt + storyboard "
                       "in this entry"),
        "image_public_url": None,
        "scheduled_for": now,
        "created_at": now,
        "status": AWAITING,
        "channels": [primary],
        "results": {},
        # Content Factory payload
        "platform": primary,
        "format": "short",
        "source": "content_factory",
        "title": title,
        "hook": hook,
        "concept": concept,
        "description": description,
        "caption_text": caption,
        "hashtags": hashtags,
        "cta": _CTA,
        "script": script,
        "storyboard": storyboard,
        "video_prompt": video_prompt,
        "series": series,
        "cover": cover,
        "edit_brief": edit_brief,
        "music": music,
        "engagement": engagement,
        "platforms": platforms,
        "schedule_suggestion": schedule,
        "scores": scores,
        "ai_generated": True,
        "host": HOST_LABEL,
        "factory_notes": notes,
    }
    ApprovalQueue().add(entry)
    librarian.record({
        "status": "queued", "queue_id": pid, "concept": concept,
        "location": location, "title": title, "hook": hook,
        "scores": scores, "attempts": attempts,
    })
    return {"ok": True, "ai_used": True, "queued": True, "id": pid,
            "package": package, "scores": scores, "attempts": attempts,
            "notes": notes}


def _print_summary_fa(result):
    if not result.get("queued"):
        print("🏭 ربات ارشد کارخانه‌ی محتوا: هیچ بسته‌ای در صف ثبت نشد.")
        print(f"دلیل: {result.get('error')}")
        for n in result.get("notes", []):
            print(f"  - {n}")
        return
    p, s = result["package"], result["scores"]
    print("🏭 ربات ارشد کارخانه‌ی محتوا — یک بسته‌ی کامل ساخته شد")
    print(f"🎬 {p['title']}")
    print(f"🪝 قلاب: «{p['hook']}»")
    print(f"⭐ امتیاز قلاب: {s['hook']}/۱۰ — امتیاز نهایی دروازه‌ی "
          f"کیفیت: {s['final']}/۱۰ (حداقل {s['gate_min']})")
    print(f"تلاش‌ها تا قبولی: {result['attempts']}")
    print(f"شناسه در صف تأیید: {result['id']}")
    print("بسته در صف تأیید (approval_queue.json) با وضعیت «در "
          "انتظار تأیید» ثبت شد. هیچ‌چیز منتشر نشده است — اول "
          "تأیید شما، بعد انتشار.")


def main(argv):
    focus = " ".join(argv[1:]).strip() or None
    result = build_package(focus=focus)
    _print_summary_fa(result)
    return 0 if result.get("queued") else 1


# The orchestrator, as a named team member.
CONTENT_SUPER_ROBOT = {"build_package": build_package}


if __name__ == "__main__":
    sys.exit(main(sys.argv))
