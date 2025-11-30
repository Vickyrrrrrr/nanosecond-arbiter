import json
import socket
import threading
import time
import random
import websocket # pip install websocket-client

# Configuration
BINANCE_WS = "wss://stream.binance.com:9443/ws/btcusdt@trade"
LOCAL_ENGINE_IP = "127.0.0.1"
LOCAL_ENGINE_PORT = 8083

# Connect to Local Rust Engine via TCP
def connect_to_engine():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((LOCAL_ENGINE_IP, LOCAL_ENGINE_PORT))
        print(f"✅ Connected to Local Engine at {LOCAL_ENGINE_IP}:{LOCAL_ENGINE_PORT}")
        return s
    except Exception as e:
        print(f"❌ Could not connect to engine: {e}")
        return None

engine_socket = connect_to_engine()

def send_order(side, price, quantity):
    if not engine_socket:
        return

    order = {
        "id": int(time.time() * 1000000) + random.randint(1, 1000), # Unique ID
        "side": side,
        "price": int(price * 100), # Convert to cents (e.g. $100.00 -> 10000)
        "quantity": int(quantity)
    }
    
    try:
        # Send JSON with newline delimiter
        message = json.dumps(order) + "\n"
        engine_socket.sendall(message.encode('utf-8'))
        # print(f"Sent {side} @ {price}")
    except Exception as e:
        print(f"Error sending: {e}")

# Handle incoming Binance messages
def on_message(ws, message):
    data = json.loads(message)
    
    # Real Bitcoin Price
    btc_price = float(data['p'])
    
    # MARKET MAKING STRATEGY
    # We place a BUY slightly below the real price
    # We place a SELL slightly above the real price
    
    spread = 5.0 # $5 spread
    
    buy_price = btc_price - (spread / 2)
    sell_price = btc_price + (spread / 2)
    
    # Send to our engine
    send_order("Buy", buy_price, 1)
    send_order("Sell", sell_price, 1)
    
    print(f"📉 BTC: ${btc_price:.2f} | Placed BUY: ${buy_price:.2f} | Placed SELL: ${sell_price:.2f}")

def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### Connection Closed ###")

def on_open(ws):
    print("✅ Connected to Binance Real-Time Feed")

if __name__ == "__main__":
    print("🚀 Starting Crypto Bridge...")
    print("1. Listening to Binance (Real Data)")
    print("2. Forwarding to Local Rust Engine (Your Project)")
    
    # Create WebSocket connection
    ws = websocket.WebSocketApp(BINANCE_WS,
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)
    
    ws.run_forever()
