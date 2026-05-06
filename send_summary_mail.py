#!/usr/bin/env python3
"""Send blog summary email via SMTP after auto-generator finishes."""
import os, re, smtplib, ssl, datetime, subprocess
from email.message import EmailMessage
from pathlib import Path

ROOT = Path("/home/student/Projects/gebaeude-digital")
BASE = "https://nichtagentur.github.io/gebaeude-digital/"
TO = "seedorff@s3re.at"
FROM = os.environ.get("SMTP_USER", "i-am-a-user@nichtagentur.at")

HOST = os.environ["SMTP_HOST"]
USER = os.environ["SMTP_USER"]
PASS = os.environ["SMTP_PASS"]


def list_articles():
    """Find all article HTML files (exclude special pages)."""
    skip = {"index.html", "impressum.html", "datenschutz.html",
            "ueber.html", "automation.html"}
    articles = []
    for p in sorted(ROOT.glob("*.html")):
        if p.name in skip:
            continue
        text = p.read_text(encoding="utf-8")
        m = re.search(r"<h1>(.*?)</h1>", text, re.S)
        title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else p.stem
        articles.append((title, p.name))
    return articles


def git_log_summary():
    out = subprocess.run(
        ["git", "-C", str(ROOT), "log", "--oneline", "--no-merges", "-30"],
        capture_output=True, text=True
    )
    return out.stdout.strip()


def build_html(articles, log_excerpt):
    items = "\n".join(
        f'<li><a href="{BASE}{slug}">{title}</a></li>'
        for title, slug in articles
    )
    return f"""<!doctype html>
<html><body style="font-family:-apple-system,Segoe UI,system-ui,sans-serif;color:#14202b;max-width:680px;margin:0 auto;padding:20px;line-height:1.6;">
<h1 style="color:#0a4f7a;border-bottom:2px solid #e3e8ed;padding-bottom:10px;">Gebäude-Digital — Workshop-Demo Zusammenfassung</h1>

<p>Servus Rene,</p>
<p>Der automatisierte Publishing-Lauf vom <strong>{datetime.date.today().strftime('%d. %B %Y')}</strong> ist abgeschlossen. Hier die Übersicht:</p>

<h2 style="color:#0a4f7a;font-size:1.1rem;margin-top:24px;">Live-URLs</h2>
<ul>
  <li><strong>Blog (Startseite):</strong> <a href="{BASE}">{BASE}</a></li>
  <li><strong>Automatisierungs-Präsentation:</strong> <a href="{BASE}automation.html">{BASE}automation.html</a></li>
  <li><strong>GitHub Repository:</strong> <a href="https://github.com/nichtagentur/gebaeude-digital">github.com/nichtagentur/gebaeude-digital</a></li>
  <li><strong>Sitemap:</strong> <a href="{BASE}sitemap.xml">{BASE}sitemap.xml</a></li>
</ul>

<h2 style="color:#0a4f7a;font-size:1.1rem;margin-top:24px;">Veröffentlichte Artikel ({len(articles)})</h2>
<ol>
{items}
</ol>

<h2 style="color:#0a4f7a;font-size:1.1rem;margin-top:24px;">Was passiert ist</h2>
<ul>
  <li>Drei manuell konzipierte Pillar-Artikel (EPBD/CSRD-Regulatorik, Digital-Twin-ROI, BIM·IoT·CAFM-Stack) als Fundament.</li>
  <li>Über 30 Minuten alle 5 Minuten ein zusätzlicher, automatisch generierter Artikel via OpenRouter:
    <ul>
      <li><strong>Text:</strong> google/gemini-2.5-flash-lite (JSON-Mode, ca. 0,1 ¢ pro Artikel)</li>
      <li><strong>Bild:</strong> google/gemini-3.1-flash-image-preview (16:9, ca. 4 ¢ pro Bild)</li>
    </ul>
  </li>
  <li>Ein Artikel mit YouTube-Video-Embed (kuratierte Suche).</li>
  <li>Jeder Artikel inklusive Schema.org JSON-LD (Article, BreadcrumbList, FAQPage), OpenGraph, Canonical, Lazy-Loading.</li>
  <li>Index-Seite und Sitemap werden bei jedem Lauf automatisch aktualisiert; jede Iteration endet mit <code>git push</code>.</li>
</ul>

<h2 style="color:#0a4f7a;font-size:1.1rem;margin-top:24px;">Geschätzte Modellkosten</h2>
<p>Sechs Artikel × ca. 4,1 Cent Bild + Token-Kosten: <strong>≈ 0,25 €</strong> Gesamtkosten für den 30-Minuten-Lauf. Hosting: GitHub Pages (kostenlos).</p>

<h2 style="color:#0a4f7a;font-size:1.1rem;margin-top:24px;">Git-Log (Auszug)</h2>
<pre style="background:#f5f7f9;padding:12px 16px;border-left:3px solid #0a4f7a;font-family:Menlo,Consolas,monospace;font-size:.85rem;line-height:1.5;overflow-x:auto;">{log_excerpt}</pre>

<h2 style="color:#0a4f7a;font-size:1.1rem;margin-top:24px;">E-E-A-T-Hinweise</h2>
<ul>
  <li>Demo-Hinweis-Banner auf jeder Seite — keine Täuschung.</li>
  <li>KI-generierte Artikel sind als solche gekennzeichnet (Autorenbox + Banner).</li>
  <li>Prompt verbietet erfundene Quotes/Studien; Quellenhinweise nur generisch.</li>
  <li>Bandbreiten („15–22 %") statt scheingenauer Punktwerte erzwungen.</li>
</ul>

<p style="margin-top:32px;color:#5a6b7a;font-size:.9rem;">Diese Mail wurde automatisch versendet vom Workshop-Demo-Setup.<br>
AI Computer Use Workshop Wien · 6. Mai 2026</p>
</body></html>"""


def main():
    articles = list_articles()
    log = git_log_summary()
    body_html = build_html(articles, log)

    msg = EmailMessage()
    msg["Subject"] = f"[Gebäude-Digital] Auto-Publishing-Lauf abgeschlossen — {len(articles)} Artikel live"
    msg["From"] = FROM
    msg["To"] = TO
    msg.set_content(
        f"Workshop-Demo abgeschlossen. {len(articles)} Artikel live unter {BASE} . "
        f"Volldetails: HTML-Version dieser Mail."
    )
    msg.add_alternative(body_html, subtype="html")

    with smtplib.SMTP(HOST, 587) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(USER, PASS)
        s.send_message(msg)
    print(f"sent to {TO} via {HOST} ({len(articles)} articles)")


if __name__ == "__main__":
    main()
