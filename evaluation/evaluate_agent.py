import argparse
import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from app import run_agent


def keyword_score(answer, required_keywords):
    if not required_keywords:
        return 1.0

    matched = [keyword for keyword in required_keywords if keyword in answer]
    return len(matched) / len(required_keywords)


def evaluate_case(case):
    answer = run_agent(case["task"])
    score = keyword_score(answer, case.get("required_keywords", []))

    return {
        "id": case["id"],
        "score": score,
        "passed": score >= 0.8,
        "answer": answer,
    }


def main():
    parser = argparse.ArgumentParser(description="Run simple evaluation cases for the AI Agent.")
    parser.add_argument(
        "--cases",
        default=str(ROOT_DIR / "evaluation" / "sample_cases.json"),
        help="Path to evaluation cases JSON file.",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT_DIR / "evaluation" / "results.json"),
        help="Path to save evaluation results.",
    )
    args = parser.parse_args()

    with open(args.cases, "r", encoding="utf-8") as file:
        cases = json.load(file)

    results = [evaluate_case(case) for case in cases]
    average_score = sum(result["score"] for result in results) / len(results)

    report = {
        "average_score": average_score,
        "results": results,
    }

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print(f"Evaluation complete. Average score: {average_score:.2f}")
    print(f"Saved results to {args.output}")


if __name__ == "__main__":
    main()
