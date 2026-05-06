#!/usr/bin/env python3
"""Automated article generator for Gebäude-Digital.
Runs N topics, one every INTERVAL seconds, pushes to GitHub each time."""
import json, os, sys, time, base64, subprocess, datetime, urllib.request, urllib.error, html, re
from pathlib import Path

KEY = os.environ["OPENROUTER_API_KEY"]
ROOT = Path("/home/student/Projects/gebaeude-digital")
LOG = ROOT / "auto-articles.log"

TEXT_MODEL = "google/gemini-2.5-flash-lite"
IMAGE_MODEL = "google/gemini-3.1-flash-image-preview"
API = "https://openrouter.ai/api/v1/chat/completions"

INTERVAL = int(os.environ.get("INTERVAL", "300"))  # seconds between articles

TOPICS = [
    {"slug": "predictive-maintenance-ki-facility-management",
     "title": "Predictive Maintenance mit KI im Facility Management",
     "kw": "Predictive Maintenance Gebäude",
     "tag": "Operations",
     "video_query": "Predictive Maintenance Building Facility Management"},
    {"slug": "lorawan-submetering-praxis-guide",
     "title": "LoRaWAN für Gebäude-Submetering: Praxis-Guide",
     "kw": "LoRaWAN Gebäude Submetering",
     "tag": "Technik"},
    {"slug": "iso-50001-energiemanagement-2026",
     "title": "ISO 50001: Was sich 2026 für Gebäudebetreiber ändert",
     "kw": "ISO 50001 Gebäude Energiemanagement 2026",
     "tag": "Norm"},
    {"slug": "co2-bilanz-quadratmeter-benchmark-dach",
     "title": "CO2-Bilanz pro Quadratmeter: Benchmark im DACH-Raum",
     "kw": "CO2 Bilanz Gebäude Benchmark DACH",
     "tag": "ESG"},
    {"slug": "smart-meter-rollout-oesterreich-2026",
     "title": "Smart Meter Rollout in Österreich: Stand 2026",
     "kw": "Smart Meter Österreich 2026",
     "tag": "Markt"},
    {"slug": "mieterstrom-modelle-digitale-abrechnung",
     "title": "Mieterstrom-Modelle: Digitale Abrechnung im Bestand",
     "kw": "Mieterstrom digitale Abrechnung",
     "tag": "Recht"},
]

BASE_URL = "https://nichtagentur.github.io/gebaeude-digital/"


def log(msg):
    t = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{t}] {msg}\n"
    sys.stdout.write(line); sys.stdout.flush()
    with open(LOG, "a") as f:
        f.write(line)


def call_text(prompt):
    body = {
        "model": TEXT_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read())
    return data["choices"][0]["message"]["content"]


def call_image(prompt: str, out_path: Path):
    body = {
        "model": IMAGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "modalities": ["image", "text"],
    }
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = json.loads(r.read())
    images = data["choices"][0]["message"].get("images") or []
    if not images:
        raise RuntimeError("no image returned")
    img_url = images[0]["image_url"]["url"]
    _, b64 = img_url.split(",", 1)
    out_path.write_bytes(base64.b64decode(b64))


def parse_json_loose(raw: str):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z]*\n", "", raw)
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def render_section(s: dict) -> str:
    parts = [f"<h2>{esc(s['h2'])}</h2>"]
    for p in s.get("paragraphs", []):
        parts.append(f"<p>{esc(p)}</p>")
    items = s.get("list") or []
    if items:
        parts.append("<ul>" + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>")
    return "\n".join(parts)


def render_faq(faq: list) -> str:
    rows = []
    for f in faq:
        rows.append(
            f"<details><summary>{esc(f['q'])}</summary><p>{esc(f['a'])}</p></details>"
        )
    return "\n".join(rows)


def build_html(topic, data, video_query=None) -> str:
    title = data["title"]
    desc = data["meta_description"]
    url = BASE_URL + f"{topic['slug']}.html"
    img_url = BASE_URL + f"assets/img/hero-{topic['slug']}.jpg"
    today = datetime.date.today().isoformat()

    sections_html = "\n".join(render_section(s) for s in data["sections"])
    faq_html = render_faq(data["faq"])

    video_block = ""
    if video_query:
        from urllib.parse import quote
        embed_src = f"https://www.youtube-nocookie.com/embed?listType=search&list={quote(video_query)}"
        video_block = f"""
<h2>Video zum Thema</h2>
<p>Kuratierte YouTube-Suche zum Stichwort &quot;{esc(video_query)}&quot; — eingebettet, externe Inhalte:</p>
<div style="position:relative;padding-bottom:56.25%;height:0;overflow:hidden;border-radius:10px;box-shadow:0 1px 2px rgba(20,32,43,.04),0 8px 24px rgba(20,32,43,.06);margin:24px 0;">
<iframe src="{embed_src}" style="position:absolute;top:0;left:0;width:100%;height:100%;border:0;" allowfullscreen referrerpolicy="strict-origin-when-cross-origin" loading="lazy" title="YouTube Suche: {esc(video_query)}"></iframe>
</div>
"""

    faq_jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f["q"],
             "acceptedAnswer": {"@type": "Answer", "text": f["a"]}}
            for f in data["faq"]
        ]
    }, ensure_ascii=False)

    article_jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "Article",
        "mainEntityOfPage": url,
        "headline": title,
        "description": desc,
        "image": [img_url],
        "datePublished": today, "dateModified": today,
        "inLanguage": "de-AT",
        "author": {"@type": "Person", "name": "Rene Seedorff", "email": "seedorff@s3re.at"},
        "publisher": {"@type": "Organization", "name": "Gebäude-Digital (Workshop-Demo)"},
        "keywords": topic["kw"],
    }, ensure_ascii=False)

    breadcrumb_jsonld = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Startseite", "item": BASE_URL},
            {"@type": "ListItem", "position": 2, "name": title, "item": url},
        ]
    }, ensure_ascii=False)

    return f"""<!doctype html>
<html lang="de-AT">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | Gebäude-Digital</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
<link rel="stylesheet" href="assets/css/style.css">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:locale" content="de_AT">
<meta property="og:image" content="{img_url}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{article_jsonld}</script>
<script type="application/ld+json">{breadcrumb_jsonld}</script>
<script type="application/ld+json">{faq_jsonld}</script>
</head>
<body>
<div class="demo-notice">Workshop-Demo — automatisch generierter Artikel ({today}). Inhalte zur Veranschaulichung, keine Beratung.</div>
<header class="site-header">
  <div class="site-header-inner">
    <a class="brand" href="./">Gebäude<span>·Digital</span></a>
    <nav class="site-nav" aria-label="Hauptnavigation">
      <a href="./">Startseite</a>
      <a href="warum-gebaeude-digitalisieren-2026.html">Warum jetzt</a>
      <a href="digitaler-zwilling-bestandsbau-roi.html">Digitaler Zwilling</a>
      <a href="bim-iot-cafm-technologie-stack.html">BIM·IoT·CAFM</a>
      <a href="ueber.html">Über</a>
    </nav>
  </div>
</header>
<main>
<article>
  <h1>{esc(title)}</h1>
  <p class="meta">
    <span>Von <a rel="author" href="ueber.html">Rene Seedorff</a></span>
    <span><time datetime="{today}">{today}</time></span>
    <span>Tag: {esc(topic['tag'])}</span>
    <span>Auto-generiert (Workshop-Demo)</span>
  </p>
  <img class="hero-img" src="assets/img/hero-{esc(topic['slug'])}.jpg" alt="Symbolbild zum Thema {esc(topic['kw'])}" width="1600" height="900" loading="eager" fetchpriority="high">

  <section class="tldr">
    <h2>TL;DR</h2>
    <p>{esc(data['tldr'])}</p>
  </section>

  <p>{esc(data['lede'])}</p>

  {sections_html}
  {video_block}

  <section class="faq">
    <h2>Häufige Fragen</h2>
    {faq_html}
  </section>

  <section class="related">
    <h2>Weiterlesen</h2>
    <ul>
      <li><a href="warum-gebaeude-digitalisieren-2026.html">Warum Gebäudedigitalisierung 2026 keine Option mehr ist</a></li>
      <li><a href="digitaler-zwilling-bestandsbau-roi.html">Digitaler Zwilling im Bestandsbau: ROI in 18 Monaten</a></li>
      <li><a href="bim-iot-cafm-technologie-stack.html">BIM, IoT, CAFM: Welche Technologie-Schicht zuerst?</a></li>
    </ul>
  </section>

  <section class="author">
    <div class="author-avatar">RS</div>
    <div class="author-body">
      <p><strong>Rene Seedorff</strong> <span class="role">· Autor (Workshop-Demo, KI-unterstützt)</span></p>
      <p>Dieser Artikel wurde automatisiert mit Google Gemini 2.5 Flash Lite (Text) und Gemini 3.1 Flash Image (Bild) erzeugt und redaktionell freigegeben. Kontakt: <a href="mailto:seedorff@s3re.at">seedorff@s3re.at</a>.</p>
    </div>
  </section>
</article>
</main>
<footer class="site-footer">
  <div class="site-footer-inner">
    <div>© 2026 Gebäude-Digital · Workshop-Demo</div>
    <nav>
      <a href="ueber.html">Über</a> ·
      <a href="impressum.html">Impressum</a> ·
      <a href="datenschutz.html">Datenschutz</a>
    </nav>
  </div>
</footer>
</body>
</html>
"""


def update_index(topic, data):
    """Insert a card for the new article into index.html cards grid."""
    idx = ROOT / "index.html"
    page = idx.read_text(encoding="utf-8")
    card = f"""    <article class="card">
      <a href="{topic['slug']}.html"><img src="assets/img/hero-{topic['slug']}.jpg" alt="Symbolbild {esc(topic['kw'])}" width="1600" height="900" loading="lazy"></a>
      <div class="card-body">
        <div class="card-tag">Auto · {esc(topic['tag'])}</div>
        <h2><a href="{topic['slug']}.html">{esc(data['title'])}</a></h2>
        <p>{esc(data['meta_description'])}</p>
        <span class="more">Artikel lesen →</span>
      </div>
    </article>

  </div>"""
    if "</div>\n\n  <section class=\"author\">" in page:
        page = page.replace("  </div>\n\n  <section class=\"author\">",
                            card + "\n\n  <section class=\"author\">", 1)
    else:
        page = page.replace("  </div>", card, 1)
    idx.write_text(page, encoding="utf-8")


def update_sitemap(topic):
    sm = ROOT / "sitemap.xml"
    text = sm.read_text(encoding="utf-8")
    today = datetime.date.today().isoformat()
    new_url = (f"  <url><loc>{BASE_URL}{topic['slug']}.html</loc>"
               f"<lastmod>{today}</lastmod><changefreq>monthly</changefreq>"
               f"<priority>0.8</priority></url>\n")
    if topic['slug'] not in text:
        text = text.replace("</urlset>", new_url + "</urlset>")
        sm.write_text(text, encoding="utf-8")


def git_publish(slug):
    subprocess.run(["git", "-C", str(ROOT), "add", "."], check=True)
    subprocess.run(["git", "-C", str(ROOT), "commit", "-q", "-m",
                    f"auto: add article {slug}"], check=True)
    subprocess.run(["git", "-C", str(ROOT), "push", "-q"], check=True)


def gen_one(topic):
    log(f"START {topic['slug']}")
    prompt = f"""Du bist Fachjournalist:in für Gebäudedigitalisierung im DACH-Raum.
Schreibe einen tiefgehenden, präzisen Fachartikel auf Deutsch (de-AT) zum Thema:
"{topic['title']}"

Hauptkeyword: {topic['kw']}
Zielgruppe: B2B (Bauherren, Asset Manager, Facility Manager).
Tonalität: nüchtern, präzise, mit konkreten Bandbreiten und Beispielzahlen statt scheingenauer Werte.
Länge: 800–1200 Wörter Fließtext insgesamt verteilt auf die Sections.
E-E-A-T: keine erfundenen Quotes, keine Fake-Studien, Quellenhinweise nur generisch (z.B. "Studienergebnisse von Fraunhofer", "dena-Studien").

Liefere ausschließlich gültiges JSON, keine Code-Fences, kein Kommentar:
{{
  "title": "Artikel-Titel max 65 Zeichen, Hauptkeyword vorne",
  "meta_description": "150-160 Zeichen, CTR-orientiert",
  "tldr": "1 Absatz, 2-4 Sätze",
  "lede": "Einleitungs-Absatz, 2-3 Sätze",
  "sections": [
    {{"h2": "Sektionstitel", "paragraphs": ["Absatz 1", "Absatz 2"], "list": ["Punkt", "Punkt"]}}
  ],
  "faq": [
    {{"q": "Frage", "a": "Antwort"}}
  ]
}}
- 4-6 sections, manche mit list, manche ohne (list optional)
- 3-5 FAQ-Einträge
- Alle Texte als reine Strings, keine HTML-Tags innerhalb."""
    raw = call_text(prompt)
    data = parse_json_loose(raw)

    img_prompt = (
        f"Editorial architectural photograph illustrating the topic '{topic['title']}' "
        f"in a Central European DACH context, photorealistic, natural daylight, "
        f"cool blue-grey palette with subtle warm highlights, restrained semi-transparent "
        f"data overlay (thin lines, small data points) integrated subtly, "
        f"no people, no faces, no text, no logos, no watermarks, no cyberpunk cliches, "
        f"premium editorial photography, 16:9 aspect ratio, ultra high detail."
    )
    img_path = ROOT / "assets" / "img" / f"hero-{topic['slug']}.jpg"
    call_image(img_prompt, img_path)
    log(f"  image: {img_path.name} ({img_path.stat().st_size//1024} KB)")

    video_q = topic.get("video_query")
    page = build_html(topic, data, video_query=video_q)
    (ROOT / f"{topic['slug']}.html").write_text(page, encoding="utf-8")
    log(f"  html: {topic['slug']}.html")

    update_index(topic, data)
    update_sitemap(topic)
    git_publish(topic['slug'])
    log(f"  pushed {topic['slug']}  title='{data['title'][:60]}'")


def main():
    log(f"=== auto-generator start, INTERVAL={INTERVAL}s, topics={len(TOPICS)} ===")
    start = time.time()
    for i, topic in enumerate(TOPICS):
        target = start + i * INTERVAL
        wait = target - time.time()
        if wait > 0:
            log(f"sleeping {int(wait)}s before topic {i+1}/{len(TOPICS)}")
            time.sleep(wait)
        try:
            gen_one(topic)
        except Exception as e:
            log(f"  FAILED {topic['slug']}: {type(e).__name__}: {e}")
    log("=== auto-generator done ===")


if __name__ == "__main__":
    main()
