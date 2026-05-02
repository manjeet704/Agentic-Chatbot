import json
import os
import re
import requests
from functools import lru_cache

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OLLAMA_URL        = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL      = os.environ.get("OLLAMA_MODEL", "cmyuva")   # our fine-tuned model

# ── Chatbot identity ──────────────────────────────────────────────────────────
BOT_NAME = "CM Yuva Analytics Assistant"
BOT_VERSION = "v4"

DATA_CONTEXT = """
You are analyzing the CM Yuva (Chief Minister Youth Entrepreneurship) scheme data from Uttar Pradesh, India.

DATASET FACTS (use ONLY these numbers — never invent):
- Loan Applications: 30,000 records across 6 districts
- Districts: Agra (7,406), Aligarh (6,984), Ambedkar Nagar (6,264), Amroha (5,065), Amethi (3,746), Auraiya (535)
- Certifications: 55,512 records
- Fraud Cases: 59 investigated cases
- Loan Statuses: Reject by Bank (11,620), Margin Money Released (8,118), Forwarded to Bank (3,393),
  Sanctioned (1,299), Revert by DIC (2,928), Disbursed (781), Reject after Sanction (1,073),
  Rejected by DIC (329), Forwarded to DIC (152), MM Claimed (305)
- Overall Rejection Rate: 39.8%
- Sanction Rate: 34%
- Disbursal Rate: 2.6%
- Top Fraud Districts: Auraiya (9), Basti (5), Hardoi (4), Lalitpur (3), Lakhimpur (3)
- 86% of fraud-investigated businesses NOT running as per DPR
- District Loan Amounts: Agra highest (₹367 Cr project cost), Auraiya lowest (₹25.8 Cr)
- Certifications by Referral: District Manager (34,940), Self (9,323), Channel Partner (7,309)
"""

SYSTEM_PROMPT = """You are """ + BOT_NAME + """, a smart AI assistant for the CM Yuva scheme in Uttar Pradesh, India.

PERSONALITY: Friendly, professional, concise. Always respond in the same language the user uses.

STRICT RULES:
1. GREETINGS (hi/hello/good morning/namaste/hey): Respond warmly. Say your name. List what you can help with. NO DATA shown.
2. YOUR NAME/IDENTITY: You are "CM Yuva Analytics Assistant". Tell them this clearly.
3. OUT OF SCOPE (weather/jokes/maths/cricket/movies etc): Politely say you only handle CM Yuva scheme data.
4. DATA QUESTIONS: Use ONLY the data context below. Never invent numbers.
5. UNKNOWN DATA: If asked something not in context (e.g. city not in dataset), say exactly: "That information is not available in the current dataset."
6. LOWEST/HIGHEST: Always answer these — they ARE in the data.
7. Keep answers SHORT and CLEAR. Use bullet points for lists.
8. If analytics JSON is provided, use those EXACT numbers in your response.

""" + DATA_CONTEXT


class AIHandler:
    def __init__(self, engine):
        self.engine = engine
        self._ollama_available = None  # None = not yet checked

    def process(self, query, history):
        intent = self._detect_intent(query)

        if intent in ("greeting", "identity", "out_of_scope"):
            answer = self._call_llm(query, {}, history, intent)
            return {'answer': answer, 'query': query}

        analytics = self._gather_analytics(query)
        answer = self._call_llm(query, analytics, history, intent)
        return {'answer': answer, 'analytics': analytics, 'query': query}

    # ── INTENT DETECTION ──────────────────────────────────────────────────────
    def _detect_intent(self, query):
        q = query.lower().strip()

        identity_words = ['your name', 'who are you', 'what are you', 'introduce yourself',
                          'tum kaun', 'aap kaun', 'tumhara naam', 'what is your name',
                          'whats your name', 'tell me about yourself']
        if any(p in q for p in identity_words):
            return "identity"

        greeting_patterns = [
            r'^\s*(hi|hello|hey|yo)\b',
            r'\bgood\s+(morning|afternoon|evening|night)\b',
            r'\b(namaste|namaskar|howdy|greetings|sup)\b',
            r'^how are (you|u)\b',
            r'^what\'?s up\b',
        ]
        if any(re.search(p, q) for p in greeting_patterns):
            # Only treat as greeting if no data keywords present
            data_words = ['loan', 'certif', 'fraud', 'district', 'agra', 'aligarh',
                          'reject', 'approv', 'sanction', 'gender', 'bank', 'amount',
                          'how many', 'count', 'list', 'show', 'which', 'total']
            if not any(w in q for w in data_words):
                return "greeting"

        out_of_scope = ['weather', 'cricket', 'ipl', 'movie', 'film', 'joke', 'funny',
                        'what is 2', 'capital of', 'president of', 'prime minister',
                        'recipe', 'cook', 'song', 'music', 'news', 'stock', 'bitcoin',
                        'whatsapp', 'instagram', 'facebook', 'who invented', 'history of']
        if any(p in q for p in out_of_scope):
            return "out_of_scope"

        return "data_query"

    # ── LLM CALL ─────────────────────────────────────────────────────────────
    def _call_llm(self, query, analytics, history, intent):
        context = ""
        if analytics:
            context = "\n\nANALYTICS DATA (use these exact numbers):\n" + json.dumps(analytics, indent=2, default=str)

        messages = []
        for h in history[-4:]:
            messages.append({"role": h['role'], "content": h['content']})
        messages.append({"role": "user", "content": query + context})

        # 1. Try Ollama (local fine-tuned model)
        if self._check_ollama():
            answer = self._call_ollama(messages)
            if answer:
                return answer

        # 2. Try Anthropic API
        if ANTHROPIC_API_KEY:
            answer = self._call_anthropic(messages)
            if answer:
                return answer

        # 3. Fast built-in rule engine
        return self._builtin_answer(query, analytics, intent)

    def _check_ollama(self):
        """Check Ollama availability once, cache result for 60s."""
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            r = requests.get(OLLAMA_URL + "/api/tags", timeout=2)
            self._ollama_available = r.status_code == 200
        except:
            self._ollama_available = False
        return self._ollama_available

    def _call_ollama(self, messages):
        try:
            full_prompt = SYSTEM_PROMPT + "\n\nConversation:\n"
            for m in messages:
                role = "User" if m['role'] == 'user' else "Assistant"
                full_prompt += role + ": " + m['content'] + "\n"
            full_prompt += "Assistant:"

            resp = requests.post(
                OLLAMA_URL + "/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": full_prompt,
                      "stream": False, "options": {"temperature": 0.2, "num_predict": 500}},
                timeout=45
            )
            if resp.status_code == 200:
                text = resp.json().get('response', '').strip()
                if text and len(text) > 10:
                    return text
        except:
            self._ollama_available = False
        return None

    def _call_anthropic(self, messages):
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"Content-Type": "application/json",
                         "x-api-key": ANTHROPIC_API_KEY,
                         "anthropic-version": "2023-06-01"},
                json={"model": "claude-haiku-4-5-20251001", "max_tokens": 600,
                      "system": SYSTEM_PROMPT, "messages": messages},
                timeout=20
            )
            data = resp.json()
            if data.get('content'):
                return data['content'][0]['text']
        except:
            pass
        return None

    # ── SMART BUILT-IN ANSWER ENGINE ─────────────────────────────────────────
    def _builtin_answer(self, query, analytics, intent):
        q = query.lower()

        if intent == "identity":
            return ("I'm the **CM Yuva Analytics Assistant** — an AI-powered chatbot built to help you "
                    "explore data from the CM Yuva (Chief Minister's Youth Entrepreneurship) scheme "
                    "in Uttar Pradesh.\n\n"
                    "I can help you with:\n"
                    "- Loan application counts, statuses, and amounts by district\n"
                    "- Applicant names and details\n"
                    "- Rejection and approval analysis\n"
                    "- Certification statistics and trends\n"
                    "- Fraud investigation insights\n"
                    "- District performance rankings\n\n"
                    "What would you like to know?")

        if intent == "greeting":
            import random
            greetings = [
                "Hello! I'm the **CM Yuva Analytics Assistant**. I can help you explore loan, certification, and fraud data from the CM Yuva scheme in UP.\n\nTry asking:\n- \"How many loans from Agra?\"\n- \"Which district has lowest loan amount?\"\n- \"Show fraud analysis\"",
                "Hi there! Great to see you. I'm here to help you analyze the CM Yuva scheme data — loans, certifications, fraud, districts, and more.\n\nWhat would you like to know?",
                "Good day! I'm the CM Yuva Analytics Assistant. Ask me anything about the scheme's loan applications, certification data, or fraud investigations!",
            ]
            return random.choice(greetings)

        if intent == "out_of_scope":
            return ("I'm specialized in CM Yuva scheme data only — I can't help with that topic.\n\n"
                    "I can answer questions about:\n"
                    "- Loan applications, amounts, rejections, approvals\n"
                    "- District-wise analysis (Agra, Aligarh, Amroha, etc.)\n"
                    "- Certification statistics\n"
                    "- Fraud investigation cases\n\n"
                    "What CM Yuva data would you like to explore?")

        if not analytics:
            return ("I couldn't find specific data for that query. Try asking:\n"
                    "- \"How many loans from Agra?\"\n"
                    "- \"Which city takes highest loan amount?\"\n"
                    "- \"Show rejection analysis\"\n"
                    "- \"Show fraud by district\"\n"
                    "- \"Give me funnel analysis\"")

        parts = []
        district = analytics.get('detected_district')

        # Total loans
        if 'total_loan_applications' in analytics:
            n = analytics['total_loan_applications']
            parts.append("There are **{:,} total loan applications** in the CM Yuva dataset (FY 2024-26).".format(n))

        # District loan count
        if 'applications_in_district' in analytics and district:
            n = analytics['applications_in_district']
            parts.append("**{}** has **{:,} loan applications**.".format(district, n))

        # Status breakdown
        if 'status_breakdown' in analytics:
            sb = analytics['status_breakdown']
            total = sum(sb.values())
            label = " in {}".format(district) if district else ""
            rows = "\n".join("- {}: **{:,}** ({:.1f}%)".format(s, c, c/total*100)
                             for s,c in sorted(sb.items(), key=lambda x:-x[1])[:8])
            parts.append("**Application Status{}:**\n{}".format(label, rows))

        # Names
        if 'applicant_names' in analytics:
            names = analytics['applicant_names']
            label = "from {}".format(district) if district else "found"
            numbered = "\n".join("{}. {}".format(i+1, n) for i,n in enumerate(names[:50]))
            parts.append("**Applicants {} ({} shown):**\n{}".format(label, len(names), numbered))

        # District ranking by count
        if 'district_breakdown' in analytics:
            dd = analytics['district_breakdown']
            total = sum(dd.values())
            rows = "\n".join("  {}. **{}** — {:,} ({:.1f}%)".format(i+1, d, c, c/total*100)
                             for i,(d,c) in enumerate(list(dd.items())[:10]))
            parts.append("**District-wise Loan Applications:**\n{}".format(rows))

        # Highest loan district
        if 'highest_loan_district' in analytics:
            hld = analytics['highest_loan_district']
            top = hld.get('district', '')
            pc  = hld.get('total_project_cost', 0)
            sc  = hld.get('total_sanctioned', 0)
            all_d = hld.get('all_districts', [])
            rows = "\n".join("  {}. **{}** — Rs {:,.0f} ({} apps)".format(
                i+1, d['district'], d['project_cost'], d['applications'])
                for i,d in enumerate(all_d))
            parts.append(
                "The district with the **highest total loan amount** is **{}**.\n\n"
                "- Total Project Cost: **Rs {:,.0f}** (~Rs {:.1f} Crore)\n"
                "- Applications: **{:,}**\n"
                "- Sanctioned by Bank: **Rs {:,.0f}**\n\n"
                "**All Districts by Loan Amount:**\n{}".format(
                    top, pc, pc/1e7, hld.get('applications',0), sc, rows))

        # Lowest loan district
        if 'lowest_loan_district' in analytics:
            lld = analytics['lowest_loan_district']
            bot = lld.get('district', '')
            pc  = lld.get('total_project_cost', 0)
            sc  = lld.get('total_sanctioned', 0)
            all_d = lld.get('all_districts_asc', [])
            rows = "\n".join("  {}. **{}** — Rs {:,.0f} ({} apps)".format(
                i+1, d['district'], d['project_cost'], d['applications'])
                for i,d in enumerate(all_d))
            parts.append(
                "The district with the **lowest total loan amount** is **{}**.\n\n"
                "- Total Project Cost: **Rs {:,.0f}** (~Rs {:.2f} Crore)\n"
                "- Applications: **{:,}**\n"
                "- Sanctioned by Bank: **Rs {:,.0f}**\n\n"
                "**All Districts (Lowest to Highest):**\n{}".format(
                    bot, pc, pc/1e7, lld.get('applications',0), sc, rows))

        # Specific district loan amount
        if 'district_loan_amount' in analytics:
            dla = analytics['district_loan_amount']
            d_name = dla.get('district', district or '')
            pc = dla.get('project_cost', 0)
            sc = dla.get('sanctioned_amount', 0)
            lb = dla.get('disbursed_amount', 0)
            mm = dla.get('mm_released', 0)
            parts.append(
                "**Total Loan Amounts for {}:**\n"
                "- Applications: **{:,}**\n"
                "- Total Project Cost: **Rs {:,.0f}** (~Rs {:.2f} Crore)\n"
                "- Sanctioned by Bank: **Rs {:,.0f}**\n"
                "- Disbursed: **Rs {:,.0f}**\n"
                "- Margin Money Released: **Rs {:,.0f}**".format(
                    d_name, dla.get('applications',0), pc, pc/1e7, sc, lb, mm))

        # Rejection analysis
        if 'rejection_analysis' in analytics:
            r = analytics['rejection_analysis']
            top_rej = "\n".join("- **{}**: {:,} rejections".format(d,c)
                                for d,c in list(r['top_districts_by_rejection'].items())[:6])
            parts.append(
                "**Rejection Analysis:**\n"
                "- Total Applications: **{:,}**\n"
                "- Rejected by Bank: **{:,}**\n"
                "- Rejected by DIC: **{:,}**\n"
                "- **Overall Rejection Rate: {}%**\n\n"
                "Districts with most rejections:\n{}\n\n"
                "**Insight:** Pre-screening with CIBIL score checks before bank forwarding "
                "could significantly reduce the {}% rejection rate.".format(
                    r['total_applications'], r['rejected_by_bank'],
                    r['rejected_by_dic'], r['rejection_rate_pct'], top_rej, r['rejection_rate_pct']))

        # Funnel
        if 'funnel' in analytics:
            f = analytics['funnel']
            lbl = " — {}".format(district) if district else ""
            parts.append(
                "**Loan Approval Funnel{}:**\n"
                "- Applied: {:,}\n"
                "- Forwarded to Bank: {:,}\n"
                "- Sanctioned: **{:,}** ({}%)\n"
                "- Disbursed: **{:,}** ({}%)\n"
                "- Margin Money Released: {:,}\n"
                "- Rejected: **{:,}** ({}%)".format(
                    lbl, f['total_applied'], f['forwarded_to_bank'],
                    f['sanctioned'], f['sanction_rate_pct'],
                    f['disbursed'], f['disbursal_rate_pct'],
                    f['margin_money_released'],
                    f['rejected'], f['rejection_rate_pct']))

        # Full funnel
        if 'full_funnel' in analytics:
            ff = analytics['full_funnel']
            parts.append(
                "**Complete CM Yuva Funnel:**\n"
                "- Certified: **{:,}**\n"
                "- Loan Applied: **{:,}** ({}% of certified)\n"
                "- Sanctioned: **{:,}** ({}% of applied)\n"
                "- Disbursed: **{:,}** ({}% of applied)\n"
                "- Margin Money Released: **{:,}**\n\n"
                "Only {}% of certified candidates actually got loans disbursed.".format(
                    ff['certified'], ff['loan_applied'], ff['cert_to_loan_rate_pct'],
                    ff['loan_sanctioned'], ff['sanction_rate_pct'],
                    ff['loan_disbursed'], ff['disbursal_rate_pct'],
                    ff['margin_money_released'], ff['disbursal_rate_pct']))

        # Fraud
        if 'fraud_by_district' in analytics:
            fd = analytics['fraud_by_district']
            total_f = analytics.get('fraud_total', 59)
            br = analytics.get('fraud_business_running', {})
            not_run = sum(v for k,v in br.items() if 'no' in str(k).lower())
            rows = "\n".join("- **{}**: {} case(s)".format(d, c)
                             for d,c in sorted(fd.items(), key=lambda x:-x[1])[:10] if d)
            parts.append(
                "**Fraud Investigation Report ({} total cases):**\n{}\n\n"
                "- Businesses NOT running as per DPR: **{} ({}%)**\n"
                "- **Risk:** Loan diversion suspected — recommend mandatory field audits.".format(
                    total_f, rows, not_run, round(not_run/total_f*100) if total_f else 0))

        # District performance
        if 'district_performance' in analytics:
            dp = analytics['district_performance']
            h_rows = "\n".join("  {}. **{}** — {}% approval rate".format(i+1, d, v['approval_rate'])
                               for i,(d,v) in enumerate(dp['high_performing']))
            l_rows = "\n".join("  {}. **{}** — {}% rejection rate".format(i+1, d, v['rejection_rate'])
                               for i,(d,v) in enumerate(dp['low_performing']))
            parts.append(
                "**District Performance:**\n\n"
                "Top Performing (Best Approval):\n{}\n\n"
                "Underperforming (Highest Rejection):\n{}".format(h_rows, l_rows))

        # Gender
        if 'gender_breakdown' in analytics:
            gb = analytics['gender_breakdown']
            total = sum(gb.values())
            rows = "\n".join("- **{}**: {:,} ({:.1f}%)".format(g, c, c/total*100) for g,c in gb.items())
            lbl = " — {}".format(district) if district else ""
            parts.append("**Gender Breakdown{}:**\n{}".format(lbl, rows))

        # Certification
        if 'cert_total' in analytics:
            ct = analytics['cert_total']
            lbl = "in {}".format(district) if district else "total"
            parts.append("**{:,} certifications** issued {}.".format(ct, lbl))

        if 'cert_district_breakdown' in analytics:
            cd = analytics['cert_district_breakdown']
            rows = "\n".join("  {}. **{}**: {:,}".format(i+1, d, c) for i,(d,c) in enumerate(list(cd.items())[:10]))
            parts.append("**Top Certified Districts:**\n{}".format(rows))

        if 'cert_monthly_trend' in analytics:
            mt = analytics['cert_monthly_trend']
            recent = sorted(mt.items())[-8:]
            rows = "\n".join("- {}: **{:,}**".format(m,c) for m,c in recent)
            peak = max(mt.items(), key=lambda x:x[1])
            parts.append("**Monthly Certification Trend:**\n{}\n\nPeak: **{}** ({:,} certifications)".format(
                rows, peak[0], peak[1]))

        # Category / industry / bank / qualification / area
        for key, label in [('category_breakdown','Category Breakdown'),
                            ('industry_breakdown','Industry Breakdown'),
                            ('bank_breakdown','Bank-wise Distribution'),
                            ('qualification_breakdown','Qualification Breakdown'),
                            ('area_breakdown','Urban vs Rural')]:
            if key in analytics:
                bd = analytics[key]
                total = sum(bd.values())
                rows = "\n".join("- {}: {:,} ({:.1f}%)".format(k, v, v/total*100)
                                 for k,v in list(bd.items())[:8])
                parts.append("**{}:**\n{}".format(label, rows))

        # CIBIL
        if 'cibil_analysis' in analytics:
            ca = analytics['cibil_analysis']
            if ca:
                parts.append("**CIBIL Score Analysis:**\n"
                             "- Average: **{}**\n- Min: {} | Max: {}\n"
                             "- Records: {:,}".format(ca['average'], ca['min'], ca['max'], ca['count']))

        # Project cost
        if 'project_cost_stats' in analytics:
            pc = analytics['project_cost_stats']
            if pc:
                lbl = " — {}".format(district) if district else ""
                parts.append("**Avg Project Cost{}:** Rs {:,.0f} | Min: Rs {:,.0f} | Max: Rs {:,.0f}".format(
                    lbl, pc['average'], pc['min'], pc['max']))

        # Overview
        if 'overview' in analytics and not parts:
            ov = analytics['overview']
            parts.append(
                "**CM Yuva Scheme — Overview:**\n"
                "- Total Loan Applications: **{:,}**\n"
                "- Total Certifications: **{:,}**\n"
                "- Fraud Cases: **{}**\n\n"
                "Ask me anything specific!".format(
                    ov.get('total_loan_applications', 30000),
                    ov.get('total_certifications', 55512),
                    ov.get('total_fraud_cases', 59)))

        if not parts:
            return ("I don't have specific data for that. Try:\n"
                    "- \"How many loans from Agra?\"\n"
                    "- \"Which city has highest/lowest loan amount?\"\n"
                    "- \"Show rejection analysis\"\n"
                    "- \"Fraud by district\"\n"
                    "- \"What is your name?\"")

        return "\n\n".join(parts)

    # ── ANALYTICS GATHERING (fast — uses pre-built indexes) ───────────────────
    def _gather_analytics(self, query):
        q = query.lower()
        engine = self.engine
        results = {}

        district = engine.find_district(query)
        if district:
            results['detected_district'] = district

        # --- AMOUNT / COST QUERIES ---
        amount_kw = ['highest amount', 'highest loan', 'most loan', 'takes the highest',
                     'takes highest', 'which city', 'amount of loan', 'total loan',
                     'amount taken', 'how much', 'crore', 'total amount', 'loan value',
                     'lowest amount', 'lowest loan', 'least loan', 'minimum loan',
                     'least amount', 'lowest city', 'lowest district']
        if any(w in q for w in amount_kw) or ('cost' in q and not 'project' in q) or 'amount' in q:
            if district:
                all_amounts = engine.district_loan_amounts()
                for d_name, d_vals in all_amounts:
                    if d_name.lower() == district.lower():
                        results['district_loan_amount'] = {'district': d_name, **d_vals}
                        break
            elif any(w in q for w in ['lowest', 'least', 'minimum', 'smallest', 'minimum']):
                results['lowest_loan_district'] = engine.lowest_loan_district()
            else:
                results['highest_loan_district'] = engine.highest_loan_district()
            if 'project cost' in q or 'average cost' in q:
                results['project_cost_stats'] = engine.project_cost_stats(district=district)

        # --- COUNT / TOTAL QUERIES ---
        if any(w in q for w in ['total', 'how many', 'count', 'number of', 'kitne', 'applications']):
            if district:
                results['applications_in_district'] = engine.total_loan_applications(district=district)
                results['status_breakdown'] = engine.status_breakdown(district=district)
            else:
                results['total_loan_applications'] = engine.total_loan_applications()
                results['status_breakdown'] = engine.status_breakdown()

        # --- NAMES ---
        if any(w in q for w in ['name', 'list', 'who', 'members', 'people', 'applicant', 'naam']):
            status = engine.find_status(query)
            if district or status:
                results['applicant_names'] = engine.applicant_names(district=district, status=status, limit=50)

        # --- DISTRICT RANKING ---
        if any(w in q for w in ['district-wise', 'districtwise', 'all district', 'district wise', 'by district']) and not district:
            results['district_breakdown'] = engine.applicants_by_district()

        # --- REJECTION ---
        if any(w in q for w in ['reject', 'rejection', 'rejected', 'most rejected', 'banda reject']):
            results['rejection_analysis'] = engine.rejection_analysis()
            if district:
                results['status_breakdown'] = engine.status_breakdown(district=district)

        # --- APPROVAL / FUNNEL ---
        if any(w in q for w in ['approv', 'sanction', 'disburse', 'approval rate']):
            results['funnel'] = engine.approval_funnel(district=district)
        if any(w in q for w in ['funnel', 'pipeline', 'journey', 'applied to', 'complete flow', 'full flow']):
            results['full_funnel'] = engine.full_funnel()
            results['funnel'] = engine.approval_funnel(district=district)

        # --- STATUS ---
        if any(w in q for w in ['status', 'pending', 'forward', 'current status', 'breakdown']):
            results['status_breakdown'] = engine.status_breakdown(district=district)

        # --- CERTIFICATION ---
        if any(w in q for w in ['certif', 'training', 'course', 'enroll', 'certified']):
            results['cert_total'] = engine.cert_total(district=district)
            if not district:
                results['cert_district_breakdown'] = engine.cert_district_breakdown()
            results['cert_referral_breakdown'] = engine.cert_referral_breakdown()

        # --- MONTHLY TREND ---
        if any(w in q for w in ['month', 'trend', 'monthly', 'growth', 'over time', 'mahine']):
            results['cert_monthly_trend'] = engine.cert_monthly_trend()

        # --- FRAUD ---
        if any(w in q for w in ['fraud', 'fake', 'irregular', 'misuse', 'dhokha', 'scam']):
            results['fraud_by_district'] = engine.fraud_by_district()
            results['fraud_total'] = engine.fraud_total()
            results['fraud_business_running'] = engine.fraud_business_running()

        # --- PERFORMANCE ---
        if any(w in q for w in ['perform', 'best district', 'worst district', 'top district',
                                  'ranking', 'high perform', 'low perform']):
            results['district_performance'] = engine.high_low_districts()

        # --- GENDER ---
        if any(w in q for w in ['gender', 'male', 'female', 'women', 'man', 'mahila', 'purush']):
            results['gender_breakdown'] = engine.gender_breakdown(district=district)

        # --- CATEGORY ---
        if any(w in q for w in ['category', 'caste', 'sc', 'st', 'obc', 'general', 'jati']):
            results['category_breakdown'] = engine.category_breakdown(district=district)

        # --- INDUSTRY ---
        if any(w in q for w in ['industry', 'sector', 'business type', 'udyog']):
            results['industry_breakdown'] = engine.industry_breakdown(district=district)

        # --- CIBIL ---
        if any(w in q for w in ['cibil', 'credit score', 'credit rating']):
            results['cibil_analysis'] = engine.cibil_analysis(district=district)

        # --- BANK ---
        if any(w in q for w in ['bank', 'lender', 'sbi', 'pnb']):
            results['bank_breakdown'] = engine.bank_wise_breakdown(district=district)

        # --- QUALIFICATION ---
        if any(w in q for w in ['qualif', 'education', 'graduate', 'padhai', '10th', '12th']):
            results['qualification_breakdown'] = engine.qualification_breakdown(district=district)

        # --- AREA ---
        if any(w in q for w in ['urban', 'rural', 'shehar', 'gaon', 'area']):
            results['area_breakdown'] = engine.area_breakdown(district=district)

        # --- OVERVIEW / STRATEGY ---
        if any(w in q for w in ['overview', 'summary', 'dashboard', 'insight', 'strateg',
                                  'policy', 'recommend', 'jankari']):
            results['full_funnel'] = engine.full_funnel()
            results['rejection_analysis'] = engine.rejection_analysis()
            results['district_performance'] = engine.high_low_districts()
            results['fraud_summary'] = {'total': engine.fraud_total(), 'by_district': engine.fraud_by_district()}
            results['overview'] = {
                'total_loan_applications': engine.total_loan_applications(),
                'total_certifications': engine.cert_total(),
                'total_fraud_cases': engine.fraud_total(),
            }

        return results
