import pandas as pd
from data_loader import DataLoader
from ai_parser import AIParser
from state_builder import StateBuilder
from simulator import Simulator

dl = DataLoader(is_sample=True)
dl.load_all()
sb = StateBuilder(dl, AIParser())
sim = Simulator(dl)

matches = 0
total = 0
for _, req in dl.requests.iterrows():
    state = sb.get_user_state(req['user_id'], req['request_date'].strftime('%Y-%m-%d'))
    safe = sim.calculate_max_safe_payment(state, req['request_date'].strftime('%Y-%m-%d'), req['requested_amount'])
    truth_safe = req['amount_safe_to_pay']
    
    print(f"{req['request_id']}: truth={truth_safe} calculated={safe} diff={round(abs(safe-truth_safe), 2)}")
    if round(safe, 2) == round(truth_safe, 2):
        matches += 1
    total += 1

print(f"Matched {matches}/{total}")
