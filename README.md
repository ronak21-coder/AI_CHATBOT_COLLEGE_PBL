## File: README (How to Run & Notes)
```text
# AI Chatbot for College Info – PBL (NLP + Flask)

## 1) Prerequisites
- Python 3.9+

## 2) Project structure
.
├── app.py
├── data/
│ └── events.json
├── static/
│ └── style.css
└── templates/
└── index.html

## 3) Install dependencies
This project uses only Flask (no heavy ML libs), so it's classroom-friendly.

pip install flask

## 4) Run
python app.py
Open: http://127.0.0.1:5000

## 5) NLP Approach (explain in report)
- Tokenization with regex; stopword removal
- Synonym normalization to canonical intents (when/where/register/who/what/next)
- Intent detection via keyword sets
- Event retrieval with simple keyword-overlap scoring (title + description + tags) and upcoming-boost
- Templated replies per intent; graceful fallback lists the next 3 events

## 6) Try sample questions
- "when is the tech fest?"
- "where is hackathon venue?"
- "how to register for machine learning workshop? what are the fees?"
- "upcoming events"
- "who is organizing sports meet?"

## 7) Customize for your college
- Edit `data/events.json` and add real events.
- Update synonyms/intents in `app.py` if you need more question types (e.g., duration, eligibility).
- For multilingual support, add Hindi synonyms and titles/tags.

## 8) Optional enhancements (future work section)
- Replace keyword scoring with TF-IDF + cosine similarity (scikit-learn)
- Add context memory for follow-up questions (e.g., pronouns referring to last event)
- Admin panel to manage events
- Deploy to Render/Heroku/PythonAnywhere

## 9) Academic mapping to NLP
- Text normalization, stopword removal
- Synonym mapping (lexical semantics)
- Intent classification (rule-based)
- Information retrieval over a domain KB
- NLG via templated responses
