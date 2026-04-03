"""
inference.py — OpenEnv-required entry point for baseline inference.

Thin wrapper around baseline/baseline.py. Runs the gpt-5.4-mini baseline
agent against all 3 tasks and prints results.

Usage:
    python inference.py
    python inference.py --seed 42
"""

import asyncio

from environment.engine import PTPAEngine
from server.session import SessionStore
from baseline.baseline import run_baseline_internal


def main():
    engine = PTPAEngine()
    store = SessionStore()

    result = asyncio.run(run_baseline_internal(engine, store))

    print(f"Model: {result.model_used}")
    print(f"Overall Score: {result.overall_score:.4f}")
    print()
    for tr in result.task_results:
        status = "PASS" if tr.success else "FAIL"
        print(f"  {tr.task_id.value}: {tr.final_score:.4f} ({tr.steps_taken} steps) [{status}]")


if __name__ == "__main__":
    main()
