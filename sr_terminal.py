#!/usr/bin/env python3
"""
S/R Terminal - Web Dashboard
Run this on your local machine or VM to manage support/resistance levels
Access at: http://localhost:5000
"""

from flask import Flask, render_template_string, request, jsonify
from sr_manager import SRManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
sr_manager = SRManager("sr_levels.json")

SYMBOLS = ["R_10", "R_25", "R_50", "R_75"]

# Simple HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>S/R Terminal</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f1419; color: #e0e0e0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        header { padding: 20px 0; border-bottom: 1px solid #333; margin-bottom: 30px; }
        h1 { font-size: 28px; font-weight: 600; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 30px; }
        
        .card { background: #1a1f2e; border: 1px solid #333; border-radius: 8px; padding: 20px; }
        .card h2 { font-size: 16px; font-weight: 600; margin-bottom: 15px; color: #00d4ff; }
        
        .form-group { margin-bottom: 12px; }
        label { display: block; font-size: 12px; font-weight: 500; margin-bottom: 4px; color: #888; text-transform: uppercase; }
        select, input, button { width: 100%; padding: 10px; border: 1px solid #333; background: #0f1419; color: #e0e0e0; border-radius: 4px; font-size: 14px; }
        select:focus, input:focus { outline: none; border-color: #00d4ff; box-shadow: 0 0 8px rgba(0, 212, 255, 0.2); }
        button { background: #00d4ff; color: #0f1419; font-weight: 600; cursor: pointer; border: none; margin-top: 8px; }
        button:hover { background: #00b8cc; }
        button.danger { background: #ff4444; }
        button.danger:hover { background: #cc0000; }
        
        .levels-list { margin-top: 15px; }
        .level-item { background: #0f1419; border-left: 3px solid #00d4ff; padding: 12px; margin-bottom: 8px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
        .level-item.resistance { border-left-color: #ff6b6b; }
        .level-item.expired { opacity: 0.5; }
        
        .level-price { font-weight: 600; font-size: 16px; }
        .level-type { font-size: 11px; font-weight: 500; text-transform: uppercase; color: #888; }
        .level-time { font-size: 11px; color: #666; }
        .level-delete { background: #ff4444; color: white; border: none; padding: 4px 8px; font-size: 11px; cursor: pointer; border-radius: 3px; }
        
        .status { padding: 12px; background: #1a2332; border-left: 3px solid #00d4ff; margin-bottom: 20px; border-radius: 4px; }
        .status.error { border-left-color: #ff4444; }
        .status.success { border-left-color: #4ade80; }
        
        .stats { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-top: 15px; }
        .stat { background: #0f1419; padding: 12px; border-radius: 4px; text-align: center; }
        .stat-value { font-size: 24px; font-weight: 600; color: #00d4ff; }
        .stat-label { font-size: 11px; color: #888; margin-top: 4px; }
        
        @media (max-width: 768px) {
            .grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>📊 S/R Terminal</h1>
            <p style="font-size: 13px; color: #666; margin-top: 4px;">Manage support/resistance levels for Volatility Pulse Bot</p>
        </header>
        
        <div id="status"></div>
        
        <div class="grid">
            <!-- Add Level Card -->
            <div class="card">
                <h2>➕ Add Level</h2>
                <div class="form-group">
                    <label>Symbol</label>
                    <select id="symbol">
                        <option value="R_10">R_10 (10-Index)</option>
                        <option value="R_25">R_25 (25-Index)</option>
                        <option value="R_50">R_50 (50-Index)</option>
                        <option value="R_75">R_75 (75-Index)</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>Price Level</label>
                    <input type="number" id="price" placeholder="150.32" step="0.01">
                </div>
                
                <div class="form-group">
                    <label>Type</label>
                    <select id="type">
                        <option value="SUPPORT">Support</option>
                        <option value="RESISTANCE">Resistance</option>
                    </select>
                </div>
                
                <div class="form-group">
                    <label>TTL (minutes)</label>
                    <input type="number" id="ttl" value="240" min="30" max="1440">
                </div>
                
                <button onclick="addLevel()">Add Level</button>
            </div>
            
            <!-- Current Levels Card -->
            <div class="card">
                <h2>📍 Active Levels</h2>
                
                <div class="form-group">
                    <label>View Symbol</label>
                    <select id="viewSymbol" onchange="loadLevels()">
                        <option value="R_10">R_10</option>
                        <option value="R_25">R_25</option>
                        <option value="R_50">R_50</option>
                        <option value="R_75">R_75</option>
                    </select>
                </div>
                
                <div class="stats" id="statsDiv"></div>
                <div class="levels-list" id="levelsList"></div>
                <button class="danger" onclick="clearAllLevels()" style="margin-top: 12px;">Clear All for Symbol</button>
            </div>
        </div>
    </div>
    
    <script>
        async function addLevel() {
            const symbol = document.getElementById('symbol').value;
            const price = parseFloat(document.getElementById('price').value);
            const type = document.getElementById('type').value;
            const ttl = parseInt(document.getElementById('ttl').value);
            
            if (!price || price <= 0) {
                showStatus('Invalid price', 'error');
                return;
            }
            
            try {
                const res = await fetch('/add', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol, price, type, ttl })
                });
                
                const data = await res.json();
                if (data.success) {
                    showStatus(`✓ Added ${type} ${price} to ${symbol}`, 'success');
                    document.getElementById('price').value = '';
                    loadLevels();
                } else {
                    showStatus(data.error || 'Error adding level', 'error');
                }
            } catch (e) {
                showStatus('Connection error', 'error');
            }
        }
        
        async function deleteLevel(symbol, price) {
            try {
                const res = await fetch('/delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ symbol, price })
                });
                
                const data = await res.json();
                if (data.success) {
                    showStatus('✓ Level deleted', 'success');
                    loadLevels();
                }
            } catch (e) {
                showStatus('Error deleting level', 'error');
            }
        }
        
        async function clearAllLevels() {
            const symbol = document.getElementById('viewSymbol').value;
            if (confirm(`Clear all levels for ${symbol}?`)) {
                try {
                    const res = await fetch('/clear', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ symbol })
                    });
                    
                    const data = await res.json();
                    showStatus('✓ All levels cleared', 'success');
                    loadLevels();
                } catch (e) {
                    showStatus('Error clearing levels', 'error');
                }
            }
        }
        
        async function loadLevels() {
            const symbol = document.getElementById('viewSymbol').value;
            
            try {
                const res = await fetch(`/levels/${symbol}`);
                const data = await res.json();
                
                const levelsList = document.getElementById('levelsList');
                const statsDiv = document.getElementById('statsDiv');
                
                if (data.levels.length === 0) {
                    levelsList.innerHTML = '<p style="color: #666; font-size: 13px;">No active levels</p>';
                    statsDiv.innerHTML = '<div class="stat"><div class="stat-value">0</div><div class="stat-label">Levels</div></div>';
                    return;
                }
                
                // Stats
                statsDiv.innerHTML = `
                    <div class="stat">
                        <div class="stat-value">${data.levels.length}</div>
                        <div class="stat-label">Total Levels</div>
                    </div>
                `;
                
                // Levels list
                levelsList.innerHTML = data.levels.map(lvl => `
                    <div class="level-item ${lvl.type.toLowerCase()}">
                        <div>
                            <div class="level-price">$${lvl.price.toFixed(2)}</div>
                            <div class="level-type">${lvl.type}</div>
                            <div class="level-time">${lvl.time_remaining_min.toFixed(0)}m remaining</div>
                        </div>
                        <button class="level-delete" onclick="deleteLevel('${symbol}', ${lvl.price})">Delete</button>
                    </div>
                `).join('');
            } catch (e) {
                document.getElementById('levelsList').innerHTML = '<p style="color: #ff4444; font-size: 13px;">Error loading levels</p>';
            }
        }
        
        function showStatus(msg, type) {
            const statusDiv = document.getElementById('status');
            statusDiv.innerHTML = `<div class="status ${type}">${msg}</div>`;
            if (type === 'success') {
                setTimeout(() => statusDiv.innerHTML = '', 3000);
            }
        }
        
        // Load on start
        loadLevels();
        setInterval(loadLevels, 30000);  // Refresh every 30 sec
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/add', methods=['POST'])
def add_level():
    data = request.json
    success = sr_manager.add_level(
        data['symbol'],
        data['price'],
        data['type'],
        data.get('ttl', 240)
    )
    return jsonify({
        'success': success,
        'error': None if success else 'Level already exists'
    })

@app.route('/delete', methods=['POST'])
def delete_level():
    data = request.json
    sr_manager.remove_level(data['symbol'], data['price'])
    return jsonify({'success': True})

@app.route('/clear', methods=['POST'])
def clear_symbol():
    data = request.json
    sr_manager.clear_symbol(data['symbol'])
    return jsonify({'success': True})

@app.route('/levels/<symbol>')
def get_levels(symbol):
    levels = sr_manager.get_levels(symbol)
    return jsonify({
        'symbol': symbol,
        'levels': [lvl.to_dict() for lvl in levels]
    })

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("S/R Terminal running at http://localhost:5000")
    logger.info("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)
