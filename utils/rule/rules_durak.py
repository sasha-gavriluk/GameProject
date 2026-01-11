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

    def is_legal_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        engine = kwargs.get('engine')
        
        player_idx = engine.players.index(player)
        is_defender = (player_idx == self.defender_idx)
        
        if isinstance(action, str):
            if action == 'take': return True # Брати можна завжди
        
            if action == 'pass':
                return True

        cards_played = action if isinstance(action, list) else [action]

        for c in cards_played:
            if c not in player.hand: return False

        if is_defender:
            if len(cards_played) > len(self.pending_attacks):
                return False 

            can_transfer = self.settings['mode'] in ['perevodnoy', 'mixed'] and self.transfer_allowed
            is_transfer_attempt = False
            
            if can_transfer and len(cards_played) == len(self.pending_attacks):
                match = True
                for i in range(len(cards_played)):
                    if cards_played[i].rank != self.pending_attacks[i].rank:
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

        if action == "take":
            player.hand.extend(table)
            table.clear()
            self.pending_attacks.clear()
            print(f"> {player.name} ВЗЯВ карти.")
            if self.settings['mode'] == 'mixed': self.transfer_allowed = False
            
            # ЗАПАМ'ЯТОВУЄМО: раунд закінчився взяттям
            self.bout_ended_with_take = True 
            
        elif action == "pass":
            print(f"> {player.name} сказав БИТО.")
            table.clear()
            self.pending_attacks.clear()
            # ЗАПАМ'ЯТОВУЄМО: раунд закінчився битом
            self.bout_ended_with_take = False
            
        else:
            cards_played = action if isinstance(action, list) else [action]
            
            is_transfer = False
            if engine.players.index(player) == self.defender_idx and self.pending_attacks:
                 if len(cards_played) == len(self.pending_attacks) and self.settings['mode'] in ['perevodnoy', 'mixed'] and self.transfer_allowed:
                     if cards_played[0].rank == self.pending_attacks[0].rank:
                         is_transfer = True

            if is_transfer:
                print(f"!!! {player.name} ПЕРЕВІВ стрілки!")
                for c in cards_played:
                    player.hand.remove(c)
                    table.append(c)
                    self.pending_attacks.append(c) 
                self.is_transfer_move = True
                
            elif engine.players.index(player) == self.defender_idx:
                print(f"{player.name} відбивається.")
                for c in cards_played:
                    player.hand.remove(c)
                    table.append(c)
                    if self.pending_attacks:
                        self.pending_attacks.pop(0)
                
                if self.settings['mode'] == 'mixed': self.transfer_allowed = False
                
            else:
                print(f"{player.name} підкидає.")
                for c in cards_played:
                    player.hand.remove(c)
                    table.append(c)
                    self.pending_attacks.append(c)

    def should_switch_turn(self, action, player, **kwargs):
        engine = kwargs.get('engine')
        total_players = len(engine.players)
        
        if self.is_transfer_move:
            self.defender_idx = (engine.active_player_idx + 1) % total_players
            return self.defender_idx

        if action == "take":
            current_defender = engine.active_player_idx
            next_attacker = (current_defender + 1) % total_players
            self.defender_idx = (next_attacker + 1) % total_players 
            return next_attacker

        if action == "pass":
            next_attacker = self.defender_idx
            self.defender_idx = (next_attacker + 1) % total_players
            return next_attacker

        if len(self.pending_attacks) == 0:
            attacker_idx = (self.defender_idx - 1) % total_players
            return attacker_idx
        else:
            return self.defender_idx

    def post_move_cleanup(self, **kwargs):
        engine = kwargs.get('engine')
        
        # Якщо стіл пустий, значить раунд завершився ("Бито" або "Взято")
        if not engine.table:
            self.bout_count += 1
            self.transfer_allowed = True
            current_active_idx = engine.active_player_idx
            
            # Визначаємо, хто взяв карти (якщо дія була 'take')
            # При 'take', active_player_idx - це той, хто взяв (захисник)
            taker_player = None
            if self.bout_ended_with_take:
                taker_player = engine.players[current_active_idx]

            # Добір карт з колоди
            # Проходимо по гравцях, починаючи з поточного активного
            for i in range(len(engine.players)):
                p_idx = (current_active_idx + i) % len(engine.players)
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

    def get_winner(self, **kwargs):
        players = kwargs.get('players')
        active = [p for p in players if len(p.hand) > 0]
        deck_is_empty = (self.deck is None) or (len(self.deck.cards) == 0)
        
        if deck_is_empty and len(active) <= 1:
            if len(active) == 1: return f"Дурак: {active[0].name}"
            return "Нічия"
        return None