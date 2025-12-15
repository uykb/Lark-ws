import time
import json
import os
from config import (
    FVG_COOLDOWN_PERIOD_MINUTES, 
    FVG_PRICE_TOLERANCE_PERCENT,
    MAX_COOLDOWN_PERIOD_MINUTES,
    COOLDOWN_BACKOFF_FACTOR
)
from logger import log

class SignalStateManager:
    def __init__(self, state_file='signal_state.json'):
        """
        Initializes the signal state manager with persistence.
        """
        self.state_file = state_file
        # Storage structure: { "unique_key": {"timestamp": float, "signal_data": dict, "trigger_count": int} }
        self.last_triggered_signals = self._load_state()

    def _load_state(self):
        """Loads the last triggered signals from the state file."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                log.warning(f"Could not load signal state from {self.state_file}. Starting with a fresh state. Error: {e}")
                return {}
        return {}

    def _save_state(self):
        """Saves the current signal state to the state file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.last_triggered_signals, f, indent=4)
        except IOError as e:
            log.error(f"Could not save signal state to {self.state_file}. Error: {e}")

    def _get_unique_key(self, symbol, signal):
        """
        Generates a unique key based on the symbol, indicator name, and signal type.
        """
        indicator = signal['primary_signal'].get('indicator', 'UnknownIndicator')
        signal_type = signal['primary_signal'].get('signal_type', 'UnknownType')
        return f"{symbol}-{indicator}-{signal_type}"

    def should_send_alert(self, symbol, signal):
        """
        Determines if a new alert should be sent based on dynamic cooldown and signal significance.
        Returns a tuple (should_send: bool, previous_signal: dict | None)
        """
        unique_key = self._get_unique_key(symbol, signal)
        current_time = time.time()
        
        last_signal_info = self.last_triggered_signals.get(unique_key)

        # 1. If the signal has never been sent before, it should be sent.
        if not last_signal_info:
            log.info(f"New signal type {unique_key}, allowing send.")
            self._update_state(unique_key, signal, trigger_count=1)
            return True, None

        last_timestamp = last_signal_info['timestamp']
        last_signal_data = last_signal_info['signal_data']['primary_signal']
        current_signal_data = signal['primary_signal']
        trigger_count = last_signal_info.get('trigger_count', 1)
        
        # 2. Check logic for FVG signals
        if current_signal_data.get('indicator') == "Fair Value Gap Rebalance":
            # Check for significant changes (Price Tolerance)
            is_similar = False
            try:
                last_fvg_top = float(last_signal_data.get('fvg_top', '0'))
                last_fvg_bottom = float(last_signal_data.get('fvg_bottom', '0'))
                current_fvg_top = float(current_signal_data.get('fvg_top', '0'))
                current_fvg_bottom = float(current_signal_data.get('fvg_bottom', '0'))
                
                last_conf_candle = last_signal_data.get('confirmation_candle')
                current_conf_candle = current_signal_data.get('confirmation_candle')

                # Calculate midpoints
                last_fvg_mid = (last_fvg_top + last_fvg_bottom) / 2
                current_fvg_mid = (current_fvg_top + current_fvg_bottom) / 2

                # Calculate percentage difference
                if last_fvg_mid != 0:
                    fvg_mid_diff_percent = abs((current_fvg_mid - last_fvg_mid) / last_fvg_mid) * 100
                else:
                    fvg_mid_diff_percent = 0 if current_fvg_mid == 0 else float('inf')
                
                if fvg_mid_diff_percent < FVG_PRICE_TOLERANCE_PERCENT and \
                   last_conf_candle == current_conf_candle:
                    is_similar = True
            except (ValueError, TypeError) as e:
                log.warning(f"Error comparing FVG data for {unique_key}: {e}")
                is_similar = False # Treat as different on error
            
            if is_similar:
                # Calculate Dynamic Cooldown: Base * (Factor ^ (Count - 1))
                # Count 1: 15 * 2^0 = 15 min
                # Count 2: 15 * 2^1 = 30 min
                # Count 3: 15 * 2^2 = 60 min ...
                
                # Special user request handling logic interpretation:
                # If user wants 15 -> 60 (4x jump) initially, we could adjust.
                # But standard backoff (x2) is implemented here for consistency: 15 -> 30 -> 60 -> 120.
                dynamic_cooldown = FVG_COOLDOWN_PERIOD_MINUTES * (COOLDOWN_BACKOFF_FACTOR ** (trigger_count - 1))
                
                # Cap at MAX limit
                dynamic_cooldown = min(dynamic_cooldown, MAX_COOLDOWN_PERIOD_MINUTES)
                
                time_since_last_min = (current_time - last_timestamp) / 60
                
                if time_since_last_min < dynamic_cooldown:
                    log.info(f"FVG signal {unique_key} suppressed. Count: {trigger_count}. Cooldown: {dynamic_cooldown:.1f}m (Elapsed: {time_since_last_min:.1f}m).")
                    return False, last_signal_data
                else:
                    log.info(f"FVG signal {unique_key} passed dynamic cooldown ({dynamic_cooldown:.1f}m). Sending repeated alert (Count {trigger_count + 1}).")
                    self._update_state(unique_key, signal, trigger_count=trigger_count + 1)
                    return True, last_signal_data
            else:
                # Significant change detected -> Reset trigger count
                log.info(f"FVG signal {unique_key} features changed significantly (Diff: {fvg_mid_diff_percent:.2f}%). Resetting cooldown.")
                self._update_state(unique_key, signal, trigger_count=1)
                return True, last_signal_data

        # If it's not an FVG signal or other logic
        log.info(f"Signal {unique_key} logic fell through. Updating state and sending.")
        self._update_state(unique_key, signal, trigger_count=1)
        return True, last_signal_data

    def _update_state(self, unique_key, signal, trigger_count=1):
        """
        Updates or creates the state of a signal and saves it to the file.
        """
        self.last_triggered_signals[unique_key] = {
            "timestamp": time.time(),
            "signal_data": signal,
            "trigger_count": trigger_count
        }
        self._save_state()