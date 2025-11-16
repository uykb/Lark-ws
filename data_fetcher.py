import requests
import pandas as pd
from config import DATA_FETCH_LIMIT

BASE_URL = "https://fapi.binance.com"

def get_all_usdt_futures_symbols():
    """获取币安所有U本位永续合约交易对"""
    try:
        info_url = f"{BASE_URL}/fapi/v1/exchangeInfo"
        exchange_info = requests.get(info_url).json()
        
        symbols = [
            s['symbol'] 
            for s in exchange_info['symbols'] 
            if s['contractType'] == 'PERPETUAL' and s['symbol'].endswith('USDT') and s['status'] == 'TRADING'
        ]
        
        print(f"获取到 {len(symbols)} 个USDT永续合约交易对。")
        return symbols
        
    except Exception as e:
        print(f"获取所有交易对列表失败: {e}")
        return []

def get_binance_data(symbol: str, timeframe: str):
    """获取一个币种的所有相关数据：K-line, OI, L/S Ratio"""
    try:
        # 1. 获取K线数据 (价格, 成交量)
        klines_url = f"{BASE_URL}/fapi/v1/klines"
        params = {'symbol': symbol, 'interval': timeframe, 'limit': DATA_FETCH_LIMIT}
        klines_data = requests.get(klines_url, params=params).json()
        
        df = pd.DataFrame(klines_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        numeric_cols = ['open', 'high', 'low', 'close', 'volume', 'taker_buy_base_asset_volume']
        df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

        # 4. 计算 CVD (Cumulative Volume Delta)
        volume_delta = df['taker_buy_base_asset_volume'] - (df['volume'] - df['taker_buy_base_asset_volume'])
        df['cvd'] = volume_delta.cumsum()
        
        # 2. 获取持仓量 (OI)
        oi_url = f"{BASE_URL}/futures/data/openInterestHist"
        oi_params = {'symbol': symbol, 'period': timeframe, 'limit': DATA_FETCH_LIMIT}
        oi_data = requests.get(oi_url, params=oi_params).json()
        oi_df = pd.DataFrame(oi_data)
        oi_df['timestamp'] = pd.to_datetime(oi_df['timestamp'], unit='ms')
        oi_df.set_index('timestamp', inplace=True)
        df['oi'] = pd.to_numeric(oi_df['sumOpenInterestValue'])
        # 3. 获取多空比
        ls_url = f"{BASE_URL}/futures/data/globalLongShortAccountRatio"
        ls_params = {'symbol': symbol, 'period': timeframe, 'limit': DATA_FETCH_LIMIT}
        ls_data = requests.get(ls_url, params=ls_params).json()
        ls_df = pd.DataFrame(ls_data)
        ls_df['timestamp'] = pd.to_datetime(ls_df['timestamp'], unit='ms')
        ls_df.set_index('timestamp', inplace=True)
        df['ls_ratio'] = pd.to_numeric(ls_df['longShortRatio'])
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()
