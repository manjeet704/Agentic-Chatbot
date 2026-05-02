from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
import re
from analytics_engine import AnalyticsEngine
from ai_handler import AIHandler

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, 'frontend')

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='')
CORS(app)

DATA_DIR = os.path.join(BASE_DIR, 'data')

# Load data once on startup
print("Loading datasets...")
engine = AnalyticsEngine(DATA_DIR)
ai = AIHandler(engine)
print("Ready!")

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'datasets': engine.get_summary()})

@app.route('/api/chat', methods=['POST'])
def chat():
    body = request.json
    query = body.get('query', '').strip()
    history = body.get('history', [])
    if not query:
        return jsonify({'error': 'Empty query'}), 400
    result = ai.process(query, history)
    return jsonify(result)

@app.route('/api/suggestions', methods=['GET'])
def suggestions():
    return jsonify({'suggestions': [
        "How many loan applications are there in total?",
        "Show me district-wise loan application count",
        "What is the loan approval rate?",
        "Which district has the most rejected loans?",
        "How many members from Agra have taken a loan?",
        "Show fraud cases by district",
        "What is the certification completion rate?",
        "Show month-wise certification trends",
        "Give me the funnel analysis from applied to approved",
        "Which districts are high performing?",
        "What are the top rejection reasons?",
        "Show me gender-wise applicant breakdown",
        "How many loans were sanctioned vs rejected?",
        "Show industry-wise loan distribution",
        "What is the average project cost?"
    ]})


@app.route('/api/ai-status', methods=['GET'])
def ai_status():
    import requests as req
    # Check Ollama
    try:
        r = req.get('http://localhost:11434/api/tags', timeout=2)
        if r.status_code == 200:
            models = [m['name'] for m in r.json().get('models', [])]
            return jsonify({'engine': 'ollama', 'models': models, 'status': 'online'})
    except:
        pass
    # Check Anthropic key
    if ANTHROPIC_API_KEY:
        return jsonify({'engine': 'anthropic', 'status': 'online'})
    return jsonify({'engine': 'builtin', 'status': 'online'})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
