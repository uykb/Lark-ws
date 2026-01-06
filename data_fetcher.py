import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
import pandas as pd
from config import (
    TIMEFRAMES, 
    DATA_FETCH_LIMIT, 
    MAJOR_COINS, 
    SOCKS5_PROXY,
    ENABLE_DYNAMIC_SCAN,
    TOP_N_BY_VOLUME,
    MIN_24H_QUOTE_VOLUME
)
from logger import log

BASE_URL = "https://fapi.binance.com"

async def get_all_usdt_futures_symbols(session):
    """
    Returns a list of symbols to monitor.
    If ENABLE_DYNAMIC_SCAN is True, fetches top volume USDT futures from Binance.
    Otherwise, returns the static MAJOR_COINS list.
    """
    if not ENABLE_DYNAMIC_SCAN:
        if not MAJOR_COINS:
            log.warning("MAJOR_COINS list in config.py is empty and Dynamic Scan is disabled! No symbols will be scanned.")
            return []
        log.info(f"Using the predefined list of {len(MAJOR_COINS)} major coins for scanning: {MAJOR_COINS}")
        return MAJOR_COINS

    log.info("Dynamic Scan Enabled: Fetching 24hr ticker data from Binance...")
    try:
        url = f"{BASE_URL}/fapi/v1/ticker/24hr"
        async with session.get(url) as response:
            response.raise_for_status()
            tickers = await response.json()
        
        # Filter and sort
        usdt_pairs = []
        for t in tickers:
            symbol = t['symbol']
            quote_vol = float(t['quoteVolume'])
            
            # Filter criteria:
            # 1. Must end with USDT
            # 2. Must not be an Index or heavily leveraged token (usually distinct, but for standard futures simple suffix check is mostly enough. 
            #    Binance Futures symbols are mostly standard. We can filter out things like 'USDC' pairs if needed, but here we want USDT.)
            # 3. Volume check
            
            if symbol.endswith('USDT') and quote_vol >= MIN_24H_QUOTE_VOLUME:
                usdt_pairs.append({
                    'symbol': symbol,
                    'quoteVolume': quote_vol
                })
        
        # Sort by volume descending
        usdt_pairs.sort(key=lambda x: x['quoteVolume'], reverse=True)
        
        # Take Top N
        top_pairs = usdt_pairs[:TOP_N_BY_VOLUME]
        selected_symbols = [p['symbol'] for p in top_pairs]
        
        log.info(f"Dynamic Scan selected top {len(selected_symbols)} coins by volume: {selected_symbols}")
        return selected_symbols

    except Exception as e:
        log.error(f"Error during dynamic symbol discovery: {e}. Falling back to MAJOR_COINS.")
        return MAJOR_COINS

async def fetch_binance_server_time(session):
    """Fetches the current server time from Binance (Futures API)."""
    try:
        url = f"{BASE_URL}/fapi/v1/time"
        async with session.get(url) as response:
            response.raise_for_status()
            data = await response.json()
            server_time_ms = data['serverTime']
            # Convert to UTC datetime
            server_time_utc = pd.to_datetime(server_time_ms, unit='ms').to_pydatetime()
            return server_time_utc
    except Exception as e:
        log.error(f"Failed to fetch Binance server time: {e}")
        return None

async def get_binance_data_async(symbol: str, timeframe: str, session):
    """Asynchronously fetches K-lines, OI, and L/S Ratio for a single symbol and timeframe."""
    try:
        # 1. Fetch K-lines
        klines_url = f"{BASE_URL}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': timeframe, 'limit': DATA_FETCH_LIMIT}
        async with session.get(klines_url, params=params) as response:
            response.raise_for_status()
            klines_data = await response.json()

        if not klines_data:
            return symbol, timeframe, pd.DataFrame()

        df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base_asset_volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        volume_delta = df['taker_buy_base_asset_volume'] - (df['volume'] - df['taker_buy_base_asset_volume'])
        df['cvd'] = volume_delta.cumsum()
        
        # 2. Fetch Open Interest (OI)
        oi_url = f"{BASE_URL}/futures/data/openInterestHist"
        oi_params = {'symbol': symbol, 'period': timeframe, 'limit': DATA_FETCH_LIMIT}
        async with session.get(oi_url, params=oi_params) as response:
            response.raise_for_status()
            oi_data = await response.json()
        oi_df = pd.DataFrame(oi_data)
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'], unit='ms')
        oi_df.set_index('timestamp', inplace=True)
        df['oi'] = pd.to_numeric(oi_df['sumOpenInterestValue'])

        # 3. Fetch Long/Short Ratio
        ls_url = f"{BASE_URL}/futures/data/globalLongShortAccountRatio"
        ls_params = {'symbol': symbol, 'period': timeframe, 'limit': DATA_FETCH_LIMIT}
        async with session.get(ls_url, params=ls_params) as response:
            response.raise_for_status()
            ls_data = await response.json()
        ls_df = pd.DataFrame(ls_data)
        ls_df['timestamp'] = pd.to_datetime(ls_df['timestamp'], unit='ms')
        ls_df.set_index('timestamp', inplace=True)
        df['ls_ratio'] = pd.to_numeric(ls_df['longShortRatio'])
        
        df.bfill(inplace=True)
        df.ffill(inplace=True)
        
        return symbol, timeframe, df

    except aiohttp.ClientError as e:
        log.warning(f"Error fetching data for {symbol} {timeframe}: {e}")
        return symbol, timeframe, pd.DataFrame()
    except Exception as e:
        log.error(f"An unexpected error occurred for {symbol} {timeframe}: {e}")
        return symbol, timeframe, pd.DataFrame()

async def get_all_binance_data_async():
    """Fetches data for monitored symbols and timeframes in parallel."""
    if SOCKS5_PROXY:
        # Enable SOCKS5 proxy for Binance requests if configured
        connector = ProxyConnector.from_url(SOCKS5_PROXY, ssl=False)
        log.info(f"Using SOCKS5 Proxy for Binance: {SOCKS5_PROXY}")
    else:
        connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        symbols = await get_all_usdt_futures_symbols(session)
        if not symbols:
            return {}
            
        tasks = []
        for symbol in symbols:
            for timeframe in TIMEFRAMES:
                tasks.append(get_binance_data_async(symbol, timeframe, session))
        
        results = await asyncio.gather(*tasks)
        
        # Return a dictionary of {symbol: {timeframe: dataframe}}
        data = {}
        for symbol, timeframe, df in results:
            if not df.empty:
                if symbol not in data:
                    data[symbol] = {}
                data[symbol][timeframe] = df
        return data

