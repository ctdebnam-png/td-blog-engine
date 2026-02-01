#!/usr/bin/env python3
"""
Batch runner — generate optimized blog posts for multiple communities.

Usage:
    python batch.py --type community_guide --communities Westerville Dublin Powell
    python batch.py --type market_update --all
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from config import BUSINESS, CONTENT_TYPES
from optimizer import run_optimization


def main():
    parser = argparse.ArgumentParser(description="Batch generate optimized blog posts")
    parser.add_argument("--type", dest="content_type", default="community_guide",
                        help=f"Content type: {', '.join(CONTENT_TYPES.keys())}")
    parser.add_argument("--communities", nargs="+", help="Specific communities")
    parser.add_argument("--all", action="store_true", help="All configured communities")
    parser.add_argument("--iterations", type=int, default=5, help="Iterations per post (default: 5)")
    parser.add_argument("--model", default="claude-sonnet-4-5-20250929", help="Anthropic model")

    args = parser.parse_args()

    if args.all:
        communities = BUSINESS["communities"]
    elif args.communities:
        communities = args.communities
    else:
        print("Specify --communities or --all")
        sys.exit(1)

    print(f"\n{'='*70}")
    print(f"  BATCH SEO BLOG GENERATION")
    print(f"  Content type: {args.content_type}")
    print(f"  Communities:  {len(communities)}")
    print(f"  Iterations:   {args.iterations} per post")
    print(f"{'='*70}\n")

    results = []
    for i, community in enumerate(communities, 1):
        print(f"\n{'─'*70}")
        print(f"  [{i}/{len(communities)}] {community}")
        print(f"{'─'*70}")
        try:
            result = run_optimization(
                community=community, content_type=args.content_type,
                iterations=args.iterations, model=args.model, verbose=True,
            )
            results.append({
                "community": community, "status": "success",
                "best_score": result["best_score"], "iterations": result["iterations_run"],
                "improvement": result["all_scores"][-1] - result["all_scores"][0] if len(result["all_scores"]) > 1 else 0,
                "output": result["final_path"],
            })
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results.append({"community": community, "status": "error", "error": str(e)})

    # Summary
    print(f"\n\n{'='*70}")
    print(f"  BATCH RESULTS")
    print(f"{'='*70}\n")
    success = [r for r in results if r["status"] == "success"]
    if success:
        avg_score = sum(r["best_score"] for r in success) / len(success)
        avg_imp = sum(r["improvement"] for r in success) / len(success)
        print(f"  Successful: {len(success)}/{len(results)}")
        print(f"  Avg score:  {avg_score:.1f}/100")
        print(f"  Avg improvement: {avg_imp:+.1f}\n")
        for r in sorted(success, key=lambda x: x["best_score"], reverse=True):
            bar_len = int(r["best_score"] / 2.5)
            bar = "█" * bar_len + "░" * (40 - bar_len)
            print(f"  {r['community']:<20} {bar} {r['best_score']:.1f} ({r['improvement']:+.1f})")

    report_path = Path("output") / f"batch_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(results, indent=2))
    print(f"\n  Report: {report_path}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    main()
