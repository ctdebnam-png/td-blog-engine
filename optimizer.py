#!/usr/bin/env python3
"""
SEO Blog Optimizer — Recursive Self-Improvement Engine

Usage:
    python optimizer.py --community "Westerville" --type community_guide
    python optimizer.py --community "Powell" --keyword "homes for sale in Powell Ohio 2026" --iterations 8
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic

from config import BUSINESS, CONTENT_TYPES, ITERATIONS, OUTPUT
from scoring import score_post
from prompts import get_generation_prompt, get_improvement_prompt


def call_claude(client: anthropic.Anthropic, prompt: str, model: str) -> str:
    message = client.messages.create(
        model=model,
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def extract_markdown(response: str) -> str:
    if "```markdown" in response:
        start = response.index("```markdown") + len("```markdown")
        end = response.rindex("```")
        return response[start:end].strip()
    elif "```" in response and response.strip().startswith("```"):
        start = response.index("\n") + 1
        end = response.rindex("```")
        return response[start:end].strip()
    if response.strip().startswith("---"):
        return response.strip()
    return response.strip()


def run_optimization(
    community: str,
    content_type: str = "community_guide",
    primary_keyword: str | None = None,
    iterations: int | None = None,
    model: str = "claude-sonnet-4-5-20250929",
    output_dir: str | None = None,
    verbose: bool = True,
) -> dict:
    if content_type not in CONTENT_TYPES:
        print(f"Unknown content type: {content_type}")
        print(f"Available: {', '.join(CONTENT_TYPES.keys())}")
        sys.exit(1)

    ct = CONTENT_TYPES[content_type]
    year = datetime.now().year

    if not primary_keyword:
        primary_keyword = ct["target_keywords_pattern"].format(community=community, year=year)
    if iterations is None:
        iterations = ITERATIONS["default_count"]
    iterations = min(iterations, ITERATIONS["max_count"])

    if output_dir is None:
        output_dir = OUTPUT["dir"]
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    slug = f"{community.lower().replace(' ', '-')}-{content_type.replace('_', '-')}"
    run_dir = out_path / slug
    run_dir.mkdir(parents=True, exist_ok=True)

    client = anthropic.Anthropic()

    if verbose:
        print(f"\n{'='*70}")
        print(f"  SEO BLOG OPTIMIZER — RECURSIVE IMPROVEMENT ENGINE")
        print(f"{'='*70}")
        print(f"  Community:    {community}, Ohio")
        print(f"  Content Type: {ct['description']}")
        print(f"  Keyword:      {primary_keyword}")
        print(f"  Model:        {model}")
        print(f"  Iterations:   {iterations}")
        print(f"  Output:       {run_dir}")
        print(f"{'='*70}\n")

    # ── ITERATION 0: Generate initial version ────────────────────────
    if verbose:
        print("▶ Generating initial version (v0)...")

    gen_prompt = get_generation_prompt(
        primary_keyword=primary_keyword, community=community,
        content_type=content_type, content_type_description=ct["description"], year=year,
    )

    start_time = time.time()
    response = call_claude(client, gen_prompt, model)
    gen_time = time.time() - start_time

    content = extract_markdown(response)
    report = score_post(content, primary_keyword, community, iteration=0)

    if verbose:
        print(f"  Generated in {gen_time:.1f}s")
        print(f"\n{report.summary()}\n")

    if OUTPUT["save_all_versions"]:
        (run_dir / "v0.md").write_text(content)
        (run_dir / "v0_score.json").write_text(json.dumps(report.to_dict(), indent=2))

    history = [{
        "iteration": 0, "score": report.total_score, "percentage": report.percentage,
        "generation_time": gen_time,
        "category_scores": {d.category: d.score for d in report.details},
    }]

    best_content = content
    best_score = report.total_score
    best_iteration = 0
    plateau_count = 0

    # ── ITERATIONS 1-N: Recursive improvement ────────────────────────
    for i in range(1, iterations + 1):
        if verbose:
            print(f"▶ Improvement iteration {i}/{iterations}...")

        improvement_prompt = get_improvement_prompt(
            content=content, score_report_dict=report.to_dict(),
            primary_keyword=primary_keyword, community=community, iteration=i,
        )

        start_time = time.time()
        response = call_claude(client, improvement_prompt, model)
        iter_time = time.time() - start_time

        new_content = extract_markdown(response)
        new_report = score_post(new_content, primary_keyword, community, iteration=i)
        improvement = new_report.total_score - report.total_score

        if verbose:
            print(f"  Completed in {iter_time:.1f}s")
            print(f"\n{new_report.summary()}")
            delta = "↑" if improvement > 0 else "↓" if improvement < 0 else "→"
            print(f"\n  {delta} Change from last iteration: {improvement:+.1f} points\n")

        if OUTPUT["save_all_versions"]:
            (run_dir / f"v{i}.md").write_text(new_content)
            (run_dir / f"v{i}_score.json").write_text(json.dumps(new_report.to_dict(), indent=2))

        history.append({
            "iteration": i, "score": new_report.total_score, "percentage": new_report.percentage,
            "generation_time": iter_time, "improvement": improvement,
            "category_scores": {d.category: d.score for d in new_report.details},
        })

        if new_report.total_score > best_score:
            best_content = new_content
            best_score = new_report.total_score
            best_iteration = i
            plateau_count = 0
        else:
            plateau_count += 1

        content = new_content
        report = new_report

        if plateau_count >= ITERATIONS["plateau_patience"]:
            if verbose:
                print(f"  ⚠ Plateau detected — no improvement for {plateau_count} iterations. Stopping.\n")
            break

    # ── FINALIZE ─────────────────────────────────────────────────────
    final_path = run_dir / "FINAL.md"
    final_path.write_text(best_content)

    summary = {
        "community": community, "content_type": content_type,
        "primary_keyword": primary_keyword, "model": model,
        "best_score": best_score, "best_iteration": best_iteration,
        "total_iterations": len(history) - 1, "history": history,
        "timestamp": datetime.now().isoformat(),
    }
    (run_dir / "run_summary.json").write_text(json.dumps(summary, indent=2))

    if verbose:
        print(f"\n{'='*70}")
        print(f"  OPTIMIZATION COMPLETE")
        print(f"{'='*70}")
        print(f"  Best score:     {best_score:.1f}/100 ({best_score:.1f}%)")
        print(f"  Best iteration: v{best_iteration}")
        print(f"  Improvement:    {best_score - history[0]['score']:+.1f} points from v0")
        print(f"  Output:         {final_path}")
        print()
        print("  SCORE PROGRESSION:")
        for h in history:
            bar_len = int(h["percentage"] / 2.5)
            bar = "█" * bar_len + "░" * (40 - bar_len)
            delta = f" ({h.get('improvement', 0):+.1f})" if "improvement" in h else ""
            print(f"    v{h['iteration']}: {bar} {h['score']:.1f}{delta}")
        print(f"{'='*70}\n")

    return {
        "best_content": best_content, "best_score": best_score,
        "best_iteration": best_iteration,
        "all_scores": [h["score"] for h in history],
        "iterations_run": len(history) - 1,
        "improvement_history": history,
        "output_dir": str(run_dir), "final_path": str(final_path),
    }


def main():
    parser = argparse.ArgumentParser(description="SEO Blog Optimizer for TD Realty Ohio")
    parser.add_argument("--community", required=True, help=f"Target community: {', '.join(BUSINESS['communities'])}")
    parser.add_argument("--type", dest="content_type", default="community_guide",
                        help=f"Content type: {', '.join(CONTENT_TYPES.keys())}")
    parser.add_argument("--keyword", help="Custom primary keyword (auto-generated if omitted)")
    parser.add_argument("--iterations", type=int, default=None,
                        help=f"Improvement iterations (default: {ITERATIONS['default_count']})")
    parser.add_argument("--model", default="claude-sonnet-4-5-20250929", help="Anthropic model")
    parser.add_argument("--output-dir", default=None, help=f"Output directory (default: {OUTPUT['dir']})")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose output")

    args = parser.parse_args()

    if args.community not in BUSINESS["communities"]:
        match = next((c for c in BUSINESS["communities"] if c.lower() == args.community.lower()), None)
        if match:
            args.community = match
        else:
            print(f"Warning: '{args.community}' not in configured communities. Proceeding anyway.")

    run_optimization(
        community=args.community, content_type=args.content_type,
        primary_keyword=args.keyword, iterations=args.iterations,
        model=args.model, output_dir=args.output_dir, verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
