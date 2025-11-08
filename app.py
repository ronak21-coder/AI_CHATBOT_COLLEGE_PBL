from flask import Flask, render_template, request, jsonify
from datetime import datetime
import json
import os
import re

app = Flask(__name__)

# ------------------------------
# Load events knowledge base
# ------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'events.json')

with open(DATA_PATH, 'r', encoding='utf-8') as f:
    EVENTS = json.load(f)

# Precompute lowercase fields for matching
for ev in EVENTS:
    ev["_title"] = ev["title"].lower()
    ev["_desc"] = ev["description"].lower()
    ev["_tags"] = [t.lower() for t in ev.get("tags", [])]

# ------------------------------
# Simple NLP helpers
# ------------------------------
STOPWORDS = set("""
a an the is are was were be been being do does did to for of on in at by with from and or as about into over after before between during under again further then once here there when where why how all any both each few more most other some such no nor not only own same so than too very can will just don don should now i you he she it we they me my our your their what which who whom this that these those
afterwards also although among amongst am aren because couldn couldn didn down hadn hasn haven having isn let might must needn ought shouldn wasn weren won wouldn
""".split())

SYNONYMS = {
    # intent synonyms
    "when": {"when", "date", "time", "schedule", "timing", "day", "today", "tomorrow"},
    "where": {"where", "venue", "location", "place", "hall", "room", "auditorium", "block"},
    "register": {"register", "registration", "apply", "enroll", "signup", "sign-up", "fees", "cost"},
    "what": {"what", "info", "details", "about", "describe", "description"},
    "who": {"who", "speaker", "host", "club", "department", "organizer"},
    "next": {"next", "upcoming", "soon", "latest", "nearest"},
}

# map of common words -> canonical
CANONICAL = {
    "venue": "where", "location": "where", "place": "where", "hall": "where",
    "when": "when", "date": "when", "time": "when", "timing": "when", "schedule": "when",
    "register": "register", "registration": "register", "signup": "register", "fees": "register",
    "speaker": "who", "host": "who", "club": "who", "organizer": "who",
    "about": "what", "details": "what",
    "upcoming": "next", "latest": "next", "soon": "next",
}

TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")

def tokenize(text: str):
    tokens = [t.lower() for t in TOKEN_RE.findall(text)]
    return [t for t in tokens if t not in STOPWORDS]


def normalize(tokens):
    norm = []
    for t in tokens:
        if t in CANONICAL:
            norm.append(CANONICAL[t])
        else:
            norm.append(t)
    return norm


def detect_intents(tokens):
    """Return a set of intents mentioned in the tokens."""
    intents = set()
    for intent, syns in SYNONYMS.items():
        if any(s in tokens for s in syns):
            intents.add(intent)
    # also include canonical hits
    for t in tokens:
        if t in CANONICAL:
            intents.add(CANONICAL[t])
    return intents


def score_event(query_tokens, ev):
    """Simple keyword overlap score across title, description, and tags."""
    bag = set(query_tokens)
    score = 0
    textbag = set(ev["_title"].split()) | set(ev["_desc"].split()) | set(ev["_tags"])
    for t in bag:
        if t in textbag:
            score += 2
        # partial match (substring) for robustness, avoid too many hits
        else:
            if any((t in w) and len(t) > 3 for w in textbag):
                score += 1
    # boost upcoming events
    try:
        d = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        if d >= datetime.now().date():
            score += 1
    except Exception:
        pass
    return score


def find_best_event(query_tokens):
    ranked = sorted(EVENTS, key=lambda e: score_event(query_tokens, e), reverse=True)
    best = ranked[0]
    # if score is very low, treat as unknown
    if score_event(query_tokens, best) < 2:
        return None
    return best


# ------------------------------
# Response generators by intent
# ------------------------------

def fmt_datetime(ev):
    try:
        d = datetime.strptime(ev["date"], "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        d = ev["date"]
    t = ev.get("time", "")
    return d if not t else f"{d} at {t}"


def reply_when(ev):
    return f"📅 {ev['title']} is scheduled on {fmt_datetime(ev)}."


def reply_where(ev):
    return f"📍 Venue: {ev['location']} (for {ev['title']})."


def reply_register(ev):
    fee = f"Fee: ₹{ev['fee']}" if ev.get('fee') else ""
    link = ev.get("registration_link") or "Registration link will be announced soon."
    parts = [f"📝 Registration for {ev['title']}", fee, f"Link: {link}"]
    return " | ".join([p for p in parts if p])


def reply_who(ev):
    org = ev.get('organizer', 'the organizing team')
    return f"👥 Organized by {org} for {ev['title']}."


def reply_what(ev):
    return f"ℹ️ {ev['title']}: {ev['description']}"


def reply_next():
    today = datetime.now().date()
    upcoming = []
    for ev in EVENTS:
        try:
            d = datetime.strptime(ev["date"], "%Y-%m-%d").date()
            if d >= today:
                upcoming.append((d, ev))
        except Exception:
            continue
    upcoming.sort(key=lambda x: x[0])
    if not upcoming:
        return "There are no upcoming events right now. Please check back later."
    top = upcoming[:3]
    lines = ["🗓️ Upcoming events:"]
    for d, ev in top:
        lines.append(f"• {ev['title']} — {d.strftime('%d %b %Y')} at {ev.get('time','')} — {ev['location']}")
    return "\n".join(lines)


INTENT_TO_HANDLER = {
    "when": reply_when,
    "where": reply_where,
    "register": reply_register,
    "who": reply_who,
    "what": reply_what,
}


# ------------------------------
# Core chatbot logic
# ------------------------------

def generate_response(user_text: str) -> str:
    if not user_text or not user_text.strip():
        return "Please type a question about a college event."

    tokens = normalize(tokenize(user_text))
    intents = detect_intents(tokens)

    # Small talk shortcuts
    if any(w in tokens for w in ["hello", "hi", "hey"]):
        return "Hi! Ask me about college events — try 'when is the tech fest?' or 'how to register for hackathon?'"

    if "next" in intents:
        return reply_next()

    # Try to locate the most relevant event
    ev = find_best_event(tokens)
    if not ev:
        # fallback to upcoming list as a helpful response
        return "I couldn't find that event. Try including the event name (e.g., 'tech fest', 'hackathon').\n\n" + reply_next()

    # If user asked a specific intent, answer that; else give a compact summary
    for intent in ["when", "where", "register", "who", "what"]:
        if intent in intents:
            return INTENT_TO_HANDLER[intent](ev)

    # default concise card
    return (
        f"{ev['title']} — {fmt_datetime(ev)} at {ev['location']}. "
        f"Register: {ev.get('registration_link', 'TBA')}\n"
        f"About: {ev['description']}"
    )


# ------------------------------
# Routes
# ------------------------------
@app.route('/')
def home():
    return render_template('index.html')


@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get('message', '')
    reply = generate_response(message)
    return jsonify({"reply": reply})


if __name__ == '__main__':
    # Use host=0.0.0.0 to allow LAN access for demos; remove if not needed.
    app.run(host='0.0.0.0', port=5000, debug=True)
