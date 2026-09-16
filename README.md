# Volatility Pulse Bot

WhatsApp trading signals for Deriv Indices (R_10, R_25, R_50, R_75) with Support/Resistance reversal detection.

---

## **Features**

✅ **Real-time Signal Generation**
- Monitors 4 synthetic indices 24/7
- Fires signals when confluence reaches 75%+
- 4-hour cooldown per index (prevents spam)

✅ **S/R Reversal Bonus**
- Add support/resistance levels via web terminal
- Bot catches reversals near key levels
- Can lower threshold from 75% → 60% if RSI is extreme + price near S/R
- Levels auto-expire (configurable TTL)

✅ **WhatsApp Delivery**
- Signals sent instantly via Green API
- Clean, professional format (no indicator details)
- Entry zone, S/L, T/P, R:R, confluence %

---

## **Setup**

### **1. Install Dependencies**

```bash
cd ~/volatility-pulse
source venv/bin/activate
pip install -r requirements.txt
```

### **2. Configure Environment**

Create `.env` file with your credentials:

```bash
nano .env
```

Paste:

```
DERIV_API_TOKEN=pat_861384d5f88f0d95117a150ddc5a8258066431d20d7a8cb5e86485a76c46fec7
GREEN_API_INSTANCE_ID=710722734647
GREEN_API_TOKEN=774963bf8bd74d20aa2133728423e294a413c14a4d364785bd
WHATSAPP_GROUP_ID=120363413768704559@g.us
SCAN_INTERVAL=300
LOG_LEVEL=INFO
```

### **3. Test Connection**

```bash
python3 test_connection.py
```

Expected output:
```
✓ Green API account is active
✓ Test message sent to WhatsApp group
✓ Connected to Deriv WebSocket
✓ ALL TESTS PASSED - Bot is ready!
```

---

## **Running the Bot**

### **Option A: Foreground (Testing)**

```bash
python3 main.py
```

Watch logs in real-time. Press `Ctrl+C` to stop.

### **Option B: Background (Production)**

Run detached in tmux:

```bash
tmux new-session -d -s volatility-pulse "source venv/bin/activate && cd ~/volatility-pulse && python3 main.py"

# Attach to see logs:
tmux attach-session -t volatility-pulse

# Detach (keep running): Ctrl+B then D

# Kill session:
tmux kill-session -t volatility-pulse
```

### **Option C: Auto-restart on Reboot**

Create systemd service (Linux/Unix):

```bash
sudo nano /etc/systemd/system/volatility-pulse.service
```

Paste:

```ini
[Unit]
Description=Volatility Pulse Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/volatility-pulse
Environment="PATH=/home/ubuntu/volatility-pulse/venv/bin"
ExecStart=/home/ubuntu/volatility-pulse/venv/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable volatility-pulse
sudo systemctl start volatility-pulse
sudo systemctl status volatility-pulse

# View logs:
sudo journalctl -u volatility-pulse -f
```

---

## **Managing S/R Levels**

### **Start Web Terminal**

```bash
python3 sr_terminal.py
```

Then open browser: **http://localhost:5000**

### **Features**

- Add/remove support and resistance levels
- Set custom TTL (time-to-live) per level
- View active levels for each index
- Levels auto-expire and cleanup

### **How It Works**

When you add a level:

1. Bot stores it with expiration time
2. Each scan checks: "Is price within $0.50 of this level?"
3. If YES + RSI extreme (< 30 or > 70) → +10-15% confidence bonus
4. Lower threshold kicks in automatically
5. Level expires after TTL (default 4 hours)

**Example:**

- Normal signal threshold: 75%
- You add resistance at $150.00
- Price reaches $150.15, RSI = 72
- Bot calculates: 65% + 10% S/R bonus = 75% → **SIGNAL FIRES**
- Without S/R, signal wouldn't have fired (65% < 75%)

---

## **Logs**

Main bot logs to `volatility_pulse.log`:

```bash
# View last 50 lines
tail -50 volatility_pulse.log

# Follow live (updates in real-time)
tail -f volatility_pulse.log

# Search for specific symbol
grep "R_25" volatility_pulse.log
```

Example log output:

```
2026-09-14 13:45:32,123 [INFO] [2026-09-14 13:45 UTC] Scanning indices...
2026-09-14 13:45:33,456 [INFO] R_10: 68% | Dir UP | Threshold: 75%
2026-09-14 13:45:33,789 [INFO] R_25: 71% | Dir DOWN | Threshold: 75%
2026-09-14 13:45:34,012 [INFO] R_50: 78% | Dir UP | Threshold: 75%
2026-09-14 13:45:34,345 [INFO] 🔥 SIGNAL FIRED: R_50 UP
2026-09-14 13:45:35,678 [INFO] ✓ R_50 signal delivered to WhatsApp
```

---

## **Strategy Details**

### **Confluence Scoring (Max 20 pts)**

| Timeframe | Max Pts | What It Measures |
|-----------|---------|------------------|
| **1H** | 5 | Macro bias + trend strength (EMA stack + ADX) |
| **15M** | 9 | Pullback exhaustion + mean reversion (RSI + 9EMA + SAR) |
| **5M** | 6 | Entry trigger + confirmation (RSI extreme + MACD) |

### **Threshold Logic**

- **Base threshold:** 75% confluence
- **With S/R bonus:** Can drop to 60%
- **Cooldown:** 4 hours per index (prevents duplicate signals)
- **Validity window:** Signal valid for 10 minutes after fire

---

## **Files**

| File | Purpose |
|------|---------|
| `main.py` | Orchestrator - listens, scores, sends signals |
| `deriv_websocket.py` | WebSocket client for Deriv tick data + candle builder |
| `volatility_pulse_strategy.py` | All indicators (EMA, RSI, MACD, ATR, ADX, SAR) + scoring |
| `whatsapp_sender.py` | Green API integration for WhatsApp delivery |
| `sr_manager.py` | Support/resistance level manager with expiry |
| `sr_terminal.py` | Flask web app for managing S/R levels |
| `test_connection.py` | Quick connectivity test |
| `.env` | Environment config (credentials) |
| `sr_levels.json` | Persistent S/R level storage |
| `volatility_pulse.log` | Bot activity log |

---

## **Troubleshooting**

### **Bot won't start**

```bash
# Check Python version
python3 --version  # Should be 3.8+

# Check dependencies
pip list | grep websocket
pip list | grep requests

# Reinstall if needed
pip install -r requirements.txt
```

### **No signals firing**

1. Check `.env` credentials are correct
2. Run `python3 test_connection.py` - verify connections work
3. Wait 5 minutes for tick data to populate
4. Check `volatility_pulse.log` for errors

### **Green API errors**

- Verify Green API token is valid (not expired)
- Verify WhatsApp group ID is correct (should have @g.us suffix)
- Test manually: `whatsapp.send_test_message(WHATSAPP_GROUP)`

### **Deriv WebSocket disconnects**

- Normal - bot auto-reconnects every 30 seconds
- Check internet connection
- Verify Deriv API token hasn't expired

---

## **Next Phase: MT5 EA**

Once you've validated signals for 30 days:

1. **Measure accuracy** - Win rate, R:R hits, best times
2. **Build MT5 EA** - Reads same signals, auto-executes on Deriv MT5
3. **Run parallel test** - Signals + EA trades together for 2 weeks
4. **Go live** - EA customers get auto-execution

---

## **Questions?**

Check logs first: `tail -f volatility_pulse.log`

---

**Bot Status:** ✅ Ready to deploy
