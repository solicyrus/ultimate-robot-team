"""ULTIMATE ROBOT TEAM — content_factory/video_finisher.py

The Content Factory's missing finisher — the tool that actually
RENDERS a finished Short. editor.py (robot 12) writes the assembly
brief; this robot executes it, deterministically, with ffmpeg + PIL.
No AI, no network, no API keys.

What it burns in — each overlay exactly ONCE on a 30-second
timeline (the single-pass standard Cyrus ordered 2026-10-25; the
old loop-the-finished-file shortcut repeated the hook and the CTA
band at every loop join, which is why this tool exists):

  - the footage: the entry's RAW clip (queue `video_path`, no
    overlays) looped x3 and normalized to 720x1280; the two loop
    joins are softened with a 0.3s crossfade (audio acrossfaded on
    the same offsets, so lip sync never drifts);
  - the HOOK text: 0.0-3.0s only, big bold gold letters with a
    black outline across the top — the established house style;
  - the circular Cyrus logo (the C+S monogram — Cyrus's primary
    brand mark, settled 2026-10-25 — in a gold ring): top-left,
    burned in for the FULL duration;
  - the END CARD: the last 2.5s only — a translucent black band
    across the bottom with the entry's CTA line in gold plus the
    approved price line "CA$10 for 14 days".

Output: exactly 30.000s, 720x1280, H.264 (CRF 18) + AAC, written
to the entry's `edited_file` (edited/<id>-final.mp4) and recorded
on the queue entry the same way thumbnail_maker records
`thumbnail_file`.

Entry sources: seven bank entries carry their raw clip in the
queue's `video_path`. The Butchart package (73e65443) was produced
from a video_prompt, so its queue entry has no video_path — its
generated source clip lives in the media-generation library and
is mapped in RAW_OVERRIDES below.

Run it (from the project root):
    ./venv/bin/python -m content_factory.video_finisher e67f1214
    ./venv/bin/python -m content_factory.video_finisher --all
    ./venv/bin/python -m content_factory.video_finisher 73e65443
"""

import os
import re
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from content_factory.common import fail  # noqa: E402
from robots.runner import ApprovalQueue  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- canvas / timing (the locked production standard) ----------------
WIDTH, HEIGHT, FPS = 720, 1280, 24
DURATION = 30.0
HOOK_SECONDS = 3.0            # hook overlay: 0.0s -> 3.0s, once
END_CARD_SECONDS = 2.5        # end card: last 2.5s, once
XFADE = 0.3                   # crossfade softening each loop join

# --- house style, measured off the established finals ----------------
GOLD = (248, 184, 28)
BLACK = (0, 0, 0)
BAND_ALPHA = 205              # translucent black end-card band
PRICE_LINE = "CA$10 for 14 days"   # approved fact, common.py

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

# The logo the finisher burns in: Cyrus's primary brand mark —
# the C+S metallic green/gold monogram in a circle with a gold
# ring, top-left (settled by Cyrus 2026-10-25; the same badge
# thumbnail_maker stamps). NOT the commander avatar the earliest
# finals carried.
LOGO_CANDIDATES = (
    os.path.join(REPO_ROOT, "images", "cyrus-logo-profile.jpg"),
    os.path.expanduser("~/workspace/imagine_media/"
                       "cyrus-logo-profile.png"),
    os.path.expanduser("~/workspace/imagine_media/"
                       "cyrus-logo-profile.jpg"),
)

# Queue id -> output file stem when it differs from the id, and
# queue id -> raw source when the entry carries no video_path.
FILE_ALIASES = {"73e65443": "butchart-fall"}
RAW_OVERRIDES = {
    "73e65443": os.path.expanduser(
        "~/workspace/imagine_media/"
        "media-generation-butchart-fall-factory-1-"
        "0-9c47e730-d03e-4c23-933b-33854d9dcbae.mp4"),
}

# The entries this tool was built to (re)finish: every queue entry
# that already has an edited_file, plus the alias-mapped package.
KNOWN_TARGETS = ("e67f1214", "e0332991", "cb43bf2b", "0ede2a33",
                 "28bcfc3c", "567a16d3", "69049887", "73e65443")


def _first_existing(paths):
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None


_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D\u2190-\u21FF]")


def clean_overlay_text(text):
    """Overlay text the way the established finals render it:
    emojis stripped, the ellipsis as three dots, single spaces."""
    t = _EMOJI_RE.sub("", str(text or ""))
    t = t.replace("\u2026", "...")
    return " ".join(t.split()).strip()


def end_card_lines(entry):
    """The end card's two gold lines for an entry.

    Line 1 is the entry's own CTA opener: the script's closing
    "Plan your ..." line when the package carries a script
    (Butchart: "Plan your visit with Cyrus AI ..."), else the
    queue CTA's first clause ("Plan your trip with Cyrus AI").
    Line 2 is the one approved price fact. Returns [] when no
    CTA can be derived — the caller fails honestly.
    """
    line1 = ""
    script = entry.get("script") or {}
    lines = script.get("lines") or []
    for item in reversed(lines):
        text = str((item or {}).get("text", "")).strip()
        if text.lower().startswith("plan your"):
            line1 = re.split(r"\s+for\s+|\s+—\s+|\s+-\s+|\.",
                             text)[0].strip()
            break
    if not line1:
        cta = str(entry.get("cta", "")).strip()
        if cta:
            line1 = re.split(r"\s+—\s+|\s+-\s+|\.|,", cta)[0].strip()
    if not line1:
        return []
    if not line1.endswith("!"):
        line1 += "!"
    return [clean_overlay_text(line1), PRICE_LINE]


def _probe(video_path):
    """(duration, has_audio) via ffprobe, or None."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration", "-show_entries", "stream=codec_type",
             "-of", "json", video_path],
            capture_output=True, text=True, timeout=30)
        import json
        data = json.loads(out.stdout)
        dur = float(data["format"]["duration"])
        has_audio = any(s.get("codec_type") == "audio"
                        for s in data.get("streams", []))
        return dur, has_audio
    except Exception:
        return None


def _fit_lines(draw, text, font_path, max_size, max_w, max_lines,
               min_size=28):
    """Largest font (<= max_size) whose word-wrapped text fits
    max_w on at most max_lines. Returns (font, lines) or None."""
    from PIL import ImageFont
    words = text.split()
    size = max_size
    while size >= min_size:
        font = ImageFont.truetype(font_path, size)
        lines, cur = [], ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if draw.textlength(trial, font=font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if len(lines) <= max_lines and all(
                draw.textlength(l, font=font) <= max_w for l in lines):
            return font, lines
        size = int(size * 0.92)
    return None


def _draw_block(img, lines, font, top_y, line_ratio=1.18):
    """Draw gold text lines as one block: the block is centred
    horizontally, the lines left-aligned inside it — the layout
    the established finals use."""
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    widths = [draw.textlength(l, font=font) for l in lines]
    x0 = (img.width - max(widths)) / 2
    stroke = max(2, font.size // 11)
    y = top_y
    for line in lines:
        draw.text((x0, y), line, font=font, fill=GOLD + (255,),
                  stroke_width=stroke, stroke_fill=BLACK + (255,))
        y += int(font.size * line_ratio)
    return img


def _circular_logo(diameter):
    """The C+S monogram as a circular badge with a gold ring
    (the finisher's burned-in logo), or None."""
    from PIL import Image, ImageDraw
    path = _first_existing(LOGO_CANDIDATES)
    if not path:
        return None
    try:
        logo = Image.open(path).convert("RGB")
    except Exception:
        return None
    side = min(logo.size)
    logo = logo.crop(((logo.width - side) // 2,
                      (logo.height - side) // 2,
                      (logo.width + side) // 2,
                      (logo.height + side) // 2))
    logo = logo.resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new("L", (diameter, diameter), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, diameter, diameter),
                                 fill=255)
    badge = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    badge.paste(logo, (0, 0), mask)
    ring = max(3, diameter // 28)
    ImageDraw.Draw(badge).ellipse(
        (ring // 2, ring // 2, diameter - ring // 2 - 1,
         diameter - ring // 2 - 1), outline=GOLD + (255,),
        width=ring)
    return badge


def render_overlays(entry, work_dir):
    """Render the three overlay PNGs (hook canvas, logo badge,
    end-card canvas) for one entry into work_dir.

    Returns {"ok": True, "hook":..., "logo":..., "endcard":...,
    "hook_text":..., "end_lines":[...]} or an honest failure.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        return fail("Pillow is not installed (requirements.txt "
                    "has it)")
    font_path = _first_existing(FONT_CANDIDATES)
    if not font_path:
        return fail("no bold font available for PIL text rendering")

    hook_text = clean_overlay_text(entry.get("hook", ""))
    if not hook_text:
        return fail("entry has no hook text to burn in")
    end_lines = end_card_lines(entry)
    if not end_lines:
        return fail("entry has no CTA to derive the end card from")
    badge = _circular_logo(int(WIDTH * 0.195))
    if badge is None:
        return fail("C+S monogram logo file not found "
                    "(images/cyrus-logo-profile.jpg)")

    # Hook canvas: text block across the top.
    hook_img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    fitted = _fit_lines(ImageDraw.Draw(hook_img), hook_text,
                        font_path, max_size=int(WIDTH * 0.08),
                        max_w=int(WIDTH * 0.94), max_lines=2)
    if fitted is None:
        return fail(f"hook text did not fit: {hook_text!r}")
    font, lines = fitted
    _draw_block(hook_img, lines, font, top_y=int(HEIGHT * 0.078))
    hook_png = os.path.join(work_dir, "hook.png")
    hook_img.save(hook_png)

    logo_png = os.path.join(work_dir, "logo.png")
    badge.save(logo_png)

    # End-card canvas: translucent black band + gold CTA lines.
    end_img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    band_h = int(HEIGHT * 0.285)
    band = Image.new("RGBA", (WIDTH, band_h),
                     BLACK + (BAND_ALPHA,))
    end_img.alpha_composite(band, (0, HEIGHT - band_h))
    fitted = _fit_lines(ImageDraw.Draw(end_img), " ".join(end_lines),
                        font_path, max_size=int(WIDTH * 0.072),
                        max_w=int(WIDTH * 0.94), max_lines=99)
    if fitted is None:
        return fail("end-card text did not fit")
    # fit the two lines at ONE shared size (the finals match sizes)
    from PIL import ImageFont
    size = int(WIDTH * 0.072)
    while size >= 28:
        font = ImageFont.truetype(font_path, size)
        d = ImageDraw.Draw(end_img)
        if all(d.textlength(l, font=font) <= int(WIDTH * 0.94)
               for l in end_lines):
            break
        size = int(size * 0.92)
    _draw_block(end_img, end_lines, font,
                top_y=HEIGHT - band_h + int(HEIGHT * 0.055),
                line_ratio=1.25)
    end_png = os.path.join(work_dir, "endcard.png")
    end_img.save(end_png)

    return {"ok": True, "hook": hook_png, "logo": logo_png,
            "endcard": end_png, "hook_text": hook_text,
            "end_lines": end_lines}


def finish_video(entry, raw_path, out_path):
    """Render one finished Short from its raw clip.

    Single pass: the raw clip is looped x3 in the filter graph
    with a short crossfade on each join (audio acrossfaded on the
    same offsets), then hook (0-3s), logo (full duration) and end
    card (last 2.5s) are overlaid — each exactly once.
    Returns a result dict; never raises.
    """
    info = _probe(raw_path)
    if not info:
        return fail(f"ffprobe could not read the raw clip: "
                    f"{raw_path}")
    seg, has_audio = info
    if seg <= 0:
        return fail(f"raw clip has no duration: {raw_path}")
    # The third segment runs long by the two crossfade overlaps
    # so the joined timeline lands on exactly DURATION:
    # total = seg + seg + seg3 - 2*XFADE = DURATION.
    seg3 = DURATION - 2 * seg + 2 * XFADE
    if seg3 < seg:
        seg3 = seg

    with tempfile.TemporaryDirectory() as td:
        ov = render_overlays(entry, td)
        if not ov.get("ok"):
            return ov
        scale = (f"scale={WIDTH}:{HEIGHT}:"
                 f"force_original_aspect_ratio=increase:"
                 f"flags=lanczos,crop={WIDTH}:{HEIGHT},"
                 f"setsar=1,fps={FPS}")
        fc = []
        for i in range(3):
            fc.append(f"[{i}:v]{scale},trim=0:{seg if i < 2 else seg3},"
                      f"setpts=PTS-STARTPTS[v{i}]")
        off1 = seg - XFADE
        len1 = 2 * seg - XFADE
        off2 = len1 - XFADE
        fc.append(f"[v0][v1]xfade=transition=fade:"
                  f"duration={XFADE}:offset={off1}[x1]")
        fc.append(f"[x1][v2]xfade=transition=fade:"
                  f"duration={XFADE}:offset={off2}[vbase]")
        fc.append(f"[vbase]tpad=stop_mode=clone:stop_duration=2,"
                  f"trim=0:{DURATION},setpts=PTS-STARTPTS[vp]")
        margin = int(WIDTH * 0.014)
        fc.append(f"[vp][3:v]overlay={margin}:{margin}[w1]")
        fc.append(f"[w1][4:v]overlay=0:0:"
                  f"enable='between(t,0,{HOOK_SECONDS})'[w2]")
        fc.append(f"[w2][5:v]overlay=0:0:"
                  f"enable='between(t,{DURATION - END_CARD_SECONDS},"
                  f"{DURATION})'[vout]")
        if has_audio:
            for i in range(3):
                fc.append(f"[{i}:a]aresample=48000,"
                          f"atrim=0:{seg if i < 2 else seg3},"
                          f"asetpts=PTS-STARTPTS[a{i}]")
            fc.append(f"[a0][a1]acrossfade=d={XFADE}[ac1]")
            fc.append(f"[ac1][a2]acrossfade=d={XFADE},"
                      f"apad,atrim=0:{DURATION}[aout]")
        cmd = ["ffmpeg", "-y",
               "-i", raw_path, "-i", raw_path,
               "-stream_loop", "1", "-i", raw_path]
        for png in (ov["logo"], ov["hook"], ov["endcard"]):
            cmd += ["-loop", "1", "-framerate", str(FPS),
                    "-t", str(DURATION), "-i", png]
        cmd += ["-filter_complex", ";".join(fc),
                "-map", "[vout]"]
        if has_audio:
            cmd += ["-map", "[aout]", "-c:a", "aac", "-b:a", "160k"]
        cmd += ["-c:v", "libx264", "-crf", "18", "-preset", "medium",
                "-pix_fmt", "yuv420p", "-t", str(DURATION),
                "-movflags", "+faststart", out_path]
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=900)
        if r.returncode != 0 or not os.path.isfile(out_path):
            tail = (r.stderr or "").strip().splitlines()[-3:]
            return fail("ffmpeg failed: " + " | ".join(tail))
    done = _probe(out_path)
    return {"ok": True, "path": out_path,
            "duration": done[0] if done else None,
            "audio": bool(done and done[1]),
            "hook_text": ov["hook_text"],
            "end_lines": ov["end_lines"]}


def entry_raw_path(entry):
    """The entry's raw source clip: an explicit override first
    (factory packages produced from a prompt), then the queue's
    own video_path."""
    eid = str(entry.get("id", ""))
    if eid in RAW_OVERRIDES and os.path.isfile(RAW_OVERRIDES[eid]):
        return RAW_OVERRIDES[eid]
    raw = str(entry.get("video_path") or "").strip()
    if raw:
        p = raw if os.path.isabs(raw) else os.path.join(REPO_ROOT,
                                                        raw)
        if os.path.isfile(p):
            return p
    return None


def entry_out_path(entry, root=REPO_ROOT):
    """edited/<stem>-final.mp4 for the entry (the alias map covers
    the Butchart package, whose file stem is not its queue id)."""
    eid = str(entry.get("id", "entry"))
    stem = FILE_ALIASES.get(eid, eid)
    return os.path.join(root, "edited", f"{stem}-final.mp4")


def finish_entry(entry, root=REPO_ROOT, raw_path=None, out_path=None):
    """Finish one queue entry and record `edited_file` on it the
    way the team's finish step always has (repo-relative)."""
    raw = raw_path or entry_raw_path(entry)
    if not raw:
        return fail("no raw source clip found for this entry "
                    "(no video_path, no override)")
    out = out_path or entry_out_path(entry, root)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    r = finish_video(entry, raw, out)
    if not r.get("ok"):
        return r
    r["raw"] = raw
    try:
        rel = os.path.relpath(out, root)
    except Exception:
        rel = out
    r["edited_file"] = rel if not rel.startswith("..") else out
    return r


def finish_all(queue_path=None, root=REPO_ROOT):
    """Finish every KNOWN_TARGETS entry. Returns a summary dict;
    never raises. Entries already carrying the single-pass mark
    are re-finished too — finishing is idempotent."""
    queue = ApprovalQueue(queue_path)
    done, failed = [], []
    for eid in KNOWN_TARGETS:
        entry, err = queue.find(eid)
        if err:
            failed.append({"id": eid, "error": err})
            continue
        r = finish_entry(entry, root=root)
        if r.get("ok"):
            entry["edited_file"] = r["edited_file"]
            entry["finish_pass"] = "single-pass-30s"
            queue._save()
            done.append(eid)
        else:
            failed.append({"id": eid, "error": r.get("error")})
    return {"ok": True, "finished": done, "failed": failed}


def main(argv):
    entry_id, queue_path, raw, out = None, None, None, None
    args = list(argv[1:])
    do_all = "--all" in args
    args = [a for a in args if a != "--all"]
    while args:
        a = args.pop(0)
        if a == "--queue":
            queue_path = args.pop(0)
        elif a == "--raw":
            raw = args.pop(0)
        elif a == "--out":
            out = args.pop(0)
        elif not a.startswith("--"):
            entry_id = a
    if do_all:
        s = finish_all(queue_path=queue_path)
        print(f"🎬 video_finisher: finished "
              f"{len(s['finished'])} ({', '.join(s['finished']) or '—'}), "
              f"failed {len(s['failed'])}")
        for f in s["failed"]:
            print(f"  - {f['id']}: {f['error']}")
        return 0 if not s["failed"] else 1
    if not entry_id:
        print("🎬 video_finisher: give an entry id or --all")
        return 1
    queue = ApprovalQueue(queue_path)
    entry, err = queue.find(entry_id)
    if err:
        print(f"🎬 video_finisher: {err}")
        return 1
    r = finish_entry(entry, raw_path=raw, out_path=out)
    if not r.get("ok"):
        print(f"🎬 video_finisher: FAILED for {entry_id}: "
              f"{r.get('error')}")
        return 1
    entry["edited_file"] = r["edited_file"]
    entry["finish_pass"] = "single-pass-30s"
    queue._save()
    print(f"🎬 video_finisher: {entry_id} -> {r['edited_file']} "
          f"({r['duration']:.3f}s, audio: "
          f"{'yes' if r['audio'] else 'no'}, raw: {r['raw']})")
    return 0


VIDEO_FINISHER_ROBOT = {"finish_entry": finish_entry,
                        "finish_all": finish_all}

if __name__ == "__main__":
    sys.exit(main(sys.argv))
