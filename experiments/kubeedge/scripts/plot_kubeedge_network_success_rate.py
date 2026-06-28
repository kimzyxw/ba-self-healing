#!/usr/bin/env python3
from pathlib import Path
import argparse
import csv
import re

import numpy as np
import matplotlib.pyplot as plt


COLUMNS = [
    "Run",
    "Störung",
    "Ziel",
    "Req.",
    "OK",
    "Fail",
    "Succ. [%]",
    "Err. [%]",
    "Rec. [s]",
    "Stab. [s]",
    "Pod-Rest.",
    "NodeNotReady",
    "NotReady [s]",
    "Final Ready",
    "gültig",
]


def clean_tex(value: str) -> str:
    """Remove small LaTeX artifacts from table cells."""
    value = value.strip()
    value = value.replace(r"\%", "%")
    value = value.replace(r"{,}", ".")
    value = value.replace(r"\,", " ")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_float(value: str):
    value = clean_tex(value)
    if value in {"", "--", "-", "NA"}:
        return None
    value = value.replace(",", ".")
    return float(value)


def parse_latex_table(path: Path):
    """Parse appendix table rows from a LaTeX tabular file."""
    rows = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line.startswith("run-"):
            continue

        if "&" not in line:
            continue

        line = re.sub(r"\\\\\s*$", "", line)
        parts = [clean_tex(part) for part in line.split("&")]

        if len(parts) != len(COLUMNS):
            raise ValueError(
                f"Unexpected number of columns in {path}:\n"
                f"Expected {len(COLUMNS)}, got {len(parts)}\n"
                f"Line: {raw_line}"
            )

        row = dict(zip(COLUMNS, parts))
        row["Succ. [%]"] = parse_float(row["Succ. [%]"])
        row["gültig"] = row["gültig"].lower() == "ja"
        rows.append(row)

    return rows


def collect_success_rates(path: Path, order: list[str]):
    rows = parse_latex_table(path)

    values_by_disturbance = {name: [] for name in order}

    for row in rows:
        disturbance = row["Störung"]
        success_rate = row["Succ. [%]"]

        if disturbance not in values_by_disturbance:
            continue

        if not row["gültig"]:
            continue

        if success_rate is None:
            continue

        values_by_disturbance[disturbance].append(success_rate)

    stats = []

    for disturbance in order:
        values = values_by_disturbance[disturbance]

        if not values:
            raise ValueError(f"No valid values found for: {disturbance}")

        mean = float(np.mean(values))
        std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0

        stats.append(
            {
                "disturbance": disturbance,
                "mean": mean,
                "std": std,
                "n": len(values),
            }
        )

    return stats


def short_label(disturbance: str) -> str:
    label = disturbance
    label = label.replace("Latenz ", "")
    label = label.replace("Paketverlust ", "")
    label = label.replace("Link-Cut ", "")

    label = label.replace("1s", "1 s")
    label = label.replace("1min", "1 min")
    label = label.replace("10min", "10 min")
    label = label.replace("30min", "30 min")

    return label


def plot_chart(latency_stats, packet_loss_stats, link_cut_stats, output_base: Path):
    groups = [
        ("Erhöhte Latenz", latency_stats),
        ("Paketverlust", packet_loss_stats),
        ("Verbindungsabbruch", link_cut_stats),
    ]

    x_positions = []
    x_labels = []
    group_centers = []

    current_x = 0
    gap = 1.5

    fig, ax = plt.subplots(figsize=(14, 6))

    all_rows_for_csv = []

    for group_name, stats in groups:
        group_x = list(np.arange(current_x, current_x + len(stats), 1.0))
        group_centers.append((np.mean(group_x), group_name))

        means = [row["mean"] for row in stats]
        stds = [row["std"] for row in stats]

        ax.bar(
            group_x,
            means,
            yerr=stds,
            capsize=4,
            label=group_name,
        )

        for x, row in zip(group_x, stats):
            x_positions.append(x)
            x_labels.append(short_label(row["disturbance"]))

            label_y = min(row["mean"] + row["std"] + 2, 106)
            ax.text(
                x,
                label_y,
                f"{row['mean']:.1f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

            all_rows_for_csv.append(
                {
                    "Gruppe": group_name,
                    "Störung": row["disturbance"],
                    "gültige Runs": row["n"],
                    "Mittelwert Succ. [%]": f"{row['mean']:.4f}",
                    "Std Succ. [pp]": f"{row['std']:.4f}",
                }
            )

        current_x += len(stats) + gap

    ax.set_title("KubeEdge-Netzwerktests: Anwendungserreichbarkeit während der Störung")
    ax.set_ylabel("Mittlere Request Success Rate während der Fault-Phase [%]")
    ax.set_xlabel("Störungsstufe")

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels)

    ax.set_ylim(0, 110)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(title="Netzwerkstörung")

    for center, group_name in group_centers:
        ax.text(
            center,
            -0.16,
            group_name,
            ha="center",
            va="top",
            transform=ax.get_xaxis_transform(),
            fontsize=10,
        )

    fig.subplots_adjust(bottom=0.24, left=0.08, right=0.98, top=0.90)

    output_base.parent.mkdir(parents=True, exist_ok=True)

    png_path = output_base.with_suffix(".png")
    pdf_path = output_base.with_suffix(".pdf")
    csv_path = output_base.with_suffix(".csv")

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_rows_for_csv[0].keys())
        writer.writeheader()
        writer.writerows(all_rows_for_csv)

    print(f"Gespeichert:")
    print(f"  {png_path}")
    print(f"  {pdf_path}")
    print(f"  {csv_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create KubeEdge network success-rate chart from appendix LaTeX tables."
    )

    parser.add_argument(
        "--latency",
        type=Path,
        default=Path("appendix-tables/kubeedge_latency_appendix_runs.tex"),
        help="Path to KubeEdge latency appendix table.",
    )
    parser.add_argument(
        "--packet-loss",
        type=Path,
        default=Path("appendix-tables/kubeedge_packet_loss_appendix_runs.tex"),
        help="Path to KubeEdge packet-loss appendix table.",
    )
    parser.add_argument(
        "--link-cut",
        type=Path,
        default=Path("appendix-tables/kubeedge_link_cut_appendix_runs.tex"),
        help="Path to KubeEdge link-cut appendix table.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("figures/kubeedge_network_success_rate"),
        help="Output path without file ending.",
    )

    args = parser.parse_args()

    latency_order = [
        "Latenz 1s",
        "Latenz 1min",
        "Latenz 10min",
        "Latenz 30min",
    ]

    packet_loss_order = [
        "Paketverlust 1%",
        "Paketverlust 10%",
        "Paketverlust 50%",
        "Paketverlust 70%",
        "Paketverlust 100%",
    ]

    link_cut_order = [
        "Link-Cut 1s",
        "Link-Cut 1min",
        "Link-Cut 10min",
        "Link-Cut 30min",
    ]

    latency_stats = collect_success_rates(args.latency, latency_order)
    packet_loss_stats = collect_success_rates(args.packet_loss, packet_loss_order)
    link_cut_stats = collect_success_rates(args.link_cut, link_cut_order)

    plot_chart(
        latency_stats=latency_stats,
        packet_loss_stats=packet_loss_stats,
        link_cut_stats=link_cut_stats,
        output_base=args.out,
    )


if __name__ == "__main__":
    main()
