# 🏛️ CM Yuva Analytics — AI Data Chatbot

An intelligent AI-powered chatbot for analyzing the CM Yuva (Chief Minister's Youth Entrepreneurship Scheme) datasets from Uttar Pradesh. Ask natural language questions about loan applications, certifications, fraud cases, district performance, and more.

---

## 📊 Datasets Supported

| Dataset | Records | Description |
|---------|---------|-------------|
| `cmyuva-loan-applied-data.xlsx` | 30,000+ | Loan applications with status, district, bank, CIBIL, etc. |
| `cmyuva-certification-data.xlsx` | 55,512 | Training certification records |
| `cm-yuva-fraud-data.xlsx` | 59 | Fraud investigation cases |

---

## 🚀 Quick Start

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Place Excel Files

Copy all three `.xlsx` files into the project root directory:
```
cmyuva-chatbot/
├── cmyuva-loan-applied-data.xlsx   ← place here
├── cmyuva-certification-data.xlsx  ← place here
├── cm-yuva-fraud-data.xlsx         ← place here
├── setup_data.py
├── requirements.txt
├── backend/
└── frontend/
```
### Step 2.1 — Run training script (creates cmyuva model):
# ollama_training/train_model.sh


### Step 3: Process Data (Run Once)

```bash
python setup_data.py
```

This converts Excel files to optimized JSON (takes ~2-3 minutes for large files).

### Step 4: Start the Backend

```bash
python backend/app.py
```

Server starts at: `http://localhost:5000`

### Step 5: Open the Frontend

Open `frontend/index.html` in your browser (double-click or use a local server):

```bash
# Option A: Direct open
open frontend/index.html

# Option B: Python local server
cd frontend && python -m http.server 3000
# Then visit: http://localhost:3000
```

---

## 💬 Supported Queries

### 📋 Loan Analytics
- "How many total loan applications are there?"
- "How many members from Agra have taken a loan?"
- "Give me the names of all applicants from Lucknow"
- "Show district-wise loan application count"
- "What is the loan approval rate?"
- "How many loans were sanctioned vs rejected?"
- "Show me gender-wise applicant breakdown"
- "What is the average project cost?"
- "Show industry-wise loan distribution"
- "Which banks have the most loan applications?"
- "Show CIBIL score analysis"
- "What is the qualification breakdown of applicants?"
- "Show urban vs rural applicant distribution"

### 📉 Rejection & Approval Analysis
- "What is the overall rejection rate?"
- "Which district has the most rejected loans?"
- "Show me rejection analysis"
- "How many loans were rejected by bank vs DIC?"

### 🔽 Funnel Analysis
- "Give me the funnel analysis from applied to approved"
- "Show the complete pipeline from certification to disbursement"
- "What percentage of applicants got their margin money released?"

### 🎓 Certification Analytics
- "How many certifications have been issued?"
- "Show month-wise certification trends"
- "Which district has the most certifications?"
- "Show certification by referral role"
- "How many people are certified in Varanasi?"

### 🚨 Fraud Analysis
- "Show fraud cases by district"
- "How many fraud cases are there?"
- "Which districts have fraud risk?"
- "Are businesses running as per DPR in fraud cases?"

### 🏆 Performance Rankings
- "Which districts are high performing?"
- "Which districts are underperforming?"
- "Show me district performance rankings"
- "Compare approval rates across districts"

### 💡 Strategic Insights
- "What are strategic insights for policy improvement?"
- "Give me an overview of the entire scheme"
- "What patterns do you see in the data?"

---

## 🏗️ Architecture

```
cmyuva-chatbot/
├── backend/
│   ├── app.py              # Flask REST API server
│   ├── analytics_engine.py # Pure data analysis layer
│   └── ai_handler.py       # Claude AI integration
├── frontend/
│   └── index.html          # Beautiful single-page chatbot UI
├── data/                   # Generated JSON data (after setup)
│   ├── loan_data.json
│   ├── cert_data.json
│   └── fraud_data.json
├── setup_data.py           # One-time data processing script
└── requirements.txt
```

### How It Works

1. **User** types a natural language question in the frontend
2. **Frontend** sends query + conversation history to Flask API
3. **AI Handler** analyzes the query intent to determine which analytics to run
4. **Analytics Engine** computes the relevant statistics from JSON data
5. **Claude AI** receives the analytics results and formulates an intelligent, insightful response
6. **Frontend** displays the formatted response with markdown rendering

---

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/health` | GET | Dataset status and record counts |
| `POST /api/chat` | POST | Process a user query |
| `GET /api/suggestions` | GET | Sample questions for the UI |

### Chat API Request Format
```json
{
  "query": "How many loans from Agra?",
  "history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

---

## ⚙️ Configuration

The Anthropic API key is automatically handled by the Claude.ai environment. If running standalone, add your key:

In `backend/ai_handler.py`, add to the `requests.post()` headers:
```python
"x-api-key": "your-anthropic-api-key-here",
"anthropic-version": "2023-06-01"
```

---

## 📋 Sample Outputs

**Query:** "How many members from Agra have taken a loan?"
> There are **7,406 loan applications** from Agra district. Breaking this down by status:
> - ✅ Margin Money Released: 2,847 (38.4%)
> - ❌ Rejected by Bank: 2,012 (27.2%)
> - 🏦 Forwarded to Bank: 1,103 (14.9%)
> - 📋 Loan Sanctioned: 589 (7.9%)

**Query:** "Show me fraud analysis by district"
> I found **59 fraud investigation cases** across 28 districts. The highest concentration is in **Auraiya** (9 cases), followed by **Basti** (5 cases) and **Hardoi** (4 cases). Notably, **85.5% of investigated businesses** (51 out of 59) are **not running as per their DPR/business plan**...

---

## 🛡️ Responsible AI Notes

- Data is anonymized (Aadhar, mobile numbers masked)
- No personal data leaves your local machine
- AI responses are grounded in actual dataset analytics
- Fraud analysis is for policy use only

---

*Built for CM Yuva Scheme Analytics · Uttar Pradesh Government Initiative*
