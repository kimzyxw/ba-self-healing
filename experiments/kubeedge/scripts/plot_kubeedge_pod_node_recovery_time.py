from pathlib import Path
import csv
import statistics
import matplotlib.pyplot as plt

BASE = Path("experiments/kubeedge")

POD_CSV = BASE / "pod-failure" / "analysis" / "kubeedge_pod_failure_per_run_final.csv"
NODE_CSV = BASE / "node-failure" / "analysis" / "kubeedge_node_failure_per_run_final.csv"

OUT_DIR = BASE / "analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_PDF = OUT_DIR / "kubeedge_pod_node_recovery_time.pdf"
OUT_PNG = OUT_DIR / "kubeedge_pod_node_recovery_time.png"


def read_pod_recovery_seconds(path):
    values = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            values.append(float(row["recovery_seconds"]))
    return values


def read_node_recovery_seconds(path, role):
    values = []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["role"] == role:
                values.append(float(row["node_recovery_seconds"]))
    return values


def seconds_to_minutes(values):
    return [v / 60.0 for v in values]


def fmt_de(value, digits=2):
    return f"{value:.{digits}f}".replace(".", ",")


groups = [
    ("Pod-Ausfall", seconds_to_minutes(read_pod_recovery_seconds(POD_CSV))),
    ("Edge-Node-Ausfall", seconds_to_minutes(read_node_recovery_seconds(NODE_CSV, "edge"))),
    ("Cloud-Node-Ausfall", seconds_to_minutes(read_node_recovery_seconds(NODE_CSV, "cloud"))),
]

labels = [g[0] for g in groups]
means = [statistics.mean(g[1]) for g in groups]
stds = [statistics.stdev(g[1]) if len(g[1]) > 1 else 0.0 for g in groups]

fig, ax = plt.subplots(figsize=(8.2, 4.8))

x = list(range(len(labels)))
bars = ax.bar(x, means, yerr=stds, capsize=6)

# Einzelwerte als Punkte anzeigen, damit sichtbar bleibt, dass je Szenario 10 Läufe vorliegen.
for i, (_, values) in enumerate(groups):
    offsets = [-0.16, -0.12, -0.08, -0.04, 0.0, 0.04, 0.08, 0.12, 0.16, 0.20]
    for j, value in enumerate(values):
        ax.scatter(i + offsets[j % len(offsets)], value, s=22, zorder=3)

# Mittelwerte über den Balken beschriften.
for i, value in enumerate(means):
    ax.text(
        i,
        value + max(means) * 0.035,
        f"{fmt_de(value, 2)} min",
        ha="center",
        va="bottom",
        fontsize=10,
    )

ax.set_ylabel("Recovery Time [min]")
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_title("KubeEdge: Recovery Time bei Pod- und Node-Ausfällen")
ax.grid(axis="y", linestyle=":", linewidth=0.8)
ax.set_axisbelow(True)

# Etwas Platz für die Beschriftungen über den Balken.
ax.set_ylim(0, max(m + s for m, s in zip(means, stds)) * 1.18)

fig.tight_layout()
fig.savefig(OUT_PDF, bbox_inches="tight")
fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")

print(f"Wrote: {OUT_PDF}")
print(f"Wrote: {OUT_PNG}")

print()
print("Summary:")
for label, values in groups:
    print(
        f"{label}: mean={fmt_de(statistics.mean(values), 2)} min, "
        f"median={fmt_de(statistics.median(values), 2)} min, "
        f"std={fmt_de(statistics.stdev(values) if len(values) > 1 else 0.0, 2)} min"
    )
