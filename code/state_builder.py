import pandas as pd
from datetime import timedelta
import os
from dateutil.relativedelta import relativedelta

class StateBuilder:
    def __init__(self, data_loader, ai_parser):
        self.dl = data_loader
        self.ai = ai_parser
        
    def fill_missing_amounts_from_images(self, events):
        """
        Uses images to fill NaN amounts in events.
        """
        missing_amounts = events[events['amount'].isna()].copy()
        if missing_amounts.empty:
            return events
            
        for idx, row in missing_amounts.iterrows():
            image_match = self.dl.images[self.dl.images['related_event_id'] == row['event_id']]
            if not image_match.empty:
                image_id = image_match.iloc[0]['image_id']
                img_path = os.path.join(self.dl.data_dir, f"media/images/{image_id}.png")
                amount = self.ai.extract_amount_from_image(img_path)
                if amount is not None:
                    events.at[idx, 'amount'] = amount
        return events

    def apply_message_amendments(self, events, user_id, request_date):
        """
        Applies message effects to events based on AI parsing.
        """
        user_msgs = self.dl.messages[self.dl.messages['user_id'] == user_id]
        if user_msgs.empty:
            return events
            
        user_msgs = user_msgs.sort_values(by='sent_at')
        
        for _, msg_row in user_msgs.iterrows():
            msg_date = pd.to_datetime(msg_row['sent_at']).tz_localize(None)
            if msg_date > request_date:
                continue
                
            parse_res = self.ai.parse_message(msg_row['message_text'])
            action = parse_res.get('action')
            conf = parse_res.get('confidence', 'confirmed')
            amt = parse_res.get('updated_amount')
            dt = parse_res.get('updated_date')
            eff_dt = parse_res.get('effective_date')
            
            if parse_res.get('cancel_commission'):
                mask = events['description'].str.contains('commission', case=False, na=False)
                events = events[~mask]
            
            related_id = msg_row.get('related_event_id')
            
            if pd.notna(related_id) and related_id in events.index:
                if action == 'cancel' and conf == 'confirmed':
                    events.at[related_id, 'status'] = 'cancelled'
                elif action == 'payment_delay' and dt:
                    events.at[related_id, 'event_date'] = pd.to_datetime(dt)
                    events.at[related_id, 'settlement_date'] = pd.to_datetime(dt)
                elif action == 'amount_change' and amt is not None:
                    events.at[related_id, 'amount'] = amt
            else:
                # General message (e.g., salary change)
                if action == 'salary_change' and amt is not None and eff_dt is not None:
                    eff_date_parsed = pd.to_datetime(eff_dt)
                    # Find future salary events and update them
                    # Assuming category='salary' or similar description
                    mask = (events['category'] == 'salary') | (events['description'].str.contains(r'\bsalary\b|\bpayroll\b', case=False, na=False, regex=True))
                    mask = mask & (events['event_date'] >= eff_date_parsed)
                    if conf == 'confirmed':
                        events.loc[mask, 'amount'] = amt
                    
        return events

    def resolve_conflicts(self, events):
        """
        Resolves lifecycle conflicts using linked_event_id.
        Rules:
        - If new event is settled, it overrides older pending/scheduled.
        - If new event is cancelled/failed, remove the linked chain from cash flow.
        """
        resolved = events.to_dict(orient='index')
        
        # Sort by event_date
        events_sorted = events.sort_values(by='event_date')
        
        for idx, row in events_sorted.iterrows():
            eid = row['event_id']
            linked_id = row['linked_event_id']
            status = row['status']
            
            if pd.notna(linked_id) and linked_id in resolved:
                if status in ['cancelled', 'failed']:
                    del resolved[linked_id]
                    if eid in resolved:
                        del resolved[eid] # this is also a failure
                elif status == 'settled':
                    # new settled replaces old pending
                    del resolved[linked_id]
                elif status == 'unrealized':
                    # Unrealized gain isn't cash flow, just remove it.
                    # but keep original purchase if it was settled cash
                    if eid in resolved:
                        del resolved[eid]
            else:
                if status in ['cancelled', 'failed', 'unrealized']:
                    if eid in resolved:
                        del resolved[eid]
                    
        return pd.DataFrame(resolved.values()) if resolved else pd.DataFrame(columns=events.columns)

    def detect_recurring_patterns(self, resolved_events):
        """
        Groups events by (description, direction, category, currency).
        Requires >= 2 occurrences to call it recurring.
        """
        patterns = []
        if resolved_events.empty:
            return patterns
            
        # Standardize salary descriptions using time-based tracks to support multiple incomes
        df = resolved_events.copy()
        df['orig_description'] = df['description']
        
        salary_events = df[df['category'] == 'salary'].sort_values('event_date')
        tracks = []
        for _, row in salary_events.iterrows():
            placed = False
            for track in tracks:
                diff = (row['event_date'] - track[-1]['event_date']).days
                if 10 <= diff <= 40:
                    track.append(row)
                    placed = True
                    break
            if not placed:
                tracks.append([row])
                
        for track in tracks:
            base_desc = track[0]['description']
            for row in track:
                df.loc[df['event_id'] == row['event_id'], 'description'] = base_desc
            
        groups = df.groupby(['description', 'direction', 'category', 'currency'])
        
        used_ids = set()
        
        def process_group(g, used):
            if len(g) >= 2:
                g = g.sort_values('event_date')
                last_event = g.iloc[-1]
                if 'final' in str(last_event.get('orig_description', last_event.get('description', ''))).lower():
                    return
                dates = g['event_date'].tolist()
                diffs = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
                
                is_fixed = last_event['flexibility'] == 'fixed'
                
                # STRICT VARIANCE CHECK: Reject if diffs vary too much (interleaved distinct events)
                if max(diffs) - min(diffs) > 5:
                    return
                    
                avg_diff = sum(diffs) / len(diffs) if diffs else 0
                cadence = None
                if 25 <= avg_diff <= 35: cadence = 'monthly'
                elif 5 <= avg_diff <= 8: cadence = 'weekly'
                elif 9 <= avg_diff <= 11: cadence = 'ten_days'
                elif 12 <= avg_diff <= 16: cadence = 'biweekly'
                elif 19 <= avg_diff <= 23: cadence = 'three_weekly'
                elif 80 <= avg_diff <= 100: cadence = 'quarterly'
                elif 360 <= avg_diff <= 370: cadence = 'yearly'
                if cadence:
                    amount = last_event['amount'] if is_fixed else (g['amount'].median() if not g['amount'].empty else last_event['amount'])
                    patterns.append({
                        'event_id_base': last_event['event_id'],
                        'description': last_event['description'],
                        'direction': last_event['direction'],
                        'category': last_event['category'],
                        'currency': last_event['currency'],
                        'flexibility': last_event['flexibility'],
                        'min_allowed_amt': last_event.get('minimum_allowed_amount'),
                        'cadence': cadence,
                        'last_date': last_event['event_date'],
                        'amount': amount
                    })
                    used.update(g['event_id'].tolist())

        for name, group in groups:
            process_group(group, used_ids)
            
        leftover = df[~df['event_id'].isin(used_ids)]
        left_flex = leftover[leftover['flexibility'] != 'fixed']
        
        if not left_flex.empty:
            cat_groups = left_flex.groupby(['category', 'direction', 'currency'])
            for name, group in cat_groups:
                process_group(group, used_ids)
                
        return patterns

    def get_user_state(self, user_id, request_date_str):
        request_date = pd.to_datetime(request_date_str)
        
        profile_df = self.dl.profiles[self.dl.profiles['user_id'] == user_id]
        if profile_df.empty:
            return None
        profile = profile_df.iloc[0].to_dict()
        
        # Get all events
        events = self.dl.events[(self.dl.events['user_id'] == user_id)].copy()
        events.set_index('event_id', inplace=True, drop=False)
        
        # 1. Fill missing amounts
        events = self.fill_missing_amounts_from_images(events)
        
        # 2. Apply messages up to request_date
        events = self.apply_message_amendments(events, user_id, request_date)
        
        # Resolve conflicts globally first
        resolved_events = self.resolve_conflicts(events)
        
        # Split past and future relative to request_date
        past_events = resolved_events[resolved_events['event_date'] <= request_date].copy()
        
        valid_past = past_events[
            (past_events['direction'] == 'debit') | 
            ((past_events['direction'] == 'credit') & (past_events['status'] == 'settled'))
        ]
        
        # Scheduled Future Events (within 90 days of request date)
        future_mask = (resolved_events['event_date'] > request_date) & (resolved_events['event_date'] <= request_date + timedelta(days=90))
        future_events = resolved_events[future_mask].copy()
        
        valid_future = pd.DataFrame()
        if not future_events.empty:
            valid_future = future_events[
                (future_events['direction'] == 'debit') | 
                ((future_events['direction'] == 'credit') & (future_events['status'] == 'settled')) |
                ((future_events['direction'] == 'credit') & (future_events['status'] == 'scheduled') & (future_events['category'] == 'salary'))
            ]
            
        # Detect patterns from past + valid future
        valid_all = pd.concat([valid_past, valid_future]) if not valid_future.empty else valid_past
        patterns = self.detect_recurring_patterns(valid_all)
        
        # Annotate patterns with profile-based flags
        annotated_patterns = []
        for p in patterns:
            cat = p['category']
            is_protected = cat in profile.get('expense_categories_to_protect', [])
            is_stop_willing = cat in profile.get('expense_categories_user_is_willing_to_stop', [])
            is_reduce_willing = cat in profile.get('expense_categories_user_is_willing_to_reduce', [])
            
            p['is_protected'] = is_protected
            p['is_stoppable'] = (not is_protected) and is_stop_willing and (p['flexibility'] == 'stoppable')
            p['is_reducible'] = (not is_protected) and is_reduce_willing and (p['flexibility'] == 'reducible')
            annotated_patterns.append(p)
            
        stoppable_future = []
        if not valid_future.empty:
            for _, ev in valid_future.iterrows():
                cat = ev['category']
                is_protected = cat in profile.get('expense_categories_to_protect', [])
                is_stop_willing = cat in profile.get('expense_categories_user_is_willing_to_stop', [])
                is_reduce_willing = cat in profile.get('expense_categories_user_is_willing_to_reduce', [])
                
                is_stoppable = (not is_protected) and is_stop_willing and (ev['flexibility'] == 'stoppable')
                is_reducible = (not is_protected) and is_reduce_willing and (ev['flexibility'] == 'reducible')
                
                if is_stoppable or is_reducible:
                    stoppable_future.append({
                        'event_id_base': ev['event_id'],
                        'description': ev['description'],
                        'direction': ev['direction'],
                        'category': ev['category'],
                        'currency': ev['currency'],
                        'flexibility': ev['flexibility'],
                        'min_allowed_amt': ev.get('minimum_allowed_amount'),
                        'amount': ev['amount'],
                        'is_stoppable': is_stoppable,
                        'is_reducible': is_reducible,
                        'date': ev['event_date']
                    })
            
        return {
            'profile': profile,
            'current_balance': profile['current_available_balance'],
            'recurring_patterns': annotated_patterns,
            'scheduled_events': valid_future.to_dict(orient='records') if not valid_future.empty else [],
            'stoppable_future': stoppable_future
        }
