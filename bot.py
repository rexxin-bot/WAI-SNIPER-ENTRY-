import os
import requests
from flask import Flask, request

# =========================================================
# CONFIG
# =========================================================

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "xauusd-secret")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN belum diatur di Environment Variables Render")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F"

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

app = Flask(__name__)


# =========================================================
# TELEGRAM
# =========================================================

def send_message(chat_id, text):
    try:
        url = f"{TELEGRAM_API}/sendMessage"

        payload = {
            "chat_id": chat_id,
            "text": text
        }

        response = requests.post(
            url,
            json=payload,
            timeout=15
        )

        return response.ok

    except Exception as e:
        print("Telegram error:", e)
        return False


# =========================================================
# GET GOLD DATA
# =========================================================

def get_data(interval):

    params = {
        "range": "5d",
        "interval": interval
    }

    response = requests.get(
        YAHOO_URL,
        params=params,
        headers=HEADERS,
        timeout=15
    )

    response.raise_for_status()

    result = response.json()["chart"]["result"][0]

    closes = result["indicators"]["quote"][0]["close"]

    data = [
        float(price)
        for price in closes
        if price is not None
    ]

    return data


# =========================================================
# SMA
# =========================================================

def sma(data, period):

    if len(data) < period:
        return None

    return sum(data[-period:]) / period


# =========================================================
# RSI
# =========================================================

def rsi(data, period=14):

    if len(data) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, len(data)):

        change = data[i] - data[i - 1]

        if change > 0:
            gains.append(change)
            losses.append(0)

        else:
            gains.append(0)
            losses.append(abs(change))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss

    return 100 - (100 / (1 + rs))


# =========================================================
# ANALYSIS
# =========================================================

def analyze(data):

    price = data[-1]

    ma20 = sma(data, 20)
    ma50 = sma(data, 50)

    r = rsi(data)

    if ma20 is None or ma50 is None or r is None:
        return None

    # Trend

    if price > ma20 and ma20 > ma50:
        trend = "BULLISH"

    elif price < ma20 and ma20 < ma50:
        trend = "BEARISH"

    else:
        trend = "SIDEWAYS"

    return {
        "price": price,
        "ma20": ma20,
        "ma50": ma50,
        "rsi": r,
        "trend": trend
    }


# =========================================================
# XAUUSD ANALYSIS
# =========================================================

def get_analysis():

    m5_data = get_data("5m")
    m15_data = get_data("15m")
    h1_data = get_data("1h")

    m5 = analyze(m5_data)
    m15 = analyze(m15_data)
    h1 = analyze(h1_data)

    if not m5 or not m15 or not h1:
        return "Data belum cukup untuk melakukan analisis."

    # =====================================================
    # SIGNAL
    # =====================================================

    signal = "WAIT"

    reason = []

    # BUY condition
    if (
        h1["trend"] == "BULLISH"
        and m15["trend"] == "BULLISH"
        and m5["trend"] == "BULLISH"
        and 45 <= m5["rsi"] <= 70
    ):

        signal = "BUY"

        reason.append(
            "Trend H1, M15 dan M5 bullish"
        )

        reason.append(
            "RSI M5 berada pada area valid"
        )

    # SELL condition
    elif (
        h1["trend"] == "BEARISH"
        and m15["trend"] == "BEARISH"
        and m5["trend"] == "BEARISH"
        and 30 <= m5["rsi"] <= 55
    ):

        signal = "SELL"

        reason.append(
            "Trend H1, M15 dan M5 bearish"
        )

        reason.append(
            "RSI M5 berada pada area valid"
        )

    else:

        signal = "WAIT"

        reason.append(
            "Trend antar timeframe belum sepenuhnya searah"
        )

    # =====================================================
    # FORMAT MESSAGE
    # =====================================================

    message = (
        "📊 XAUUSD ANALYZER\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        f"💰 Harga: {m5['price']:.2f}\n\n"

        "📈 M5\n"
        f"Trend: {m5['trend']}\n"
        f"RSI: {m5['rsi']:.2f}\n"
        f"SMA20: {m5['ma20']:.2f}\n"
        f"SMA50: {m5['ma50']:.2f}\n\n"

        "📊 M15\n"
        f"Trend: {m15['trend']}\n"
        f"RSI: {m15['rsi']:.2f}\n"
        f"SMA20: {m15['ma20']:.2f}\n"
        f"SMA50: {m15['ma50']:.2f}\n\n"

        "⏰ H1\n"
        f"Trend: {h1['trend']}\n"
        f"RSI: {h1['rsi']:.2f}\n"
        f"SMA20: {h1['ma20']:.2f}\n"
        f"SMA50: {h1['ma50']:.2f}\n\n"

        "━━━━━━━━━━━━━━━━━━\n"

        f"🎯 SIGNAL: {signal}\n\n"

        "📝 Alasan:\n"
        + "\n".join(
            f"• {item}" for item in reason
        )

        + "\n\n"
        "⚠️ Untuk edukasi/simulasi, bukan sinyal pasti."
    )

    return message


# =========================================================
# TELEGRAM COMMANDS
# =========================================================

def process_message(message):

    if "chat" not in message:
        return

    chat_id = message["chat"]["id"]

    text = message.get("text", "").strip()

    if not text:
        return

    command = text.split()[0].lower()

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    if command == "/start":

        reply = (
            "🤖 XAUUSD Analyzer aktif!\n\n"

            "Perintah yang tersedia:\n\n"

            "/xauusd - Analisis XAUUSD\n"
            "/status - Cek status bot\n"
            "/help - Bantuan\n\n"

            "Bot menggunakan analisis:\n"
            "• M5\n"
            "• M15\n"
            "• H1\n"
            "• SMA20 / SMA50\n"
            "• RSI14\n\n"

            "⚠️ Hasil hanya untuk edukasi/simulasi."
        )

        send_message(chat_id, reply)

    # -----------------------------------------------------
    # HELP
    # -----------------------------------------------------

    elif command == "/help":

        reply = (
            "📖 BANTUAN XAUUSD BOT\n\n"

            "/start\n"
            "Menampilkan menu bot.\n\n"

            "/xauusd\n"
            "Menjalankan analisis XAUUSD.\n\n"

            "/status\n"
            "Memeriksa apakah bot aktif.\n"
        )

        send_message(chat_id, reply)

    # -----------------------------------------------------
    # STATUS
    # -----------------------------------------------------

    elif command == "/status":

        reply = (
            "🟢 BOT ONLINE\n\n"
            "XAUUSD Analyzer siap digunakan."
        )

        send_message(chat_id, reply)

    # -----------------------------------------------------
    # XAUUSD
    # -----------------------------------------------------

    elif command == "/xauusd":

        send_message(
            chat_id,
            "⏳ Sedang mengambil data XAUUSD..."
        )

        try:

            result = get_analysis()

            send_message(
                chat_id,
                result
            )

        except Exception as e:

            print("Analysis error:", e)

            send_message(
                chat_id,
                "❌ Gagal mengambil data.\n\n"
                "Coba lagi beberapa saat."
            )

    # -----------------------------------------------------
    # UNKNOWN COMMAND
    # -----------------------------------------------------

    else:

        send_message(
            chat_id,
            "❓ Perintah tidak dikenal.\n\n"
            "Gunakan /help untuk melihat daftar perintah."
        )


# =========================================================
# WEBHOOK
# =========================================================

@app.route(
    "/telegram-webhook",
    methods=["POST"]
)
def telegram_webhook():

    # Security check

    secret = request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    )

    if secret != WEBHOOK_SECRET:
        return "Unauthorized", 403

    try:

        update = request.get_json()

        if update and "message" in update:

            process_message(
                update["message"]
            )

        return "OK", 200

    except Exception as e:

        print("Webhook error:", e)

        return "OK", 200


# =========================================================
# HEALTH CHECK
# =========================================================

@app.route("/")
def home():

    return (
        "XAUUSD Telegram Bot is running."
    )


@app.route("/health")
def health():

    return {
        "status": "online"
    }


# =========================================================
# RUN
# =========================================================

if __name__ == "__main__":

    port = int(
        os.environ.get(
            "PORT",
            10000
        )
    )

    app.run(
        host="0.0.0.0",
        port=port
  )
      
