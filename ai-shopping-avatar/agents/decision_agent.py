import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.agent_logger import log_event

class DecisionAgent:
    BUY_SCORE_THRESHOLD  = 5.0
    PRICE_DROP_THRESHOLD = 0.07

    def evaluate(self, product, score, current_price=None):
        base_price = product.get('price', 0)
        rating = float(product.get('rating', 0))

        decision = {
            "product_id":   product['id'],
            "product_name": product['name'],
            "action":       "recommend",
            "reason":       "",
            "urgency":      "low"
        }

        if current_price and base_price > 0:
            drop = (base_price - current_price) / base_price
            if drop >= self.PRICE_DROP_THRESHOLD:
                decision['action']  = 'alert_price_drop'
                decision['reason']  = f"Price dropped {round(drop*100,1)}% · Save ₹{base_price - current_price:,}"
                decision['urgency'] = 'high'
                log_event("DecisionAgent",
                          f"ALERT: Price drop {round(drop*100,1)}% — recommending purchase",
                          level="alert", product_name=product['name'])
                return decision

        if score >= self.BUY_SCORE_THRESHOLD and rating >= 4.5:
            decision['action']  = 'suggest_purchase'
            decision['reason']  = f"Strong match (score {score}) · {rating}★ rating"
            decision['urgency'] = 'medium'
            log_event("DecisionAgent",
                      f"Suggesting purchase — score {score}, rating {rating}★",
                      level="success", product_name=product['name'])
        elif score >= 3.0:
            decision['action']  = 'recommend'
            decision['reason']  = f"Good match for your preferences"
            decision['urgency'] = 'low'
        else:
            decision['action']  = 'ignore'
            decision['reason']  = "Low preference match"
            decision['urgency'] = 'none'

        return decision

    def should_buy(self, product, score, current_price=None):
        d = self.evaluate(product, score, current_price)
        return d['action'] in ('suggest_purchase', 'alert_price_drop')
