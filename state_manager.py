import time
import json
import os
from config import SIGNAL_COOLDOWN_PERIOD, Z_SCORE_CHANGE_THRESHOLD, PERCENTAGE_CHANGE_THRESHOLD, FVG_COOLDOWN_PERIOD_MINUTES, FVG_PRICE_TOLERANCE_PERCENT
from logger import log

class SignalStateManager:
    def __init__(self, state_file='signal_state.json'):
        """
        Initializes the signal state manager with persistence.
        """
        self.state_file = state_file
        # Storage structure: { "unique_key": {"timestamp": float, "signal_data": dict} }
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
        Determines if a new alert should be sent based on cooldown and signal significance.
        Returns a tuple (should_send: bool, previous_signal: dict | None)
        """
        unique_key = self._get_unique_key(symbol, signal)
        current_time = time.time()
        
        last_signal_info = self.last_triggered_signals.get(unique_key)

        # 1. If the signal has never been sent before, it should be sent.
        if not last_signal_info:
            log.info(f"New signal type {unique_key}, allowing send.")
            self._update_state(unique_key, signal)
            return True, None

        last_timestamp = last_signal_info['timestamp']
        last_signal_data = last_signal_info['signal_data']['primary_signal']
        current_signal_data = signal['primary_signal']
        
        # 2. Check if the cooldown period has passed for the specific signal type.
        # FVG specific cooldown logic
        if current_signal_data.get('indicator') == "Fair Value Gap Rebalance":
            if (current_time - last_timestamp) / 60 < FVG_COOLDOWN_PERIOD_MINUTES:
                log.debug(f"FVG signal {unique_key} is within its specific cooldown period.")
                # Compare FVG price levels and confirmation candle
                try:
                    last_fvg_top = float(last_signal_data.get('fvg_top', '0'))
                    last_fvg_bottom = float(last_signal_data.get('fvg_bottom', '0'))
                    current_fvg_top = float(current_signal_data.get('fvg_top', '0'))
                    current_fvg_bottom = float(current_signal_data.get('fvg_bottom', '0'))
                    
                    last_conf_candle = last_signal_data.get('confirmation_candle')
                    current_conf_candle = current_signal_data.get('confirmation_candle')

                    # Calculate midpoints for comparison robustness
                    last_fvg_mid = (last_fvg_top + last_fvg_bottom) / 2
                    current_fvg_mid = (current_fvg_top + current_fvg_bottom) / 2

                    # Calculate percentage difference for FVG midpoints
                    # Avoid division by zero
                    if last_fvg_mid != 0:
                        fvg_mid_diff_percent = abs((current_fvg_mid - last_fvg_mid) / last_fvg_mid) * 100
                    else: # If last_fvg_mid is zero, and current_fvg_mid is also zero, they are same. Otherwise, they are different.
                        fvg_mid_diff_percent = 0 if current_fvg_mid == 0 else float('inf')
                    
                    if fvg_mid_diff_percent < FVG_PRICE_TOLERANCE_PERCENT and \
                       last_conf_candle == current_conf_candle:
                        log.info(f"FVG signal {unique_key} suppressed: within cooldown, similar price levels (midpoint diff {fvg_mid_diff_percent:.2f}%) and same confirmation candle.")
                        return False, last_signal_data

                except (ValueError, TypeError) as e:
                    log.warning(f"Error parsing FVG data for comparison for {unique_key}: {e}")
            else:
                log.info(f"FVG signal {unique_key} passed its specific cooldown period ({FVG_COOLDOWN_PERIOD_MINUTES} min), allowing send.")
                self._update_state(unique_key, signal)
                return True, last_signal_data
        
        # General cooldown logic for other signal types or if FVG specific cooldown passed
        if (current_time - last_timestamp) / 60 > SIGNAL_COOLDOWN_PERIOD:
            log.info(f"Signal {unique_key} has passed the general cooldown period, allowing send.")
            self._update_state(unique_key, signal)
            return True, last_signal_data
            
        # 3. Within the cooldown, check if the signal has changed significantly.

        # 3a. For Z-Score type signals
        if 'z_score' in current_signal_data:
            try:
                last_z = float(last_signal_data.get('z_score', 0))
                current_z = float(current_signal_data.get('z_score', 0))
                if abs(current_z - last_z) > Z_SCORE_CHANGE_THRESHOLD:
                    log.info(f"Z-Score for {unique_key} changed significantly ({last_z:.2f} -> {current_z:.2f}), allowing send.")
                    self._update_state(unique_key, signal)
                    return True, last_signal_data
            except (ValueError, TypeError):
                pass # Ignore if z_score is not a number

        # 3b. For percentage change type signals (e.g., 24h OI change)
        if 'change_24h' in current_signal_data:
            try:
                # Convert from string 'xx.xx%' back to float
                last_change_str = last_signal_data.get('change_24h', '0%').strip('%')
                current_change_str = current_signal_data.get('change_24h', '0%').strip('%')
                last_change = float(last_change_str) / 100
                current_change = float(current_change_str) / 100
                if abs(current_change - last_change) > PERCENTAGE_CHANGE_THRESHOLD:
                    log.info(f"Percentage change for {unique_key} changed significantly ({last_change:.2%} -> {current_change:.2%}), allowing send.")
                    self._update_state(unique_key, signal)
                    return True, last_signal_data
            except (ValueError, TypeError):
                pass

        log.info(f"Signal {unique_key} is within cooldown and has not changed significantly. Suppressed.")
        return False, last_signal_data

    def _update_state(self, unique_key, signal):
        """
        Updates or creates the state of a signal and saves it to the file.
        """
        self.last_triggered_signals[unique_key] = {
            "timestamp": time.time(),
            "signal_data": signal
        }
        self._save_state()
