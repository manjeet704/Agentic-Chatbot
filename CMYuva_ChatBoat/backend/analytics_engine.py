import json
import os
from collections import Counter, defaultdict
from datetime import datetime

class AnalyticsEngine:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self._load_data()

    def _load_data(self):
        with open(os.path.join(self.data_dir, 'loan_data.json'), 'r', encoding='utf-8') as f:
            raw = json.load(f)
            self.loan_headers = raw['headers']
            self.loan_data = raw['data']

        with open(os.path.join(self.data_dir, 'cert_data.json'), 'r', encoding='utf-8') as f:
            self.cert_data = json.load(f)

        with open(os.path.join(self.data_dir, 'fraud_data.json'), 'r', encoding='utf-8') as f:
            self.fraud_data = json.load(f)

        # Pre-build lookup indexes for fast queries
        self._build_indexes()
        print(f"Loaded: {len(self.loan_data)} loan records, {len(self.cert_data)} cert records, {len(self.fraud_data)} fraud records")

    def _build_indexes(self):
        """Pre-compute indexes at startup so queries are instant."""
        # District index for loans
        self._loan_by_district = defaultdict(list)
        for r in self.loan_data:
            d = r.get('District_Name', '')
            if d:
                self._loan_by_district[d.lower()].append(r)

        # District index for certs
        self._cert_by_district = defaultdict(list)
        for r in self.cert_data:
            d = r.get('District', '')
            if d:
                self._cert_by_district[d.lower()].append(r)

        # Pre-compute all districts (lowercase -> original)
        self._district_map = {}
        for r in self.loan_data:
            d = r.get('District_Name', '')
            if d:
                self._district_map[d.lower()] = d

        # Pre-compute district-level loan amounts
        self._district_amounts = defaultdict(lambda: {
            'applications': 0, 'project_cost': 0,
            'sanctioned_amount': 0, 'disbursed_amount': 0, 'mm_released': 0
        })
        for r in self.loan_data:
            d = r.get('District_Name', '')
            if not d: continue
            self._district_amounts[d]['applications'] += 1
            for field, key in [('Project_Cost','project_cost'),
                                ('Sanctioned_by_Bank_Total','sanctioned_amount'),
                                ('Loan_Release_Amount','disbursed_amount'),
                                ('MM_Release_Amount','mm_released')]:
                v = r.get(field) or 0
                if isinstance(v, (int, float)):
                    self._district_amounts[d][key] += v

    def get_summary(self):
        return {
            'loan_records': len(self.loan_data),
            'cert_records': len(self.cert_data),
            'fraud_records': len(self.fraud_data)
        }

    # ─── LOAN ANALYTICS ──────────────────────────────────────────────────────

    def total_loan_applications(self, district=None, year=None, status=None):
        data = self._filter_loan(district=district, year=year, status=status)
        return len(data)

    def applicants_by_district(self, district=None):
        if district:
            data = self._filter_loan(district=district)
            return {district: len(data)}
        return dict(Counter(r['District_Name'] for r in self.loan_data if r['District_Name']).most_common(30))

    def status_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r['Current_Status'] for r in data if r['Current_Status']).most_common())

    def applicant_names(self, district=None, status=None, limit=50):
        data = self._filter_loan(district=district, status=status)
        return [r['Applicant_Name'] for r in data if r.get('Applicant_Name')][:limit]

    def gender_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r.get('Gender') for r in data if r.get('Gender')).most_common())

    def category_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r.get('Category') for r in data if r.get('Category')).most_common())

    def industry_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r.get('Industry_Type') for r in data if r.get('Industry_Type')).most_common())

    def sector_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r.get('sector_name') for r in data if r.get('sector_name')).most_common(15))

    def rejection_analysis(self):
        total = len(self.loan_data)
        rejected_bank = self._filter_loan(status='Reject by Bank')
        rejected_dic = self._filter_loan(status='Application Rejected BY DIC')
        reject_total = len(rejected_bank) + len(rejected_dic)
        by_district = Counter(r['District_Name'] for r in rejected_bank + rejected_dic if r['District_Name'])
        return {
            'total_applications': total,
            'rejected_by_bank': len(rejected_bank),
            'rejected_by_dic': len(rejected_dic),
            'total_rejected': reject_total,
            'rejection_rate_pct': round(reject_total / total * 100, 2),
            'top_districts_by_rejection': dict(by_district.most_common(10))
        }

    def approval_funnel(self, district=None):
        data = self._filter_loan(district=district)
        total = len(data)
        status_counts = Counter(r['Current_Status'] for r in data if r['Current_Status'])

        approved_statuses = ['Loan Sanctioned by Bank', 'Loan Disbursed by bank',
                             'Margin Money released by Department', 'Margin Money claimed by Bank Branch to Bank nodal']
        rejected_statuses = ['Reject by Bank', 'Application Rejected BY DIC', 'Loan reject after sanction']
        forwarded = status_counts.get('Forwarded to Bank', 0) + status_counts.get('Application Forwarded to DIC', 0)

        sanctioned = sum(status_counts.get(s, 0) for s in ['Loan Sanctioned by Bank', 'Loan Disbursed by bank',
                                                             'Margin Money released by Department',
                                                             'Margin Money claimed by Bank Branch to Bank nodal'])
        disbursed = status_counts.get('Loan Disbursed by bank', 0)
        mm_released = status_counts.get('Margin Money released by Department', 0)
        rejected = sum(status_counts.get(s, 0) for s in rejected_statuses)

        return {
            'total_applied': total,
            'forwarded_to_bank': forwarded,
            'sanctioned': sanctioned,
            'disbursed': disbursed,
            'margin_money_released': mm_released,
            'rejected': rejected,
            'sanction_rate_pct': round(sanctioned / total * 100, 2) if total else 0,
            'disbursal_rate_pct': round(disbursed / total * 100, 2) if total else 0,
            'rejection_rate_pct': round(rejected / total * 100, 2) if total else 0,
        }

    def high_low_districts(self):
        by_district = defaultdict(list)
        for r in self.loan_data:
            d = r.get('District_Name')
            if d:
                by_district[d].append(r)

        results = {}
        for d, rows in by_district.items():
            total = len(rows)
            sanctioned = sum(1 for r in rows if r.get('Current_Status') in
                             ['Loan Sanctioned by Bank', 'Loan Disbursed by bank', 'Margin Money released by Department'])
            rejected = sum(1 for r in rows if r.get('Current_Status') in
                          ['Reject by Bank', 'Application Rejected BY DIC'])
            results[d] = {
                'total': total,
                'sanctioned': sanctioned,
                'rejected': rejected,
                'approval_rate': round(sanctioned / total * 100, 1) if total else 0,
                'rejection_rate': round(rejected / total * 100, 1) if total else 0
            }

        sorted_by_approval = sorted(results.items(), key=lambda x: x[1]['approval_rate'], reverse=True)
        return {
            'high_performing': sorted_by_approval[:5],
            'low_performing': sorted_by_approval[-5:],
            'all': results
        }

    def financial_year_breakdown(self):
        return dict(Counter(r.get('financial_year') for r in self.loan_data if r.get('financial_year')).most_common())

    def bank_wise_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r.get('Bank_Name') for r in data if r.get('Bank_Name')).most_common(15))

    def project_cost_stats(self, district=None):
        data = self._filter_loan(district=district)
        costs = [r.get('Project_Cost') for r in data if r.get('Project_Cost') and isinstance(r.get('Project_Cost'), (int, float))]
        if not costs:
            return {}
        return {
            'count': len(costs),
            'average': round(sum(costs) / len(costs), 2),
            'min': min(costs),
            'max': max(costs),
            'total': sum(costs)
        }

    def cibil_analysis(self, district=None):
        data = self._filter_loan(district=district)
        scores = [r.get('CIBIL_SCORE') for r in data if r.get('CIBIL_SCORE') and str(r.get('CIBIL_SCORE')).replace('.','').isdigit()]
        scores = [float(s) for s in scores if float(s) > 0]
        if not scores:
            return {}
        return {
            'count': len(scores),
            'average': round(sum(scores) / len(scores), 1),
            'min': min(scores),
            'max': max(scores)
        }

    def qualification_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r.get('Qualification') for r in data if r.get('Qualification')).most_common(10))

    def area_breakdown(self, district=None):
        data = self._filter_loan(district=district)
        return dict(Counter(r.get('Area') for r in data if r.get('Area')).most_common())

    # ─── CERTIFICATION ANALYTICS ──────────────────────────────────────────────

    def cert_district_breakdown(self):
        return dict(Counter(r.get('District') for r in self.cert_data if r.get('District')).most_common(20))

    def cert_monthly_trend(self):
        monthly = defaultdict(int)
        for r in self.cert_data:
            t = r.get('txn_time')
            if t:
                try:
                    month = t[:7]  # YYYY-MM
                    monthly[month] += 1
                except:
                    pass
        return dict(sorted(monthly.items()))

    def cert_referral_breakdown(self):
        return dict(Counter(r.get('Referral Role') for r in self.cert_data if r.get('Referral Role')).most_common())

    def cert_total(self, district=None):
        if district:
            return sum(1 for r in self.cert_data if r.get('District', '').lower() == district.lower())
        return len(self.cert_data)

    def cert_names_by_district(self, district, limit=50):
        return [r['Applicant Name'] for r in self.cert_data
                if r.get('District', '').lower() == district.lower() and r.get('Applicant Name')][:limit]

    # ─── FRAUD ANALYTICS ──────────────────────────────────────────────────────

    def fraud_by_district(self):
        return dict(Counter(r.get('District') for r in self.fraud_data if r.get('District')).most_common())

    def fraud_business_running(self):
        return dict(Counter(r.get('Is the business currently running accourding to DPR report. (Yes/No)')
                            for r in self.fraud_data).most_common())

    def fraud_details(self, district=None):
        if district:
            return [r for r in self.fraud_data if r.get('District', '').lower() == district.lower()]
        return self.fraud_data

    def fraud_total(self):
        return len(self.fraud_data)

    # ─── FUNNEL: Cert → Loan → Approved ──────────────────────────────────────

    def full_funnel(self):
        total_cert = len(self.cert_data)
        total_loan = len(self.loan_data)
        sanctioned = sum(1 for r in self.loan_data if r.get('Current_Status') in
                        ['Loan Sanctioned by Bank', 'Loan Disbursed by bank', 'Margin Money released by Department'])
        disbursed = sum(1 for r in self.loan_data if r.get('Current_Status') == 'Loan Disbursed by bank')
        mm_released = sum(1 for r in self.loan_data if r.get('Current_Status') == 'Margin Money released by Department')
        return {
            'certified': total_cert,
            'loan_applied': total_loan,
            'loan_sanctioned': sanctioned,
            'loan_disbursed': disbursed,
            'margin_money_released': mm_released,
            'cert_to_loan_rate_pct': round(total_loan / total_cert * 100, 2) if total_cert else 0,
            'sanction_rate_pct': round(sanctioned / total_loan * 100, 2) if total_loan else 0,
            'disbursal_rate_pct': round(disbursed / total_loan * 100, 2) if total_loan else 0
        }

    # ─── HELPERS ──────────────────────────────────────────────────────────────

    def _filter_loan(self, district=None, status=None, year=None):
        # Use pre-built index for district filter (much faster)
        if district:
            data = self._loan_by_district.get(district.lower(), [])
        else:
            data = self.loan_data
        if status:
            sl = status.lower()
            data = [r for r in data if r.get('Current_Status', '').lower() == sl]
        if year:
            data = [r for r in data if r.get('financial_year') == year]
        return data


    def district_loan_amounts(self, district=None):
        """Total project cost and sanctioned amounts by district."""
        from collections import defaultdict
        by_d = defaultdict(lambda: {
            'applications': 0, 'project_cost': 0,
            'sanctioned_amount': 0, 'disbursed_amount': 0, 'mm_released': 0
        })
        data = self._filter_loan(district=district)
        for r in data:
            d = r.get('District_Name', 'Unknown')
            by_d[d]['applications'] += 1
            pc = r.get('Project_Cost') or 0
            sc = r.get('Sanctioned_by_Bank_Total') or 0
            lr = r.get('Loan_Release_Amount') or 0
            mm = r.get('MM_Release_Amount') or 0
            if isinstance(pc, (int, float)): by_d[d]['project_cost'] += pc
            if isinstance(sc, (int, float)): by_d[d]['sanctioned_amount'] += sc
            if isinstance(lr, (int, float)): by_d[d]['disbursed_amount'] += lr
            if isinstance(mm, (int, float)): by_d[d]['mm_released'] += mm
        # Sort by project cost
        sorted_d = sorted(by_d.items(), key=lambda x: -x[1]['project_cost'])
        return sorted_d

    def highest_loan_district(self):
        """Which district has highest total loan/project cost."""
        amounts = self.district_loan_amounts()
        if not amounts:
            return {}
        top = amounts[0]
        return {
            'district': top[0],
            'applications': top[1]['applications'],
            'total_project_cost': top[1]['project_cost'],
            'total_sanctioned': top[1]['sanctioned_amount'],
            'total_disbursed': top[1]['disbursed_amount'],
            'all_districts': [
                {
                    'district': d,
                    'applications': v['applications'],
                    'project_cost': v['project_cost'],
                    'sanctioned': v['sanctioned_amount'],
                    'disbursed': v['disbursed_amount'],
                    'mm_released': v['mm_released']
                }
                for d, v in amounts
            ]
        }

    def district_application_ranking(self):
        """Districts ranked purely by number of applications."""
        return dict(Counter(r['District_Name'] for r in self.loan_data if r['District_Name']).most_common())

    def find_district(self, text):
        """Fuzzy match a district name from text using pre-built index."""
        text_lower = text.lower()
        for dl, d_orig in self._district_map.items():
            if dl in text_lower:
                return d_orig
        return None

    def lowest_loan_district(self):
        """District with lowest total loan/project cost."""
        amounts = self.district_loan_amounts()
        if not amounts:
            return {}
        bottom = amounts[-1]
        return {
            'district': bottom[0],
            'applications': bottom[1]['applications'],
            'total_project_cost': bottom[1]['project_cost'],
            'total_sanctioned': bottom[1]['sanctioned_amount'],
            'total_disbursed': bottom[1]['disbursed_amount'],
            'all_districts_asc': [
                {'district': d, 'applications': v['applications'],
                 'project_cost': v['project_cost'], 'sanctioned': v['sanctioned_amount']}
                for d, v in reversed(amounts)
            ]
        }

    def find_status(self, text):
        text_l = text.lower()
        status_map = {
            'reject': 'Reject by Bank',
            'bank reject': 'Reject by Bank',
            'dic reject': 'Application Rejected BY DIC',
            'sanction': 'Loan Sanctioned by Bank',
            'disburse': 'Loan Disbursed by bank',
            'margin money release': 'Margin Money released by Department',
            'forward': 'Forwarded to Bank',
            'revert': 'Revert by DIC to applicant',
            'pending': 'Forwarded to Bank',
            'approved': 'Loan Sanctioned by Bank',
        }
        for key, val in status_map.items():
            if key in text_l:
                return val
        return None
