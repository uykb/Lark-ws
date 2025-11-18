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

class MomentumSpikeSignal:
    """
    Detects a momentum spike based on significant changes in both price and open interest.
    Triggers when |OI Change| > 5% and |Price Change| > 2% in a single 15-minute candle.
    """
    def check(self, df: pd.DataFrame):
        if len(df) < 2:
            return None
            
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Calculate percentage change
        price_change = (latest['close'] / previous['close']) - 1
        oi_change = (latest['oi'] / previous['oi']) - 1
        
        if abs(oi_change) > RISE_OI_CHANGE_THRESHOLD and abs(price_change) > RISE_PRICE_CHANGE_THRESHOLD:
            
            direction = "Bullish" if price_change > 0 else "Bearish"
            
            signal = {
                "indicator": "Price/OI Momentum Spike",
                "signal_type": f"{direction} Spike",
                "price_change": f"{price_change:+.2%}",
                "oi_change": f"{oi_change:+.2%}",
                "current_price": f"{latest['close']:.2f}",
                "current_oi": f"${latest['oi']:,.0f}"
            }
            return _create_market_snapshot(df, signal)
        return None
