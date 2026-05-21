import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.memory import load_profile, update_preference, log_interaction
from core.agent_logger import log_event

class PreferenceAgent:
    def get_profile(self):
        return load_profile()

    def record_like(self, product):
        tags = [t.strip() for t in product.get('tags', '').split(',')]
        update_preference(category=product.get('category'), brand=product.get('brand'), liked_tags=tags)
        log_interaction(product['id'], product['name'], 'liked')
        log_event("PreferenceAgent",
                  f"Learned preference: {product['category']} / {product['brand']} / tags: {', '.join(tags[:3])}",
                  level="success", product_name=product['name'])

    def record_dislike(self, product):
        tags = [t.strip() for t in product.get('tags', '').split(',')]
        update_preference(disliked_tags=tags)
        log_interaction(product['id'], product['name'], 'disliked')
        log_event("PreferenceAgent",
                  f"Filtering out tags: {', '.join(tags[:3])}",
                  level="warning", product_name=product['name'])

    def record_view(self, product):
        log_interaction(product['id'], product['name'], 'viewed')

    def set_budget(self, amount):
        update_preference(budget=amount)
        log_event("PreferenceAgent", f"Budget updated to ₹{amount:,}", level="info")

    def set_name(self, name):
        update_preference(user_name=name)

    def set_categories(self, categories):
        profile = load_profile()
        profile['preferred_categories'] = list(categories)
        from core.memory import save_profile
        save_profile(profile)
        if categories:
            log_event("PreferenceAgent", f"Categories updated: {', '.join(categories)}", level="info")
        else:
            log_event("PreferenceAgent", "Preferred categories cleared", level="info")

    def set_brands(self, brands):
        for brand in brands:
            update_preference(brand=brand)
        if brands:
            log_event("PreferenceAgent", f"Brands updated: {', '.join(brands)}", level="info")

    def get_score_weights(self):
        return {
            "category_match":    3.0,
            "brand_match":       2.0,
            "tag_like_match":    1.5,
            "tag_dislike_penalty": -3.0,
            "budget_fit":        1.0,
            "rating_bonus":      0.5
        }
