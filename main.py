import time
import schedule
from datetime import datetime
from config import TIMEFRAME
from data_fetcher import get_binance_data, get_all_usdt_futures_symbols
from indicators import CatchTheRiseSignal, FVGTrendSignal
from ai_interpreter import get_gemini_interpretation
from alerter import send_discord_alert
from state_manager import SignalStateManager

# Initialize the state manager and signal checkers
state_manager = SignalStateManager()
fvg_checker = FVGTrendSignal()
rise_checker = CatchTheRiseSignal()

def run_check():
    """
    Main function to run the combined signal check.
    """
    symbols_to_check = get_all_usdt_futures_symbols()
    if not symbols_to_check:
        print("Could not fetch any symbols to check. Skipping this run.")
        return

    print(f"\n[{datetime.now()}] Starting check for {len(symbols_to_check)} symbols on the {TIMEFRAME} timeframe...")

    for symbol in symbols_to_check:
        print(f"--- Checking {symbol} ---")
        
        # Fetch the 15-minute data for the symbol
        df = get_binance_data(symbol)
        
        if df.empty:
            print(f"    Could not fetch data for {symbol}. Skipping.")
            continue
        
        # 1. First, check for an FVG trend signal
        fvg_signal = fvg_checker.check(df)
        
        if fvg_signal:
            print(f"    Found FVG signal for {symbol}. Now checking for rise signal...")
            
            # 2. If FVG exists, check for a "Catch the Rise" signal on the same data
            rise_signal = rise_checker.check(df)
            
            if rise_signal:
                print(f"    Found combined signal for {symbol}!")
                
                # 3. Combine the signals into a single, more informative signal
                combined_signal_details = {
                    "indicator": "FVG + Price/OI Spike",
                    "signal_type": "Combined Momentum Signal",
                    **fvg_signal['primary_signal'],
                    **rise_signal['primary_signal']
                }
                
                # Re-package the signal with the full market context
                final_signal = {
                    "primary_signal": combined_signal_details,
                    "market_context": rise_signal['market_context'] # Context is the same
                }

                # 4. Check if the combined alert should be sent
                should_send, prev_signal = state_manager.should_send_alert(symbol, final_signal)
                if should_send:
                    ai_insight = get_gemini_interpretation(symbol, TIMEFRAME, final_signal, previous_signal=prev_signal)
                    send_discord_alert(symbol, final_signal, ai_insight)
                    time.sleep(2) # Small delay to avoid rate limiting

    print("Check complete.")

if __name__ == "__main__":
    print("Starting the crypto indicator monitor...")
    run_check()
    
    schedule.every(15).minutes.do(run_check)
    print("Scheduled to run every 15 minutes.")
    
    while True:
        schedule.run_pending()
        time.sleep(1)
