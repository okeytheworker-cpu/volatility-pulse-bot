# Volatility Pulse Bot on Replit

Deploy a 24/7 always-on bot for free using Replit.

---

## **Step 1: Create Replit Account**

1. Go to **replit.com**
2. Sign up (use GitHub if you have one)
3. Create new Repl → Select **Python**

---

## **Step 2: Upload Files**

In Replit file editor, create these files (copy-paste content):

1. **Create `.env`**
   ```
   DERIV_API_TOKEN=pat_861384d5f88f0d95117a150ddc5a8258066431d20d7a8cb5e86485a76c46fec7
   GREEN_API_INSTANCE_ID=710722734647
   GREEN_API_TOKEN=774963bf8bd74d20aa2133728423e294a413c14a4d364785bd
   WHATSAPP_GROUP_ID=120363413768704559@g.us
   SCAN_INTERVAL=300
   LOG_LEVEL=INFO
   ```

2. **Create `requirements.txt`**
   ```
   requests==2.31.0
   pandas==2.0.3
   numpy==1.24.3
   python-dotenv==1.0.0
   Flask==3.0.0
   ```

3. **Upload all `.py` files:**
   - `main.py`
   - `deriv_websocket.py` (refactored for REST API)
   - `volatility_pulse_strategy.py`
   - `whatsapp_sender.py`
   - `sr_manager.py`
   - `sr_terminal.py`
   - `test_connection.py`

---

## **Step 3: Install Dependencies**

Click **Shell** at bottom of Replit.

Run:
```bash
pip install -r requirements.txt
```

---

## **Step 4: Test Connection**

```bash
python3 test_connection.py
```

Expected output:
```
✓ Green API account is active
✓ Test message sent to WhatsApp group
✓ ALL TESTS PASSED
```

---

## **Step 5: Run the Bot**

```bash
python3 main.py
```

Bot starts scanning every 5 minutes. Watch logs in real-time.

To stop: Press `Ctrl+C`

---

## **Step 6: Keep It Running 24/7 (Always-On)**

Replit stops bots when you close the tab. To keep running:

### **Option A: Replit Deployments (Easiest)**

1. Click **Deploy** button (top right)
2. Choose **Run** → Select `python3 main.py`
3. Replit deploys to always-on server
4. Bot runs 24/7 for free

### **Option B: External Keep-Alive (Advanced)**

Services like **Uptime Robot** ping your Repl every 5 minutes to keep it alive:

1. Go to **uptimerobot.com** (free tier)
2. Create monitor → URL: `https://your-repl-url.repl.co`
3. Interval: 5 minutes
4. Monitors ping your Repl, keeping it alive

---

## **Monitoring**

### **View Live Logs**

In Replit console, logs print in real-time:
```
[2026-09-14 13:45:32] Scanning indices...
R_10: 68% | Dir UP | Threshold: 75%
R_25: 71% | Dir DOWN | Threshold: 75%
🔥 SIGNAL FIRED: R_50 UP
✓ R_50 signal delivered to WhatsApp
```

### **Check Signals Sent**

Replit saves signals to `signals_log.json`:
```bash
cat signals_log.json
```

Shows last 10 signals with timestamp + confluence %.

---

## **S/R Terminal (Optional)**

To manage support/resistance levels via web dashboard:

1. In Replit, click **Webview** (or open your Repl URL)
2. Run in a **separate terminal**:
   ```bash
   python3 sr_terminal.py
   ```
3. Access at `http://localhost:5000`
4. Add/remove S/R levels in real-time

**Note:** S/R Terminal only works locally (Replit free tier doesn't support multiple ports in webview). You can still add levels via JSON editing.

---

## **Troubleshooting**

### **Bot stops after 30 minutes**

Replit's free tier stops inactive Repls. Solutions:

1. **Use Replit Deployments** (see Step 6 Option A)
2. **Use Uptime Robot** (see Step 6 Option B)

### **No signals firing**

1. Check `.env` credentials are correct
2. Run `python3 test_connection.py`
3. Check `signals_log.json` file (should grow with each scan)
4. Check logs for errors

### **Green API errors**

- Verify token hasn't expired
- Verify WhatsApp group ID is correct (should end with `@g.us`)

---

## **Pricing**

**Free tier:** ✅ Unlimited runtime for 1 Repl
**Paid tier:** $7/month (if you want multiple Repls or more resources)

---

## **What's Different from Local?**

| Local | Replit |
|-------|--------|
| Runs while terminal open | Runs 24/7 (with Deployments) |
| Logs in console | Logs in Replit console |
| S/R Terminal on :5000 | S/R only via JSON edit |
| Manual restart on crash | Auto-restarts on deploy |

---

## **Next: GitHub Deployment (Forex Bot Comparison)**

Once Volatility Pulse is stable on Replit, compare:

**Forex Bot on GitHub Actions:**
- Runs every 15 min (2,000 min/month free)
- REST API (yfinance)
- Simple, proven

**Indices Bot on Replit:**
- Runs 24/7 (unlimited on free tier)
- REST API (Deriv)
- Always available

This split keeps both running without hitting GitHub's minute limits.

---

**Bot is ready to deploy to Replit!**
