# AlphaBaguette 🥖

This repository contains our final submission for the [IMC Prosperity 3](https://prosperity.imc.com/) trading competition (2025).  

**Final rank:**  
- 109th globally out of 4,000+ teams  
- 10th in France out of 300+ teams  

---

## 📜 About Prosperity 3

Prosperity 3 was a 15-day quantitative trading competition hosted by IMC, featuring five algorithmic rounds and five manual rounds.  
Each round introduced new products — ranging from simple mean-reverting assets to option contracts and ETFs — while keeping all previous products live.  

Our challenge as a team was to design robust trading algorithms under strict position limits, evolving market structures, and increasingly complex product interactions. The goal was to maximize **PNL in "SeaShells"**, the in-game currency, by combining **market microstructure intuition**, **risk management**, and **systematic trading strategies**.

---

## 👥 The Team

**AlphaBaguette** was a small team of French quant enthusiasts. We approached Prosperity 3 with the mindset of quantitative researchers:  
- start simple and robust,  
- analyze order book dynamics carefully,  
- gradually layer in statistical signals and arbitrage opportunities,  
- always manage risk under tight position limits.  

---

## 🧠 Strategy Overview

Our final submission combined several complementary strategies. The code is written in Python and runs inside the Prosperity 3 trading engine.  

### 1. Adaptive Market Making
- **Products:** Rainforest Resin, Kelp, Squid Ink, Magnificent Macarons  
- We quoted dynamically inside the spread with variable edge sizes, adapting to position imbalances and liquidity conditions.  
- Implemented both **taking** (crossing favorable orders) and **making** (placing limit orders at improved prices).  
- For volatile assets like Squid Ink, we added safeguards against adverse selection by filtering out “suspicious” small orders.

### 2. Informed Signal Trading (Olivia Detection)
- **Products:** Squid Ink, Croissants, Picnic Basket 2  
- In Round 5, the competition revealed the identities of trading bots. We discovered that bot **Olivia** consistently bought at daily lows and sold at daily highs.  
- Our algorithm parsed the trade history (`state.market_trades`) to detect Olivia’s activity:  
  - When Olivia bought Croissants against Caesar, we followed aggressively on the buy side.  
  - When Olivia sold, we mirrored the trade by selling.  
- We extended this logic to **Picnic Basket 2**, using Croissants’ trade flow as a proxy signal.  
- This gave us an **informed execution advantage** over naive market making.

### 3. Index Arbitrage
- **Product:** Picnic Basket 1 (6× Croissants, 3× Jams, 1× Djembe)  
- We continuously compared the basket mid-price to the synthetic fair value from its components.  
- If the basket traded at a large premium/discount (>5 units), we arbitraged by taking the opposite side.  
- For Basket 2, instead of synthetic arbitrage, we relied exclusively on Olivia-driven signals (per teammate discussion).

### 4. Options Pricing & Hedging
- **Products:** Volcanic Rock & 5 Vouchers (strikes 9500–10500)  
- Implemented a **Black–Scholes call model** with delta computation.  
- Each timestep, we priced the vouchers, compared them to market quotes, and traded mispricings.  
- We monitored implied volatility deviations using an Ornstein–Uhlenbeck (OU) process.  
- Large z-scores triggered slight price adjustments (e.g., buying undervalued options, selling overvalued ones).  
- Delta exposure across all vouchers was aggregated and hedged dynamically in the underlying Volcanic Rock.

### 5. Location Arbitrage
- **Product:** Magnificent Macarons  
- Arbitraged between the local order book and the external conversion market.  
- Adjusted our quoting edge dynamically based on recent fill volumes (adaptive edge tuning).  
- Combined active conversion with market making, ensuring we consistently captured the tariff- and fee-adjusted spread.

---

## ⚖️ Risk Management

- **Position limits:** strictly respected for all products.  
- **Soft limits:** adaptive quoting logic slowed down new orders when inventories approached critical thresholds.  
- **Stop-loss rules:** built into Olivia-based trades to reset state machines if positions filled too aggressively.  
- **Delta hedging:** kept overall exposure on Volcanic Rock under control, while allowing for limited volatility bets.  

---

## 🚀 Results & Lessons

- Our hybrid approach allowed us to rank **109th worldwide** and **10th in France**, among more than 4,000 teams.  
- We learned first-hand the importance of:
  - Exploiting **structural inefficiencies** (like Olivia’s predictable trades),  
  - Balancing **simple market making** with **signal-driven trades**,  
  - Managing risk under tight position constraints.  
- In hindsight, additional improvements could have included more aggressive basket arbitrage and refined statistical testing on option IV signals.  

---

## 📈 Key Takeaways

1. **Microstructure awareness beats complexity.** Understanding how bots traded (e.g., Olivia at extremes) created more alpha than overfitting fancy models.  
2. **Diversification across strategies matters.** Market making, arbitrage, and options scalping each contributed at different times.  
3. **Risk is everything.** Without strict position discipline, strategies that looked profitable in backtest would have collapsed in live runs.  

---

## 🏁 Final Thoughts

Competing in Prosperity 3 was an intense crash-course in quantitative trading.  
We are proud of AlphaBaguette’s performance: top 3% globally and top 10 in France.  

This repo contains our **final algorithmic submission (Round 5)**. We hope it helps future participants understand how to combine **adaptive market making, arbitrage, and informed signals** into a coherent trading system.

🥖 *AlphaBaguette, signing off.*
