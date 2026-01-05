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

    # --- Market Structure Context ---
    # Calculate simple structure points (High/Low of last 50 candles) to help AI identify sweeps
    recent_window = 50
    recent_high = df['high'].tail(recent_window).max() if len(df) >= recent_window else df['high'].max()
    recent_low = df['low'].tail(recent_window).min() if len(df) >= recent_window else df['low'].min()
    
    current_close = df['close'].iloc[-1]
    
    structure = {
        "recent_high_50": f"{recent_high:.2f}",
        "recent_low_50": f"{recent_low:.2f}",
        "dist_from_high": f"{(recent_high - current_close)/recent_high*100:.2f}%",
        "dist_from_low": f"{(current_close - recent_low)/recent_low*100:.2f}%"
    }

    return {
        "primary_signal": primary_signal,
        "market_context": {
            "recent_klines": klines_data,
            "key_indicators": context_indicators,
            "technical_indicators": tech_indicators,
            "market_structure": structure
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

class RSIDivergenceSignal(BaseSignal):
    """
    Detects RSI Divergences (Bullish and Bearish).
    """
    @property
    def name(self):
        return "RSI Divergence"

    def check(self, df: pd.DataFrame, symbol: str = None):
        if len(df) < RSI_LENGTH + RSI_DIVERGENCE_WINDOW + 5:
            return None

        # Ensure RSI is calculated
        rsi_col = f'RSI_{RSI_LENGTH}'
        if rsi_col not in df.columns:
            df.ta.rsi(length=RSI_LENGTH, append=True)
        
        # We need to find local extrema (pivots) for Price and RSI
        
        curr_idx = len(df) - 2 # The last closed candle
        if curr_idx < 5: return None
        
        # Candidate Pivot at i (using -2 as the "current" confirmed pivot point)
        i = len(df) - 2
        
        # 1. Bullish Divergence Check (Lower Price Lows, Higher RSI Lows)
        # Check if candle[i] is a local Low
        is_price_low = df.iloc[i]['low'] < df.iloc[i-1]['low'] and df.iloc[i]['low'] < df.iloc[i+1]['low']
        
        if is_price_low:
            curr_low_price = df.iloc[i]['low']
            curr_low_rsi = df.iloc[i][rsi_col]
            
            # Find a previous local low within the window
            for j in range(i - 2, i - RSI_DIVERGENCE_WINDOW, -1):
                if j < 2: break
                
                # Check if j is a local low
                is_prev_low = df.iloc[j]['low'] < df.iloc[j-1]['low'] and df.iloc[j]['low'] < df.iloc[j+1]['low']
                
                if is_prev_low:
                    prev_low_price = df.iloc[j]['low']
                    prev_low_rsi = df.iloc[j][rsi_col]
                    
                    # Bullish Divergence Condition
                    if curr_low_price < prev_low_price and curr_low_rsi > prev_low_rsi:
                        signal = {
                            "indicator": self.name,
                            "signal_type": "Bullish Divergence",
                            "current_low": f"{curr_low_price:.2f}",
                            "prev_low": f"{prev_low_price:.2f}",
                            "current_rsi": f"{curr_low_rsi:.2f}",
                            "prev_rsi": f"{prev_low_rsi:.2f}",
                            "current_price": f"{df.iloc[-1]['close']:.2f}"
                        }
                        return _create_market_snapshot(df, signal)
                    break # Only compare with the most recent previous pivot

        # 2. Bearish Divergence Check (Higher Price Highs, Lower RSI Highs)
        # Check if candle[i] is a local High
        is_price_high = df.iloc[i]['high'] > df.iloc[i-1]['high'] and df.iloc[i]['high'] > df.iloc[i+1]['high']
        
        if is_price_high:
            curr_high_price = df.iloc[i]['high']
            curr_high_rsi = df.iloc[i][rsi_col]
            
            # Find a previous local high within the window
            for j in range(i - 2, i - RSI_DIVERGENCE_WINDOW, -1):
                if j < 2: break
                
                # Check if j is a local high
                if df.iloc[j]['high'] > df.iloc[j-1]['high'] and df.iloc[j]['high'] > df.iloc[j+1]['high']:
                    prev_high_price = df.iloc[j]['high']
                    prev_high_rsi = df.iloc[j][rsi_col]
                    
                    # Bearish Divergence Condition
                    if curr_high_price > prev_high_price and curr_high_rsi < prev_high_rsi:
                        signal = {
                            "indicator": self.name,
                            "signal_type": "Bearish Divergence",
                            "current_high": f"{curr_high_price:.2f}",
                            "prev_high": f"{prev_high_price:.2f}",
                            "current_rsi": f"{curr_high_rsi:.2f}",
                            "prev_rsi": f"{prev_high_rsi:.2f}",
                            "current_price": f"{df.iloc[-1]['close']:.2f}"
                        }
                        return _create_market_snapshot(df, signal)
                    break

        return None

class BollingerBandsBreakoutSignal(BaseSignal):
    """
    Detects breakouts from Bollinger Bands.
    """
    @property
    def name(self):
        return "Bollinger Bands Breakout"

    def check(self, df: pd.DataFrame, symbol: str = None):
        if len(df) < BB_LENGTH + 5:
            return None

        # Calculate Bollinger Bands
        # Returns a dataframe with columns like BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
        bb_df = df.ta.bbands(length=BB_LENGTH, std=BB_STD)
        
        if bb_df is None: return None
        
        # Append to main df for easier access if needed, or just use the result
        # Names depend on the lib version, but usually:
        lower_col = f"BBL_{BB_LENGTH}_{BB_STD}"
        upper_col = f"BBU_{BB_LENGTH}_{BB_STD}"
        
        if lower_col not in bb_df.columns or upper_col not in bb_df.columns:
            # Fallback to standard naming if specific float formatting differs
            cols = bb_df.columns
            lower_col = [c for c in cols if c.startswith('BBL')][0]
            upper_col = [c for c in cols if c.startswith('BBU')][0]

        current_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        current_lower = bb_df.iloc[-1][lower_col]
        current_upper = bb_df.iloc[-1][upper_col]
        prev_lower = bb_df.iloc[-2][lower_col]
        prev_upper = bb_df.iloc[-2][upper_col]
        
        # Bullish Breakout: Close crosses above Upper Band
        # Checking if previous close was below or near, and current is above.
        # Or just strictly current close > upper band? 
        # A breakout usually implies the candle closes outside the band.
        if prev_candle['close'] <= prev_upper and current_candle['close'] > current_upper:
             signal = {
                "indicator": self.name,
                "signal_type": "Bullish Breakout",
                "upper_band": f"{current_upper:.2f}",
                "close_price": f"{current_candle['close']:.2f}",
                "current_price": f"{current_candle['close']:.2f}"
            }
             return _create_market_snapshot(df, signal)

        # Bearish Breakout: Close crosses below Lower Band
        if prev_candle['close'] >= prev_lower and current_candle['close'] < current_lower:
             signal = {
                "indicator": self.name,
                "signal_type": "Bearish Breakout",
                "lower_band": f"{current_lower:.2f}",
                "close_price": f"{current_candle['close']:.2f}",
                "current_price": f"{current_candle['close']:.2f}"
            }
             return _create_market_snapshot(df, signal)
             
        return None

class VolumeSpikeSignal(BaseSignal):
    """
    Detects abnormal volume spikes.
    """
    @property
    def name(self):
        return "Volume Spike"

    def check(self, df: pd.DataFrame, symbol: str = None):
        if len(df) < VOLUME_MA_LENGTH + 5:
            return None

        # Calculate Volume SMA
        # df.ta.sma returns a Series
        vol_sma = df.ta.sma(close=df['volume'], length=VOLUME_MA_LENGTH)
        
        if vol_sma is None: return None
        
        current_vol = df.iloc[-1]['volume']
        current_sma = vol_sma.iloc[-1]
        
        # Check for spike
        if current_sma > 0 and current_vol > current_sma * VOLUME_SPIKE_THRESHOLD:
            # Determine direction based on price candle
            candle_color = "Green" if df.iloc[-1]['close'] > df.iloc[-1]['open'] else "Red"
            direction = "Bullish" if candle_color == "Green" else "Bearish"
            
            signal = {
                "indicator": self.name,
                "signal_type": f"{direction} Volume Spike",
                "volume": f"{current_vol:,.0f}",
                "average_volume": f"{current_sma:,.0f}",
                "ratio": f"{current_vol/current_sma:.1f}x",
                "current_price": f"{df.iloc[-1]['close']:.2f}"
            }
            return _create_market_snapshot(df, signal)
            
        return None

class OrderBlockSignal(BaseSignal):
    """
    Detects Order Blocks (OB) and alerts on retests.
    OB is defined as the candle preceding a significant displacement (momentum move).
    """
    @property
    def name(self):
        return "Order Block"

    def check(self, df: pd.DataFrame, symbol: str = None):
        if len(df) < OB_LOOKBACK + 5: return None
        
        # Ensure ATR is there for displacement check
        if 'ATRr_14' not in df.columns:
            df.ta.atr(length=14, append=True)
            
        current_candle = df.iloc[-1]
        
        # Iterate backwards to find the *first* (most recent) OB that matches the current price
        # We start from -2 (completed candle) back to OB_LOOKBACK
        for i in range(len(df) - 2, len(df) - OB_LOOKBACK, -1):
            candle = df.iloc[i]     # The displacement candle candidate
            prev_candle = df.iloc[i-1] # The OB candidate
            
            # Safe ATR access
            atr = df.iloc[i]['ATRr_14'] if 'ATRr_14' in df.columns and not pd.isna(df.iloc[i]['ATRr_14']) else 0
            if atr == 0: continue
            
            body_size = abs(candle['close'] - candle['open'])
            
            # Check for Displacement: Body significantly larger than ATR
            if body_size > atr * OB_ATR_MULTIPLIER:
                
                # --- Potential Bearish OB ---
                # Pattern: Green Candle (OB) -> Large Red Candle (Displacement)
                # But strict color isn't always required, just the move. 
                # Standard ICT: The last up candle before the down move.
                
                if candle['close'] < candle['open']: # Downward displacement
                    ob_top = prev_candle['high']
                    ob_bottom = prev_candle['low']
                    
                    # Check if OB Candle was actually "Up" (Green) or at least not a massive red one?
                    # ICT: "Last up close candle". Let's stick to standard definition: Green candle.
                    if prev_candle['close'] > prev_candle['open']:
                        
                        # Check if CURRENT price is retesting this zone
                        # Overlap logic
                        is_retesting = (current_candle['high'] >= ob_bottom) and (current_candle['low'] <= ob_top)
                        
                        if is_retesting:
                             signal = {
                                "indicator": self.name,
                                "signal_type": "Bearish OB Retest",
                                "ob_top": f"{ob_top:.2f}",
                                "ob_bottom": f"{ob_bottom:.2f}",
                                "displacement_candle_date": str(candle.name), # Index is usually datetime
                                "current_price": f"{current_candle['close']:.2f}"
                            }
                             return _create_market_snapshot(df, signal)

                # --- Potential Bullish OB ---
                # Pattern: Red Candle (OB) -> Large Green Candle (Displacement)
                elif candle['close'] > candle['open']: # Upward displacement
                    ob_top = prev_candle['high']
                    ob_bottom = prev_candle['low']
                    
                    # ICT: "Last down close candle". Red candle.
                    if prev_candle['close'] < prev_candle['open']:
                        
                        is_retesting = (current_candle['high'] >= ob_bottom) and (current_candle['low'] <= ob_top)
                        
                        if is_retesting:
                             signal = {
                                "indicator": self.name,
                                "signal_type": "Bullish OB Retest",
                                "ob_top": f"{ob_top:.2f}",
                                "ob_bottom": f"{ob_bottom:.2f}",
                                "displacement_candle_date": str(candle.name),
                                "current_price": f"{current_candle['close']:.2f}"
                            }
                             return _create_market_snapshot(df, signal)
                           
        return None
