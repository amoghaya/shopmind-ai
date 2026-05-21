# 🧠 ShopMind AI — Autonomous Shopping Avatar

An AI-powered multi-agent shopping assistant that learns your preferences,
recommends products, and tracks prices autonomously.

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run ui/app.py
```

## ✅ Features Implemented

### 1. Preference Learning Agent
- Learns from your likes/dislikes/category/brand selections
- Persists your profile in `memory/user_profile.json`
- Tag-based dislike filtering

### 2. AI Recommendation Engine
- Scores each product against your profile using weighted factors
- Category match, brand match, tag affinity, budget fit, rating
- Falls back to top-rated products if no preferences set yet

### 3. Price Tracking Agent (Simulated)
- Generates realistic 7-day price history with natural fluctuations
- Detects price drops ≥5% and shows alerts
- Visual price chart per product
- Refresh button to simulate live price check

## 🏗️ Architecture

```
ui/app.py (Streamlit)
├── agents/preference_agent.py     → Learns user preferences
├── agents/recommendation_agent.py → Generates personalized picks
├── agents/price_tracker_agent.py  → Tracks & detects price drops
├── agents/decision_agent.py       → Decides: recommend/buy/alert
├── core/memory.py                 → Profile persistence (JSON)
├── core/recommendation_engine.py → Scoring algorithm (pandas)
└── data/products.csv              → 30-product catalog
```

## 🧠 How the Scoring Works

Each product gets a score based on:
- +3.0 Category match
- +2.0 Brand match  
- +1.5 per liked tag match
- -3.0 per disliked tag
- +1.0 Budget fit
- +0.5 × Rating bonus

Products above score 5.0 + rating ≥ 4.5 are marked "🔥 Buy Now"
