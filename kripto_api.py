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
if df is None or len(df) < atr_period + 2:
        print("⚠️ Yetersiz veya boş veri geldi, indikatör hesaplanamadı.")
        return df

    df = df.copy()
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    atr = true_range.rolling(atr_period).mean() # Standart RMA yerine basit hareketli ortalama (SMA) yaklaşımı
    
    x_atr_trailing_stop = np.zeros(len(df))
    n_loss = key_value * atr

    # 2. Trailing Stop (Takip Eden Zarar Durdurma) Çizgisi Hesaplama
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
    ema = df['close'].ewm(span=1, adjust=False).mean() # Kaynak çizgi (Kapanış fiyatı)
    position = np.zeros(len(df))
    signals = [] # "AL", "SAT" veya "BEKLE"

    for i in range(len(df)):
        if i == 0 or x_atr_trailing_stop[i] == 0:
            signals.append("BEKLE")
            continue
        
        # Fiyat çizgiyi yukarı keserse AL, aşağı keserse SAT
        if ema.iloc[i] > x_atr_trailing_stop[i] and ema.iloc[i-1] <= x_atr_trailing_stop[i-1]:
            position[i] = 1 # AL Pozisyonu
            signals.append("AL")
        elif ema.iloc[i] < x_atr_trailing_stop[i] and ema.iloc[i-1] >= x_atr_trailing_stop[i-1]:
            position[i] = -1 # SAT Pozisyonu
            signals.append("SAT")
        else:
            position[i] = position[i-1]
            signals.append("BEKLE")
            
    df['signal'] = signals
    return df

# --- BINANCE'DEN CANLI VERİ ÇEKME ---
def get_binance_data(symbol="BTCUSDT", interval="15m", limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url).json()
    
    df = pd.DataFrame(response, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    
    # Verileri sayısal formata çeviriyoruz
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    return df

# --- BOTUN ANA ÇALIŞMA DÖNGÜSÜ ---
async def bot_islem_dovusu():
    son_sinyal = None
    print("🤖 Bağımsız Bot Döngüsü Başlatıldı. 15 dakikada bir kontrol edilecek...")
    
    while True:
        try:
            coin = "BTCUSDT"
            periyot = "15m"
            
            # Veriyi çek ve indikatörü hesapla
            df = get_binance_data(symbol=coin, interval=periyot, limit=100)
            df_with_signals = ut_bot_alerts(df, key_value=1, atr_period=10) # Grafik ayarların: 1 ve 10
            
            # En son oluşan sinyali al (Son tamamlanan muma bakıyoruz)
            guncel_satir = df_with_signals.iloc[-1]
            guncel_sinyal = guncel_satir['signal']
            guncel_fiyat = guncel_satir['close']
            
            if guncel_sinyal in ["AL", "SAT"] and guncel_sinyal != son_sinyal:
                son_sinyal = guncel_sinyal
                print(f"🚨 YENİ SİNYAL ÜRETİLDİ! -> {coin} | {guncel_sinyal} | Fiyat: {guncel_fiyat}")
                
                # Gemini Analizi İsteyelim
                prompt = f"Kripto para {coin} için {periyot} grafiklerinde UT Bot Alerts indikatörü fiyata göre yeni bir {guncel_sinyal} sinyali üretti. Güncel fiyat: {guncel_fiyat}. Bu sinyali teknik olarak yorumla, Binance üzerinde bu işleme girmeli miyim? Kısa ve net bir yanıt üret."
                response = model.generate_content(prompt)
                ai_yorum = response.text
                print(f"🤖 Gemini Yapay Zeka Yorumu:\n{ai_yorum}")
                
                # EMİR VERME ADIMI
                # (Buraya ilerleyen aşamada gerçek Binance API emir kodlarını ekleyeceğiz Soner)
                print(f"🛒 [Binance Simülasyonu] {coin} için {guncel_sinyal} emri gönderildi!")
                
        except Exception as e:
            print(f"❌ Döngü sırasında bir hata oluştu: {str(e)}")
            
        # 15 dakikalık periyot için her 60 saniyede bir yeni mum kapanmış mı diye kontrol et
        await asyncio.sleep(60)

# Render sunucusu açıldığında bot döngüsünü arka planda otomatik tetikle
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(bot_islem_dovusu())

@app.get("/")
def home():
    return {"durum": "Bot arka planda tıkır tıkır çalışıyor ve Binance'i tarıyor!"}
