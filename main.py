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

# Liste simboli consentiti (fuori dal try!)
only_long_symbols = ["NDQM", "QQQ", "VOO", "AAPL", "WWRL", "ISP", "VDE", "NVDA"]
only_short_symbols = ["VWCE"]
both_directions = ["NDX", "NAS1OO", "SPY", "XLE", "UVXY", "CEMB", "ITA", "CSSPX", "ENI", "TSLA"]

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True, silent=True)
    if not data:
        return "Nessun dato ricevuto", 400

    action = data.get("action")
    symbol = data.get("symbol", "").replace("BINANCE:", "").replace(":", "")
    tp = data.get("take_profit")
    sl = data.get("stop_loss")

    if not all([action, symbol, tp, sl]):
        return "Dati incompleti. Richiesti: action, symbol, take_profit, stop_loss", 400

    try:
        tp = float(tp)
        sl = float(sl)
    except ValueError:
        return "Valori take_profit o stop_loss non validi", 400

    if symbol in only_long_symbols and action == "short":
        return jsonify({"error": f"{symbol} è solo LONG"}), 403
    if symbol in only_short_symbols and action == "long":
        return jsonify({"error": f"{symbol} è solo SHORT"}), 403
    if symbol not in (only_long_symbols + only_short_symbols + both_directions):
        return jsonify({"error": f"{symbol} non è nella lista dei simboli permessi"}), 403

    if action not in ["long", "short"]:
        return f"Azione non riconosciuta: {action}", 400

    try:
        account = api.get_account()
        buying_power = float(account.buying_power)
        amount_to_trade = buying_power * 0.03
        market_price = float(api.get_latest_trade(symbol).price)
        qty = round(amount_to_trade / market_price, 4)

        side = "buy" if action == "long" else "sell"

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
