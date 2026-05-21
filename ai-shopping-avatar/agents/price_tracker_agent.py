import sys, os
import random
import json
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.memory import load_profile, save_profile
from core.agent_logger import log_event

PRICE_HISTORY_PATH = os.path.join(os.path.dirname(__file__), '..', 'memory', 'price_history.json')

def load_price_history():
    if os.path.exists(PRICE_HISTORY_PATH):
        with open(PRICE_HISTORY_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_price_history(history):
    with open(PRICE_HISTORY_PATH, 'w') as f:
        json.dump(history, f, indent=2)

class PriceTrackerAgent:
    DROP_THRESHOLD = 0.05  # 5% drop triggers alert
    HISTORY_DAYS   = 30    # one month

    def _fluctuate(self, base_price):
        rand = random.random()
        if rand < 0.12:
            factor = random.uniform(0.75, 0.93)   # drop 7-25%
        elif rand < 0.22:
            factor = random.uniform(1.02, 1.12)   # rise 2-12%
        else:
            factor = random.uniform(0.97, 1.03)   # stable ±3%
        return max(1, round(base_price * factor))

    def generate_price_history(self, product_id, base_price):
        history = load_price_history()
        pid = str(product_id)
        if pid not in history:
            entries = []
            price = base_price
            for i in range(self.HISTORY_DAYS, 0, -1):
                price = self._fluctuate(base_price)
                date = (datetime.now() - timedelta(days=i)).strftime('%b %d')
                entries.append({"date": date, "price": price})
            # Today
            entries.append({"date": "Today", "price": self._fluctuate(base_price)})
            history[pid] = entries
            save_price_history(history)
            log_event("PriceTrackerAgent",
                      f"Started tracking price history ({self.HISTORY_DAYS} days)",
                      level="info")
        return history[pid]

    def get_current_price(self, product_id, base_price):
        history = load_price_history()
        pid = str(product_id)
        if pid in history and history[pid]:
            return history[pid][-1]['price']
        generated = self.generate_price_history(product_id, base_price)
        return generated[-1]['price']

    def refresh_price(self, product_id, base_price, product_name=""):
        history = load_price_history()
        pid = str(product_id)
        if pid not in history:
            self.generate_price_history(product_id, base_price)
            history = load_price_history()
        new_price = self._fluctuate(base_price)
        now_str = datetime.now().strftime('%b %d %H:%M')
        history[pid][-1] = {"date": now_str, "price": new_price}
        save_price_history(history)
        log_event("PriceTrackerAgent",
                  f"Price refreshed → ₹{new_price:,}",
                  level="info",
                  product_name=product_name)
        return new_price

    def check_alerts(self, watchlist):
        alerts = []
        history = load_price_history()
        for item in watchlist:
            pid = str(item['id'])
            original_price = item.get('price_at_add', 0)
            if pid in history and history[pid]:
                current_price = history[pid][-1]['price']
                if original_price > 0:
                    change = (current_price - original_price) / original_price
                    if change <= -self.DROP_THRESHOLD:
                        alert = {
                            "product_id": item['id'],
                            "product_name": item['name'],
                            "original_price": original_price,
                            "current_price": current_price,
                            "drop_percent": round(abs(change) * 100, 1),
                            "savings": original_price - current_price
                        }
                        alerts.append(alert)
                        log_event("PriceTrackerAgent",
                                  f"Price drop {alert['drop_percent']}% detected! ₹{original_price:,} → ₹{current_price:,}",
                                  level="alert",
                                  product_name=item['name'])
        return alerts

    def get_lowest_price(self, product_id, base_price):
        h = self.generate_price_history(product_id, base_price)
        return min(e['price'] for e in h)

    def get_highest_price(self, product_id, base_price):
        h = self.generate_price_history(product_id, base_price)
        return max(e['price'] for e in h)

    def get_avg_price(self, product_id, base_price):
        h = self.generate_price_history(product_id, base_price)
        return round(sum(e['price'] for e in h) / len(h))
