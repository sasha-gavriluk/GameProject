# utils/engine.py
import random

class Player:
    def __init__(self, name, player_id=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.player_id = player_id or name
        self.hand = []
        self.is_attacker = False
        self.score = 0

    def add_card(self, card):
        self.hand.append(card)

    def remove_card(self, card):
        if card in self.hand:
            self.hand.remove(card)
    
    def clear_hand(self):
        self.hand = []

    def receive_card(self, card):
        self.add_card(card)

    def has_cards(self):
        return len(self.hand) > 0

    def __repr__(self):
        return f"Player(id={self.player_id}, name={self.name}, cards={len(self.hand)})"

class GameRules:
    """
    Базовий клас правил.
    """
    def on_game_start(self, **kwargs): pass
    def is_legal_move(self, action, player, **kwargs): raise NotImplementedError
    def execute_move(self, action, player, **kwargs): raise NotImplementedError
    def get_winner(self, **kwargs): raise NotImplementedError
    def should_switch_turn(self, action, player, **kwargs): return True
    def post_move_cleanup(self, **kwargs): pass
    def get_allowed_commands(self, **kwargs): return []
    def get_prompt_message(self, **kwargs): return "Введіть номер карти:"

class GameEngine:
    def __init__(self, rules: GameRules):
        self.rules = rules
        self.players = []
        self.deck = None
        self.table = []
        self.active_player_idx = 0
        self.game_over = False
        self.extra_data = {} 
        
        # --- НОВЕ: Система подій (Observer) ---
        # Сюди ми підключимо обробник з PlayGameScreen
        self.on_game_event = None 

    def notify(self, event_type, **kwargs):
        """Відправляє подію назовні (у GUI)"""
        if self.on_game_event:
            self.on_game_event(event_type, kwargs)

    def add_player(self, player: Player):
        self.players.append(player)

    def setup_game(self, deck_object):
        """Підготовка до гри (перемішування, роздача)"""
        self.deck = deck_object
        self.deck.shuffle()
        
        # Очищення рук перед новою грою
        for player in self.players:
            player.clear_hand()
        
        # Передаємо engine у правила для ініціалізації
        self.rules.on_game_start(engine=self)

    def start_game(self):
        """Явний запуск гри і сповіщення UI"""
        # Сповіщаємо, що гра почалась (наприклад, щоб показати козиря)
        self.notify("GAME_START", trump=self.extra_data.get('trump'))
        
        # Виконуємо початкову роздачу
        count = self.rules.initial_cards_count
        # Роздаємо по колу (як у реальності), щоб це виглядало гарно
        # Або просто роздаємо всім по черзі
        for _ in range(count):
            for player in self.players:
                if self.deck and len(self.deck.cards) > 0:
                    card = self.deck.deal()
                    player.receive_card(card)
        
        # Сповіщаємо візуал, що треба намалювати карти в руках
        self.notify("DEAL_CARDS")

    def draw_cards(self, player, count):
        """Взяття карт з колоди з оповіщенням"""
        cards_drawn = []
        for _ in range(count):
            if self.deck and len(self.deck.cards) > 0:
                card = self.deck.deal()
                player.receive_card(card)
                cards_drawn.append(card)
        
        # === ЗМІНА: Відправляємо специфічну подію для колоди ===
        if cards_drawn:
            # Передаємо також залишок у колоді, щоб оновити лічильник
            self.notify("PLAYER_DRAW_DECK", player=player, cards=cards_drawn, deck_count=len(self.deck.cards))

    def play_turn(self, player_action):
        """
        Основний метод ходу.
        Обробляє логіку ходу, визначення переможця раунду (Війна) та переможця гри.
        """
        if self.game_over:
            return False

        current_player = self.players[self.active_player_idx]
        
        context = {
            "table": self.table,
            "engine": self,
            "deck": self.deck,
            "players": self.players
        }
        
        # 1. Перевірка легальності ходу
        if not self.rules.is_legal_move(action=player_action, player=current_player, **context):
            print(f"Illegal move by {current_player.name}: {player_action}")
            self.notify("INVALID_MOVE", player=current_player, error="Цей хід неможливий")
            return False 

        # 2. Виконання ходу (зміна стану)
        self.rules.execute_move(action=player_action, player=current_player, **context)
        self.notify("PLAYER_MOVE", player=current_player, action=player_action)

        # 3. Перевірка результату ходу (Переможець раунду або гри)
        result = self.rules.get_winner(**context)

        # === ЛОГІКА ДЛЯ ВІЙНИ (Round Winner) ===
        # Якщо get_winner повертає int (індекс гравця), це означає перемогу в РАУНДІ
        if isinstance(result, int):
            winner_player = self.players[result]
            print(f"Раунд виграв: {winner_player.name}")

            # 3.1. Переможець забирає карти
            cards_on_table = list(self.table) # Копіюємо список
            winner_player.hand.extend(cards_on_table)
            
            # 3.2. Сповіщаємо візуал (карти летять до переможця)
            self.notify("PLAYER_TOOK_CARDS", player=winner_player, cards=cards_on_table)
            
            # 3.3. Очищаємо стіл
            self.table.clear()
            self.notify("TABLE_CLEARED")

            # 3.4. Переможець ходить наступним
            self.active_player_idx = result
            
            # 3.5. Перевірка на кінець гри для Війни (якщо у когось закінчились карти)
            # У Війні програє той, у кого 0 карт.
            alive_players = [p for p in self.players if len(p.hand) > 0]
            if len(alive_players) == 1:
                game_winner = alive_players[0].name
                self.game_over = True
                self.notify("GAME_OVER", winner=game_winner)
                return f"Переміг {game_winner}!"
            
            # Раунд завершено, хід передано, виходимо
            return True

        # === ЛОГІКА ДЛЯ ІНШИХ ІГОР (Game Winner) ===
        # Якщо get_winner повертає рядок або об'єкт, це кінець гри
        elif result is not None:
            self.game_over = True
            self.notify("GAME_OVER", winner=result)
            return f"Переміг {result}!"

        # 4. Якщо переможця немає — продовжуємо гру
        self.rules.post_move_cleanup(**context)
        
        # Специфічна перевірка для Дурака (очищення столу при "pass"/Бито)
        if not self.table and player_action == "pass":
             self.notify("TABLE_CLEARED")

        # 5. Перехід ходу
        switch_result = self.rules.should_switch_turn(action=player_action, player=current_player, **context)

        prev_idx = self.active_player_idx
        if isinstance(switch_result, int) and not isinstance(switch_result, bool):
            self.active_player_idx = switch_result % len(self.players)
        elif switch_result is True:
            self.active_player_idx = (self.active_player_idx + 1) % len(self.players)
        
        # Оповіщаємо про зміну ходу
        if prev_idx != self.active_player_idx:
            self.notify("TURN_SWITCH", active_player_idx=self.active_player_idx)
        
        return True