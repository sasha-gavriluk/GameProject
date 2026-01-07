import os
import sys
import time
import random

# Додаємо шлях, щоб модуль бачив utils
sys.path.append(os.path.join(os.path.dirname(__file__), 'utils'))

from utils.cards import Deck
from utils.engine import GameEngine, Player
from utils.rule.rules_war import WarRules
from utils.rule.rules_durak import DurakRules
from utils.rule.rules_bridge import BridgeRules

# --- КЛАС БОТА ---
class BotPlayer(Player):
    def think(self, engine):
        """Універсальна логіка бота для різних ігор"""
        rules = engine.rules
        
        if isinstance(rules, BridgeRules):
            return self._bridge_strategy(engine)
        if isinstance(rules, DurakRules):
            return self._durak_strategy(engine)
        return None

    def _bridge_strategy(self, engine):
        rules = engine.rules
        if rules.has_taken_card:
            legal_cards = [c for c in self.hand if rules.is_legal_move(c, self, table=engine.table, engine=engine)]
            if not legal_cards: return "pass"
        
        legal_cards = [c for c in self.hand if rules.is_legal_move(c, self, table=engine.table, engine=engine)]
        if not legal_cards: return "take"

        # Пріоритет: 7, 8, 9, A, J, 6
        action_ranks = ['7', '8', '9', 'A', 'J', '6']
        for rank in action_ranks:
            candidates = [c for c in legal_cards if c.rank == rank]
            if candidates: return candidates[0]
        
        return sorted(legal_cards, key=lambda c: rules.scores.get(c.rank, 0), reverse=True)[0]

    def _durak_strategy(self, engine):
        rules = engine.rules
        trump = engine.extra_data.get('trump')
        trump_suit = trump.suit if trump else None
        
        legal_cards = [c for c in self.hand if rules.is_legal_move([c], self, table=engine.table, engine=engine)]
        
        my_idx = engine.players.index(self)
        is_defender = (my_idx == rules.defender_idx)

        if is_defender:
            if not legal_cards: return "take"
            return sorted(legal_cards, key=lambda c: (c.suit == trump_suit, rules.ranks_values.get(c.rank, 0)))[0]
        else:
            if not legal_cards: return "pass"
            return sorted(legal_cards, key=lambda c: (c.suit == trump_suit, rules.ranks_values.get(c.rank, 0)))[0]

# --- ДОПОМІЖНІ ФУНКЦІЇ ---

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_separator(char='-', length=40):
    print(char * length)

def run_game_loop(engine):
    # Скидаємо прапор завершення гри перед початком
    engine.game_over = False
    print("\n" + "="*20 + " ГРА ПОЧАЛАСЯ " + "="*20)
    
    while not engine.game_over:
        current_player = engine.players[engine.active_player_idx]
        
        # Візуальне розділення ходів
        print_separator('=')
        if 'trump' in engine.extra_data:
            print(f"КОЗИР: {engine.extra_data['trump']}")
            
        print(f"КАРТИ НА СТОЛІ: {engine.table}")
        print(f"У колоді: {len(engine.deck.cards)} карт")
        print_separator()

        action = None
        
        # --- ХІД БОТА ---
        if isinstance(current_player, BotPlayer):
            print(f"ХІД БОТА: {current_player.name}")
            time.sleep(1) # Затримка для реалістичності
            action = current_player.think(engine)
            print(f"Бот вибрав: {action}")
            
            # Виконуємо хід бота
            # (Логіка вибору масті для J або Бріджу тепер всередині rules_bridge.py)
            result = engine.play_turn(action)

        # --- ХІД ГРАВЦЯ ---
        else:
            print(f"ХІД ГРАВЦЯ: {current_player.name}")
            print("Твоя рука:")
            for i, card in enumerate(current_player.hand):
                print(f"  [{i}] {card}")
            
            prompt = engine.rules.get_prompt_message(engine=engine)
            print(prompt + " (можна кілька через пробіл, напр: 0 1)") 
            
            user_input = input("Ваш хід > ").strip().lower()

            # === ЧІТ-КОД: TAKEALL ===
            if user_input == 'takeall':
                print("\n🕵️  CHEAT ACTIVATED: TAKE ALL  🕵️")
                
                # 1. Забираємо все з колоди
                if engine.deck.cards:
                    current_player.hand.extend(engine.deck.cards)
                    engine.deck.cards = []
                    print("-> Колода переміщена в руку.")
                
                # 2. Забираємо все зі столу
                if engine.table:
                    current_player.hand.extend(engine.table)
                    engine.table = []
                    print("-> Стіл очищено в руку.")
                
                # Сортуємо руку (за мастю та рангом)
                current_player.hand.sort(key=lambda c: (c.suit, c.rank))
                
                print(f"Тепер у вас {len(current_player.hand)} карт.")
                continue # Перезапускаємо цикл, щоб оновити екран
            # ========================

            # Перевірка стандартних команд (take, pass)
            if user_input in engine.rules.get_allowed_commands(engine=engine):
                action = user_input
            else:
                try:
                    # --- ОБРОБКА ВВОДУ КАРТ ---
                    # Підтримуємо розділювачі: пробіл або кома
                    indices_str = user_input.replace(',', ' ').split()
                    indices = [int(i) for i in indices_str]
                    
                    # Валідація індексів
                    if any(idx < 0 or idx >= len(current_player.hand) for idx in indices):
                        print("❌ Невірний номер карти!")
                        continue
                    
                    # Формуємо список карт
                    selected_cards = [current_player.hand[idx] for idx in indices]
                    
                    # Якщо карта одна - передаємо як об'єкт, якщо більше - список
                    if len(selected_cards) == 1:
                        action = selected_cards[0]
                    else:
                        action = selected_cards
                    # --------------------------
                except ValueError:
                    print("❌ Невірний ввід! Введіть номери карт, команду або 'takeall'.")
                    continue

            # Виконуємо хід гравця
            result = engine.play_turn(action)

        # --- ОБРОБКА РЕЗУЛЬТАТУ ---
        if result is False:
            print("❌ Хід неможливий! (Можливо, карти різного номіналу або не підходять)")
        elif isinstance(result, str):
            # Якщо play_turn повернув рядок (наприклад, ім'я переможця)
            print(f"\n!!! {result} !!!")
            # Цикл завершиться, бо engine.game_over стане True

def run_bridge_session():
    clear_screen()
    print("♠️ ♦️  БРІДЖ: ТУРНІРНИЙ РЕЖИМ  ♣️ ♥️")
    
    try:
        total = int(input("Скільки всього гравців? (2-6): "))
        bot_choice = input("Грати з ботами? (y/n): ").lower() == 'y'
    except: total, bot_choice = 2, True

    players = []
    players.append(Player(input("Ваше ім'я: ") or "Sasha"))
    for i in range(1, total):
        players.append(BotPlayer(f"Бот {i}") if bot_choice else Player(f"Гравець {i+1}"))

    rules = BridgeRules()
    engine = GameEngine(rules)
    for p in players: engine.add_player(p)

    while len(players) > 1:
        deck = Deck()
        # Починаємо новий раунд
        engine.setup_game(deck)
        run_game_loop(engine)
        
        # Виводимо результати після раунду
        print("\n--- РАХУНОК ТУРНІРУ ---")
        for p in players:
            print(f"{p.name}: {p.score} очок")

        # Перевірка на вибування
        for p in players[:]:
            if p.score > 225:
                print(f"💀 {p.name} вибуває ({p.score} > 225)!")
                players.remove(p)
        
        if len(players) > 1:
            input("\nНатисніть Enter для наступного раунду...")
        else:
            print(f"\n🏆 ПЕРЕМОЖЕЦЬ ТУРНІРУ: {players[0].name}! 🏆")
            input("\nEnter для виходу в меню...")

def main():
    while True:
        clear_screen()
        print("=== МУЛЬТИ-ІГРОВИЙ ДВИГУН ===")
        print("1. Війна")
        print("2. Дурак")
        print("3. Брідж (Турнір з ботами)")
        print("4. Вихід")
        
        choice = input("\nВиберіть: ")
        
        if choice == '1':
            e = GameEngine(WarRules()); e.add_player(Player("P1")); e.add_player(Player("P2"))
            e.setup_game(Deck()); run_game_loop(e)
        elif choice == '2':
            print("Налаштування Дурака...")
            e = GameEngine(DurakRules({'mode':'mixed'})); e.add_player(Player("Ви")); e.add_player(BotPlayer("Бот"))
            e.setup_game(Deck()); run_game_loop(e)
        elif choice == '3':
            run_bridge_session()
        elif choice == '4':
            break

if __name__ == "__main__":
    main()