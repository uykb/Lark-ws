import time
import schedule
from datetime import datetime
from config import TIMEFRAME
from data_fetcher import get_binance_data, get_all_usdt_futures_symbols
from indicators import MomentumSpikeSignal
from ai_interpreter import get_gemini_interpretation
from alerter import send_discord_alert
from state_manager import SignalStateManager

# Initialize the state manager and signal checker
state_manager = SignalStateManager()
momentum_checker = MomentumSpikeSignal()

def run_check():
    """
    Main function to run the momentum spike signal check.
    """
    symbols_to_check = get_all_usdt_futures_symbols()
    if not symbols_to_check:
        print("Could not fetch any symbols to check. Skipping this run.")
        return

    print(f"\n[{datetime.now()}] Starting check for {len(symbols_to_check)} symbols on the {TIMEFRAME} timeframe...")

    for symbol in symbols_to_check:
        # Fetch the 15-minute data for the symbol
        df = get_binance_data(symbol)
        
        if df.empty:
            # Silently skip symbols with no data to reduce log noise
            continue
        
        # Check for a momentum spike signal
        signal = momentum_checker.check(df)
        
        if signal:
            print(f"--- Found potential signal for {symbol} ---")
            print(f"    Details: {signal['primary_signal']}")
            
            # Check if the alert should be sent
            should_send, prev_signal = state_manager.should_send_alert(symbol, signal)
            if should_send:
                ai_insight = get_gemini_interpretation(symbol, TIMEFRAME, signal, previous_signal=prev_signal)
                send_discord_alert(symbol, signal, ai_insight)
                time.sleep(2) # Small delay to avoid rate limiting

    print("Check complete.")

if __name__ == "__main__":
    print("Starting the crypto momentum spike monitor...")
    run_check()
    
    schedule.every(15).minutes.do(run_check)
    print("Scheduled to run every 15 minutes.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
