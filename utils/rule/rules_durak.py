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
        
        # --- НОВА ЛОГІКА СТАНУ ---
        self.defender_idx = None      
        self.pending_attacks = []     # Карти на столі, які треба побити
        self.transfer_allowed = True
        self.is_transfer_move = False 

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

    def is_legal_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        engine = kwargs.get('engine')
        
        player_idx = engine.players.index(player)
        is_defender = (player_idx == self.defender_idx)
        
        # 1. КОМАНДИ
        if isinstance(action, str):
            if action == "take":
                # ВИПРАВЛЕНО: Можна брати, якщо ти захисник і на столі є карти
                return is_defender and len(table) > 0
            if action == "pass":
                # Можна пасувати, якщо ти НЕ захисник і всі атаки відбиті
                # (або якщо черга атакуючого, а він не хоче додавати)
                return not is_defender and len(table) > 0 and len(self.pending_attacks) == 0

        # 2. ПЕРЕТВОРЕННЯ В СПИСОК
        # Працюємо завжди зі списком карток для зручності
        cards_played = action if isinstance(action, list) else [action]

        # Перевірка наявності карт в руці (технічна)
        for c in cards_played:
            if c not in player.hand: return False

        # --- ЗАХИСТ ---
        if is_defender:
            # Захисник має побити карти з pending_attacks.
            # 1. Перевірка кількості: захисник може бити по одній або всі зразу
            # Але для простоти вашого запиту: карти накладаються на список pending_attacks.
            if len(cards_played) > len(self.pending_attacks):
                return False # Не можна покласти більше карт захисту, ніж є загроз

            # 2. Логіка ПЕРЕВЕДЕННЯ (Тільки якщо кладемо стільки ж карт, скільки загроз)
            # Приклад: атакують двома 5. Треба перевести двома 5.
            can_transfer = self.settings['mode'] in ['perevodnoy', 'mixed'] and self.transfer_allowed
            is_transfer_attempt = False
            
            if can_transfer and len(cards_played) == len(self.pending_attacks):
                match = True
                for i in range(len(cards_played)):
                    # Ранги мають співпадати з картами атаки
                    if cards_played[i].rank != self.pending_attacks[i].rank:
                        match = False; break
                if match: is_transfer_attempt = True

            if is_transfer_attempt:
                return True

            # 3. Логіка БИТТЯ
            # Перевіряємо кожну пару (Карта Захисту vs Карта Атаки)
            for i in range(len(cards_played)):
                def_card = cards_played[i]
                att_card = self.pending_attacks[i] # Б'ємо перші у списку черги
                
                beat_suit = (def_card.suit == att_card.suit and self.ranks_values[def_card.rank] > self.ranks_values[att_card.rank])
                beat_trump = (def_card.suit == self.trump_suit and att_card.suit != self.trump_suit)
                
                if not (beat_suit or beat_trump):
                    return False
            
            return True

        # --- АТАКА / ПІДКИДАННЯ ---
        else:
            # Атакуючий кидає карти.
            # 1. Якщо стіл пустий -> можна все, але карти мають бути одного рангу (якщо їх декілька)
            if not table:
                first_rank = cards_played[0].rank
                for c in cards_played:
                    if c.rank != first_rank: return False
                return True
            
            # 2. Якщо підкидання -> ранги мають бути на столі
            ranks_on_table = [c.rank for c in table]
            for c in cards_played:
                if c.rank not in ranks_on_table:
                    return False
            
            # TODO: Перевірка ліміту карт захисника
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
            
        elif action == "pass":
            print(f"> {player.name} сказав БИТО.")
            table.clear()
            self.pending_attacks.clear()
            
        else:
            cards_played = action if isinstance(action, list) else [action]
            
            # Перевірка на переведення (в execute легше перевірити факт)
            is_transfer = False
            if engine.players.index(player) == self.defender_idx and self.pending_attacks:
                 if len(cards_played) == len(self.pending_attacks) and self.settings['mode'] in ['perevodnoy', 'mixed'] and self.transfer_allowed:
                     if cards_played[0].rank == self.pending_attacks[0].rank:
                         is_transfer = True

            if is_transfer:
                print(f"!!! {player.name} ПЕРЕВІВ стрілки!")
                # При переведенні карти додаються до "Атак" для наступного гравця
                for c in cards_played:
                    player.hand.remove(c)
                    table.append(c)
                    self.pending_attacks.append(c) # Список загроз росте
                self.is_transfer_move = True
                
            elif engine.players.index(player) == self.defender_idx:
                # Це звичайний захист
                print(f"{player.name} відбивається.")
                for c in cards_played:
                    player.hand.remove(c)
                    table.append(c)
                    # Видаляємо першу карту зі списку загроз (бо ми її побили)
                    if self.pending_attacks:
                        self.pending_attacks.pop(0)
                
                if self.settings['mode'] == 'mixed': self.transfer_allowed = False
                
            else:
                # Це атака/підкидання
                print(f"{player.name} підкидає.")
                for c in cards_played:
                    player.hand.remove(c)
                    table.append(c)
                    self.pending_attacks.append(c) # Нова загроза для захисника

    def should_switch_turn(self, action, player, **kwargs):
        engine = kwargs.get('engine')
        total_players = len(engine.players)
        
        if self.is_transfer_move:
            # Захисник стає наступний
            self.defender_idx = (engine.active_player_idx + 1) % total_players
            return self.defender_idx

        if action == "take":
            # Захисник пропускає хід
            current_defender = engine.active_player_idx
            next_attacker = (current_defender + 1) % total_players
            self.defender_idx = (next_attacker + 1) % total_players 
            return next_attacker

        if action == "pass":
            # Бито -> Захисник стає Атакуючим
            next_attacker = self.defender_idx
            self.defender_idx = (next_attacker + 1) % total_players
            return next_attacker

        # Карти
        # Якщо всі загрози відбиті (pending_attacks пустий) -> черга Атакуючих підкидати
        if len(self.pending_attacks) == 0:
            attacker_idx = (self.defender_idx - 1) % total_players
            return attacker_idx
        else:
            # Є невідбиті карти -> черга Захисника
            return self.defender_idx

    def post_move_cleanup(self, **kwargs):
        engine = kwargs.get('engine')
        if not engine.table:
            self.bout_count += 1
            self.transfer_allowed = True
            current = engine.active_player_idx
            # Добір
            for i in range(len(engine.players)):
                p_idx = (current + i) % len(engine.players)
                player = engine.players[p_idx]
                needed = 6 - len(player.hand)
                if self.settings['first_bout_5'] and self.bout_count == 1: needed = 5 - len(player.hand)
                if needed > 0 and engine.deck.cards:
                    engine.draw_cards(player, needed)

    def get_winner(self, **kwargs):
        players = kwargs.get('players')
        active = [p for p in players if len(p.hand) > 0]
        deck_is_empty = (self.deck is None) or (len(self.deck.cards) == 0)
        
        if deck_is_empty and len(active) <= 1:
            if len(active) == 1: return f"Дурак: {active[0].name}"
            return "Нічия"
        return None