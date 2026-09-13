import pandas as pd
from dateutil.relativedelta import relativedelta
from datetime import timedelta

class Simulator:
    def __init__(self, data_loader):
        self.dl = data_loader

    def simulate_90_days(self, state, request_date_str, plan_payments, spending_changes=None):
        """
        Simulate balance day-by-day for 90 days from request_date.
        """
        request_date = pd.to_datetime(request_date_str)
        end_date = request_date + timedelta(days=90)
        
        profile = state['profile']
        current_balance = state['current_balance']
        min_required = profile['minimum_balance_to_keep']
        home_currency = profile['home_currency']
        
        spending_changes = spending_changes or {"stop": [], "reduce_to": {}}
        
        timeline = []
        
        # 1. Plan payments
        for p in plan_payments:
            p_date = pd.to_datetime(p['date'])
            if request_date <= p_date <= end_date:
                timeline.append({
                    "date": p_date,
                    "amount": float(p['amount']),
                    "direction": "debit"
                })
                
        # 2. Scheduled future events
        for ev in state['scheduled_events']:
            ev_date = pd.to_datetime(ev['event_date'])
            if request_date <= ev_date <= end_date:
                amount = float(ev['amount'])
                if ev['currency'] != home_currency:
                    amount *= self.dl.get_exchange_rate(ev['settlement_date'], ev['currency'], home_currency)
                timeline.append({
                    "date": ev_date,
                    "amount": amount,
                    "direction": ev['direction']
                })
        
        # 3. Recurring patterns projected forward
        for pattern in state['recurring_patterns']:
            base_id = pattern['event_id_base']
            if base_id in spending_changes["stop"]:
                continue
                
            amount = float(pattern['amount'])
            if base_id in spending_changes["reduce_to"]:
                amount = float(spending_changes["reduce_to"][base_id])
                
            cadence = pattern['cadence']
            last_date = pd.to_datetime(pattern['last_date'])
            next_date = last_date
            
            while next_date <= end_date:
                if cadence == 'monthly':
                    next_date += relativedelta(months=1)
                elif cadence == 'weekly':
                    next_date += timedelta(days=7)
                elif cadence == 'ten_days':
                    next_date += timedelta(days=10)
                elif cadence == 'biweekly':
                    next_date += timedelta(days=14)
                elif cadence == 'three_weekly':
                    next_date += timedelta(days=21)
                elif cadence == 'quarterly':
                    next_date += relativedelta(months=3)
                elif cadence == 'yearly':
                    next_date += relativedelta(years=1)
                else:
                    break
                    
                if request_date <= next_date <= end_date:
                    loop_amount = amount
                    if pattern['currency'] != home_currency:
                        loop_amount *= self.dl.get_exchange_rate(next_date.strftime("%Y-%m-%d"), pattern['currency'], home_currency)
                    timeline.append({
                        "date": next_date,
                        "amount": loop_amount,
                        "direction": pattern['direction']
                    })
                    
        # Sort: primary by date, secondary by direction (debits before credits) for conservative tracking
        timeline.sort(key=lambda x: (x['date'], 0 if x['direction'] == 'debit' else 1))
        
        balance = current_balance
        lowest_balance = balance
        is_safe = balance >= min_required
        
        for event in timeline:
            if event['direction'] == 'debit':
                balance -= event['amount']
            elif event['direction'] == 'credit':
                balance += event['amount']
                
            if balance < lowest_balance:
                lowest_balance = balance
                
            if balance < min_required:
                is_safe = False
                
        return is_safe, lowest_balance

    def calculate_max_safe_payment(self, state, request_date_str, requested_amount):
        """
        Binary search for the maximum amount payable on request_date
        such that the 90-day simulation stays safe.
        """
        # Baseline with payment = 0
        is_safe, lowest = self.simulate_90_days(state, request_date_str, [{"date": request_date_str, "amount": 0}])
        if not is_safe:
            return 0.0
            
        min_required = state['profile']['minimum_balance_to_keep']
        buffer = lowest - min_required
        
        if buffer <= 0:
            return 0.0
            
        # The most we can pay is the buffer, capped at requested_amount
        max_possible = min(buffer, float(requested_amount))
        
        # Verify
        is_safe, _ = self.simulate_90_days(state, request_date_str, [{"date": request_date_str, "amount": max_possible}])
        if is_safe:
            return round(max_possible, 2)
            
        # Binary search
        low = 0.0
        high = max_possible
        best_safe = 0.0
        
        for _ in range(50): # 50 iterations guarantees precision even for millions of IDR
            mid = (low + high) / 2
            is_safe, _ = self.simulate_90_days(state, request_date_str, [{"date": request_date_str, "amount": mid}])
            if is_safe:
                best_safe = mid
                low = mid
            else:
                high = mid
                
        return round(best_safe, 2)
        
    def find_earliest_full_payment_date(self, state, request_date_str, full_amount):
        """
        Find earliest date to pay full_amount safely without spending changes.
        """
        request_date = pd.to_datetime(request_date_str)
        
        for i in range(91):
            test_date = request_date + timedelta(days=i)
            test_date_str = test_date.strftime("%Y-%m-%d")
            
            is_safe, _ = self.simulate_90_days(state, request_date_str, [{"date": test_date_str, "amount": full_amount}])
            if is_safe:
                return test_date_str
                
        return ""
