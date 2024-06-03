import numpy as np
import pandas as pd
import talib


def sar(high, low, acceleration=0, maximum=0):
    """
    Calculate the Parabolic Stop and Reverse (SAR) indicator using the default parameters.
    Args:
        high (list or array-like): The high prices of the asset for each period.
        low (list or array-like): The low prices of the asset for each period.
        acceleration (float): The acceleration factor for SAR calculation. Default is 0.
        maximum (float): The maximum value for the acceleration factor. Default is 0.
    Returns:
        numpy array: The calculated SAR values for each period.
    """
    return talib.SAR(high, low, acceleration, maximum)


class Supertrend:
    def __init__(self, high, low, close, length, multiplier):
        """
        Initialize the Supertrend indicator.
        Using this class as a supertrend indicator make its calculation much faster and more reliable,
        since there are issues associated with lookback and keeping track of the trend with the other implementations.
        Args:
            high (list or ndarray): List or array of high prices.
            low (list or ndarray): List or array of low prices.
            close (list or ndarray): List or array of close prices.
            length (int): Length parameter for ATR calculation.
            multiplier (float): Multiplier parameter for Supertrend calculation.
        """
        self.high = pd.Series(high)
        self.low = pd.Series(low)
        self.close = pd.Series(close)
        self.length = length
        self.multiplier = multiplier
        self.trend = None
        self.dir = None
        self.lowerband = None
        self.upperband = None

    def update(self, high, low, close):
        """
        Update the Supertrend indicator with new price data.
        Args:
            high (list or ndarray): List or array of high prices.
            low (list or ndarray): List or array of low prices.
            close (list or ndarray): List or array of close prices.
        """
        high = pd.Series(high)
        low = pd.Series(low)
        close = pd.Series(close)

        price_diffs = [high - low, high - close.shift(), low - close.shift()]
        true_range = pd.concat(price_diffs, axis=1)
        true_range = true_range.abs().max(axis=1)
        true_range[0] = (high[0] + low[0]) / 2
        atr = true_range.ewm(alpha=1 / self.length, min_periods=self.length, ignore_na=True, adjust=False).mean()
        atr.fillna(0, inplace=True)

        hl2 = (high + low) / 2
        upperband = hl2 + (self.multiplier * atr)
        lowerband = hl2 - (self.multiplier * atr)

        if self.trend is None:
            self.trend = [np.nan] * close.size
            self.dir = [np.nan] * close.size

            for i in range(1, len(close)):
                curr, prev = i, i - 1

                lowerband[curr] = (
                    lowerband[curr]
                    if lowerband[curr] > lowerband[prev] or close[prev] < lowerband[prev]
                    else lowerband[prev]
                )

                upperband[curr] = (
                    upperband[curr]
                    if upperband[curr] < upperband[prev] or close[prev] > upperband[prev]
                    else upperband[prev]
                )

                if np.isnan(atr[prev]):
                    self.dir[curr] = -1
                elif self.trend[prev] == upperband[prev]:
                    self.dir[curr] = 1 if close[curr] > upperband[curr] else -1
                else:
                    self.dir[curr] = -1 if close[curr] < lowerband[curr] else 1

                self.trend[curr] = lowerband[curr] if self.dir[curr] == 1 else upperband[curr]

            self.lowerband = lowerband.values
            self.upperband = upperband.values
            return

        close = close.values
        upperband = upperband.values
        lowerband = lowerband.values

        lowerbandd = (
            lowerband[-1]
            if lowerband[-1] > self.lowerband[-1] or close[-1] < self.lowerband[-1]
            else self.lowerband[-1]
        )
        upperbandd = (
            upperband[-1]
            if upperband[-1] < self.upperband[-1] or close[-1] > self.upperband[-1]
            else self.upperband[-1]
        )

        if self.trend[-1] == self.upperband[-1]:
            dir = 1 if close[-1] > self.upperband[-1] else -1
        else:
            dir = -1 if close[-1] < self.lowerband[-1] else 1

        trend = lowerbandd if dir == 1 else upperbandd

        self.trend.append(trend)
        self.dir.append(dir)
        self.lowerband = np.append(self.lowerband, [lowerbandd])
        self.upperband = np.append(self.upperband, [upperbandd])


def hurst_exponent(data):
    """Calculate the Hurst exponent using the R/S method.
    Args:
        data (numpy.ndarray or list): The input time series data.
    Returns:
        float: The calculated Hurst exponent.
    """
    data = np.asarray(data)
    n = len(data)
    rs = np.zeros((len(data) // 2, 2))

    for i in range(1, n // 2 + 1):
        cumsum = np.cumsum(data - np.mean(data))
        rs[i - 1, 0] = np.max(cumsum[:i]) - np.min(cumsum[:i])
        rs[i - 1, 1] = np.std(data)

    avg_rs = np.mean(rs[:, 0] / rs[:, 1])

    return np.log2(avg_rs)


def atr(high, low, close, period):
    """
    Average True Range
    """
    return talib.ATR(high, low, close, period)


def stdev(source, period):
    """
    Calculate the rolling standard deviation of a time series data.
    Args:
        source (list or pandas.Series): The time series data for which to calculate the standard deviation.
        period (int): The number of periods to consider for the rolling standard deviation.

    Returns:
        numpy.ndarray: An array containing the rolling standard deviation values.
    """
    return pd.Series(source).rolling(period).std().values


def macd(close, fastperiod=12, slowperiod=26, signalperiod=9):
    """
    Calculate the Moving Average Convergence Divergence (MACD) using TA-Lib.
    Args:
        close (list or array-like): The close price time series data.
        fastperiod (int, optional): The number of periods for the fast moving average. Default is 12.
        slowperiod (int, optional): The number of periods for the slow moving average. Default is 26.
        signalperiod (int, optional): The number of periods for the signal line. Default is 9.
    Returns:
        tuple: A tuple containing three arrays: (macd, macdsignal, macdhist).
            - macd: The MACD line.
            - macdsignal: The signal line.
            - macdhist: The MACD histogram (the difference between MACD and signal).
    """
    return talib.MACD(close, fastperiod, slowperiod, signalperiod)


def cci(high, low, close, period):
    return talib.CCI(high, low, close, period)


def rci(src, itv):
    """
    Calculate the Rolling Coefficient of Inefficiency (RCI) indicator for a given data series.
    Args:
        src (list or numpy array): The input data series for which RCI will be calculated.
        itv (int): The size of the rolling window or interval used for RCI calculation.
    Returns:
        list: A list containing the RCI values for each window in the input data series.
    """
    reversed_src = src[::-1]
    ret = [(1.0 - 6.0 * d(reversed_src[i: i + itv], itv) / (itv * (itv * itv - 1.0))) * 100.0 for i in range(2)]
    return ret[::-1]


def sma(source, period):
    return pd.Series(source).rolling(period).mean().values


def ema(source, period):
    return talib.EMA(np.array(source), period)


def double_ema(src, length):
    ema_val = ema(src, length)
    return 2 * ema_val - ema(ema_val, length)


def triple_ema(src, length):
    ema_val = ema(src, length)
    return 3 * (ema_val - ema(ema_val, length)) + ema(ema(ema_val, length), length)


def wma(src, length):
    """
    Calculate the Weighted Moving Average (WMA) of a given dataset. (TA-lib)
    Args:
        src (list or numpy array): The input data.
        length (int): The period for the moving average.
    Returns:
        numpy array: The WMA values.
    """
    return talib.WMA(src, length)


def ewma(data, alpha):
    """
    Calculate Exponentially Weighted Moving Average (EWMA) using Pandas.
    Args:
        data (list or numpy array): Input data for calculating EWMA.
        alpha (float): Smoothing factor for EWMA.
    Returns:
        list: List containing the calculated EWMA values.
    """
    data_arr = np.asarray(data, dtype=float)
    ewma_series = pd.Series(data_arr).ewm(alpha=alpha).mean()
    ewma_list = ewma_series.tolist()
    return ewma_list


def ssma(src, length):
    return pd.Series(src).ewm(alpha=1.0 / length).mean().values.flatten()


def hull(src, length):
    return wma(2 * wma(src, length / 2) - wma(src, length), round(np.sqrt(length)))


def crossover(a, b):
    return a[-2] < b[-2] and a[-1] > b[-1]


def crossunder(a, b):
    return a[-2] > b[-2] and a[-1] < b[-1]


def ord(seq, sort_seq, idx, itv):
    """
    Calculate the ordinal rank of a given element in a sorted sequence.
    Args:
        seq (list or numpy array): The input unsorted data sequence.
        sort_seq (list or numpy array): The sorted version of the input data sequence.
        idx (int): The index of the element in the input sequence for which the rank is to be determined.
        itv (int): The number of elements in the sorted sequence.
    Returns:
        int: The ordinal rank of the element at the specified index in the sorted sequence.
    """
    p = seq[idx]
    for i in range(0, itv):
        if p >= sort_seq[i]:
            return i + 1


def highest(source, period):
    return pd.Series(source).rolling(period).max().values


def lowest(source, period):
    return pd.Series(source).rolling(period).min().values


def d(src, itv):
    """
    Calculate a custom metric to quantify the "disorder" or "inefficiency" of the data.
    Args:
        src (list or numpy array): The input data series for which the metric will be calculated.
        itv (int): The length of the metric calculation (number of periods).
    Returns:
        float: The calculated metric representing the "disorder" or "inefficiency" of the data.
    """
    sort_src = np.sort(src)[::-1]
    sum = 0.0
    for i in range(0, itv):
        sum += pow((i + 1) - ord(src, sort_src, i, itv), 2)
    return sum


def sharpe_ratio(returns, risk_free_rate):
    """
    Calculates the Sharpe ratio given a list of returns.
    Args:
        returns (list or array-like): List of decimal returns.
        risk_free_rate (float): Risk-free rate of return.
    Returns:
        float: Sharpe ratio.
    """
    returns = np.array(returns)
    excess_returns = returns - risk_free_rate
    std_dev = np.std(returns)
    sharpe_ratio = np.mean(excess_returns) / std_dev
    return sharpe_ratio
