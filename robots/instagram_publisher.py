"""ULTIMATE ROBOT TEAM — robots/instagram_publisher.py

REAL Instagram publishing via the official Meta Graph API
(two-step photo flow):

  1. POST https://graph.facebook.com/v21.0/{ig_user_id}/media
     with image_url + caption + access_token   -> creation id
  2. Poll GET /{creation_id}?fields=status_code until the container is
     FINISHED (up to ~60s — a real status check, not a blind sleep)
  3. POST https://graph.facebook.com/v21.0/{ig_user_id}/media_publish
     with creation_id + access_token            -> real post id

Credentials come ONLY from the environment:
    IG_ACCESS_TOKEN   (Meta token with instagram_content_publish)
    IG_USER_ID        (the Instagram business/creator account id)

=====================================================================
CRITICAL — READ THIS BEFORE CALLING publish():

Instagram does NOT accept a local file path. image_url MUST be a
PUBLIC https URL — Meta's own servers fetch the image from it.
A local path ("temp_image.png", "/home/...", "file://...") is REFUSED
with a clear error BEFORE any network call. The missing bridge is
uploading the generated image somewhere public first — see README
"The public-URL bridge" for the concrete approach. This module never
auto-uploads anything anywhere without Cyrus's approval.
=====================================================================

publish(image_url, caption) returns:
    {"ok": True, "post_id": ...}
        ONLY when Meta really published the post.
    {"ok": False, "skipped": True, "reason": ...}
        clean skip (no token / no user id / local path refused).
    {"ok": False, "error": ...}
        the REAL Graph API error, surfaced — never faked as success.

Never raises. Never prints or logs the token.
"""

import os
import time

import requests

_API = "https://graph.facebook.com/v21.0"
_POLL_TIMEOUT_S = 60
_POLL_INTERVAL_S = 5


def _looks_public_url(value):
    v = (value or "").strip()
    return v.startswith("https://") and " " not in v


def publish(image_url, caption, token=None, ig_user_id=None):
    """Publish a photo post to Instagram. Real work or honest failure —
    never raises."""
    token = (token if token is not None
             else os.environ.get("IG_ACCESS_TOKEN", "")).strip()
    ig_user_id = (ig_user_id if ig_user_id is not None
                  else os.environ.get("IG_USER_ID", "")).strip()
    image_url = (image_url or "").strip()

    # --- hard refusal: Instagram cannot fetch a local file ---
    if not _looks_public_url(image_url):
        return {"ok": False, "skipped": True,
                "reason": (
                    "refused: image_url must be a PUBLIC https URL — "
                    f"got {image_url!r}. Instagram's servers fetch the image "
                    "themselves, so a local file path can never work. "
                    "Upload the image somewhere public first (see README "
                    "'The public-URL bridge'), then pass that URL.")}

    if not token or not ig_user_id:
        return {"ok": False, "skipped": True,
                "reason": ("IG_ACCESS_TOKEN / IG_USER_ID not set — "
                           "publish skipped, nothing was sent")}

    try:
        # 1. create the media container
        r = requests.post(
            f"{_API}/{ig_user_id}/media",
            data={"image_url": image_url, "caption": caption,
                  "access_token": token},
            timeout=30,
        )
        data = r.json()
        creation_id = data.get("id")
        if not creation_id:
            return {"ok": False,
                    "error": f"Graph API refused the media container: {data}"}

        # 2. poll the container status until FINISHED (real check)
        deadline = time.time() + _POLL_TIMEOUT_S
        status = None
        while time.time() < deadline:
            s = requests.get(
                f"{_API}/{creation_id}",
                params={"fields": "status_code",
                        "access_token": token},
                timeout=30,
            ).json()
            status = (s.get("status_code") or "").upper()
            if status == "FINISHED":
                break
            if status in ("ERROR", "EXPIRED"):
                return {"ok": False,
                        "error": ("media container failed on Meta's side: "
                                  f"{s}")}
            time.sleep(_POLL_INTERVAL_S)
        if status != "FINISHED":
            return {"ok": False,
                    "error": (f"media container not ready after "
                              f"{_POLL_TIMEOUT_S}s (last status: {status})")}

        # 3. publish the container
        p = requests.post(
            f"{_API}/{ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": token},
            timeout=30,
        )
        pdata = p.json()
        post_id = pdata.get("id")
        if post_id:
            return {"ok": True, "post_id": post_id,
                    "creation_id": creation_id}
        return {"ok": False,
                "error": f"Graph API refused to publish: {pdata}"}

    except Exception as e:  # never raise; report the real error
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
