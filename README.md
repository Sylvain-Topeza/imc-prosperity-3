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

# AlphaBaguette 🥖

Final submission for the [IMC Prosperity 3](https://prosperity.imc.com/) trading competition (2025).  

**Result:** 109th globally (out of 4,000+ teams) and 10th in France (out of 300+ teams).  

---

## 📜 About Prosperity 3

Prosperity is a 15-day algorithmic trading competition hosted by IMC.  
Each round introduced new products while keeping all previous ones active, forcing teams to design strategies that adapt to an increasingly complex market:

- **Round 1:** basic assets (Resin, Kelp, Squid Ink).  
- **Round 2:** composite products (Croissants, Jams, Djembes, Picnic Baskets).  
- **Round 3:** options (Volcanic Rock + vouchers).  
- **Round 4:** location arbitrage (Magnificent Macarons).  
- **Round 5:** trader IDs revealed, enabling flow-based strategies.  

---

## 🧠 Strategy Overview

Our final algorithm combined several quantitative approaches. Below is a structured overview of our strategies.

### **Round 1 – Market Making Foundation**
- **Rainforest Resin & Kelp**  
  - Used adaptive market making: posting buy orders slightly below fair value and sell orders above.  
  - For Kelp, included a simple mean-reversion adjustment (Ornstein–Uhlenbeck style) to refine fair value estimation.  
- **Squid Ink**  
  - Introduced filters against small “toxic” orders.  
  - Integrated a mode that followed Olivia’s trades once she was revealed (Round 5).

### **Round 2 – Basket Arbitrage**
- **Picnic Basket 1**  
  - Classical index arbitrage: compared basket mid-price to synthetic fair value (6 Croissants + 3 Jams + 1 Djembe).  
  - Took positions whenever the deviation exceeded a fixed threshold.  
- **Croissants & Jams**  
  - Served as inputs to baskets but also traded individually.  
  - Added informed trading on Croissants once Olivia’s pattern was identified.  
- **Picnic Basket 2**  
  - We chose not to run synthetic arbitrage. Instead, we tied Basket 2 execution directly to Croissant flows (see Round 5).

### **Round 3 – Options Pricing**
- **Volcanic Rock & Vouchers**  
  - Implemented Black–Scholes pricing with delta computation.  
  - Compared theoretical values to market mid-prices to detect mispricings.  
  - Adjusted theoretical price slightly based on implied volatility z-scores.  
  - Aggregated delta exposure across vouchers and hedged in the underlying Volcanic Rock.  

### **Round 4 – Location Arbitrage**
- **Magnificent Macarons**  
  - Arbitraged between local order book and the external conversion market (with tariffs and fees).  
  - Adaptive edge: quoting logic adjusted based on recent trading volumes.  
  - Combined aggressive arbitrage (taking mispriced orders) with passive liquidity provision around the implied fair bid/ask.

### **Round 5 – Trader IDs & Informed Signals**
- **Olivia detection**  
  - On **Croissants**: when Olivia bought from Caesar, we entered long; when she sold, we followed short.  
  - On **Basket 2**: extended Croissant-based signals to baskets.  
  - On **Squid Ink**: adapted position to Olivia’s trades, switching between aggressive buy/sell modes.  
- This flow-based logic gave a clear edge over purely statistical approaches.

---

## ⚖️ Key Insights

- **Microstructure over models:** The most consistent edge came from recognizing Olivia’s predictable trading, not from over-engineering signals.  
- **Diversification mattered:** Resin/Kelp market making provided a stable base; baskets and options added bursts of PnL.  
- **Risk control was critical:** Every strategy respected hard position limits, with soft limits to avoid concentration risk.  
- **Adaptation each round:** From quoting basics to option pricing to informed flow, our bot evolved with the market.  

---

🥖 *AlphaBaguette – Final submission for IMC Prosperity 3 (2025)*  
