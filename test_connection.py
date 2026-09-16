#!/usr/bin/env python3
"""Quick connectivity test before running bot"""

import os
import time
from dotenv import load_dotenv
from deriv_websocket import DérivWebSocket
from whatsapp_sender import WhatsAppSender

load_dotenv(".env")

print("=" * 60)
print("VOLATILITY PULSE BOT - CONNECTION TEST")
print("=" * 60)

# Test Green API
print("\n1. Testing Green API...")
whatsapp = WhatsAppSender(
    os.getenv("GREEN_API_INSTANCE_ID"),
    os.getenv("GREEN_API_TOKEN")
)

if whatsapp.get_account_status():
    print("✓ Green API account is active")
    
    # Send test message
    print("   Sending test message...")
    if whatsapp.send_test_message(os.getenv("WHATSAPP_GROUP_ID")):
        print("✓ Test message sent to WhatsApp group")
    else:
        print("✗ Failed to send test message")
else:
    print("✗ Green API account inactive")

# Test Deriv WebSocket
print("\n2. Testing Deriv WebSocket...")
deriv = DérivWebSocket(os.getenv("DERIV_API_TOKEN"))

if deriv.connect():
    print("✓ Connected to Deriv WebSocket")
    
    # Wait for ticks
    print("   Waiting 10 seconds for tick data...")
    time.sleep(10)
    
    # Check candles
    has_data = False
    for symbol in ["R_10", "R_25", "R_50", "R_75"]:
        candles_5m = deriv.get_candles(symbol, "5m")
        if candles_5m:
            has_data = True
            print(f"✓ {symbol}: {len(candles_5m)} 5M candles received")
        else:
            print(f"⏳ {symbol}: Waiting for candles...")
    
    if has_data:
        print("\n✓ ALL TESTS PASSED - Bot is ready!")
    else:
        print("\n⏳ Candles not yet received - bot will work once data flows in")
    
    deriv.disconnect()
else:
    print("✗ Failed to connect to Deriv WebSocket")

print("\n" + "=" * 60)
print("To start the bot, run: python3 main.py")
print("=" * 60)
