"""
Generates a fine-tuning dataset (JSONL) from the CM Yuva data.
Run: python ollama_training/generate_dataset.py
Output: ollama_training/cmyuva_training.jsonl
"""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
from analytics_engine import AnalyticsEngine

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
engine = AnalyticsEngine(DATA_DIR)

SYSTEM = """You are the CM Yuva Analytics Assistant, an expert on the CM Yuva youth entrepreneurship scheme in Uttar Pradesh, India. Answer accurately using only the data provided."""

def make_pair(user, assistant):
    return {"messages": [
        {"role": "system",    "content": SYSTEM},
        {"role": "user",      "content": user},
        {"role": "assistant", "content": assistant}
    ]}

pairs = []

# ── Identity / Greeting ───────────────────────────────────────────────────────
pairs += [
    make_pair("What is your name?",
              "I'm the CM Yuva Analytics Assistant — an AI chatbot built to help you explore data from the CM Yuva (Chief Minister's Youth Entrepreneurship) scheme in Uttar Pradesh."),
    make_pair("Who are you?",
              "I'm the CM Yuva Analytics Assistant. I can answer questions about loan applications, certifications, fraud cases, and district performance data from the CM Yuva scheme in UP."),
    make_pair("hi", "Hello! I'm the CM Yuva Analytics Assistant. Ask me about loans, certifications, fraud, or district performance!"),
    make_pair("hello", "Hi there! I'm here to help you explore the CM Yuva scheme data. What would you like to know?"),
    make_pair("good morning", "Good morning! Ready to help you with CM Yuva scheme insights. What's your question?"),
    make_pair("namaste", "Namaste! Main CM Yuva Analytics Assistant hoon. Aap kya jaanna chahte hain?"),
    make_pair("what can you do?",
              "I can help you with:\n- Loan application counts by district\n- Applicant names and details\n- Rejection and approval analysis\n- Certification statistics and trends\n- Fraud investigation insights\n- District performance rankings\n- Loan amounts and project costs"),
]

# ── Out of scope ───────────────────────────────────────────────────────────────
pairs += [
    make_pair("What is the weather today?",
              "I can only help with CM Yuva scheme data — I'm not able to provide weather information."),
    make_pair("Tell me a joke",
              "I'm a data analytics assistant, so jokes aren't my specialty! But I can tell you some interesting facts about the CM Yuva scheme. Want to know which district has the highest loan amount?"),
    make_pair("What is 2 + 2?",
              "I'm specialized in CM Yuva scheme analytics and can't help with general maths. Ask me about loans, certifications, or fraud data instead!"),
    make_pair("Who is the Prime Minister of India?",
              "That's outside my area — I focus exclusively on CM Yuva scheme data in Uttar Pradesh."),
]

# ── Total loans ───────────────────────────────────────────────────────────────
total = engine.total_loan_applications()
pairs += [
    make_pair("How many total loan applications are there?",
              "There are **{:,} total loan applications** in the CM Yuva dataset, covering financial years 2024-25 and 2025-26.".format(total)),
    make_pair("What is the total number of loan applications?",
              "The CM Yuva scheme has received **{:,} loan applications** in this dataset.".format(total)),
    make_pair("kitne loan applications hain total?",
              "CM Yuva scheme mein kul **{:,} loan applications** hain.".format(total)),
]

# ── District-wise counts ───────────────────────────────────────────────────────
district_counts = engine.applicants_by_district()
for district, count in district_counts.items():
    status = engine.status_breakdown(district=district)
    sanctioned = status.get('Loan Sanctioned by Bank', 0) + status.get('Margin Money released by Department', 0) + status.get('Loan Disbursed by bank', 0)
    rejected   = status.get('Reject by Bank', 0) + status.get('Application Rejected BY DIC', 0)
    pairs += [
        make_pair("How many loan applications are from {}?".format(district),
                  "There are **{:,} loan applications** from {} district.".format(count, district)),
        make_pair("How many members from {} have taken a loan?".format(district),
                  "**{:,} loan applications** have been submitted from {} district. Of these, {:,} have been approved/sanctioned and {:,} have been rejected.".format(count, district, sanctioned, rejected)),
        make_pair("Show me {} district data".format(district),
                  "**{}** has {:,} loan applications.\n- Approved/Sanctioned: {:,}\n- Rejected: {:,}".format(district, count, sanctioned, rejected)),
    ]

# ── Loan amounts ──────────────────────────────────────────────────────────────
hld = engine.highest_loan_district()
lld = engine.lowest_loan_district()
all_amounts = engine.district_loan_amounts()

highest_d = hld['district']
highest_pc = hld['total_project_cost']
lowest_d = lld['district']
lowest_pc = lld['total_project_cost']

ranking = "\n".join("{}. {} — Rs {:,.0f}".format(i+1, d['district'], d['project_cost'])
                    for i,d in enumerate(hld['all_districts']))

pairs += [
    make_pair("Which city takes the highest amount of loan?",
              "**{}** has the highest total loan demand with a project cost of **Rs {:,.0f}** (~Rs {:.1f} Crore) across {:,} applications.".format(
                  highest_d, highest_pc, highest_pc/1e7, hld['applications'])),
    make_pair("In Uttar Pradesh which city takes the highest amount of loan?",
              "In the CM Yuva scheme, **{}** has the highest total loan amount:\n- Project Cost: **Rs {:,.0f}** (~Rs {:.1f} Crore)\n- Applications: {:,}\n- Sanctioned by Bank: Rs {:,.0f}".format(
                  highest_d, highest_pc, highest_pc/1e7, hld['applications'], hld['total_sanctioned'])),
    make_pair("Which district takes the lowest loan?",
              "**{}** has the lowest total loan demand with a project cost of **Rs {:,.0f}** (~Rs {:.2f} Crore) across {:,} applications.".format(
                  lowest_d, lowest_pc, lowest_pc/1e7, lld['applications'])),
    make_pair("Which city takes the least loan amount?",
              "**{}** has the lowest total loan amount in the CM Yuva scheme — Rs {:,.0f} (~Rs {:.2f} Crore).".format(
                  lowest_d, lowest_pc, lowest_pc/1e7)),
    make_pair("Rank all districts by loan amount",
              "**Districts Ranked by Total Project Cost:**\n" + ranking),
    make_pair("which districts takes the highest loan in Uttar pradesh",
              "**All Districts by Total Loan Amount:**\n" + ranking + "\n\n**{}** leads with Rs {:.1f} Crore in total project cost.".format(highest_d, highest_pc/1e7)),
]

# Agra-specific amount
for d_name, d_vals in all_amounts:
    pc = d_vals['project_cost']
    sc = d_vals['sanctioned_amount']
    lb = d_vals['disbursed_amount']
    pairs += [
        make_pair("show total loan amount taken by {} city".format(d_name.lower()),
                  "**Total Loan Amounts for {}:**\n- Applications: {:,}\n- Total Project Cost: Rs {:,.0f} (~Rs {:.2f} Crore)\n- Sanctioned by Bank: Rs {:,.0f}\n- Disbursed: Rs {:,.0f}".format(
                      d_name, d_vals['applications'], pc, pc/1e7, sc, lb)),
        make_pair("how much total loan amount in {}".format(d_name.lower()),
                  "**{}** has a total project cost (loan demand) of **Rs {:,.0f}** (~Rs {:.2f} Crore). Of this, Rs {:,.0f} was sanctioned by banks and Rs {:,.0f} actually disbursed.".format(
                      d_name, pc, pc/1e7, sc, lb)),
    ]

# ── Rejection analysis ────────────────────────────────────────────────────────
rej = engine.rejection_analysis()
top_rej_districts = list(rej['top_districts_by_rejection'].items())[:5]
top_str = ", ".join("{} ({:,})".format(d,c) for d,c in top_rej_districts)
top_d = top_rej_districts[0][0]

pairs += [
    make_pair("Which district has the most rejected loans?",
              "**{}** has the most loan rejections. Overall, the CM Yuva scheme has a **{}% rejection rate** ({:,} rejections out of {:,} applications).\n\nTop districts by rejections: {}".format(
                  top_d, rej['rejection_rate_pct'], rej['total_rejected'], rej['total_applications'], top_str)),
    make_pair("Show me rejection analysis",
              "**Loan Rejection Analysis:**\n- Total Applications: {:,}\n- Rejected by Bank: {:,}\n- Rejected by DIC: {:,}\n- **Overall Rejection Rate: {}%**\n\nMost rejections: {}".format(
                  rej['total_applications'], rej['rejected_by_bank'], rej['rejected_by_dic'], rej['rejection_rate_pct'], top_str)),
    make_pair("What is the loan rejection rate?",
              "The overall loan rejection rate in CM Yuva is **{}%** — {:,} applications out of {:,} were rejected ({:,} by bank, {:,} by DIC).".format(
                  rej['rejection_rate_pct'], rej['total_rejected'], rej['total_applications'], rej['rejected_by_bank'], rej['rejected_by_dic'])),
]

# ── Funnel ────────────────────────────────────────────────────────────────────
ff = engine.full_funnel()
pairs += [
    make_pair("Give me the funnel analysis from applied to approved",
              "**Complete CM Yuva Scheme Funnel:**\n- Certified: {:,}\n- Loan Applied: {:,} ({}% of certified)\n- Sanctioned: {:,} ({}% of applied)\n- Disbursed: {:,} ({}% of applied)\n- Margin Money Released: {:,}\n\nOnly {}% of certified candidates received actual loan disbursement.".format(
                  ff['certified'], ff['loan_applied'], ff['cert_to_loan_rate_pct'],
                  ff['loan_sanctioned'], ff['sanction_rate_pct'],
                  ff['loan_disbursed'], ff['disbursal_rate_pct'],
                  ff['margin_money_released'], ff['disbursal_rate_pct'])),
    make_pair("What is the loan approval rate?",
              "The loan sanction (approval) rate in CM Yuva is **{}%** — {:,} loans sanctioned out of {:,} applied. However, actual disbursal rate is only **{}%** ({:,} loans disbursed).".format(
                  ff['sanction_rate_pct'], ff['loan_sanctioned'], ff['loan_applied'],
                  ff['disbursal_rate_pct'], ff['loan_disbursed'])),
]

# ── Fraud ─────────────────────────────────────────────────────────────────────
fraud_d = engine.fraud_by_district()
fraud_br = engine.fraud_business_running()
not_run = sum(v for k,v in fraud_br.items() if 'no' in str(k).lower())
top_fraud = sorted(fraud_d.items(), key=lambda x:-x[1])[:5]
top_fraud_str = "\n".join("- {}: {} cases".format(d,c) for d,c in top_fraud if d)

pairs += [
    make_pair("Show fraud cases by district",
              "**Fraud Investigation Summary (59 total cases):**\n{}\n\n**{}%** of investigated businesses are NOT running as per their business plan (DPR) — indicating loan misuse.".format(
                  top_fraud_str, round(not_run/59*100))),
    make_pair("Show me fraud analysis by district",
              "**Fraud Cases by District:**\n{}\n\n- Businesses NOT running as per DPR: **{} ({}%)**\n- This indicates significant loan diversion risk.".format(
                  top_fraud_str, not_run, round(not_run/59*100))),
    make_pair("Which district has the most fraud?",
              "**{}** has the most fraud cases ({}) in the CM Yuva scheme. Out of 59 total investigated cases, {}% of businesses were found NOT operating as per their submitted business plan.".format(
                  top_fraud[0][0], top_fraud[0][1], round(not_run/59*100))),
]

# ── Certification ─────────────────────────────────────────────────────────────
cert_total = engine.cert_total()
cert_top = engine.cert_district_breakdown()
top_cert_d = list(cert_top.items())[0]

pairs += [
    make_pair("How many certifications have been issued?",
              "**{:,} certifications** have been issued under the CM Yuva scheme. The top certified district is {} with {:,} certifications.".format(
                  cert_total, top_cert_d[0], top_cert_d[1])),
    make_pair("What is the certification completion rate?",
              "The CM Yuva scheme has issued **{:,} certifications** total. Of these certified candidates, only {}% have applied for loans — suggesting awareness campaigns are needed.".format(
                  cert_total, ff['cert_to_loan_rate_pct'])),
]

# ── Performance ───────────────────────────────────────────────────────────────
perf = engine.high_low_districts()
high = perf['high_performing']
low  = perf['low_performing']

pairs += [
    make_pair("Which districts are high performing?",
              "**Top Performing Districts (by approval rate):**\n" +
              "\n".join("{}. {} — {}% approval".format(i+1,d,v['approval_rate']) for i,(d,v) in enumerate(high)) +
              "\n\n**Underperforming Districts:**\n" +
              "\n".join("{}. {} — {}% rejection".format(i+1,d,v['rejection_rate']) for i,(d,v) in enumerate(low))),
    make_pair("Which district is performing the worst?",
              "Based on rejection rates, the underperforming districts are:\n" +
              "\n".join("- {} ({}% rejection rate)".format(d, v['rejection_rate']) for d,v in low) +
              "\n\nThese districts need additional DIC officer support and pre-screening improvement."),
]

# ── Gender ────────────────────────────────────────────────────────────────────
gender = engine.gender_breakdown()
total_g = sum(gender.values())
pairs += [
    make_pair("What is the gender breakdown of applicants?",
              "**Gender Breakdown:**\n" + "\n".join("- {}: {:,} ({:.1f}%)".format(g, c, c/total_g*100) for g,c in gender.items())),
    make_pair("How many female applicants are there?",
              "Gender distribution:\n" + "\n".join("- {}: {:,} ({:.1f}%)".format(g, c, c/total_g*100) for g,c in gender.items())),
]

# Save
out_path = os.path.join(os.path.dirname(__file__), 'cmyuva_training.jsonl')
with open(out_path, 'w', encoding='utf-8') as f:
    for pair in pairs:
        f.write(json.dumps(pair, ensure_ascii=False) + '\n')

print("Generated {} training pairs -> {}".format(len(pairs), out_path))
