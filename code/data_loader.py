import pandas as pd
import os
import math

class DataLoader:
    def __init__(self, data_dir="dataset", is_sample=False):
        self.data_dir = data_dir
        self.is_sample = is_sample
        self.profiles = None
        self.events = None
        self.exchange_rates = None
        self.payment_options = None
        self.messages = None
        self.images = None
        self.requests = None
        
        self.load_all()
        
    def _parse_pipe_delimited(self, val):
        if pd.isna(val) or str(val).strip() == '':
            return []
        return [x.strip() for x in str(val).split('|') if x.strip()]

    def load_all(self):
        # 1. Load profiles and parse lists/ints
        self.profiles = pd.read_csv(os.path.join(self.data_dir, "financial_profiles.csv"))
        # Parse pipe-delimited fields
        list_fields = [
            'financial_priorities', 
            'expense_categories_to_protect', 
            'expense_categories_user_is_willing_to_reduce', 
            'expense_categories_user_is_willing_to_stop', 
            'payment_methods_user_will_consider'
        ]
        for field in list_fields:
            self.profiles[field] = self.profiles[field].apply(self._parse_pipe_delimited)
            
        # Parse max_installment_months
        def parse_max_inst(val):
            if pd.isna(val) or str(val).strip() == '':
                return None
            try:
                return int(float(val))
            except:
                return None
        self.profiles['max_installment_months'] = self.profiles['max_installment_months'].apply(parse_max_inst)

        # 2. Parse dates in events
        self.events = pd.read_csv(os.path.join(self.data_dir, "financial_events.csv"))
        if 'event_date' in self.events.columns:
            self.events['event_date'] = pd.to_datetime(self.events['event_date'])
        if 'settlement_date' in self.events.columns:
            self.events['settlement_date'] = pd.to_datetime(self.events['settlement_date'])
            
        # 3. Exchange rates
        self.exchange_rates = pd.read_csv(os.path.join(self.data_dir, "exchange_rates.csv"))
        if 'rate_date' in self.exchange_rates.columns:
            self.exchange_rates['rate_date'] = pd.to_datetime(self.exchange_rates['rate_date'])
            
        # 4. Payment options, messages, images
        self.payment_options = pd.read_csv(os.path.join(self.data_dir, "request_payment_options.csv"))
        self.messages = pd.read_csv(os.path.join(self.data_dir, "messages.csv"))
        self.images = pd.read_csv(os.path.join(self.data_dir, "images.csv"))
        
        # 5. Requests
        req_file = "sample_requests.csv" if self.is_sample else "requests.csv"
        req_path = os.path.join(self.data_dir, req_file)
        if os.path.exists(req_path):
            self.requests = pd.read_csv(req_path)
            if 'request_date' in self.requests.columns:
                self.requests['request_date'] = pd.to_datetime(self.requests['request_date'])
            if 'desired_completion_date' in self.requests.columns:
                self.requests['desired_completion_date'] = pd.to_datetime(self.requests['desired_completion_date'])
            if 'allows_partial_payment' in self.requests.columns:
                # Proper boolean parsing
                self.requests['allows_partial_payment'] = self.requests['allows_partial_payment'].astype(str).str.lower() == 'true'
            
    def get_exchange_rate(self, settlement_date_str, from_currency, to_currency):
        """
        Returns the conversion rate from from_currency to to_currency.
        For a foreign-currency cash event, use the row for its settlement_date
        and the stated from_currency -> to_currency direction.
        If no exact match, falls back to nearest earlier date.
        """
        if from_currency == to_currency:
            return 1.0
            
        target_date = pd.to_datetime(settlement_date_str)
        
        # 1. Direct match on exact date
        direct = self.exchange_rates[
            (self.exchange_rates['rate_date'] == target_date) & 
            (self.exchange_rates['from_currency'] == from_currency) & 
            (self.exchange_rates['to_currency'] == to_currency)
        ]
        if not direct.empty:
            return direct.iloc[0]['rate']
            
        # 2. Nearest earlier date (direct direction)
        earlier = self.exchange_rates[
            (self.exchange_rates['rate_date'] <= target_date) & 
            (self.exchange_rates['from_currency'] == from_currency) & 
            (self.exchange_rates['to_currency'] == to_currency)
        ].sort_values('rate_date', ascending=False)
        
        if not earlier.empty:
            return earlier.iloc[0]['rate']
            
        # 3. Try inverse direction exact date
        inv_direct = self.exchange_rates[
            (self.exchange_rates['rate_date'] == target_date) & 
            (self.exchange_rates['from_currency'] == to_currency) & 
            (self.exchange_rates['to_currency'] == from_currency)
        ]
        if not inv_direct.empty:
            return 1.0 / inv_direct.iloc[0]['rate']
            
        # 4. Try inverse direction nearest earlier date
        inv_earlier = self.exchange_rates[
            (self.exchange_rates['rate_date'] <= target_date) & 
            (self.exchange_rates['from_currency'] == to_currency) & 
            (self.exchange_rates['to_currency'] == from_currency)
        ].sort_values('rate_date', ascending=False)
        
        if not inv_earlier.empty:
            return 1.0 / inv_earlier.iloc[0]['rate']
            
        raise ValueError(f"Exchange rate not found for {from_currency} -> {to_currency} on or before {settlement_date_str}")

if __name__ == '__main__':
    dl = DataLoader(os.path.join(os.path.dirname(__file__), '..', 'dataset'))
    print("Data loaded successfully.")
    print("Profiles:", len(dl.profiles))
    print("Events:", len(dl.events))
