# Gebäude-Digital

Workshop-Demo-Blog zur Gebäudedigitalisierung im DACH-Raum. Statische Site, gehostet auf GitHub Pages.

**Live:** https://nichtagentur.github.io/gebaeude-digital/

Drei Hauptartikel:

1. [Warum Gebäudedigitalisierung 2026 keine Option mehr ist](warum-gebaeude-digitalisieren-2026.html) — EPBD, CSRD, ETS 2.
2. [Digitaler Zwilling im Bestandsbau: ROI in 18 Monaten](digitaler-zwilling-bestandsbau-roi.html) — Wirtschaftlichkeitsrechnung.
3. [BIM, IoT, CAFM: Welche Technologie-Schicht zuerst?](bim-iot-cafm-technologie-stack.html) — Stack-Vergleich und Reihenfolge.

## Tech

- Reines HTML5 + ein `style.css`, kein Build, kein Framework.
- Schema.org JSON-LD (Article, BreadcrumbList, FAQPage, Organization, Person).
- Hero-Bilder via Google Gemini 3.1 Flash Image (OpenRouter), siehe `generate_images.py`.
- E-E-A-T-konform: Autor + Kontakt + Demo-Hinweis sichtbar, keine Täuschung.

## Lokal testen

```bash
google-chrome ~/Projects/gebaeude-digital/index.html
```

## Bilder regenerieren

```bash
source ~/.env && python3 generate_images.py [key]
```
