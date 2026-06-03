"""
==============================================================================
 AI DIVIDEND FUND  —  ENDOWMENT MONTE CARLO  (allocation sweep)
==============================================================================

WHAT THIS DOES
--------------
Simulates a $5B endowment invested across three "buckets":

    1. AI            (high growth, high volatility)
    2. Real Economy  (moderate growth, moderate volatility)
    3. Reserve       (low growth, very low volatility — the spending cushion)

It runs 10,000 random 25-year futures for EACH candidate target allocation,
then compares allocations on the things an endowment actually cares about:

    * How big is the corpus likely to be in 25 years?
    * What's the chance it preserves its real (inflation-adjusted) value?
    * How much does it pay out over its life, and how stable are the payouts?
    * What's the worst-case (downside) outcome?

Spending each year follows a smoothing rule (Yale-style):

    distribution_t = smoothing * distribution_{t-1}
                   + (1 - smoothing) * base_rate * market_value_t

Smoothing keeps payouts steady even when markets swing.

HOW TO RUN
----------
    cd ~/ai-dividend-fund
    python3 montecarlo.py

Outputs (written to this folder):
    results_allocations.csv      full table, one row per allocation tested
    chart_terminal_corpus.png    heatmap: median ending corpus by allocation
    chart_preservation.png       heatmap: chance of preserving real value
    chart_frontier.png           tradeoff: lifetime payout vs. sustainability

EDIT ASSUMPTIONS
----------------
Everything you can change lives in the CONFIG block directly below.
==============================================================================
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# =============================================================================
# CONFIG  — edit these freely
# =============================================================================

# --- Buckets: order is [AI, Real Economy, Reserve] everywhere below ----------
BUCKET_NAMES = ["AI", "Real", "Reserve"]
MEAN_RETURN  = np.array([0.13, 0.07, 0.02])   # expected arithmetic annual return
VOLATILITY   = np.array([0.30, 0.13, 0.02])   # annual standard deviation

# Correlation matrix (symmetric). Rows/cols = [AI, Real, Reserve]
#   AI-Real = 0.45 ,  AI-Reserve = 0.00 ,  Real-Reserve = 0.10
CORRELATION = np.array([
    [1.00, 0.45, 0.00],
    [0.45, 1.00, 0.10],
    [0.00, 0.10, 1.00],
])

# --- Endowment terms ---------------------------------------------------------
STARTING_CORPUS = 5_000_000_000.0   # $5 billion
HORIZON_YEARS   = 25

# --- Spending rule -----------------------------------------------------------
BASE_SPEND_RATE = 0.025   # 2.5% of market value
SMOOTHING       = 0.70    # weight on PRIOR year's distribution (0..1)

# --- Optional knobs (set to 0 to ignore) -------------------------------------
INFLATION   = 0.00   # escalates prior-year spending & deflates terminal corpus
FEE_RATE    = 0.00   # annual management fee as % of assets

# --- Simulation settings -----------------------------------------------------
N_SIMS    = 10_000
GRID_STEP = 0.05     # allocation grid resolution (0.05 = test every 5%)
SEED      = 42       # makes results reproducible; change for a fresh draw

# =============================================================================
# 1.  Build correlated LOGNORMAL annual returns (generated once, reused for
#     every allocation so all allocations face the same set of futures).
# =============================================================================

def build_return_draws():
    """Return array shape (N_SIMS, HORIZON_YEARS, 3) of GROSS returns (1+r).

    Lognormal returns are produced from a correlated multivariate normal in
    log-space, calibrated so each bucket's level returns hit the target mean
    and volatility above. (Correlations are applied to the log-returns, the
    standard simplifying convention.)
    """
    # Convert target (mean, vol) of the LEVEL return into the mu/sigma of the
    # underlying normal of a lognormal distribution.
    sigma2 = np.log(1.0 + (VOLATILITY ** 2) / ((1.0 + MEAN_RETURN) ** 2))
    sigma  = np.sqrt(sigma2)
    mu     = np.log(1.0 + MEAN_RETURN) - 0.5 * sigma2

    # Covariance of the underlying normals = corr_ij * sigma_i * sigma_j
    cov = CORRELATION * np.outer(sigma, sigma)
    chol = np.linalg.cholesky(cov)   # fails loudly if matrix isn't valid (PSD)

    rng = np.random.default_rng(SEED)
    z = rng.standard_normal((N_SIMS, HORIZON_YEARS, 3))
    x = mu + z @ chol.T              # correlated normals in log-space
    gross = np.exp(x)                # 1 + return, always positive
    return gross


# =============================================================================
# 2.  Simulate one allocation across all paths/years (fully vectorized).
# =============================================================================

def simulate_allocation(weights, gross):
    """Run all N_SIMS paths for one target allocation.

    weights : array of 3 target weights summing to 1 (rebalanced to annually)
    gross   : pre-generated gross returns (N_SIMS, HORIZON_YEARS, 3)

    Returns a dict of summary metrics for this allocation.
    """
    w = np.asarray(weights)

    # Start every path at the target allocation.
    V = np.full((N_SIMS, 3), STARTING_CORPUS) * w           # (N_SIMS, 3)

    # Prior-year distribution seed = base rate on the starting corpus.
    dist_prev = np.full(N_SIMS, BASE_SPEND_RATE * STARTING_CORPUS)

    dist_paths   = np.zeros((N_SIMS, HORIZON_YEARS))        # payout each year
    ever_depleted = np.zeros(N_SIMS, dtype=bool)

    for t in range(HORIZON_YEARS):
        # (a) Markets move.
        V = V * gross[:, t, :]

        # (b) Annual fee (if any), taken proportionally across buckets.
        if FEE_RATE > 0:
            V = V * (1.0 - FEE_RATE)

        total = V.sum(axis=1)

        # (c) Smoothed spending target. Prior distribution may be inflated.
        target = (SMOOTHING * dist_prev * (1.0 + INFLATION)
                  + (1.0 - SMOOTHING) * BASE_SPEND_RATE * total)

        # Can't spend more than exists.
        spend = np.minimum(target, total)
        spend = np.maximum(spend, 0.0)

        remaining = total - spend
        ever_depleted |= (remaining <= 0.0)

        # (d) Rebalance whatever's left back to the target weights.
        V = remaining[:, None] * w[None, :]

        dist_paths[:, t] = spend
        dist_prev = spend

    ending_nominal = V.sum(axis=1)
    deflator = (1.0 + INFLATION) ** HORIZON_YEARS
    ending_real = ending_nominal / deflator

    total_payout = dist_paths.sum(axis=1)
    # Per-path stability of payouts: coefficient of variation (lower = smoother)
    with np.errstate(divide="ignore", invalid="ignore"):
        cov_path = np.where(dist_paths.mean(axis=1) > 0,
                            dist_paths.std(axis=1) / dist_paths.mean(axis=1),
                            np.nan)

    return {
        "w_AI": w[0], "w_Real": w[1], "w_Reserve": w[2],
        # Terminal corpus, real terms ($B)
        "end_p5":   np.percentile(ending_real, 5)  / 1e9,
        "end_p25":  np.percentile(ending_real, 25) / 1e9,
        "end_med":  np.percentile(ending_real, 50) / 1e9,
        "end_p75":  np.percentile(ending_real, 75) / 1e9,
        "end_p95":  np.percentile(ending_real, 95) / 1e9,
        # Sustainability
        "p_preserve":  np.mean(ending_real >= STARTING_CORPUS),   # keeps real value
        "p_depleted":  np.mean(ever_depleted),                    # ever ran dry
        # Distributions over the fund's life ($B)
        "payout_med":  np.percentile(total_payout, 50) / 1e9,     # median lifetime
        "payout_p5":   np.percentile(total_payout, 5)  / 1e9,     # downside lifetime
        "annual_med":  np.percentile(total_payout, 50) / HORIZON_YEARS / 1e9,
        "payout_cv":   np.nanmedian(cov_path),                    # payout smoothness
    }


# =============================================================================
# 3.  Sweep every allocation on the grid.
# =============================================================================

def allocation_grid(step):
    """All (AI, Real, Reserve) weight combos on `step` grid summing to 1."""
    ticks = np.round(np.arange(0.0, 1.0 + 1e-9, step), 10)
    combos = []
    for a in ticks:
        for b in ticks:
            c = round(1.0 - a - b, 10)
            if c >= -1e-9 and c <= 1.0 + 1e-9:
                combos.append((a, b, max(c, 0.0)))
    # de-dup floating point near-equals
    return sorted(set((round(a, 4), round(b, 4), round(c, 4)) for a, b, c in combos))


def main():
    print(f"Generating {N_SIMS:,} x {HORIZON_YEARS}-year return paths ...")
    gross = build_return_draws()

    grid = allocation_grid(GRID_STEP)
    print(f"Sweeping {len(grid)} allocations "
          f"({N_SIMS:,} sims each = {len(grid) * N_SIMS:,} total paths) ...")

    rows = [simulate_allocation(w, gross) for w in grid]
    df = pd.DataFrame(rows)

    df.to_csv("results_allocations.csv", index=False)
    print("\nSaved full table -> results_allocations.csv")

    # ---- Headline findings --------------------------------------------------
    def show(title, sub):
        print(f"\n{title}")
        cols = ["w_AI", "w_Real", "w_Reserve", "end_med", "end_p5",
                "p_preserve", "p_depleted", "payout_med", "payout_cv"]
        with pd.option_context("display.float_format", lambda v: f"{v:,.3f}"):
            print(sub[cols].to_string(index=False))

    print("\n" + "=" * 78)
    print("RESULTS  (terminal corpus & payouts in $ billions, real terms)")
    print("=" * 78)
    show("Highest MEDIAN terminal corpus:",
         df.nlargest(5, "end_med"))
    show("Best DOWNSIDE protection (highest 5th-percentile terminal corpus):",
         df.nlargest(5, "end_p5"))
    show("Highest chance of PRESERVING real value:",
         df.nlargest(5, "p_preserve"))
    show("Highest MEDIAN lifetime distributions:",
         df.nlargest(5, "payout_med"))

    make_charts(df)
    print("\nCharts saved: chart_terminal_corpus.png, "
          "chart_preservation.png, chart_frontier.png")
    print("Done.")


# =============================================================================
# 4.  Charts.
# =============================================================================

def _heatmap(df, value_col, title, fname, fmt="{:.1f}", cmap="viridis"):
    """Heatmap over (AI weight x Reserve weight); Real = 1 - AI - Reserve."""
    ai = np.sort(df["w_AI"].unique())
    rs = np.sort(df["w_Reserve"].unique())
    grid = np.full((len(rs), len(ai)), np.nan)
    lookup = {(round(r.w_AI, 4), round(r.w_Reserve, 4)): getattr(r, value_col)
              for r in df.itertuples()}
    for i, rsv in enumerate(rs):
        for j, a in enumerate(ai):
            grid[i, j] = lookup.get((round(a, 4), round(rsv, 4)), np.nan)

    fig, ax = plt.subplots(figsize=(9, 7))
    im = ax.imshow(grid, origin="lower", aspect="auto", cmap=cmap,
                   extent=[ai.min() - GRID_STEP / 2, ai.max() + GRID_STEP / 2,
                           rs.min() - GRID_STEP / 2, rs.max() + GRID_STEP / 2])
    ax.set_xlabel("AI bucket weight")
    ax.set_ylabel("Reserve bucket weight")
    ax.set_title(title + "\n(Real Economy weight = 1 - AI - Reserve)")
    fig.colorbar(im, ax=ax, label=value_col)

    # mark the best cell
    best = df.loc[df[value_col].idxmax()]
    ax.scatter([best.w_AI], [best.w_Reserve], marker="*", s=300,
               edgecolor="white", color="red", zorder=5,
               label=f"best: AI {best.w_AI:.0%} / Real {best.w_Real:.0%} / "
                     f"Res {best.w_Reserve:.0%}")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(fname, dpi=130)
    plt.close(fig)


def make_charts(df):
    _heatmap(df, "end_med",
             "Median terminal corpus, $B (real)",
             "chart_terminal_corpus.png", cmap="viridis")
    _heatmap(df, "p_preserve",
             "Probability of preserving real value (25 yrs)",
             "chart_preservation.png", cmap="RdYlGn")

    # Frontier: lifetime payout vs. sustainability, colored by AI weight.
    fig, ax = plt.subplots(figsize=(9, 7))
    sc = ax.scatter(df["payout_med"], df["p_preserve"],
                    c=df["w_AI"], cmap="plasma", s=40, edgecolor="k", lw=0.3)
    ax.set_xlabel("Median lifetime distributions, $B (real)")
    ax.set_ylabel("Probability of preserving real value")
    ax.set_title("The endowment tradeoff: spend more now vs. last forever\n"
                 "(each dot = one allocation; color = AI weight)")
    fig.colorbar(sc, ax=ax, label="AI bucket weight")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig("chart_frontier.png", dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    main()
