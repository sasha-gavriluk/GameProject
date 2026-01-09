# Code/utils/engine.py
class Player:
    def __init__(self, name, player_id=None, **kwargs):
        # Викликаємо super, щоб передати керування далі по ланцюжку (до object або інших класів)
        super().__init__(**kwargs)
        self.name = name
        self.player_id = player_id or name
        self.hand = []
        self.is_attacker = False

    def add_card(self, card):
        self.hand.append(card)

    def remove_card(self, card):
        if card in self.hand:
            self.hand.remove(card)

    def has_cards(self):
        return len(self.hand) > 0

    def __repr__(self):
        return f"Player(id={self.player_id}, name={self.name}, cards={len(self.hand)})"

class GameRules:
    """
    Базовий клас правил. 
    Використовує **kwargs, щоб приймати будь-які параметри від двигуна,
    не ламаючи сумісність.
    """
    def on_game_start(self, **kwargs):
        pass

    def is_legal_move(self, action, player, **kwargs):
        raise NotImplementedError
        
    def execute_move(self, action, player, **kwargs):
        raise NotImplementedError

    def get_winner(self, **kwargs):
        raise NotImplementedError

    def should_switch_turn(self, action, player, **kwargs):
        return True
    
    def post_move_cleanup(self, **kwargs):
        pass

    def get_allowed_commands(self, **kwargs):
        """Повертає список текстових команд (напр. ['take', 'pass'])."""
        return []

    def get_prompt_message(self, **kwargs):
        """Повертає текст підказки для гравця."""
        return "Введіть номер карти для ходу:"

class GameEngine:
    def __init__(self, rules: GameRules):
        self.rules = rules
        self.players = []
        self.deck = None
        self.table = []
        self.active_player_idx = 0
        self.game_over = False
        self.extra_data = {} 

    def add_player(self, player: Player):
        self.players.append(player)

    def setup_game(self, deck_object):
        self.deck = deck_object
        self.deck.shuffle()
        
        count = self.rules.initial_cards_count
        for player in self.players:
            player.clear_hand()
            for _ in range(count):
                card = self.deck.deal()
                if card:
                    player.receive_card(card)
        
        # ВИПРАВЛЕННЯ: передаємо engine як іменований аргумент
        self.rules.on_game_start(engine=self)

    def draw_cards(self, player, count):
        for _ in range(count):
            if self.deck and len(self.deck.cards) > 0:
                card = self.deck.deal()
                player.receive_card(card)

    def play_turn(self, player_action):
        current_player = self.players[self.active_player_idx]
        
        # Збираємо контекст — все, що може знадобитись правилам
        context = {
            "table": self.table,
            "engine": self,
            "deck": self.deck,
            "players": self.players
        }
        
        # 1. Перевірка
        # action і player передаємо явно, решту через **context
        if not self.rules.is_legal_move(action=player_action, player=current_player, **context):
            print(f"Хід неможливий: {player_action}")
            return False 

        # 2. Виконання
        self.rules.execute_move(action=player_action, player=current_player, **context)

        # 3. Очищення
        self.rules.post_move_cleanup(**context)

        # 4. Перевірка переможця
        winner = self.rules.get_winner(**context)
        if winner:
            self.game_over = True
            return f"Переміг {winner}!"

        # 5. Перехід ходу
        switch_result = self.rules.should_switch_turn(action=player_action, player=current_player, **context)

        if isinstance(switch_result, int) and not isinstance(switch_result, bool):
            self.active_player_idx = switch_result % len(self.players)
        elif switch_result is True:
            self.active_player_idx = (self.active_player_idx + 1) % len(self.players)
        
        return True