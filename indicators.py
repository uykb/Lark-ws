import pandas as pd
import pandas_ta as ta
from config import *

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
    
    # 3. Calculate additional technical indicators (RSI, EMA)
    df.ta.rsi(length=14, append=True)
    df.ta.ema(length=12, append=True)
    df.ta.ema(length=26, append=True)
    
    latest_tech_indicators = df.tail(1)
    tech_indicators = {
        "rsi_14": f"{latest_tech_indicators['RSI_14'].iloc[0]:.2f}",
        "ema_12": f"{latest_tech_indicators['EMA_12'].iloc[0]:.2f}",
        "ema_26": f"{latest_tech_indicators['EMA_26'].iloc[0]:.2f}",
    }

    return {
        "primary_signal": primary_signal,
        "market_context": {
            "recent_klines": klines_data,
            "key_indicators": context_indicators,
            "technical_indicators": tech_indicators
        }
    }

class CatchTheRiseSignal:
    """
    Rule 1: Catch the Rise - 15min
    Triggers when Open Interest increases by >5% and price increases by >2% in a single 15-minute candle.
    """
    def check(self, df: pd.DataFrame):
        if len(df) < 2:
            return None
            
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Calculate percentage change
        price_change = (latest['close'] / previous['close']) - 1
        oi_change = (latest['oi'] / previous['oi']) - 1
        
        if oi_change > RISE_OI_CHANGE_THRESHOLD and price_change > RISE_PRICE_CHANGE_THRESHOLD:
            signal = {
                "indicator": "Price/OI Spike",
                "signal_type": "Catch the Rise",
                "price_change": f"{price_change:+.2%}",
                "oi_change": f"{oi_change:+.2%}",
                "current_price": f"{latest['close']:.2f}",
                "current_oi": f"${latest['oi']:,.0f}"
            }
            return _create_market_snapshot(df, signal)
        return None

class FVGTrendSignal:
    """
    Rule 2: Catch the Trend - 15min FVG Reversal
    Identifies a Fair Value Gap (FVG), waits for it to be rebalanced, and then triggers on a trend reversal candle.
    """
    def _find_fvg(self, df: pd.DataFrame):
        """Finds the most recent FVG in the last 20 candles."""
        for i in range(len(df) - 3, max(0, len(df) - 20), -1):
            candle1 = df.iloc[i]
            candle3 = df.iloc[i+2]
            
            # Bullish FVG: Candle 1's high is lower than Candle 3's low
            if candle1['high'] < candle3['low']:
                return 'bullish', candle1['high'], candle3['low'], i + 2
            # Bearish FVG: Candle 1's low is higher than Candle 3's high
            if candle1['low'] > candle3['high']:
                return 'bearish', candle3['high'], candle1['low'], i + 2
        return None, None, None, None

    def check(self, df: pd.DataFrame):
        if len(df) < 20: # Need enough data to find FVGs and check for reversals
            return None

        fvg_type, fvg_top, fvg_bottom, fvg_candle_index = self._find_fvg(df)
        
        if not fvg_type:
            return None

        # Check for rebalancing and reversal in the candles *after* the FVG was formed
        for i in range(fvg_candle_index + 1, len(df) -1):
            current_candle = df.iloc[i]
            next_candle = df.iloc[i+1]

            if fvg_type == 'bullish':
                # Rebalancing: price dips into the FVG zone
                if current_candle['low'] < fvg_bottom:
                    # Reversal: the next candle is a strong bullish candle
                    if next_candle['close'] > next_candle['open'] and (next_candle['close'] - next_candle['open']) > (current_candle['open'] - current_candle['close']):
                        signal = {
                            "indicator": "FVG Trend",
                            "signal_type": "Bullish Reversal after FVG Fill",
                            "fvg_range": f"${fvg_top:.2f} - ${fvg_bottom:.2f}",
                            "reversal_candle_close": f"${next_candle['close']:.2f}"
                        }
                        return _create_market_snapshot(df, signal)

            elif fvg_type == 'bearish':
                # Rebalancing: price rallies into the FVG zone
                if current_candle['high'] > fvg_top:
                    # Reversal: the next candle is a strong bearish candle
                    if next_candle['close'] < next_candle['open'] and (next_candle['open'] - next_candle['close']) > (current_candle['close'] - current_candle['open']):
                        signal = {
                            "indicator": "FVG Trend",
                            "signal_type": "Bearish Reversal after FVG Fill",
                            "fvg_range": f"${fvg_top:.2f} - ${fvg_bottom:.2f}",
                            "reversal_candle_close": f"${next_candle['close']:.2f}"
                        }
                        return _create_market_snapshot(df, signal)
        
        return None
