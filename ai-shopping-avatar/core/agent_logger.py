import json
import os
from datetime import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'memory', 'agent_log.json')

AGENT_ICONS = {
    "PreferenceAgent":      "🧠",
    "RecommendationAgent":  "📊",
    "PriceTrackerAgent":    "📈",
    "DecisionAgent":        "🤖",
    "ExecutionAgent":       "⚡",
    "NotificationAgent":    "🔔",
    "CriticAgent":          "🎯",
    "System":               "⚙️",
}

def load_log():
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            return json.load(f)
    return []

def save_log(log):
    with open(LOG_PATH, 'w') as f:
        json.dump(log, f, indent=2)

def log_event(agent: str, message: str, level: str = "info", product_name: str = None):
    """
    level: info | success | warning | alert | action
    """
    log = load_log()
    entry = {
        "agent": agent,
        "icon": AGENT_ICONS.get(agent, "⚙️"),
        "message": message,
        "level": level,
        "product": product_name,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "date": datetime.now().strftime("%b %d")
    }
    log.insert(0, entry)  # newest first
    log = log[:100]       # keep last 100 events
    save_log(log)

def clear_log():
    save_log([])
