#!/usr/bin/env python3
"""
AI image generator via Gemini Flash Image on OpenRouter.

Usage:
    cp this file into <project>/generate_images.py
    Edit PROMPTS dict: { "key": "prompt", ... }
    source ~/.env && python3 generate_images.py [key1 key2 ...]

Saves images to <project>/photos/<key>.{jpg|png}.
Requires OPENROUTER_API_KEY in env.
"""
import base64, json, os, sys, urllib.request, urllib.error
from pathlib import Path

KEY = os.environ.get("OPENROUTER_API_KEY")
if not KEY:
    sys.exit("Missing OPENROUTER_API_KEY (source ~/.env first)")

OUT = Path(__file__).parent / "assets" / "img"
OUT.mkdir(parents=True, exist_ok=True)

# ============================================================
# EDIT THIS DICT for each project.
# Keys become filenames (no extension). Values are the prompts.
# Recommended structure: shared style DNA + specific subject per key.
# ============================================================

STYLE = (
    "premium editorial architectural photography, photorealistic, natural daylight, "
    "cool blue-grey palette with subtle warm highlights, restrained semi-transparent "
    "data overlays (thin lines, small data points, subtle wireframe contours) integrated "
    "naturally onto real architecture, no people, no faces, no text, no logos, no watermarks, "
    "no cyberpunk cliches, no plastic glow, shallow depth of field where appropriate, "
    "shot on full-frame DSLR, 35mm or 50mm lens, 16:9 aspect ratio, ultra high detail"
)

PROMPTS = {
    "hero-home": (
        "Wide editorial photograph of a modern Central European city skyline at golden hour, "
        "mix of contemporary office buildings and classic Gründerzeit facades, "
        "very subtle holographic data points and thin connecting lines hovering above the rooftops, "
        "shot from a slightly elevated angle, atmospheric haze, " + STYLE
    ),
    "hero-warum": (
        "Editorial architectural photograph of a modern glass-and-stone office building in DACH region "
        "(Vienna or Zurich aesthetic), facade reflecting soft afternoon sky, "
        "discrete energy and sensor data points faintly overlaid on windows, "
        "low angle composition, " + STYLE
    ),
    "hero-zwilling": (
        "Editorial split composition: on the left a real photograph of a Gründerzeit residential "
        "building facade in Vienna, on the right the same building rendered as a clean 3D wireframe "
        "digital twin against a neutral studio background, seamless transition in the middle, "
        "soft daylight, " + STYLE
    ),
    "hero-stack": (
        "Editorial photograph of a modern building control room or technical facility management "
        "workspace, large monitors showing abstract floor plans and sensor dashboards "
        "(no readable text), tablet on desk in foreground, blurred ventilation and HVAC "
        "infrastructure in background, cool industrial daylight from above, " + STYLE
    ),
}

# ============================================================

MODEL = "google/gemini-3.1-flash-image-preview"
API = "https://openrouter.ai/api/v1/chat/completions"


def gen(name: str, prompt: str) -> Path:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
    }).encode()

    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "ai-images skill",
    })
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code}: {e.read().decode()[:400]}", file=sys.stderr)
        raise

    msg = data["choices"][0]["message"]
    images = msg.get("images") or []
    if not images:
        print(f"  no images in response. content={msg.get('content','')[:200]}", file=sys.stderr)
        raise RuntimeError("no image returned")

    img_url = images[0]["image_url"]["url"]
    if not img_url.startswith("data:"):
        raise RuntimeError(f"unexpected image url: {img_url[:100]}")
    header, b64 = img_url.split(",", 1)
    ext = "png" if "png" in header else "jpg"
    out = OUT / f"{name}.{ext}"
    out.write_bytes(base64.b64decode(b64))
    return out


if __name__ == "__main__":
    if not PROMPTS:
        sys.exit("PROMPTS dict is empty — edit this file before running.")

    targets = sys.argv[1:] or list(PROMPTS.keys())
    for name in targets:
        if name not in PROMPTS:
            print(f"skip unknown key: {name}")
            continue
        print(f"generating {name}...", flush=True)
        try:
            p = gen(name, PROMPTS[name])
            print(f"  -> {p} ({p.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"  FAILED: {e}")
