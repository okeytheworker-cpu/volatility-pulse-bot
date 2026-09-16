import requests
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class WhatsAppSender:
    def __init__(self, instance_id, api_token):
        self.instance_id = instance_id
        self.api_token = api_token
        self.base_url = f"https://api.green-api.com/waInstance{instance_id}"
    
    def send_signal(self, chat_id, signal_data):
        """Send trading signal to WhatsApp group"""
        try:
            message = self._format_signal_message(signal_data)
            
            payload = {
                "chatId": chat_id,
                "message": message
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage?token={self.api_token}",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"✓ Signal sent to {signal_data['symbol']}")
                return True
            else:
                logger.error(f"✗ Send failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending signal: {e}")
            return False
    
    def _format_signal_message(self, data):
        """Format signal data into WhatsApp message (clean, no indicator breakdown)"""
        symbol = data["symbol"]
        direction = data["direction"]
        entry_price = data["entry_price"]
        entry_zone = data["entry_zone"]
        sl = data["sl"]
        tp = data["tp"]
        confluence = data["confluence_pct"]
        
        # Direction emoji
        emoji = "📈" if direction == "UP" else "📉"
        
        # Quality label based on confluence
        if confluence >= 87:
            quality = "🔥 Exceptional"
        elif confluence >= 80:
            quality = "💪 Very Strong"
        elif confluence >= 75:
            quality = "✅ Strong"
        else:
            quality = "👍 Good"
        
        # Build message (clean, no strategy details)
        msg = f"""{emoji} *{symbol} {direction}*

Entry: ${entry_price:.2f}
Zone: ${entry_zone['low']:.2f} - ${entry_zone['high']:.2f}

S/L: ${sl:.2f}
T/P: ${tp:.2f}
R:R = 1:{data['rr_ratio']:.1f}

{quality}
Confluence: {confluence:.0f}%
Valid: 10 min

{datetime.now().strftime('%d %b %Y %H:%M UTC')}
"""
        return msg
    
    def send_test_message(self, chat_id, text="Test message from Volatility Pulse Bot ✓"):
        """Send simple test message"""
        try:
            payload = {
                "chatId": chat_id,
                "message": text
            }
            
            response = requests.post(
                f"{self.base_url}/sendMessage?token={self.api_token}",
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✓ Test message sent")
                return True
            else:
                logger.error(f"✗ Test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending test: {e}")
            return False
    
    def get_account_status(self):
        """Check if Green API account is active"""
        try:
            response = requests.get(
                f"{self.base_url}/getSettings?token={self.api_token}",
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("✓ Green API account active")
                return True
            else:
                logger.error(f"✗ Account check failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking account: {e}")
            return False
