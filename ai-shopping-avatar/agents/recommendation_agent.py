import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from core.recommendation_engine import get_recommendations, search_products
from core.agent_logger import log_event

class RecommendationAgent:
    def __init__(self, preference_agent):
        self.pref_agent = preference_agent

    def recommend(self, top_n=9):
        profile = self.pref_agent.get_profile()
        weights = self.pref_agent.get_score_weights()
        has_prefs = (profile['preferred_categories'] or
                     profile['preferred_brands'] or
                     profile['liked_tags'])

        if not has_prefs:
            from core.recommendation_engine import load_products
            df = load_products()
            budget = profile.get('budget_max', 50000)
            df = df[df['price'] <= budget]
            df = df.sort_values(by='rating', ascending=False)
            results = df.head(top_n).to_dict(orient='records')
            log_event("RecommendationAgent",
                      f"No preferences yet — showing top {top_n} rated within budget",
                      level="info")
            return results, "top_rated"

        products = get_recommendations(profile, weights, top_n)
        log_event("RecommendationAgent",
                  f"Scored 110 products → top {len(products)} personalized picks",
                  level="success")
        return products, "personalized"

    def search(self, query):
        results = search_products(query)
        log_event("RecommendationAgent",
                  f"Search '{query}' → {len(results)} results",
                  level="info")
        return results

    def explain_recommendation(self, product, profile, score):
        """Generate a natural language explanation for why a product was recommended."""
        reasons = []
        if product.get('category') in profile.get('preferred_categories', []):
            reasons.append(f"matches your interest in {product['category']}")
        if product.get('brand') in profile.get('preferred_brands', []):
            reasons.append(f"from your preferred brand {product['brand']}")
        tags = [t.strip() for t in str(product.get('tags', '')).split(',')]
        matched_tags = [t for t in tags if t in profile.get('liked_tags', [])]
        if matched_tags:
            reasons.append(f"tagged {', '.join(matched_tags[:2])}")
        if product.get('price', 0) <= profile.get('budget_max', 50000):
            reasons.append("fits your budget")
        if float(product.get('rating', 0)) >= 4.5:
            reasons.append(f"highly rated at {product['rating']}★")
        if not reasons:
            reasons.append(f"rated {product.get('rating', '')}★ overall")
        return "Recommended because it " + " · ".join(reasons)
