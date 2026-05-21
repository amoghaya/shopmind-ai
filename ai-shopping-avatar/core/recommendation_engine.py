import os
import re
import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'products.csv')

def load_products():
    df = pd.read_csv(DATA_PATH)
    return df

def score_product(row, profile, weights):
    score = 0.0
    product_tags = [t.strip() for t in str(row.get('tags', '')).split(',')]

    # Category match
    if row.get('category') in profile.get('preferred_categories', []):
        score += weights['category_match']

    # Brand match
    if row.get('brand') in profile.get('preferred_brands', []):
        score += weights['brand_match']

    # Liked tag matches
    for tag in product_tags:
        if tag in profile.get('liked_tags', []):
            score += weights['tag_like_match']

    # Disliked tag penalty
    for tag in product_tags:
        if tag in profile.get('disliked_tags', []):
            score += weights['tag_dislike_penalty']

    # Budget fit
    budget = profile.get('budget_max', 50000)
    if row.get('price', 0) <= budget:
        score += weights['budget_fit']
    else:
        score -= 2.0  # penalize over budget

    # Rating bonus
    score += float(row.get('rating', 0)) * weights['rating_bonus']

    return round(score, 2)

def get_recommendations(profile, weights, top_n=8):
    df = load_products()
    df['score'] = df.apply(lambda row: score_product(row, profile, weights), axis=1)
    df_sorted = df.sort_values(by=['score', 'rating'], ascending=False)
    return df_sorted.head(top_n).to_dict(orient='records')

def get_all_products():
    return load_products().to_dict(orient='records')

def get_product_by_id(pid):
    df = load_products()
    result = df[df['id'] == pid]
    if not result.empty:
        return result.iloc[0].to_dict()
    return None

def search_products(query, profile=None, budget=None):
    df = load_products()
    query_lower = query.lower()
    categories = sorted(df['category'].dropna().unique().tolist(), key=len, reverse=True)

    matched_category = None
    for category in categories:
        category_lower = category.lower()
        if query_lower == category_lower or re.search(rf'\b{re.escape(category_lower)}\b', query_lower):
            matched_category = category
            break

    if matched_category:
        results = df[df['category'].str.lower() == matched_category.lower()]
        remaining_query = re.sub(rf'\b{re.escape(matched_category.lower())}\b', ' ', query_lower).strip()
        if remaining_query:
            mask = (
                results['name'].str.lower().str.contains(remaining_query, na=False) |
                results['brand'].str.lower().str.contains(remaining_query, na=False) |
                results['tags'].str.lower().str.contains(remaining_query, na=False)
            )
            results = results[mask]
    else:
        mask = (
            df['name'].str.lower().str.contains(query_lower, na=False) |
            df['category'].str.lower().str.contains(query_lower, na=False) |
            df['brand'].str.lower().str.contains(query_lower, na=False) |
            df['tags'].str.lower().str.contains(query_lower, na=False)
        )
        results = df[mask]

    if budget:
        results = results[results['price'] <= budget]
    return results.to_dict(orient='records')
