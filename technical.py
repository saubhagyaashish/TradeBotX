"""technical.py — Technical indicator computation from raw candle data.

Computes indicators locally using pandas/numpy.
Input: OHLCV DataFrame from upstox_client.get_candles_as_df()

Indicators:
  - RSI (Relative Strength Index)
  - EMA (Exponential Moving Average)
  - SMA (Simple Moving Average)
  - MACD (Moving Average Convergence Divergence)
  - VWAP (Volume Weighted Average Price)
  - Bollinger Bands
  - Stochastic Oscillator
  - ATR (Average True Range)
  - Volume surge detector
  - Composite signal score
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
# INDIVIDUAL INDICATORS
# ══════════════════════════════════════════════════════════════════════════════


def compute_rsi(df: pd.DataFrame, period: int = 14, col: str = "close") -> pd.Series:
    """
    Compute RSI (Relative Strength Index).

    Returns:
        Series with RSI values (0-100). < 30 = oversold, > 70 = overbought.
    """
    delta = df[col].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)  # Default to neutral


def compute_ema(df: pd.DataFrame, period: int = 20, col: str = "close") -> pd.Series:
    """Compute Exponential Moving Average."""
    return df[col].ewm(span=period, adjust=False).mean()


def compute_sma(df: pd.DataFrame, period: int = 20, col: str = "close") -> pd.Series:
    """Compute Simple Moving Average."""
    return df[col].rolling(window=period).mean()


def compute_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    col: str = "close",
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Compute MACD (Moving Average Convergence Divergence).

    Returns:
        (macd_line, signal_line, histogram)
    """
    ema_fast = df[col].ewm(span=fast, adjust=False).mean()
    ema_slow = df[col].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_vwap(df: pd.DataFrame) -> pd.Series:
    """
    Compute VWAP (Volume Weighted Average Price).
    NOTE: Only meaningful on intraday data. For daily data, use compute_vwap_intraday().
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (typical_price * df["volume"]).cumsum()
    cumulative_vol = df["volume"].cumsum()
    vwap = cumulative_tp_vol / cumulative_vol.replace(0, np.nan)
    return vwap.fillna(df["close"])


def compute_vwap_intraday(intraday_df: pd.DataFrame) -> pd.Series:
    """
    Compute proper intraday VWAP from 5-minute (or similar) candles.
    Resets at market open each day (Fix #8: correct VWAP).

    Args:
        intraday_df: DataFrame with today's intraday candles (5min/1min)

    Returns:
        Series with VWAP values that reset daily.
    """
    if intraday_df is None or len(intraday_df) == 0:
        return pd.Series(dtype=float)

    df = intraday_df.copy()
    # Skip zero-volume rows (indices, pre-market)
    valid_vol = df["volume"].replace(0, np.nan)

    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cumulative_tp_vol = (typical_price * valid_vol).cumsum()
    cumulative_vol = valid_vol.cumsum()

    vwap = cumulative_tp_vol / cumulative_vol.replace(0, np.nan)
    return vwap.fillna(df["close"])


def compute_intraday_momentum(intraday_df: pd.DataFrame, lookback: int = 6) -> dict:
    """
    Compute intraday momentum from 5-min candles (Fix #8: new indicator).

    Checks:
      - Are the last N candles trending up or down?
      - Is the current candle's close higher than the VWAP?
      - Is volume increasing in the last N candles?

    Returns:
        dict with momentum metrics
    """
    if intraday_df is None or len(intraday_df) < lookback:
        return {"score": 0.5, "trend": "INSUFFICIENT_DATA"}

    recent = intraday_df.tail(lookback)
    closes = recent["close"].values
    volumes = recent["volume"].values

    # Price direction: count up-candles vs down-candles
    up_candles = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i - 1])
    down_candles = lookback - 1 - up_candles
    price_bias = up_candles / (lookback - 1)  # 0=all down, 1=all up

    # Volume trend: is volume increasing?
    vol_first_half = volumes[:lookback // 2].mean() if len(volumes) >= 2 else 0
    vol_second_half = volumes[lookback // 2:].mean() if len(volumes) >= 2 else 0
    vol_increasing = vol_second_half > vol_first_half * 1.1 if vol_first_half > 0 else False

    # Momentum score: 0-1
    momentum_score = price_bias * 0.7 + (0.3 if vol_increasing else 0.0)
    momentum_score = max(0.0, min(1.0, momentum_score))

    if momentum_score >= 0.65:
        trend = "UP"
    elif momentum_score <= 0.35:
        trend = "DOWN"
    else:
        trend = "FLAT"

    return {
        "score": round(momentum_score, 3),
        "trend": trend,
        "up_candles": up_candles,
        "down_candles": down_candles,
        "volume_increasing": vol_increasing,
    }


def compute_bollinger_bands(
    df: pd.DataFrame, period: int = 20, num_std: float = 2.0, col: str = "close"
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Compute Bollinger Bands.

    Returns:
        (upper_band, middle_band, lower_band)
    """
    middle = df[col].rolling(window=period).mean()
    std = df[col].rolling(window=period).std()
    upper = middle + (num_std * std)
    lower = middle - (num_std * std)
    return upper, middle, lower


def compute_stochastic(
    df: pd.DataFrame, k_period: int = 14, d_period: int = 3
) -> tuple[pd.Series, pd.Series]:
    """
    Compute Stochastic Oscillator (%K and %D).

    Returns:
        (%K, %D) — both 0-100 range
    """
    low_min = df["low"].rolling(window=k_period).min()
    high_max = df["high"].rolling(window=k_period).max()
    denom = (high_max - low_min).replace(0, np.nan)
    k = ((df["close"] - low_min) / denom) * 100
    d = k.rolling(window=d_period).mean()
    return k.fillna(50), d.fillna(50)


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute ATR (Average True Range).
    Useful for position sizing and stop-loss calculation.
    """
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.ewm(alpha=1 / period, min_periods=period).mean()
    return atr


def detect_volume_surge(
    df: pd.DataFrame, lookback: int = 20, threshold: float = 2.0
) -> pd.Series:
    """
    Detect volume surges — volume > threshold * average volume.

    Returns:
        Boolean Series — True where volume is surging.
    """
    avg_vol = df["volume"].rolling(window=lookback).mean()
    return df["volume"] > (threshold * avg_vol)


# ══════════════════════════════════════════════════════════════════════════════
# COMPOSITE SIGNAL SCORE
# ══════════════════════════════════════════════════════════════════════════════


def generate_signal_score(
    df: pd.DataFrame,
    intraday_df: pd.DataFrame = None,
) -> Optional[dict]:
    """
    Compute a composite signal score from all indicators (Fix #8: dual-timeframe).

    Args:
        df: Daily OHLCV DataFrame (≥50 candles) — for RSI, MACD, EMA, Bollinger, ATR
        intraday_df: Optional 5-min intraday DataFrame (today) — for VWAP, momentum

    Weights (rebalanced):
        Momentum (RSI+Stochastic merged): 15%
        MACD:                             20%
        EMA Trend:                        15%
        VWAP (intraday if available):     15%
        Bollinger Bands:                  10%
        Volume:                           15%
        Intraday Momentum (if available): 10%

    Returns:
        {
            'score': 0.72,  # 0.0 (strong sell) to 1.0 (strong buy)
            'trend': 'BULLISH' | 'BEARISH' | 'NEUTRAL',
            'signals': {...},
            'recommendation': 'BUY' | 'SELL' | 'HOLD',
            'component_scores': {...},
            'dual_timeframe': True/False
        }
    """
    if df is None or len(df) < 50:
        logger.warning("Not enough data for signal generation (need ≥50 candles)")
        return None

    has_intraday = intraday_df is not None and len(intraday_df) >= 6

    # ── Compute daily indicators ──
    rsi = compute_rsi(df)
    ema_20 = compute_ema(df, period=20)
    ema_50 = compute_ema(df, period=50)
    macd_line, signal_line, macd_hist = compute_macd(df)
    bb_upper, bb_middle, bb_lower = compute_bollinger_bands(df)
    stoch_k, stoch_d = compute_stochastic(df)
    atr = compute_atr(df)
    vol_surge = detect_volume_surge(df)

    # ── Compute intraday indicators (if available) ──
    if has_intraday:
        intraday_vwap = compute_vwap_intraday(intraday_df)
        intraday_momentum = compute_intraday_momentum(intraday_df)
        current_vwap = float(intraday_vwap.iloc[-1]) if len(intraday_vwap) > 0 else None
        intraday_close = float(intraday_df["close"].iloc[-1])
    else:
        # Fallback: use 200-SMA as VWAP substitute on daily data
        sma_200 = compute_sma(df, period=min(200, len(df) - 1)) if len(df) > 20 else df["close"]
        current_vwap = float(sma_200.iloc[-1]) if sma_200 is not None else None
        intraday_momentum = {"score": 0.5, "trend": "NO_DATA"}
        intraday_close = None

    # Get the latest daily values
    latest = len(df) - 1
    close = df["close"].iloc[latest]

    current_rsi = rsi.iloc[latest]
    current_macd = macd_line.iloc[latest]
    current_signal = signal_line.iloc[latest]
    current_macd_hist = macd_hist.iloc[latest]
    current_ema_20 = ema_20.iloc[latest]
    current_ema_50 = ema_50.iloc[latest]
    current_bb_upper = bb_upper.iloc[latest]
    current_bb_lower = bb_lower.iloc[latest]
    current_stoch_k = stoch_k.iloc[latest]
    current_atr = atr.iloc[latest]
    current_vol_surge = bool(vol_surge.iloc[latest])

    # Use intraday close for VWAP comparison if available
    compare_price = intraday_close if intraday_close else close

    # ── Individual signal scores ──
    scores = []

    # Momentum Score — RSI + Stochastic MERGED (weight: 15%) — Fix #8
    if current_rsi < 30:
        rsi_score = 0.9  # Oversold
        rsi_signal = "OVERSOLD"
    elif current_rsi > 70:
        rsi_score = 0.1  # Overbought
        rsi_signal = "OVERBOUGHT"
    else:
        rsi_score = 0.5 + (50 - current_rsi) * 0.01
        rsi_signal = "NEUTRAL"

    if current_stoch_k < 20:
        stoch_score = 0.85
    elif current_stoch_k > 80:
        stoch_score = 0.15
    else:
        stoch_score = 0.5

    # Merged: 60% RSI + 40% Stochastic (they're correlated, so blend them)
    momentum_score = rsi_score * 0.6 + stoch_score * 0.4
    scores.append(("momentum", momentum_score, 0.15))

    # MACD Score (weight: 20%)
    macd_bullish = current_macd > current_signal
    macd_score = 0.7 if macd_bullish else 0.3
    if current_macd_hist > 0 and macd_hist.iloc[latest - 1] < 0:
        macd_score = 0.9  # Fresh bullish crossover
    elif current_macd_hist < 0 and macd_hist.iloc[latest - 1] > 0:
        macd_score = 0.1  # Fresh bearish crossover
    scores.append(("macd", macd_score, 0.20))

    # EMA Trend Score (weight: 15%)
    above_ema_20 = close > current_ema_20
    above_ema_50 = close > current_ema_50
    ema_score = 0.5
    if above_ema_20 and above_ema_50:
        ema_score = 0.8
    elif above_ema_20:
        ema_score = 0.6
    elif not above_ema_20 and not above_ema_50:
        ema_score = 0.2
    scores.append(("ema", ema_score, 0.15))

    # VWAP Score (weight: 15%) — uses intraday VWAP when available (Fix #8)
    if current_vwap and current_vwap > 0:
        above_vwap = compare_price > current_vwap
        vwap_distance = abs(compare_price - current_vwap) / current_vwap * 100
        # Closer to VWAP = more neutral, farther = stronger signal
        if above_vwap:
            vwap_score = min(0.9, 0.6 + vwap_distance * 0.05)
        else:
            vwap_score = max(0.1, 0.4 - vwap_distance * 0.05)
    else:
        above_vwap = False
        vwap_score = 0.5
    scores.append(("vwap", vwap_score, 0.15))

    # Bollinger Band Position (weight: 10%)
    bb_range = current_bb_upper - current_bb_lower
    if bb_range > 0:
        bb_position = (close - current_bb_lower) / bb_range
        bb_position = max(0, min(1, bb_position))
    else:
        bb_position = 0.5
    bb_score = 0.5 + (0.5 - bb_position) * 0.6
    bb_score = max(0.1, min(0.9, bb_score))
    scores.append(("bollinger", bb_score, 0.10))

    # Volume Score (weight: 15%)
    vol_score = 0.7 if current_vol_surge else 0.5
    scores.append(("volume", vol_score, 0.15))

    # Intraday Momentum Score (weight: 10%) — NEW (Fix #8)
    intra_score = intraday_momentum.get("score", 0.5)
    scores.append(("intraday_momentum", intra_score, 0.10))

    # ── Weighted composite score ──
    total_score = sum(s * w for _, s, w in scores)
    total_score = max(0.0, min(1.0, total_score))

    # ── Derive trend and recommendation ──
    if total_score >= 0.65:
        trend = "BULLISH"
        recommendation = "BUY"
    elif total_score <= 0.35:
        trend = "BEARISH"
        recommendation = "SELL"
    else:
        trend = "NEUTRAL"
        recommendation = "HOLD"

    return {
        "score": round(total_score, 3),
        "trend": trend,
        "recommendation": recommendation,
        "dual_timeframe": has_intraday,
        "signals": {
            "rsi": round(float(current_rsi), 2),
            "rsi_signal": rsi_signal,
            "macd_bullish": bool(macd_bullish),
            "macd_histogram": round(float(current_macd_hist), 4),
            "above_ema_20": bool(above_ema_20),
            "above_ema_50": bool(above_ema_50),
            "ema_20": round(float(current_ema_20), 2),
            "ema_50": round(float(current_ema_50), 2),
            "above_vwap": bool(above_vwap),
            "vwap": round(float(current_vwap), 2) if current_vwap else None,
            "vwap_source": "intraday_5min" if has_intraday else "sma_200_fallback",
            "bollinger_position": round(float(bb_position), 3),
            "stochastic_k": round(float(current_stoch_k), 2),
            "volume_surge": current_vol_surge,
            "atr": round(float(current_atr), 2),
            "close": round(float(close), 2),
            "intraday_momentum": intraday_momentum,
        },
        "component_scores": {name: round(score, 3) for name, score, _ in scores},
    }


def enrich_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all indicator columns to a candle DataFrame.
    Useful for charting / backtesting.
    """
    if df is None or len(df) < 2:
        return df

    df = df.copy()
    df["rsi"] = compute_rsi(df)
    df["ema_20"] = compute_ema(df, period=20)
    df["ema_50"] = compute_ema(df, period=50)
    df["sma_20"] = compute_sma(df, period=20)

    macd_line, signal_line, histogram = compute_macd(df)
    df["macd"] = macd_line
    df["macd_signal"] = signal_line
    df["macd_histogram"] = histogram

    df["vwap"] = compute_vwap(df)

    bb_upper, bb_middle, bb_lower = compute_bollinger_bands(df)
    df["bb_upper"] = bb_upper
    df["bb_middle"] = bb_middle
    df["bb_lower"] = bb_lower

    stoch_k, stoch_d = compute_stochastic(df)
    df["stoch_k"] = stoch_k
    df["stoch_d"] = stoch_d

    df["atr"] = compute_atr(df)
    df["volume_surge"] = detect_volume_surge(df)

    return df
