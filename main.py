import asyncio
from datetime import datetime
from config import TIMEFRAME, ACTIVE_SIGNALS
from data_fetcher import get_all_binance_data_async
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

async def run_check():
    """
    Main function to run all active signal checks.
    """
    log.info(f"Starting data fetch for all symbols on the {TIMEFRAME} timeframe...")
    all_data = await get_all_binance_data_async()

    if not all_data:
        log.warning("Could not fetch any market data. Skipping this run.")
        return

    log.info(f"Data fetched for {len(all_data)} symbols. Now checking for signals...")

    for symbol, df in all_data.items():
        # Iterate through all active signal checkers
        for checker in signal_checkers:
            signal = checker.check(df, symbol=symbol)
            
            if signal:
                log.info(f"Found potential signal for {symbol} using {checker.name}")
                log.debug(f"Signal details: {signal['primary_signal']}")
                
                # Check if the alert should be sent
                should_send, prev_signal = state_manager.should_send_alert(symbol, signal)
                if should_send:
                    # Async AI interpretation
                    ai_insight = await get_gemini_interpretation(symbol, TIMEFRAME, signal, previous_signal=prev_signal)
                    
                    # Run synchronous Discord alert in a separate thread to avoid blocking
                    await asyncio.to_thread(send_discord_alert, symbol, signal, ai_insight)
                    
                    # Small delay to avoid hitting rate limits if multiple signals trigger at once
                    await asyncio.sleep(2) 

    log.info("Check complete.")

async def main_loop():
    """
    Async main loop replacing the schedule library.
    """
    if not signal_checkers:
        log.error("No signal checkers initialized. Please check your ACTIVE_SIGNALS configuration. Exiting.")
        return

    log.info("Starting the crypto signal monitor (Async Mode)...")
    
    while True:
        try:
            await run_check()
        except Exception as e:
            log.error(f"Error in main loop: {e}")
        
        # Calculate next run time (15 minutes interval)
        # Using a simple sleep for now, can be made more precise if needed
        log.info("Sleeping for 15 minutes...")
        await asyncio.sleep(15 * 60) 

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
