import pandas as pd
import pandas_ta as ta
from config import *
from abc import ABC, abstractmethod

def _create_market_snapshot(df: pd.DataFrame, primary_signal: dict):
    """
    Creates a rich data package containing the primary signal and a market context snapshot.
    """
    # 1. Extract the last 16 candlesticks
    recent_klines = df.tail(16).copy()
    klines_data = recent_klines[['open', 'high', 'low', 'close', 'volume']].to_dict(orient='records')

    # 2. Extract the latest values of key indicators
    latest_indicators = df.tail(1).copy()
    context_indicators = {
        "oi": f"${latest_indicators['oi'].iloc[0]:,.0f}",
        "price": f"{latest_indicators['close'].iloc[0]:.2f}",
        "volume": f"{latest_indicators['volume'].iloc[0]:,.0f}",
        "cvd": f"{latest_indicators['cvd'].iloc[0]:,.0f}",
        "long_short_ratio": f"{latest_indicators['ls_ratio'].iloc[0]:.3f}"
    }
    
    # 3. Calculate additional technical indicators (RSI, EMA, ATR)
    # Optimize: Check if columns exist to avoid redundant calculation
    if 'RSI_14' not in df.columns:
        df.ta.rsi(length=14, append=True)
    if 'EMA_12' not in df.columns:
        df.ta.ema(length=12, append=True)
    if 'EMA_26' not in df.columns:
        df.ta.ema(length=26, append=True)
    if 'ATRr_14' not in df.columns:
        df.ta.atr(length=14, append=True)
    
    latest_tech_indicators = df.tail(1)
    
    # Safely get ATR, handling potential NaN for short data
    atr_val = latest_tech_indicators['ATRr_14'].iloc[0] if 'ATRr_14' in latest_tech_indicators else 0.0
    
    tech_indicators = {
        "rsi_14": f"{latest_tech_indicators['RSI_14'].iloc[0]:.2f}",
        "ema_12": f"{latest_tech_indicators['EMA_12'].iloc[0]:.2f}",
        "ema_26": f"{latest_tech_indicators['EMA_26'].iloc[0]:.2f}",
        "atr_14": f"{atr_val:.4f}"
    }

    return {
        "primary_signal": primary_signal,
        "market_context": {
            "recent_klines": klines_data,
            "key_indicators": context_indicators,
            "technical_indicators": tech_indicators
        }
    }

class BaseSignal(ABC):
    """
    Abstract base class for all signal detectors.
    """
    @property
    @abstractmethod
    def name(self):
        """
        Returns the name of the signal.
        """
        pass

    @abstractmethod
    def check(self, df: pd.DataFrame, symbol: str = None):
        """
        Checks for the signal in the given DataFrame.
        Returns a signal data dictionary if a signal is found, otherwise None.
        """
        pass

class FairValueGapSignal(BaseSignal):
    """
    Detects a Fair Value Gap (FVG) and triggers a signal when the price rebalances
    within the gap and shows a confirmation reversal candle.
    """
    @property
    def name(self):
        return "Fair Value Gap Rebalance"

    def check(self, df: pd.DataFrame, symbol: str = None):
        if len(df) < 5:  # Need at least 5 candles to detect FVG and subsequent moves
            return None

        # FVG Detection
        for i in range(len(df) - 4, 0, -1): # Iterate backwards to find the latest FVG
            candle_minus_2 = df.iloc[i-1]
            candle_minus_1 = df.iloc[i]
            candle_zero = df.iloc[i+1]

            # Bullish FVG: High of candle[-2] < Low of candle[0]
            is_bullish_fvg = candle_minus_2['high'] < candle_zero['low']
            # Bearish FVG: Low of candle[-2] > High of candle[0]
            is_bearish_fvg = candle_minus_2['low'] > candle_zero['high']

            if is_bullish_fvg or is_bearish_fvg:
                fvg_top = candle_zero['low'] if is_bullish_fvg else candle_minus_2['low']
                fvg_bottom = candle_minus_2['high'] if is_bullish_fvg else candle_zero['high']
                
                # Check for rebalance and confirmation in the candles following the FVG
                for j in range(i + 2, len(df)):
                    current_candle = df.iloc[j]
                    
                    # Price entered the FVG zone
                    price_in_fvg = fvg_bottom <= current_candle['low'] <= fvg_top or \
                                   fvg_bottom <= current_candle['high'] <= fvg_top

                    if price_in_fvg:
                        # Confirmation: Bullish reversal (e.g., Hammer) after rebalancing in a bullish FVG
                        if is_bullish_fvg and (current_candle['close'] > current_candle['open']):
                            body_size = abs(current_candle['close'] - current_candle['open'])
                            lower_wick = current_candle['open'] - current_candle['low']
                            if lower_wick > body_size * 2: # Simple Hammer check
                                signal = {
                                    "indicator": self.name,
                                    "signal_type": "Bullish Reversal Confirmation",
                                    "fvg_top": f"{fvg_top:.2f}",
                                    "fvg_bottom": f"{fvg_bottom:.2f}",
                                    "confirmation_candle": "Hammer",
                                    "current_price": f"{current_candle['close']:.2f}"
                                }
                                return _create_market_snapshot(df, signal)

                        # Confirmation: Bearish reversal (e.g., Shooting Star) after rebalancing in a bearish FVG
                        elif is_bearish_fvg and (current_candle['close'] < current_candle['open']):
                            body_size = abs(current_candle['open'] - current_candle['close'])
                            upper_wick = current_candle['high'] - current_candle['open']
                            if upper_wick > body_size * 2: # Simple Shooting Star check
                                signal = {
                                    "indicator": self.name,
                                    "signal_type": "Bearish Reversal Confirmation",
                                    "fvg_top": f"{fvg_top:.2f}",
                                    "fvg_bottom": f"{fvg_bottom:.2f}",
                                    "confirmation_candle": "Shooting Star",
                                    "current_price": f"{current_candle['close']:.2f}"
                                }
                                return _create_market_snapshot(df, signal)
                break # Found the latest FVG, no need to check older ones
        return None
