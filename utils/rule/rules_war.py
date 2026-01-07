from utils.engine import GameRules

class WarRules(GameRules):
    def __init__(self):
        self.initial_cards_count = 26
        self.ranks_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }

    # --- UI налаштування ---
    def get_allowed_commands(self, **kwargs):
        return [] # У війні немає текстових команд, тільки карти

    def get_prompt_message(self, **kwargs):
        return "Ваш хід! Введіть номер карти:"
    # -----------------------

    def on_game_start(self, **kwargs):
        pass
    
    def is_legal_move(self, action, player, **kwargs):
        if isinstance(action, list):
            return False # Війна не підтримує мульти-хід
        return True

    def execute_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        player.hand.remove(action)
        table.append(action)
        print(f"{player.name} поклав {action}")

    def should_switch_turn(self, action, player, **kwargs):
        return True
    
    def post_move_cleanup(self, **kwargs):
        pass

    def get_winner(self, **kwargs):
        table = kwargs.get('table')
        players = kwargs.get('players')
        
        if len(table) < 2:
            return None

        card1 = table[-2]
        card2 = table[-1]
        val1 = self.ranks_values[card1.rank]
        val2 = self.ranks_values[card2.rank]

        if val1 > val2:
            print(f"Раунд за {players[0].name}!")
            players[0].hand.extend(table)
            table.clear()
        elif val2 > val1:
            print(f"Раунд за {players[1].name}!")
            players[1].hand.extend(table)
            table.clear()
        else:
            print("Війна! (Нічия)")

        if len(players[0].hand) == 0: return players[1].name
        elif len(players[1].hand) == 0: return players[0].name
        return None