
# breakout_bot.py (Bybit version)
# ⭐️ Breakout Bot with Bybit + Discord + RSI/Volume Strategy

import ccxt
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
import io
import time
from datetime import datetime, timedelta

WEBHOOK_URL = "https://discord.com/api/webhooks/1397095996512665765/fg-af8SfPQUa2Lxoqb9h4DxUZL1_Kn3RqeJXeCZR40EYaxeGKakKy5Hq0vvZ22LB8YDn"

exchange = ccxt.bybit()

def fetch_ohlcv(symbol, timeframe='1h', limit=200):
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def calculate_rsi(close_prices, period=14):
    delta = close_prices.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def is_sideways(df, days=3, tolerance=0.03):
    recent = df[-days*24:]
    high = recent['high'].max()
    low = recent['low'].min()
    return (high - low) / low < tolerance

def detect_breakout(df):
    rsi = calculate_rsi(df['close'])
    df['RSI'] = rsi
    last_rsi = rsi.iloc[-1]
    prev_rsi = rsi.iloc[-2]

    recent_high = df['high'][-48:-1].max()
    last_close = df['close'].iloc[-1]
    last_volume = df['volume'].iloc[-1]
    avg_volume = df['volume'][-48:-1].mean()

    breakout = last_close > recent_high and last_volume > 1.5 * avg_volume and last_rsi > 60 and last_rsi > prev_rsi
    take_profit = last_rsi > 70 and last_rsi < prev_rsi

    return breakout, take_profit

def plot_chart(df, symbol):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    df['RSI'] = calculate_rsi(df['close'])

    ax1.plot(df.index, df['close'], label='Close Price')
    ax1.set_title(f'{symbol} Price')
    ax1.legend()
    ax2.plot(df.index, df['RSI'], label='RSI', color='orange')
    ax2.axhline(70, color='red', linestyle='--')
    ax2.axhline(30, color='green', linestyle='--')
    ax2.set_title('RSI')
    ax2.legend()

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

def send_to_discord(symbol, price, chart_buf):
    files = {"file": (f"{symbol}.png", chart_buf, "image/png")}
    data = {
        "content": f"🚨 **Tín hiệu Breakout phát hiện trên {symbol}**
💰 Giá hiện tại: `{price}` USDT
📈 RSI tăng và volume vượt mức trung bình
🎯 Thời điểm: {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}"
    }
    requests.post(WEBHOOK_URL, data=data, files=files)

def run_bot():
    markets = exchange.load_markets()
    usdt_pairs = [symbol for symbol in markets if symbol.endswith("/USDT")]
    print(f"Tìm thấy {len(usdt_pairs)} cặp USDT")

    for symbol in usdt_pairs:
        try:
            df = fetch_ohlcv(symbol)
            if is_sideways(df, days=3):
                breakout, take_profit = detect_breakout(df)
                if breakout:
                    chart_buf = plot_chart(df, symbol)
                    current_price = df['close'].iloc[-1]
                    send_to_discord(symbol, current_price, chart_buf)
                time.sleep(0.2)
        except Exception as e:
            print(f"Lỗi với {symbol}: {e}")

if __name__ == "__main__":
    while True:
        run_bot()
        print("⏳ Đợi 1 giờ trước lần quét tiếp theo...")
        time.sleep(3600)
