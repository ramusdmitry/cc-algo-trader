# coding: UTF-8

import math
from collections.abc import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
import sklearn
import talib
from numpy import nan as npNaN
from pandas import Series
from scipy import stats

from src import verify_series



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


def sarext(
    high,
    low,
    startvalue=0,
    offsetonreverse=0,
    accelerationinitlong=0.02,
    accelerationlong=0.02,
    accelerationmaxlong=0.2,
    accelerationinitshort=0.02,
    accelerationshort=0.02,
    accelerationmaxshort=0.2,
):
    """
    Calculate the Extended Parabolic Stop and Reverse (SAR) indicator.
    Args:
        high (list or array-like): The high prices of the asset for each period.
        low (list or array-like): The low prices of the asset for each period.
        startvalue (float): The initial value for SAR. Default is 0.
        offsetonreverse (float): The offset applied to the price for SAR reversal. Default is 0.
        accelerationinitlong (float): The initial acceleration factor for long positions. Default is 0.02.
        accelerationlong (float): The acceleration factor for long positions. Default is 0.02.
        accelerationmaxlong (float): The maximum value for the acceleration factor in long positions. Default is 0.2.
        accelerationinitshort (float): The initial acceleration factor for short positions. Default is 0.02.
        accelerationshort (float): The acceleration factor for short positions. Default is 0.02.
        accelerationmaxshort (float): The maximum value for the acceleration factor in short positions. Default is 0.2.
    Returns:
        numpy array: The calculated absolute values of Extended SAR for each period.
    """
    return abs(
        talib.SAREXT(
            high,
            low,
            startvalue,
            offsetonreverse,
            accelerationinitlong,
            accelerationlong,
            accelerationmaxlong,
            accelerationinitshort,
            accelerationshort,
            accelerationmaxshort,
        )
    )


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
        atr = true_range.ewm(
            alpha=1 / self.length, min_periods=self.length, ignore_na=True, adjust=False
        ).mean()
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
                    if lowerband[curr] > lowerband[prev]
                    or close[prev] < lowerband[prev]
                    else lowerband[prev]
                )

                upperband[curr] = (
                    upperband[curr]
                    if upperband[curr] < upperband[prev]
                    or close[prev] > upperband[prev]
                    else upperband[prev]
                )

                if np.isnan(atr[prev]):
                    self.dir[curr] = -1
                elif self.trend[prev] == upperband[prev]:
                    self.dir[curr] = 1 if close[curr] > upperband[curr] else -1
                else:
                    self.dir[curr] = -1 if close[curr] < lowerband[curr] else 1

                self.trend[curr] = (
                    lowerband[curr] if self.dir[curr] == 1 else upperband[curr]
                )

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


def supertrend(high, low, close, length=None, multiplier=None, offset=None):
    """
    Indicator: Supertrend
    """
    length = int(length) if length and length > 0 else 7
    multiplier = float(multiplier) if multiplier and multiplier > 0 else 3.0
    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)
    high = verify_series(high, length)
    low = verify_series(low, length)
    close = verify_series(close, length)

    if high is None or low is None or close is None:
        return

    m = close.size
    dir_, trend = [1] * m, [0] * m
    long, short = [npNaN] * m, [npNaN] * m

    hl2_ = med_price(high, low)
    matr = multiplier * atr(high, low, close, length)
    upperband = hl2_ + matr
    lowerband = hl2_ - matr

    for i in range(1, m):
        if close.iloc[i] > upperband.iloc[i - 1]:
            dir_[i] = 1
        elif close.iloc[i] < lowerband.iloc[i - 1]:
            dir_[i] = -1
        else:
            dir_[i] = dir_[i - 1]
            if dir_[i] > 0 and lowerband.iloc[i] < lowerband.iloc[i - 1]:
                lowerband.iloc[i] = lowerband.iloc[i - 1]
            if dir_[i] < 0 and upperband.iloc[i] > upperband.iloc[i - 1]:
                upperband.iloc[i] = upperband.iloc[i - 1]

        if dir_[i] > 0:
            trend[i] = long[i] = lowerband.iloc[i]
        else:
            trend[i] = short[i] = upperband.iloc[i]

    _props = f"_{length}_{multiplier}"
    df = pd.DataFrame(
        {
            "SUPERT": trend,
            "SUPERTd": dir_,
            "SUPERTl": long,
            "SUPERTs": short,
        },
        index=close.index,
    )

    df.name = f"SUPERT{_props}"
    df.category = "overlap"

    if offset != 0 and offset is not None:
        df = df.shift(offset)

    return df


def tv_supertrend(high, low, close, length=14, multiplier=3):

    high = pd.Series(high)
    low = pd.Series(low)
    close = pd.Series(close)

    price_diffs = [high - low, high - close.shift(), low - close.shift()]
    true_range = pd.concat(price_diffs, axis=1)
    true_range = true_range.abs().max(axis=1)
    true_range[0] = (high[0] + low[0]) / 2
    atr = true_range.ewm(
        alpha=1 / length, min_periods=length, ignore_na=True, adjust=False
    ).mean()

    atr.fillna(0, inplace=True)

    hl2 = (high + low) / 2
    upperband = hl2 + (multiplier * atr)
    lowerband = hl2 - (multiplier * atr)

    dir = [np.NaN] * close.size
    trend = [np.NaN] * close.size

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
            dir[curr] = -1
        elif trend[prev] == upperband[prev]:
            dir[curr] = 1 if close[curr] > upperband[curr] else -1
        else:
            dir[curr] = -1 if close[curr] < lowerband[curr] else 1

        trend[curr] = lowerband[curr] if dir[curr] == 1 else upperband[curr]

    return pd.DataFrame(
        {
            "SUPERT": trend,
            "SUPERTd": dir,
            "SUPERTl": lowerband,
            "SUPERTs": upperband,
        },
        index=close.index,
    )


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


def lyapunov_exponent(data, dt):
    """
    Calculate the Lyapunov exponent for a given time series data.
    Parameters:
        data: Time series data of the dynamical system.
        dt (float): Time step between consecutive state vectors.
    Returns:
        float: The Lyapunov exponent.
    """
    data = data if isinstance(data[0], Iterable) else [data]
    n = len(data)
    d = len(data[0])
    epsilon = 1e-8

    sum_lyapunov = 0.0

    for i in range(n):
        x = data[i]

        v = np.zeros(d)
        v[0] = 1.0

        for j in range(d):
            x_forward = data[(i + j) % n]
            x_backward = data[(i - j) % n]

            forward_difference = x_forward - x
            backward_difference = x - x_backward

            norm_forward = np.linalg.norm(forward_difference) + epsilon
            norm_backward = np.linalg.norm(backward_difference) + epsilon

            v += (
                np.log(norm_forward / norm_backward)
                * backward_difference
                / norm_backward
            )

            v -= np.dot(v, x) * x / np.dot(x, x)

        sum_lyapunov += np.log(np.linalg.norm(v) + epsilon) / dt

    average_lyapunov = sum_lyapunov / n

    return average_lyapunov




def tr(high, low, close):
    """
    True Range
    """
    return talib.TRANGE(high, low, close)


def atr(high, low, close, period):
    """
    Average True Range
    """
    return talib.ATR(high, low, close, period)


def natr(high, low, close, period):
    """
    Calculate Normalized Average True Range (NATR) using TA-Lib.
    Args:
        high (list or np.ndarray): List or array of high prices.
        low (list or np.ndarray): List or array of low prices.
        close (list or np.ndarray): List or array of closing prices.
        period (int): Period for NATR calculation.
    Returns:
        np.ndarray: Array of NATR values.
    """
    return talib.NATR(high, low, close, timeperiod=period)


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


def stddev(source, period, nbdev=1):
    """
    Calculate the standard deviation of a time series data using TA-Lib.
    Args:
        source (list or numpy.ndarray): The time series data for which to calculate the standard deviation.
        period (int): The number of periods to consider for calculating the standard deviation.
        nbdev (int, optional): The number of standard deviations to use. Default is 1.
    Returns:
        numpy.ndarray: An array containing the standard deviation values.
    """
    return talib.STDDEV(source, timeperiod=period, nbdev=nbdev)


def vix(close, low, pd=23, bbl=23, mult=1.9, lb=88, ph=0.85, pl=1.01):
    """
    Calculate the VIX Histogram.
    Args:
        close (list): List of closing prices.
        low (list): List of low prices.
        pd (int, optional): Period for calculating the highest value. Default is 23.
        bbl (int, optional): Period for calculating the standard deviation. Default is 23.
        mult (float, optional): Multiplier for the standard deviation. Default is 1.9.
        lb (int, optional): Lookback period for calculating range high and range low. Default is 88.
        ph (float, optional): Threshold for calculating the range high. Default is 0.85.
        pl (float, optional): Threshold for calculating the range low. Default is 1.01.
    Returns:
        tuple: A tuple containing two lists:
            - green_hist: A list of boolean values indicating if each element represents a green histogram bar.
            - red_hist: A list of boolean values indicating if each element represents a red histogram bar.
    """
    hst = highest(close, pd)

    wvf = (hst - low) / hst * 100

    s_dev = mult * stdev(wvf, bbl)
    mid_line = sma(wvf, bbl)

    lower_band = mid_line - s_dev
    upper_band = mid_line + s_dev

    range_high = (highest(wvf, lb)) * ph
    range_low = (lowest(wvf, lb)) * pl

    green_hist = [
        wvf[-i] >= upper_band[-i] or wvf[-i] >= range_high[-i] for i in range(8)
    ][::-1]

    red_hist = [
        wvf[-i] <= lower_band[-i] or wvf[-i] <= range_low[-i] for i in range(8)
    ][::-1]

    return green_hist, red_hist


def ulcer_index(data):
    """
    Calculate the Ulcer Index of a given data series.
    Parameters:
        data (numpy.ndarray): Input data series.
    Returns:
        float: Ulcer Index value.
    """
    # Calculate the maximum drawdown
    max_drawdown = np.maximum.accumulate(data) - data

    # Square the maximum drawdown
    squared_drawdown = np.square(max_drawdown)

    # Calculate the average of squared drawdowns
    average_squared_drawdown = np.mean(squared_drawdown)

    # Take the square root to obtain the Ulcer Index
    ulcer_index = np.sqrt(average_squared_drawdown)

    return ulcer_index




def adx(high, low, close, period=14):
    """
    This function calculates the Average Directional Index (ADX) using TA-Lib.
    """
    return talib.ADX(high, low, close, period)


def di_plus(high, low, close, period=14):
    """
    This function calculates the Plus Directional Indicator (+DI) using TA-Lib.
    """
    return talib.PLUS_DI(high, low, close, period)


def di_minus(high, low, close, period=14):
    """
    This function calculates the Minus Directional Indicator (-DI) using TA-Lib.
    """
    return talib.MINUS_DI(high, low, close, period)


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


def obv(close, volume):
    """
    Calculates the On-Balance Volume (OBV) indicator using the ta-lib library.
    Args:
        close (list): List of closing prices.
        volume (list): List of volume values.
    Returns:
        list: OBV values.
    """
    obv = talib.OBV(close, volume)
    return obv


def mfi(high, low, close, volume, period=14):
    """
    Calculates the Money Flow Index (MFI) using the ta-lib library.
    Args:
        high (list): List of high prices.
        low (list): List of low prices.
        close (list): List of closing prices.
        volume (list): List of volume values.
        period (int, optional): Number of periods to consider (default is 14).
    Returns:
        list: MFI values.
    """
    mfi = talib.MFI(high, low, close, volume, timeperiod=period)
    return mfi


def stochastic(high, low, close, fastK_period=14, slowk_period=5, d_period=3):
    """
    Calculate the Stochastic indicator.
    Parameters:
        high: A list or array of high prices.
        low: A list or array of low prices.
        close: A list or array of closing prices.
        period: The number of periods to consider for the Stochastic calculation. Default is 14.
        k_period: The number of periods to consider for the %K line. Default is 5.
        d_period: The number of periods to consider for the %D line. Default is 3.
    Returns:
        slowk: The slow %K line values.
        slowd: The slow %D line values.
    """
    slowk, slowd = talib.STOCH(
        high,
        low,
        close,
        fastk_period=fastK_period,
        slowk_period=slowk_period,
        slowd_period=d_period,
    )
    return slowk, slowd


def cci(high, low, close, period):
    return talib.CCI(high, low, close, period)


def rsi(close, period=14):
    return talib.RSI(close, period)


def rsx(source, length=None, drift=None, offset=None):
    """
    Indicator: Relative Strength Xtra (inspired by Jurik RSX)
    """
    # Validate arguments
    length = int(length) if length and length > 0 else 14
    source = pd.Series(source)
    source = verify_series(source, length)
    # drift = get_drift(drift)
    # offset = get_offset(offset)

    if source is None:
        return

    # variables
    vC, v1C = 0, 0
    v4, v8, v10, v14, v18, v20 = 0, 0, 0, 0, 0, 0

    f0, f8, f10, f18, f20, f28, f30, f38 = 0, 0, 0, 0, 0, 0, 0, 0
    f40, f48, f50, f58, f60, f68, f70, f78 = 0, 0, 0, 0, 0, 0, 0, 0
    f80, f88, f90 = 0, 0, 0

    # Calculate Result
    m = source.size
    result = [npNaN for _ in range(0, length - 1)] + [0]
    for i in range(length, m):
        if f90 == 0:
            f90 = 1.0
            f0 = 0.0
            if length - 1.0 >= 5:
                f88 = length - 1.0
            else:
                f88 = 5.0
            f8 = 100.0 * source.iloc[i]
            f18 = 3.0 / (length + 2.0)
            f20 = 1.0 - f18
        else:
            if f88 <= f90:
                f90 = f88 + 1
            else:
                f90 = f90 + 1
            f10 = f8
            f8 = 100 * source.iloc[i]
            v8 = f8 - f10
            f28 = f20 * f28 + f18 * v8
            f30 = f18 * f28 + f20 * f30
            vC = 1.5 * f28 - 0.5 * f30
            f38 = f20 * f38 + f18 * vC
            f40 = f18 * f38 + f20 * f40
            v10 = 1.5 * f38 - 0.5 * f40
            f48 = f20 * f48 + f18 * v10
            f50 = f18 * f48 + f20 * f50
            v14 = 1.5 * f48 - 0.5 * f50
            f58 = f20 * f58 + f18 * abs(v8)
            f60 = f18 * f58 + f20 * f60
            v18 = 1.5 * f58 - 0.5 * f60
            f68 = f20 * f68 + f18 * v18
            f70 = f18 * f68 + f20 * f70
            v1C = 1.5 * f68 - 0.5 * f70
            f78 = f20 * f78 + f18 * v1C
            f80 = f18 * f78 + f20 * f80
            v20 = 1.5 * f78 - 0.5 * f80

            if f88 >= f90 and f8 != f10:
                f0 = 1.0
            if f88 == f90 and f0 == 0.0:
                f90 = 0.0

        if f88 < f90 and v20 > 0.0000000001:
            v4 = (v14 / v20 + 1.0) * 50.0
            if v4 > 100.0:
                v4 = 100.0
            if v4 < 0.0:
                v4 = 0.0
        else:
            v4 = 50.0
        result.append(v4)
    rsx = Series(result, index=source.index)

    # Offset
    if offset != 0 and offset is not None:
        rsx = rsx.shift(offset)

    return rsx


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
    ret = [
        (1.0 - 6.0 * d(reversed_src[i : i + itv], itv) / (itv * (itv * itv - 1.0)))
        * 100.0
        for i in range(2)
    ]
    return ret[::-1]


def klinger_oscillator(
    high, low, close, volume, ema_short_length=34, ema_long_length=55, signal_length=13
):
    """
    Calculates the Klinger Oscillator and Signal values based on high, low, close, and volume.
    Args:
        high (array-like): Array or list of high prices.
        low (array-like): Array or list of low prices.
        close (array-like): Array or list of closing prices.
        volume (array-like): Array or list of volume values.
        ema_short_length (int, optional): Length of the short EMA. Default is 34.
        ema_long_length (int, optional): Length of the long EMA. Default is 55.
        signal_length (int, optional): Length of the signal EMA. Default is 13.
    Returns:
        kvo (array): Array of Klinger Oscillator values.
        sig (array): Array of Signal values.
    """
    high = np.array(high)
    low = np.array(low)
    close = np.array(close)
    volume = np.array(volume)

    cumVol = np.cumsum(volume)
    if cumVol[-1] == 0:
        raise ValueError("No volume is provided by the data vendor.")

    hl_avg = (high + low + close) / 3
    hl_avg_diff = np.diff(hl_avg)
    sv = np.where(hl_avg_diff >= 0, volume[1:], -volume[1:])
    kvo = ema(sv, ema_short_length) - ema(sv, ema_long_length)
    sig = ema(kvo, signal_length)

    return kvo, sig




def sma(source, period):
    return pd.Series(source).rolling(period).mean().values


def ema(source, period):
    return talib.EMA(np.array(source), period)


def double_ema(src, length):
    ema_val = ema(src, length)
    return 2 * ema_val - ema(ema_val, length)


def dema(data, period):
    """
    Calculate the Double Exponential Moving Average (DEMA) of a given dataset. (TA-lib)
    Args:
        data (list or numpy array): The input data.
        period (int): The period for the moving average.
    Returns:
        numpy array: The DEMA values.
    """
    return talib.DEMA(data, timeperiod=period)


def triple_ema(src, length):
    ema_val = ema(src, length)
    return 3 * (ema_val - ema(ema_val, length)) + ema(ema(ema_val, length), length)


def tema(data, period):
    """
    Calculate the Triple Exponential Moving Average (TEMA) of a given dataset. (TA-lib)
    Args:
        data (list or numpy array): The input data.
        period (int): The period for the moving average.
    Returns:
        numpy array: The TEMA values.
    """
    return talib.TEMA(data, timeperiod=period)


def trima(data, period):
    """
    Calculate the Triangular Moving Average (TRIMA) of a given dataset. (TA-lib)
    Args:
        data (list or numpy array): The input data.
        period (int): The period for the moving average.
    Returns:
        numpy array: The TRIMA values.
    """
    return talib.TRIMA(data, timeperiod=period)


def kama(data, period):
    """
    Calculate Kaufman's Adaptive Moving Average (KAMA) of a given dataset. (TA-lib)
    Args:
        data (list or numpy array): The input data.
        period (int): The period for the moving average.
    Returns:
        numpy array: The KAMA values.
    """
    return talib.KAMA(data, timeperiod=period)


def mama(data, fastlimit=0.5, slowlimit=0.05):
    """
    Calculate the Mesa Adaptive Moving Average (MAMA) of a given dataset. (TA-lib)
    Args:
        data (list or numpy array): The input data.
        fastlimit (float): The fast limit parameter for MAMA.
        slowlimit (float): The slow limit parameter for MAMA.
    Returns:
        numpy array: The MAMA values.
    """
    return talib.MAMA(data, fastlimit=fastlimit, slowlimit=slowlimit)


def mavp(data, periods, minperiod=2, maxperiod=30, matype=0):
    """
    Calculate the Moving Average with Variable Period (MAVP) of a given dataset. (TA-lib)
    Args:
        data (list or numpy array): The input data.
        periods (list): A list of periods to be used for variable period calculation.
        minperiod (int): The minimum period for the moving average.
        maxperiod (int): The maximum period for the moving average.
        matype (int): The type of moving average to use.
    Returns:
        numpy array: The MAVP values.
    """
    return talib.MAVP(
        data, periods, minperiod=minperiod, maxperiod=maxperiod, matype=matype
    )


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


def vwma(data, volume_data, period, ma_type="sma"):
    """
    Calculate the Volume Weighted Moving Average (VWMA) of a given dataset using the specified moving average type. (using TA-lib)
    Args:
        price_data (list or numpy array): The price data.
        volume_data (list or numpy array): The volume data.
        period (int): The period for the moving average.
        ma_type (str): The type of moving average to use ('sma', 'ema', 'wma', 'dema', 'tema', etc.).
    Returns:
        numpy array: The VWMA values.
    """
    weighted_price = data * volume_data

    if ma_type == "sma":
        return talib.SMA(weighted_price, timeperiod=period)
    elif ma_type == "ema":
        return talib.EMA(weighted_price, timeperiod=period)
    elif ma_type == "wma":
        return talib.WMA(weighted_price, timeperiod=period)
    elif ma_type == "dema":
        return talib.DEMA(weighted_price, timeperiod=period)
    elif ma_type == "tema":
        return talib.TEMA(weighted_price, timeperiod=period)
    else:
        raise ValueError(
            "Invalid ma_type. Supported values are 'sma', 'ema', 'wma', 'dema', 'tema', etc."
        )


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


def vwap(high, low, volume):
    average_price = volume * (high + low) / 2
    return average_price.sum() / volume.sum()


def ssma(src, length):
    return pd.Series(src).ewm(alpha=1.0 / length).mean().values.flatten()


def hull(src, length):
    return wma(2 * wma(src, length / 2) - wma(src, length), round(np.sqrt(length)))




def bbands(source, timeperiod=5, nbdevup=2, nbdevdn=2, matype=0):
    return talib.BBANDS(source, timeperiod, nbdevup, nbdevdn, matype)


def donchian(high, low, lower_length=None, upper_length=None, offset=None, **kwargs):
    """
    Indicator: Donchian Channels (DC)
    """
    high = pd.Series(high)
    low = pd.Series(low)

    lower_length = int(lower_length) if lower_length and lower_length > 0 else 20
    upper_length = int(upper_length) if upper_length and upper_length > 0 else 20
    lower_min_periods = (
        int(kwargs["lower_min_periods"])
        if "lower_min_periods" in kwargs and kwargs["lower_min_periods"] is not None
        else lower_length
    )
    upper_min_periods = (
        int(kwargs["upper_min_periods"])
        if "upper_min_periods" in kwargs and kwargs["upper_min_periods"] is not None
        else upper_length
    )
    _length = max(lower_length, lower_min_periods, upper_length, upper_min_periods)
    high = verify_series(high, _length)
    low = verify_series(low, _length)

    if high is None or low is None:
        return

    lower = low.rolling(lower_length, min_periods=lower_min_periods).min()
    upper = high.rolling(upper_length, min_periods=upper_min_periods).max()
    mid = 0.5 * (lower + upper)

    if offset != 0 and offset is not None:
        lower = lower.shift(offset)
        mid = mid.shift(offset)
        upper = upper.shift(offset)

    lower.name = "DCL"
    mid.name = "DCM"
    upper.name = "DCU"
    mid.category = upper.category = lower.category = "volatility"

    # Prepare DataFrame to return
    data = {lower.name: lower, mid.name: mid, upper.name: upper}
    dcdf = pd.DataFrame(data)
    dcdf.name = f"DC_{lower_length}_{upper_length}"
    dcdf.category = mid.category

    return dcdf


def keltner_channel(high, low, close, period=20, atr_period=20, multiplier=2):
    """
    Calculate the Keltner Channel.
    Args:
        high (array-like): High prices.
        low (array-like): Low prices.
        close (array-like): Close prices.
        period (int, optional): Number of periods to use for calculations (default is 20).
        atr_period (int, optional): Number of periods to use for calculations of ATR (default is 20).
        multiplier (float, optional): Multiplier for the width of the channel (default is 2).
    Returns:
        tuple: A tuple containing:
            upper_band (ndarray): Upper band values.
            middle_band (ndarray): Middle band values.
            lower_band (ndarray): Lower band values.
    """
    # Calculate the middle band (EMA of the closing prices)
    middle_band = talib.EMA(close, timeperiod=period)

    # Calculate the average true range (ATR)
    atr = talib.ATR(high, low, close, timeperiod=atr_period)

    # Calculate the upper band (middle band + multiplier * ATR)
    upper_band = middle_band + (multiplier * atr)

    # Calculate the lower band (middle band - multiplier * ATR)
    lower_band = middle_band - (multiplier * atr)

    return upper_band, middle_band, lower_band




def highestbars(source, length):
    """
    Highest value offset for a given number of bars back.
    Returns offset to the highest bar.
    """
    source = source[-length:]
    offset = abs(length - 1 - np.argmax(source))

    return offset


def lowestbars(source, length):
    """
    Lowest value offset for a given number of bars back.
    Returns offset to the lowest bar.
    """
    source = source[-length:]
    offset = abs(length - 1 - np.argmin(source))

    return offset


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


def is_under(src, value, p):
    for i in range(p, -1, -1):
        if src[-i - 1] > value:
            return False
    return True


def is_over(src, value, p):
    for i in range(p, -1, -1):
        if src[-i - 1] < value:
            return False
    return True




def highest(source, period):
    return pd.Series(source).rolling(period).max().values


def lowest(source, period):
    return pd.Series(source).rolling(period).min().values


def med_price(high, low):
    """
    Also found in tradingview as hl2 source
    """
    return talib.MEDPRICE(high, low)


def avg_price(open, high, low, close):
    """
    Also found in tradingview as ohlc4 source
    """
    return talib.AVGPRICE(open, high, low, close)


def typ_price(high, low, close):
    """
    Typical price, also found in tradingview as hlc3 source
    """
    return talib.TYPPRICE(high, low, close)


def wclprice(high, low, close):
    """
    Calculate Weighted Close Price (WCLPRICE) using TA-Lib.
    Also found in tradingview as hlcc4
    Args:
        high (list or numpy array): List or array of high prices for the period.
        low (list or numpy array): List or array of low prices for the period.
        close (list or numpy array): List or array of closing prices for the period.
    Returns:
        numpy array: Array of WCLPRICE values.
    """
    wclprice = talib.WCLPRICE(high, low, close)
    return wclprice


def MAX(close, period):
    return talib.MAX(close, period)




def detrended_fluctuation_analysis(data, window_sizes):
    """
    Perform Detrended Fluctuation Analysis (DFA) on the given data.
    Parameters:
        data: 1-D array or list containing the data.
        window_sizes: List of window sizes (list of integers).
    Returns:
        List of tuples (window_size, fluctuation) representing the detrended fluctuation values.
    """
    data = np.asarray(data)

    cumulative_sum = np.cumsum(data - np.mean(data))

    fluctuation = []

    for window_size in window_sizes:
        if window_size > len(data):
            continue

        num_windows = len(data) // window_size

        local_trends = []
        local_detrended_data = []

        for i in range(num_windows):
            window_data = cumulative_sum[i * window_size : (i + 1) * window_size]

            polynomial = np.polyfit(np.arange(window_size), window_data, 1)

            local_trend = np.polyval(polynomial, np.arange(window_size))
            local_trends.extend(local_trend)

            local_detrended_data.extend(window_data - local_trend)

        local_trends = np.asarray(local_trends)
        local_detrended_data = np.asarray(local_detrended_data)

        rms = np.sqrt(np.mean(local_detrended_data**2))

        fluctuation.append((window_size, rms))

    return fluctuation


def psd(sig, fs):
    """
    Compute the Power Spectral Density (PSD) of a given signal.
    Parameters:
        sig (array-like): Input signal.
        fs (float): Sampling frequency of the signal.
    Returns:
        f (array-like): Frequency values.
        psd (array-like): Power Spectral Density values.
    """
    f, psd = scipy.welch(sig, fs=fs, nperseg=len(sig))
    return f, psd


def autocorrelation(data):
    n = len(data)
    mean = np.mean(data)
    autocorr = np.correlate(data - mean, data - mean, mode="full")
    autocorr /= autocorr[n - 1]
    return autocorr[n - 1 :]


def shannon_entropy(probabilities):
    """
    Calculates the Shannon entropy of a probability distribution.
    Args:
        probabilities (list): List of probabilities.
    Returns:
        float: Shannon entropy value.
    """
    entropy = 0
    for probability in probabilities:
        if probability > 0:
            entropy -= probability * math.log2(probability)
    return entropy


def brownian_motion(timesteps, dt, initial_position=0, drift=0, volatility=1):
    """Simulates a Brownian motion path.
    Args:
        timesteps (int): Number of time steps to simulate.
        dt (float): Time step size.
        initial_position (float, optional): Initial position of the Brownian motion. Defaults to 0.
        drift (float, optional): Drift parameter. Defaults to 0.
        volatility (float, optional): Volatility parameter. Defaults to 1.
    Returns:
        numpy.ndarray: Array of simulated positions.
    """
    num_dimensions = 1

    num_increments = int(timesteps / dt)

    increments = np.random.normal(
        loc=0, scale=np.sqrt(dt), size=(num_increments, num_dimensions)
    )

    path = np.cumsum(increments, axis=0)

    path = drift * dt + volatility * path

    path = initial_position + path

    return path


def brownian_bridge(timesteps, dt, initial_value, final_value):
    """Simulates a Brownian bridge path.
    Args:
        timesteps (int): Number of time steps to simulate.
        dt (float): Time step size.
        initial_value (float): Initial value of the bridge.
        final_value (float): Final value of the bridge.
    Returns:
        numpy.ndarray: Array of simulated values.
    """
    num_dimensions = 1

    num_increments = int(timesteps / dt)

    increments = np.random.normal(
        loc=0, scale=np.sqrt(dt), size=(num_increments, num_dimensions)
    )

    path = np.cumsum(increments, axis=0)

    path = initial_value + path * ((final_value - initial_value) / path[-1])

    return path


def bessel_process(timesteps, dt, initial_value):
    """Simulates a Bessel process path.
    Args:
        timesteps (int): Number of time steps to simulate.
        dt (float): Time step size.
        initial_value (float): Initial value of the process.
    Returns:
        numpy.ndarray: Array of simulated values.
    """
    num_dimensions = 1

    num_increments = int(timesteps / dt)

    increments = np.random.normal(
        loc=0, scale=np.sqrt(dt), size=(num_increments, num_dimensions)
    )

    path = np.cumsum(increments, axis=0)

    path = np.sqrt(initial_value**2 + 2 * np.cumsum(path, axis=0))

    return path


def bessel_process_euler_maruyama(T, dt, x0, n_paths):
    """
    Simulates paths of the Bessel process using the Euler-Maruyama method.
    Args:
        T (float): Total time.
        dt (float): Time step size.
        x0 (float): Initial value.
        n_paths (int): Number of paths to simulate.
    Returns:
        paths (ndarray): Array of shape (n_paths, n_steps) containing the simulated paths.
        t (ndarray): Array of time points.
    """
    t = np.arange(0, T, dt)
    n_steps = len(t)
    paths = np.zeros((n_paths, n_steps))
    paths[:, 0] = x0

    for i in range(1, n_steps):
        dW = np.random.normal(0, np.sqrt(dt), n_paths)
        paths[:, i] = np.sqrt(paths[:, i - 1] + 0.5 * dt) * dW + paths[:, i - 1]

    return paths, t


def ornstein_uhlenbeck_process(
    timesteps, dt, mean_reversion, volatility, initial_value
):
    """Simulates an Ornstein-Uhlenbeck process.
    Args:
        timesteps (int): Number of time steps to simulate.
        dt (float): Time step size.
        mean_reversion (float): Mean reversion rate.
        volatility (float): Volatility parameter.
        initial_value (float): Initial value of the process.
    Returns:
        numpy.ndarray: Array of simulated values.
    """
    num_dimensions = 1

    num_increments = int(timesteps / dt)

    increments = np.random.normal(
        loc=0, scale=np.sqrt(dt), size=(num_increments, num_dimensions)
    )

    path = np.cumsum(increments, axis=0)

    path = (
        initial_value
        + mean_reversion * path
        + volatility
        * np.sqrt(dt)
        * np.random.normal(loc=0, scale=1, size=(num_increments, num_dimensions))
    )

    return path


def cir_process(
    timesteps, dt, mean_reversion, volatility, long_term_mean, initial_value
):
    """Simulates a Cox-Ingersoll-Ross (CIR) process.
    Args:
        timesteps (int): Number of time steps to simulate.
        dt (float): Time step size.
        mean_reversion (float): Mean reversion rate.
        volatility (float): Volatility parameter.
        long_term_mean (float): Long-term mean value of the process.
        initial_value (float): Initial value of the process.
    Returns:
        numpy.ndarray: Array of simulated values.
    """
    num_dimensions = 1

    num_increments = int(timesteps / dt)

    increments = np.random.normal(
        loc=0, scale=np.sqrt(dt), size=(num_increments, num_dimensions)
    )

    path = np.cumsum(increments, axis=0)

    path = (
        initial_value
        + mean_reversion * (long_term_mean - path) * dt
        + volatility
        * np.sqrt(np.abs(path) * dt)
        * np.random.normal(loc=0, scale=1, size=(num_increments, num_dimensions))
    )

    return path


def heston_model(
    timesteps,
    dt,
    initial_price,
    mean_reversion,
    long_term_volatility,
    volatility_of_volatility,
    correlation,
    initial_volatility,
):
    num_dimensions = 2

    num_increments = int(timesteps / dt)

    increments = np.random.normal(
        loc=0, scale=np.sqrt(dt), size=(num_increments, num_dimensions)
    )

    stock_path = np.zeros(num_increments + 1)
    volatility_path = np.zeros(num_increments + 1)
    stock_path[0] = initial_price
    volatility_path[0] = initial_volatility

    for i in range(num_increments):
        volatility = (
            volatility_path[i]
            + mean_reversion * (long_term_volatility - volatility_path[i]) * dt
            + volatility_of_volatility * np.sqrt(volatility_path[i]) * increments[i, 1]
        )

        stock_path[i + 1] = (
            stock_path[i]
            + correlation * volatility_path[i] * increments[i, 0]
            + np.sqrt(1 - correlation**2)
            * np.sqrt(volatility_path[i])
            * increments[i, 1]
        )

        volatility_path[i + 1] = volatility

    return stock_path


def jump_diffusion_model(
    timesteps,
    dt,
    initial_price,
    mean_return,
    volatility,
    jump_intensity,
    jump_mean,
    jump_std,
):
    """Simulates a stock price path using the Jump Diffusion model.
    Args:
        timesteps (int): Number of time steps to simulate.
        dt (float): Time step size.
        initial_price (float): Initial price of the stock.
        mean_return (float): Mean return rate.
        volatility (float): Volatility of the stock.
        jump_intensity (float): Intensity of the jumps.
        jump_mean (float): Mean of the jump sizes.
        jump_std (float): Standard deviation of the jump sizes.
    Returns:
        numpy.ndarray: Array of simulated stock prices.
    """
    num_dimensions = 1

    num_increments = int(timesteps / dt)

    increments = np.random.normal(
        loc=0, scale=np.sqrt(dt), size=(num_increments, num_dimensions)
    )

    jump_occurrences = np.random.poisson(lam=jump_intensity * dt, size=num_increments)

    path = np.zeros(num_increments + 1)
    path[0] = initial_price

    for i in range(num_increments):
        drift = mean_return * dt
        diffusion = volatility * increments[i]

        jump = jump_occurrences[i] * np.random.normal(loc=jump_mean, scale=jump_std)

        path[i + 1] = path[i] + drift + diffusion + jump

    return path


def monte_carlo_simulation(
    start_equity,
    profit_to_loss_ratio,
    num_simulations,
    win_rate,
    num_steps,
    risk_per_trade_input,
    randomize_winrate=0,
    compounding=False,
):
    equity_curves = []

    for _ in range(num_simulations):
        equity_curve = [start_equity]
        equity = start_equity

        for _ in range(num_steps):
            # Randomize winrate if specified
            if randomize_winrate:
                random_factor = np.random.uniform(
                    1 - randomize_winrate, 1 + randomize_winrate
                )
                randomized_win_rate = win_rate * random_factor
            else:
                randomized_win_rate = win_rate

            # Calculate risk per trade as a percentage of equity
            risk_per_trade = start_equity * risk_per_trade_input

            # Simulate profit/loss based on winrate
            if np.random.rand() < randomized_win_rate:
                profit = profit_to_loss_ratio * risk_per_trade
            else:
                profit = -risk_per_trade

            # Update equity based on compounding or non-compounding logic
            if compounding:
                equity = equity + equity * profit / start_equity
            else:
                equity = equity + profit  # if equity + profit >= 0 else 0

            equity_curve.append(equity)

        equity_curves.append(equity_curve)

    plt.figure(figsize=(10, 6))
    for i, curve in enumerate(equity_curves):
        plt.plot(curve, label=f"Simulation {i+1}")

    max_drawdowns = [
        np.max(np.maximum.accumulate(curve) - curve) / start_equity * 100
        for curve in equity_curves
    ]
    average_drawdowns = [
        np.mean(np.maximum.accumulate(curve) - curve) / start_equity * 100
        for curve in equity_curves
    ]
    average_equity = [np.mean(curve) / start_equity * 100 for curve in equity_curves]
    max_equity = [np.max(curve) / start_equity * 100 for curve in equity_curves]

    win_rate_text = f"Win Rate: {randomized_win_rate * 100:.2f}%"
    max_drawdown_text = f"Max Drawdown: {np.max(max_drawdowns):.2f}%"
    average_drawdown_text = f"Average Drawdown: {np.mean(average_drawdowns):.2f}%"
    max_equity_text = f"Max Equity: {np.max(max_equity):.2f}%"
    average_equity_text = f"Average Equity: {np.mean(average_equity):.2f}%"

    plt.legend(
        [
            win_rate_text,
            max_drawdown_text,
            average_drawdown_text,
            average_equity_text,
            max_equity_text,
        ]
    )

    plt.xlabel("Steps")
    plt.ylabel("Equity")
    plt.title("Monte Carlo Simulation")
    plt.grid(True)
    plt.show()



def linreg(close, period):
    """
    Calculate Linear Regression (LINEARREG) using TA-Lib.

    Args:
        close (list or np.ndarray): List or array of closing prices.
        period (int): Period for LINEARREG calculation.

    Returns:
        np.ndarray: Array of LINEARREG values.
    """
    return talib.LINEARREG(close, timeperiod=period)


def linreg_slope(close, period):
    """
    Calculate Linear Regression Slope (LINEARREG_SLOPE) using TA-Lib.

    Args:
        close (list or np.ndarray): List or array of closing prices.
        period (int): Period for LINEARREG_SLOPE calculation.

    Returns:
        np.ndarray: Array of LINEARREG_SLOPE values.
    """
    return talib.LINEARREG_SLOPE(close, timeperiod=period)



def min_max_normalization(data):
    """
    Min-max normalization scales the values to a specific range, typically between 0 and 1.
    """
    normalized = (data - np.min(data)) / (np.max(data) - np.min(data))
    return normalized


def z_score_normalization(data):
    """
    Z-score normalization (also known as standardization) transforms the values to have a mean of 0 and a standard deviation of 1.
    """
    return stats.zscore(data)


def decimal_scaling_normalization(data):
    """
    Decimal scaling normalizes the values by dividing them by a suitable power of 10, based on the maximum absolute value in the dataset,
    often between -1 and 1.
    """
    magnitude = np.ceil(np.log10(np.max(np.abs(data))))
    return data / 10**magnitude


def log_normalization(data):
    """
    This method applies the natural logarithm function to the data, which can help reduce the impact of outliers and skewness.
    """
    return np.log1p(data)


def robust_normalization(data):
    """
    This method is robust to outliers and uses the median and interquartile range (IQR) to scale the data.
    """
    return sklearn.preprocessing.robust_scale(data)


def unit_vector_normalization(data):
    """
    Unit vector normalization (also known as vector normalization or L2 normalization)
    scales the values such that the Euclidean norm (L2 norm) of the vector is 1.
    """
    norms = scipy.linalg.norm(data, axis=1)
    return data / norms[:, np.newaxis]


def power_normalization(data, method="box-cox", power=1.0):
    data = np.asarray(data)

    valid_methods = ["box-cox", "yeo-johnson"]
    if method not in valid_methods:
        raise ValueError(
            f"Invalid method '{method}'. Supported methods are: {valid_methods}"
        )
    if method == "box-cox":
        normalized_data, _ = stats.boxcox(data, lmbda=power)
    else:
        normalized_data, _ = stats.yeojohnson(data, lmbda=power)

    return normalized_data


def softmax_normalization(data):
    exp_vals = np.exp(data)
    return exp_vals / np.sum(exp_vals)


def median_normalization(data):
    median_val = np.median(data)
    mad_val = stats.median_absolute_deviation(data)
    return (data - median_val) / mad_val


def pareto_scaling(data):
    std_val = np.std(data)
    return data / np.sqrt(std_val)


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


def compute_log_returns(balance_changes):
    """
    Computes the log returns of a list or NumPy array of balance changes.
    Args:
        balance_changes: A list or NumPy array of balance changes.
    Returns:
        log_returns: A list containing the log returns of the balance changes.
    """
    if isinstance(balance_changes, np.ndarray):
        mask = balance_changes > 0
        masked_balance_changes = np.ma.array(
            balance_changes, mask=~mask
        )
        log_returns = np.ma.log(masked_balance_changes).filled(0)
    else:
        log_returns = []
        for i, balance_change in enumerate(balance_changes):
            if balance_change > 0:
                log_returns.append(math.log(balance_change))
            else:
                log_returns.append(0.0)
        if len(log_returns) < len(balance_changes):
            log_returns.extend([0.0] * (len(balance_changes) - len(log_returns)))
    return log_returns
