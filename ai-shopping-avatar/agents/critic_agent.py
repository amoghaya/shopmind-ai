import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.memory import load_profile, save_profile
from core.agent_logger import log_event

class CriticAgent:
    """
    Learns from user approval/rejection of purchase suggestions.
    Adjusts tag weights and dislike list accordingly.
    """

    def on_purchase_approved(self, product):
        """User approved a purchase — reinforce preferences strongly."""
        profile = load_profile()
        tags = [t.strip() for t in str(product.get('tags', '')).split(',')]

        # Add to purchase history
        from datetime import datetime
        profile.setdefault('purchase_history', []).append({
            "product_id":   product['id'],
            "product_name": product['name'],
            "price":        product.get('current_price', product.get('price')),
            "timestamp":    datetime.now().isoformat()
        })

        # Reinforce liked tags (add duplicates = higher weight effect)
        for tag in tags:
            if tag not in profile['liked_tags']:
                profile['liked_tags'].append(tag)

        # Reinforce category + brand
        cat = product.get('category')
        brand = product.get('brand')
        if cat and cat not in profile['preferred_categories']:
            profile['preferred_categories'].append(cat)
        if brand and brand not in profile['preferred_brands']:
            profile['preferred_brands'].append(brand)

        save_profile(profile)
        log_event("CriticAgent",
                  f"Purchase approved — reinforcing {product.get('category')} / {product.get('brand')} preferences",
                  level="success", product_name=product['name'])

    def on_purchase_rejected(self, product, reason=None):
        """User rejected a suggestion — learn what NOT to show."""
        profile = load_profile()
        tags = [t.strip() for t in str(product.get('tags', '')).split(',')]

        # Add tags to disliked if not already liked
        for tag in tags:
            if tag not in profile['liked_tags'] and tag not in profile['disliked_tags']:
                profile['disliked_tags'].append(tag)

        save_profile(profile)
        msg = f"Purchase rejected{' — reason: '+reason if reason else ''} — adding to dislike filter"
        log_event("CriticAgent", msg, level="warning", product_name=product['name'])

    def get_purchase_history(self):
        profile = load_profile()
        return profile.get('purchase_history', [])
