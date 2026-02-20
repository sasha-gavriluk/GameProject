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
        # ВИПРАВЛЕННЯ: Тепер дозволяємо список, якщо в ньому рівно 1 карта
        if isinstance(action, list):
            if len(action) == 1:
                return True
            return False # Якщо карт більше однієї — не можна
        return True

    def execute_move(self, action, player, **kwargs):
        # ВИПРАВЛЕННЯ: Дістаємо карту зі списку перед використанням
        if isinstance(action, list):
            action = action[0]

        table = kwargs.get('table')
        
        # Перевірка на всяк випадок, щоб не було крашу при видаленні
        if action in player.hand:
            player.hand.remove(action)
            table.append(action)
            print(f"{player.name} поклав {action}")

    def should_switch_turn(self, action, player, **kwargs):
        return True
    
    def post_move_cleanup(self, **kwargs):
        pass

    def get_winner(self, **kwargs):
        """
        Повертає індекс переможця раунду (0 або 1), або None, якщо раунд ще не закінчено.
        """
        table = kwargs.get('table')
        
        # Чекаємо, поки на столі буде парна кількість карт (2, 4, 6...)
        # Якщо карт менше 2 або непарна кількість — раунд триває
        if len(table) < 2 or len(table) % 2 != 0:
            return None

        # Беремо дві останні карти для порівняння
        card1 = table[-2] # Карта першого гравця (героя)
        card2 = table[-1] # Карта другого гравця (бота)
        
        # Отримуємо їх силу
        # Важливо: використовуємо str(rank), щоб уникнути помилок типів
        val1 = self.ranks_values.get(str(card1.rank), 0)
        val2 = self.ranks_values.get(str(card2.rank), 0)

        if val1 > val2:
            return 0 # Переміг гравець 0 (Герой)
        elif val2 > val1:
            return 1 # Переміг гравець 1 (Бот)
        else:
            # Якщо рівні — це Війна!
            # Повертаємо None, щоб карти залишились на столі для наступного ходу
            print("--- ВІЙНА! Карти залишаються на столі ---")
            return None