import asyncio
from datetime import datetime, time
import pytz
from config import TIMEFRAMES, ACTIVE_SIGNALS, ACTIVE_SESSIONS
from data_fetcher import get_all_binance_data_async
import indicators as indicator_module
from ai_interpreter import get_ai_interpretation
from alerter import send_all_alerts
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

def is_within_trading_hours() -> bool:
    """
    Checks if the current UTC time falls within any of the defined ACTIVE_SESSIONS.
    Handles different timezones and daylight saving time automatically.
    """
    now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)

    for tz_name, start_time_str, end_time_str in ACTIVE_SESSIONS:
        try:
            timezone = pytz.timezone(tz_name)
            # Get current time in the session's timezone
            now_in_tz = now_utc.astimezone(timezone)

            # Parse start and end times
            start_hour, start_minute = map(int, start_time_str.split(':'))
            end_hour, end_minute = map(int, end_time_str.split(':'))

            session_start = now_in_tz.replace(hour=start_hour, minute=start_minute, second=0, microsecond=0)
            session_end = now_in_tz.replace(hour=end_hour, minute=end_minute, second=0, microsecond=0)

            # Handle overnight sessions (e.g., 22:00 - 04:00 next day)
            if session_start > session_end:
                # If current time is past start_time or before end_time (on the next day)
                if now_in_tz >= session_start or now_in_tz < session_end:
                    return True
            else:
                # Normal session (start_time < end_time)
                if session_start <= now_in_tz < session_end:
                    return True
        except pytz.exceptions.UnknownTimeZoneError:
            log.error(f"Unknown timezone in config: {tz_name}")
            continue
        except Exception as e:
            log.error(f"Error checking trading hours for {tz_name} ({start_time_str}-{end_time_str}): {e}")
            continue
    return False

state_manager = SignalStateManager()
signal_checkers = initialize_signal_checkers()

async def run_check():
    """
    Main function to run all active signal checks.
    """
    log.info(f"Starting data fetch for monitored symbols on timeframes: {TIMEFRAMES}...")
    all_data = await get_all_binance_data_async()

    if not all_data:
        log.warning("Could not fetch any market data. Skipping this run.")
        return

    log.info(f"Data fetched for {len(all_data)} symbols. Now checking for signals...")

    for symbol, timeframe_data in all_data.items():
        for timeframe, df in timeframe_data.items():
            # Iterate through all active signal checkers
            for checker in signal_checkers:
                signal = checker.check(df, symbol=symbol)
                
                if signal:
                    log.info(f"Found potential signal for {symbol} ({timeframe}) using {checker.name}")
                    log.debug(f"Signal details: {signal['primary_signal']}")
                    
                    # Check if the alert should be sent
                    should_send, prev_signal = state_manager.should_send_alert(symbol, timeframe, signal)
                    if should_send:
                        # Async AI interpretation
                        ai_insight, model_name = await get_ai_interpretation(symbol, timeframe, signal, previous_signal=prev_signal)
                        
                        # Async Lark alert
                        await send_all_alerts(symbol, timeframe, signal, ai_insight, model_name=model_name)
                        
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
        # Check if current time is within active trading sessions
        if not is_within_trading_hours():
            log.info("Outside of active trading hours. Sleeping for 1 minute until next check.")
            await asyncio.sleep(1 * 60) # Still sleep for 1 minute before re-checking
            continue # Skip run_check and go to next loop iteration

        try:
            await run_check()
        except Exception as e:
            log.error(f"Error in main loop: {e}")
        
        # Calculate next run time (15 minutes interval)
        log.info("Sleeping for 1 minute...")
        await asyncio.sleep(1 * 60) 

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        log.info("Bot stopped by user.")
