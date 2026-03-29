from __future__ import annotations

from collections import Counter

from .models import Lead
from .utils import directory_url, html_escape, tel_href


TRADE_CONFIGS = {
    "plumber": {
        "label": "Plumber",
        "headline": "Reliable plumbing help for __CITY__ homes and businesses",
        "description": "Fast repair, drain, fixture, and emergency plumbing work with clear pricing and direct phone-first service.",
        "primary": "#0f2d55",
        "accent": "#e8401c",
        "light": "#e8f0f8",
        "hero_image": "https://loremflickr.com/1600/900/plumber,plumbing?lock=101",
        "gallery": [
            ("https://loremflickr.com/800/600/plumbing,pipe,repair?lock=103", "Pipe repair and diagnostics"),
            ("https://loremflickr.com/800/600/plumbing,tools?lock=104", "Professional plumbing tools"),
            ("https://loremflickr.com/800/600/bathroom,faucet,plumbing?lock=105", "Fixture installation and repair"),
        ],
        "services": [
            ("Leak detection", "Fast diagnosis for active leaks, hidden moisture, and recurring water issues."),
            ("Drain cleaning", "Kitchen, bathroom, and main-line drain clearing without the runaround."),
            ("Fixture installs", "Toilets, faucets, garbage disposals, and replacement hardware done cleanly."),
        ],
        "faq": [
            ("Do you handle same-day plumbing work?", "Yes. The page is designed to pitch same-day scheduling and direct phone contact."),
            ("What kinds of jobs do you highlight?", "Emergency plumbing, repairs, drain cleaning, leak detection, and fixture replacements."),
            ("Why make the page phone-first?", "The fastest path to revenue for this kind of outreach is getting a business owner to imagine immediate inbound calls."),
        ],
    },
    "landscaper": {
        "label": "Landscaper",
        "headline": "Clean, credible landscaping pages ready for __CITY__ lead outreach",
        "description": "A polished page focused on lawn care, landscape upkeep, design work, and dependable local service for homeowners.",
        "primary": "#1a3d1a",
        "accent": "#4caf50",
        "light": "#edf5ed",
        "hero_image": "https://loremflickr.com/1600/900/landscaping,lawn?lock=201",
        "gallery": [
            ("https://loremflickr.com/800/600/lawn,mowing?lock=202", "Lawn care and edging"),
            ("https://loremflickr.com/800/600/landscaping,garden?lock=203", "Landscape design and planting"),
            ("https://loremflickr.com/800/600/autumn,leaves,yard?lock=204", "Seasonal cleanup and yard maintenance"),
        ],
        "services": [
            ("Routine maintenance", "Recurring mowing, trimming, cleanup, and property care presented as dependable ongoing service."),
            ("Landscape upgrades", "Beds, plants, mulch, pathways, and curb-appeal improvements that feel premium but approachable."),
            ("Seasonal cleanup", "Storm cleanup, leaf removal, refresh work, and prep for the next season."),
        ],
        "faq": [
            ("Can the page work for small lawn crews?", "Yes. The template is intentionally simple and local so solo operators and small teams still look established."),
            ("Does it only fit mowing companies?", "No. It also works for landscape design, cleanup, hardscape, and general yard service businesses."),
            ("What makes this pitch stronger?", "You can show the owner a finished page built around their business before they spend anything."),
        ],
    },
    "water_heater_repair": {
        "label": "Water Heater Repair",
        "headline": "Conversion-focused pages for water heater and HVAC-style service leads in __CITY__",
        "description": "Built for repair-heavy categories where trust, urgency, and phone calls matter more than a complicated website.",
        "primary": "#4d2c1d",
        "accent": "#ff7a18",
        "light": "#fff2e8",
        "hero_image": "https://loremflickr.com/1600/900/water,heater?lock=301",
        "gallery": [
            ("https://loremflickr.com/800/600/water,heater?lock=302", "Water heater installation and service"),
            ("https://loremflickr.com/800/600/plumbing,pipe?lock=303", "System diagnostics and repair"),
            ("https://loremflickr.com/800/600/plumber,repair,service?lock=304", "In-home repair service"),
        ],
        "services": [
            ("Water heater repair", "Emergency fixes, pilot issues, leaks, and inconsistent hot-water problems."),
            ("Replacement installs", "Positioned for tank and tankless replacement estimates and consults."),
            ("Maintenance and tune-ups", "Flushes, inspections, and performance checks that feel proactive and trustworthy."),
        ],
        "faq": [
            ("Why is HVAC included in this template family?", "In your existing repo, heating and cooling style businesses are grouped alongside water heater repair leads."),
            ("Does the page only mention water heaters?", "No. The copy can support heating, cooling, and adjacent home-service offers without changing the structure."),
            ("What is the main sales angle?", "A finished website that makes an owner look established immediately and gives them a simple phone CTA."),
        ],
    },
    "local_service": {
        "label": "Local Service",
        "headline": "A ready-to-pitch local business website for __CITY__",
        "description": "A simple trust-building service page you can use when the business does not fit one of the main trade templates yet.",
        "primary": "#243447",
        "accent": "#2d9cdb",
        "light": "#edf4fb",
        "hero_image": "https://loremflickr.com/1600/900/small-business,service?lock=401",
        "gallery": [
            ("https://loremflickr.com/800/600/service,team?lock=402", "Local service team at work"),
            ("https://loremflickr.com/800/600/home,service?lock=403", "On-site service and support"),
            ("https://loremflickr.com/800/600/local,business?lock=404", "Professional local business presentation"),
        ],
        "services": [
            ("Local service calls", "A flexible section for the business's core local offer."),
            ("On-site estimates", "Copy that supports phone outreach and quick estimate requests."),
            ("Customer follow-up", "Language that positions the business as responsive and easy to reach."),
        ],
        "faq": [
            ("Can I use this when trade detection is unclear?", "Yes. It is the fallback template for leads that need a polished page before being manually categorized."),
            ("Will the colors change by business?", "The generator uses the trade family theme, or this neutral default if no better match exists."),
            ("Is the page meant to be perfect?", "No. It is meant to be strong enough to support outreach and demonstrate value immediately."),
        ],
    },
}


BUSINESS_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>__TITLE__</title>
  <meta name="description" content="__META_DESCRIPTION__">
  <meta property="og:type" content="website">
  <meta property="og:title" content="__TITLE__">
  <meta property="og:description" content="__META_DESCRIPTION__">
  <meta property="og:site_name" content="__BUSINESS_NAME__">
  <meta name="theme-color" content="__PRIMARY__">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "__JSON_NAME__",
    "telephone": "__JSON_PHONE__",
    "address": {
      "@type": "PostalAddress",
      "addressLocality": "__JSON_CITY__",
      "addressRegion": "__JSON_STATE__",
      "addressCountry": "US"
    },
    "areaServed": "__JSON_CITY__",
    "url": "__JSON_URL__"
  }
  </script>
  <style>
    :root{
      --primary: __PRIMARY__;
      --accent: __ACCENT__;
      --light: __LIGHT__;
      --text: #17202a;
      --muted: #4f5b67;
      --white: #ffffff;
      --border: #e5e7eb;
      --radius: 16px;
      --shadow: 0 16px 50px rgba(0,0,0,0.08);
    }
    *{box-sizing:border-box;margin:0;padding:0}
    html{scroll-behavior:smooth}
    body{font-family:Segoe UI,Arial,sans-serif;color:var(--text);background:#fff;line-height:1.6}
    a{text-decoration:none;color:inherit}
    img{display:block;width:100%;height:auto}
    header{
      position:sticky;top:0;z-index:50;background:rgba(255,255,255,0.96);
      border-bottom:1px solid var(--border);backdrop-filter:blur(12px)
    }
    .nav{
      max-width:1120px;margin:0 auto;padding:14px 20px;
      display:flex;justify-content:space-between;align-items:center;gap:16px
    }
    .brand{font-weight:800;color:var(--primary)}
    .brand span{display:block;font-size:12px;font-weight:500;color:var(--muted)}
    .phone-btn,.cta-btn{
      display:inline-flex;align-items:center;justify-content:center;
      padding:14px 24px;border-radius:999px;font-weight:700
    }
    .phone-btn{background:var(--primary);color:#fff}
    .hero{
      padding:88px 20px 64px;
      background:
        linear-gradient(135deg, rgba(0,0,0,.62), rgba(0,0,0,.35)),
        url("__HERO_IMAGE__") center/cover no-repeat;
      color:#fff
    }
    .hero-inner{max-width:1120px;margin:0 auto;display:grid;grid-template-columns:1.2fr .8fr;gap:28px;align-items:end}
    .eyebrow{
      display:inline-block;margin-bottom:18px;padding:6px 12px;border-radius:999px;
      background:rgba(255,255,255,0.15);border:1px solid rgba(255,255,255,0.18);font-size:13px
    }
    h1{font-size:clamp(34px,5vw,58px);line-height:1.05;margin-bottom:16px;max-width:12ch}
    .hero p{max-width:60ch;font-size:18px;color:rgba(255,255,255,0.9)}
    .hero-actions{margin-top:26px;display:flex;flex-wrap:wrap;gap:14px}
    .cta-btn{background:var(--accent);color:#fff}
    .hero-card{
      background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.18);
      border-radius:24px;padding:24px;box-shadow:var(--shadow)
    }
    .hero-card h2{font-size:20px;margin-bottom:10px}
    .hero-card ul{padding-left:18px}
    .hero-card li+li{margin-top:8px}
    .wrap{max-width:1120px;margin:0 auto;padding:0 20px}
    .stats{
      margin-top:-28px;display:grid;grid-template-columns:repeat(3,1fr);gap:16px
    }
    .stat{
      background:#fff;border:1px solid var(--border);border-radius:18px;
      padding:22px;box-shadow:var(--shadow)
    }
    .stat strong{display:block;font-size:28px;color:var(--primary)}
    section{padding:72px 0}
    .section-head{margin-bottom:26px}
    .tag{
      display:inline-block;background:var(--light);color:var(--primary);
      padding:6px 12px;border-radius:999px;font-size:12px;font-weight:700;margin-bottom:12px
    }
    h2{font-size:clamp(28px,4vw,40px);line-height:1.1;margin-bottom:10px;color:var(--primary)}
    .sub{max-width:62ch;color:var(--muted)}
    .grid-3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
    .card{
      background:#fff;border:1px solid var(--border);border-radius:18px;padding:24px;box-shadow:var(--shadow)
    }
    .card h3{margin-bottom:8px;color:var(--primary)}
    .proof{
      display:grid;grid-template-columns:repeat(3,1fr);gap:18px
    }
    .proof figure{
      overflow:hidden;border-radius:18px;border:1px solid var(--border);background:#fff;box-shadow:var(--shadow)
    }
    .proof figcaption{padding:14px 16px;color:var(--muted);font-size:14px}
    .split{display:grid;grid-template-columns:1fr 1fr;gap:22px}
    .list{display:grid;gap:14px}
    .list-item{
      padding:18px 18px 18px 20px;border-left:4px solid var(--accent);background:var(--light);border-radius:14px
    }
    .faq{display:grid;gap:14px}
    .faq details{
      background:#fff;border:1px solid var(--border);border-radius:16px;padding:18px 20px;box-shadow:var(--shadow)
    }
    .faq summary{cursor:pointer;font-weight:700;color:var(--primary)}
    .faq p{margin-top:10px;color:var(--muted)}
    .cta-panel{
      background:linear-gradient(135deg, var(--primary), color-mix(in srgb, var(--primary) 65%, black));
      color:#fff;border-radius:28px;padding:32px;display:grid;gap:12px
    }
    .cta-panel .cta-btn,.cta-panel .phone-btn{width:max-content}
    footer{padding:36px 20px 60px;color:var(--muted);text-align:center}
    .mobile-bar{
      position:fixed;left:16px;right:16px;bottom:16px;background:var(--accent);color:#fff;
      border-radius:999px;padding:16px 18px;text-align:center;font-weight:700;box-shadow:var(--shadow)
    }
    @media (max-width: 900px){
      .hero-inner,.split,.grid-3,.proof,.stats{grid-template-columns:1fr}
      h1{max-width:none}
      .nav{align-items:flex-start;flex-direction:column}
      .mobile-bar{display:block}
    }
    @media (min-width: 901px){
      .mobile-bar{display:none}
    }
  </style>
</head>
<body>
  <header>
    <div class="nav">
      <div class="brand">__BUSINESS_NAME__<span>__TRADE_LABEL__ in __CITY_STATE__</span></div>
      <a class="phone-btn" href="__TEL_HREF__">Call __PHONE__</a>
    </div>
  </header>

  <section class="hero">
    <div class="hero-inner">
      <div>
        <div class="eyebrow">Ready-to-pitch demo site</div>
        <h1>__HEADLINE__</h1>
        <p>__TRADE_DESCRIPTION__</p>
        <div class="hero-actions">
          <a class="cta-btn" href="__TEL_HREF__">Call __PHONE__</a>
          <a class="phone-btn" href="#services">See what the page includes</a>
        </div>
      </div>
      <div class="hero-card">
        <h2>Why this page works for outreach</h2>
        <ul>
          __HERO_BULLETS__
        </ul>
      </div>
    </div>
  </section>

  <div class="wrap">
    <div class="stats">
      <div class="stat"><strong>Phone-first</strong><span>Designed to turn a cold pitch into a credible local business presence.</span></div>
      <div class="stat"><strong>Local trust</strong><span>Structured around __CITY_STATE__ service messaging and simple SEO metadata.</span></div>
      <div class="stat"><strong>Fast to deliver</strong><span>Built from lead data so it can be generated in bulk and refined later.</span></div>
    </div>
  </div>

  <section id="services">
    <div class="wrap">
      <div class="section-head">
        <div class="tag">Services</div>
        <h2>What the generated website highlights</h2>
        <p class="sub">This template gives each business a believable, niche-specific landing page without requiring custom design work every time.</p>
      </div>
      <div class="grid-3">__SERVICES__</div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <div class="section-head">
        <div class="tag">Gallery</div>
        <h2>Visual proof without manual asset work</h2>
        <p class="sub">The generator uses category-matched placeholder imagery so every page feels complete during outreach.</p>
      </div>
      <div class="proof">__GALLERY__</div>
    </div>
  </section>

  <section>
    <div class="wrap split">
      <div>
        <div class="section-head">
          <div class="tag">Pitch Notes</div>
          <h2>What to say when you call __BUSINESS_NAME__</h2>
          <p class="sub">The website itself becomes the demo. Your pitch is not hypothetical because the business can see its page immediately.</p>
        </div>
        <div class="list">__PITCH_NOTES__</div>
      </div>
      <div class="cta-panel">
        <div class="tag" style="background:rgba(255,255,255,0.18);color:#fff">Business Details</div>
        <h2 style="color:#fff;margin:0">__BUSINESS_NAME__</h2>
        <div>Trade: __TRADE_LABEL__</div>
        <div>Phone: __PHONE__</div>
        <div>Category: __CATEGORY__</div>
        <div>Address: __ADDRESS__</div>
        <div>Google Maps: <a href="__GOOGLE_MAPS_URL__" style="text-decoration:underline">View listing</a></div>
        <a class="cta-btn" href="__TEL_HREF__">Call this business</a>
      </div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <div class="section-head">
        <div class="tag">FAQ</div>
        <h2>Questions this repo automation answers</h2>
        <p class="sub">These FAQs are geared toward the internal sales process rather than pretending the owner wrote the content.</p>
      </div>
      <div class="faq">__FAQ__</div>
    </div>
  </section>

  <section>
    <div class="wrap">
      <div class="cta-panel">
        <div class="tag" style="background:rgba(255,255,255,0.18);color:#fff">Generated Outreach Site</div>
        <h2 style="color:#fff;margin:0">Ready to pitch __BUSINESS_NAME__ in __CITY_STATE__</h2>
        <p>This site was generated from lead data so it can be shown during outbound calls and improved if the owner is interested.</p>
        <a class="cta-btn" href="__TEL_HREF__">Call __PHONE__</a>
      </div>
    </div>
  </section>

  <footer>
    <div>__BUSINESS_NAME__ · __TRADE_LABEL__ · __CITY_STATE__</div>
    <div>Generated by the repo automation pipeline for manual outbound sales.</div>
  </footer>

  <a class="mobile-bar" href="__TEL_HREF__">Call __BUSINESS_NAME__ · __PHONE__</a>
</body>
</html>
"""


DIRECTORY_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Business Sites Directory</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:Segoe UI,Arial,sans-serif;background:#f5f7fb;color:#122033}
    .shell{max-width:1280px;margin:0 auto;padding:0 20px}
    .hero{
      padding:64px 0 36px;
      background:radial-gradient(circle at top left, #ecf3ff, transparent 45%),
                 linear-gradient(135deg, #11243d, #1f385c);
      color:#fff
    }
    h1{font-size:clamp(32px,5vw,54px);margin-bottom:12px}
    .hero p{max-width:64ch;color:rgba(255,255,255,0.84)}
    .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:28px}
    .stat{
      background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.1);
      border-radius:18px;padding:22px
    }
    .stat strong{display:block;font-size:30px}
    .grid{
      display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));
      gap:18px;padding:32px 0 60px
    }
    .card{
      background:#fff;border-radius:18px;padding:22px;border:1px solid #e7ecf4;
      box-shadow:0 16px 40px rgba(17,36,61,0.08)
    }
    .badge{
      display:inline-block;padding:6px 10px;border-radius:999px;
      background:#ecf3ff;color:#244a78;font-size:12px;font-weight:700;margin-bottom:12px
    }
    .card h2{font-size:20px;line-height:1.2;margin-bottom:8px}
    .meta{color:#586474;font-size:14px;margin-bottom:8px}
    .links{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
    .btn{
      display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;
      border-radius:999px;background:#17345b;color:#fff;font-weight:700
    }
    .btn.secondary{background:#eef4ff;color:#17345b}
    footer{padding:24px 0 50px;color:#657286;text-align:center}
    @media (max-width:900px){.stats{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <section class="hero">
    <div class="shell">
      <h1>Business Sites Directory</h1>
      <p>Generated lead websites for outbound sales. This page is rebuilt from the lead file so the CRM export and the site inventory stay in sync.</p>
      <div class="stats">
        <div class="stat"><strong>__SITE_COUNT__</strong><span>Generated Sites</span></div>
        <div class="stat"><strong>__TRADE_COUNT__</strong><span>Trade Buckets</span></div>
        <div class="stat"><strong>__STATE_COUNT__</strong><span>States Covered</span></div>
      </div>
    </div>
  </section>

  <main class="shell">
    <div class="grid">__CARDS__</div>
  </main>

  <footer>
    <div>Directory rebuilt from structured leads for outbound calling and site previews.</div>
  </footer>
</body>
</html>
"""


def _trade_config(trade: str) -> dict[str, object]:
    return TRADE_CONFIGS.get(trade, TRADE_CONFIGS["local_service"])


def _replace_many(template: str, values: dict[str, str]) -> str:
    html = template
    for key, value in values.items():
        html = html.replace(key, value)
    return html


def _services_markup(services: list[tuple[str, str]]) -> str:
    return "".join(
        f'<article class="card"><h3>{html_escape(title)}</h3><p>{html_escape(description)}</p></article>'
        for title, description in services
    )


def _gallery_markup(items: list[tuple[str, str]]) -> str:
    return "".join(
        (
            '<figure>'
            f'<img src="{html_escape(url)}" alt="{html_escape(caption)}" loading="lazy">'
            f"<figcaption>{html_escape(caption)}</figcaption>"
            "</figure>"
        )
        for url, caption in items
    )


def _faq_markup(items: list[tuple[str, str]]) -> str:
    return "".join(
        f'<details><summary>{html_escape(question)}</summary><p>{html_escape(answer)}</p></details>'
        for question, answer in items
    )


def _bullets_markup(items: list[str]) -> str:
    return "".join(f"<li>{html_escape(item)}</li>" for item in items)


def _pitch_notes_markup(lead: Lead) -> str:
    notes = [
        f"Lead source: {lead.source_query or 'Google Maps search result'}",
        f"Website detected: {'Yes' if lead.has_website else 'No'}",
        f"Website verification: {lead.website_verification_status.replace('_', ' ')}",
        f"Use the generated page URL as a live demo during the call.",
    ]
    if lead.website_verification_notes:
        notes.append(lead.website_verification_notes)
    if lead.rating and lead.review_count:
        notes.append(f"Google Maps shows roughly {lead.rating} stars across {lead.review_count} reviews.")
    return "".join(f'<div class="list-item">{html_escape(note)}</div>' for note in notes)


def render_business_page(lead: Lead) -> str:
    config = _trade_config(lead.trade)
    city_state = ", ".join(part for part in [lead.city, lead.state] if part) or "Local Market"
    title = f"{lead.business_name} | {config['label']} in {lead.city or 'Your City'}"
    meta_description = (
        f"Prebuilt outreach website for {lead.business_name} in {city_state}. "
        f"Use this demo page during manual sales calls for {config['label'].lower()} leads."
    )
    headline = str(config["headline"]).replace("__CITY__", html_escape(lead.city or "your market"))
    hero_bullets = _bullets_markup(
        [
            "Looks polished enough to send during a live call.",
            "Uses structured business data from the lead record.",
            "Can be refined quickly if the owner wants to move forward.",
        ]
    )
    replacements = {
        "__TITLE__": html_escape(title),
        "__META_DESCRIPTION__": html_escape(meta_description),
        "__JSON_NAME__": html_escape(lead.business_name),
        "__JSON_PHONE__": html_escape(lead.phone),
        "__JSON_CITY__": html_escape(lead.city),
        "__JSON_STATE__": html_escape(lead.state),
        "__JSON_URL__": html_escape(lead.generated_site_url),
        "__PRIMARY__": str(config["primary"]),
        "__ACCENT__": str(config["accent"]),
        "__LIGHT__": str(config["light"]),
        "__BUSINESS_NAME__": html_escape(lead.business_name),
        "__TRADE_LABEL__": html_escape(str(config["label"])),
        "__CITY_STATE__": html_escape(city_state),
        "__TEL_HREF__": html_escape(tel_href(lead.phone)),
        "__PHONE__": html_escape(lead.phone or "No phone on file"),
        "__HEADLINE__": headline,
        "__TRADE_DESCRIPTION__": html_escape(str(config["description"])),
        "__HERO_IMAGE__": html_escape(str(config["hero_image"])),
        "__HERO_BULLETS__": hero_bullets,
        "__SERVICES__": _services_markup(list(config["services"])),
        "__GALLERY__": _gallery_markup(list(config["gallery"])),
        "__PITCH_NOTES__": _pitch_notes_markup(lead),
        "__CATEGORY__": html_escape(lead.category or str(config["label"])),
        "__ADDRESS__": html_escape(lead.address or city_state),
        "__GOOGLE_MAPS_URL__": html_escape(lead.google_maps_url or "#"),
        "__FAQ__": _faq_markup(list(config["faq"])),
    }
    return _replace_many(BUSINESS_TEMPLATE, replacements)


def render_directory_page(leads: list[Lead], site_base_url: str | None = None) -> str:
    states = {lead.state for lead in leads if lead.state}
    trades = Counter(lead.trade for lead in leads)
    sorted_leads = sorted(leads, key=lambda lead: (lead.city, lead.trade, lead.business_name))
    cards = []
    for lead in sorted_leads:
        config = _trade_config(lead.trade)
        site_url = lead.generated_site_url or directory_url(site_base_url, lead.slug)
        trade_label = str(config["label"])
        city_state = ", ".join(part for part in [lead.city, lead.state] if part)
        website_note = "Website found" if lead.has_website else "No website found"
        cards.append(
            (
                '<article class="card">'
                f'<div class="badge">{html_escape(trade_label)}</div>'
                f"<h2>{html_escape(lead.business_name)}</h2>"
                f'<div class="meta">{html_escape(city_state or "Location unknown")}</div>'
                f'<div class="meta">{html_escape(lead.phone or "No phone on file")}</div>'
                f'<div class="meta">{html_escape(website_note)} · Status: {html_escape(lead.business_status)}</div>'
                '<div class="links">'
                f'<a class="btn" href="{html_escape(site_url or "#")}">View Site</a>'
                f'<a class="btn secondary" href="{html_escape(lead.google_maps_url or "#")}">Google Maps</a>'
                "</div>"
                "</article>"
            )
        )
    replacements = {
        "__SITE_COUNT__": str(len(leads)),
        "__TRADE_COUNT__": str(len(trades)),
        "__STATE_COUNT__": str(len(states)),
        "__CARDS__": "".join(cards),
    }
    return _replace_many(DIRECTORY_TEMPLATE, replacements)
