# utils/rule/rules_durak.py

from utils.engine import GameRules

class DurakRules(GameRules):
    def __init__(self, settings=None):
        default_settings = {
            "mode": "mixed",            
            "neighbors_only": True,     
            "allow_overthrow": True,    
            "first_bout_5": False       
        }
        self.settings = default_settings
        if settings:
            self.settings.update(settings)

        self.initial_cards_count = 6
        self.ranks_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        
        self.trump_suit = None
        self.bout_count = 0
        self.deck = None              
        
        # --- ЛОГІКА СТАНУ ---
        self.defender_idx = None      
        self.pending_attacks = []     
        self.transfer_allowed = True
        self.is_transfer_move = False 
        
        # Прапорець для відстеження, чи закінчився раунд взяттям
        self.bout_ended_with_take = False
        # Ліміт карт у поточному бою (фіксуємо на старті бою/після переводу)
        self.current_bout_limit = None
        # Хто почав поточний бій (для коректного добору після завершення)
        self.current_bout_attacker_idx = None
        # Лічильник пасів під час фази підкидання
        self.throw_passes_in_row = 0
        self._pass_finished_bout = False
        # "Реальний" поточний гравець у фазі підкидання
        self.current_throw_turn_idx = None
        # Чи вже стартувала фаза підкидання в поточному бою
        self.throw_phase_started = False
        # Захисник поточного бою (джерело істини для передачі ходу після завершення бою)
        self.round_defender_idx = None
        # Вибір захисника у неоднозначному ході (бити чи перевести)
        self.waiting_for_defense_choice = False
        self.pending_defense_choice_data = {}

    # --- UI ---
    def get_allowed_commands(self, **kwargs):
        return ['take', 'pass']

    def get_prompt_message(self, **kwargs):
        return "Введіть номер карти (або декілька через кому), 'take', 'pass':"
    # ----------

    def on_game_start(self, **kwargs):
        engine = kwargs.get('engine')
        self.deck = engine.deck

        if self.deck.cards:
            trump = self.deck.cards[0]
            self.trump_suit = trump.suit
            engine.extra_data['trump'] = trump
            print(f"=== ГРА РОЗПОЧАЛАСЯ. Козир: {trump}. ===")
        
        self.defender_idx = (engine.active_player_idx + 1) % len(engine.players)
        self.pending_attacks = []
        self.transfer_allowed = True
        self.bout_ended_with_take = False
        self.current_bout_limit = None
        self.current_bout_attacker_idx = None
        self.throw_passes_in_row = 0
        self._pass_finished_bout = False
        self.current_throw_turn_idx = None
        self.throw_phase_started = False
        self.round_defender_idx = None
        self.waiting_for_defense_choice = False
        self.pending_defense_choice_data = {}

    def set_starting_player(self, **kwargs):
        engine = kwargs.get('engine')
        if not engine or not self.trump_suit:
            return
        best_idx = None
        best_val = None
        best_card = None
        for idx, player in enumerate(engine.players):
            trumps = [c for c in player.hand if c.suit == self.trump_suit]
            if not trumps:
                continue
            min_card = min(trumps, key=lambda c: self.ranks_values.get(c.rank, 0))
            min_val = self.ranks_values.get(min_card.rank, 0)
            if best_val is None or min_val < best_val:
                best_val = min_val
                best_idx = idx
                best_card = min_card
        if best_idx is not None:
            engine.active_player_idx = best_idx
            if best_card:
                engine.extra_data['starting_trump'] = {
                    'player_id': engine.players[best_idx].player_id,
                    'suit': best_card.suit,
                    'rank': best_card.rank
                }
        self.defender_idx = (engine.active_player_idx + 1) % len(engine.players)
        self.pending_attacks = []
        self.transfer_allowed = True
        self.current_bout_limit = None
        self.current_bout_attacker_idx = None
        self.throw_passes_in_row = 0
        self._pass_finished_bout = False
        self.current_throw_turn_idx = None
        self.throw_phase_started = False
        self.round_defender_idx = None
        self.waiting_for_defense_choice = False
        self.pending_defense_choice_data = {}

    def _has_cards(self, engine, idx):
        return 0 <= idx < len(engine.players) and len(engine.players[idx].hand) > 0

    def _active_with_cards(self, engine):
        return [i for i, p in enumerate(engine.players) if len(p.hand) > 0]

    def _ensure_valid_defender(self, engine):
        if self.defender_idx is None:
            return
        if self._has_cards(engine, self.defender_idx):
            return
        total = len(engine.players)
        for hop in range(1, total + 1):
            cand = (self.defender_idx + hop) % total
            if self._has_cards(engine, cand):
                self.defender_idx = cand
                return

    def _eligible_throwers(self, engine):
        self._ensure_valid_defender(engine)
        # У чистому перевідному підкидання не допускається.
        if self.settings.get("mode") == "perevodnoy":
            return []
        active = self._active_with_cards(engine)
        if self.defender_idx not in active:
            return []
        if not self.settings.get('neighbors_only', True) or len(active) <= 2:
            return [i for i in active if i != self.defender_idx]
        pos = active.index(self.defender_idx)
        left = active[(pos - 1) % len(active)]
        right = active[(pos + 1) % len(active)]
        if left == right:
            return [left] if left != self.defender_idx else []
        return [left, right]

    def _ordered_throwers(self, engine, start_idx=None):
        throwers = self._eligible_throwers(engine)
        if not throwers:
            return []
        throwers_set = set(throwers)
        total = len(engine.players)
        if start_idx is None:
            start_idx = self.current_bout_attacker_idx
        if start_idx not in throwers_set:
            # Якщо попередній гравець вже не може підкидати (наприклад, вийшов),
            # беремо наступного по колу, а не "першого в масиві".
            picked = None
            if start_idx is None:
                start_idx = 0
            for hop in range(1, total + 1):
                cand = (start_idx + hop) % total
                if cand in throwers_set:
                    picked = cand
                    break
            start_idx = picked if picked is not None else throwers[0]

        order = [start_idx]
        for hop in range(1, total + 1):
            cand = (start_idx + hop) % total
            if cand in throwers_set and cand not in order:
                order.append(cand)
        return order

    def _next_thrower_idx(self, engine, current_idx):
        order = self._ordered_throwers(engine, start_idx=self.current_bout_attacker_idx)
        if not order:
            return None
        if current_idx in order:
            return order[(order.index(current_idx) + 1) % len(order)]
        return order[0]

    def _next_with_cards(self, engine, start_idx, exclude_idx=None):
        total_players = len(engine.players)
        for i in range(total_players):
            idx = (start_idx + i) % total_players
            if exclude_idx is not None and idx == exclude_idx:
                continue
            if len(engine.players[idx].hand) > 0:
                return idx
        return start_idx % total_players

    def _next_attacker_after_bito(self, engine):
        round_def = self.round_defender_idx if self.round_defender_idx is not None else self.defender_idx
        # Після "Бито" хід завжди починає запам'ятаний захисник поточного бою.
        # Виняток "взяв карти" обробляється окремо в гілці action == "take".
        if round_def is not None:
            next_attacker = round_def
        else:
            # Аварійний fallback, якщо стан бою був неповним.
            next_attacker = engine.active_player_idx if engine.players else 0
        self.defender_idx = self._next_with_cards(engine, next_attacker + 1)
        self.current_bout_limit = None
        self.current_bout_attacker_idx = None
        self.current_throw_turn_idx = None
        self.round_defender_idx = None
        return next_attacker

    def _finish_bito(self, table):
        table.clear()
        self.pending_attacks.clear()
        self.bout_ended_with_take = False
        self.throw_passes_in_row = 0
        self._pass_finished_bout = True
        self.current_throw_turn_idx = None
        self.throw_phase_started = False
        self.waiting_for_defense_choice = False
        self.pending_defense_choice_data = {}

    def _is_transfer_possible(self, cards_played, table):
        if not self.pending_attacks:
            return False
        # Якщо хоч одна атака вже побита, переводити не можна.
        beaten_pairs = (len(table) - len(self.pending_attacks)) // 2
        if beaten_pairs > 0:
            return False
        # Переводимо 1..N картами, але не більше кількості невідбитих атак.
        if len(cards_played) == 0 or len(cards_played) > len(self.pending_attacks):
            return False
        if self.settings['mode'] not in ['perevodnoy', 'mixed'] or not self.transfer_allowed:
            return False
        target_rank = self.pending_attacks[0].rank
        return all(c.rank == target_rank for c in cards_played)

    def _is_beating_set(self, cards_played):
        if len(cards_played) > len(self.pending_attacks):
            return False
        for i in range(len(cards_played)):
            def_card = cards_played[i]
            att_card = self.pending_attacks[i]
            beat_suit = (def_card.suit == att_card.suit and self.ranks_values[def_card.rank] > self.ranks_values[att_card.rank])
            beat_trump = (def_card.suit == self.trump_suit and att_card.suit != self.trump_suit)
            if not (beat_suit or beat_trump):
                return False
        return True

    def _apply_transfer_cards(self, player, cards_played, table):
        print(f"!!! {player.name} ПЕРЕВІВ стрілки!")
        for c in cards_played:
            player.hand.remove(c)
            table.append(c)
            self.pending_attacks.append(c)
        self.is_transfer_move = True

    def _apply_defense_cards(self, player, cards_played, table):
        print(f"{player.name} відбивається.")
        for c in cards_played:
            player.hand.remove(c)
            table.append(c)
            if self.pending_attacks:
                self.pending_attacks.pop(0)
        if self.settings['mode'] == 'mixed':
            self.transfer_allowed = False

    def _attack_cards_count_on_table(self, table):
        # На столі: 2*биті_пари + невідбиті_атаки.
        # Кількість атак = биті_пари + невідбиті_атаки.
        # => attacks = (len(table) + len(pending_attacks)) // 2
        return (len(table) + len(self.pending_attacks)) // 2

    def is_legal_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        engine = kwargs.get('engine')
        table = table if table is not None else []
        self._ensure_valid_defender(engine)

        if isinstance(action, dict):
            if action.get('action') == 'set_durak_defense_choice':
                return self.waiting_for_defense_choice
            return False
        
        player_idx = engine.players.index(player)
        is_defender = (player_idx == self.defender_idx)
        defender = engine.players[self.defender_idx] if self.defender_idx is not None else None
        if self.current_bout_limit is not None:
            max_cards_on_table = self.current_bout_limit
        else:
            max_cards_on_table = 6
            if defender:
                max_cards_on_table = min(6, len(defender.hand))

        def is_allowed_attacker():
            if not self.settings.get('neighbors_only', True):
                return True
            active_idxs = self._active_with_cards(engine)
            if len(active_idxs) <= 2:
                return True
            if self.defender_idx not in active_idxs:
                return False
            pos = active_idxs.index(self.defender_idx)
            left = active_idxs[(pos - 1) % len(active_idxs)]
            right = active_idxs[(pos + 1) % len(active_idxs)]
            return player_idx in (left, right)
        
        if isinstance(action, str):
            if action == 'take':
                # Брати може тільки захисник
                return is_defender
        
            if action == 'pass':
                # У чистому перевідному підкидання/бито кнопкою не використовується.
                if self.settings.get("mode") == "perevodnoy":
                    return False
                # "Бито" може сказати тільки атакуючий, коли відбито всі атаки
                if is_defender:
                    return False
                if not is_allowed_attacker():
                    return False
                if not table:
                    return False
                if len(self.pending_attacks) > 0:
                    return False
                return True

        cards_played = action if isinstance(action, list) else [action]

        for c in cards_played:
            if c not in player.hand: return False

        if is_defender:
            if len(cards_played) > len(self.pending_attacks):
                return False 

            can_transfer = self.settings['mode'] in ['perevodnoy', 'mixed'] and self.transfer_allowed
            is_transfer_attempt = False
            
            beaten_pairs = (len(table) - len(self.pending_attacks)) // 2
            if can_transfer and beaten_pairs == 0 and len(cards_played) > 0 and len(cards_played) <= len(self.pending_attacks):
                match = True
                for i in range(len(cards_played)):
                    if cards_played[i].rank != self.pending_attacks[0].rank:
                        match = False; break
                if match: is_transfer_attempt = True

            if is_transfer_attempt:
                return True

            for i in range(len(cards_played)):
                def_card = cards_played[i]
                att_card = self.pending_attacks[i] 
                
                beat_suit = (def_card.suit == att_card.suit and self.ranks_values[def_card.rank] > self.ranks_values[att_card.rank])
                beat_trump = (def_card.suit == self.trump_suit and att_card.suit != self.trump_suit)
                
                if not (beat_suit or beat_trump):
                    return False
            
            return True

        else:
            if not is_allowed_attacker():
                return False
            # У чистому перевідному після стартової атаки підкидати не можна.
            if self.settings.get("mode") == "perevodnoy" and table:
                return False
            if not self.settings.get('allow_overthrow', True) and table:
                return False

            # Ліміт 6/ліміт захисника застосовується тільки до кількості атак, а не всіх карт на столі.
            attacks_on_table = self._attack_cards_count_on_table(table)
            if attacks_on_table + len(cards_played) > max_cards_on_table:
                return False
            if not table:
                first_rank = cards_played[0].rank
                for c in cards_played:
                    if c.rank != first_rank: return False
                return True
            
            ranks_on_table = [c.rank for c in table]
            for c in cards_played:
                if c.rank not in ranks_on_table:
                    return False
            
            return True

    def execute_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        engine = kwargs.get('engine')
        self.is_transfer_move = False 
        self._pass_finished_bout = False

        if isinstance(action, dict) and action.get('action') == 'set_durak_defense_choice':
            if not self.waiting_for_defense_choice:
                return
            data = self.pending_defense_choice_data
            saved_cards = list(data.get("cards", []))
            saved_player_id = data.get("player_id")
            if not saved_cards or player.player_id != saved_player_id:
                self.waiting_for_defense_choice = False
                self.pending_defense_choice_data = {}
                return

            choice = action.get('choice')
            transfer_possible = self._is_transfer_possible(saved_cards, table)
            beat_possible = self._is_beating_set(saved_cards)

            self.waiting_for_defense_choice = False
            self.pending_defense_choice_data = {}
            engine.extra_data["_resolved_action"] = list(saved_cards)

            if choice == 'transfer' and transfer_possible:
                self._apply_transfer_cards(player, saved_cards, table)
            elif beat_possible:
                print(f"[DEFENSE] {player.name} обрав БИТИ ({len(saved_cards)} карт).")
                self._apply_defense_cards(player, saved_cards, table)
            elif transfer_possible:
                self._apply_transfer_cards(player, saved_cards, table)
            return

        if action == "take":
            player.hand.extend(table)
            table.clear()
            self.pending_attacks.clear()
            print(f"> {player.name} ВЗЯВ карти.")
            if self.settings['mode'] == 'mixed': self.transfer_allowed = False
            
            # ЗАПАМ'ЯТОВУЄМО: раунд закінчився взяттям
            self.bout_ended_with_take = True 
            self.throw_passes_in_row = 0
            self.current_throw_turn_idx = None
            self.throw_phase_started = False
            
        elif action == "pass":
            # У фазі підкидання pass означає "я не підкидаю".
            # Раунд закриваємо "Бито" тільки коли всі причетні пасанули.
            self.throw_phase_started = True
            self.throw_passes_in_row += 1
            throwers_count = len(self._ordered_throwers(engine, start_idx=self.current_bout_attacker_idx))
            if throwers_count <= 1 or self.throw_passes_in_row >= throwers_count:
                print(f"> {player.name} сказав БИТО.")
                self._finish_bito(table)
            else:
                print(f"> {player.name} пасує у фазі підкидання.")
            
        else:
            cards_played = action if isinstance(action, list) else [action]
            is_defender = (engine.players.index(player) == self.defender_idx)

            if is_defender:
                transfer_possible = self._is_transfer_possible(cards_played, table)
                beat_possible = self._is_beating_set(cards_played)

                if transfer_possible and beat_possible:
                    if hasattr(player, 'think'):
                        self._apply_transfer_cards(player, cards_played, table)
                    else:
                        self.waiting_for_defense_choice = True
                        self.pending_defense_choice_data = {
                            "player_id": player.player_id,
                            "cards": list(cards_played),
                        }
                        engine.extra_data["_resolved_action"] = None
                        engine.notify("SHOW_DURAK_DEFENSE_CHOICE", player_id=player.player_id)
                    return

                if transfer_possible:
                    self._apply_transfer_cards(player, cards_played, table)
                else:
                    self._apply_defense_cards(player, cards_played, table)
                    
                    # --- АВТОВІДБІЙ (перенесено сюди для правильного добору карт) ---
                    if len(self.pending_attacks) == 0:
                        max_cards = self.current_bout_limit if self.current_bout_limit is not None else 6
                        attacks_on_table = self._attack_cards_count_on_table(table)
                        order = self._ordered_throwers(engine, start_idx=self.current_bout_attacker_idx)
                        
                        if len(player.hand) == 0 or attacks_on_table >= max_cards or self.settings.get("mode") == "perevodnoy" or not order:
                            print("> Спрацював автоматичний відбій.")
                            self._finish_bito(table)
                
            else:
                print(f"{player.name} підкидає.")
                # Перший атакуючий хід у бою фіксує ліміт та стартового атакуючого.
                if not table:
                    defender = engine.players[self.defender_idx]
                    self.current_bout_limit = min(6, len(defender.hand))
                    self.current_bout_attacker_idx = engine.players.index(player)
                    self.current_throw_turn_idx = self.current_bout_attacker_idx
                    self.throw_phase_started = False
                    self.round_defender_idx = self.defender_idx
                else:
                    self.current_throw_turn_idx = engine.players.index(player)
                    self.throw_phase_started = True
                for c in cards_played:
                    player.hand.remove(c)
                    table.append(c)
                    self.pending_attacks.append(c)
                self.throw_passes_in_row = 0

    def should_switch_turn(self, action, player, **kwargs):
        engine = kwargs.get('engine')
        self._ensure_valid_defender(engine)
        table = kwargs.get('table') or []

        if self.waiting_for_defense_choice:
            return engine.active_player_idx

        if self.is_transfer_move:
            self.defender_idx = self._next_with_cards(engine, engine.active_player_idx + 1)
            self.current_bout_limit = min(6, len(engine.players[self.defender_idx].hand))
            self.throw_passes_in_row = 0
            self.current_throw_turn_idx = None
            self.throw_phase_started = False
            self.round_defender_idx = self.defender_idx
            self.current_bout_attacker_idx = engine.active_player_idx 
            return self.defender_idx

        if action == "take":
            current_defender = self.round_defender_idx
            if current_defender is None:
                current_defender = engine.active_player_idx
            next_attacker = self._next_with_cards(engine, current_defender + 1, exclude_idx=None)
            self.defender_idx = self._next_with_cards(engine, next_attacker + 1)
            self.throw_passes_in_row = 0
            self.current_throw_turn_idx = None
            self.throw_phase_started = False
            self.round_defender_idx = None
            return next_attacker

        # Якщо стіл порожній, значить раунд щойно успішно завершився (Бито)
        # (execute_move очистив стіл: або по команді 'pass', або через авто-відбій)
        if len(table) == 0:
            engine.notify("TABLE_CLEARED")
            return self._next_attacker_after_bito(engine)

        if action == "pass":
            # Якщо ми тут, а стіл не порожній, значить це звичайний пас одного гравця у фазі підкидання
            next_thrower = self._next_thrower_idx(engine, engine.active_player_idx)
            self.current_throw_turn_idx = next_thrower
            return next_thrower if next_thrower is not None else engine.active_player_idx

        # Якщо є ще невідбиті атаки, хід ОБОВ'ЯЗКОВО залишається за захисником
        if len(self.pending_attacks) > 0:
            if len(engine.players[self.defender_idx].hand) == 0:
                self.defender_idx = self._next_with_cards(engine, self.defender_idx + 1)
            return self.defender_idx

        # Якщо всі поточні карти відбиті, починається (або триває) фаза підкидання
        self.throw_passes_in_row = 0
        order = self._ordered_throwers(engine, start_idx=self.current_bout_attacker_idx)
        
        if not self.throw_phase_started:
            self.throw_phase_started = True
            self.current_throw_turn_idx = order[0]
            return order[0]

        throw_from = self.current_throw_turn_idx
        if throw_from is None:
            throw_from = self.current_bout_attacker_idx
        
        if throw_from in order:
            return throw_from
            
        next_thrower = self._next_thrower_idx(engine, throw_from)
        self.current_throw_turn_idx = next_thrower
        return next_thrower

    def post_move_cleanup(self, **kwargs):
        engine = kwargs.get('engine')
        
        # Якщо стіл пустий, значить раунд завершився ("Бито" або "Взято")
        if not engine.table:
            self.bout_count += 1
            self.transfer_allowed = True
            # Добір у Дураку йде від стартового атакуючого поточного бою.
            start_draw_idx = self.current_bout_attacker_idx
            if start_draw_idx is None:
                start_draw_idx = engine.active_player_idx
            current_active_idx = engine.active_player_idx
            
            # Визначаємо, хто взяв карти (якщо дія була 'take')
            # При 'take', active_player_idx - це той, хто взяв (захисник)
            taker_player = None
            if self.bout_ended_with_take:
                taker_player = engine.players[current_active_idx]

            # Добір карт з колоди
            # Проходимо по гравцях, починаючи зі стартового атакуючого бою.
            for i in range(len(engine.players)):
                p_idx = (start_draw_idx + i) % len(engine.players)
                player = engine.players[p_idx]
                
                # === ВИПРАВЛЕННЯ: Пропускаємо того, хто ВЗЯВ карти ===
                if player == taker_player:
                    continue
                # =====================================================

                needed = 6 - len(player.hand)
                if self.settings['first_bout_5'] and self.bout_count == 1: 
                    needed = 5 - len(player.hand)
                
                if needed > 0 and engine.deck.cards:
                    engine.draw_cards(player, needed)
            
            # Скидаємо прапорець
            self.bout_ended_with_take = False
            self.current_bout_limit = None
            self.current_bout_attacker_idx = None
            self.throw_passes_in_row = 0
            self._pass_finished_bout = False
            self.current_throw_turn_idx = None
            self.throw_phase_started = False
            # Важливо: round_defender_idx очищається у should_switch_turn
            # після визначення, хто починає наступний бій.

    def get_winner(self, **kwargs):
        players = kwargs.get('players')
        active = [p for p in players if len(p.hand) > 0]
        deck_is_empty = (self.deck is None) or (len(self.deck.cards) == 0)
        
        if deck_is_empty and len(active) <= 1:
            if len(active) == 1: return f"Дурак: {active[0].name}"
            return "Нічия"
        return None
