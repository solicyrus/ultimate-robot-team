"""ULTIMATE ROBOT TEAM — content_factory/thumbnail_maker.py

Content Factory robot 21 of 22: the thumbnail maker.

cover_designer (robot 11) writes the cover BRIEF — the words, the
frame choice, the layout. This robot turns that brief into the
actual thumbnail IMAGE: it pulls a strong frame out of the
finished video (ffmpeg), lays the hook text over it in the team's
brand style — big GOLD letters on a deep-NAVY band, readable at a
glance on a phone — stamps the circular Cyrus logo in the corner,
and saves <entry-id>-thumb.jpg next to the edited video. The queue
entry gains a `thumbnail_file` field, exactly the way the finish
step records `edited_file`.

Fully deterministic and offline: fixed frame-sampling fractions, a
fixed brightness/detail score for picking the frame, PIL text
rendering. No AI, no network, no API keys. On any failure it
reports honestly (the team's rule) and changes nothing.

Run it (from the project root):
    ./venv/bin/python -m content_factory.thumbnail_maker
    ./venv/bin/python -m content_factory.thumbnail_maker e67f1214
    ./venv/bin/python -m content_factory.thumbnail_maker --queue COPY.json --out-dir /tmp/thumbs
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

# The team's brand: gold letters on deep navy (the finish pipeline's
# hook-text colours, the channel's monogram colours).
GOLD = (216, 178, 60)
NAVY = (8, 24, 52)
NAVY_DARK = (3, 9, 24)

# The circular Cyrus logo: the channel monogram. First existing
# candidate wins — the repo copy if present, else the team's media
# library original (same places the finish pipeline reads it from).
LOGO_CANDIDATES = (
    os.path.join(REPO_ROOT, "images", "cyrus-logo-profile.jpg"),
    os.path.expanduser("~/workspace/imagine_media/cyrus-logo-profile.png"),
    os.path.expanduser("~/workspace/imagine_media/cyrus-logo-profile.jpg"),
)

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)

# Frame sampling points (fractions of the duration) — past the
# burned-in hook overlay at 0-2.2s, before the end card.
_FRAME_FRACTIONS = (0.22, 0.42, 0.62)


def _first_existing(paths):
    for p in paths:
        if p and os.path.isfile(p):
            return p
    return None


def thumbnail_text(entry):
    """The ≤4 thumbnail words for an entry: cover_designer's
    cover_text when the package has one, else the first words of
    the hook (then the title). Emojis and punctuation are stripped
    — thumbnail type is letters, big and clean."""
    cover = entry.get("cover") or {}
    raw = (str(cover.get("cover_text", "")).strip()
           or str(entry.get("hook", "")).strip()
           or str(entry.get("title", "")).strip())
    raw = re.sub(r"[^\w\s'\-&!?]", " ", raw, flags=re.UNICODE)
    words = [w for w in raw.split() if w]
    return " ".join(words[:4]).upper()


def _probe(video_path):
    """(width, height, duration) via ffprobe, or None."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,duration",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True, timeout=30)
        w, h, d = out.stdout.strip().split(",")[:3]
        return int(w), int(h), float(d)
    except Exception:
        return None


def _extract_frame(video_path, at_seconds, out_png):
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{at_seconds:.2f}", "-i",
             video_path, "-frames:v", "1", "-q:v", "2", out_png],
            capture_output=True, timeout=60)
        return r.returncode == 0 and os.path.isfile(out_png)
    except Exception:
        return False


def _frame_score(pil_img):
    """Deterministic 'strong frame' score: detailed (high local
    contrast) and neither blown out nor murky."""
    from PIL import ImageStat
    g = pil_img.convert("L").resize((96, 96))
    stat = ImageStat.Stat(g)
    mean, std = stat.mean[0], stat.stddev[0]
    exposure = 1.0 - min(abs(mean - 118.0) / 140.0, 0.9)
    return std * exposure


def _pick_frame(video_path):
    """Extract the candidate frames and return the best PIL image,
    or None when ffmpeg cannot read the video at all."""
    from PIL import Image
    info = _probe(video_path)
    if not info:
        return None
    _, _, duration = info
    best, best_score = None, -1.0
    with tempfile.TemporaryDirectory() as td:
        for i, frac in enumerate(_FRAME_FRACTIONS):
            png = os.path.join(td, f"f{i}.png")
            if not _extract_frame(video_path, max(duration * frac, 0.1),
                                  png):
                continue
            try:
                img = Image.open(png).convert("RGB")
                img.load()
            except Exception:
                continue
            score = _frame_score(img)
            if score > best_score:
                best, best_score = img, score
    return best


def _cover(img, target_w, target_h):
    """Scale-to-cover + centre crop to the exact canvas."""
    from PIL import Image
    scale = max(target_w / img.width, target_h / img.height)
    img = img.resize((round(img.width * scale),
                      round(img.height * scale)), Image.LANCZOS)
    x = (img.width - target_w) // 2
    y = (img.height - target_h) // 2
    return img.crop((x, y, x + target_w, y + target_h))


def _circular_logo(diameter):
    """The Cyrus monogram as a circular badge with a gold ring,
    or None when no logo file exists (the render goes on without
    it — noted in the result)."""
    from PIL import Image, ImageDraw
    path = _first_existing(LOGO_CANDIDATES)
    if not path:
        return None
    try:
        logo = Image.open(path).convert("RGB")
    except Exception:
        return None
    side = min(logo.size)
    logo = logo.crop(((logo.width - side) // 2, (logo.height - side) // 2,
                      (logo.width + side) // 2, (logo.height + side) // 2))
    logo = logo.resize((diameter, diameter), Image.LANCZOS)
    mask = Image.new("L", (diameter, diameter), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse((0, 0, diameter, diameter), fill=255)
    badge = Image.new("RGBA", (diameter, diameter), (0, 0, 0, 0))
    badge.paste(logo, (0, 0), mask)
    ring = max(3, diameter // 26)
    bd = ImageDraw.Draw(badge)
    bd.ellipse((ring // 2, ring // 2, diameter - ring // 2 - 1,
                diameter - ring // 2 - 1), outline=GOLD + (255,),
               width=ring)
    return badge


def _fit_lines(draw, words, font_path, max_size, max_w, max_h):
    """Largest font (≤ max_size) whose wrapped text (≤2 lines)
    fits the box. Returns (font, lines) or None."""
    from PIL import ImageFont
    size = max_size
    while size >= 24:
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
        if len(lines) <= 2:
            widths = [draw.textlength(l, font=font) for l in lines]
            height = sum(draw.textbbox((0, 0), l, font=font)[3]
                         for l in lines) + int(size * 0.18) * (len(lines) - 1)
            if max(widths) <= max_w and height <= max_h:
                return font, lines
        size = int(size * 0.9)
    return None


def render_thumbnail(entry, video_path, out_path, still_path=None):
    """Render the thumbnail for one queue entry.

    Returns {"ok": True, "path":..., "text":..., "logo": bool} or
    an honest failure dict. Pure PIL + ffmpeg — deterministic.
    """
    try:
        from PIL import Image, ImageDraw, ImageEnhance
    except Exception:
        return fail("Pillow is not installed (requirements.txt has it)")
    text = thumbnail_text(entry)
    if not text:
        return fail("entry has no hook/title words for the thumbnail")
    font_path = _first_existing(FONT_CANDIDATES)
    if not font_path:
        return fail("no bold font available for PIL text rendering")

    if still_path:
        try:
            base = Image.open(still_path).convert("RGB")
            base.load()
        except Exception:
            return fail(f"cannot read the supplied still: {still_path}")
    else:
        base = _pick_frame(video_path)
        if base is None:
            return fail(f"ffmpeg could not extract a frame from "
                        f"{video_path}")

    portrait = base.height >= base.width
    target = (1080, 1920) if portrait else (1280, 720)
    img = _cover(base, *target)
    img = ImageEnhance.Color(img).enhance(1.07)
    img = ImageEnhance.Contrast(img).enhance(1.05)
    img = ImageEnhance.Sharpness(img).enhance(1.15)
    img = img.convert("RGBA")
    W, H = img.size

    # Navy band across the bottom, fading in from transparent.
    band_h = int(H * (0.30 if portrait else 0.36))
    band = Image.new("RGBA", (W, band_h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(band)
    for y in range(band_h):
        alpha = int(70 + (245 - 70) * (y / max(band_h - 1, 1)) ** 1.4)
        bd.line([(0, y), (W, y)], fill=NAVY + (alpha,))
    img.alpha_composite(band, (0, H - band_h))

    # Hook text: gold, huge, centred in the band.
    draw = ImageDraw.Draw(img)
    fitted = _fit_lines(draw, text.split(), font_path,
                        max_size=int(W * 0.135),
                        max_w=int(W * 0.92), max_h=int(band_h * 0.74))
    if fitted is None:
        return fail("thumbnail text did not fit the band")
    font, lines = fitted
    line_h = [draw.textbbox((0, 0), l, font=font)[3] for l in lines]
    total_h = sum(line_h) + int(font.size * 0.18) * (len(lines) - 1)
    y = H - band_h + (band_h - total_h) // 2
    for line, lh in zip(lines, line_h):
        x = (W - draw.textlength(line, font=font)) / 2
        draw.text((x, y), line, font=font, fill=GOLD + (255,),
                  stroke_width=max(2, font.size // 16),
                  stroke_fill=NAVY_DARK + (255,))
        y += lh + int(font.size * 0.18)

    # Circular Cyrus logo, top-RIGHT — the finish pipeline already
    # stamps its own circular logo top-left, and the host's face is
    # centre-frame; top-right is the corner that stays clear.
    badge = _circular_logo(int(W * (0.19 if portrait else 0.15)))
    if badge is not None:
        margin = int(W * 0.035)
        img.alpha_composite(badge, (W - margin - badge.width, margin))

    os.makedirs(os.path.dirname(os.path.abspath(out_path)),
                exist_ok=True)
    img.convert("RGB").save(out_path, "JPEG", quality=90)
    return {"ok": True, "path": out_path, "text": text,
            "logo": badge is not None}


def _entry_video(entry, root):
    """The entry's finished video path, or None: `edited_file`
    first (the finish step's file), then the raw `video_path`."""
    rel = str(entry.get("edited_file") or "").strip()
    if rel:
        p = rel if os.path.isabs(rel) else os.path.join(root, rel)
        if os.path.isfile(p):
            return p
    raw = str(entry.get("video_path") or "").strip()
    if raw:
        p = raw if os.path.isabs(raw) else os.path.join(root, raw)
        if os.path.isfile(p):
            return p
    return None


def make_thumbnail(entry, root=REPO_ROOT, out_dir=None, still_path=None):
    """Render one entry's thumbnail and return the result dict
    with `thumbnail_file` set the way `edited_file` is recorded:
    repo-root-relative when the image lands under the root."""
    video = _entry_video(entry, root)
    if not video and not still_path:
        return fail("entry has no video file yet (no edited_file / "
                    "video_path on disk)")
    out_dir = out_dir or os.path.dirname(os.path.abspath(video))
    out_path = os.path.join(out_dir, f"{entry.get('id', 'entry')}"
                                     f"-thumb.jpg")
    r = render_thumbnail(entry, video, out_path, still_path=still_path)
    if not r.get("ok"):
        return r
    try:
        rel = os.path.relpath(out_path, root)
    except Exception:
        rel = out_path
    r["thumbnail_file"] = rel if not rel.startswith("..") else out_path
    return r


def make_missing_thumbnails(queue_path=None, root=REPO_ROOT,
                            out_dir=None):
    """Scan the approval queue: every entry that HAS a finished
    video but NO thumbnail gets one, and its queue entry gains
    `thumbnail_file`. Returns a summary dict; never raises."""
    queue = ApprovalQueue(queue_path)
    made, failed, skipped = [], [], 0
    dirty = False
    for entry in queue.all():
        if entry.get("thumbnail_file"):
            skipped += 1
            continue
        if not _entry_video(entry, root):
            skipped += 1
            continue
        r = make_thumbnail(entry, root=root, out_dir=out_dir)
        if r.get("ok"):
            entry["thumbnail_file"] = r["thumbnail_file"]
            made.append(entry.get("id"))
            dirty = True
        else:
            failed.append({"id": entry.get("id"),
                           "error": r.get("error")})
    if dirty:
        queue._save()
    return {"ok": True, "made": made, "failed": failed,
            "skipped": skipped}


def main(argv):
    entry_id, queue_path, out_dir, still = None, None, None, None
    args = list(argv[1:])
    while args:
        a = args.pop(0)
        if a == "--queue":
            queue_path = args.pop(0)
        elif a == "--out-dir":
            out_dir = args.pop(0)
        elif a == "--still":
            still = args.pop(0)
        elif not a.startswith("--"):
            entry_id = a
    if entry_id:
        queue = ApprovalQueue(queue_path)
        entry, err = queue.find(entry_id)
        if err:
            print(f"🖼️ thumbnail_maker: {err}")
            return 1
        r = make_thumbnail(entry, out_dir=out_dir, still_path=still)
        if not r.get("ok"):
            print(f"🖼️ thumbnail_maker: FAILED for {entry_id}: "
                  f"{r.get('error')}")
            return 1
        entry["thumbnail_file"] = r["thumbnail_file"]
        queue._save()
        print(f"🖼️ thumbnail_maker: {entry_id} -> "
              f"{r['thumbnail_file']} (text: \"{r['text']}\", "
              f"logo: {'yes' if r['logo'] else 'no logo file found'})")
        return 0
    s = make_missing_thumbnails(queue_path=queue_path, out_dir=out_dir)
    print(f"🖼️ thumbnail_maker: made {len(s['made'])} "
          f"({', '.join(s['made']) or '—'}), skipped "
          f"{s['skipped']}, failed {len(s['failed'])}")
    for f in s["failed"]:
        print(f"  - {f['id']}: {f['error']}")
    return 0 if not s["failed"] else 1


THUMBNAIL_MAKER_ROBOT = {"make_thumbnail": make_thumbnail,
                         "make_missing_thumbnails":
                         make_missing_thumbnails}

if __name__ == "__main__":
    sys.exit(main(sys.argv))
