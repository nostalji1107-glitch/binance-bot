import os
import time
import requests
import asyncio
import pandas as pd
import numpy as np
from fastapi import FastAPI, BackgroundTasks
import google.generativeai as genai

app = FastAPI()

# --- YAPAY ZEKA AYARI ---
GOOGLE_API_KEY = "AQ.Ab8RN6LAMOMQpw7MrQEiMgVOiEk52j5YBlTZSFnWe6OrZTf9uQ"
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# --- UT BOT ALERTS MATEMATİKSEL HESAPLAMASI ---
def ut_bot_alerts(df, key_value=1, atr_period=10):
    if df is None or len(df) < (atr_period + 5):
        print("⚠️ Yetersiz veri. İndikatör hesaplanamadı, döngü atlanıyor.")
        return None

    df = df.copy()
    
    # Eksik olan high_low hesaplaması eklendi ve hatalar giderildi
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(atr_period).mean()
    
    x_atr_trailing_stop = np.zeros(len(df))
    n_loss = key_value * atr

    # 2. Trailing Stop Çizgisi Hesaplama
    for i in range(1, len(df)):
        if pd.isna(atr.iloc[i]):
            continue
        
        close_curr = df['close'].iloc[i]
        close_prev = df['close'].iloc[i-1]
        stop_prev = x_atr_trailing_stop[i-1]
        loss_curr = n_loss.iloc[i]

        if close_curr > stop_prev and close_prev > stop_prev:
            x_atr_trailing_stop[i] = max(stop_prev, close_curr - loss_curr)
        elif close_curr < stop_prev and close_prev < stop_prev:
            x_atr_trailing_stop[i] = min(stop_prev, close_curr + loss_curr)
        else:
            x_atr_trailing_stop[i] = (close_curr - loss_curr) if close_curr > stop_prev else (close_curr + loss_curr)

    # 3. Sinyal Üretme Mantığı
    ema = df['close'].ewm(span=1, adjust=False).mean()
    position = np.zeros(len(df))
    signals = []

    for i in range(len(df)):
        if i == 0 or x_atr_trailing_stop[i] == 0:
            signals.append("BEKLE")
            continue
        
        if ema.iloc[i] > x_atr_trailing_stop[i] and ema.iloc[i-1] <= x_atr_trailing_stop[i-1]:
            position[i] = 1
            signals.append("AL")
        elif ema.iloc[i] < x_atr_trailing_stop[i] and ema.iloc[i-1] >= x_atr_trailing_stop[i-1]:
            position[i] = -1
            signals.append("SAT")
        else:
            position[i] = position[i-1]
            signals.append("BEKLE")
            
    df['signal'] = signals
    return df

# --- BINANCE'DEN CANLI VERİ ÇEKME ---
def get_binance_data
