import streamlit as st
import sys, os, time, json
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.preference_agent    import PreferenceAgent
from agents.recommendation_agent import RecommendationAgent
from agents.price_tracker_agent import PriceTrackerAgent
from agents.decision_agent      import DecisionAgent
from agents.critic_agent        import CriticAgent
from core.memory                import (load_profile, add_to_watchlist,
                                        remove_from_watchlist, reset_profile)
from core.recommendation_engine import load_products, score_product
from core.agent_logger          import load_log, log_event, clear_log

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="ShopMind AI", page_icon="🧠",
                   layout="wide", initial_sidebar_state="expanded")

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=Syne:wght@600;700;800&display=swap');
html,body,[class*="css"]{font-family:'DM Sans',sans-serif;}
.stApp{background:linear-gradient(135deg,#080810 0%,#0c0c18 60%,#080f18 100%);color:#dde1f0;}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0a0a16 0%,#08101a 100%);border-right:1px solid rgba(139,92,246,.18);}

.hero{font-family:'Syne',sans-serif;font-size:2.6rem;font-weight:800;
  background:linear-gradient(120deg,#a78bfa,#67e8f9,#34d399);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;letter-spacing:-1px;}
.hero-sub{color:#4b5563;font-size:.9rem;margin-top:2px;letter-spacing:.05em;}

.card{background:rgba(255,255,255,.028);border:1px solid rgba(255,255,255,.07);
  border-radius:16px;padding:18px;transition:all .25s ease;height:100%;}
.card:hover{border-color:rgba(167,139,250,.35);background:rgba(167,139,250,.045);transform:translateY(-2px);}

.p-brand{font-size:.72rem;color:#a78bfa;font-weight:600;text-transform:uppercase;letter-spacing:.08em;}
.p-name{font-family:'Syne',sans-serif;font-size:.98rem;font-weight:700;color:#e2e8f0;margin:3px 0;}
.p-cat{font-size:.72rem;color:#374151;margin-bottom:6px;}
.p-price{font-family:'Syne',sans-serif;font-size:1.35rem;font-weight:800;}
.p-rating{font-size:.82rem;color:#fbbf24;}
.p-reason{font-size:.72rem;color:#4b5563;margin-top:6px;line-height:1.4;}

.badge{display:inline-block;padding:2px 9px;border-radius:20px;font-size:.65rem;font-weight:700;
  letter-spacing:.06em;text-transform:uppercase;}
.b-buy{background:rgba(52,211,153,.12);color:#34d399;border:1px solid rgba(52,211,153,.3);}
.b-drop{background:rgba(239,68,68,.12);color:#f87171;border:1px solid rgba(239,68,68,.3);}
.b-rec{background:rgba(167,139,250,.12);color:#a78bfa;border:1px solid rgba(167,139,250,.25);}
.b-nl{background:rgba(96,165,250,.12);color:#60a5fa;border:1px solid rgba(96,165,250,.25);}

.tag{display:inline-block;padding:2px 8px;border-radius:12px;font-size:.65rem;font-weight:500;
  background:rgba(255,255,255,.04);color:#6b7280;border:1px solid rgba(255,255,255,.07);margin:1px;}

.sh{font-family:'Syne',sans-serif;font-size:1.25rem;font-weight:700;color:#e2e8f0;
  padding-bottom:6px;border-bottom:1px solid rgba(255,255,255,.05);margin-bottom:4px;}
.ssub{font-size:.78rem;color:#374151;margin-bottom:14px;}

/* confirm modal overlay */
.modal-bg{position:fixed;inset:0;background:rgba(0,0,0,.75);z-index:999;display:flex;
  align-items:center;justify-content:center;}
.modal{background:#111827;border:1px solid rgba(167,139,250,.3);border-radius:20px;
  padding:32px;max-width:420px;width:90%;}

/* agent log */
.log-entry{display:flex;gap:10px;padding:8px 10px;border-radius:8px;
  margin-bottom:4px;border-left:2px solid transparent;font-size:.78rem;}
.log-info   {border-color:#4b5563;background:rgba(255,255,255,.02);}
.log-success{border-color:#34d399;background:rgba(52,211,153,.05);}
.log-warning{border-color:#fbbf24;background:rgba(251,191,36,.05);}
.log-alert  {border-color:#f87171;background:rgba(239,68,68,.07);}
.log-action {border-color:#60a5fa;background:rgba(96,165,250,.07);}
.log-icon{font-size:1rem;min-width:20px;}
.log-body{flex:1;}
.log-agent{font-weight:600;color:#a78bfa;font-size:.7rem;text-transform:uppercase;}
.log-msg{color:#9ca3af;}
.log-prod{color:#60a5fa;font-size:.68rem;}
.log-time{color:#374151;font-size:.65rem;white-space:nowrap;}

/* execution steps */
.exec-step{display:flex;align-items:center;gap:12px;padding:10px 14px;
  border-radius:10px;margin-bottom:6px;font-size:.85rem;}
.exec-pending {background:rgba(255,255,255,.03);color:#4b5563;}
.exec-running {background:rgba(96,165,250,.08);color:#93c5fd;border:1px solid rgba(96,165,250,.2);}
.exec-done    {background:rgba(52,211,153,.07);color:#6ee7b7;border:1px solid rgba(52,211,153,.18);}
.exec-icon{font-size:1.1rem;min-width:24px;}

/* metric box */
.mbox{background:rgba(255,255,255,.025);border:1px solid rgba(255,255,255,.06);
  border-radius:10px;padding:14px;text-align:center;}
.mval{font-family:'Syne',sans-serif;font-size:1.7rem;font-weight:800;color:#a78bfa;}
.mlbl{font-size:.68rem;color:#374151;text-transform:uppercase;letter-spacing:.1em;}

/* alert box */
.alert-drop{background:rgba(239,68,68,.07);border:1px solid rgba(239,68,68,.2);
  border-left:3px solid #ef4444;border-radius:10px;padding:12px 16px;margin-bottom:10px;}

/* NL search chip */
.nl-chip{display:inline-block;padding:4px 12px;border-radius:20px;cursor:pointer;margin:3px;
  font-size:.78rem;background:rgba(96,165,250,.1);color:#60a5fa;
  border:1px solid rgba(96,165,250,.25);}

/* Streamlit overrides */
.stButton>button{background:rgba(139,92,246,.1);color:#a78bfa;
  border:1px solid rgba(139,92,246,.3);border-radius:8px;
  font-family:'DM Sans',sans-serif;font-weight:600;transition:all .2s;}
.stButton>button:hover{background:rgba(139,92,246,.22);border-color:rgba(139,92,246,.6);}
.stTabs [data-baseweb="tab"]{font-family:'DM Sans',sans-serif;color:#4b5563;font-weight:500;}
.stTabs [aria-selected="true"]{color:#a78bfa!important;}
.stTabs [data-baseweb="tab-border"]{background-color:#a78bfa!important;}
div[data-testid="stMetricValue"]{color:#a78bfa;font-family:'Syne',sans-serif;}
</style>
""", unsafe_allow_html=True)

# ── Agents ────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_agents():
    pref   = PreferenceAgent()
    rec    = RecommendationAgent(pref)
    tracker= PriceTrackerAgent()
    dec    = DecisionAgent()
    critic = CriticAgent()
    return pref, rec, tracker, dec, critic

pref_agent, rec_agent, tracker_agent, decision_agent, critic_agent = get_agents()

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "confirm_product": None,
    "exec_running":    False,
    "exec_steps":      [],
    "exec_done":       False,
    "nl_query":        "",
    "for_you_category_filters": [],
    "for_you_brand_filters": [],
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Confirm + Execute Modal ───────────────────────────────────────────────────
def show_confirm_modal():
    p = st.session_state.confirm_product
    if not p:
        return

    st.markdown("---")
    st.markdown("### 🤖 Agent Recommendation — Awaiting Your Approval")

    col_info, col_actions = st.columns([2, 1])

    with col_info:
        current_price = p.get("current_price", p["price"])
        saving = p["price"] - current_price if current_price < p["price"] else 0
        st.markdown(f"""
        <div style="background:rgba(167,139,250,.07);border:1px solid rgba(167,139,250,.25);
          border-radius:16px;padding:20px;">
          <div class="p-brand">{p['brand']}</div>
          <div style="font-family:'Syne',sans-serif;font-size:1.3rem;font-weight:700;
            color:#e2e8f0;margin:4px 0 8px;">{p['name']}</div>
          <div style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#34d399;">
            ₹{current_price:,}
            {"<span style='font-size:.9rem;color:#6b7280;text-decoration:line-through;margin-left:8px'>₹"+str(p['price'])+",</span>" if saving > 0 else ""}
          </div>
          {"<div style='color:#f87171;font-size:.82rem;margin-top:4px'>💰 You save ₹"+str(saving)+","+" with current price drop</div>" if saving > 0 else ""}
          <div style="margin-top:10px;font-size:.82rem;color:#6b7280;">{p.get('decision_reason','')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_actions:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**The agent recommends this purchase.**")
        st.markdown("Do you want to proceed with simulated checkout?")
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Approve & Buy", key="modal_approve", use_container_width=True):
            st.session_state.exec_running = True
            st.session_state.exec_done    = False
            st.session_state.exec_steps   = []
            critic_agent.on_purchase_approved(p)
            log_event("ExecutionAgent", "Purchase approved by user — initiating execution", level="action", product_name=p['name'])
            st.rerun()

        if st.button("❌ Reject", key="modal_reject", use_container_width=True):
            critic_agent.on_purchase_rejected(p, "user rejected at confirmation")
            st.session_state.confirm_product = None
            st.toast("Noted! Won't suggest this type again.", icon="🎯")
            st.rerun()

        if st.button("⏰ Remind Me Later", key="modal_later", use_container_width=True):
            st.session_state.confirm_product = None
            st.toast("We'll remind you when the price changes.", icon="⏰")
            st.rerun()

# ── Execution Flow ────────────────────────────────────────────────────────────
def show_execution_flow():
    p = st.session_state.confirm_product
    if not p:
        return

    st.markdown("---")
    st.markdown("### ⚡ Execution Agent — Simulated Purchase Flow")

    STEPS = [
        ("🌐", "Opening Flipkart",                     1.2),
        ("🔍", f"Searching for '{p['name']}'",          1.0),
        ("📦", "Product located — verifying details",  0.8),
        ("🏷️", f"Confirmed price ₹{p.get('current_price', p['price']):,}", 0.7),
        ("🛒", "Adding to cart",                        1.0),
        ("📋", "Reviewing cart",                        0.6),
        ("💳", "Proceeding to checkout (simulated)",   1.2),
        ("✅", "Order placed successfully!",            0.5),
    ]

    placeholder = st.empty()

    completed = []
    for i, (icon, label, delay) in enumerate(STEPS):
        # Build display
        html = ""
        for j, (ic, lb, _) in enumerate(STEPS):
            if j < i:
                cls = "exec-done"
                status_icon = "✔️"
            elif j == i:
                cls = "exec-running"
                status_icon = "⏳"
            else:
                cls = "exec-pending"
                status_icon = "·"
            html += f'<div class="exec-step {cls}"><span class="exec-icon">{ic}</span>{lb}<span style="margin-left:auto;font-size:.75rem">{status_icon}</span></div>'

        placeholder.markdown(f'<div style="max-width:500px">{html}</div>', unsafe_allow_html=True)
        log_event("ExecutionAgent", label, level="action", product_name=p['name'])
        time.sleep(delay)

    # Final state — all done
    html = ""
    for ic, lb, _ in STEPS:
        html += f'<div class="exec-step exec-done"><span class="exec-icon">{ic}</span>{lb}<span style="margin-left:auto;font-size:.75rem">✔️</span></div>'
    placeholder.markdown(f'<div style="max-width:500px">{html}</div>', unsafe_allow_html=True)

    st.success(f"🎉 Simulated purchase of **{p['name']}** completed! ₹{p.get('current_price', p['price']):,}")
    st.info("ℹ️ This is a simulation — no real payment was made.")

    st.session_state.exec_running = False
    st.session_state.exec_done    = True

    if st.button("↩️ Back to Shopping"):
        st.session_state.confirm_product = None
        st.session_state.exec_done       = False
        st.rerun()

# ── If execution is running, show only that ───────────────────────────────────
if st.session_state.exec_running:
    show_execution_flow()
    st.stop()

if st.session_state.exec_done and st.session_state.confirm_product:
    show_execution_flow.__doc__  # just to not crash
    # Already handled above, but keep state clean
    pass

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="hero" style="font-size:1.8rem">🧠 ShopMind AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-sub">Autonomous Shopping Avatar</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    profile = load_profile()

    st.markdown("### 👤 Profile")
    name = st.text_input("Your name", value=profile.get('user_name',''), placeholder="Enter name")
    if name and name != profile.get('user_name',''):
        pref_agent.set_name(name)
        st.rerun()

    st.markdown("---")
    st.markdown("### 🎯 Preferences")
    st.caption("Preferences are learned automatically from what you like and buy.")

    all_products = load_products()
    all_categories = sorted(all_products['category'].dropna().unique().tolist())
    all_brands = sorted(all_products['brand'].dropna().unique().tolist())
    preferred_categories = profile.get('preferred_categories', [])
    preferred_brands = profile.get('preferred_brands', [])

    st.markdown("### 🔎 For You Filters")
    category_filters = st.multiselect(
        "Categories",
        options=all_categories,
        default=[c for c in st.session_state.for_you_category_filters if c in all_categories],
        key="sidebar_for_you_categories",
    )
    brand_filters = st.multiselect(
        "Brands",
        options=all_brands,
        default=[b for b in st.session_state.for_you_brand_filters if b in all_brands],
        key="sidebar_for_you_brands",
    )
    st.session_state.for_you_category_filters = category_filters
    st.session_state.for_you_brand_filters = brand_filters

    if preferred_categories or preferred_brands:
        learned_bits = []
        if preferred_categories:
            learned_bits.append(f"learned categories: {', '.join(preferred_categories[:4])}")
        if preferred_brands:
            learned_bits.append(f"learned brands: {', '.join(preferred_brands[:4])}")
        st.caption("Your profile is learning from interactions: " + " | ".join(learned_bits))

    budget = st.slider("Max Budget (₹)", 500, 250000,
                       value=profile.get('budget_max', 50000), step=500, format="₹%d")
    if budget != profile.get('budget_max', 50000):
        pref_agent.set_budget(budget)
        st.rerun()

    st.markdown("---")
    profile = load_profile()
    c1, c2 = st.columns(2)
    with c1: st.metric("Watchlist",     len(profile.get('watchlist',[])))
    with c2: st.metric("Purchases",     len(profile.get('purchase_history',[])))

    st.markdown("---")
    if st.button("🗑️ Reset Everything"):
        reset_profile()
        clear_log()
        ph_path = os.path.join(os.path.dirname(__file__), '..', 'memory', 'price_history.json')
        if os.path.exists(ph_path): os.remove(ph_path)
        st.success("Reset done!")
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
profile = load_profile()
uname   = profile.get('user_name','')
greeting = f"Hey {uname} 👋" if uname else "Welcome 👋"
st.markdown(f'<div class="hero">{greeting}</div>', unsafe_allow_html=True)
st.markdown('<div class="hero-sub">Your AI agents are learning, tracking, and deciding — 24/7.</div>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# Show confirm modal if needed (but not during execution)
if st.session_state.confirm_product and not st.session_state.exec_running:
    show_confirm_modal()
    st.markdown("---")

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "✨ For You", "🔍 Search", "📈 Price Tracker", "🤖 Agent Log", "🗂️ Profile"
])

# ════════════════════════════════════════════════════
# TAB 1 — FOR YOU
# ════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="sh">AI Recommendations</div>', unsafe_allow_html=True)

    profile   = load_profile()
    has_prefs = profile['preferred_categories'] or profile['preferred_brands'] or profile['liked_tags']
    weights = pref_agent.get_score_weights()
    if not has_prefs:
        st.info("Like products to teach the app what you want. Showing top-rated picks for now.")

    selected_categories = st.session_state.get("for_you_category_filters", [])
    selected_brands = st.session_state.get("for_you_brand_filters", [])

    if selected_categories or selected_brands:
        filtered_df = load_products()
        budget_max = profile.get('budget_max', 50000)
        filtered_df = filtered_df[filtered_df['price'] <= budget_max]
        if selected_categories:
            filtered_df = filtered_df[filtered_df['category'].isin(selected_categories)]
        if selected_brands:
            filtered_df = filtered_df[filtered_df['brand'].isin(selected_brands)]
        filtered_df = filtered_df.copy()
        filtered_df['score'] = filtered_df.apply(lambda row: score_product(row, profile, weights), axis=1)
        recs = filtered_df.sort_values(by=['score', 'rating'], ascending=False).to_dict(orient='records')
        mode_lbl = "🔎 Filtered results"
    else:
        recs, mode = rec_agent.recommend(top_n=12)
        mode_lbl = "🎯 Personalized for you" if mode == "personalized" else "⭐ Top Rated"

    filter_bits = []
    if selected_categories:
        filter_bits.append(f"categories: {', '.join(selected_categories)}")
    if selected_brands:
        filter_bits.append(f"brands: {', '.join(selected_brands)}")
    filter_text = f" · Filtered by {' | '.join(filter_bits)}" if filter_bits else ""
    st.markdown(f'<div class="ssub">{mode_lbl} · {len(recs)} products · 110 item catalog{filter_text}</div>',
                unsafe_allow_html=True)

    if not recs:
        st.warning("No recommendations match the selected filters yet. Clear a filter or like more products in those categories or brands.")

    for row_start in range(0, len(recs), 3):
        cols = st.columns(3)
        for i, col in enumerate(cols):
            idx = row_start + i
            if idx >= len(recs): break
            p = recs[idx]
            score         = p.get('score', 0)
            current_price = tracker_agent.get_current_price(p['id'], p['price'])
            decision      = decision_agent.evaluate(p, score, current_price)
            explanation   = rec_agent.explain_recommendation(p, profile, score)

            with col:
                if decision['action'] == 'suggest_purchase':
                    badge = '<span class="badge b-buy">🔥 Buy Now</span>'
                elif decision['action'] == 'alert_price_drop':
                    badge = '<span class="badge b-drop">📉 Price Drop</span>'
                else:
                    badge = '<span class="badge b-rec">✨ Recommended</span>'

                tags_html   = ' '.join([f'<span class="tag">{t.strip()}</span>'
                                        for t in str(p['tags']).split(',')[:3]])
                price_color = "#f87171" if current_price < p['price'] else "#34d399"
                strike      = (f"<span style='color:#374151;font-size:.7rem;"
                               f"text-decoration:line-through;margin-left:6px'>₹{p['price']:,}</span>"
                               if current_price < p['price'] else "")

                st.markdown(f"""
                <div class="card">
                  {badge}
                  <div style="margin-top:10px">
                    <div class="p-brand">{p['brand']}</div>
                    <div class="p-name">{p['name']}</div>
                    <div class="p-cat">{p['category']}</div>
                  </div>
                  <div style="display:flex;align-items:baseline;gap:4px;margin:6px 0">
                    <span class="p-price" style="color:{price_color}">₹{current_price:,}</span>{strike}
                  </div>
                  <div class="p-rating">{'★'*int(p['rating'])}{'☆'*(5-int(p['rating']))} {p['rating']}</div>
                  <div style="margin-top:6px">{tags_html}</div>
                  <div class="p-reason">{explanation}</div>
                </div>
                """, unsafe_allow_html=True)

                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("👍", key=f"l_{p['id']}", help="Like"):
                        pref_agent.record_like(p); st.toast("Preference learned!", icon="👍"); st.rerun()
                with c2:
                    if st.button("👎", key=f"d_{p['id']}", help="Dislike"):
                        pref_agent.record_dislike(p); st.toast("Got it!", icon="👎"); st.rerun()
                with c3:
                    if st.button("📌", key=f"w_{p['id']}", help="Watchlist"):
                        pc = dict(p); pc['price'] = current_price
                        add_to_watchlist(pc); st.toast("Added to watchlist!", icon="📌")
                with c4:
                    if st.button("🛒", key=f"b_{p['id']}", help="Buy"):
                        pc = dict(p); pc['current_price'] = current_price
                        pc['decision_reason'] = decision['reason']
                        st.session_state.confirm_product = pc
                        log_event("DecisionAgent", "Buy Now triggered — awaiting user approval",
                                  level="alert", product_name=p['name'])
                        st.rerun()

# ════════════════════════════════════════════════════
# TAB 2 — SEARCH (with NL search)
# ════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="sh">Search Products</div>', unsafe_allow_html=True)

    # NL quick chips
    st.markdown("**Try natural language:**")
    chip_queries = [
        "wireless under ₹5000",
        "premium fitness gear",
        "gaming laptop",
        "budget smartphone",
        "home appliances",
        "running shoes Nike"
    ]
    chip_cols = st.columns(len(chip_queries))
    for i, chip in enumerate(chip_queries):
        with chip_cols[i]:
            if st.button(chip, key=f"chip_{i}"):
                st.session_state.nl_query = chip
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    query = st.text_input("", value=st.session_state.nl_query,
                          placeholder="🔍  e.g. 'noise cancelling headphones under ₹10000'",
                          key="search_box")

    if query != st.session_state.nl_query:
        st.session_state.nl_query = query

    if query:
        # Parse budget from NL query
        import re
        budget_match = re.search(r'₹?\s*(\d[\d,]*)', query)
        budget_filter = None
        if budget_match:
            budget_filter = int(budget_match.group(1).replace(',',''))

        # Clean query — remove price part for keyword search
        clean_q = re.sub(r'(under|below|within|upto|up to)?\s*₹?\s*\d[\d,]*', '', query).strip()
        if not clean_q:
            clean_q = query

        results = rec_agent.search(clean_q)

        # Apply budget filter from NL
        if budget_filter and budget_filter > 100:
            results = [r for r in results if r['price'] <= budget_filter]

        if not results:
            st.warning(f"No products found for **'{query}'**. Try different keywords.")
        else:
            category_matches = sorted({p['category'] for p in results})
            category_note = f"Category: {', '.join(category_matches)} · " if len(category_matches) == 1 else ""
            st.markdown(f'<div class="ssub">{len(results)} results · '
                        f'{category_note}'
                        f'{"Budget filtered ≤ ₹"+str(budget_filter)+"," if budget_filter else "No price filter"}'
                        f'</div>', unsafe_allow_html=True)

            profile = load_profile()
            for row_start in range(0, len(results), 3):
                cols = st.columns(3)
                for i, col in enumerate(cols):
                    idx = row_start + i
                    if idx >= len(results): break
                    p = results[idx]
                    current_price = tracker_agent.get_current_price(p['id'], p['price'])
                    price_color   = "#f87171" if current_price < p['price'] else "#34d399"
                    strike        = (f"<span style='color:#374151;font-size:.7rem;"
                                     f"text-decoration:line-through'>₹{p['price']:,}</span>"
                                     if current_price < p['price'] else "")
                    tags_html     = ' '.join([f'<span class="tag">{t.strip()}</span>'
                                             for t in str(p['tags']).split(',')[:3]])

                    with col:
                        st.markdown(f"""
                        <div class="card">
                          <span class="badge b-nl">🔍 Search Result</span>
                          <div style="margin-top:10px">
                            <div class="p-brand">{p['brand']}</div>
                            <div class="p-name">{p['name']}</div>
                            <div class="p-cat">{p['category']}</div>
                          </div>
                          <div style="display:flex;align-items:baseline;gap:6px;margin:6px 0">
                            <span class="p-price" style="color:{price_color}">₹{current_price:,}</span>{strike}
                          </div>
                          <div class="p-rating">{'★'*int(p['rating'])}{'☆'*(5-int(p['rating']))} {p['rating']}</div>
                          <div style="margin-top:6px">{tags_html}</div>
                        </div>
                        """, unsafe_allow_html=True)

                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.button("👍", key=f"sl_{p['id']}"):
                                pref_agent.record_like(p); st.toast("Liked!", icon="👍"); st.rerun()
                        with c2:
                            if st.button("📌", key=f"sw_{p['id']}"):
                                pc = dict(p); pc['price'] = current_price
                                add_to_watchlist(pc); st.toast("Watching!", icon="📌")
                        with c3:
                            if st.button("🛒", key=f"sb_{p['id']}"):
                                pc = dict(p); pc['current_price'] = current_price
                                st.session_state.confirm_product = pc; st.rerun()
    else:
        st.markdown("""
        <div style="text-align:center;padding:50px 20px;color:#374151">
          <div style="font-size:2.5rem;margin-bottom:10px">🔍</div>
          <div style="font-family:'Syne',sans-serif;font-size:1.1rem;color:#4b5563">
            Search across 110 products</div>
          <div style="font-size:.82rem;margin-top:6px">
            Try natural language: "wireless earbuds under ₹3000" or "premium running shoes"</div>
        </div>
        """, unsafe_allow_html=True)


# ════════════════════════════════════════════════════
# TAB 3 — PRICE TRACKER
# ════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="sh">📈 Price Tracker — 30 Day History</div>', unsafe_allow_html=True)
    st.markdown('<div class="ssub">Watching your saved products for price drops</div>',
                unsafe_allow_html=True)

    profile   = load_profile()
    watchlist = profile.get('watchlist', [])

    if not watchlist:
        st.markdown("""
        <div style="text-align:center;padding:60px;color:#374151">
          <div style="font-size:2.5rem">📌</div>
          <div style="font-family:'Syne',sans-serif;font-size:1.1rem;color:#4b5563;margin-top:8px">
            Watchlist is empty</div>
          <div style="font-size:.82rem;margin-top:4px">
            Click 📌 on any product to start tracking its price</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        alerts = tracker_agent.check_alerts(watchlist)
        if alerts:
            st.markdown("### 🚨 Price Drop Alerts")
            for a in alerts:
                st.markdown(f"""
                <div class="alert-drop">
                  <div style="font-family:'Syne',sans-serif;font-weight:700;color:#f87171">
                    📉 {a['product_name']}</div>
                  <div style="font-size:.82rem;color:#9ca3af;margin-top:3px">
                    Dropped <strong style="color:#f87171">{a['drop_percent']}%</strong> —
                    ₹{a['original_price']:,} → <strong style="color:#34d399">₹{a['current_price']:,}</strong>
                    &nbsp;·&nbsp; Save ₹{a['savings']:,}
                  </div>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("---")

        all_df = load_products()
        for item in watchlist:
            pid  = item['id']
            row  = all_df[all_df['id'] == pid]
            if row.empty: continue
            product    = row.iloc[0].to_dict()
            base_price = product['price']
            history    = tracker_agent.generate_price_history(pid, base_price)
            curr       = history[-1]['price']
            lo         = tracker_agent.get_lowest_price(pid, base_price)
            hi         = tracker_agent.get_highest_price(pid, base_price)
            avg        = tracker_agent.get_avg_price(pid, base_price)
            at_add     = item.get('price_at_add', base_price)
            chg_pct    = ((curr - at_add) / at_add * 100) if at_add else 0

            with st.expander(
                f"**{item['name']}** — ₹{curr:,}  "
                f"{'📉' if chg_pct < -2 else '📈' if chg_pct > 2 else '→'}  "
                f"({chg_pct:+.1f}%)",
                expanded=True
            ):
                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Current",   f"₹{curr:,}",    f"{chg_pct:+.1f}%")
                m2.metric("Added At",  f"₹{at_add:,}")
                m3.metric("30d Low",   f"₹{lo:,}")
                m4.metric("30d High",  f"₹{hi:,}")
                m5.metric("30d Avg",   f"₹{avg:,}")

                chart_df = pd.DataFrame(history).rename(columns={"date":"Date","price":"Price ₹"})
                chart_df = chart_df.set_index("Date")
                st.line_chart(chart_df, color="#a78bfa", height=200)

                ca, cb, cc = st.columns([1, 1, 4])
                with ca:
                    if st.button("🔄", key=f"ref_{pid}", help="Refresh price"):
                        np = tracker_agent.refresh_price(pid, base_price, item['name'])
                        st.toast(f"Updated: ₹{np:,}", icon="🔄"); st.rerun()
                with cb:
                    if st.button("🛒", key=f"wbuy_{pid}", help="Buy now"):
                        pc = dict(product); pc['current_price'] = curr
                        st.session_state.confirm_product = pc; st.rerun()
                with cc:
                    if st.button("🗑️ Remove from Watchlist", key=f"rem_{pid}"):
                        remove_from_watchlist(pid); st.toast("Removed", icon="🗑️"); st.rerun()


# ════════════════════════════════════════════════════
# TAB 4 — AGENT LOG
# ════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="sh">🤖 Agent Activity Feed</div>', unsafe_allow_html=True)
    st.markdown('<div class="ssub">Real-time log of what every agent is doing</div>',
                unsafe_allow_html=True)

    log_entries = load_log()

    col_stats, _ = st.columns([3, 1])
    with col_stats:
        agents_active = list({e['agent'] for e in log_entries})
        c1,c2,c3 = st.columns(3)
        c1.metric("Total Events",  len(log_entries))
        c2.metric("Agents Active", len(agents_active))
        c3.metric("Alerts",        sum(1 for e in log_entries if e.get('level') == 'alert'))

    st.markdown("<br>", unsafe_allow_html=True)

    # Filter
    filter_agent = st.selectbox("Filter by agent",
                                ["All"] + sorted(set(e['agent'] for e in log_entries)),
                                key="log_filter")
    filtered = log_entries if filter_agent == "All" else \
               [e for e in log_entries if e['agent'] == filter_agent]

    if not filtered:
        st.info("No agent activity yet. Start browsing and liking products!")
    else:
        for entry in filtered[:50]:
            cls      = f"log-{entry.get('level','info')}"
            prod_html = f'<div class="log-prod">📦 {entry["product"]}</div>' if entry.get("product") else ""
            date_str  = entry.get('date','')
            st.markdown(f"""
            <div class="log-entry {cls}">
              <span class="log-icon">{entry['icon']}</span>
              <div class="log-body">
                <div class="log-agent">{entry['agent']}</div>
                <div class="log-msg">{entry['message']}</div>
                {prod_html}
              </div>
              <span class="log-time">{date_str} {entry['timestamp']}</span>
            </div>
            """, unsafe_allow_html=True)

    if log_entries:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Log"):
            clear_log(); st.rerun()


# ════════════════════════════════════════════════════
# TAB 5 — PROFILE
# ════════════════════════════════════════════════════
with tab5:
    st.markdown('<div class="sh">🗂️ Your Profile</div>', unsafe_allow_html=True)
    profile = load_profile()

    c1,c2,c3,c4,c5 = st.columns(5)
    for col, (val, lbl) in zip([c1,c2,c3,c4,c5], [
        (len(profile.get('preferred_categories',[])), "Categories"),
        (len(profile.get('preferred_brands',[])),     "Brands"),
        (len(profile.get('liked_tags',[])),           "Liked Tags"),
        (len(profile.get('interaction_history',[])),  "Interactions"),
        (len(profile.get('purchase_history',[])),     "Purchases"),
    ]):
        col.markdown(f'<div class="mbox"><div class="mval">{val}</div>'
                     f'<div class="mlbl">{lbl}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    left, right = st.columns(2)

    with left:
        st.markdown("**🏷️ Preferred Categories**")
        cats = profile.get('preferred_categories',[])
        st.markdown(' '.join([f'<span class="badge b-rec">{c}</span>' for c in cats])
                    if cats else "<span style='color:#374151'>None set</span>",
                    unsafe_allow_html=True)

        st.markdown("<br>**🏢 Preferred Brands**")
        brands = profile.get('preferred_brands',[])
        st.markdown(' '.join([f'<span class="badge b-buy">{b}</span>' for b in brands])
                    if brands else "<span style='color:#374151'>None set</span>",
                    unsafe_allow_html=True)

        st.markdown(f"<br>**💰 Budget:** ₹{profile.get('budget_max',50000):,}",
                    unsafe_allow_html=True)

    with right:
        st.markdown("**❤️ Liked Tags**")
        liked = profile.get('liked_tags',[])
        st.markdown(' '.join([f'<span class="tag">{t}</span>' for t in liked[:20]])
                    if liked else "<span style='color:#374151'>Like products to build profile</span>",
                    unsafe_allow_html=True)

        st.markdown("<br>**👎 Disliked Tags**")
        dis = profile.get('disliked_tags',[])
        st.markdown(' '.join([f'<span class="badge b-drop">{t}</span>' for t in dis[:12]])
                    if dis else "<span style='color:#374151'>None filtered yet</span>",
                    unsafe_allow_html=True)

    # Purchase history
    purchases = profile.get('purchase_history',[])
    if purchases:
        st.markdown("<br>**🛒 Purchase History (Simulated)**")
        ph_df = pd.DataFrame(list(reversed(purchases)))
        ph_df['timestamp'] = pd.to_datetime(ph_df['timestamp']).dt.strftime('%b %d, %H:%M')
        ph_df = ph_df.rename(columns={
            "product_name":"Product","price":"Price (₹)","timestamp":"Time"
        })[["Product","Price (₹)","Time"]]
        st.dataframe(ph_df, use_container_width=True, hide_index=True)

    # Interaction history
    history = profile.get('interaction_history',[])
    if history:
        st.markdown("<br>**🕐 Recent Interactions**")
        recent = list(reversed(history[-15:]))
        df_h   = pd.DataFrame(recent)[['product_name','action','timestamp']]
        df_h.columns = ['Product','Action','Time']
        df_h['Time']   = pd.to_datetime(df_h['Time']).dt.strftime('%b %d, %H:%M')
        icons  = {'liked':'👍','disliked':'👎','viewed':'👁️'}
        df_h['Action'] = df_h['Action'].map(lambda x: f"{icons.get(x,'')} {x}")
        st.dataframe(df_h, use_container_width=True, hide_index=True)
