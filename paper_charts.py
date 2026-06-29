"""
Publication figures for the AI Dividend Fund paper.

Reuses the audited Monte Carlo engine in montecarlo.py (same assumptions:
$5B corpus, 25-yr horizon, 2.5% spend rate, 0.70 smoothing on the
beginning-of-year corpus, 10,000 sims, seed 42).

Each figure is saved as a vector PDF (for the paper) and a PNG (for preview).

Figure 1 — Distribution stability vs. growth, by AI allocation
    x: probability of cutting distributions (>25% below a prior peak)
    y: median ending corpus (real $B)
    points: AI allocation = 0%, 30%, 50%, 100%
    Non-AI remainder is held entirely in the Real-Economy bucket (Reserve = 0),
    so AI allocation is the single dimension that varies.
"""

import textwrap

import numpy as np
import matplotlib
matplotlib.use("Agg")                     # no display needed
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

import montecarlo as mc

AI_LEVELS = [0, 30, 50, 100]              # AI allocation points to plot (percent)


def apply_house_style():
    """Consistent, white-paper-grade styling shared by every figure."""
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 12,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#9aa5b1",
        "axes.linewidth": 1.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlecolor": "#1a1a1a",
        "axes.labelcolor": "#333333",
        "xtick.color": "#333333",
        "ytick.color": "#333333",
        "axes.titlepad": 14,
    })


RESERVE = 0.25   # Reserve held constant at 25% where feasible


def alloc_from_ai(ai_pct):
    """AI / Real / Reserve weights. Reserve is held at 25% and Real economy
    absorbs the rest. At very high AI the 25% Reserve cannot be held, so it
    falls to 0 (the all-AI exception at 100%)."""
    ai = ai_pct / 100.0
    res = min(RESERVE, 1.0 - ai)        # 0.25 normally; 0 only when AI > 75%
    real = 1.0 - ai - res
    return np.array([ai, real, res])


def fig1_stability_vs_growth(gross):
    rows = []
    for ai in AI_LEVELS:
        w = alloc_from_ai(ai)
        r = mc.simulate_allocation(w, gross)
        rows.append({"ai": ai, "res": w[2], "p_cut": r["p_cut"], "end_med": r["end_med"]})
        print(f"  AI {ai:3d}%  Real {w[1]*100:3.0f}%  Reserve {w[2]*100:3.0f}%   "
              f"P(cut) = {r['p_cut']*100:5.1f}%   median end = ${r['end_med']:5.1f}B")

    rows.sort(key=lambda d: d["ai"])
    x = np.array([d["p_cut"] for d in rows])
    y = np.array([d["end_med"] for d in rows])
    ai = np.array([d["ai"] for d in rows])
    has_exception = any(abs(d["res"] - RESERVE) > 1e-9 for d in rows)

    apply_house_style()
    fig, ax = plt.subplots(figsize=(8, 5.6), dpi=300)

    # data points only (no connecting line); navy gradient deepens with AI weight
    colors = plt.cm.Blues(0.45 + 0.50 * (ai / 100.0))
    ax.scatter(x, y, s=240, c=colors, edgecolors="white", linewidths=1.8, zorder=3)

    # label each point (* marks the all-AI exception); keep the rightmost label inboard
    xmax_idx = int(np.argmax(x))
    for i, (d, xi, yi, a) in enumerate(zip(rows, x, y, ai)):
        star = "*" if abs(d["res"] - RESERVE) > 1e-9 else ""
        dx, ha = (-14, "right") if i == xmax_idx else (14, "left")
        ax.annotate(f"{a}% AI{star}", (xi, yi),
                    textcoords="offset points", xytext=(dx, 13), ha=ha,
                    fontsize=11.5, fontweight="bold", color="#1a1a1a")

    ax.set_title("Distribution Stability Versus Growth By AI Allocation",
                 fontsize=15.5, fontweight="bold", pad=16)
    ax.set_xlabel("Probability Of Cutting Distributions", fontsize=12.5, labelpad=11)
    ax.set_ylabel("Median Ending Corpus (Real $B)", fontsize=12.5, labelpad=11)

    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}B")
    ax.grid(True, axis="y", color="#e9ecf1", lw=1.0)
    ax.grid(False, axis="x")
    ax.set_axisbelow(True)
    ax.tick_params(length=4, color="#9aa5b1", labelsize=11)
    ax.margins(x=0.22, y=0.24)

    reserve_note = ("Reserve is held at 25%; the Real-Economy bucket absorbs the remainder"
                    + (" (*100% AI is the all-AI case, with 0% Reserve)."
                       if has_exception else "."))
    note = ('Note: A "cut" is an annual distribution more than 25% below its prior peak. '
            f"Assumes a $5B corpus, 25-year horizon, a 2.5% spend rate with 0.70 smoothing, "
            f"and {mc.N_SIMS:,} simulations. " + reserve_note)
    fig.text(0.065, -0.01, "\n".join(textwrap.wrap(note, 96)),
             ha="left", va="top", fontsize=8.5, color="#6b7785")

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"fig1_stability_vs_growth.{ext}",
                    bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print("  saved fig1_stability_vs_growth.pdf / .png")


def main():
    print("Building shared return draws (one set of futures for every allocation)...")
    gross = mc.build_return_draws()
    print("\nFigure 1 — Distribution stability vs. growth, by AI allocation:")
    fig1_stability_vs_growth(gross)


if __name__ == "__main__":
    main()
