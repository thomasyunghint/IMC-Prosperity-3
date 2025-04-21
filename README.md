# 💡 Goldberg Sentiment‑Driven Asset Allocator

[![Python](https://img.shields.io/badge/python-3.8%2B-blue)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green)]()
[![CVXPY](https://img.shields.io/badge/cvxpy-1.3.0-orange)]()

A lightweight, high‑performance **quantitative allocator** that translates real‑world news sentiment into optimized buy‑and‑sell signals.  

---

## 🚀 Why This Repo

- **Easy to read**: Clear code, self‑documented functions, and intuitive variable names.  
- **Fintech‑smart**: Maps sentiment (±1.0 scale) to expected returns, then runs a convex optimizer to maximize net gain.  
- **Eye‑catching**: Beautiful console output, neat markdown docs, and plug‑and‑play sentiment mapping.

---

## ⚙️ Key Features

1. **Sentiment → Returns**  
   Assign each asset a “happiness score” from news events.  
2. **Nonlinear Fee Model**  
   Fees grow quadratically with trade size—captures real transaction costs.  
3. **Convex Optimization**  
   Uses [CVXPY](https://www.cvxpy.org) to solve for the exact mix of buys and shorts under risk and budget constraints.  
4. **Integer Percent Rounding**  
   Converts fractional allocations into whole‑percent orders for real trading.  
5. **Plug‑and‑Play**  
   Drop in your own sentiment map, adjust fee parameters, and go live in minutes.

---

## 🔍 How It Works

1. **Score Mapping**  
   Convert each news event’s sentiment into a numeric return expectation.

2. **Objective**  
   Maximize  
   ```text
   gain – fee = capital × (rᵀ x) – θ ∑ᵢ xᵢ²

3. **Constraints**  
   Total exposure (L1 norm) ≤ 100%
   Single-asset bounds: –50% ≤ xᵢ ≤ +50%
4. **Solve & Round**  
   Use CVXPY’s solver, then round fractions to whole percents for trading.
