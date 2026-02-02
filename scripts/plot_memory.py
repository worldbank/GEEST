# -*- coding: utf-8 -*-

"""Plot QGIS memory usage from the monitor log."""

import sys
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402


def main():
    """Generate a memory usage chart from the monitor log."""
    log_path = sys.argv[1] if len(sys.argv) > 1 else "qgis_memory.log"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "qgis_memory_chart.png"

    times, mem = [], []
    with open(log_path) as f:
        next(f)  # skip header
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) == 2:
                times.append(datetime.strptime(parts[0], "%Y-%m-%dT%H:%M:%SZ"))
                mem.append(float(parts[1]))

    if not times:
        print("No data points found.")
        sys.exit(1)

    fig, ax = plt.subplots(figsize=(14, 5))

    # Gradient fill under the line
    ax.fill_between(times, mem, alpha=0.25, color="#2196F3")
    ax.plot(times, mem, color="#1565C0", linewidth=1.8, label="QGIS RSS")

    # 4 GB limit line
    ax.axhline(y=4096, color="#E53935", linestyle="--", linewidth=1.2, label="4 GB limit")

    # Peak annotation
    peak_mb = max(mem)
    peak_time = times[mem.index(peak_mb)]
    ax.annotate(
        f"Peak: {peak_mb:.0f} MB",
        xy=(peak_time, peak_mb),
        xytext=(0, 14),
        textcoords="offset points",
        ha="center",
        fontsize=9,
        fontweight="bold",
        color="#1565C0",
        arrowprops=dict(arrowstyle="->", color="#1565C0", lw=1.2),
    )

    ax.set_xlabel("Time (UTC)", fontsize=11)
    ax.set_ylabel("Resident Memory (MB)", fontsize=11)
    ax.set_title("QGIS Memory Usage Over Time", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)

    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    fig.autofmt_xdate()

    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_ylim(bottom=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Chart saved to {out_path}")


if __name__ == "__main__":
    main()
