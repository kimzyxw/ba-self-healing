from pathlib import Path
import csv
import matplotlib.pyplot as plt

OUT_DIR = Path("experiments/k3s/network-tests/analysis")
OUT_DIR.mkdir(parents=True, exist_ok=True)

INPUTS = [
    (
        "Latenz",
        Path("experiments/k3s/latency-tests/analysis/k3s_latency_summary.csv"),
        {
            "latency-1s-short": "1s",
            "latency-1min-short": "1min",
            "latency-10min-async-limited": "10min",
            "latency-30min-async-limited": "30min",
        },
    ),
    (
        "Paketverlust",
        Path("experiments/k3s/packet-loss-tests/analysis/k3s_packet_loss_summary_final.csv"),
        {
            "packet-loss-1pct-async-limited": "1%",
            "packet-loss-10pct-async-limited": "10%",
            "packet-loss-50pct-async-limited": "50%",
            "packet-loss-70pct-router-cleanup": "70%",
            "packet-loss-100pct-safety-cleanup": "100%",
        },
    ),
    (
        "Verbindungsabbruch",
        Path("experiments/k3s/link-cut-tests/analysis/k3s_link_cut_summary_final.csv"),
        {
            "link-cut-1s": "1s",
            "link-cut-1min": "1min",
            "link-cut-10min": "10min",
            "link-cut-30min": "30min",
        },
    ),
]

rows = []

for test_type, path, scenario_labels in INPUTS:
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            scenario = row["scenario"]
            if scenario not in scenario_labels:
                continue

            rows.append({
                "label": f"{test_type}\n{scenario_labels[scenario]}",
                "success": float(row["fault_success_rate_mean_percent"]),
                "std": float(row["fault_success_rate_std_percent"]),
            })

labels = [r["label"] for r in rows]
success = [r["success"] for r in rows]
std = [r["std"] for r in rows]
y_pos = list(range(len(rows)))

fig, ax = plt.subplots(figsize=(9, 6))

ax.barh(y_pos, success, xerr=std, capsize=3)

ax.set_yticks(y_pos)
ax.set_yticklabels(labels)
ax.invert_yaxis()

ax.set_xlabel("Request Success Rate während der Fault-Phase [%]")
ax.set_xlim(0, 105)
ax.set_title("K3s-Netzwerktests: Anwendungserreichbarkeit während der Störung")

ax.grid(axis="x", linestyle=":", linewidth=0.7)

for i, value in enumerate(success):
    ax.text(min(value + 1.5, 101), i, f"{value:.2f}%".replace(".", ","), va="center", fontsize=8)

fig.tight_layout()

pdf_path = OUT_DIR / "k3s_network_success_rate_fault_phase.pdf"
png_path = OUT_DIR / "k3s_network_success_rate_fault_phase.png"

fig.savefig(pdf_path, bbox_inches="tight")
fig.savefig(png_path, dpi=300, bbox_inches="tight")

print(f"Wrote {pdf_path}")
print(f"Wrote {png_path}")