from pathlib import Path
import csv
import matplotlib.pyplot as plt

BASE = Path("experiments/kubeedge/latency-tests")
IN_CSV = BASE / "kubeedge-latency-comparison-summary.csv"
OUT_DIR = BASE / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_PDF = OUT_DIR / "kubeedge_latency_fault_success_rate.pdf"
OUT_PNG = OUT_DIR / "kubeedge_latency_fault_success_rate.png"

labels = []
fault_success = []
after_success = []
stable_after = []

with IN_CSV.open(encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        labels.append(row["label"])
        fault_success.append(float(row["fault_success_rate_median"]))
        after_success.append(float(row["after_success_rate_median"]))
        stable_after.append(int(row["runs_with_stable_after_snapshot"]))

x = list(range(len(labels)))
width = 0.36

fig, ax = plt.subplots(figsize=(8.4, 4.8))

bars_fault = ax.bar([i - width / 2 for i in x], fault_success, width, label="Fault-Phase")
bars_after = ax.bar([i + width / 2 for i in x], after_success, width, label="After-Phase")

for bars in [bars_fault, bars_after]:
    for bar in bars:
        value = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.5,
            f"{value:.1f} %",
            ha="center",
            va="bottom",
            fontsize=9,
        )

ax.set_ylabel("Request Success Rate [%]")
ax.set_xlabel("Latenzszenario")
ax.set_title("KubeEdge: Request Success Rate während und nach Latenzinjektion")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylim(0, 110)
ax.grid(axis="y", linestyle=":", linewidth=0.8)
ax.set_axisbelow(True)
ax.legend()

fig.tight_layout()
fig.savefig(OUT_PDF, bbox_inches="tight")
fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")

print(f"Wrote: {OUT_PDF}")
print(f"Wrote: {OUT_PNG}")

print()
print("Summary:")
for label, fault, after, stable in zip(labels, fault_success, after_success, stable_after):
    print(f"{label}: fault={fault:.2f} %, after={after:.2f} %, stable_after={stable}/10")
