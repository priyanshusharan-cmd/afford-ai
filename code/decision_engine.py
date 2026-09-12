import pandas as pd
from datetime import timedelta

class DecisionEngine:
    def __init__(self, simulator):
        self.sim = simulator
        self.dl = simulator.dl
        
    def generate_explanation(self, method, req_amount, amount_safe, earliest_date, last_date, chg_str, min_balance):
        if method == "full_payment":
            if chg_str == "none":
                return f"Pay {req_amount} today. This keeps the {min_balance} minimum available over the next 90 days."
            else:
                return f"After applying spending changes, pay {req_amount} today. This leaves at least {min_balance} available."
        elif method == "wait":
            return f"Wait until {earliest_date}, then pay {req_amount} in full. Paying sooner would put the {min_balance} minimum at risk."
        elif method == "partial_payment":
            return f"Pay {amount_safe} today and the remaining {req_amount - amount_safe} on {last_date}. This completes the full request and keeps the {min_balance} minimum protected."
        elif method == "installments":
            return f"Use installments to pay the amount over time. This leaves at least {min_balance} available."
        else:
            return f"Do not make this payment. None of the available options keeps the {min_balance} minimum protected."

    def generate_installment_plans(self, request_id, request_date_str, max_months):
        options = self.dl.payment_options[self.dl.payment_options['request_id'] == request_id]
        plans = []
        for _, opt in options.iterrows():
            if opt['payment_method'] == 'installments':
                n_payments = int(opt['number_of_payments'])
                freq = int(opt['payment_frequency_days'])
                amount = float(opt['payment_amount'])
                first_date = pd.to_datetime(opt['first_payment_date'])
                
                # Check max months constraint
                if max_months is not None:
                    # rough duration in months
                    duration_days = n_payments * freq
                    if duration_days > max_months * 31: # simple approx
                        continue
                        
                schedule = []
                for i in range(n_payments):
                    d = first_date + timedelta(days=i*freq)
                    schedule.append({"date": d.strftime("%Y-%m-%d"), "amount": amount})
                
                plans.append({
                    "method": "installments",
                    "option_id": opt['payment_option_id'],
                    "schedule": schedule,
                    "total_paid": opt['total_payable_amount'],
                    "last_date": schedule[-1]["date"]
                })
        return plans

    def generate_spending_changes(self, state, target_amount, request_date_str):
        changes = {"stop": [], "reduce_to": {}}
        change_strs = []
        
        # 1. From recurring patterns
        flexible = [p for p in state['recurring_patterns'] if p['is_stoppable'] or p['is_reducible']]
        
        # 2. From stoppable future events
        for p in state.get('stoppable_future', []):
            flexible.append(p)
            
        # Deduplicate by event_id_base (in case a recurring event is also in future)
        seen = set()
        unique_flexible = []
        for p in flexible:
            if p['event_id_base'] not in seen:
                seen.add(p['event_id_base'])
                unique_flexible.append(p)
                
        unique_flexible.sort(key=lambda x: x['amount'], reverse=True)
        
        freed = 0.0
        for p in unique_flexible:
            if len(changes["stop"]) + len(changes["reduce_to"]) >= 3 or freed >= target_amount:
                break
                
            base_id = p['event_id_base']
            
            if p['is_stoppable'] and freed < target_amount:
                changes["stop"].append(base_id)
                change_strs.append(f"stop:{base_id}")
                freed += p['amount']
            elif p['is_reducible'] and freed < target_amount:
                min_allow = p['min_allowed_amt'] if pd.notna(p.get('min_allowed_amt')) else 0.0
                if p['amount'] > min_allow:
                    shortfall = target_amount - freed
                    proposed_reduction = min(shortfall, p['amount'] - min_allow)
                    new_amt = round(p['amount'] - proposed_reduction, 2)
                    changes["reduce_to"][base_id] = new_amt
                    
                    amt_fmt = f"{new_amt:.2f}" if new_amt % 1 != 0 else str(int(new_amt))
                    change_strs.append(f"reduce_to:{base_id}:{amt_fmt}")
                    freed += proposed_reduction
                    
        return changes, "|".join(change_strs) if change_strs else "none"

    def evaluate_request(self, request_row, state):
        req_id = request_row['request_id']
        req_date_str = request_row['request_date'].strftime("%Y-%m-%d") if isinstance(request_row['request_date'], pd.Timestamp) else request_row['request_date']
        req_amount = float(request_row['requested_amount'])
        desired_date_str = request_row['desired_completion_date'].strftime("%Y-%m-%d") if isinstance(request_row['desired_completion_date'], pd.Timestamp) else request_row['desired_completion_date']
        allows_partial = request_row['allows_partial_payment']
        
        user_methods = state['profile'].get('payment_methods_user_will_consider', [])
        max_inst_months = state['profile'].get('max_installment_months', None)
        
        # 1. Base max safe amount
        amount_safe = self.sim.calculate_max_safe_payment(state, req_date_str, req_amount)
        amount_safe = min(amount_safe, req_amount)
        
        # 2. Earliest full payment date
        earliest_full_date = self.sim.find_earliest_full_payment_date(state, req_date_str, req_amount)
        
        valid_plans = []
        
        # Test full_payment
        if 'full_payment' in user_methods and amount_safe >= req_amount:
            valid_plans.append({
                "method": "full_payment",
                "schedule": [{"date": req_date_str, "amount": req_amount}],
                "total_paid": req_amount,
                "spending_changes": "none",
                "spending_changes_dict": None,
                "last_date": req_date_str,
                "start_date": req_date_str,
                "option_id": ""
            })
            
        # Test wait
        if 'full_payment' in user_methods:
            if earliest_full_date and earliest_full_date <= desired_date_str and earliest_full_date != req_date_str:
                valid_plans.append({
                    "method": "wait",
                    "schedule": [{"date": earliest_full_date, "amount": req_amount}],
                    "total_paid": req_amount,
                    "spending_changes": "none",
                    "spending_changes_dict": None,
                    "last_date": earliest_full_date,
                    "start_date": earliest_full_date,
                    "option_id": ""
                })
                
        # Test partial_payment
        if 'partial_payment' in user_methods and allows_partial and 0 < amount_safe < req_amount:
            if earliest_full_date and earliest_full_date <= desired_date_str:
                rem_amount = round(req_amount - amount_safe, 2)
                valid_plans.append({
                    "method": "partial_payment",
                    "schedule": [
                        {"date": req_date_str, "amount": amount_safe},
                        {"date": earliest_full_date, "amount": rem_amount}
                    ],
                    "total_paid": req_amount,
                    "spending_changes": "none",
                    "spending_changes_dict": None,
                    "last_date": earliest_full_date,
                    "start_date": req_date_str,
                    "option_id": ""
                })
                
        # Test installments
        if 'installments' in user_methods:
            inst_plans = self.generate_installment_plans(req_id, req_date_str, max_inst_months)
            for p in inst_plans:
                if p["last_date"] <= desired_date_str:
                    is_safe, _ = self.sim.simulate_90_days(state, req_date_str, p["schedule"])
                    if is_safe:
                        valid_plans.append({
                            "method": "installments",
                            "schedule": p["schedule"],
                            "total_paid": float(p["total_paid"]),
                            "spending_changes": "none",
                            "spending_changes_dict": None,
                            "last_date": p["last_date"],
                            "start_date": p["schedule"][0]["date"],
                            "option_id": p["option_id"]
                        })

        # Try spending changes for full_payment if no plans or if we want to find a better one
        if 'full_payment' in user_methods and amount_safe < req_amount:
            chg_dict, chg_str = self.generate_spending_changes(state, req_amount - amount_safe, req_date_str)
            if chg_str != "none":
                is_safe, _ = self.sim.simulate_90_days(state, req_date_str, [{"date": req_date_str, "amount": req_amount}], spending_changes=chg_dict)
                if is_safe:
                    valid_plans.append({
                        "method": "full_payment",
                        "schedule": [{"date": req_date_str, "amount": req_amount}],
                        "total_paid": req_amount,
                        "spending_changes": chg_str,
                        "spending_changes_dict": chg_dict,
                        "last_date": req_date_str,
                        "start_date": req_date_str,
                        "option_id": ""
                    })

        if not valid_plans:
            affordability = "not_affordable"
            method = "not_recommended"
            plan_str = "none"
            chg_str = "none"
            ret_earliest = ""
            explanation = self.generate_explanation(
                method, req_amount, amount_safe, 
                ret_earliest, "", "none", state['profile']['minimum_balance_to_keep']
            )
        else:
            def rank_key(p):
                # 1. Complete by desired_completion_date (all valid plans already filter for this)
                # 2. Require no spending changes (none first)
                has_chg = p["spending_changes"] != "none"
                # 3. Minimize total amount paid
                total = p["total_paid"]
                # 4. Start payment earlier
                start_date = p["start_date"]
                # 5. Use fewer payments
                num_payments = len(p["schedule"])
                # 6. Lowest payment_option_id
                opt_id = p["option_id"]
                return (has_chg, total, start_date, num_payments, opt_id)
                
            valid_plans.sort(key=rank_key)
            best_plan = valid_plans[0]
            
            method = best_plan["method"]
            chg_str = best_plan["spending_changes"]
            
            plan_str_parts = []
            for x in best_plan["schedule"]:
                amt_fmt = f"{x['amount']:.2f}" if x['amount'] % 1 != 0 else str(int(x['amount']))
                plan_str_parts.append(f"{x['date']}:{amt_fmt}")
            plan_str = "|".join(plan_str_parts)
            
            if method == "full_payment" and best_plan["last_date"] == req_date_str and chg_str == "none":
                affordability = "affordable_now"
            elif method in ["partial_payment", "installments"] or chg_str != "none":
                affordability = "affordable_with_plan"
            elif method == "wait":
                affordability = "affordable_later"
            else:
                affordability = "affordable_now"
                
            ret_earliest = earliest_full_date
            
            explanation = self.generate_explanation(
                method, req_amount, amount_safe, 
                best_plan["start_date"], 
                best_plan["last_date"], chg_str, state['profile']['minimum_balance_to_keep']
            )

        # Make sure amount_safe formatting is clean
        amount_safe = round(amount_safe, 2)
        if amount_safe % 1 == 0:
            amount_safe = int(amount_safe)
            
        return {
            "amount_safe_to_pay": amount_safe,
            "affordability_status": affordability,
            "recommended_payment_method": method,
            "payment_plan": plan_str,
            "earliest_date_for_full_payment": ret_earliest,
            "spending_changes_needed": chg_str,
            "decision_explanation": explanation
        }
