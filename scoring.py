"""
SEO Scoring Engine for blog post evaluation.
"""

import re
import json
import yaml
from dataclasses import dataclass, field
from typing import Optional

from config import SCORING, BUSINESS


@dataclass
class ScoreDetail:
    category: str
    score: float
    max_score: float
    percentage: float
    findings: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


@dataclass
class ScoreReport:
    total_score: float
    max_possible: float
    percentage: float
    details: list[ScoreDetail] = field(default_factory=list)
    iteration: int = 0

    def to_dict(self) -> dict:
        return {
            "total_score": round(self.total_score, 1),
            "max_possible": self.max_possible,
            "percentage": round(self.percentage, 1),
            "iteration": self.iteration,
            "categories": [
                {
                    "category": d.category,
                    "score": round(d.score, 1),
                    "max_score": d.max_score,
                    "percentage": round(d.percentage, 1),
                    "findings": d.findings,
                    "suggestions": d.suggestions,
                }
                for d in self.details
            ],
        }

    def summary(self) -> str:
        lines = [
            f"═══ ITERATION {self.iteration} — TOTAL: {self.total_score:.1f}/{self.max_possible} ({self.percentage:.1f}%) ═══",
            "",
        ]
        for d in sorted(self.details, key=lambda x: x.percentage):
            bar_len = int(d.percentage / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"  {d.category:<22} {bar} {d.score:.1f}/{d.max_score} ({d.percentage:.0f}%)")
        lines.append("")
        worst = sorted(self.details, key=lambda x: x.percentage)[:3]
        lines.append("  TOP IMPROVEMENT AREAS:")
        for d in worst:
            if d.suggestions:
                lines.append(f"    → {d.category}: {d.suggestions[0]}")
        return "\n".join(lines)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    frontmatter = {}
    body = content
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)$', content, re.DOTALL)
    if fm_match:
        try:
            frontmatter = yaml.safe_load(fm_match.group(1)) or {}
        except yaml.YAMLError:
            frontmatter = {}
        body = fm_match.group(2)
    return frontmatter, body


def count_words(text: str) -> int:
    clean = re.sub(r'[#*\[\]()>`_~]', ' ', text)
    clean = re.sub(r'https?://\S+', '', clean)
    return len(clean.split())


def extract_headings(body: str) -> dict[str, list[str]]:
    headings = {"h1": [], "h2": [], "h3": [], "h4": []}
    for line in body.split("\n"):
        line = line.strip()
        if line.startswith("#### "):
            headings["h4"].append(line[5:].strip())
        elif line.startswith("### "):
            headings["h3"].append(line[4:].strip())
        elif line.startswith("## "):
            headings["h2"].append(line[3:].strip())
        elif line.startswith("# "):
            headings["h1"].append(line[2:].strip())
    return headings


def extract_sentences(text: str) -> list[str]:
    clean = re.sub(r'[#*>\[\]()]', '', text)
    clean = re.sub(r'https?://\S+', '', clean)
    sentences = re.split(r'[.!?]+\s+', clean)
    return [s.strip() for s in sentences if len(s.strip().split()) > 2]


def extract_paragraphs(body: str) -> list[str]:
    paragraphs = []
    current = []
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            if current:
                text = " ".join(current)
                if not text.startswith("#") and len(text.split()) > 5:
                    paragraphs.append(text)
                current = []
        elif not stripped.startswith("#") and not stripped.startswith("---"):
            current.append(stripped)
    if current:
        text = " ".join(current)
        if not text.startswith("#") and len(text.split()) > 5:
            paragraphs.append(text)
    return paragraphs


def score_word_count(body: str) -> ScoreDetail:
    cfg = SCORING["word_count"]
    wc = count_words(body)
    weight = cfg["weight"]
    findings = [f"Word count: {wc}"]
    suggestions = []
    if cfg["target_min"] <= wc <= cfg["target_max"]:
        score = weight
        findings.append(f"✓ Within target range ({cfg['target_min']}-{cfg['target_max']})")
    elif cfg["hard_min"] <= wc < cfg["target_min"]:
        ratio = (wc - cfg["hard_min"]) / (cfg["target_min"] - cfg["hard_min"])
        score = weight * (0.5 + 0.5 * ratio)
        suggestions.append(f"Add {cfg['target_min'] - wc} more words to reach minimum target of {cfg['target_min']}")
    elif cfg["target_max"] < wc <= cfg["hard_max"]:
        ratio = (cfg["hard_max"] - wc) / (cfg["hard_max"] - cfg["target_max"])
        score = weight * (0.5 + 0.5 * ratio)
        suggestions.append(f"Trim {wc - cfg['target_max']} words — content over {cfg['target_max']} words can hurt engagement")
    else:
        score = weight * 0.2
        if wc < cfg["hard_min"]:
            suggestions.append(f"Significantly below minimum. Target at least {cfg['target_min']} words")
        else:
            suggestions.append(f"Significantly over maximum. Target under {cfg['target_max']} words")
    return ScoreDetail(category="Word Count", score=score, max_score=weight,
                       percentage=(score / weight) * 100, findings=findings, suggestions=suggestions)


def score_keyword_optimization(body: str, frontmatter: dict, primary_keyword: str) -> ScoreDetail:
    cfg = SCORING["keyword_optimization"]
    weight = cfg["weight"]
    points = 0
    per_check = weight / 5
    findings = []
    suggestions = []
    kw_lower = primary_keyword.lower()

    title = frontmatter.get("title", "")
    if kw_lower in title.lower():
        points += per_check
        findings.append("✓ Primary keyword in title")
    else:
        suggestions.append(f"Include '{primary_keyword}' in the post title")
        findings.append("✗ Primary keyword missing from title")

    words = body.split()
    first_100 = " ".join(words[:100]).lower()
    if kw_lower in first_100:
        points += per_check
        findings.append("✓ Keyword in first 100 words")
    else:
        suggestions.append(f"Mention '{primary_keyword}' within the first 100 words/opening paragraph")
        findings.append("✗ Keyword missing from first 100 words")

    headings = extract_headings(body)
    all_headings = " ".join(h for hlist in headings.values() for h in hlist).lower()
    if kw_lower in all_headings:
        points += per_check
        findings.append("✓ Keyword appears in headings")
    else:
        suggestions.append(f"Use '{primary_keyword}' (or close variant) in at least one H2 subheading")
        findings.append("✗ Keyword missing from all headings")

    total_words = count_words(body)
    if total_words > 0:
        kw_count = len(re.findall(re.escape(kw_lower), body.lower()))
        kw_word_count = len(kw_lower.split())
        density = (kw_count * kw_word_count) / total_words
        findings.append(f"Keyword density: {density:.3f} ({density*100:.1f}%)")
        if cfg["target_density_min"] <= density <= cfg["target_density_max"]:
            points += per_check
            findings.append("✓ Keyword density in optimal range")
        elif density < cfg["target_density_min"]:
            points += per_check * 0.4
            suggestions.append(f"Increase keyword usage — density {density*100:.1f}% is below {cfg['target_density_min']*100:.1f}% target")
        else:
            points += per_check * 0.3
            suggestions.append(f"Reduce keyword stuffing — density {density*100:.1f}% exceeds {cfg['target_density_max']*100:.1f}% ceiling")

    meta_desc = frontmatter.get("description", "")
    if kw_lower in meta_desc.lower():
        points += per_check
        findings.append("✓ Keyword in meta description")
    else:
        suggestions.append(f"Include '{primary_keyword}' in the meta description")
        findings.append("✗ Keyword missing from meta description")

    return ScoreDetail(category="Keyword Optimization", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_heading_structure(body: str) -> ScoreDetail:
    cfg = SCORING["heading_structure"]
    weight = cfg["weight"]
    points = 0
    per_check = weight / 4
    findings = []
    suggestions = []
    headings = extract_headings(body)

    h1_count = len(headings["h1"])
    if h1_count <= 1:
        points += per_check
        findings.append(f"✓ H1 count: {h1_count} (appropriate)")
    else:
        suggestions.append(f"Reduce to 1 H1 tag — found {h1_count}")
        findings.append(f"✗ Multiple H1 tags: {h1_count}")

    h2_count = len(headings["h2"])
    findings.append(f"H2 count: {h2_count}")
    if cfg["target_h2_count_min"] <= h2_count <= cfg["target_h2_count_max"]:
        points += per_check
        findings.append(f"✓ H2 count in target range ({cfg['target_h2_count_min']}-{cfg['target_h2_count_max']})")
    elif h2_count > 0:
        points += per_check * 0.5
        if h2_count < cfg["target_h2_count_min"]:
            suggestions.append(f"Add more H2 sections — have {h2_count}, target {cfg['target_h2_count_min']}+")
        else:
            suggestions.append(f"Consolidate sections — {h2_count} H2s may fragment the content")
    else:
        suggestions.append("Add H2 subheadings to break up content into scannable sections")

    h3_count = len(headings["h3"])
    findings.append(f"H3 count: {h3_count}")
    if h3_count >= cfg["target_h3_count_min"]:
        points += per_check
        findings.append("✓ Content has sub-section depth with H3s")
    elif h3_count > 0:
        points += per_check * 0.6
        suggestions.append(f"Add more H3 sub-sections for depth — have {h3_count}, target {cfg['target_h3_count_min']}+")
    else:
        suggestions.append("Add H3 sub-sections under H2s for better content hierarchy")

    hierarchy_ok = True
    last_level = 0
    for line in body.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#### "):
            level = 4
        elif stripped.startswith("### "):
            level = 3
        elif stripped.startswith("## "):
            level = 2
        elif stripped.startswith("# "):
            level = 1
        else:
            continue
        if level > last_level + 1 and last_level > 0:
            hierarchy_ok = False
        last_level = level

    if hierarchy_ok:
        points += per_check
        findings.append("✓ Heading hierarchy is logical")
    else:
        points += per_check * 0.3
        suggestions.append("Fix heading hierarchy — don't skip levels (e.g., H2 → H4)")

    return ScoreDetail(category="Heading Structure", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_readability(body: str) -> ScoreDetail:
    cfg = SCORING["readability"]
    weight = cfg["weight"]
    points = 0
    per_check = weight / 3
    findings = []
    suggestions = []
    sentences = extract_sentences(body)
    paragraphs = extract_paragraphs(body)

    if sentences:
        avg_sentence_len = sum(len(s.split()) for s in sentences) / len(sentences)
        findings.append(f"Average sentence length: {avg_sentence_len:.1f} words")
        if cfg["target_avg_sentence_length_min"] <= avg_sentence_len <= cfg["target_avg_sentence_length_max"]:
            points += per_check
            findings.append("✓ Sentence length in optimal range")
        elif avg_sentence_len < cfg["target_avg_sentence_length_min"]:
            points += per_check * 0.6
            suggestions.append("Sentences are too short — combine some for better flow and depth")
        else:
            points += per_check * 0.5
            suggestions.append(f"Average sentence too long ({avg_sentence_len:.0f} words). Break up complex sentences")
    else:
        suggestions.append("Could not parse sentences — check content formatting")

    if paragraphs:
        para_sentence_counts = []
        for p in paragraphs:
            p_sentences = re.split(r'[.!?]+\s+', p)
            para_sentence_counts.append(len([s for s in p_sentences if len(s.split()) > 2]))
        avg_para = sum(para_sentence_counts) / len(para_sentence_counts)
        findings.append(f"Average paragraph length: {avg_para:.1f} sentences")
        if cfg["target_avg_paragraph_sentences_min"] <= avg_para <= cfg["target_avg_paragraph_sentences_max"]:
            points += per_check
            findings.append("✓ Paragraph length in optimal range")
        else:
            points += per_check * 0.5
            if avg_para < cfg["target_avg_paragraph_sentences_min"]:
                suggestions.append("Paragraphs are too short — combine related sentences")
            else:
                suggestions.append("Paragraphs are too long — break into smaller chunks for web readability")

    if len(sentences) > 3:
        lens = [len(s.split()) for s in sentences]
        mean_len = sum(lens) / len(lens)
        variance = sum((x - mean_len) ** 2 for x in lens) / len(lens)
        std_dev = variance ** 0.5
        findings.append(f"Sentence length variety (std dev): {std_dev:.1f}")
        if std_dev > 5:
            points += per_check
            findings.append("✓ Good sentence length variety")
        elif std_dev > 3:
            points += per_check * 0.6
            suggestions.append("Vary sentence lengths more — mix short punchy sentences with longer ones")
        else:
            points += per_check * 0.3
            suggestions.append("Sentences are too uniform in length — monotonous reading rhythm")

    return ScoreDetail(category="Readability", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_local_seo(body: str, community: str) -> ScoreDetail:
    cfg = SCORING["local_seo"]
    weight = cfg["weight"]
    points = 0
    per_check = weight / 4
    findings = []
    suggestions = []
    body_lower = body.lower()

    community_count = len(re.findall(re.escape(community.lower()), body_lower))
    findings.append(f"Community name '{community}' mentions: {community_count}")
    if community_count >= cfg["community_mention_min"]:
        points += per_check
        findings.append("✓ Sufficient community mentions")
    elif community_count > 0:
        points += per_check * 0.5
        suggestions.append(f"Mention '{community}' more — found {community_count}, target {cfg['community_mention_min']}+")
    else:
        suggestions.append(f"'{community}' doesn't appear in body text — critical for local SEO")

    region_hits = [term for term in cfg["region_terms"] if term.lower() in body_lower]
    findings.append(f"Regional terms found: {len(region_hits)}/{len(cfg['region_terms'])}")
    if len(region_hits) >= 3:
        points += per_check
        findings.append(f"✓ Good regional context: {', '.join(region_hits[:5])}")
    elif len(region_hits) >= 1:
        points += per_check * 0.5
        missing = [t for t in cfg["region_terms"] if t not in region_hits][:3]
        suggestions.append(f"Add more regional context. Consider: {', '.join(missing)}")
    else:
        suggestions.append("No regional terms found — add Central Ohio, county, landmark references")

    other_communities = [c for c in BUSINESS["communities"] if c.lower() != community.lower()]
    nearby_mentions = [c for c in other_communities if c.lower() in body_lower]
    findings.append(f"Nearby community mentions: {len(nearby_mentions)}")
    if len(nearby_mentions) >= 2:
        points += per_check
        findings.append(f"✓ References other communities: {', '.join(nearby_mentions[:4])}")
    elif len(nearby_mentions) == 1:
        points += per_check * 0.5
        suggestions.append("Reference more nearby communities for internal linking opportunities")
    else:
        suggestions.append(f"Mention nearby communities (e.g., {', '.join(other_communities[:3])}) for cross-linking")

    local_signals = [
        r'\b\d{5}\b', r'school district', r'elementary|middle school|high school',
        r'park\b|trail\b|recreation', r'downtown\s+\w+', r'library|community center',
        r'interstate|highway|route\s+\d+',
    ]
    signal_count = sum(1 for p in local_signals if re.search(p, body_lower))
    findings.append(f"Local detail signals found: {signal_count}/{len(local_signals)}")
    if signal_count >= 3:
        points += per_check
        findings.append("✓ Strong local detail signals")
    elif signal_count >= 1:
        points += per_check * 0.5
        suggestions.append("Add more hyperlocal details — school districts, parks, ZIP codes, landmarks")
    else:
        suggestions.append("Content lacks local specificity — add school districts, parks, ZIP codes")

    return ScoreDetail(category="Local SEO", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_meta_description(frontmatter: dict, primary_keyword: str) -> ScoreDetail:
    cfg = SCORING["meta_description"]
    weight = cfg["weight"]
    points = 0
    per_check = weight / 4
    findings = []
    suggestions = []
    desc = frontmatter.get("description", "")

    if not desc:
        suggestions.append("Add a meta description in frontmatter — critical for search results CTR")
        return ScoreDetail(category="Meta Description", score=0, max_score=weight, percentage=0,
                           findings=["✗ No meta description found"], suggestions=suggestions)

    findings.append(f"Meta description length: {len(desc)} chars")
    if cfg["target_length_min"] <= len(desc) <= cfg["target_length_max"]:
        points += per_check
        findings.append(f"✓ Length in optimal range ({cfg['target_length_min']}-{cfg['target_length_max']})")
    elif 100 <= len(desc) < cfg["target_length_min"]:
        points += per_check * 0.6
        suggestions.append(f"Meta description slightly short ({len(desc)} chars). Target {cfg['target_length_min']}-{cfg['target_length_max']}")
    elif cfg["target_length_max"] < len(desc) <= 200:
        points += per_check * 0.5
        suggestions.append(f"Meta description too long ({len(desc)} chars) — will be truncated")
    else:
        suggestions.append(f"Meta description length ({len(desc)}) far from optimal. Target {cfg['target_length_min']}-{cfg['target_length_max']}")

    if primary_keyword.lower() in desc.lower():
        points += per_check
        findings.append("✓ Contains primary keyword")
    else:
        suggestions.append(f"Include '{primary_keyword}' in meta description")

    cta_patterns = [r'learn', r'discover', r'find out', r'explore', r'contact', r'call',
                    r'get started', r'see', r'browse', r'search', r'view', r'check out']
    if any(re.search(p, desc.lower()) for p in cta_patterns):
        points += per_check
        findings.append("✓ Contains action-oriented language")
    else:
        suggestions.append("Add a call-to-action in meta description")

    generic_patterns = [r'^this (article|post|blog|page)', r'^read (about|more)', r'^in this (article|post)']
    is_generic = any(re.search(p, desc.lower()) for p in generic_patterns)
    if not is_generic and len(desc) > 50:
        points += per_check
        findings.append("✓ Description appears unique and compelling")
    else:
        points += per_check * 0.3
        suggestions.append("Make meta description more compelling — avoid generic openings")

    return ScoreDetail(category="Meta Description", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_internal_linking(body: str, community: str) -> ScoreDetail:
    cfg = SCORING["internal_linking"]
    weight = cfg["weight"]
    points = 0
    per_check = weight / 3
    findings = []
    suggestions = []

    links = re.findall(r'\[([^\]]+)\]\(([^\)]+)\)', body)
    internal_links = [l for l in links if 'tdrealtyohio.com' in l[1] or l[1].startswith('/')]
    external_links = [l for l in links if l not in internal_links]
    findings.append(f"Internal links: {len(internal_links)}")
    findings.append(f"External links: {len(external_links)}")

    if cfg["target_min_links"] <= len(internal_links) <= cfg["target_max_links"]:
        points += per_check
        findings.append("✓ Internal link count in optimal range")
    elif len(internal_links) > 0:
        points += per_check * 0.5
        if len(internal_links) < cfg["target_min_links"]:
            suggestions.append(f"Add more internal links — have {len(internal_links)}, target {cfg['target_min_links']}+")
        else:
            suggestions.append(f"Too many internal links ({len(internal_links)}) — may appear spammy")
    else:
        suggestions.append("Add internal links to community and service pages on tdrealtyohio.com")

    service_keywords = ["commission", "listing", "buyer", "seller", "cashback", "inspection"]
    has_service_link = any(
        any(kw in anchor.lower() or kw in url.lower() for kw in service_keywords)
        for anchor, url in internal_links
    )
    if has_service_link:
        points += per_check
        findings.append("✓ Links to service/value proposition pages")
    else:
        suggestions.append("Add link to TD Realty's service pages (commission savings, free inspections, etc.)")

    other_communities = [c for c in BUSINESS["communities"] if c.lower() != community.lower()]
    community_links = []
    for anchor, url in internal_links:
        for c in other_communities:
            if c.lower() in anchor.lower() or c.lower() in url.lower():
                community_links.append(c)
    if community_links:
        points += per_check
        findings.append(f"✓ Cross-community links: {', '.join(set(community_links))}")
    else:
        suggestions.append(f"Add links to nearby community pages (e.g., {', '.join(other_communities[:3])})")

    return ScoreDetail(category="Internal Linking", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_content_depth(body: str) -> ScoreDetail:
    cfg = SCORING["content_depth"]
    weight = cfg["weight"]
    points = 0
    per_check = weight / 4
    findings = []
    suggestions = []
    headings = extract_headings(body)
    body_lower = body.lower()

    section_count = len(headings["h2"]) + len(headings["h3"])
    findings.append(f"Total sections (H2+H3): {section_count}")
    if section_count >= cfg["target_unique_sections"]:
        points += per_check
        findings.append("✓ Sufficient content sections")
    elif section_count >= 2:
        points += per_check * 0.5
        suggestions.append(f"Add more content sections — have {section_count}, target {cfg['target_unique_sections']}+")
    else:
        suggestions.append("Content needs more structured sections for depth")

    stat_patterns = [r'\d+%', r'\$[\d,]+', r'median', r'average', r'increased|decreased|grew|declined',
                     r'year-over-year|month-over-month|yoy|mom', r'according to|data shows|reports? (show|indicate)']
    stat_count = sum(1 for p in stat_patterns if re.search(p, body_lower))
    findings.append(f"Statistical/data signals: {stat_count}")
    if stat_count >= 3:
        points += per_check
        findings.append("✓ Content includes data and statistics")
    elif stat_count >= 1:
        points += per_check * 0.5
        suggestions.append("Add more market data, statistics, or percentage comparisons")
    else:
        suggestions.append("Include concrete statistics — median home prices, market trends, percentages")

    question_count = body.count("?")
    has_faq = bool(re.search(r'faq|frequently asked|common questions', body_lower))
    findings.append(f"Questions in content: {question_count}")
    if has_faq or question_count >= 3:
        points += per_check
        findings.append("✓ FAQ/question-based content present")
    elif question_count >= 1:
        points += per_check * 0.5
        suggestions.append("Add an FAQ section — great for featured snippets")
    else:
        suggestions.append("Add FAQ section with common homebuyer/seller questions")

    comparison_patterns = [r'pros? and cons?', r'compared? to', r'versus|vs\.?',
                           r'top \d+', r'best \d+', r'advantages|disadvantages']
    if any(re.search(p, body_lower) for p in comparison_patterns):
        points += per_check
        findings.append("✓ Comparative/evaluative content present")
    else:
        points += per_check * 0.3
        suggestions.append("Add comparative elements — how this community compares to alternatives")

    return ScoreDetail(category="Content Depth", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_cta(body: str) -> ScoreDetail:
    cfg = SCORING["call_to_action"]
    weight = cfg["weight"]
    findings = []
    suggestions = []

    cta_patterns = [r'contact\s+(us|td realty)', r'call\s+(us|today|now)', r'schedule\s+(a|your)',
                    r'get\s+(started|in touch|your free)', r'reach\s+out', r'book\s+(a|your)',
                    r'ready\s+to\s+(buy|sell|move|start|explore)', r'(visit|check out)\s+(our|tdrealtyohio)',
                    r'\(614\)', r'free\s+(consultation|estimate|home\s+valuation)',
                    r'save\s+thousands', r'1%\s+(listing|commission)']

    cta_count = sum(1 for p in cta_patterns if re.search(p, body.lower()))
    findings.append(f"CTAs detected: {cta_count}")

    if cfg["target_cta_count_min"] <= cta_count <= cfg["target_cta_count_max"]:
        points = weight
        findings.append("✓ CTA count in optimal range")
    elif cta_count > cfg["target_cta_count_max"]:
        points = weight * 0.7
        suggestions.append("Slightly too many CTAs — reduce to 2-3 natural touchpoints")
    elif cta_count == 1:
        points = weight * 0.5
        suggestions.append("Add another CTA — one mid-content and one at the end")
    else:
        points = 0
        suggestions.append("Add calls to action — invite readers to contact TD Realty")

    return ScoreDetail(category="Call to Action", score=points, max_score=weight,
                       percentage=(points / weight) * 100, findings=findings, suggestions=suggestions)


def score_frontmatter(frontmatter: dict) -> ScoreDetail:
    cfg = SCORING["frontmatter"]
    weight = cfg["weight"]
    findings = []
    suggestions = []

    present = [f for f in cfg["required_fields"] if f in frontmatter and frontmatter[f]]
    missing = [f for f in cfg["required_fields"] if f not in frontmatter or not frontmatter[f]]

    findings.append(f"Frontmatter fields present: {len(present)}/{len(cfg['required_fields'])}")
    if present:
        findings.append(f"✓ Has: {', '.join(present)}")
    if missing:
        findings.append(f"✗ Missing: {', '.join(missing)}")
        suggestions.append(f"Add missing frontmatter fields: {', '.join(missing)}")

    ratio = len(present) / len(cfg["required_fields"]) if cfg["required_fields"] else 0
    score = weight * ratio

    return ScoreDetail(category="Frontmatter", score=score, max_score=weight,
                       percentage=ratio * 100, findings=findings, suggestions=suggestions)


def score_post(content: str, primary_keyword: str, community: str, iteration: int = 0) -> ScoreReport:
    frontmatter, body = parse_frontmatter(content)
    details = [
        score_word_count(body),
        score_keyword_optimization(body, frontmatter, primary_keyword),
        score_heading_structure(body),
        score_readability(body),
        score_local_seo(body, community),
        score_meta_description(frontmatter, primary_keyword),
        score_internal_linking(body, community),
        score_content_depth(body),
        score_cta(body),
        score_frontmatter(frontmatter),
    ]
    total = sum(d.score for d in details)
    max_possible = sum(d.max_score for d in details)
    return ScoreReport(
        total_score=total, max_possible=max_possible,
        percentage=(total / max_possible) * 100 if max_possible > 0 else 0,
        details=details, iteration=iteration,
    )
