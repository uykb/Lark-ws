import time
import schedule
from datetime import datetime
from config import DEFAULT_TIMEFRAME, FVG_TIMEFRAME
from data_fetcher import get_binance_data, get_all_usdt_futures_symbols
from indicators import CatchTheRiseSignal, FVGTrendSignal
from ai_interpreter import get_gemini_interpretation
from alerter import send_discord_alert
from state_manager import SignalStateManager

# Initialize the state manager
state_manager = SignalStateManager()

# Associate signal checkers with their respective timeframes
CHECKERS_BY_TIMEFRAME = {
    DEFAULT_TIMEFRAME: [CatchTheRiseSignal()],
    FVG_TIMEFRAME: [FVGTrendSignal()]
}

def run_check():
    """
    Main function to run the signal checks across different timeframes.
    """
    symbols_to_check = get_all_usdt_futures_symbols()
    if not symbols_to_check:
        print("Could not fetch any symbols to check. Skipping this run.")
        return

    print(f"\n[{datetime.now()}] Starting check for {len(symbols_to_check)} symbols across {len(CHECKERS_BY_TIMEFRAME)} timeframes...")

    for symbol in symbols_to_check:
        print(f"--- Checking {symbol} ---")
        
        for timeframe, checkers in CHECKERS_BY_TIMEFRAME.items():
            print(f"  - Timeframe: {timeframe}")
            
            # Fetch data for the specific symbol and timeframe
            df = get_binance_data(symbol, timeframe)
            
            if df.empty:
                print(f"    Could not fetch data for {symbol} on {timeframe}. Skipping.")
                continue
            
            # Run the designated checkers for this timeframe
            for checker in checkers:
                signal = checker.check(df)
                if signal:
                    print(f"    Potential signal found for {symbol} on {timeframe}: {signal['primary_signal']}")
                    
                    # Check if the alert should be sent
                    should_send, prev_signal = state_manager.should_send_alert(symbol, signal)
                    if should_send:
                        # Get AI interpretation
                        ai_insight = get_gemini_interpretation(symbol, timeframe, signal, previous_signal=prev_signal)
                        # Send Discord alert
                        send_discord_alert(symbol, signal, ai_insight)
                        # Small delay to avoid rate limiting
                        time.sleep(2)
    
    print("Check complete.")

if __name__ == "__main__":
    print("Starting the crypto indicator monitor...")
    
    # Run the check immediately on startup
    run_check()
    
    # Schedule the check to run every 15 minutes
    # Note: This will check both 15m and 1h signals during each run.
    # The schedule library is not precise, but this ensures both are checked regularly.
    schedule.every(15).minutes.do(run_check)
    print("Scheduled to run every 15 minutes.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
