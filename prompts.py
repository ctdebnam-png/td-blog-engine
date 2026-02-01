"""
Prompt templates for SEO blog post generation and iterative improvement.
"""

from config import BUSINESS


def get_generation_prompt(
    primary_keyword: str,
    community: str,
    content_type: str,
    content_type_description: str,
    year: int = 2025,
) -> str:
    communities_list = ", ".join(BUSINESS["communities"])
    services_list = "\n".join(f"  - {s}" for s in BUSINESS["services"])

    return f"""You are an expert real estate SEO content writer creating a blog post for TD Realty Ohio, LLC — a discount real estate brokerage serving Central Ohio since 2017.

## BUSINESS CONTEXT

- Company: {BUSINESS['name']}
- Website: {BUSINESS['url']}
- Services:
  {services_list}
- Communities served: {communities_list}
- Phone: {BUSINESS['phone']}

## ASSIGNMENT

Write a **{content_type_description}** blog post targeting the community of **{community}, Ohio**.

## TARGET KEYWORD

Primary keyword: **{primary_keyword}**

## REQUIREMENTS

### Format

- Output as a complete markdown file with YAML frontmatter
- Frontmatter MUST include: title, description (meta description, 140-160 chars), date, keywords (array), author (TD Realty Ohio), community, category

### Content Requirements

- Target word count: 1,500-2,500 words
- Use the primary keyword naturally throughout (0.8%-2.0% density)
- Include the keyword in: title, first 100 words, at least one H2, and meta description
- Use 3-6 H2 headings with H3 sub-sections for depth
- Include concrete local details: school districts, parks, ZIP codes, landmarks, neighborhoods
- Reference nearby communities ({communities_list}) for cross-linking
- Include market statistics, data points, and percentage comparisons
- Add an FAQ section with 3-5 common questions
- Include 2-3 natural calls to action referencing TD Realty's services
- Add 3-5 internal links using markdown format pointing to tdrealtyohio.com pages:
  - Link to community pages: /communities/[community-name]
  - Link to service pages: /services, /sell-your-home, /buy-a-home
  - Link to other blog posts: /blog/[topic]

### Tone & Style

- Professional but approachable — like a knowledgeable local expert
- Avoid generic filler content — every paragraph should provide real value
- Vary sentence length for natural reading rhythm
- Use data to support claims rather than vague statements
- DO NOT use the word "nestled" or other cliche real estate language

### SEO Structure

- One H1 (the title in frontmatter handles this)
- 3-6 H2 sections
- H3 sub-sections where appropriate
- Short paragraphs (2-4 sentences) for web readability
- Logical heading hierarchy (never skip levels)

Write the complete blog post now. Output ONLY the markdown content starting with the --- frontmatter delimiter. No additional commentary."""


def get_improvement_prompt(
    content: str,
    score_report_dict: dict,
    primary_keyword: str,
    community: str,
    iteration: int,
) -> str:
    categories = sorted(score_report_dict["categories"], key=lambda x: x["percentage"])
    worst_3 = categories[:3]

    improvement_instructions = []
    for cat in worst_3:
        if cat["suggestions"]:
            improvement_instructions.append(
                f"**{cat['category']}** (scored {cat['score']}/{cat['max_score']} = {cat['percentage']:.0f}%):\n"
                + "\n".join(f"  - {s}" for s in cat["suggestions"])
            )

    all_suggestions = []
    for cat in categories:
        for s in cat["suggestions"]:
            all_suggestions.append(f"[{cat['category']}] {s}")

    return f"""You are improving an SEO blog post for TD Realty Ohio, LLC targeting **{community}, Ohio** with primary keyword **"{primary_keyword}"**.

## CURRENT SCORE: {score_report_dict['total_score']}/{score_report_dict['max_possible']} ({score_report_dict['percentage']:.1f}%)

This is improvement iteration #{iteration}.

## PRIORITY IMPROVEMENT AREAS (lowest-scoring categories):

{chr(10).join(improvement_instructions)}

## ALL SUGGESTIONS:

{chr(10).join(f"- {s}" for s in all_suggestions)}

## FULL SCORE BREAKDOWN:

{chr(10).join(f"- {cat['category']}: {cat['score']}/{cat['max_score']} ({cat['percentage']:.0f}%)" for cat in categories)}

## CURRENT BLOG POST:

```markdown
{content}
```

## INSTRUCTIONS

Rewrite the blog post to address the improvement suggestions above, focusing especially on the 3 lowest-scoring categories. Important rules:

- Keep all improvements that scored well — don't regress on high-scoring areas
- Maintain natural, readable prose — don't sacrifice quality for metrics
- Stay within 1,500-2,500 words
- Keep keyword usage natural (0.8%-2.0% density)
- Preserve the YAML frontmatter format
- DO NOT use the word "nestled" or cliche real estate filler

Output ONLY the complete improved markdown blog post starting with the --- frontmatter delimiter. No additional commentary."""
