from datamodel import OrderDepth, TradingState, Order, Trade, ProsperityEncoder, Observation, Listing, Symbol
from typing import List, Dict, Tuple, Any
import jsonpickle
import numpy as np
import math
import json

class Product:
    RAINFOREST_RESIN = "RAINFOREST_RESIN"
    KELP = "KELP"
    PICNIC_BASKET1 = "PICNIC_BASKET1"
    PICNIC_BASKET2 = "PICNIC_BASKET2"
    CROISSANTS = "CROISSANTS"
    JAMS = "JAMS"
    DJEMBES = "DJEMBES"
    SQUID_INK = "SQUID_INK"
    MAGNIFICENT_MACARONS = "MAGNIFICENT_MACARONS"

class ConversionObservation:
    def __init__(self, bidPrice: float, askPrice: float, transportFees: float, exportTariff: float, importTariff: float, sugarPrice: float, sunlightIndex: float):
        self.bidPrice = bidPrice
        self.askPrice = askPrice
        self.transportFees = transportFees
        self.exportTariff = exportTariff
        self.importTariff = importTariff
        self.sugarPrice = sugarPrice
        self.sunlightIndex = sunlightIndex
        
conversion_obs = {
    "MAGNIFICENT_MACARONS": ConversionObservation(
        bidPrice=100,
        askPrice=105,
        transportFees=1.0,
        exportTariff=0.5,
        importTariff=0.5,
        sugarPrice=50.0,
        sunlightIndex=0.8
    )
}

observations = Observation(
    plainValueObservations={},
    conversionObservations=conversion_obs
)
        
PARAMS = {
    Product.RAINFOREST_RESIN: {
        "fair_value": 10000,
        "take_width": 1,
        "clear_width": 1,
        "volume_limit": 20
    },
    Product.KELP: {
        "take_width": 1,
        "clear_width": 1,
        "prevent_adverse": False,
        "adverse_volume": 10,
        "reversion_beta": -0.229,
        "disregard_edge": 0,
        "join_edge": 1,
        "default_edge": 0,
    },
    Product.SQUID_INK: {
        "take_width": 3.83,
        "clear_width": 0,
        "prevent_adverse": True,
        "adverse_volume": 18,
        "reversion_beta": -0.17,
        "disregard_edge": 0,
        "join_edge": 0,
        "default_edge": 1,
    },
    Product.MAGNIFICENT_MACARONS:{
        "make_edge": 2,
        "make_min_edge": 1,
        "make_probability": 0.7,
        "init_make_edge": 1.5,
        "min_edge": 0.6,
        "volume_avg_timestamp": 3,
        "volume_bar": 50,
        "dec_edge_discount": 0.9,
        "step_size":0.6,
        
    }
}

class Trader:
    def __init__(self, params=None):
        if params is None:
            params = PARAMS
        self.params = params
        self.price_history: Dict[str, List[float]] = {"JAMS": []}
        self.window = 60
        self.short_window = 10
        self.entry_threshold = 1
        self.exit_threshold = 1
        self.position_size = 350
        self.stop_loss = 0.02
        self.take_profit = 0.03
        self.entry_price = None
        self.in_trade = False
        self.spread_mean = 0
        self.spread_std = 1
        self.spread_window = []
        self.window_size = 100
        self.beta = 0.1738
        self.alpha = 3183.36

        self.sigma = 0.3  # Implied volatility for Black-Scholes
        self.r = 0.0
        self.TRADING_DAYS = 252
        self.current_round = 3

        # OU mean-reversion parameters for IV signal
        self.ou_mu = 0.122261
        self.ou_sigma = 0.002313
        self.threshold = 400

        self.voucher_products = [
            "VOLCANIC_ROCK_VOUCHER_9500",
            "VOLCANIC_ROCK_VOUCHER_9750",
            "VOLCANIC_ROCK_VOUCHER_10000",
            "VOLCANIC_ROCK_VOUCHER_10250",
            "VOLCANIC_ROCK_VOUCHER_10500"
        ]

        self.LIMIT = {
            Product.RAINFOREST_RESIN: 50,
            Product.KELP: 50,
            Product.PICNIC_BASKET1: 60,
            Product.PICNIC_BASKET2: 100,
            Product.CROISSANTS: 250,
            Product.JAMS: 350,
            Product.DJEMBES: 60,
            Product.SQUID_INK: 20,
            Product.MAGNIFICENT_MACARONS: 75,
        }

    # Returns buy_order_volume, sell_order_volume
    def take_best_orders(
        self,
        product: str,
        fair_value: int,
        take_width: float,
        orders: List[Order],
        order_depth: OrderDepth,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
        prevent_adverse: bool = False,
        adverse_volume: int = 0,
    ) -> (int, int):
        position_limit = self.LIMIT[product]
        if len(order_depth.sell_orders) != 0:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_amount = -1 * order_depth.sell_orders[best_ask]

            if best_ask <= fair_value - take_width:
                quantity = min(
                    best_ask_amount, position_limit - position
                )  # max amt to buy
                if quantity > 0:
                    orders.append(Order(product, best_ask, quantity))
                    buy_order_volume += quantity
                    order_depth.sell_orders[best_ask] += quantity
                    if order_depth.sell_orders[best_ask] == 0:
                        del order_depth.sell_orders[best_ask]

        if len(order_depth.buy_orders) != 0:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_amount = order_depth.buy_orders[best_bid]
            if best_bid >= fair_value + take_width:
                quantity = min(
                    best_bid_amount, position_limit + position
                )  # should be the max we can sell
                if quantity > 0:
                    orders.append(Order(product, best_bid, -1 * quantity))
                    sell_order_volume += quantity
                    order_depth.buy_orders[best_bid] -= quantity
                    if order_depth.buy_orders[best_bid] == 0:
                        del order_depth.buy_orders[best_bid]
        return buy_order_volume, sell_order_volume

    def take_best_orders_with_adverse(
        self,
        product: str,
        fair_value: int,
        take_width: float,
        orders: List[Order],
        order_depth: OrderDepth,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
        adverse_volume: int,
    ) -> (int, int):

        position_limit = self.LIMIT[product]
        if len(order_depth.sell_orders) != 0:
            best_ask = min(order_depth.sell_orders.keys())
            best_ask_amount = -1 * order_depth.sell_orders[best_ask]
            if abs(best_ask_amount) <= adverse_volume:
                if best_ask <= fair_value - take_width:
                    quantity = min(
                        best_ask_amount, position_limit - position
                    )  # max amt to buy
                    if quantity > 0:
                        orders.append(Order(product, best_ask, quantity))
                        buy_order_volume += quantity
                        order_depth.sell_orders[best_ask] += quantity
                        if order_depth.sell_orders[best_ask] == 0:
                            del order_depth.sell_orders[best_ask]

        if len(order_depth.buy_orders) != 0:
            best_bid = max(order_depth.buy_orders.keys())
            best_bid_amount = order_depth.buy_orders[best_bid]
            if abs(best_bid_amount) <= adverse_volume:
                if best_bid >= fair_value + take_width:
                    quantity = min(
                        best_bid_amount, position_limit + position
                    )  # should be the max we can sell
                    if quantity > 0:
                        orders.append(Order(product, best_bid, -1 * quantity))
                        sell_order_volume += quantity
                        order_depth.buy_orders[best_bid] -= quantity
                        if order_depth.buy_orders[best_bid] == 0:
                            del order_depth.buy_orders[best_bid]

        return buy_order_volume, sell_order_volume

    def market_make(
        self,
        product: str,
        orders: List[Order],
        bid: int,
        ask: int,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
    ) -> (int, int):
        buy_quantity = self.LIMIT[product] - (position + buy_order_volume)
        if buy_quantity > 0:
            orders.append(Order(product, round(bid), buy_quantity))  # Buy order

        sell_quantity = self.LIMIT[product] + (position - sell_order_volume)
        if sell_quantity > 0:
            orders.append(Order(product, round(ask), -sell_quantity))  # Sell order
        return buy_order_volume, sell_order_volume

    def clear_position_order(
        self,
        product: str,
        fair_value: float,
        width: int,
        orders: List[Order],
        order_depth: OrderDepth,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
    ) -> List[Order]:
        position_after_take = position + buy_order_volume - sell_order_volume
        fair_for_bid = round(fair_value - width)
        fair_for_ask = round(fair_value + width)

        buy_quantity = self.LIMIT[product] - (position + buy_order_volume)
        sell_quantity = self.LIMIT[product] + (position - sell_order_volume)

        if position_after_take > 0:
            # Aggregate volume from all buy orders with price greater than fair_for_ask
            clear_quantity = sum(
                volume
                for price, volume in order_depth.buy_orders.items()
                if price >= fair_for_ask
            )
            clear_quantity = min(clear_quantity, position_after_take)
            sent_quantity = min(sell_quantity, clear_quantity)
            if sent_quantity > 0:
                orders.append(Order(product, fair_for_ask, -abs(sent_quantity)))
                sell_order_volume += abs(sent_quantity)

        if position_after_take < 0:
            # Aggregate volume from all sell orders with price lower than fair_for_bid
            clear_quantity = sum(
                abs(volume)
                for price, volume in order_depth.sell_orders.items()
                if price <= fair_for_bid
            )
            clear_quantity = min(clear_quantity, abs(position_after_take))
            sent_quantity = min(buy_quantity, clear_quantity)
            if sent_quantity > 0:
                orders.append(Order(product, fair_for_bid, abs(sent_quantity)))
                buy_order_volume += abs(sent_quantity)

        return buy_order_volume, sell_order_volume
    
    def make_rainforest_resin_orders(
        self,
        order_depth: OrderDepth,
        fair_value: int,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
        volume_limit: int,
    ) -> tuple[List[Order], int, int]:
        orders: List[Order] = []
        baaf = [price for price in order_depth.sell_orders.keys() if price > fair_value + 1]
        bbbf = [price for price in order_depth.buy_orders.keys() if price < fair_value - 1]
        if not baaf or not bbbf:
            return orders, buy_order_volume, sell_order_volume
        if baaf:
            baaf=min(baaf)
        if bbbf:
            bbbf=max(bbbf)
        if baaf <= fair_value + 2:
            if position <= volume_limit:
                baaf = fair_value + 3  # still want edge 2 if position is not a concern

        if bbbf >= fair_value - 2:
            if position >= -volume_limit:
                bbbf = fair_value - 3  # still want edge 2 if position is not a concern

        buy_order_volume, sell_order_volume = self.market_make(
            Product.RAINFOREST_RESIN,
            orders,
            bbbf + 1,
            baaf - 1,
            position,
            buy_order_volume,
            sell_order_volume,
        )
        return orders, buy_order_volume, sell_order_volume

    def take_orders(
        self,
        product: str,
        order_depth: OrderDepth,
        fair_value: float,
        take_width: float,
        position: int,
        prevent_adverse: bool = False,
        adverse_volume: int = 0,
    ) -> tuple[List[Order], int, int]:
        orders: List[Order] = []
        buy_order_volume = 0
        sell_order_volume = 0

        if prevent_adverse:
            buy_order_volume, sell_order_volume = self.take_best_orders_with_adverse(
                product,
                fair_value,
                take_width,
                orders,
                order_depth,
                position,
                buy_order_volume,
                sell_order_volume,
                adverse_volume,
            )
        else:
            buy_order_volume, sell_order_volume = self.take_best_orders(
                product,
                fair_value,
                take_width,
                orders,
                order_depth,
                position,
                buy_order_volume,
                sell_order_volume,
            )
        return orders, buy_order_volume, sell_order_volume

    def make_orders(
        self,
        product,
        order_depth: OrderDepth,
        fair_value: float,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
        disregard_edge: float, 
        join_edge: float,  
        default_edge: float,  
        manage_position: bool = False,
        soft_position_limit: int = 0,
        
    ):
        orders: List[Order] = []
        asks_above_fair = [
            price
            for price in order_depth.sell_orders.keys()
            if price > fair_value + disregard_edge
        ]
        bids_below_fair = [
            price
            for price in order_depth.buy_orders.keys()
            if price < fair_value - disregard_edge
        ]

        best_ask_above_fair = min(asks_above_fair) if len(asks_above_fair) > 0 else None
        best_bid_below_fair = max(bids_below_fair) if len(bids_below_fair) > 0 else None

        ask = round(fair_value + default_edge)
        if best_ask_above_fair != None:
            if abs(best_ask_above_fair - fair_value) <= join_edge:
                ask = best_ask_above_fair  # join
            else:
                ask = best_ask_above_fair - 1  # penny

        bid = round(fair_value - default_edge)
        if best_bid_below_fair != None:
            if abs(fair_value - best_bid_below_fair) <= join_edge:
                bid = best_bid_below_fair
            else:
                bid = best_bid_below_fair + 1

        if manage_position:
            if position > soft_position_limit:
                ask -= 1
            elif position < -1 * soft_position_limit:
                bid += 1

        buy_order_volume, sell_order_volume = self.market_make(
            product,
            orders,
            bid,
            ask,
            position,
            buy_order_volume,
            sell_order_volume,
        )

        return orders, buy_order_volume, sell_order_volume

    def clear_orders(
        self,
        product: str,
        order_depth: OrderDepth,
        fair_value: float,
        clear_width: int,
        position: int,
        buy_order_volume: int,
        sell_order_volume: int,
    ) -> (List[Order], int, int):
        orders: List[Order] = []
        buy_order_volume, sell_order_volume = self.clear_position_order(
            product,
            fair_value,
            clear_width,
            orders,
            order_depth,
            position,
            buy_order_volume,
            sell_order_volume,
        )
        return orders, buy_order_volume, sell_order_volume
    
    def KELP_fair_value(self, order_depth: OrderDepth, traderObject) -> float:
        if len(order_depth.sell_orders) != 0 and len(order_depth.buy_orders) != 0:
            best_ask = min(order_depth.sell_orders.keys())
            best_bid = max(order_depth.buy_orders.keys())
            filtered_ask = [
                price
                for price in order_depth.sell_orders.keys()
                if abs(order_depth.sell_orders[price])
                >= self.params[Product.KELP]["adverse_volume"]
            ]
            filtered_bid = [
                price
                for price in order_depth.buy_orders.keys()
                if abs(order_depth.buy_orders[price])
                >= self.params[Product.KELP]["adverse_volume"]
            ]
            mm_ask = min(filtered_ask) if len(filtered_ask) > 0 else None
            mm_bid = max(filtered_bid) if len(filtered_bid) > 0 else None
            if mm_ask == None or mm_bid == None:
                if traderObject.get("KELP_last_price", None) == None:
                    mmmid_price = (best_ask + best_bid) / 2
                else:
                    mmmid_price = traderObject["KELP_last_price"]
            else:
                mmmid_price = (mm_ask + mm_bid) / 2

            if traderObject.get("KELP_last_price", None) != None:
                last_price = traderObject["KELP_last_price"]
                last_returns = (mmmid_price - last_price) / last_price
                pred_returns = (
                    last_returns * self.params[Product.KELP]["reversion_beta"]
                )
                fair = mmmid_price + (mmmid_price * pred_returns)
            else:
                fair = mmmid_price
            traderObject["KELP_last_price"] = mmmid_price
            return fair
        return None

    def squid_ink_fair_value(self, order_depth, traderObject):
        if len(order_depth.sell_orders) != 0 and len(order_depth.buy_orders) != 0:
            best_ask = min(order_depth.sell_orders.keys())
            best_bid = max(order_depth.buy_orders.keys())
            filtered_ask = [price for price in order_depth.sell_orders.keys() if abs(order_depth.sell_orders[price]) >= self.params[Product.SQUID_INK]["adverse_volume"]]
            filtered_bid = [price for price in order_depth.buy_orders.keys() if abs(order_depth.buy_orders[price]) >= self.params[Product.SQUID_INK]["adverse_volume"]]
            mm_ask = min(filtered_ask) if filtered_ask else None
            mm_bid = max(filtered_bid) if filtered_bid else None
            if mm_ask is None or mm_bid is None:
                mmmid_price = (best_ask + best_bid) / 2 if traderObject.get("squid_ink_last_price") is None else traderObject["squid_ink_last_price"]
            else:
                mmmid_price = (mm_ask + mm_bid) / 2

            if traderObject.get("squid_ink_last_price") is not None:
                last_price = traderObject["squid_ink_last_price"]
                last_returns = (mmmid_price - last_price) / last_price
                pred_returns = last_returns * self.params[Product.SQUID_INK]["reversion_beta"]
                fair = mmmid_price + (mmmid_price * pred_returns)
            else:
                fair = mmmid_price
            traderObject["squid_ink_last_price"] = mmmid_price
            return fair
        return None

    def compute_mid_price(self, order_depth: OrderDepth) -> float:
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return None
        best_bid = max(order_depth.buy_orders.keys())
        best_ask = min(order_depth.sell_orders.keys())
        return (best_bid + best_ask) / 2

    def compute_spread(self, djembe_price, basket_price):
        return djembe_price - (self.beta * basket_price + self.alpha)
    
    def black_scholes_call(self, S: float, K: float, t: float, sigma: float) -> float:
        if t <= 0 or S <= 0 or K <= 0:
            return max(S - K, 0)
        d1 = (math.log(S / K) + (self.r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
        d2 = d1 - sigma * math.sqrt(t)
        N_d1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
        N_d2 = 0.5 * (1 + math.erf(d2 / math.sqrt(2)))
        return S * N_d1 - K * math.exp(-self.r * t) * N_d2

    def compute_delta(self, S: float, K: float, t: float, sigma: float) -> float:
        if t <= 0 or S <= 0 or K <= 0:
            return 1.0 if S > K else 0.0
        d1 = (math.log(S / K) + (self.r + 0.5 * sigma**2) * t) / (sigma * math.sqrt(t))
        N_d1 = 0.5 * (1 + math.erf(d1 / math.sqrt(2)))
        return N_d1

    def compute_mid_price(self, order_depth: OrderDepth) -> float:
        best_bid = max(order_depth.buy_orders.keys()) if order_depth.buy_orders else None
        best_ask = min(order_depth.sell_orders.keys()) if order_depth.sell_orders else None
        if best_bid is not None and best_ask is not None:
            return (best_bid + best_ask) / 2.0
        return best_bid if best_bid is not None else best_ask if best_ask is not None else 0.0

    def get_strike_price(self, product: str) -> float:
        try:
            return float(product.split("_")[-1])
        except:
            return 0.0

    def time_to_expiry(self) -> float:
        return max(7 - (self.current_round - 1), 1) / self.TRADING_DAYS
    
    
         

    def magnificent_macarons_arb_clear(self, position: int) -> int:
        conversions = max(-10, min(10, -position)) 
        return conversions

    
    def magnificent_macarons_implied_bid_ask(
        self,
        observation: ConversionObservation,
    ) -> (float, float):
        return observation.bidPrice - observation.exportTariff - observation.transportFees - 0.1, observation.askPrice + observation.importTariff + observation.transportFees

    def magnificent_macarons_adap_edge(
        self,
        timestamp: int,
        curr_edge: float,
        position: int,
        traderObject: dict
    ) -> float: 
        if timestamp == 0:
            traderObject["MAGNIFICENT_MACARONS"]["curr_edge"] = self.params[Product.MAGNIFICENT_MACARONS]["init_make_edge"]
            return self.params[Product.MAGNIFICENT_MACARONS]["init_make_edge"]


        traderObject["MAGNIFICENT_MACARONS"]["volume_history"].append(abs(position))
        if len(traderObject["MAGNIFICENT_MACARONS"]["volume_history"]) > self.params[Product.MAGNIFICENT_MACARONS]["volume_avg_timestamp"]:
            traderObject["MAGNIFICENT_MACARONS"]["volume_history"].pop(0)

        if len(traderObject["MAGNIFICENT_MACARONS"]["volume_history"]) < self.params[Product.MAGNIFICENT_MACARONS]["volume_avg_timestamp"]:
            return curr_edge
        elif not traderObject["MAGNIFICENT_MACARONS"]["optimized"]:
            volume_avg = np.mean(traderObject["MAGNIFICENT_MACARONS"]["volume_history"])

         
            if volume_avg >= self.params[Product.MAGNIFICENT_MACARONS]["volume_bar"]:
                traderObject["MAGNIFICENT_MACARONS"]["volume_history"] = [] 
                traderObject["MAGNIFICENT_MACARONS"]["curr_edge"] = curr_edge + self.params[Product.MAGNIFICENT_MACARONS]["step_size"]
                return curr_edge + self.params[Product.MAGNIFICENT_MACARONS]["step_size"]

           
            elif self.params[Product.MAGNIFICENT_MACARONS]["dec_edge_discount"] * self.params[Product.MAGNIFICENT_MACARONS]["volume_bar"] * (curr_edge - self.params[Product.MAGNIFICENT_MACARONS]["step_size"]) > volume_avg * curr_edge:
                if curr_edge - self.params[Product.MAGNIFICENT_MACARONS]["step_size"] > self.params[Product.MAGNIFICENT_MACARONS]["min_edge"]:
                    traderObject["MAGNIFICENT_MACARONS"]["volume_history"] = [] 
                    traderObject["MAGNIFICENT_MACARONS"]["curr_edge"] = curr_edge - self.params[Product.MAGNIFICENT_MACARONS]["step_size"]
                    traderObject["MAGNIFICENT_MACARONS"]["optimized"] = True
                    return curr_edge - self.params[Product.MAGNIFICENT_MACARONS]["step_size"]
                else:
                    traderObject["MAGNIFICENT_MACARONS"]["curr_edge"] = self.params[Product.MAGNIFICENT_MACARONS]["min_edge"]
                    return self.params[Product.MAGNIFICENT_MACARONS]["min_edge"]

        traderObject["MAGNIFICENT_MACARONS"]["curr_edge"] = curr_edge
        return curr_edge

    def magnificent_macarons_arb_take(
        self,
        order_depth: OrderDepth,
        observation: ConversionObservation,
        adap_edge: float,
        position: int
    ) -> (List[Order], int, int):
        orders: List[Order] = []
        position_limit = self.LIMIT[Product.MAGNIFICENT_MACARONS]
        buy_order_volume = 0
        sell_order_volume = 0

        implied_bid, implied_ask = self.magnificent_macarons_implied_bid_ask(observation)                                                                                                                                                                    

        buy_quantity = position_limit - position
        sell_quantity = position_limit + position

        ask = implied_ask + adap_edge

        foreign_mid = (observation.askPrice + observation.bidPrice) / 2
        aggressive_ask = foreign_mid - 1.6

        if aggressive_ask > implied_ask:
            ask = aggressive_ask

        edge = (ask - implied_ask) * self.params[Product.MAGNIFICENT_MACARONS]["make_probability"]

        for price in sorted(list(order_depth.sell_orders.keys())):
            if price > implied_bid - edge:
                break

            if price < implied_bid - edge:
                quantity = min(abs(order_depth.sell_orders[price]), buy_quantity)
                if quantity > 0:
                    orders.append(Order(Product.MAGNIFICENT_MACARONS, round(price), quantity))
                    buy_order_volume += quantity

        for price in sorted(list(order_depth.buy_orders.keys()), reverse=True):
            if price < implied_ask + edge:
                break

            if price > implied_ask + edge:
                quantity = min(abs(order_depth.buy_orders[price]), sell_quantity)
                if quantity > 0:
                    orders.append(Order(Product.MAGNIFICENT_MACARONS, round(price), -quantity))
                    sell_order_volume += quantity

        return orders, buy_order_volume, sell_order_volume

    

    def magnificent_macarons_arb_make(
        self,
        order_depth: OrderDepth,
        observation: ConversionObservation,
        position: int,
        edge: float,
        buy_order_volume: int,
        sell_order_volume: int,
    ) -> (List[Order], int, int):
        orders: List[Order] = []
        position_limit = self.LIMIT[Product.MAGNIFICENT_MACARONS]

        
        
        implied_bid, implied_ask = self.magnificent_macarons_implied_bid_ask(observation)

        bid = implied_bid - edge
        ask = implied_ask + edge

      
        foreign_mid = (observation.askPrice + observation.bidPrice) / 2
        aggressive_ask = foreign_mid - 1.6 

        
        if aggressive_ask >= implied_ask + self.params[Product.MAGNIFICENT_MACARONS]['min_edge']:
            ask = aggressive_ask
            print("AGGRESSIVE")
            print(f"ALGO ASK: {round(ask)}")
            print(f"ALGO BID: {round(bid)}")
        else:
            print(f"ALGO ASK: {round(ask)}")
            print(f"ALGO BID: {round(bid)}")

        filtered_ask = [price for price in order_depth.sell_orders.keys() if abs(order_depth.sell_orders[price]) >= 40]
        filtered_bid = [price for price in order_depth.buy_orders.keys() if abs(order_depth.buy_orders[price]) >= 25]

        # pennying
        if len(filtered_ask) > 0 and ask > filtered_ask[0]:
            if filtered_ask[0] - 1 > implied_ask:
                ask = filtered_ask[0] - 1
            else:
                ask = implied_ask + edge
        if len(filtered_bid) > 0 and  bid < filtered_bid[0]:
            if filtered_bid[0] + 1 < implied_bid:
                bid = filtered_bid[0] + 1
            else:
                bid = implied_bid - edge

        print(f"IMPLIED_BID: {implied_bid}")
        print(f"IMPLIED_ASK: {implied_ask}")
        print(f"FOREIGN ASK: {observation.askPrice}")
        print(f"FOREIGN BID: {observation.bidPrice}")

        best_bid = min(order_depth.buy_orders.keys())
        best_ask = max(order_depth.sell_orders.keys())

        buy_quantity = position_limit - (position + buy_order_volume)
        if buy_quantity > 0:
            orders.append(Order(Product.MAGNIFICENT_MACARONS, round(bid), buy_quantity))  

        sell_quantity = position_limit + (position - sell_order_volume)
        if sell_quantity > 0:
            orders.append(Order(Product.MAGNIFICENT_MACARONS, round(ask), -sell_quantity))  

        return orders, buy_order_volume, sell_order_volume


    def run(self, state: TradingState) -> Tuple[Dict[str, List[Order]], int, str]:
        result: Dict[str, List[Order]] = {}
        traderObject = {}
        
        if state.traderData is not None and state.traderData != "":
            traderObject = jsonpickle.decode(state.traderData)

        conversions = 0
        timestamp = state.timestamp

        
        # RAINFOREST_RESIN
        if Product.RAINFOREST_RESIN in self.params and Product.RAINFOREST_RESIN in state.order_depths:
            rainforest_resin_position = (state.position[Product.RAINFOREST_RESIN]
                                        if Product.RAINFOREST_RESIN in state.position else 0)
            rainforest_resin_take_orders, buy_order_volume, sell_order_volume = self.take_orders(
                Product.RAINFOREST_RESIN,
                state.order_depths[Product.RAINFOREST_RESIN],
                self.params[Product.RAINFOREST_RESIN]["fair_value"],
                self.params[Product.RAINFOREST_RESIN]["take_width"],
                rainforest_resin_position,
            )
            rainforest_resin_clear_orders, buy_order_volume, sell_order_volume = self.clear_orders(
                Product.RAINFOREST_RESIN,
                state.order_depths[Product.RAINFOREST_RESIN],
                self.params[Product.RAINFOREST_RESIN]["fair_value"],
                self.params[Product.RAINFOREST_RESIN]["clear_width"],
                rainforest_resin_position,
                buy_order_volume,
                sell_order_volume,
            )
            rainforest_resin_make_orders, _, _ = self.make_rainforest_resin_orders(
                state.order_depths[Product.RAINFOREST_RESIN],
                self.params[Product.RAINFOREST_RESIN]["fair_value"],
                rainforest_resin_position,
                buy_order_volume,
                sell_order_volume,
                self.params[Product.RAINFOREST_RESIN]["volume_limit"],
            )
            result[Product.RAINFOREST_RESIN] = (
                rainforest_resin_take_orders + rainforest_resin_clear_orders + rainforest_resin_make_orders
            )

        # KELP
        if Product.KELP in self.params and Product.KELP in state.order_depths:
            KELP_position = (state.position[Product.KELP]
                            if Product.KELP in state.position else 0)
            KELP_fair_value = self.KELP_fair_value(state.order_depths[Product.KELP], traderObject)
            KELP_take_orders, buy_order_volume, sell_order_volume = self.take_orders(
                Product.KELP,
                state.order_depths[Product.KELP],
                KELP_fair_value,
                self.params[Product.KELP]["take_width"],
                KELP_position,
                self.params[Product.KELP]["prevent_adverse"],
                self.params[Product.KELP]["adverse_volume"],
            )
            KELP_clear_orders, buy_order_volume, sell_order_volume = self.clear_orders(
                Product.KELP,
                state.order_depths[Product.KELP],
                KELP_fair_value,
                self.params[Product.KELP]["clear_width"],
                KELP_position,
                buy_order_volume,
                sell_order_volume,
            )
            KELP_make_orders, _, _ = self.make_orders(
                Product.KELP,
                state.order_depths[Product.KELP],
                KELP_fair_value,
                KELP_position,
                buy_order_volume,
                sell_order_volume,
                self.params[Product.KELP]["disregard_edge"],
                self.params[Product.KELP]["join_edge"],
                self.params[Product.KELP]["default_edge"],
            )
            result[Product.KELP] = KELP_take_orders + KELP_clear_orders + KELP_make_orders

        # Arbitrage PICNIC_BASKET1
        if all(p in state.order_depths for p in ["PICNIC_BASKET1", "CROISSANTS", "JAMS", "DJEMBES"]):
            d = state.order_depths
            croissant_mid = self.compute_mid_price(d["CROISSANTS"])
            jam_mid = self.compute_mid_price(d["JAMS"])
            djembe_mid = self.compute_mid_price(d["DJEMBES"])
            basket_mid = self.compute_mid_price(d["PICNIC_BASKET1"])
            if None not in [croissant_mid, jam_mid, djembe_mid, basket_mid]:
                fair_value = 6 * croissant_mid + 3 * jam_mid + djembe_mid
                deviation = basket_mid - fair_value
                position = state.position.get("PICNIC_BASKET1", 0)
                limit = self.LIMIT["PICNIC_BASKET1"]
                orders = result.get("PICNIC_BASKET1", [])
                if deviation < -5:
                    best_ask = min(d["PICNIC_BASKET1"].sell_orders.keys())
                    volume = min(-d["PICNIC_BASKET1"].sell_orders[best_ask], limit - position, 5)
                    if volume > 0:
                        orders.append(Order("PICNIC_BASKET1", best_ask, volume))
                elif deviation > 5:
                    best_bid = max(d["PICNIC_BASKET1"].buy_orders.keys())
                    volume = min(d["PICNIC_BASKET1"].buy_orders[best_bid], position + limit, 5)
                    if volume > 0:
                        orders.append(Order("PICNIC_BASKET1", best_bid, -volume))
                result["PICNIC_BASKET1"] = orders

        # Arbitrage PICNIC_BASKET2
        if all(p in state.order_depths for p in ["PICNIC_BASKET2", "CROISSANTS", "JAMS"]):
            d = state.order_depths
            croissant_mid = self.compute_mid_price(d["CROISSANTS"])
            jam_mid = self.compute_mid_price(d["JAMS"])
            basket_mid = self.compute_mid_price(d["PICNIC_BASKET2"])
            if None not in [croissant_mid, jam_mid, basket_mid]:
                fair_value = 4 * croissant_mid + 2 * jam_mid
                deviation = basket_mid - fair_value
                position = state.position.get("PICNIC_BASKET2", 0)
                limit = self.LIMIT["PICNIC_BASKET2"]
                orders = result.get("PICNIC_BASKET2", [])
                if deviation < -5:
                    best_ask = min(d["PICNIC_BASKET2"].sell_orders.keys())
                    volume = min(-d["PICNIC_BASKET2"].sell_orders[best_ask], limit - position, 5)
                    if volume > 0:
                        orders.append(Order("PICNIC_BASKET2", best_ask, volume))
                elif deviation > 5:
                    best_bid = max(d["PICNIC_BASKET2"].buy_orders.keys())
                    volume = min(d["PICNIC_BASKET2"].buy_orders[best_bid], position + limit, 5)
                    if volume > 0:
                        orders.append(Order("PICNIC_BASKET2", best_bid, -volume))
                result["PICNIC_BASKET2"] = orders

        # JAMS Trend Strategy
        product = "JAMS"
        orders_jams: List[Order] = []
        order_depth_jams: OrderDepth = state.order_depths[product]
        best_ask = min(order_depth_jams.sell_orders.keys()) if order_depth_jams.sell_orders else None
        best_bid = max(order_depth_jams.buy_orders.keys()) if order_depth_jams.buy_orders else None
        if best_ask is not None and best_bid is not None:
            mid_price = (best_ask + best_bid) / 2
            self.price_history[product].append(mid_price)
            if len(self.price_history[product]) > self.window:
                self.price_history[product] = self.price_history[product][-self.window:]
            if len(self.price_history[product]) == self.window:
                mean = np.mean(self.price_history[product])
                std = np.std(self.price_history[product])
                z_score = (mid_price - mean) / std if std > 0 else 0
                short_ma = np.mean(self.price_history[product][-self.short_window:])
                long_ma = mean
                pos_exchange = state.position.get(product, 0)
                if not self.in_trade:
                    if z_score < -self.entry_threshold and short_ma > long_ma:
                        volume = self.position_size
                        orders_jams.append(Order(product, best_ask, volume))
                        self.entry_price = best_ask
                        self.in_trade = True
                    elif z_score > self.entry_threshold and short_ma < long_ma:
                        volume = self.position_size
                        orders_jams.append(Order(product, best_bid, -volume))
                        self.entry_price = best_bid
                        self.in_trade = True
                else:
                    if pos_exchange > 0:
                        if mid_price <= self.entry_price * (1 - self.stop_loss) or mid_price >= self.entry_price * (1 + self.take_profit):
                            orders_jams.append(Order(product, best_bid, -pos_exchange))
                            self.in_trade = False
                    elif pos_exchange < 0:
                        if mid_price >= self.entry_price * (1 + self.stop_loss) or mid_price <= self.entry_price * (1 - self.take_profit):
                            orders_jams.append(Order(product, best_ask, -pos_exchange))
                            self.in_trade = False
        result[product] = orders_jams
        
        # MAGNIFICENT_MACARONS Strategy
        if Product.MAGNIFICENT_MACARONS in self.params and Product.MAGNIFICENT_MACARONS in state.order_depths :
            if "MAGNIFICENT_MACARONS" not in traderObject:
                traderObject["MAGNIFICENT_MACARONS"] = {
                    "curr_edge": self.params[Product.MAGNIFICENT_MACARONS]["init_make_edge"],
                    "volume_history": [],
                    "optimized": False
                }
            magnificent_macarons_position = (
                state.position[Product.MAGNIFICENT_MACARONS]
                if Product.MAGNIFICENT_MACARONS in state.position
                else 0
            )
            print(f"MAGNIFICENT_MACARONS POSITION: {magnificent_macarons_position}")
            pos = state.position.get(Product.MAGNIFICENT_MACARONS, 0)
            if state.timestamp<999100:    
                conversions = self.magnificent_macarons_arb_clear(
                    magnificent_macarons_position
                )

            adap_edge = self.magnificent_macarons_adap_edge(
                state.timestamp,
                traderObject["MAGNIFICENT_MACARONS"]["curr_edge"],
                magnificent_macarons_position,
                traderObject,
            )

            pos_after_clear = pos + conversions

            magnificent_macarons_take_orders, buy_order_volume, sell_order_volume = self.magnificent_macarons_arb_take(
                state.order_depths[Product.MAGNIFICENT_MACARONS],
                state.observations.conversionObservations[Product.MAGNIFICENT_MACARONS],
                adap_edge,
                pos_after_clear,
            )

            magnificent_macarons_make_orders, _, _ = self.magnificent_macarons_arb_make(
                state.order_depths[Product.MAGNIFICENT_MACARONS],
                state.observations.conversionObservations[Product.MAGNIFICENT_MACARONS],
                pos_after_clear,
                adap_edge,
                buy_order_volume,
                sell_order_volume
            )

            result[Product.MAGNIFICENT_MACARONS] = (
                magnificent_macarons_take_orders + magnificent_macarons_make_orders
            )


        # SQUID_INK Strategy
        if Product.SQUID_INK in self.params and Product.SQUID_INK in state.order_depths:
            product = Product.SQUID_INK
            ink_orders: List[Order] = []
            ink_position = state.position.get(product, 0)
            position_limit = 50  # nouvelle limite pour SQUID_INK
            # Utilisation d'une variable locale distincte pour le carnet
            ink_order_depth: OrderDepth = state.order_depths[product]
            recent_trades: List[Trade] = state.market_trades.get(product, [])
            
            # Charger la mémoire déjà présente dans traderObject ou initialiser par défaut
            memory = traderObject.get("SQUID_INK_memory", {"mode": 0})
            
            for trade in recent_trades:
                if trade.buyer == "Olivia":
                    memory["mode"] = 1
                    break
                elif trade.seller == "Olivia":
                    memory["mode"] = 2
                    break
            
            if memory["mode"] == 1 and ink_position < position_limit:
                remaining_volume = position_limit - ink_position
                for price in sorted(ink_order_depth.sell_orders.keys()):
                    sell_volume = -ink_order_depth.sell_orders[price]
                    volume_to_buy = min(sell_volume, remaining_volume)
                    if volume_to_buy > 0:
                        ink_orders.append(Order(product, price, volume_to_buy))
                        remaining_volume -= volume_to_buy
                    if remaining_volume <= 0:
                        break
                if ink_position + sum(order.quantity for order in ink_orders) >= position_limit:
                    memory["mode"] = 0
            
            elif memory["mode"] == 2 and ink_position > -position_limit:
                remaining_volume = ink_position + position_limit
                for price in sorted(ink_order_depth.buy_orders.keys(), reverse=True):
                    buy_volume = ink_order_depth.buy_orders[price]
                    volume_to_sell = min(buy_volume, remaining_volume)
                    if volume_to_sell > 0:
                        ink_orders.append(Order(product, price, -volume_to_sell))
                        remaining_volume -= volume_to_sell
                    if remaining_volume <= 0:
                        break
                if ink_position - sum(order.quantity for order in ink_orders) <= -position_limit:
                    memory["mode"] = 0
            
            traderObject["SQUID_INK_memory"] = memory
            result[Product.SQUID_INK] = ink_orders
        
        # CROISSANTS Strategy
        if "CROISSANTS" in state.order_depths:
            product = "CROISSANTS"
            croissants_orders: List[Order] = []
            croissants_position = state.position.get(product, 0)
            position_limit = 250  # limite pour CROISSANTS
            # Variable locale pour le carnet de croissants
            croissants_order_depth: OrderDepth = state.order_depths[product]
            recent_trades: List[Trade] = state.market_trades.get(product, [])
            
            # Charger ou initialiser la mémoire dédiée aux CROISSANTS dans traderObject
            memory = traderObject.get("CROISSANTS_memory", {"mode": 0})
            
            # Détection : Olivia agissant avec Caesar
            for trade in recent_trades:
                if trade.buyer == "Olivia" and trade.seller == "Caesar":
                    memory["mode"] = 1  # mode achat
                    break
                elif trade.seller == "Olivia" and trade.buyer == "Caesar":
                    memory["mode"] = 2  # mode vente
                    break
            
            # Logique d'achat
            if memory["mode"] == 1 and croissants_position < position_limit:
                remaining_volume = position_limit - croissants_position
                for price in sorted(croissants_order_depth.sell_orders.keys()):
                    sell_volume = -croissants_order_depth.sell_orders[price]
                    volume_to_buy = min(sell_volume, remaining_volume)
                    if volume_to_buy > 0:
                        croissants_orders.append(Order(product, price, volume_to_buy))
                        remaining_volume -= volume_to_buy
                    if remaining_volume <= 0:
                        break
                if croissants_position + sum(order.quantity for order in croissants_orders) >= position_limit:
                    memory["mode"] = 0
            
            # Logique de vente
            elif memory["mode"] == 2 and croissants_position > -position_limit:
                remaining_volume = croissants_position + position_limit
                for price in sorted(croissants_order_depth.buy_orders.keys(), reverse=True):
                    buy_volume = croissants_order_depth.buy_orders[price]
                    volume_to_sell = min(buy_volume, remaining_volume)
                    if volume_to_sell > 0:
                        croissants_orders.append(Order(product, price, -volume_to_sell))
                        remaining_volume -= volume_to_sell
                    if remaining_volume <= 0:
                        break
                if croissants_position - sum(order.quantity for order in croissants_orders) <= -position_limit:
                    memory["mode"] = 0
            
            # Mettre à jour traderObject et intégrer le résultat
            traderObject["CROISSANTS_memory"] = memory
            result[product] = croissants_orders

        # VOLCANIC_ROCK Strategy
        underlying_od = state.order_depths.get("VOLCANIC_ROCK", OrderDepth())
        underlying_mid = self.compute_mid_price(underlying_od) if underlying_od is not None else 0
        t_expiry = self.time_to_expiry()
        total_delta_exposure = 0.0
        z_scores = {}
        position_limits = {"VOLCANIC_ROCK": 400}
        for vp in self.voucher_products:
            position_limits[vp] = 200

        for product, order_depth in state.order_depths.items():
            orders_vp: List[Order] = []
            current_pos = state.position.get(product, 0)
            if product in self.voucher_products:
                strike = self.get_strike_price(product)
                theo_price = self.black_scholes_call(underlying_mid, strike, t_expiry, self.sigma)
                delta = self.compute_delta(underlying_mid, strike, t_expiry, self.sigma)
                total_delta_exposure += delta * current_pos

                option_mid = self.compute_mid_price(order_depth)
                if underlying_mid > 0 and option_mid > 0:
                    market_iv = math.sqrt(2 * math.pi / t_expiry) * (option_mid / underlying_mid)
                    z = (market_iv - self.ou_mu) / self.ou_sigma
                    z_scores[product] = z
                    if z < -self.threshold:
                        theo_price *= 1.005  
                    elif z > self.threshold:
                        theo_price *= 0.995  

                best_bid = max(order_depth.buy_orders.items(), key=lambda x: x[0], default=(None, 0))
                best_ask = min(order_depth.sell_orders.items(), key=lambda x: x[0], default=(None, 0))
                if best_bid[0] is not None and best_bid[0] > theo_price:
                    sell_amt = min(best_bid[1], current_pos + position_limits[product])
                    if sell_amt > 0:
                        orders_vp.append(Order(product, best_bid[0], -sell_amt))
                if best_ask[0] is not None and best_ask[0] < theo_price:
                    buy_amt = min(-best_ask[1], position_limits[product] - current_pos)
                    if buy_amt > 0:
                        orders_vp.append(Order(product, best_ask[0], buy_amt))
                result[product] = result.get(product, []) + orders_vp
            
            elif product == "VOLCANIC_ROCK":
                continue

        
        hedge_orders: List[Order] = []
        underlying_position = state.position.get("VOLCANIC_ROCK", 0)
        best_bid_vr = max(state.order_depths["VOLCANIC_ROCK"].buy_orders.items(), key=lambda x: x[0], default=(None, 0))
        best_ask_vr = min(state.order_depths["VOLCANIC_ROCK"].sell_orders.items(), key=lambda x: x[0], default=(None, 0))
        if total_delta_exposure > 300 and best_ask_vr[0] is not None:
            hedge_qty = min(int(total_delta_exposure), position_limits["VOLCANIC_ROCK"] - underlying_position)
            if hedge_qty > 0:
                hedge_orders.append(Order("VOLCANIC_ROCK", best_ask_vr[0], hedge_qty))
        elif total_delta_exposure < -300 and best_bid_vr[0] is not None:
            hedge_qty = min(int(-total_delta_exposure), underlying_position + position_limits["VOLCANIC_ROCK"])
            if hedge_qty > 0:
                hedge_orders.append(Order("VOLCANIC_ROCK", best_bid_vr[0], -hedge_qty))
        if hedge_orders:
            result["VOLCANIC_ROCK"] = result.get("VOLCANIC_ROCK", []) + hedge_orders

        
        print(f"Round {self.current_round} Z-scores: {z_scores}")
        print(f"Round {self.current_round} Total Delta Exposure: {total_delta_exposure}")
        self.current_round += 1

        traderData = jsonpickle.encode(traderObject)
    
        return result, conversions, traderData
   
