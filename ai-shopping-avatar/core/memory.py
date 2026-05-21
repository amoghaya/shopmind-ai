import json
import os
from datetime import datetime

PROFILE_PATH = os.path.join(os.path.dirname(__file__), '..', 'memory', 'user_profile.json')

DEFAULTS = {
    "user_name": "",
    "preferred_categories": [],
    "preferred_brands": [],
    "budget_max": 50000,
    "liked_tags": [],
    "disliked_tags": [],
    "interaction_history": [],
    "watchlist": [],
    "purchase_history": []
}

def load_profile():
    if not os.path.exists(PROFILE_PATH):
        save_profile(dict(DEFAULTS))
        return dict(DEFAULTS)
    with open(PROFILE_PATH, 'r') as f:
        data = json.load(f)
    if 'non_preferred_categories' in data:
        del data['non_preferred_categories']
        save_profile(data)
    # Merge with defaults so missing keys never cause KeyError
    for key, val in DEFAULTS.items():
        if key not in data:
            data[key] = val
    return data

def save_profile(profile):
    with open(PROFILE_PATH, 'w') as f:
        json.dump(profile, f, indent=2)

def update_preference(category=None, brand=None, liked_tags=None, disliked_tags=None, budget=None, user_name=None):
    profile = load_profile()
    if user_name:
        profile['user_name'] = user_name
    if category and category not in profile['preferred_categories']:
        profile['preferred_categories'].append(category)
    if brand and brand not in profile['preferred_brands']:
        profile['preferred_brands'].append(brand)
    if liked_tags:
        for tag in liked_tags:
            if tag not in profile['liked_tags']:
                profile['liked_tags'].append(tag)
    if disliked_tags:
        for tag in disliked_tags:
            if tag not in profile['disliked_tags']:
                profile['disliked_tags'].append(tag)
    if budget:
        profile['budget_max'] = budget
    save_profile(profile)

def log_interaction(product_id, product_name, action):
    profile = load_profile()
    profile['interaction_history'].append({
        "product_id": product_id,
        "product_name": product_name,
        "action": action,
        "timestamp": datetime.now().isoformat()
    })
    save_profile(profile)

def add_to_watchlist(product):
    profile = load_profile()
    ids = [p['id'] for p in profile['watchlist']]
    if product['id'] not in ids:
        profile['watchlist'].append({
            "id": product['id'],
            "name": product['name'],
            "price_at_add": product['price'],
            "added_at": datetime.now().isoformat()
        })
        save_profile(profile)
        return True
    return False

def remove_from_watchlist(product_id):
    profile = load_profile()
    profile['watchlist'] = [p for p in profile['watchlist'] if p['id'] != product_id]
    save_profile(profile)

def reset_profile():
    default = {
        "user_name": "",
        "preferred_categories": [],
        "preferred_brands": [],
        "budget_max": 50000,
        "liked_tags": [],
        "disliked_tags": [],
        "interaction_history": [],
        "watchlist": [],
        "purchase_history": []
    }
    save_profile(default)
