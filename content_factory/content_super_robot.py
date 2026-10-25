"""ULTIMATE ROBOT TEAM — content_factory/content_super_robot.py

The Content Factory's SUPER ROBOT: orchestrates all 20 factory
robots into one production line and enqueues ONE finished package
per concept — whenever it is fact-clean (see the gate rule below).

Pipeline:
    librarian (avoid-list + rejection lessons)
      -> trend_scout -> idea_generator
      -> hook_master (FIVE formula candidates) -> hook_critic
         batch-scores them -> the package runs with the winner
      -> scriptwriter (line 1 IS the winning hook) -> storyboarder
      -> title_writer / caption_writer /
         hashtag_researcher / video_prompt_engineer / series_planner /
         cover_designer / editor / music_picker / adapter /
         engagement_writer / scheduler
      -> hook_critic + fact_critic -> quality_gatekeeper
         (NO critic blocking, Cyrus's rule 2026-10-25: the hook
          score only ranks candidates and is recorded as
          information — it never blocks. The ONLY hard gate is
          fact_critic's deterministic scan: invented prices,
          hours or phone numbers reject the package; on a fact
          rejection, ONE retry revises whichever fields the scan
          concretely flagged — hook, title, caption, description,
          script — then re-checks. Still dirty -> nothing queued.)
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
import re
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
from content_factory.common import (                # noqa: E402
    APPROVED_FACTS, HOST_LABEL, role_ask)
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


_TEXT_FIELDS = ("hook", "title", "caption", "description", "script")

_REVISE_SYSTEM = (
    "You revise ONE field of a travel short-form content package "
    "after a fact-scan rejection. Remove ONLY the flagged "
    "invented facts and change nothing else — same tone, same "
    "structure, about the same length, same call to action and "
    "links. " + APPROVED_FACTS +
    " Reply with ONLY valid JSON, no other text."
)


def _revise_field(field, text, concept, fix_notes):
    """Rewrite one text field against concrete fix notes.

    Returns the revised text, or None on AI failure (the caller
    keeps the original and notes it honestly).
    """
    if not str(text or "").strip() or not fix_notes:
        return None
    prompt = (
        f"Field: {field}\nConcept: {concept}\n"
        "The fact scan flagged these CONCRETE problems in this "
        "field — fix exactly these, change nothing else:\n- "
        + "\n- ".join(str(n) for n in fix_notes) + "\n"
        f"Current text:\n{text}\n"
        'Reply ONLY valid JSON: {"text": "..."}'
    )
    data = role_ask(_REVISE_SYSTEM, prompt, max_tokens=900,
                    temperature=0.5)
    if data is None:
        return None
    new = str(data.get("text", "")).strip()
    return new or None


def _flagged_fields(fact_result):
    """Fields carrying a CONCRETE hard flag. Fact-critic flags are
    formatted "field: ..." and always quote the offending text, so
    the field prefix is trustworthy."""
    fields = []
    for f in (fact_result or {}).get("flags", []):
        head = str(f).split(":", 1)[0].strip().lower()
        if head in _TEXT_FIELDS and head not in fields:
            fields.append(head)
    return fields


def _field_notes(field, fact_result, gate):
    """The fix notes that concern one field: its own concrete fact
    flags, plus the gate's general removal instruction."""
    notes = [str(f) for f in (fact_result or {}).get("flags", [])
             if str(f).split(":", 1)[0].strip().lower() == field]
    for n in (gate or {}).get("fix_notes", []):
        if not str(n).startswith("FACT:"):
            notes.append(str(n))
    return notes


def _revise_after_gate(gate, fact_result, hook_score, concept,
                       location, fields, script, notes):
    """ONE revision pass after a fact-scan rejection.

    Revises whichever text fields the deterministic fact scan
    concretely flagged — the hook goes back to the hook master
    ONLY when the hook itself is flagged (a low hook score alone
    never triggers a rewrite: scores no longer block); title,
    caption, description and script are rewritten against their
    own flags. Mutates script in place; returns
    (fields, changed) where fields is the updated
    {hook, title, caption, description} dict.
    """
    changed = False
    flagged = _flagged_fields(fact_result)

    if "hook" in flagged:
        retry = hook_master.write_hooks(
            concept, location, fix_notes=gate["fix_notes"])
        if retry.get("ok"):
            old_hook = fields["hook"]
            fields["hook"] = retry["best_hook"]
            # keep the script coherent: line 1 IS the hook
            if script.get("lines"):
                script["lines"][0]["text"] = fields["hook"]
            script["spoken_text"] = script.get(
                "spoken_text", "").replace(old_hook, fields["hook"], 1)
            changed = True
        else:
            notes.append("hook revision unavailable: "
                         f"{retry.get('error')}")

    for field in ("title", "caption", "description"):
        if field not in flagged:
            continue
        new = _revise_field(field, fields[field], concept,
                            _field_notes(field, fact_result, gate))
        if new:
            fields[field] = new
            changed = True
        else:
            notes.append(f"{field} revision unavailable — kept "
                         "the flagged original")

    if "script" in flagged:
        snotes = _field_notes("script", fact_result, gate)
        new_spoken = _revise_field("script",
                                   script.get("spoken_text", ""),
                                   concept, snotes)
        if new_spoken:
            quotes = []
            for f in (fact_result or {}).get("flags", []):
                if str(f).split(":", 1)[0].strip().lower() == "script":
                    quotes += re.findall(r"'([^']{3,})'", str(f))
            for line in script.get("lines", []):
                low = line.get("text", "").lower()
                if any(q.lower() in low for q in quotes):
                    new_line = _revise_field("script line",
                                             line["text"], concept,
                                             snotes)
                    if new_line:
                        line["text"] = new_line
            script["spoken_text"] = new_spoken
            changed = True
        else:
            notes.append("script revision unavailable — kept the "
                         "flagged original")

    if changed:
        notes.append(
            f"fact scan rejected attempt 1 — revised field(s): "
            + ", ".join(f for f in _TEXT_FIELDS if f in flagged))
    return fields, changed


def build_package(focus=None):
    """Run the full pipeline for ONE concept.

    Returns {"ok": True, "queued": True, "id":..., "package": {...},
    "scores": {...}, "attempts": n} when a package was fact-clean
    and queued; an honest _fail(...) otherwise (nothing queued).
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

    # -- hook (5 formula candidates, batch-scored) + script + board --
    cands = hook_master.write_hook_candidates(concept, location)
    if not cands.get("ok"):
        return _fail(f"hook_master: {cands.get('error')}", notes=notes)
    ranked = hook_critic.score_hooks_batch(cands["candidates"],
                                           concept)
    if not ranked.get("ok"):
        return _fail(f"hook_critic: {ranked.get('error')}",
                     notes=notes)
    hook = ranked["best_hook"]
    hook_candidates = [c["hook"] for c in cands["candidates"]]
    notes.append(
        f"hook picked from {len(hook_candidates)} formula "
        f"candidates — batch best {ranked['best_score']}/10 "
        f"({ranked['ranked'][0]['formula']})")
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

    # -- fact scan (the only hard gate) + hook score (info only) --
    # The hook critic scores each attempt so the score is recorded
    # in the package; it never blocks. A gate failure here means
    # the deterministic fact scan flagged an invented price /
    # hour / phone: ONE revision of the flagged fields, re-check,
    # and if it is still dirty the package is honestly rejected.
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
            fields = {"hook": hook, "title": title,
                      "caption": caption, "description": description}
            fields, changed = _revise_after_gate(
                gate, fact_result, hook_scores["score"], concept,
                location, fields, script, notes)
            hook, title = fields["hook"], fields["title"]
            caption, description = (fields["caption"],
                                    fields["description"])
            if platforms.get("youtube"):
                platforms["youtube"]["title"] = title
                platforms["youtube"]["description"] = description
            if not changed:
                notes.append("fact scan rejected attempt 1 and no "
                             "flagged field could be revised — "
                             "giving up honestly")
                break

    # Kept in the scores for ledger-schema continuity with older
    # entries; the regeneration round was removed 2026-10-25 when
    # hook scores stopped blocking, so it is always False now.
    hook_regen_used = False

    scores = {"hook": hook_scores["score"],
              "final": gate["final_score"],
              "gate_min": quality_gatekeeper.GATE_MIN,
              "fact_passed": bool(fact_result.get("passed")),
              "fact_flags": fact_result.get("flags", []),
              "fact_warnings": fact_result.get("warnings", []),
              "hook_reasons": hook_scores.get("reasons", []),
              "hook_regen_used": hook_regen_used}

    if not gate["passed"]:
        # Reachable ONLY via the fact scan now (scores never
        # block); the ledger status string is kept for continuity
        # with the librarian's stats/rejection-lessons machinery.
        librarian.record({
            "status": "rejected_by_gate", "concept": concept,
            "location": location, "title": title, "hook": hook,
            "scores": scores, "fix_notes": gate["fix_notes"],
            "attempts": attempts,
        })
        return _fail(
            f"fact scan rejected the package after {attempts} "
            f"attempt(s): "
            + "; ".join(fact_result.get("flags", [])),
            notes=notes, scores=scores, gate=gate, concept=concept)

    # -- queue the finished package ------------------------------------
    package = {
        "concept": concept, "location": location,
        "setting": idea.get("setting", ""),
        "host_moment": idea.get("host_moment", ""),
        "technique": idea.get("technique", ""),
        "hook": hook, "hook_candidates": hook_candidates,
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
        f"⭐ Hook score (info only, never blocks): "
        f"{scores['hook']}/10 | fact scan: clean ✅\n"
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
    print(f"⭐ امتیاز قلاب (فقط برای اطلاع — هیچ امتیازی جلوی "
          f"ثبت را نمی‌گیرد): {s['hook']}/۱۰ | بررسی واقعیت: پاک ✅")
    print(f"تلاش‌ها تا ثبت: {result['attempts']}")
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
