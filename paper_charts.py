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

import numpy as np
import matplotlib
matplotlib.use("Agg")                     # no display needed
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

import montecarlo as mc

AI_LEVELS = [0, 30, 50, 100]              # AI allocation points to plot (percent)


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

    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.size": 12,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })
    fig, ax = plt.subplots(figsize=(8, 6), dpi=200)

    # connecting path (shows the tradeoff as AI rises)
    ax.plot(x, y, "-", color="#9fb0c0", lw=1.5, zorder=1)

    # colored points (purple -> yellow with AI, matching the tool's palette)
    colors = plt.cm.viridis(ai / 100.0)
    ax.scatter(x, y, s=170, c=colors, edgecolors="white", linewidths=1.5, zorder=3)

    # label each point with its AI allocation (* marks the all-AI exception)
    for d, xi, yi, a in zip(rows, x, y, ai):
        star = "*" if abs(d["res"] - RESERVE) > 1e-9 else ""
        ax.annotate(f"{a}% AI{star}", (xi, yi),
                    textcoords="offset points", xytext=(10, 10),
                    fontsize=11, fontweight="bold", color="#2c3a49")

    ax.set_xlabel("Probability of cutting distributions\n(payout >25% below a prior peak)")
    ax.set_ylabel("Median ending corpus  (real $B)")
    ax.set_title("Distribution stability vs. growth, by AI allocation",
                 fontsize=15, fontweight="bold", pad=12)

    ax.xaxis.set_major_formatter(PercentFormatter(xmax=1.0, decimals=0))
    ax.yaxis.set_major_formatter(lambda v, _: f"${v:.0f}B")
    ax.grid(True, color="#e6e9ee", lw=0.8)
    ax.set_axisbelow(True)

    # a little breathing room around the points
    ax.margins(x=0.18, y=0.18)

    reserve_note = ("Reserve held at 25%; Real economy takes the rest"
                    + (" (*100% AI is all-AI: Reserve 0%)." if has_exception else "."))
    note = (f"$5B corpus · 25-yr horizon · 2.5% spend, 0.70 smoothing · "
            f"{mc.N_SIMS:,} sims · {reserve_note}\n"
            "Up-and-right = more growth but less stable payouts.")
    fig.text(0.5, -0.02, note, ha="center", va="top",
             fontsize=9, color="#6b7785")

    fig.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(f"fig1_stability_vs_growth.{ext}", bbox_inches="tight")
    plt.close(fig)
    print("  saved fig1_stability_vs_growth.pdf / .png")


def main():
    print("Building shared return draws (one set of futures for every allocation)...")
    gross = mc.build_return_draws()
    print("\nFigure 1 — Distribution stability vs. growth, by AI allocation:")
    fig1_stability_vs_growth(gross)


if __name__ == "__main__":
    main()
