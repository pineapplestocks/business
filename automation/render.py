from __future__ import annotations

from collections import Counter
from datetime import date

from .models import Lead
from .utils import directory_url, html_escape, tel_href


TRADE_CONFIGS: dict[str, dict] = {
    "plumber": {
        "label": "Plumber",
        "primary": "#0f2d55",
        "primary_dk": "#081d38",
        "accent": "#e8401c",
        "accent_dk": "#c4340f",
        "favicon_emoji": "🔧",
        "announcement": "🚨 Emergency Plumbing Available — Call __PHONE__",
        "hero_badge": "Licensed & Insured · __CITY_STATE__",
        "hero_headline": "Plumbing Problem? We're On Our Way.",
        "hero_subtext": "Fast, reliable plumbing in __CITY__. Leaks, drains, fixtures, and emergency service — transparent pricing, guaranteed work.",
        "hero_bg": "linear-gradient(135deg, #081d38 0%, #0f2d55 55%, #163d6e 100%)",
        "stat_1": ("Same Day", "Service Available"),
        "stat_2_fallback": ("Licensed", "& Insured"),
        "stat_3": ("Guaranteed", "Workmanship"),
        "problems": [
            ("💧", "Leaks & Burst Pipes", "Even a small leak can cause serious water damage quickly. We locate and fix leaks before they become expensive disasters."),
            ("🚿", "Clogged Drains", "Slow or blocked drains in your kitchen, bathroom, or main line — we clear them completely, not just temporarily."),
            ("🔩", "Broken Fixtures", "Faucets, toilets, and garbage disposals that drip, run, or won't shut off — fixed or replaced same day."),
        ],
        "services": [
            ("🔍", "Leak Detection", "We locate hidden leaks fast — no unnecessary tearing into walls or floors."),
            ("🚰", "Drain Cleaning", "Kitchen, bathroom, and main-line drain clearing that actually lasts."),
            ("🪛", "Fixture Installation", "Toilets, faucets, and disposals installed cleanly and correctly the first time."),
            ("🔧", "Pipe Repair", "Cracked, corroded, or burst pipes repaired with professional materials and technique."),
            ("🚨", "Emergency Service", "Plumbing emergencies don't keep business hours. We respond fast, any time you call."),
            ("📋", "Free Estimates", "We assess the problem and give you a clear written quote before any work begins."),
        ],
        "process": [
            ("📞", "Call or Text Us", "Describe the problem and we'll give you an honest upfront estimate before we show up."),
            ("🔍", "We Diagnose On-Site", "Our licensed plumber arrives on time, inspects the issue, and explains what needs to be done — no upsells."),
            ("✅", "Fixed & Guaranteed", "We complete the repair cleanly and back every job with our workmanship guarantee."),
        ],
        "why_us": [
            ("Licensed & Insured", "Fully licensed and insured. We carry the credentials — you don't have to guess."),
            ("Upfront Pricing", "You know the cost before we start. No surprise charges, no hidden fees."),
            ("Same-Day Available", "Most jobs scheduled and completed the same day. We don't make you wait a week."),
            ("Guaranteed Work", "If it's not right after we leave, we come back and fix it at no charge."),
        ],
        "hero_bullets": [
            "Licensed & insured plumbers",
            "Same-day scheduling available",
            "Upfront pricing — no surprises",
            "Satisfaction guaranteed",
        ],
        "reviews": [
            ("They came out the same day and fixed our burst pipe in under two hours. Fair price, clean work. Couldn't ask for more.", "Robert M.", "⭐⭐⭐⭐⭐"),
            ("Honest, professional, and didn't try to upsell me on anything I didn't need. Will definitely call again.", "Sandra L.", "⭐⭐⭐⭐⭐"),
        ],
        "faq": [
            ("Do you offer same-day service?", "Yes. We keep our schedule flexible for urgent jobs and can usually come out the same day you call."),
            ("Are you licensed and insured?", "Yes — fully licensed and insured. We're happy to share credentials before starting any work."),
            ("Will I get a quote before work starts?", "Always. You get a clear written estimate before we touch anything. No surprises."),
            ("What areas do you serve?", "We serve __CITY__ and the surrounding area. Call us to confirm we cover your location."),
        ],
        "cta_heading": "Got a plumbing problem?",
        "cta_subtext": "Call now and we'll have a licensed plumber at your door — often the same day.",
    },
    "landscaper": {
        "label": "Landscaper",
        "primary": "#1a3d1a",
        "primary_dk": "#0e2610",
        "accent": "#3d9e3d",
        "accent_dk": "#2d7a2d",
        "favicon_emoji": "🌿",
        "announcement": "🌿 Free Estimates — No Contracts Required · Call __PHONE__",
        "hero_badge": "Serving __CITY_STATE__",
        "hero_headline": "A Yard You're Proud Of, All Season Long.",
        "hero_subtext": "Reliable lawn care and landscaping for __CITY__ homeowners. No contracts, no surprises — just a great-looking yard.",
        "hero_bg": "linear-gradient(135deg, #0e2610 0%, #1a3d1a 55%, #245524 100%)",
        "stat_1": ("Free", "Estimates"),
        "stat_2_fallback": ("No", "Contracts"),
        "stat_3": ("All Seasons", "Covered"),
        "problems": [
            ("🌾", "Overgrown Lawn", "A yard that's gotten out of control is stressful to look at and hard to tackle alone. We get it back in shape fast."),
            ("🍂", "Seasonal Mess", "Spring debris, fall leaves, and winter damage add up. We handle the seasonal work so you don't have to."),
            ("🌱", "Tired Flower Beds", "Overgrown beds and patchy mulch drag down your curb appeal. We clean them up and keep them looking sharp."),
        ],
        "services": [
            ("🌿", "Lawn Mowing", "Consistent mowing, edging, and blowing on a schedule that keeps your yard looking sharp all season."),
            ("🌳", "Landscape Design", "We'll help you plan and install plantings, beds, and features that add beauty and value to your property."),
            ("🌸", "Spring Cleanup", "Post-winter debris removal, bed cleanup, and prep work so your yard starts the season looking great."),
            ("🍂", "Fall Cleanup", "Leaf removal, bed cutback, and winterizing so your yard is ready when spring returns."),
            ("✂️", "Shrub Trimming", "Overgrown shrubs and hedges trimmed cleanly and shaped to enhance your home's curb appeal."),
            ("🪨", "Mulching", "Fresh mulch installed in your beds to suppress weeds, retain moisture, and give your landscaping a polished look."),
        ],
        "process": [
            ("📋", "Get a Free Estimate", "Call or text and tell us about your yard. We'll come out, take a look, and give you a clear quote — no pressure."),
            ("🌿", "We Do the Work", "Our crew shows up on schedule with the right equipment. We treat your property with care and leave the site clean."),
            ("😊", "Enjoy Your Yard", "Come home to a yard you're proud of. Flexible scheduling, consistent crews, no contracts required."),
        ],
        "why_us": [
            ("No Contracts", "We earn your business every visit. No long-term contracts, no lock-in, no cancellation hassles."),
            ("Free Estimates", "We come out and give you a real quote before any work starts — completely free, no obligation."),
            ("Consistent Crews", "The same team shows up every time so they know your property and you know who to expect."),
            ("All Seasons", "Spring cleanups, summer maintenance, fall leaf removal — year-round reliability."),
        ],
        "hero_bullets": [
            "Free estimates, no obligation",
            "No contracts required",
            "Consistent, on-time crews",
            "All seasons covered",
        ],
        "reviews": [
            ("Our yard has never looked better. They show up on time, do great work, and the price is fair. Highly recommend.", "Jennifer T.", "⭐⭐⭐⭐⭐"),
            ("Easy to work with, great results. They did our spring cleanup and it made a huge difference in our curb appeal.", "Marcus W.", "⭐⭐⭐⭐⭐"),
        ],
        "faq": [
            ("Do I need to sign a contract?", "No. We don't require contracts. You can schedule one-time jobs or recurring service with no long-term commitment."),
            ("Do you offer free estimates?", "Yes — always. We'll come out, walk your property, and give you a clear quote before any work begins."),
            ("How often should I get my lawn mowed?", "Most lawns need mowing every 1–2 weeks during the growing season. We'll recommend a schedule based on your grass and goals."),
            ("What areas do you serve?", "We serve __CITY__ and nearby communities. Give us a call to confirm we cover your neighborhood."),
        ],
        "cta_heading": "Ready for a greener yard?",
        "cta_subtext": "Call us for a free estimate — no contracts, no pressure, just a yard you can be proud of.",
    },
    "water_heater_repair": {
        "label": "Water Heater Repair",
        "primary": "#4d2c1d",
        "primary_dk": "#2e1a00",
        "accent": "#e8640a",
        "accent_dk": "#c4500a",
        "favicon_emoji": "🔥",
        "announcement": "📞 Same-Day Service Available — Call __PHONE__",
        "hero_badge": "Licensed & Insured · __CITY_STATE__",
        "hero_headline": "No Hot Water? We Fix It Today.",
        "hero_subtext": "Fast water heater repair and replacement in __CITY__. Tank and tankless systems, same-day service, guaranteed work.",
        "hero_bg": "linear-gradient(135deg, #1a0f00 0%, #2e1a00 45%, #4d2c1d 100%)",
        "stat_1": ("Same Day", "Service Available"),
        "stat_2_fallback": ("All Brands", "& Models"),
        "stat_3": ("Guaranteed", "Workmanship"),
        "problems": [
            ("🚫", "No Hot Water", "Woke up to a cold shower? Don't wait days for a technician. We diagnose and fix most water heater issues the same day."),
            ("🌡️", "Inconsistent Temperature", "Water that swings from scalding to cold is a sign your system needs attention. We find the root cause and fix it."),
            ("💧", "Leaking or Rusty Water", "Rust-colored water or a puddle under your heater means trouble. We assess whether repair or replacement makes more sense."),
        ],
        "services": [
            ("🔥", "Water Heater Repair", "Pilot issues, thermostat problems, heating element failures — we diagnose and fix fast."),
            ("🔄", "Water Heater Replacement", "When repair doesn't make sense, we install a new unit the same day and haul away the old one."),
            ("⚡", "Tankless Systems", "Tankless installation, repair, and descaling for endless hot water and lower energy bills."),
            ("🔧", "Maintenance & Flush", "Annual flushes and inspections extend your water heater's life and catch problems early."),
            ("🚨", "Emergency Service", "No hot water is an emergency. We respond fast and work around your schedule to get it resolved."),
            ("📋", "Free Estimates", "We assess your system, explain your options, and give you a written quote before any work begins."),
        ],
        "process": [
            ("📞", "Call Us Anytime", "Tell us what's wrong — no hot water, strange noises, a leak. We give you an honest same-day estimate."),
            ("🔍", "We Diagnose On-Site", "Our licensed tech arrives on time, inspects your system, and explains your options — no upsells."),
            ("🔥", "Hot Water Restored", "We complete the job the same day in most cases, clean up completely, and back every repair with our guarantee."),
        ],
        "why_us": [
            ("Same-Day Service", "Most repairs and replacements are done the same day you call. We know you can't wait days without hot water."),
            ("All Brands & Models", "We work on every major water heater brand — tank, tankless, gas, and electric."),
            ("Honest Recommendations", "We tell you when repair makes sense and when replacement is smarter. No pressure, just honest advice."),
            ("Guaranteed Work", "Every repair and installation is backed by our workmanship guarantee. If it's not right, we fix it free."),
        ],
        "hero_bullets": [
            "Licensed & insured technicians",
            "Same-day scheduling available",
            "All brands & models serviced",
            "Satisfaction guaranteed",
        ],
        "reviews": [
            ("Same-day service, fair price, and they explained everything clearly. Hot water was back in two hours. Great experience.", "Patricia H.", "⭐⭐⭐⭐⭐"),
            ("Honest guys. They told me a repair was cheaper than replacing and were right. Didn't try to upsell me at all.", "David R.", "⭐⭐⭐⭐⭐"),
        ],
        "faq": [
            ("Can you fix my water heater the same day?", "Yes, in most cases. We keep common parts stocked and aim to complete repairs the same day you call."),
            ("Should I repair or replace my water heater?", "It depends on the age and condition of the unit. We'll give you an honest assessment and a cost comparison for both."),
            ("Do you work on tankless water heaters?", "Yes — gas and electric tankless systems, including descaling, repair, and installation."),
            ("What areas do you cover?", "We serve __CITY__ and surrounding communities. Call us to confirm service at your address."),
        ],
        "cta_heading": "No hot water?",
        "cta_subtext": "Call now and we'll have a technician at your door — most jobs done the same day.",
    },
    "local_service": {
        "label": "Local Service",
        "primary": "#243447",
        "primary_dk": "#141f2b",
        "accent": "#2d9cdb",
        "accent_dk": "#1a7ab5",
        "favicon_emoji": "⭐",
        "announcement": "📞 Now Serving __CITY_STATE__ — Call __PHONE__",
        "hero_badge": "Local & Trusted · __CITY_STATE__",
        "hero_headline": "Reliable Local Service, Done Right.",
        "hero_subtext": "Serving __CITY__ with dependable, professional service. Call us for a free estimate — no pressure, no surprise charges.",
        "hero_bg": "linear-gradient(135deg, #141f2b 0%, #243447 55%, #2d4060 100%)",
        "stat_1": ("Local", "& Trusted"),
        "stat_2_fallback": ("Free", "Estimates"),
        "stat_3": ("Guaranteed", "Satisfaction"),
        "problems": [
            ("📋", "No Time to DIY", "Some jobs need a professional. We show up on time, do the work right, and respect your property."),
            ("💰", "Surprise Bills", "Hidden fees and vague estimates are frustrating. We give you a clear price before any work starts."),
            ("🔍", "Finding Someone Reliable", "It's hard to know who to trust. We're local, licensed, and back everything we do with a satisfaction guarantee."),
        ],
        "services": [
            ("🏠", "Service Calls", "We handle the jobs you don't have time or tools for. Call and we'll come out and take care of it."),
            ("📋", "Free Estimates", "Every job starts with a clear written estimate. You know the full price before we begin."),
            ("🔧", "Repairs", "Skilled repairs done right the first time, with the right tools and the right materials."),
            ("✅", "Inspections", "We assess problems honestly and tell you what actually needs to be done — nothing more."),
            ("📅", "Flexible Scheduling", "We work around your schedule. Same-day and next-day appointments available."),
            ("⭐", "Guaranteed Work", "We stand behind every job. If you're not satisfied, we come back and make it right."),
        ],
        "process": [
            ("📞", "Give Us a Call", "Tell us what you need. We'll ask a few questions and give you an honest estimate over the phone."),
            ("🏠", "We Show Up On Time", "A professional arrives at the agreed time, reviews the job, and confirms the price before starting."),
            ("✅", "Job Done Right", "We complete the work cleanly, clean up after ourselves, and make sure you're fully satisfied."),
        ],
        "why_us": [
            ("Local & Accountable", "We're based in __CITY__ and our reputation here matters to us. We treat every job like a neighbor's home."),
            ("Upfront Pricing", "No hidden fees, no surprise charges. You get a clear quote before we start."),
            ("Flexible Scheduling", "We accommodate your schedule — same-day and next-day appointments available."),
            ("Satisfaction Guaranteed", "If something isn't right after we finish, we come back and fix it at no charge."),
        ],
        "hero_bullets": [
            "Free estimates, no obligation",
            "Upfront pricing — no surprises",
            "Flexible scheduling",
            "Satisfaction guaranteed",
        ],
        "reviews": [
            ("Professional, on time, and the price was exactly what they quoted. Easy to work with. Would definitely recommend.", "Karen B.", "⭐⭐⭐⭐⭐"),
            ("Great experience from first call to job completion. They explained everything and didn't rush.", "Thomas G.", "⭐⭐⭐⭐⭐"),
        ],
        "faq": [
            ("Do you offer free estimates?", "Yes — always. We give you a clear written quote before any work begins. No obligation."),
            ("Are you licensed and insured?", "Yes, we're fully licensed and insured for all work we perform."),
            ("How quickly can you schedule?", "We usually have same-day or next-day availability. Call us and we'll find a time that works."),
            ("What areas do you serve?", "We serve __CITY__ and the surrounding area. Give us a call to confirm we cover your location."),
        ],
        "cta_heading": "Ready to get started?",
        "cta_subtext": "Call now for a free estimate — no pressure, no surprise charges.",
    },
}


BUSINESS_TEMPLATE = """\
<!DOCTYPE html>
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
  <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>__FAVICON__</text></svg>">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Open+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "LocalBusiness",
    "name": "__JSON_NAME__",
    "telephone": "__JSON_PHONE__",
    "address": {
      "@type": "PostalAddress",
      "streetAddress": "__JSON_ADDRESS__",
      "addressLocality": "__JSON_CITY__",
      "addressRegion": "__JSON_STATE__",
      "addressCountry": "US"
    },
    "areaServed": "__JSON_CITY__, __JSON_STATE__",
    "url": "__JSON_URL__"__JSON_RATING__
  }
  </script>
  <style>
    :root {
      --primary:    __PRIMARY__;
      --primary-dk: __PRIMARY_DK__;
      --accent:     __ACCENT__;
      --accent-dk:  __ACCENT_DK__;
      --text-dark:  #1a1a1a;
      --text-body:  #333333;
      --text-muted: #6b7280;
      --bg-page:    #f5f7fa;
      --bg-card:    #ffffff;
      --border:     #e5e7eb;
      --shadow-sm:  0 2px 8px rgba(0,0,0,0.07);
      --shadow-md:  0 6px 24px rgba(0,0,0,0.09);
      --shadow-lg:  0 16px 48px rgba(0,0,0,0.12);
      --radius-sm:  6px;
      --radius-md:  10px;
      --radius-lg:  18px;
      --max-w:      1280px;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html { scroll-behavior: smooth; }
    body { font-family: 'Open Sans', sans-serif; font-size: 17px; line-height: 1.65; color: var(--text-body); background: #fff; }
    a { text-decoration: none; color: inherit; }
    img { display: block; width: 100%; height: auto; }

    /* ── HEADER ── */
    header { position: fixed; top: 0; left: 0; right: 0; z-index: 100; transition: background .3s, box-shadow .3s; }
    header.scrolled { background: #fff; box-shadow: 0 2px 16px rgba(0,0,0,0.10); }
    .announcement { background: var(--accent); color: #fff; text-align: center; font-size: 13px; font-weight: 700; padding: 7px 20px; letter-spacing: .3px; }
    .nav { max-width: var(--max-w); margin: 0 auto; padding: 14px 24px; display: flex; justify-content: space-between; align-items: center; gap: 20px; }
    .brand { font-weight: 800; font-size: 18px; color: #fff; line-height: 1.2; }
    .brand span { display: block; font-size: 12px; font-weight: 600; opacity: .8; }
    header.scrolled .brand { color: var(--primary); }
    header.scrolled .brand span { opacity: 1; color: var(--text-muted); }
    .nav-links { display: flex; gap: 28px; list-style: none; }
    .nav-links a { font-size: 14px; font-weight: 600; color: rgba(255,255,255,.85); transition: color .2s; }
    .nav-links a:hover { color: #fff; }
    header.scrolled .nav-links a { color: var(--text-muted); }
    header.scrolled .nav-links a:hover { color: var(--primary); }
    .nav-cta { display: inline-flex; align-items: center; gap: 8px; background: var(--accent); color: #fff; padding: 11px 22px; border-radius: var(--radius-sm); font-weight: 700; font-size: 14px; transition: background .2s; white-space: nowrap; }
    .nav-cta:hover { background: var(--accent-dk); }
    @media(max-width:900px) { .nav-links { display: none; } }

    /* ── HERO ── */
    .hero { position: relative; padding: 180px 24px 120px; background: __HERO_BG__; color: #fff; }
    .hero::before { content: ''; position: absolute; inset: 0; background: rgba(0,0,0,.45); }
    .hero-inner { position: relative; max-width: var(--max-w); margin: 0 auto; display: grid; grid-template-columns: 1fr 380px; gap: 40px; align-items: center; }
    .hero-badge { display: inline-flex; align-items: center; gap: 6px; background: var(--accent); color: #fff; font-size: 12px; font-weight: 800; letter-spacing: .5px; text-transform: uppercase; padding: 5px 12px; border-radius: var(--radius-sm); margin-bottom: 18px; }
    .hero h1 { font-size: clamp(36px, 4.5vw, 56px); font-weight: 800; line-height: 1.1; margin-bottom: 18px; color: #fff; }
    .hero p { font-size: 18px; line-height: 1.65; color: rgba(255,255,255,.88); max-width: 52ch; margin-bottom: 30px; }
    .hero-btns { display: flex; flex-wrap: wrap; gap: 12px; }
    .btn-primary { display: inline-flex; align-items: center; gap: 8px; background: var(--accent); color: #fff; border: 2px solid var(--accent); padding: 14px 28px; border-radius: var(--radius-sm); font-weight: 700; font-size: 16px; transition: background .2s, color .2s; }
    .btn-primary:hover { background: var(--accent-dk); border-color: var(--accent-dk); }
    .btn-outline { display: inline-flex; align-items: center; gap: 8px; background: transparent; color: #fff; border: 2px solid rgba(255,255,255,.7); padding: 14px 28px; border-radius: var(--radius-sm); font-weight: 700; font-size: 16px; transition: background .2s, color .2s; }
    .btn-outline:hover { background: #fff; color: var(--text-dark); }
    .hero-card { background: rgba(255,255,255,.1); border: 1px solid rgba(255,255,255,.18); backdrop-filter: blur(10px); border-radius: var(--radius-lg); padding: 28px; }
    .hero-card-head { font-size: 13px; font-weight: 800; letter-spacing: .5px; text-transform: uppercase; color: rgba(255,255,255,.7); margin-bottom: 14px; }
    .hero-card-list { list-style: none; display: flex; flex-direction: column; gap: 10px; }
    .hero-card-list li { font-size: 15px; font-weight: 600; color: #fff; display: flex; align-items: center; gap: 10px; }
    .hero-card-list li::before { content: '✓'; width: 22px; height: 22px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 12px; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    @media(max-width:900px) { .hero-inner { grid-template-columns: 1fr; } .hero-card { display: none; } }

    /* ── STATS BAR ── */
    .stats-bar-wrap { background: var(--bg-page); padding: 0 24px; }
    .stats-bar { max-width: var(--max-w); margin: 0 auto; display: grid; grid-template-columns: repeat(3,1fr); gap: 0; margin-top: -44px; position: relative; z-index: 10; }
    .stat-item { background: #fff; padding: 22px 28px; display: flex; flex-direction: column; gap: 2px; border: 1px solid var(--border); }
    .stat-item:first-child { border-radius: var(--radius-md) 0 0 var(--radius-md); }
    .stat-item:last-child { border-radius: 0 var(--radius-md) var(--radius-md) 0; }
    .stat-item strong { font-size: 20px; font-weight: 800; color: var(--primary); }
    .stat-item span { font-size: 13px; color: var(--text-muted); font-weight: 600; }
    @media(max-width:700px) { .stats-bar { grid-template-columns: 1fr; margin-top: 0; } .stat-item { border-radius: 0 !important; } }

    /* ── SECTIONS ── */
    .section { padding: 80px 24px; }
    .section-bg { background: var(--bg-page); }
    .wrap { max-width: var(--max-w); margin: 0 auto; }
    .section-head { text-align: center; margin-bottom: 48px; }
    .eyebrow { display: inline-block; background: color-mix(in srgb, var(--accent) 12%, white); color: var(--accent); font-size: 12px; font-weight: 800; letter-spacing: 1px; text-transform: uppercase; padding: 5px 14px; border-radius: 999px; margin-bottom: 12px; }
    .section-head h2 { font-size: clamp(28px, 3.5vw, 40px); font-weight: 800; color: var(--primary); line-height: 1.2; margin-bottom: 12px; }
    .section-head .lead { font-size: 18px; color: var(--text-muted); max-width: 58ch; margin: 0 auto; }

    /* ── PROBLEMS ── */
    .problem-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 24px; }
    .problem-card { background: var(--bg-card); border-radius: var(--radius-md); padding: 32px 28px; box-shadow: var(--shadow-sm); border-top: 4px solid var(--accent); }
    .problem-card .icon { font-size: 36px; margin-bottom: 16px; display: block; }
    .problem-card h3 { font-size: 20px; font-weight: 800; color: var(--primary); margin-bottom: 10px; }
    .problem-card p { font-size: 15px; color: var(--text-muted); line-height: 1.65; }

    /* ── SERVICES ── */
    .services-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 20px; }
    .service-card { background: var(--bg-card); border-radius: var(--radius-md); padding: 28px 24px; box-shadow: var(--shadow-sm); border: 1px solid var(--border); transition: transform .2s, box-shadow .2s; }
    .service-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-md); }
    .service-card .svc-icon { font-size: 32px; margin-bottom: 14px; display: block; }
    .service-card h3 { font-size: 18px; font-weight: 700; color: var(--primary); margin-bottom: 8px; }
    .service-card p { font-size: 14px; color: var(--text-muted); line-height: 1.6; }

    /* ── PROCESS ── */
    .process-grid { display: grid; grid-template-columns: repeat(3,1fr); gap: 28px; }
    .process-step { background: var(--bg-card); border-radius: var(--radius-md); padding: 36px 28px; box-shadow: var(--shadow-sm); border-top: 4px solid var(--accent); text-align: center; }
    .process-num { width: 52px; height: 52px; border-radius: 50%; background: var(--accent); color: #fff; font-size: 22px; font-weight: 800; display: flex; align-items: center; justify-content: center; margin: 0 auto 18px; }
    .process-icon { font-size: 36px; margin-bottom: 14px; display: block; }
    .process-step h3 { font-size: 19px; font-weight: 700; color: var(--primary); margin-bottom: 10px; }
    .process-step p { font-size: 15px; color: var(--text-muted); line-height: 1.6; }

    /* ── WHY US + CONTACT ── */
    .why-grid { display: grid; grid-template-columns: 1fr 400px; gap: 40px; align-items: start; }
    .why-list { display: flex; flex-direction: column; gap: 16px; }
    .why-item { display: flex; gap: 18px; align-items: flex-start; }
    .why-icon { width: 48px; height: 48px; border-radius: var(--radius-sm); background: color-mix(in srgb, var(--accent) 12%, white); color: var(--accent); font-size: 22px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
    .why-item h4 { font-size: 17px; font-weight: 700; color: var(--primary); margin-bottom: 4px; }
    .why-item p { font-size: 14px; color: var(--text-muted); line-height: 1.55; }
    .contact-box { background: var(--primary); border-radius: var(--radius-lg); padding: 36px 32px; color: #fff; }
    .contact-box h3 { font-size: 24px; font-weight: 800; color: #fff; margin-bottom: 8px; }
    .contact-box p { font-size: 15px; color: rgba(255,255,255,.8); margin-bottom: 24px; }
    .contact-phone { display: flex; align-items: center; gap: 12px; background: var(--accent); color: #fff; padding: 16px 24px; border-radius: var(--radius-sm); font-weight: 800; font-size: 20px; margin-bottom: 16px; transition: background .2s; }
    .contact-phone:hover { background: var(--accent-dk); }
    .contact-details { font-size: 13px; color: rgba(255,255,255,.65); line-height: 1.7; }
    @media(max-width:960px) { .why-grid { grid-template-columns: 1fr; } }

    /* ── REVIEWS ── */
    .reviews-grid { display: grid; grid-template-columns: repeat(2,1fr); gap: 24px; }
    .review-card { background: var(--bg-card); border-radius: var(--radius-md); padding: 28px; box-shadow: var(--shadow-sm); border: 1px solid var(--border); }
    .review-stars { font-size: 18px; margin-bottom: 12px; }
    .review-text { font-size: 16px; color: var(--text-body); line-height: 1.65; font-style: italic; margin-bottom: 16px; }
    .review-author { font-size: 14px; font-weight: 700; color: var(--primary); }

    /* ── FAQ ── */
    .faq-list { display: flex; flex-direction: column; gap: 12px; max-width: 800px; margin: 0 auto; }
    .faq-item { background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-md); overflow: hidden; }
    .faq-question { width: 100%; background: none; border: none; padding: 20px 24px; text-align: left; font-family: inherit; font-size: 16px; font-weight: 700; color: var(--primary); cursor: pointer; display: flex; justify-content: space-between; align-items: center; gap: 16px; }
    .faq-question .faq-toggle { width: 28px; height: 28px; border-radius: 50%; background: color-mix(in srgb, var(--accent) 12%, white); color: var(--accent); font-size: 18px; font-weight: 700; display: flex; align-items: center; justify-content: center; flex-shrink: 0; transition: transform .2s; }
    .faq-item.open .faq-toggle { transform: rotate(45deg); }
    .faq-answer { display: none; padding: 0 24px 20px; font-size: 15px; color: var(--text-muted); line-height: 1.65; }
    .faq-item.open .faq-answer { display: block; }

    /* ── CTA DARK ── */
    .cta-dark { background: #111; padding: 80px 24px; text-align: center; color: #fff; }
    .cta-dark h2 { font-size: clamp(28px, 3.5vw, 40px); font-weight: 800; color: #fff; margin-bottom: 14px; }
    .cta-dark p { font-size: 18px; color: rgba(255,255,255,.75); max-width: 52ch; margin: 0 auto 32px; }
    .cta-dark .btn-primary { font-size: 18px; padding: 16px 36px; }

    /* ── FOOTER ── */
    footer { background: #111; border-top: 1px solid #222; padding: 48px 24px 32px; }
    .footer-inner { max-width: var(--max-w); margin: 0 auto; display: grid; grid-template-columns: 1.5fr 1fr 1fr; gap: 40px; margin-bottom: 36px; }
    .footer-brand { font-size: 18px; font-weight: 800; color: #fff; margin-bottom: 8px; }
    .footer-tagline { font-size: 14px; color: #9ca3af; line-height: 1.6; }
    .footer-heading { font-size: 13px; font-weight: 700; color: #fff; text-transform: uppercase; letter-spacing: .5px; margin-bottom: 14px; }
    .footer-links { list-style: none; display: flex; flex-direction: column; gap: 8px; }
    .footer-links a { font-size: 14px; color: #9ca3af; transition: color .2s; }
    .footer-links a:hover { color: #fff; }
    .footer-contact { font-size: 14px; color: #9ca3af; line-height: 1.8; }
    .footer-contact a { color: #9ca3af; }
    .footer-bottom { max-width: var(--max-w); margin: 0 auto; padding-top: 24px; border-top: 1px solid #222; font-size: 13px; color: #6b7280; text-align: center; }
    @media(max-width:700px) { .footer-inner { grid-template-columns: 1fr; } }

    /* ── RESPONSIVE ── */
    @media(max-width:900px) {
      .problem-grid, .services-grid, .process-grid, .reviews-grid { grid-template-columns: 1fr; }
      .hero { padding: 140px 24px 80px; }
      .section { padding: 60px 24px; }
    }
  </style>
</head>
<body>
  <header id="site-header">
    <div class="announcement">__ANNOUNCEMENT__</div>
    <div class="nav">
      <div class="brand">__BUSINESS_NAME__<span>__TRADE_LABEL__ · __CITY_STATE__</span></div>
      <ul class="nav-links">
        <li><a href="#problems">Services</a></li>
        <li><a href="#work">How It Works</a></li>
        <li><a href="#reviews">Reviews</a></li>
        <li><a href="#faq">FAQ</a></li>
        <li><a href="#contact">Contact</a></li>
      </ul>
      <a class="nav-cta" href="__TEL_HREF__">📞 __PHONE__</a>
    </div>
  </header>

  <section class="hero">
    <div class="hero-inner">
      <div>
        <div class="hero-badge">__HERO_BADGE__</div>
        <h1>__HERO_HEADLINE__</h1>
        <p>__HERO_SUBTEXT__</p>
        <div class="hero-btns">
          <a class="btn-primary" href="__TEL_HREF__">📞 Call __PHONE__</a>
          <a class="btn-outline" href="#problems">See Our Services</a>
        </div>
      </div>
      <div class="hero-card">
        <div class="hero-card-head">Why choose us?</div>
        <ul class="hero-card-list">__HERO_BULLETS__</ul>
      </div>
    </div>
  </section>

  <div class="stats-bar-wrap">
    <div class="stats-bar">
      <div class="stat-item"><strong>__STAT_1_VALUE__</strong><span>__STAT_1_LABEL__</span></div>
      <div class="stat-item"><strong>__STAT_2_VALUE__</strong><span>__STAT_2_LABEL__</span></div>
      <div class="stat-item"><strong>__STAT_3_VALUE__</strong><span>__STAT_3_LABEL__</span></div>
    </div>
  </div>

  <section class="section" id="problems">
    <div class="wrap">
      <div class="section-head">
        <div class="eyebrow">Sound Familiar?</div>
        <h2>Common Problems We Solve</h2>
        <p class="lead">If any of these describe your situation, give us a call — we can usually help the same day.</p>
      </div>
      <div class="problem-grid">__PROBLEMS__</div>
    </div>
  </section>

  <section class="section section-bg" id="services">
    <div class="wrap">
      <div class="section-head">
        <div class="eyebrow">What We Do</div>
        <h2>Our Services</h2>
        <p class="lead">From routine maintenance to urgent repairs — here's how we can help.</p>
      </div>
      <div class="services-grid">__SERVICES__</div>
    </div>
  </section>

  <section class="section" id="work">
    <div class="wrap">
      <div class="section-head">
        <div class="eyebrow">How It Works</div>
        <h2>Simple, Fast, Done Right</h2>
        <p class="lead">Here's exactly what to expect from your first call to a completed job.</p>
      </div>
      <div class="process-grid">__PROCESS__</div>
    </div>
  </section>

  <section class="section section-bg" id="contact">
    <div class="wrap">
      <div class="why-grid">
        <div>
          <div class="section-head" style="text-align:left; margin-bottom:32px;">
            <div class="eyebrow">Why Us</div>
            <h2>What Makes Us Different</h2>
          </div>
          <div class="why-list">__WHY_US__</div>
        </div>
        <div class="contact-box">
          <h3>__CTA_HEADING__</h3>
          <p>__CTA_SUBTEXT__</p>
          <a class="contact-phone" href="__TEL_HREF__">📞 __PHONE__</a>
          <div class="contact-details">__CONTACT_DETAILS__</div>
        </div>
      </div>
    </div>
  </section>

  <section class="section" id="reviews">
    <div class="wrap">
      <div class="section-head">
        <div class="eyebrow">Reviews</div>
        <h2>What Our Customers Say</h2>
        <p class="lead">Real feedback from real customers in __CITY__.</p>
      </div>
      <div class="reviews-grid">__REVIEWS__</div>
    </div>
  </section>

  <section class="section section-bg" id="faq">
    <div class="wrap">
      <div class="section-head">
        <div class="eyebrow">FAQ</div>
        <h2>Common Questions</h2>
        <p class="lead">Answers to what people usually ask before calling.</p>
      </div>
      <div class="faq-list">__FAQ__</div>
    </div>
  </section>

  <section class="cta-dark">
    <div class="wrap">
      <h2>__CTA_HEADING__</h2>
      <p>__CTA_SUBTEXT__</p>
      <a class="btn-primary" href="__TEL_HREF__">📞 Call __PHONE__ Now</a>
    </div>
  </section>

  <footer>
    <div class="footer-inner">
      <div>
        <div class="footer-brand">__BUSINESS_NAME__</div>
        <div class="footer-tagline">__TRADE_LABEL__ serving __CITY_STATE__.<br>Licensed, insured, and locally trusted.</div>
      </div>
      <div>
        <div class="footer-heading">Navigate</div>
        <ul class="footer-links">
          <li><a href="#problems">Services</a></li>
          <li><a href="#work">How It Works</a></li>
          <li><a href="#reviews">Reviews</a></li>
          <li><a href="#faq">FAQ</a></li>
          <li><a href="#contact">Contact</a></li>
        </ul>
      </div>
      <div>
        <div class="footer-heading">Contact</div>
        <div class="footer-contact">
          <a href="__TEL_HREF__">__PHONE__</a><br>
          __FOOTER_ADDRESS__
          __CITY_STATE__
        </div>
      </div>
    </div>
    <div class="footer-bottom">© __YEAR__ __BUSINESS_NAME__. All rights reserved.</div>
  </footer>

  <script>
    // Scroll header
    const header = document.getElementById('site-header');
    function onScroll() {
      if (window.scrollY > 60) header.classList.add('scrolled');
      else header.classList.remove('scrolled');
    }
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    // FAQ accordion
    document.querySelectorAll('.faq-question').forEach(btn => {
      btn.addEventListener('click', () => {
        const item = btn.closest('.faq-item');
        const isOpen = item.classList.contains('open');
        document.querySelectorAll('.faq-item.open').forEach(el => el.classList.remove('open'));
        if (!isOpen) item.classList.add('open');
      });
    });
  </script>
</body>
</html>
"""


DIRECTORY_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Business Sites Directory</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:Segoe UI,Arial,sans-serif;background:#f5f7fb;color:#122033}
    .shell{max-width:1280px;margin:0 auto;padding:0 20px}
    .hero{padding:64px 0 36px;background:radial-gradient(circle at top left,#ecf3ff,transparent 45%),linear-gradient(135deg,#11243d,#1f385c);color:#fff}
    h1{font-size:clamp(32px,5vw,54px);margin-bottom:12px}
    .hero p{max-width:64ch;color:rgba(255,255,255,0.84)}
    .stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:28px}
    .stat{background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.1);border-radius:18px;padding:22px}
    .stat strong{display:block;font-size:30px}
    .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:18px;padding:32px 0 60px}
    .card{background:#fff;border-radius:18px;padding:22px;border:1px solid #e7ecf4;box-shadow:0 16px 40px rgba(17,36,61,0.08)}
    .badge{display:inline-block;padding:6px 10px;border-radius:999px;background:#ecf3ff;color:#244a78;font-size:12px;font-weight:700;margin-bottom:12px}
    .card h2{font-size:20px;line-height:1.2;margin-bottom:8px}
    .meta{color:#586474;font-size:14px;margin-bottom:8px}
    .links{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
    .btn{display:inline-flex;align-items:center;justify-content:center;padding:10px 14px;border-radius:999px;background:#17345b;color:#fff;font-weight:700}
    .btn.secondary{background:#eef4ff;color:#17345b}
    footer{padding:24px 0 50px;color:#657286;text-align:center}
    @media(max-width:900px){.stats{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <section class="hero">
    <div class="shell">
      <h1>Business Sites Directory</h1>
      <p>Generated lead websites for outbound sales. This page is rebuilt from the lead file so the site inventory stays in sync.</p>
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


# ── helpers ──────────────────────────────────────────────────────────────────

def _trade_config(trade: str) -> dict:
    return TRADE_CONFIGS.get(trade, TRADE_CONFIGS["local_service"])


def _replace_many(template: str, values: dict[str, str]) -> str:
    html = template
    for key, value in values.items():
        html = html.replace(key, value)
    return html


def _problems_markup(items: list[tuple[str, str, str]]) -> str:
    return "".join(
        f'<div class="problem-card">'
        f'<span class="icon">{icon}</span>'
        f"<h3>{html_escape(title)}</h3>"
        f"<p>{html_escape(desc)}</p>"
        f"</div>"
        for icon, title, desc in items
    )


def _services_markup(items: list[tuple[str, str, str]]) -> str:
    return "".join(
        f'<div class="service-card">'
        f'<span class="svc-icon">{icon}</span>'
        f"<h3>{html_escape(title)}</h3>"
        f"<p>{html_escape(desc)}</p>"
        f"</div>"
        for icon, title, desc in items
    )


def _process_markup(items: list[tuple[str, str, str]], city: str) -> str:
    parts = []
    for i, (icon, title, desc) in enumerate(items, start=1):
        desc_filled = desc.replace("__CITY__", html_escape(city or "your area"))
        parts.append(
            f'<div class="process-step">'
            f'<div class="process-num">{i}</div>'
            f'<span class="process-icon">{icon}</span>'
            f"<h3>{html_escape(title)}</h3>"
            f"<p>{desc_filled}</p>"
            f"</div>"
        )
    return "".join(parts)


def _why_us_markup(items: list[tuple[str, str]], city: str) -> str:
    icons = ["✅", "💲", "📅", "⭐"]
    parts = []
    for i, (title, desc) in enumerate(items):
        icon = icons[i % len(icons)]
        desc_filled = desc.replace("__CITY__", html_escape(city or "your area"))
        parts.append(
            f'<div class="why-item">'
            f'<div class="why-icon">{icon}</div>'
            f"<div><h4>{html_escape(title)}</h4><p>{desc_filled}</p></div>"
            f"</div>"
        )
    return "".join(parts)


def _reviews_markup(items: list[tuple[str, str, str]]) -> str:
    return "".join(
        f'<div class="review-card">'
        f'<div class="review-stars">{stars}</div>'
        f'<p class="review-text">"{html_escape(text)}"</p>'
        f'<div class="review-author">— {html_escape(author)}</div>'
        f"</div>"
        for text, author, stars in items
    )


def _faq_markup(items: list[tuple[str, str]], city: str) -> str:
    parts = []
    for question, answer in items:
        answer_filled = answer.replace("__CITY__", html_escape(city or "your area"))
        parts.append(
            f'<div class="faq-item">'
            f'<button class="faq-question">{html_escape(question)}<span class="faq-toggle">+</span></button>'
            f'<div class="faq-answer">{answer_filled}</div>'
            f"</div>"
        )
    return "".join(parts)


def _hero_bullets_markup(items: list[str]) -> str:
    return "".join(f"<li>{html_escape(item)}</li>" for item in items)


def _rating_schema(lead: Lead) -> str:
    if not lead.rating or not lead.review_count:
        return ""
    try:
        float(lead.rating)
        int(lead.review_count)
    except (ValueError, TypeError):
        return ""
    return (
        f',\n    "aggregateRating": {{\n'
        f'      "@type": "AggregateRating",\n'
        f'      "ratingValue": "{html_escape(lead.rating)}",\n'
        f'      "reviewCount": "{html_escape(lead.review_count)}"\n'
        f"    }}"
    )


# ── public API ───────────────────────────────────────────────────────────────

def render_business_page(lead: Lead) -> str:
    config = _trade_config(lead.trade)
    city = lead.city or "Your City"
    city_state = ", ".join(part for part in [lead.city, lead.state] if part) or "Local Market"

    title = f"{lead.business_name} | {config['label']} in {city}"
    meta_description = (
        f"{lead.business_name} — {config['label'].lower()} in {city_state}. "
        f"{config['hero_subtext'].replace('__CITY__', city).rstrip('.')}. "
        f"Call {lead.phone or 'us'} for a free estimate."
    )

    # Dynamic stat_2: use actual lead rating if available
    if lead.rating and lead.review_count:
        stat_2_value = f"{lead.rating}★ {lead.review_count} Reviews"
        stat_2_label = ""
    elif lead.rating:
        stat_2_value = f"{lead.rating}★ Rating"
        stat_2_label = "on Google Maps"
    else:
        stat_2_value, stat_2_label = config["stat_2_fallback"]

    stat_1_value, stat_1_label = config["stat_1"]
    stat_3_value, stat_3_label = config["stat_3"]

    phone = lead.phone or "Call Us"
    announcement = config["announcement"].replace("__PHONE__", html_escape(phone))
    hero_badge = config["hero_badge"].replace("__CITY_STATE__", html_escape(city_state))
    hero_headline = config["hero_headline"]
    hero_subtext = config["hero_subtext"].replace("__CITY__", html_escape(city))

    footer_address = f"{html_escape(lead.address)}<br>" if lead.address else ""
    contact_details_parts = []
    if lead.address:
        contact_details_parts.append(html_escape(lead.address))
    contact_details_parts.append(html_escape(city_state))
    contact_details = "<br>".join(contact_details_parts)

    replacements = {
        "__TITLE__": html_escape(title),
        "__META_DESCRIPTION__": html_escape(meta_description),
        "__PRIMARY__": str(config["primary"]),
        "__PRIMARY_DK__": str(config["primary_dk"]),
        "__ACCENT__": str(config["accent"]),
        "__ACCENT_DK__": str(config["accent_dk"]),
        "__FAVICON__": config["favicon_emoji"],
        "__JSON_NAME__": html_escape(lead.business_name),
        "__JSON_PHONE__": html_escape(lead.phone),
        "__JSON_ADDRESS__": html_escape(lead.address or ""),
        "__JSON_CITY__": html_escape(lead.city),
        "__JSON_STATE__": html_escape(lead.state),
        "__JSON_URL__": html_escape(lead.generated_site_url),
        "__JSON_RATING__": _rating_schema(lead),
        "__ANNOUNCEMENT__": announcement,
        "__BUSINESS_NAME__": html_escape(lead.business_name),
        "__TRADE_LABEL__": html_escape(str(config["label"])),
        "__CITY_STATE__": html_escape(city_state),
        "__CITY__": html_escape(city),
        "__PHONE__": html_escape(phone),
        "__TEL_HREF__": html_escape(tel_href(lead.phone)),
        "__HERO_BG__": str(config["hero_bg"]),
        "__HERO_BADGE__": html_escape(hero_badge),
        "__HERO_HEADLINE__": html_escape(hero_headline),
        "__HERO_SUBTEXT__": html_escape(hero_subtext),
        "__HERO_BULLETS__": _hero_bullets_markup(list(config["hero_bullets"])),
        "__STAT_1_VALUE__": html_escape(stat_1_value),
        "__STAT_1_LABEL__": html_escape(stat_1_label),
        "__STAT_2_VALUE__": html_escape(stat_2_value),
        "__STAT_2_LABEL__": html_escape(stat_2_label),
        "__STAT_3_VALUE__": html_escape(stat_3_value),
        "__STAT_3_LABEL__": html_escape(stat_3_label),
        "__PROBLEMS__": _problems_markup(list(config["problems"])),
        "__SERVICES__": _services_markup(list(config["services"])),
        "__PROCESS__": _process_markup(list(config["process"]), city),
        "__WHY_US__": _why_us_markup(list(config["why_us"]), city),
        "__CTA_HEADING__": html_escape(str(config["cta_heading"])),
        "__CTA_SUBTEXT__": html_escape(str(config["cta_subtext"])),
        "__CONTACT_DETAILS__": contact_details,
        "__REVIEWS__": _reviews_markup(list(config["reviews"])),
        "__FAQ__": _faq_markup(list(config["faq"]), city),
        "__FOOTER_ADDRESS__": footer_address,
        "__YEAR__": str(date.today().year),
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
    replacements = {
        "__SITE_COUNT__": str(len(leads)),
        "__TRADE_COUNT__": str(len(trades)),
        "__STATE_COUNT__": str(len(states)),
        "__CARDS__": "".join(cards),
    }
    return _replace_many(DIRECTORY_TEMPLATE, replacements)
