"""ULTIMATE ROBOT TEAM — robots/image_maker.py

REAL AI image creation for post visuals.

Pipeline — two real AI calls, both through the Google Gemini API:
  1. gemini-2.5-flash writes a detailed ENGLISH, photorealistic,
     cinematic prompt from the post text.
  2. Imagen (imagen-3.0-generate-002) renders one 1:1 PNG, saved
     locally to output_path.

Credentials come ONLY from the environment:
    GEMINI_API_KEY

make_post_image(post_text, output_path) returns:
    {"ok": True, "path": <local file>, "prompt": <english prompt>}
        only when the image was really generated and saved.
    {"ok": False, "reason": ...}
        honest skip (no key / library missing) or the REAL API error.

Never raises. Never prints or logs the key.

HONEST NOTE — Imagen billing: generating images through the Gemini
API (Imagen 3) typically requires a BILLING-ENABLED API key. A plain
free key often answers with a permission/billing error. That real
error is surfaced in the returned dict (never hidden, never faked as
success) so you know exactly what to fix. See README for details.
"""

import os


def _client():
    key = (os.environ.get("GEMINI_API_KEY") or "").strip()
    if not key:
        return None, "GEMINI_API_KEY not set"
    try:
        from google import genai
    except ImportError:
        return None, "google-genai library not installed (pip install google-genai)"
    try:
        return genai.Client(api_key=key), None
    except Exception as e:
        return None, f"could not create Gemini client: {type(e).__name__}: {e}"


def make_post_image(post_text, output_path="temp_image.png"):
    """Generate a 1:1 PNG visual for the post. Real work or honest
    failure — never raises."""
    client, problem = _client()
    if client is None:
        return {"ok": False, "skipped": True,
                "reason": f"image generation skipped — {problem}; "
                          "nothing was created"}

    try:
        # 1. English image prompt from the post (real AI call)
        prompt_resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                "Based on this instagram post, write a highly detailed, "
                "photorealistic, cinematic prompt in English for an AI image "
                "generator. The image should be vibrant, natural, and perfect "
                "for an outdoor adventure Instagram page. "
                "Return ONLY the english prompt:\n\n" + post_text
            ),
        )
        image_prompt = (prompt_resp.text or "").strip()
        if not image_prompt:
            return {"ok": False,
                    "reason": "Gemini returned an empty image prompt"}

        # 2. Render with Imagen 3 (real API call)
        from google.genai import types
        result = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=image_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="1:1",
            ),
        )
        images = getattr(result, "generated_images", None) or []
        if not images:
            return {"ok": False,
                    "reason": "Imagen returned no images",
                    "prompt": image_prompt}
        images[0].image.save(output_path)
        return {"ok": True, "path": output_path, "prompt": image_prompt}

    except Exception as e:  # never raise; report the REAL error
        return {"ok": False,
                "error": f"{type(e).__name__}: {e}",
                "note": ("If this mentions billing/permission, the Gemini "
                         "key needs billing enabled for Imagen — see README.")}
