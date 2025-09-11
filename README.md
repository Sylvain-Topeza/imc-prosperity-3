# AlphaBaguette 🥖

This repository contains our final submission for the [IMC Prosperity 3](https://prosperity.imc.com/) trading competition (2025).  

**Final rank:**  
- 109th globally out of 4,000+ teams  
- 10th in France out of 300+ teams  

---

## 📜 About Prosperity 3

Prosperity 3 was a 15-day quantitative trading competition hosted by IMC, featuring five algorithmic rounds and five manual rounds.  

Each round introduced new products — ranging from simple mean-reverting assets to option contracts and ETFs — while keeping all previous products live, forcing teams to design strategies that adapt to an increasingly complex market:  

- **Round 1:** basic assets (Resin, Kelp, Squid Ink).  
- **Round 2:** composite products (Croissants, Jams, Djembes, Picnic Baskets).  
- **Round 3:** options (Volcanic Rock + vouchers).  
- **Round 4:** location arbitrage (Magnificent Macarons).  
- **Round 5:** trader IDs revealed, enabling flow-based strategies.

Our challenge as a team was to design robust trading algorithms under strict position limits, evolving market structures, and increasingly complex product interactions. The goal was to maximize **PNL in "SeaShells"**, the in-game currency, by combining **market microstructure intuition**, **risk management**, and **systematic trading strategies**.

---

## 🧠 Strategy Overview

Our final submission combined several complementary strategies. The code is written in Python and runs inside the Prosperity 3 trading engine.

### 1. Adaptive Market Making
**Products:** Rainforest Resin, Kelp, Squid Ink, Magnificent Macarons  

For the simpler products (Resin and Kelp), we built market making logic that placed orders dynamically inside the spread. The quoting edge was adjusted according to inventory, recent trades, and available liquidity.  
- On **Resin**, the true value was fixed, making this a pure edge-capture problem.  
- On **Kelp**, we introduced a simple mean-reverting fair value update (Ornstein–Uhlenbeck style) to account for small random moves.  
- On **Squid Ink**, market making was more selective: we filtered out very small “toxic” orders that signaled potential adverse selection.  
- On **Macarons**, we merged making with location arbitrage (see below), adapting our quoting edge dynamically to observed trading volumes.

### 2. Informed Signal Trading (Olivia Detection)
**Products:** Squid Ink, Croissants, Picnic Basket 2  

In Round 5, trader IDs were revealed. Olivia’s trades were highly predictable: she consistently bought at daily lows and sold at daily highs.  
- On **Croissants**, we tracked recent trades with Caesar: Olivia buying from Caesar signaled us to buy, and the reverse signaled us to sell.  
- On **Squid Ink**, our logic switched into aggressive buy or sell “modes” when Olivia was detected.  
- On **Picnic Basket 2**, we tied execution directly to Croissant flows, extending the Olivia signal from Croissants into the basket.  

This informed flow-following gave us a consistent edge over purely statistical approaches.

### 3. Index Arbitrage
**Product:** Picnic Basket 1  

Basket 1 was priced against its synthetic composition (6 Croissants, 3 Jams, 1 Djembe). We continuously monitored the spread between the basket mid-price and this theoretical value.  
- When the basket traded at a significant premium, we sold it.  
- When it traded at a significant discount, we bought it.  

Unlike Basket 1, **Basket 2** was not arbitraged directly against its constituents. Instead, we relied exclusively on the Olivia-driven logic described above.

### 4. Options Pricing and Hedging
**Products:** Volcanic Rock and five strike vouchers (9500–10500)  

We implemented a Black–Scholes model to compute fair values and deltas for all vouchers.  
- Each timestep, we compared the theoretical option price to market mid-prices, trading when deviations appeared.  
- Implied volatilities were monitored and standardized into z-scores using an Ornstein–Uhlenbeck framework. Extreme z-scores slightly shifted our fair values to capture IV mean reversion.  
- All deltas across vouchers were aggregated, and we hedged exposure dynamically with the underlying Volcanic Rock.  

This kept risk under control while allowing us to systematically exploit mispricings across the option chain.

### 5. Location Arbitrage
**Product:** Magnificent Macarons  

Macarons could be traded on the local exchange or converted externally with tariffs and transport fees.  
- We derived implied fair bid and ask from the external market.  
- Whenever local prices diverged from these implied levels, we converted and traded.  
- To maximize fills, our quoting edge was adjusted based on recent volume history (adaptive tuning).  

This combination of conversion arbitrage and market making ensured that we consistently extracted value from Macarons’ dual-venue structure.

---

## ⚖️ Key Insights

- **Microstructure over models:** The most consistent edge came from recognizing Olivia’s predictable trading, not from over-engineering signals.  
- **Diversification mattered:** Resin/Kelp market making provided a stable base; baskets and options added bursts of PnL.  
- **Risk control was critical:** Every strategy respected hard position limits, with soft limits to avoid concentration risk.  
- **Adaptation each round:** From quoting basics to option pricing to informed flow, our bot evolved with the market.  

---

🥖 *AlphaBaguette – Final submission for IMC Prosperity 3 (2025)*  
