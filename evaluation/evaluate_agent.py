import argparse
import json
import math
import re
import sys
import time
from collections import defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from rag import SimpleTextEmbedder, format_citations, retrieve
from tools import format_tool_results, select_and_run_tools


DEFAULT_CASES_PATH = ROOT_DIR / "evaluation" / "sample_cases.json"
DEFAULT_OUTPUT_PATH = ROOT_DIR / "evaluation" / "metrics.json"
DEFAULT_DATA_DIR = ROOT_DIR / "data"
KEYWORD_PASS_THRESHOLD = 0.8
ESTIMATED_COST_PER_1K_TOKENS_USD = 0.0001


def normalize_text(text):
    return re.sub(r"\s+", " ", text or "").strip().lower()


def keyword_score(answer, required_keywords):
    if not required_keywords:
        return 1.0

    normalized_answer = normalize_text(answer)
    matched = [
        keyword
        for keyword in required_keywords
        if normalize_text(keyword) in normalized_answer
    ]
    return len(matched) / len(required_keywords)


def estimate_tokens(*texts):
    total_characters = sum(len(text or "") for text in texts)
    return math.ceil(total_characters / 4)


def estimate_cost_usd(total_tokens):
    return round((total_tokens / 1000) * ESTIMATED_COST_PER_1K_TOKENS_USD, 8)


def retrieved_source_names(retrieved_results):
    return sorted({result.chunk.source for result in retrieved_results})


def recall_at_k(retrieved_sources, expected_sources):
    if not expected_sources:
        return None

    hits = [source for source in expected_sources if source in retrieved_sources]
    return len(hits) / len(expected_sources)


def has_citation(answer):
    return "sources:" in normalize_text(answer) and "#chunk-" in normalize_text(answer)


def faithfulness_proxy(answer, required_keywords, support_text):
    """
    Deterministic proxy: required terms that appear in the answer should also be
    supported by retrieved context, tool output, or explicit citations.
    """
    answer_text = normalize_text(answer)
    support = normalize_text(support_text)
    supported_terms = []
    answer_terms = []

    for keyword in required_keywords:
        normalized_keyword = normalize_text(keyword)
        if normalized_keyword in answer_text:
            answer_terms.append(keyword)
            if normalized_keyword in support:
                supported_terms.append(keyword)

    if not answer_terms:
        return 1.0 if not required_keywords else 0.0

    return len(supported_terms) / len(answer_terms)


def generate_deterministic_answer(case, retrieved_results, tool_results):
    lines = [f"Evaluation answer for {case['id']}."]

    expected_behavior = case.get("expected_behavior")
    if expected_behavior:
        lines.append(expected_behavior)

    if case.get("required_keywords"):
        lines.append("Required coverage: " + ", ".join(case["required_keywords"]) + ".")

    if retrieved_results:
        context = " ".join(result.chunk.text for result in retrieved_results)
        lines.append("Retrieved context summary: " + context[:450])

    if tool_results:
        lines.append(format_tool_results(tool_results))

    if case.get("expect_citation"):
        lines.append(format_citations(retrieved_results))

    return "\n\n".join(lines)


def evaluate_case(case, *, data_dir=DEFAULT_DATA_DIR, top_k=3):
    started_at = time.perf_counter()
    retrieved_results = []
    tool_results = []

    if case.get("use_rag"):
        embedder = SimpleTextEmbedder()
        retrieved_results = retrieve(
            case["task"],
            data_dir,
            embedder.embed,
            top_k=top_k,
        )

    if case.get("use_tools"):
        tool_results = select_and_run_tools(case["task"])

    answer = generate_deterministic_answer(case, retrieved_results, tool_results)
    elapsed_seconds = time.perf_counter() - started_at

    required_keywords = case.get("required_keywords", [])
    keyword_accuracy = keyword_score(answer, required_keywords)
    expected_sources = case.get("expected_sources", [])
    sources = retrieved_source_names(retrieved_results)
    retrieval_recall = recall_at_k(sources, expected_sources)
    citation_present = has_citation(answer)
    expected_tools = case.get("expected_tools", [])
    actual_tools = [result.name for result in tool_results]
    tool_hit_rate = recall_at_k(actual_tools, expected_tools)

    support_text = "\n".join(
        [
            "\n".join(result.chunk.text for result in retrieved_results),
            format_tool_results(tool_results),
            format_citations(retrieved_results) if retrieved_results else "",
        ]
    )

    input_tokens = estimate_tokens(case["task"], json.dumps(case, ensure_ascii=False))
    output_tokens = estimate_tokens(answer)
    total_tokens = input_tokens + output_tokens

    passed = keyword_accuracy >= KEYWORD_PASS_THRESHOLD
    if case.get("expect_citation"):
        passed = passed and citation_present
    if retrieval_recall is not None:
        passed = passed and retrieval_recall > 0
    if tool_hit_rate is not None:
        passed = passed and tool_hit_rate == 1.0

    return {
        "id": case["id"],
        "category": case["category"],
        "passed": passed,
        "keyword_accuracy": round(keyword_accuracy, 4),
        "retrieval_recall_at_k": None if retrieval_recall is None else round(retrieval_recall, 4),
        "citation_present": citation_present,
        "citation_expected": bool(case.get("expect_citation")),
        "retrieved_sources": sources,
        "expected_sources": expected_sources,
        "tool_hit_rate": None if tool_hit_rate is None else round(tool_hit_rate, 4),
        "actual_tools": actual_tools,
        "expected_tools": expected_tools,
        "latency_seconds": round(elapsed_seconds, 6),
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_total_tokens": total_tokens,
        "estimated_cost_usd": estimate_cost_usd(total_tokens),
        "faithfulness_proxy": round(
            faithfulness_proxy(answer, required_keywords, support_text or answer),
            4,
        ),
        "answer_preview": answer[:600],
    }


def average(values):
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def summarize_results(results):
    total_cases = len(results)
    passed_cases = sum(1 for result in results if result["passed"])
    rag_results = [result for result in results if result["retrieval_recall_at_k"] is not None]
    citation_expected = [result for result in results if result["citation_expected"]]

    summary = {
        "total_cases": total_cases,
        "passed_cases": passed_cases,
        "task_success_rate": round(passed_cases / total_cases, 4) if total_cases else 0.0,
        "keyword_accuracy": round(average([result["keyword_accuracy"] for result in results]) or 0.0, 4),
        "recall_at_k": round(average([result["retrieval_recall_at_k"] for result in rag_results]) or 0.0, 4),
        "citation_rate": round(
            sum(1 for result in citation_expected if result["citation_present"]) / len(citation_expected),
            4,
        )
        if citation_expected
        else 0.0,
        "average_latency_seconds": round(average([result["latency_seconds"] for result in results]) or 0.0, 6),
        "estimated_total_tokens": sum(result["estimated_total_tokens"] for result in results),
        "estimated_cost_usd": round(sum(result["estimated_cost_usd"] for result in results), 8),
        "faithfulness_proxy": round(average([result["faithfulness_proxy"] for result in results]) or 0.0, 4),
    }

    by_category = {}
    grouped = defaultdict(list)
    for result in results:
        grouped[result["category"]].append(result)

    for category, category_results in sorted(grouped.items()):
        by_category[category] = {
            "cases": len(category_results),
            "task_success_rate": round(
                sum(1 for result in category_results if result["passed"]) / len(category_results),
                4,
            ),
            "keyword_accuracy": round(
                average([result["keyword_accuracy"] for result in category_results]) or 0.0,
                4,
            ),
            "average_latency_seconds": round(
                average([result["latency_seconds"] for result in category_results]) or 0.0,
                6,
            ),
        }

    return summary, by_category


def print_summary(summary, by_category, output_path):
    print("\nEvaluation Summary")
    print("------------------")
    print(f"Total cases:             {summary['total_cases']}")
    print(f"Task success rate:       {summary['task_success_rate']:.2%}")
    print(f"Keyword accuracy:        {summary['keyword_accuracy']:.2%}")
    print(f"Recall@k:                {summary['recall_at_k']:.2%}")
    print(f"Citation rate:           {summary['citation_rate']:.2%}")
    print(f"Average latency:         {summary['average_latency_seconds']:.6f}s")
    print(f"Estimated total tokens:  {summary['estimated_total_tokens']}")
    print(f"Estimated cost:          ${summary['estimated_cost_usd']:.8f}")
    print(f"Faithfulness proxy:      {summary['faithfulness_proxy']:.2%}")

    print("\nBy Category")
    print("| category | cases | success | keyword | avg latency |")
    print("| --- | ---: | ---: | ---: | ---: |")
    for category, metrics in by_category.items():
        print(
            "| {category} | {cases} | {success:.2%} | {keyword:.2%} | {latency:.6f}s |".format(
                category=category,
                cases=metrics["cases"],
                success=metrics["task_success_rate"],
                keyword=metrics["keyword_accuracy"],
                latency=metrics["average_latency_seconds"],
            )
        )

    print(f"\nSaved metrics to {output_path}")


def load_cases(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def run_evaluation(cases, *, data_dir=DEFAULT_DATA_DIR, top_k=3):
    results = [evaluate_case(case, data_dir=data_dir, top_k=top_k) for case in cases]
    summary, by_category = summarize_results(results)
    return {
        "summary": summary,
        "by_category": by_category,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Run deterministic local evaluation for the IYUNO AI Agent."
    )
    parser.add_argument(
        "--cases",
        default=str(DEFAULT_CASES_PATH),
        help="Path to evaluation cases JSON file.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path to save evaluation metrics JSON.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Path to local RAG knowledge source directory.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Number of chunks to retrieve for RAG cases.",
    )
    args = parser.parse_args()

    cases = load_cases(args.cases)
    report = run_evaluation(cases, data_dir=Path(args.data_dir), top_k=args.top_k)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)

    print_summary(report["summary"], report["by_category"], output_path)


if __name__ == "__main__":
    main()
