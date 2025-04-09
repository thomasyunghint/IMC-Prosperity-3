from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
from typing import List, Any
import string
import json
import numpy as np
import math

class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        # We truncate state.traderData, trader_data, and self.logs to the same max. length to fit the log limit
        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])

        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]

        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )

        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]

        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])

        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        if len(value) <= max_length:
            return value

        return value[: max_length - 3] + "..."


logger = Logger()

class Trader:
    def __init__(self):
        self.MAX_IN = 50
        self.time = 0
        self.counter = 0
        self.kelp_vwaps = []
        self.ink_vwaps = []
        self.cnt = 0
    

    def find_midprice(self, order_depth):
        buy_vol, buy_val, sell_vol, sell_val = 0, 0, 0, 0

        for price, q in order_depth.buy_orders.items():
            volume = q
            buy_vol += volume
            buy_val += price * volume

        for price, q in order_depth.sell_orders.items():
            volume = -q
            sell_vol += volume
            sell_val += price * volume

        buy_vwap = buy_val / buy_vol
        sell_vwap = sell_val / sell_vol
        midprice = (buy_vwap + sell_vwap) / 2

        return midprice

    # function taken from nickliu github, really useful for squeezing extra resin (and for kelp a little bit)
    def clear_position_order(self, orders: List[Order], order_depth: OrderDepth, position: int, position_limit: int, product: str, buy_order_volume: int, sell_order_volume: int, fair_value: float, width: int) -> List[Order]:
        
        position_after_take = position + buy_order_volume - sell_order_volume
        fair_for_bid = math.floor(fair_value)
        fair_for_ask = math.ceil(fair_value)

        buy_quantity = position_limit - (position + buy_order_volume)
        sell_quantity = position_limit + (position - sell_order_volume)

        if position_after_take > 0:
            if fair_for_ask in order_depth.buy_orders.keys():
                clear_quantity = min(order_depth.buy_orders[fair_for_ask], position_after_take)
                sent_quantity = min(sell_quantity, clear_quantity)
                orders.append(Order(product, fair_for_ask, -abs(sent_quantity)))
                sell_order_volume += abs(sent_quantity)

        if position_after_take < 0:
            if fair_for_bid in order_depth.sell_orders.keys():
                clear_quantity = min(abs(order_depth.sell_orders[fair_for_bid]), abs(position_after_take))
                sent_quantity = min(buy_quantity, clear_quantity)
                orders.append(Order(product, fair_for_bid, abs(sent_quantity)))
                buy_order_volume += abs(sent_quantity)
    
        return buy_order_volume, sell_order_volume


    def kelp_orders(self, state, order_depth, product):
        orders = []

        midprice = self.find_midprice(order_depth)
        self.kelp_vwaps.append(midprice)
        self.kelp_vwaps = self.kelp_vwaps[-5:]
        fair_price = round(np.mean(self.kelp_vwaps)) 
        pos = state.position.get(product, 0)

        print(product, order_depth.buy_orders.items(), order_depth.sell_orders.items())
        print("Fair price : ", fair_price)
        ask_above = int(1e9)
        bid_below = 0

        buy_amt = 0
        sell_amt = 0

        for price, q in order_depth.sell_orders.items():
            if price > fair_price:
                ask_above = min(ask_above, price)
            elif price < fair_price:
                q = min(-q, self.MAX_IN - pos - buy_amt)
                orders.append(Order(product, price, q)) 
                buy_amt += q

        for price, q in order_depth.buy_orders.items():
            if price < fair_price:
                bid_below = max(bid_below, price)
            elif price > fair_price:
                q = min(q, self.MAX_IN + pos - sell_amt)
                orders.append(Order(product, price, -q)) 
                sell_amt += q

        if bid_below == 0:
            bid_below = fair_price
        if ask_above == int(1e9):
            ask_above = fair_price
        
        buy_amt, sell_amt = self.clear_position_order(orders, order_depth, pos, self.MAX_IN, product, buy_amt, sell_amt, fair_price, 1)
        bq = self.MAX_IN - pos - buy_amt
        if bq > 0:
            orders.append(Order(product, bid_below + 1, bq)) 

        sq = self.MAX_IN + pos - sell_amt
        if sq > 0:
            orders.append(Order(product, ask_above - 1, -sq)) 
        
        return orders


    def resin_orders(self, state, order_depth, product):
        orders = []
        fair_price = 10000
        pos = state.position.get(product, 0)

        print(product, order_depth.buy_orders.items(), order_depth.sell_orders.items())
        print("Fair price : ", fair_price)
        ask_above = int(1e9)
        bid_below = 0

        buy_amt = 0
        sell_amt = 0

        for price, q in order_depth.sell_orders.items():
            if price > fair_price:
                ask_above = min(ask_above, price)
            elif price < fair_price:
                q = min(-q, self.MAX_IN - pos - buy_amt)
                orders.append(Order(product, price, q)) 
                buy_amt += q

        for price, q in order_depth.buy_orders.items():
            if price < fair_price:
                bid_below = max(bid_below, price)
            elif price > fair_price:
                q = min(q, self.MAX_IN + pos - sell_amt)
                orders.append(Order(product, price, -q)) 
                sell_amt += q

        if bid_below == 0:
            bid_below = fair_price
        if ask_above == int(1e9):
            ask_above = fair_price

        buy_amt, sell_amt = self.clear_position_order(orders, order_depth, pos, self.MAX_IN, product, buy_amt, sell_amt, fair_price, 1)

        bq = self.MAX_IN - pos - buy_amt
        if bq > 0:
            orders.append(Order(product, bid_below + 1, bq)) 

        sq = self.MAX_IN + pos - sell_amt
        if sq > 0:
            orders.append(Order(product, ask_above - 1, -sq)) 
        
        return orders
    

    def ink_orders(self, state, order_depth, product):
        # params
        shift = 5
        buy_spread = 15
        sell_spread = 15
        rolling = 100

        orders = []
        midprice = self.find_midprice(order_depth)
        self.ink_vwaps.append(midprice)
        self.ink_vwaps = self.ink_vwaps[-rolling:]
        pos = state.position.get(product, 0)
        fair_price = round(np.mean(self.ink_vwaps)) - shift # assume going downwards, so subtract fair price by something
        # stdev = 47.192198
        
        # fair_price = round(2055.655589 + -0.005636 * self.time * 2 - 112.72)
        # fair_price = round(self.ink_vwaps[0] + -0.005636 * self.time * 2 - 50)

        print(product, order_depth.buy_orders.items(), order_depth.sell_orders.items())
        print("Fair price : ", fair_price)

        buy_amt = 0
        sell_amt = 0

        for price, q in order_depth.sell_orders.items():
            if price < fair_price - buy_spread:
                q = min(-q, self.MAX_IN - pos - buy_amt)
                orders.append(Order(product, price, q)) 
                buy_amt += q
                self.cnt += q

        for price, q in order_depth.buy_orders.items():
            if price > fair_price + sell_spread:
                q = min(q, self.MAX_IN + pos - sell_amt)
                orders.append(Order(product, price, -q)) 
                sell_amt += q
                self.cnt += q
        
        print("trades:", self.cnt)
        return orders

    
    def run(self, state: TradingState):
        # Only method required. It takes all buy and sell orders for all symbols as an input, and outputs a list of orders to be sent
        # print("traderData: " + state.traderData, self.ki)
        # print("Observations: " + str(state.observations))
        result = {}

        for product in state.order_depths:
            order_depth: OrderDepth = state.order_depths[product]
            orders: List[Order] = []

            if product == "KELP":
                orders += self.kelp_orders(state, order_depth, product)
            
            elif product == 'RAINFOREST_RESIN':
                orders += self.resin_orders(state, order_depth, product)
            
            elif product == 'SQUID_INK':
                orders += self.ink_orders(state, order_depth, product)
            
            result[product] = orders
    
        traderData = "SAMPLE" # String value holding Trader state data required. It will be delivered as TradingState.traderData on next execution.
        conversions = 1
        self.time += 1
        print("time:", self.time)
        logger.flush(state, result, conversions, traderData)
        return result, conversions, traderData
    
