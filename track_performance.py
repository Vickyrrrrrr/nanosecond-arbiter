"""
Performance Tracker for Market Making Bot
==========================================
This script tracks and analyzes your bot's performance over time.
Run this daily to see if the strategy is profitable.
"""

import json
import requests
import hmac
import hashlib
import time
from datetime import datetime
from urllib.parse import urlencode

# Your API credentials
API_KEY = "YOUR_BINANCE_API_KEY_HERE"  # Replace with your actual API key
API_SECRET = "YOUR_BINANCE_API_SECRET_HERE"  # Replace with your actual API secret
BASE_URL = "https://testnet.binance.vision"

def get_signature(params):
    query_string = urlencode(params)
    signature = hmac.new(
        API_SECRET.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def get_account_info():
    """Get account balance"""
    endpoint = "/api/v3/account"
    timestamp = int(time.time() * 1000)
    
    params = {'timestamp': timestamp}
    params['signature'] = get_signature(params)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    
    response = requests.get(BASE_URL + endpoint, params=params, headers=headers)
    return response.json()

def get_trade_history():
    """Get recent trades"""
    endpoint = "/api/v3/myTrades"
    timestamp = int(time.time() * 1000)
    
    params = {
        'symbol': 'BTCUSDT',
        'timestamp': timestamp,
        'limit': 100
    }
    params['signature'] = get_signature(params)
    
    headers = {'X-MBX-APIKEY': API_KEY}
    
    response = requests.get(BASE_URL + endpoint, params=params, headers=headers)
    return response.json()

def calculate_pnl(trades):
    """Calculate profit and loss"""
    buys = []
    sells = []
    
    for trade in trades:
        price = float(trade['price'])
        qty = float(trade['qty'])
        is_buyer = trade['isBuyer']
        
        if is_buyer:
            buys.append({'price': price, 'qty': qty})
        else:
            sells.append({'price': price, 'qty': qty})
    
    # Calculate total bought and sold
    total_bought_value = sum(b['price'] * b['qty'] for b in buys)
    total_bought_qty = sum(b['qty'] for b in buys)
    
    total_sold_value = sum(s['price'] * s['qty'] for s in sells)
    total_sold_qty = sum(s['qty'] for s in sells)
    
    # Calculate PnL
    pnl = total_sold_value - total_bought_value
    
    return {
        'total_buys': len(buys),
        'total_sells': len(sells),
        'bought_qty': total_bought_qty,
        'sold_qty': total_sold_qty,
        'bought_value': total_bought_value,
        'sold_value': total_sold_value,
        'pnl': pnl,
        'avg_buy_price': total_bought_value / total_bought_qty if total_bought_qty > 0 else 0,
        'avg_sell_price': total_sold_value / total_sold_qty if total_sold_qty > 0 else 0
    }

def save_daily_report():
    """Save daily performance report"""
    account = get_account_info()
    trades = get_trade_history()
    
    # Get balances
    balances = {}
    for balance in account.get('balances', []):
        asset = balance['asset']
        free = float(balance['free'])
        locked = float(balance['locked'])
        if free > 0 or locked > 0:
            balances[asset] = {'free': free, 'locked': locked}
    
    # Calculate PnL
    pnl_data = calculate_pnl(trades)
    
    # Create report
    report = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'time': datetime.now().strftime('%H:%M:%S'),
        'balances': balances,
        'trades': pnl_data,
        'total_trades': len(trades)
    }
    
    # Save to file
    filename = f"performance_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report, filename

def print_report(report):
    """Print formatted report"""
    print("\n" + "="*60)
    print("📊 DAILY PERFORMANCE REPORT")
    print("="*60)
    print(f"Date: {report['date']} {report['time']}")
    print()
    
    print("💰 Account Balances:")
    for asset, bal in report['balances'].items():
        if asset in ['BTC', 'USDT']:
            print(f"   {asset}: {bal['free']:.8f} (Locked: {bal['locked']:.8f})")
    print()
    
    print("📈 Trading Activity:")
    trades = report['trades']
    print(f"   Total Trades: {report['total_trades']}")
    print(f"   Buy Orders: {trades['total_buys']}")
    print(f"   Sell Orders: {trades['total_sells']}")
    print()
    
    if trades['total_buys'] > 0 or trades['total_sells'] > 0:
        print("💵 Trade Summary:")
        print(f"   Bought: {trades['bought_qty']:.8f} BTC @ avg ${trades['avg_buy_price']:.2f}")
        print(f"   Sold: {trades['sold_qty']:.8f} BTC @ avg ${trades['avg_sell_price']:.2f}")
        print()
        
        print("💰 Profit/Loss:")
        pnl = trades['pnl']
        pnl_color = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        print(f"   {pnl_color} PnL: ${pnl:.2f}")
        
        if trades['bought_qty'] > 0:
            roi = (pnl / trades['bought_value']) * 100
            print(f"   ROI: {roi:.2f}%")
    else:
        print("⚠️  No trades executed yet")
    
    print()
    print("="*60)

def analyze_week():
    """Analyze performance over the week"""
    import glob
    import os
    
    files = sorted(glob.glob("performance_*.json"))
    
    if not files:
        print("❌ No performance data found. Run this script daily!")
        return
    
    print("\n" + "="*60)
    print("📊 WEEKLY PERFORMANCE ANALYSIS")
    print("="*60)
    print()
    
    total_pnl = 0
    total_trades = 0
    daily_pnls = []
    
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            pnl = data['trades']['pnl']
            trades = data['total_trades']
            
            total_pnl += pnl
            total_trades += trades
            daily_pnls.append((data['date'], pnl, trades))
    
    print("📅 Daily Breakdown:")
    for date, pnl, trades in daily_pnls:
        pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"
        print(f"   {date}: {pnl_emoji} ${pnl:.2f} ({trades} trades)")
    
    print()
    print("📊 Week Summary:")
    print(f"   Total Days: {len(files)}")
    print(f"   Total Trades: {total_trades}")
    print(f"   Total PnL: ${total_pnl:.2f}")
    print(f"   Avg Daily PnL: ${total_pnl/len(files):.2f}")
    
    # Calculate win rate
    winning_days = sum(1 for _, pnl, _ in daily_pnls if pnl > 0)
    win_rate = (winning_days / len(files)) * 100
    print(f"   Win Rate: {win_rate:.1f}%")
    
    print()
    print("🎯 Recommendation:")
    if total_pnl > 0 and win_rate >= 60:
        print("   ✅ Strategy looks profitable! Consider real trading with small capital.")
    elif total_pnl > 0 and win_rate >= 40:
        print("   ⚠️  Marginally profitable. Need more data or strategy adjustment.")
    else:
        print("   ❌ Not profitable yet. Keep testing or adjust strategy.")
    
    print("="*60)

if __name__ == "__main__":
    print("🤖 Market Making Bot - Performance Tracker")
    print()
    
    # Generate today's report
    report, filename = save_daily_report()
    print(f"✅ Report saved to: {filename}")
    print_report(report)
    
    # Show weekly analysis if data exists
    print("\n" + "-"*60 + "\n")
    analyze_week()
    
    print("\n💡 Run this script daily to track performance!")
    print("   After 7 days, you'll have enough data to decide on real trading.")
