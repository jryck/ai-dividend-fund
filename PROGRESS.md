# Project progress & next steps

_Last updated: 2026-06-03_

A working log of the AI Dividend Fund endowment Monte Carlo project, so work can be
picked up later (by me or by Claude in a future session).

## What this project is
An easy-to-use Monte Carlo simulator for a hypothetical $5B "AI Dividend Fund"
endowment — three buckets (AI / Real Economy / Reserve), correlated lognormal
returns, annual rebalancing, smoothed (Yale-style) spending.

## Files
- `ai_endowment_tool.html` — the main interactive tool (self-contained; double-click to open).
- `montecarlo.py` — Python version of the engine (allocation sweep → CSV + charts).
- `README.md` — overview and assumptions.
- `chart_*.png` — example charts from the Python run.

There's a Desktop shortcut ("AI Fund Simulator") that opens the tool.

## What's been built in the tool
- **Explorer tab:** sliders for every assumption; live fan chart of corpus, payout
  fan, terminal-outcome histogram, headline stats, and four downside-risk metrics
  (cut probability, worst cut depth, capital impairment, severe drawdown).
- **Sweep tab:** runs all allocations vs. one shared set of futures → tradeoff
  frontier, terminal-corpus heatmap, selectable risk-surface heatmap, best-per-objective
  table, and an editable head-to-head reference-allocation table.
- **Excel/CSV export:** projection (Explorer), sweep grid, and comparison table.
- **Displacement & demand module (optional, OFF by default):** a latent displacement
  factor drives a demand multiplier on distributions. Tunable displacement↔AI-return
  correlation (positive = self-hedged; negative = regulation/backlash where demand
  rises while AI falls). Presets: Off / AI-driven / Hardship / Backlash / Custom.
- **Collapsible control panel:** left-side sections collapse/expand; only Allocation
  open by default.

## Key findings so far
- ~25–35% AI / 55–65% Real / small Reserve is the sweet spot (high preservation +
  downside) for modest growth give-up vs. all-AI.
- At a 2.5% spend rate the Reserve bucket barely earns its keep; it matters more at
  higher spend rates.
- Self-hedged demand (Disp↔AI positive) protects the downside; the Backlash case
  (Disp↔AI negative) is the worst case for the fund.

## OPEN / NEXT STEPS
- [ ] **Publish to GitHub (public, with Pages live link).** Status: local git repo is
      initialized and committed (the displacement feature + collapsible panel may be
      uncommitted). User has NO GitHub account yet. The `gh` CLI installer was
      downloaded to `~/Downloads/gh_install.pkg`.
      Remaining manual steps for the user:
        1. Create a free account at https://github.com/signup
        2. Install gh: double-click `~/Downloads/gh_install.pkg`
        3. Log in: `gh auth login --web --git-protocol https --hostname github.com`
      Then Claude can: commit pending changes, create the public repo, push, and
      enable GitHub Pages for the live URL.
      (Alternative if GitHub feels heavy: a drag-and-drop host like tiiny.host for a
      60-second shareable link, or just email/AirDrop the self-contained HTML file.)

## Ideas not yet built (offered)
- Record displacement scenario settings inside the CSV exports.
- Save/load named scenarios so slider settings persist between sessions.
- A multi-sheet .xlsx export instead of separate CSVs.
- "Expand all / collapse all" control for the left panel.

## How to resume the conversation with Claude
From Terminal, in `/Users/jasperryckman`, run `claude --continue` (most recent) or
`claude --resume` (pick from a list).
