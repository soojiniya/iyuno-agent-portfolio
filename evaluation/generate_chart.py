import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT_DIR = Path(__file__).resolve().parents[1]
METRICS_PATH = ROOT_DIR / "evaluation" / "metrics.json"
OUTPUT_PATH = ROOT_DIR / "evaluation" / "evaluation_results.png"


def load_metrics(path=METRICS_PATH):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def load_font(size, bold=False):
    candidates = [
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]

    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue

    return ImageFont.load_default()


def draw_rounded_bar(draw, x, y, width, height, fill, radius=8):
    draw.rounded_rectangle((x, y, x + width, y + height), radius=radius, fill=fill)


def generate_chart(metrics, output_path=OUTPUT_PATH):
    summary = metrics["summary"]
    values = [
        ("Task Success", summary["task_success_rate"] * 100),
        ("Keyword Accuracy", summary["keyword_accuracy"] * 100),
        ("Recall@k", summary["recall_at_k"] * 100),
        ("Citation Rate", summary["citation_rate"] * 100),
        ("Faithfulness Proxy", summary["faithfulness_proxy"] * 100),
    ]

    width, height = 1200, 720
    image = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)

    title_font = load_font(42, bold=True)
    subtitle_font = load_font(21)
    label_font = load_font(22, bold=True)
    value_font = load_font(22, bold=True)
    note_font = load_font(17)

    text_color = "#111827"
    muted_color = "#6b7280"
    axis_color = "#d1d5db"
    bar_color = "#4b5563"
    highlight_color = "#111827"

    draw.text((64, 44), "IYUNO AI Agent Evaluation Results", fill=text_color, font=title_font)
    draw.text(
        (64, 98),
        "Deterministic local evaluation based on evaluation/metrics.json",
        fill=muted_color,
        font=subtitle_font,
    )

    chart_x = 310
    chart_y = 170
    chart_width = 760
    row_gap = 78
    bar_height = 34

    for tick in range(0, 101, 25):
        x = chart_x + int(chart_width * tick / 100)
        draw.line((x, chart_y - 24, x, chart_y + row_gap * len(values) - 22), fill=axis_color, width=1)
        tick_label = f"{tick}%"
        bbox = draw.textbbox((0, 0), tick_label, font=note_font)
        draw.text((x - (bbox[2] - bbox[0]) / 2, chart_y + row_gap * len(values) - 8), tick_label, fill=muted_color, font=note_font)

    for index, (label, value) in enumerate(values):
        y = chart_y + index * row_gap
        draw.text((64, y), label, fill=text_color, font=label_font)

        draw_rounded_bar(draw, chart_x, y + 2, chart_width, bar_height, "#f3f4f6")
        fill_width = int(chart_width * value / 100)
        color = highlight_color if label == "Faithfulness Proxy" else bar_color
        draw_rounded_bar(draw, chart_x, y + 2, fill_width, bar_height, color)

        value_label = f"{value:.2f}%"
        bbox = draw.textbbox((0, 0), value_label, font=value_font)
        draw.text((chart_x + chart_width + 22, y + 4), value_label, fill=text_color, font=value_font)

    summary_line_one = (
        f"Total cases: {summary['total_cases']}  |  "
        f"Passed cases: {summary['passed_cases']}  |  "
        f"Avg latency: {summary['average_latency_seconds']:.6f}s"
    )
    summary_line_two = (
        f"Estimated tokens: {summary['estimated_total_tokens']:,}  |  "
        f"Estimated cost: ${summary['estimated_cost_usd']:.8f}"
    )
    info_x, info_y = 64, 590
    draw.rounded_rectangle((info_x, info_y, 1136, 664), radius=14, fill="#f9fafb", outline="#e5e7eb")
    draw.text((info_x + 22, info_y + 18), "Summary", fill=text_color, font=label_font)
    draw.text((info_x + 150, info_y + 21), summary_line_one, fill=muted_color, font=note_font)
    draw.text((info_x + 22, info_y + 48), summary_line_two, fill=muted_color, font=note_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    return output_path


def main():
    metrics = load_metrics()
    output_path = generate_chart(metrics)
    print(f"Saved chart to {output_path}")


if __name__ == "__main__":
    main()
