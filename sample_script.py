
# import sys; sys.path.append("../")
from pythonclient.tradingClientBase import TradingClientBase
from sortedcontainers import SortedDict

class userTrading(TradingClientBase):
    
    def __init__(self, config_path: str, trading_universe: list, symbol_source: str):
        
        super().__init__(config_path, trading_universe, symbol_source)
        self.bid_dict = SortedDict()
        self.ask_dict = SortedDict()
        
        self.req_id = 1
        self.position_dict = {}

    def on_state_update(self, row_index, state, strategy_id, client_id, error_code, error_reason):
        self.config.masterlog.info("STATE UPDATE RECEIVED:", row_index, state, strategy_id, client_id, error_code, error_reason)
    
    def on_parameter_update(self, parameter_ls):
        self.config.masterlog.info("PARAMETER UPDATE RECEIVED:", parameter_ls)

    def on_trade_data(self, timestamp, symbol, price, size, open_interest):
        self.config.masterlog.info("TRADE DATA RECEIVED:", timestamp, symbol, price, size, open_interest)
    
    def on_ohlcv_data(self, start_ts, end_ts, symbol, open, high, low, close, volume, open_interest):
        self.config.masterlog.info("OHLCV DATA RECEIVED:", start_ts, end_ts, symbol, open, high, low, close, volume, open_interest)
    
    def on_bidask_data(self, timestamp, symbol, status, price, size, data_action, side, data_type):
        self.config.masterlog.info("BIDASK DATA RECEIVED:", timestamp, symbol, status, price, size, data_action, side, data_type)
        
        if symbol not in self.bid_dict:
            self.bid_dict[symbol] = SortedDict()
        
        if symbol not in self.ask_dict:
            self.ask_dict[symbol] = SortedDict()
        
        if data_action == 'DELETE':
            if side == 'BID':
                self.bid_dict[symbol].pop(price)
            else:
                self.ask_dict[symbol].pop(price)
        
        else:
            if side == 'BID':
                self.bid_dict[symbol][price] = size
            
            else:
                self.ask_dict[symbol][price] = size
        
        if data_type == 'INCREMENTAL':
            self.check_trade(side, symbol, price, size)
        
    ##
    def check_trade(self, side, symbol, price, size):
        if side == 'BID':
            best_bid = self.bid_dict[symbol].peekitem(-1)[0]

            if price > best_bid: # Placing a buy order at a price higher than the best bid
                self.place_order(symbol=symbol, side='BUY', price=price, size=1, price_type='LIMIT', time_in_force='DAY', req_id=self.req_id)
                self.req_id += 1
            
        if side == 'ASK':
            best_ask = self.ask_dict[symbol].peekitem(0)[0]

            if price < best_ask:
                self.place_order(symbol=symbol, side='SELL', price=price, size=1, price_type='LIMIT', time_in_force='DAY', req_id=self.req_id)
                self.req_id += 1
    
    def on_instrument_status(self, symbol, symbol_status, timestamp, req_status):
        self.config.masterlog.info("INSTRUMENT STATUS RECEIVED:", symbol, symbol_status, timestamp, req_status)
    
    def on_position_update(self, account_id, strategy_id, client_id, symbol, position, status):
        if status == "SUCCESS":
            self.position_dict[symbol] = position
        self.config.masterlog.info("POSITION UPDATE RECEIVED:", account_id, strategy_id, client_id, symbol, position, status)
    
    def on_pre_acknowledge(self, req_id, uuid):
        self.config.masterlog.info("PRE-ACKNOWLEDGE RECEIVED:", req_id, uuid)
    
    def on_acknowledge(self, ts, account_id, strategy_id, client_id, symbol, uuid, side, sent_price, sent_size, order_state, is_third_party_manual):
        self.config.masterlog.info("ACKNOWLEDGE RECEIVED:", ts, account_id, strategy_id, client_id, symbol, uuid, side, sent_price, sent_size, order_state, is_third_party_manual)
    
    def on_fill(self, ts, account_id, strategy_id, client_id, symbol, uuid, side, sent_price, sent_size, stop_price, exec_price, exec_size, order_state, is_third_party_manual):
        self.config.masterlog.info("FILL RECEIVED:", ts, account_id, strategy_id, client_id, symbol, uuid, side, sent_price, sent_size, stop_price, exec_price, exec_size, order_state, is_third_party_manual)
        
        if symbol not in self.position_dict:
            self.position_dict[symbol] = 0
        
        self.position_dict[symbol] += exec_size if side == 'BUY' else exec_size*-1
        self.config.masterlog.info("POSITION DICT:", self.position_dict)
        
        # shutting down if more than 10 fills have been received
        if abs(self.position_dict[symbol]) > 5:
            self.shutdown()
        
    
    def on_cancel(self, ts, account_id, strategy_id, client_id, symbol, uuid, sent_price, sent_size, stop_price, remaining_size, order_state, is_third_party_manual):
        self.config.masterlog.info("CANCEL RECEIVED:", ts, account_id, strategy_id, client_id, symbol, uuid, sent_price, sent_size, stop_price, remaining_size, order_state, is_third_party_manual)
    
    def on_reject(self, ts, account_id, strategy_id, client_id, symbol, uuid, sent_price, stop_price, order_state, rejection_code, rejection_reason, is_third_party_manual):
        self.config.masterlog.info("REJECT RECEIVED:", ts, account_id, strategy_id, client_id, symbol, uuid, sent_price, stop_price, order_state, rejection_code, rejection_reason, is_third_party_manual)

    def on_order_details(self, ts, account_id, strategy_id, client_id, symbol, uuid, side, sent_price, sent_size, stop_price, order_state, exec_price, exec_size, price_type, time_in_force):
        self.config.masterlog.info("ORDER DETAILS RECEIVED:", ts, account_id, strategy_id, client_id, symbol, uuid, side, sent_price, sent_size, stop_price, order_state, exec_price, exec_size, price_type, time_in_force)
        
    
####

if __name__ == "__main__":
    
    """
    Things to remember:
        1. Use start/stop from GUI to start/stop the strategy and place orders
        2. `cls_.run()` is a blocking call. It will keep running until the user presses Ctrl-C or `shutdown` is called
    """

    symbol_universe = ['ESH24', 'RTYH24']
    config_path = "config.json"
    cls_ = userTrading(config_path = config_path, trading_universe = symbol_universe, symbol_source = "SYMBOL_RIC")
    
    
    # You have to request a snapshot for each symbol in the trading universe before you can subscribe to data for that symbol
    # This is important if you are planning to use bidask data
    for symbol in symbol_universe:
        cls_.query_bidask_snapshot(symbol)
    
    ##
    cls_.subscribe_data(symbol_universe)
    cls_.run()
    

