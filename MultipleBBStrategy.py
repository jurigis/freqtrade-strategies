
# --- Do not remove these libs ---
from freqtrade.strategy import IStrategy, merge_informative_pair,IntParameter,informative
from typing import Dict, List
from functools import reduce
from pandas import DataFrame
import freqtrade.vendor.qtpylib.indicators as qtpylib
# --------------------------------

import talib.abstract as ta


class MultipleBBStrategy(IStrategy):

    """
    MultipleBBStrategy
    author@: Jürgen Kraus
    github@: https://github.com/freqtrade/freqtrade-strategies
    """

    INTERFACE_VERSION: int = 3
    # This attribute will be overridden if the config file contains "minimal_roi"
    minimal_roi = {
        "60":  0.01,
        "30":  0.03,
        "20":  0.04,
        "0":  0.05
    }

    # This attribute will be overridden if the config file contains "stoploss"
    stoploss = -0.32

    # Optimal timeframe for the strategy
    timeframe = '15m'
    informative_tf = '1h'

    # trailing stoploss
    trailing_stop = True
    trailing_stop_positive = 0.01
    trailing_stop_positive_offset = 0.02

    # run "populate_indicators" only for new candle
    process_only_new_candles = False

    # Optional order type mapping
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'stoploss': 'market',
        'stoploss_on_exchange': False
    }

    buy_rsi = IntParameter(20, 50, default=22, space='buy')
    sell_rsi = IntParameter(70, 90, default=87, space='sell')
    buy_rsi_informative = IntParameter(30, 50, default=50, space='buy')

    @informative('1h')
    def populate_indicators_1h(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        # Get informative BB
        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_middleband'] = bollinger['mid']
        return dataframe

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:

        # Calculate rsi of the original dataframe (5m timeframe)
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)

        bollinger = qtpylib.bollinger_bands(dataframe['close'], window=20, stds=2)
        dataframe['bb_lowerband'] = bollinger['lower']
        dataframe['bb_upperband'] = bollinger['upper']
        dataframe['bb_middleband'] = bollinger['mid']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        conditions.append(qtpylib.crossed_above(dataframe['rsi'], self.buy_rsi.value))  # Signal: RSI crosses above buy_rsi.value
        conditions.append(dataframe['rsi_'+str(self.informative_tf)] < self.buy_rsi_informative.value)                    # Ensure informativ RSI lower threshold
        conditions.append(dataframe['bb_lowerband_'+str(self.informative_tf)] - dataframe['close_'+str(self.informative_tf)] < 0)

        # Check that volume is not 0
        conditions.append(dataframe['volume'] > 0)

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'enter_long'] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions = []

        #conditions.append(qtpylib.crossed_above(dataframe['rsi'], 90))  # Signal: RSI crosses above 30
        conditions.append(dataframe['rsi_'+str(self.informative_tf)] > self.sell_rsi.value)                    # Ensure daily RSI is < 30
        conditions.append(dataframe['bb_upperband_'+str(self.informative_tf)] - dataframe['close_'+str(self.informative_tf)] > 0)

        # Check that volume is not 0
        conditions.append(dataframe['volume'] > 0)

        if conditions:
            dataframe.loc[
                reduce(lambda x, y: x & y, conditions),
                'exit_long'] = 1

        return dataframe
