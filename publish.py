#!/usr/bin/env python3
"""
Converts optimized markdown blog posts into deploy-ready HTML pages
matching the tdrealtyohio.com site template.

Usage:
    python publish.py --input output/westerville-home-buying/FINAL.md
    python publish.py --input output/westerville-home-buying/FINAL.md --output-repo /path/to/tdrealtyohio.com
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

from config import BUSINESS


def parse_frontmatter(content: str) -> tuple[dict, str]:
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if not fm_match:
        print("Error: No YAML frontmatter found")
        sys.exit(1)
    frontmatter = yaml.safe_load(fm_match.group(1)) or {}
    body = fm_match.group(2)
    return frontmatter, body


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


def markdown_to_html(body: str) -> str:
    """Convert markdown body to HTML. Handles headings, paragraphs, links, bold, italic, lists, and FAQ sections."""
    lines = body.strip().split('\n')
    html_lines = []
    in_ul = False
    in_ol = False
    in_paragraph = False
    paragraph_lines = []

    def flush_paragraph():
        nonlocal in_paragraph, paragraph_lines
        if paragraph_lines:
            text = ' '.join(paragraph_lines)
            text = inline_format(text)
            html_lines.append(f'          <p>{text}</p>')
            html_lines.append('')
            paragraph_lines = []
            in_paragraph = False

    def close_list():
        nonlocal in_ul, in_ol
        if in_ul:
            html_lines.append('          </ul>')
            html_lines.append('')
            in_ul = False
        if in_ol:
            html_lines.append('          </ol>')
            html_lines.append('')
            in_ol = False

    def inline_format(text: str) -> str:
        # Links: [text](url)
        text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', text)
        # Bold: **text**
        text = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', text)
        # Italic: *text*
        text = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', text)
        return text

    for line in lines:
        stripped = line.strip()

        # Empty line
        if not stripped:
            flush_paragraph()
            close_list()
            continue

        # Headings (skip H1 — handled by template)
        h_match = re.match(r'^(#{1,6})\s+(.+)$', stripped)
        if h_match:
            flush_paragraph()
            close_list()
            level = len(h_match.group(1))
            heading_text = inline_format(h_match.group(2))
            if level == 1:
                continue  # H1 is in the article header
            html_lines.append(f'          <h{level}>{heading_text}</h{level}>')
            html_lines.append('')
            continue

        # Unordered list
        ul_match = re.match(r'^[-*]\s+(.+)$', stripped)
        if ul_match:
            flush_paragraph()
            if not in_ul:
                close_list()
                html_lines.append('          <ul>')
                in_ul = True
            html_lines.append(f'            <li>{inline_format(ul_match.group(1))}</li>')
            continue

        # Ordered list
        ol_match = re.match(r'^\d+\.\s+(.+)$', stripped)
        if ol_match:
            flush_paragraph()
            if not in_ol:
                close_list()
                html_lines.append('          <ol>')
                in_ol = True
            html_lines.append(f'            <li>{inline_format(ol_match.group(1))}</li>')
            continue

        # Regular text — accumulate into paragraph
        close_list()
        paragraph_lines.append(stripped)
        in_paragraph = True

    flush_paragraph()
    close_list()
    return '\n'.join(html_lines)


def extract_faq_items(body: str) -> list[dict]:
    """Extract FAQ question/answer pairs from markdown."""
    faqs = []
    lines = body.split('\n')
    i = 0
    in_faq_section = False

    while i < len(lines):
        stripped = lines[i].strip()

        # Detect FAQ section
        if re.search(r'(?i)(faq|frequently asked|common questions)', stripped) and stripped.startswith('#'):
            in_faq_section = True
            i += 1
            continue

        # Next H2 ends FAQ section
        if in_faq_section and stripped.startswith('## '):
            break

        if in_faq_section:
            # Questions as H3 or bold or ending with ?
            q_match = re.match(r'^###\s+(.+\?)\s*$', stripped)
            if not q_match:
                q_match = re.match(r'^\*\*(.+\?)\*\*\s*$', stripped)
            if q_match:
                question = q_match.group(1)
                # Collect answer lines
                i += 1
                answer_lines = []
                while i < len(lines):
                    s = lines[i].strip()
                    if not s:
                        if answer_lines:
                            break
                        i += 1
                        continue
                    if s.startswith('###') or s.startswith('## ') or s.startswith('**') and s.endswith('?**'):
                        break
                    answer_lines.append(s)
                    i += 1
                if answer_lines:
                    answer = ' '.join(answer_lines)
                    answer = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', answer)
                    answer = re.sub(r'\*\*([^*]+)\*\*', r'\1', answer)
                    answer = re.sub(r'\*([^*]+)\*', r'\1', answer)
                    faqs.append({"question": question, "answer": answer})
                continue
        i += 1

    return faqs


def build_faq_html(faqs: list[dict]) -> str:
    """Build the interactive FAQ HTML matching the site template."""
    if not faqs:
        return ''

    items = []
    for faq in faqs:
        q_escaped = html.escape(faq['question'])
        a_escaped = html.escape(faq['answer'])
        items.append(f'''            <div class="faq-item">
              <button class="faq-question" aria-expanded="false">
                {q_escaped}
                <svg class="faq-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </button>
              <div class="faq-answer">
                <p>{a_escaped}</p>
              </div>
            </div>''')

    return '\n'.join(items)


def build_faq_structured_data(faqs: list[dict], url: str) -> str:
    if not faqs:
        return ''
    entities = []
    for faq in faqs:
        entities.append({
            "@type": "Question",
            "name": faq["question"],
            "acceptedAnswer": {
                "@type": "Answer",
                "text": faq["answer"],
            }
        })
    data = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }
    return json.dumps(data, indent=4)


def build_html(frontmatter: dict, body_md: str, slug: str) -> str:
    title = frontmatter.get('title', 'Blog Post')
    description = frontmatter.get('description', '')
    keywords_list = frontmatter.get('keywords', [])
    if isinstance(keywords_list, list):
        keywords = ', '.join(keywords_list)
    else:
        keywords = str(keywords_list)
    date_raw = frontmatter.get('date', datetime.now().strftime('%Y-%m-%d'))
    date_str = str(date_raw)
    community = frontmatter.get('community', '')
    author = frontmatter.get('author', 'TD Realty Ohio')

    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        date_display = date_obj.strftime('%B %d, %Y')
        date_month = date_obj.strftime('%B %Y')
    except ValueError:
        date_display = date_str
        date_month = date_str

    url = f"https://tdrealtyohio.com/blog/{slug}/"
    breadcrumb_label = title if len(title) < 40 else f"{community} Home Buying Guide"

    article_html = markdown_to_html(body_md)
    faqs = extract_faq_items(body_md)
    faq_html = build_faq_html(faqs)
    faq_structured = build_faq_structured_data(faqs, url)

    # Build FAQ section HTML if we have FAQs and they're not already in the converted HTML
    faq_section = ''
    if faq_html:
        faq_section = f'''
          <h2>Frequently Asked Questions</h2>

          <div class="faq-list" style="margin-top: 1.5rem;">
{faq_html}
          </div>'''

    faq_schema_block = ''
    if faq_structured:
        faq_schema_block = f'''
  <script type="application/ld+json">
  {faq_structured}
  </script>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(title)} | TD Realty Ohio</title>
  <meta name="description" content="{html.escape(description)}">
  <meta name="keywords" content="{html.escape(keywords)}">

  <link rel="canonical" href="{url}">

  <meta property="og:type" content="article">
  <meta property="og:title" content="{html.escape(title)} | TD Realty Ohio">
  <meta property="og:description" content="{html.escape(description)}">
  <meta property="og:url" content="{url}">
  <meta property="og:image" content="https://tdrealtyohio.com/assets/images/og-default.jpg">
  <meta property="og:image:type" content="image/jpeg">

  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{html.escape(title)}">
  <meta name="twitter:description" content="{html.escape(description)}">
  <meta name="twitter:image" content="https://tdrealtyohio.com/assets/images/og-default.jpg">

  <link rel="icon" href="/favicon.ico" sizes="32x32">
  <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  <link rel="apple-touch-icon" href="/apple-touch-icon.svg">
  <meta name="theme-color" content="#1a2e44">

  <link rel="preconnect" href="https://fonts.googleapis.com" crossorigin>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="preload" href="/assets/css/styles.css" as="style">
  <link rel="preload" href="/assets/js/main.js" as="script">
  <link href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:wght@400;700&family=Source+Sans+3:wght@400;500;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/css/styles.css">
  <!-- Google tag (gtag.js) -->
  <script async src="https://www.googletagmanager.com/gtag/js?id=AW-17866418952"></script>
  <script>
    window.dataLayer = window.dataLayer || [];
    function gtag(){{dataLayer.push(arguments);}}
    gtag('js', new Date());
    gtag('config', 'AW-17866418952');
  </script>


  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{html.escape(title)}",
    "description": "{html.escape(description)}",
    "author": {{
      "@type": "Person",
      "name": "Travis Debnam",
      "jobTitle": "Broker",
      "worksFor": {{
        "@type": "Organization",
        "name": "TD Realty Ohio, LLC"
      }}
    }},
    "publisher": {{
      "@type": "Organization",
      "name": "TD Realty Ohio, LLC",
      "url": "https://tdrealtyohio.com"
    }},
    "datePublished": "{date_str}",
    "dateModified": "{date_str}",
    "mainEntityOfPage": {{
      "@type": "WebPage",
      "@id": "{url}"
    }},
    "image": "https://tdrealtyohio.com/assets/images/og-default.jpg",
    "keywords": {json.dumps(keywords_list if isinstance(keywords_list, list) else [keywords])}
  }}
  </script>
{faq_schema_block}
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "https://tdrealtyohio.com/" }},
      {{ "@type": "ListItem", "position": 2, "name": "Blog", "item": "https://tdrealtyohio.com/blog/" }},
      {{ "@type": "ListItem", "position": 3, "name": "{html.escape(breadcrumb_label)}" }}
    ]
  }}
  </script>
</head>
<body>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  <header class="header">
    <div class="header-inner">
      <a href="/" class="logo">
        <span class="logo-mark">TD</span>
        <span>Realty Ohio</span>
      </a>

      <nav class="nav" id="main-nav" aria-label="Main navigation">
        <a href="/sellers/" class="nav-link">Sellers</a>
        <a href="/1-percent-commission/" class="nav-link">1% Listing</a>
        <a href="/buyers/" class="nav-link">Buyers</a>
        <a href="/pre-listing-inspection/" class="nav-link">Pre-Listing Inspection</a>
        <a href="/home-value/" class="nav-link">Home Value</a>
        <a href="/affordability/" class="nav-link">Affordability</a>
        <a href="/areas/" class="nav-link">Areas</a>
        <a href="/blog/" class="nav-link">Blog</a>
        <a href="/about/" class="nav-link">About</a>
        <a href="/contact/" class="btn btn-primary nav-cta">Contact</a>
      </nav>

      <button class="mobile-menu-btn" id="mobile-menu-btn" aria-label="Toggle menu" aria-expanded="false" aria-controls="main-nav">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
          <path d="M3 12h18M3 6h18M3 18h18" stroke-linecap="round"/>
        </svg>
      </button>
    </div>

  </header>

  <main id="main-content">
    <nav class="breadcrumb" aria-label="Breadcrumb">
      <div class="container">
        <ol class="breadcrumb-list">
          <li><a href="/">Home</a></li>
          <li><a href="/blog/">Blog</a></li>
          <li aria-current="page">{html.escape(breadcrumb_label)}</li>
        </ol>
      </div>
    </nav>

    <article class="section blog-article">
      <div class="container" style="max-width: 800px;">
        <header class="article-header">
          <h1>{html.escape(title)}</h1>
          <p class="post-meta">By Travis Debnam | {date_display}</p>
        </header>

        <div class="article-content">
{article_html}
{faq_section}
        </div>
      </div>
    </article>

    <section class="section cta-section">
      <div class="container">
        <h2>Ready to Find Your {html.escape(community)} Home?</h2>
        <p>Contact TD Realty Ohio for expert guidance buying your home in {html.escape(community)}. Free consultation, no obligation.</p>
        <div class="hero-buttons flex-center">
          <a href="/contact/" class="btn btn-primary btn-lg">Get in Touch</a>
          <a href="tel:6143928858" class="btn btn-outline-white btn-lg">(614) 392-8858</a>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="container" style="max-width: 800px;">
        <h2>Related Articles</h2>
        <div class="blog-list">
          <article class="blog-card">
            <h3><a href="/blog/how-much-save-selling-columbus-home-1-percent/">How Much Can You Save Selling Your Columbus Home for 1% Commission?</a></h3>
            <p>See exactly how much you save with a 1% commission realtor in Columbus. Math breakdown and savings table included.</p>
            <a href="/blog/how-much-save-selling-columbus-home-1-percent/" class="read-more">Read: 1% Commission Savings Calculator</a>
          </article>
          <article class="blog-card">
            <h3><a href="/blog/pre-listing-inspection-benefits/">What Is a Pre-Listing Inspection and Why Should Columbus Sellers Get One?</a></h3>
            <p>Discover how a pre-listing inspection can help you sell your home faster, avoid negotiation surprises, and potentially get a higher sale price.</p>
            <a href="/blog/pre-listing-inspection-benefits/" class="read-more">Read: Pre-Listing Inspection Benefits</a>
          </article>
        </div>
      </div>
    </section>
  </main>

  <footer class="footer">
    <div class="container">
      <div class="footer-main">
        <div class="footer-brand">
          <div class="footer-logo">
            <span class="logo-mark">TD</span>
            <span>Realty Ohio</span>
          </div>
          <p>Full-service real estate. Lower commission.</p>
        </div>

        <div>
          <h3 class="footer-title">Services</h3>
          <ul class="footer-links">
            <li><a href="/sellers/">For Sellers</a></li>
            <li><a href="/buyers/">For Buyers</a></li>
            <li><a href="/pre-listing-inspection/">Pre-Listing Inspection</a></li>
            <li><a href="/areas/">Service Areas</a></li>
            <li><a href="/home-value/">Free Home Value</a></li>
            <li><a href="/affordability/">Affordability Calculator</a></li>
            <li><a href="/referrals/">Referral Credit</a></li>
            <li><a href="/compare/">Compare Options</a></li>
          </ul>
        </div>

        <div>
          <h3 class="footer-title">Company</h3>
          <ul class="footer-links">
            <li><a href="/about/">About</a></li>
            <li><a href="/contact/">Contact</a></li>
            <li><a href="/blog/">Blog</a></li>
            <li><a href="/testimonials/">Testimonials</a></li>
            <li><a href="/agents/">Agent Opportunities</a></li>
          </ul>
        </div>

        <div>
          <h3 class="footer-title">Contact</h3>
          <div class="footer-contact-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
            </svg>
            <a href="tel:6143928858" data-phone>(614) 392-8858</a>
          </div>
          <div class="footer-contact-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
              <polyline points="22,6 12,13 2,6"/>
            </svg>
            <a href="mailto:info@tdrealtyohio.com" data-email>info@tdrealtyohio.com</a>
          </div>
          <div class="footer-contact-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
              <circle cx="12" cy="10" r="3"/>
            </svg>
            <span data-location>Westerville, Ohio</span>
          </div>
        </div>
      </div>

      <div class="footer-compliance-logos">
        <a href="https://www.hud.gov/program_offices/fair_housing_equal_opp" target="_blank" rel="noopener noreferrer" title="Equal Housing Opportunity" aria-label="Equal Housing Opportunity - opens in new tab">
          <img src="/media/compliance/equal-housing.svg" alt="Equal Housing Opportunity" height="50" width="50" loading="lazy">
        </a>
        <a href="https://www.nar.realtor/" target="_blank" rel="noopener noreferrer" title="National Association of REALTORS\u00ae" aria-label="National Association of REALTORS - opens in new tab">
          <img src="/media/compliance/realtor.svg" alt="REALTOR\u00ae" height="50" width="50" loading="lazy">
        </a>
        <a href="https://www.columbusrealtors.com/" target="_blank" rel="noopener noreferrer" title="Columbus REALTORS\u00ae" aria-label="Columbus REALTORS - opens in new tab">
          <img src="/media/compliance/columbus-realtors.svg" alt="Columbus REALTORS\u00ae" height="45" width="120" loading="lazy">
        </a>
        <a href="https://www.ohiorealtors.org/" target="_blank" rel="noopener noreferrer" title="Ohio REALTORS\u00ae" aria-label="Ohio REALTORS - opens in new tab">
          <img src="/media/compliance/ohio-realtors.svg" alt="Ohio REALTORS\u00ae" height="45" width="120" loading="lazy">
        </a>
      </div>

      <div class="footer-bottom">
        <div class="footer-legal">
          <a href="/privacy/">Privacy Policy</a>
          <a href="/terms/">Terms of Service</a>
          <a href="/fair-housing/">Fair Housing</a>
          <a href="/sitemap-page/">Site Map</a>
        </div>
      </div>

      <div class="footer-license">
        TD Realty Ohio, LLC | Broker: Travis Debnam | Broker License #2023006467 | Brokerage License #2023006602<br>
        Member of Columbus REALTORS, Ohio REALTORS, and the National Association of REALTORS
      </div>
    </div>
  </footer>

  <script src="/assets/js/main.js"></script>
</body>
</html>
'''


def generate_blog_card(frontmatter: dict, slug: str) -> str:
    """Generate blog card HTML for the blog index page."""
    title = frontmatter.get('title', 'Blog Post')
    description = frontmatter.get('description', '')
    date_raw = frontmatter.get('date', '')
    community = frontmatter.get('community', '')

    try:
        date_obj = datetime.strptime(str(date_raw), '%Y-%m-%d')
        date_display = date_obj.strftime('%B %Y')
    except ValueError:
        date_display = str(date_raw)

    short_title = title if len(title) < 60 else title[:57] + '...'

    return f'''          <article class="blog-card">
            <h3><a href="/blog/{slug}/">{html.escape(title)}</a></h3>
            <p class="post-meta">By Travis Debnam | {date_display}</p>
            <p>{html.escape(description)}</p>
            <a href="/blog/{slug}/" class="read-more">Read: {html.escape(short_title)}</a>
          </article>'''


def main():
    parser = argparse.ArgumentParser(description="Convert optimized markdown to tdrealtyohio.com HTML")
    parser.add_argument("--input", required=True, help="Path to FINAL.md or any markdown blog post")
    parser.add_argument("--output-repo", default=None,
                        help="Path to tdrealtyohio.com repo (will create blog post directory)")
    parser.add_argument("--slug", default=None, help="Custom URL slug (auto-generated from title if omitted)")
    parser.add_argument("--dry-run", action="store_true", help="Print HTML to stdout instead of writing files")

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    content = input_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    if args.slug:
        slug = args.slug
    else:
        title = frontmatter.get('title', 'blog-post')
        slug = slugify(title)
        # Trim to reasonable URL length
        if len(slug) > 60:
            slug = slug[:60].rsplit('-', 1)[0]

    html_content = build_html(frontmatter, body, slug)

    if args.dry_run:
        print(html_content)
        return

    if args.output_repo:
        repo_path = Path(args.output_repo)
        blog_dir = repo_path / "blog" / slug
        blog_dir.mkdir(parents=True, exist_ok=True)
        output_file = blog_dir / "index.html"
        output_file.write_text(html_content)
        print(f"Created: {output_file}")

        # Generate blog card snippet for index page
        card = generate_blog_card(frontmatter, slug)
        print(f"\nBlog card HTML (add to blog/index.html):\n")
        print(card)
    else:
        # Write next to the input file
        output_file = input_path.parent / f"{slug}.html"
        output_file.write_text(html_content)
        print(f"Created: {output_file}")

    print(f"\nSlug: {slug}")
    print(f"URL:  https://tdrealtyohio.com/blog/{slug}/")


if __name__ == "__main__":
    main()
