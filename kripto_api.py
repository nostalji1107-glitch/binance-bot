from fastapi import FastAPI, Request, HTTPException
import uvicorn
import google.generativeai as genai

app = FastAPI(title="Binance UT Bot Sinyal Altyapısı")

# TODO: Gemini API anahtarını buraya yapıştıracaksın
# genai.configure(api_key="YOUR_GEMINI_API_KEY")

@app.get("/")
def durum():
    return {"durum": "Aktif", "mesaj": "Binance UT Bot Dinleyici Sunucusu Çalışıyor."}

# TradingView Webhook'unun sinyal göndereceği kapı
@app.post("/webhook/utbot")
async def tradingview_webhook(request: Request):
    try:
        # TradingView'den gelen JSON verisini alıyoruz
        veri = await request.json()
        
        coin = veri.get("ticker")       # Örn: BTCUSDT
        sinyal = veri.get("sinyal")     # Örn: BUY veya SELL
        fiyat = veri.get("fiyat")       # Örn: 67250
        periyot = veri.get("periyot")   # Örn: 5m (5 Dakikalık)
        
        print(f"🟩 SİNYAL GELDİ: {coin} | {sinyal} | Fiyat: {fiyat} | Grafik: {periyot}")
        
        # GEMINI YAPAY ZEKA YORUMU TETİKLEME
        # Sinyal geldiğinde Gemini'a analiz yaptırıyoruz
        try:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"{coin} kripto parası {periyot} grafiklerinde UT Bot indikatörüne göre {fiyat} seviyesinden {sinyal} sinyali verdi. Kullanıcılara teknik analizi özetleyen, iştah kabartıcı kısa bir mobil bildirim metni yazar mısın?"
            cevap = model.generate_content(prompt)
            yapay_zeka_notu = cevap.text
        except Exception as e:
            yapay_zeka_notu = f"{coin} için UT Bot kırılımı gerçekleşti. Trendi takip edin."

        # Burası ileride veriyi mobil uygulamaya (Play Store) göndereceğimiz yer olacak
        return {
            "durum": "Sinyal İşlendi",
            "coin": coin,
            "sinyal": sinyal,
            "fiyat": fiyat,
            "ai_analiz": yapay_zeka_notu
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Geçersiz veri formatı: {str(e)}")

if __name__ == "__main__":
    # Localhost 8000 portunda sunucuyu ayağa kaldırıyoruz
    uvicorn.run(app, host="127.0.0.1", port=8000)