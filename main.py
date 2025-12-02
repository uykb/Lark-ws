import time
import schedule
from datetime import datetime
from config import TIMEFRAME, ACTIVE_SIGNALS
from data_fetcher import get_all_binance_data_sync
import indicators as indicator_module
from ai_interpreter import get_gemini_interpretation
from alerter import send_discord_alert
from state_manager import SignalStateManager
from logger import log

# --- Initialization ---

def initialize_signal_checkers():
    """Dynamically initializes signal checker instances based on ACTIVE_SIGNALS config."""
    checkers = []
    for signal_class_name in ACTIVE_SIGNALS:
        if hasattr(indicator_module, signal_class_name):
            signal_class = getattr(indicator_module, signal_class_name)
            checkers.append(signal_class())
            log.info(f"Successfully initialized signal checker: {signal_class_name}")
        else:
            log.warning(f"Signal checker '{signal_class_name}' not found in indicators module.")
    return checkers

state_manager = SignalStateManager()
signal_checkers = initialize_signal_checkers()

def run_check():
    """
    Main function to run all active signal checks.
    """
    log.info(f"Starting data fetch for all symbols on the {TIMEFRAME} timeframe...")
    all_data = get_all_binance_data_sync()

    if not all_data:
        log.warning("Could not fetch any market data. Skipping this run.")
        return

    log.info(f"Data fetched for {len(all_data)} symbols. Now checking for signals...")

    for symbol, df in all_data.items():
        # Iterate through all active signal checkers
        for checker in signal_checkers:
            signal = checker.check(df)
            
            if signal:
                log.info(f"Found potential signal for {symbol} using {checker.name}")
                log.debug(f"Signal details: {signal['primary_signal']}")
                
                # Check if the alert should be sent
                should_send, prev_signal = state_manager.should_send_alert(symbol, signal)
                if should_send:
                    ai_insight = get_gemini_interpretation(symbol, TIMEFRAME, signal, previous_signal=prev_signal)
                    send_discord_alert(symbol, signal, ai_insight)
                    time.sleep(2) # Small delay to avoid rate limiting

    log.info("Check complete.")

if __name__ == "__main__":
    if not signal_checkers:
        log.error("No signal checkers initialized. Please check your ACTIVE_SIGNALS configuration. Exiting.")
    else:
        log.info("Starting the crypto signal monitor...")
        run_check()
    
    schedule.every(15).minutes.do(run_check)
    log.info("Scheduled to run every 15 minutes.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
