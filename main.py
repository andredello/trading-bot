from flask import Flask, request, jsonify
import alpaca_trade_api as tradeapi
import os
from dotenv import load_dotenv

load_dotenv()  # Carica variabili da .env

app = Flask(__name__)

# Chiavi API da variabili d'ambiente
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = "https://paper-api.alpaca.markets"

# Inizializza Alpaca API
api = tradeapi.REST(ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_URL, api_version="v2")

# Liste simboli
only_long_symbols = ["NDQM", "QQQ", "VOO", "AAPL", "WWRL", "ISP", "VDE", "NVDA"]
only_short_symbols = ["VWCE"]
both_directions = ["NDX", "NAS1OO", "SPY", "XLE", "UVXY", "CEMB", "ITA", "CSSPX", "ENI", "TSLA"]

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data:
        return "Nessun dato ricevuto", 400

    action = data.get("action")
    symbol = data.get("symbol", "").replace("BINANCE:", "").replace(":", "")  # Es: BINANCE:BTCUSDT → BTCUSDT
    tp = float(data.get("take_profit"))
    sl = float(data.get("stop_loss"))

    # Controlli di simbolo e direzione
    if symbol in only_long_symbols and action == "short":
        return jsonify({"error": f"{symbol} è solo LONG"}), 403
    if symbol in only_short_symbols and action == "long":
        return jsonify({"error": f"{symbol} è solo SHORT"}), 403
    if symbol not in (only_long_symbols + only_short_symbols + both_directions):
        return jsonify({"error": f"{symbol} non è nella lista dei simboli permessi"}), 403

    try:
        # Calcolo quantità da tradare (3% del buying power)
        account = api.get_account()
        buying_power = float(account.buying_power)
        amount_to_trade = buying_power * 0.03
        market_price = float(api.get_latest_trade(symbol).price)
        qty = round(amount_to_trade / market_price, 4)

        if action == "long":
            side = "buy"
        elif action == "short":
            side = "sell"
        else:
            return f"Azione non riconosciuta: {action}", 400

        # Invia ordine bracket (TP e SL)
        api.submit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            type="market",
            time_in_force="gtc",
            order_class="bracket",
            take_profit={"limit_price": tp},
            stop_loss={"stop_price": sl}
        )

        return f"{action.upper()} su {symbol} con TP {tp} e SL {sl} inviato con quantità {qty}", 200

    except Exception as e:
        return f"Errore: {str(e)}", 500
