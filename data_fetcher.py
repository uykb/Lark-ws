import asyncio
import aiohttp
import pandas as pd
from config import TIMEFRAME, DATA_FETCH_LIMIT, MAJOR_COINS
from logger import log

BASE_URL = "https://fapi.binance.com"

async def get_all_usdt_futures_symbols(session):
    """
    Returns the static list of major coins for scanning.
    The dynamic scanning of all USDT futures has been disabled to focus on major coins.
    """
    if not MAJOR_COINS:
        log.warning("MAJOR_COINS list in config.py is empty! No symbols will be scanned.")
        return []
        
    log.info(f"Using the predefined list of {len(MAJOR_COINS)} major coins for scanning: {MAJOR_COINS}")
    return MAJOR_COINS

async def get_binance_data_async(symbol: str, session):
    """Asynchronously fetches K-lines, OI, and L/S Ratio for a single symbol."""
    try:
        # 1. Fetch K-lines
        klines_url = f"{BASE_URL}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        async with session.get(klines_url, params=params) as response:
            response.raise_for_status()
            klines_data = await response.json()

        df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base_asset_volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        volume_delta = df['taker_buy_base_asset_volume'] - (df['volume'] - df['taker_buy_base_asset_volume'])
        df['cvd'] = volume_delta.cumsum()
        
        # 2. Fetch Open Interest (OI)
        oi_url = f"{BASE_URL}/futures/data/openInterestHist"
        oi_params = {'symbol': symbol, 'period': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        async with session.get(oi_url, params=oi_params) as response:
            response.raise_for_status()
            oi_data = await response.json()
        oi_df = pd.DataFrame(oi_data)
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'], unit='ms')
        oi_df.set_index('timestamp', inplace=True)
        df['oi'] = pd.to_numeric(oi_df['sumOpenInterestValue'])

        # 3. Fetch Long/Short Ratio
        ls_url = f"{BASE_URL}/futures/data/globalLongShortAccountRatio"
        ls_params = {'symbol': symbol, 'period': TIMEFRAME, 'limit': DATA_FETCH_LIMIT}
        async with session.get(ls_url, params=ls_params) as response:
            response.raise_for_status()
            ls_data = await response.json()
        ls_df = pd.DataFrame(ls_data)
        ls_df['timestamp'] = pd.to_datetime(ls_df['timestamp'], unit='ms')
        ls_df.set_index('timestamp', inplace=True)
        df['ls_ratio'] = pd.to_numeric(ls_df['longShortRatio'])
        
        df.bfill(inplace=True)
        df.ffill(inplace=True)
        
        return symbol, df

    except aiohttp.ClientError as e:
        log.warning(f"Error fetching data for {symbol}: {e}")
        return symbol, pd.DataFrame()
    except Exception as e:
        log.error(f"An unexpected error occurred for {symbol}: {e}")
        return symbol, pd.DataFrame()

async def get_all_binance_data_async():
    """Fetches data for all USDT futures symbols in parallel."""
    async with aiohttp.ClientSession() as session:
        symbols = await get_all_usdt_futures_symbols(session)
        if not symbols:
            return {}
            
        tasks = [get_binance_data_async(symbol, session) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        # Return a dictionary of {symbol: dataframe}
        return {symbol: df for symbol, df in results if not df.empty}

# --- Synchronous Wrapper for compatibility with existing main.py structure ---
def get_all_binance_data_sync():
    """Synchronous wrapper to run the async data fetching process."""
    try:
        return asyncio.run(get_all_binance_data_async())
    except Exception as e:
        log.error(f"Error running the async data fetcher: {e}")
        return {}
