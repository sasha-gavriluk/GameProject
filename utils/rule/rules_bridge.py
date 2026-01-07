# Code/utils/rule/rules_bridge.py
import random
from utils.engine import GameRules

class BridgeRules(GameRules):
    def __init__(self):
        self.initial_cards_count = 6
        self.deck = None
        
        # Очки за карти
        self.scores = {
            '6': 0, '7': 0, '8': 0, '9': 0, 
            '10': 10, 'J': 20, 'Q': 10, 'K': 10, 'A': 15
        }
        
        # СТАН РАУНДУ
        self.forced_suit = None       
        self.pending_draw = 0         
        self.skip_counter = 0         
        self.must_cover_six = False   
        self.round_ended_flag = False # Прапор закінчення раунду
        self.round_winner_name = None
        
        # СТАН ХОДУ
        self.has_taken_card = False   # Чи брав гравець карту в цьому ході
        
        # МНОЖНИК (перевертання колоди)
        self.score_multiplier = 1

    def on_game_start(self, **kwargs):
        engine = kwargs.get('engine')
        self.deck = engine.deck
        players = engine.players
        
        # Скидання станів раунду
        self.forced_suit = None
        self.pending_draw = 0
        self.skip_counter = 0
        self.must_cover_six = False
        self.round_ended_flag = False
        self.round_winner_name = None
        self.has_taken_card = False
        self.score_multiplier = 1
        
        # --- НОВІ ЗМІННІ ДЛЯ ВАЛЕТІВ ---
        self.final_jack_multiplier = 1  # Множник від валетів (додається)
        self.winner_score_bonus = 0     # Очки для списання переможцю
        # -------------------------------
        
        # --- ФІКС КОЛОДИ (Збір і фільтрація) ---
        all_cards = self.deck.cards[:]
        for p in players:
            all_cards.extend(p.hand)
            p.hand = [] 
        
        valid_ranks = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        bridge_deck = [c for c in all_cards if c.rank in valid_ranks]
        
        self.deck.cards = bridge_deck
        self.deck.shuffle()
        
        print(f"=== НОВИЙ РАУНД БРІДЖ! Роздача по {self.initial_cards_count}. Множник x1 ===")
        for p in players:
            for _ in range(self.initial_cards_count):
                self._safe_draw(engine, p, 1, kwargs.get('table'))

    # Допоміжна функція для безпечного взяття карт (з переворотом колоди)
    def _safe_draw(self, engine, player, count, table):
        for _ in range(count):
            if len(self.deck.cards) == 0:
                self._flip_deck(engine, table)
            
            # Якщо навіть після перевороту пусто (рідкісний випадок, всі карти на руках)
            if len(self.deck.cards) > 0:
                engine.draw_cards(player, 1)

    def _flip_deck(self, engine, table):
        if not table or len(table) < 2:
            print("(!) Колода пуста, і на столі нема карт для перемішування!")
            return

        # Зберігаємо верхню карту
        top_card = table.pop()
        
        # Решту столу в колоду
        new_cards = table[:]
        table.clear()
        table.append(top_card) # Повертаємо верхню на стіл
        
        engine.deck.cards = new_cards
        engine.deck.shuffle()
        
        self.score_multiplier *= 2
        print(f"\n♻️ КОЛОДА ЗАКІНЧИЛАСЬ! Перевертаємо стіл. МНОЖНИК ОЧКІВ: x{self.score_multiplier} ♻️")

    def get_allowed_commands(self, **kwargs):
        return ['take', 'pass']

    def get_prompt_message(self, **kwargs):
        hints = []
        if self.must_cover_six:
            hints.append("⚠️ ТРЕБА НАКРИТИ 6-ку!")
        
        if self.forced_suit:
            suit_icons = {'hearts': '♥', 'diamonds': '♦', 'clubs': '♣', 'spades': '♠'}
            s_icon = suit_icons.get(self.forced_suit, self.forced_suit)
            hints.append(f"♦ ЗАМОВЛЕНО: {s_icon}")
            
        if self.score_multiplier > 1:
            hints.append(f"💰 x{self.score_multiplier}")

        base_msg = "Ваш хід"
        if hints:
            base_msg = " | ".join(hints)
        
        cmds = "номер карти, 'take'"
        # Показуємо 'pass' тільки якщо гравець ВЖЕ взяв карту
        if self.has_taken_card and not self.must_cover_six:
            cmds += ", 'pass'"
        
        return f"{base_msg}\n({cmds})"

    def is_legal_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        
        if action == 'take':
            # Можна брати карту завжди, але якщо вже взяв - це стратегічне рішення
            return True 
        
        if action == 'pass':
            # 1. Не можна пасувати, якщо треба крити 6-ку
            if self.must_cover_six: return False
            # 2. Не можна пасувати, якщо ще не брав карту в цьому ході
            if not self.has_taken_card: return False
            return True

        # Перевірка карт
        cards_played = action if isinstance(action, list) else [action]
        if not cards_played: return False

        first_card = cards_played[0]
        if not all(c.rank == first_card.rank for c in cards_played):
            return False

        if not table:
            return True

        top_card = table[-1]
        target_suit = self.forced_suit if self.forced_suit else top_card.suit
        
        if first_card.rank in ['J', '9']: return True

        matches_suit = (first_card.suit == target_suit)
        matches_rank = (first_card.rank == top_card.rank)
        
        if matches_suit or matches_rank:
            return True
            
        return False

    def execute_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        engine = kwargs.get('engine')
        
        if action == 'take':
            self._safe_draw(engine, player, 1, table)
            self.has_taken_card = True
            print(f"➕ {player.name} бере карту.")
            return

        if action == 'pass':
            print(f"⏩ {player.name} пасує.")
            self.must_cover_six = False
            return

        # 1. Кладемо карти на стіл
        cards = action if isinstance(action, list) else [action]
        for card in cards:
            player.hand.remove(card)
            table.append(card)
        
        last_card = cards[-1]
        count = len(cards)
        print(f"🃏 {player.name} поклав: {cards}")
        
        self.forced_suit = None 

        # === 2. ПРІОРИТЕТНА ПЕРЕВІРКА: БРІДЖ (4 карти) ===
        if len(table) >= 4:
            last_4 = table[-4:]
            if all(c.rank == last_4[0].rank for c in last_4):
                print(f"\n🔥🔥🔥 ЗІБРАВСЯ БРІДЖ !!! (4 {last_4[0].rank})")
                
                declare_bridge = False
                if hasattr(player, 'think'):
                    declare_bridge = True
                    print(f"🤖 {player.name} оголошує БРІДЖ!")
                else:
                    while True:
                        choice = input("🚩 Оголосити БРІДЖ і закінчити раунд? (y/n): ").lower().strip()
                        if choice in ['y', 'n']:
                            declare_bridge = (choice == 'y')
                            break
                
                if declare_bridge:
                    print(f"🏆 {player.name} ОГОЛОСИВ БРІДЖ!")
                    player.hand = [] # Очищаємо руку (перемога)

                    # --- ВИПРАВЛЕННЯ: ПЕРЕВІРКА НА ВАЛЕТІВ ВСЕРЕДИНІ БРІДЖУ ---
                    if last_4[0].rank == 'J':
                        print(f"🃏 Це БРІДЖ ВАЛЕТАМИ! Спеціальні умови!")
                        
                        # Рахуємо множник для всіх 4-х валетів
                        calc_multiplier = 0
                        jacks_value_sum = 0
                        for c in last_4:
                            jacks_value_sum += self.scores.get(c.rank, 20)
                            if c.suit == 'spades': calc_multiplier += 4
                            else: calc_multiplier += 2
                        
                        print(f"💥 Потужність: Множник x{calc_multiplier} АБО Списання -{jacks_value_sum}")
                        
                        choice = '1'
                        if not hasattr(player, 'think'):
                            print(f"1. Помножити очки ворогам (x{calc_multiplier})")
                            print(f"2. Відняти собі ({jacks_value_sum} очок)")
                            while True:
                                inp = input("Ваш вибір (1 або 2) > ").strip()
                                if inp in ['1', '2']:
                                    choice = inp
                                    break
                        
                        if choice == '1':
                            self.final_jack_multiplier = calc_multiplier
                            print(f"☠️ БРІДЖ-МНОЖЕННЯ! Очки лузерів x{calc_multiplier}!")
                        else:
                            self.winner_score_bonus = -jacks_value_sum
                            print(f"📉 БРІДЖ-СПИСАННЯ! Переможець отримує {self.winner_score_bonus} очок.")
                    
                    else:
                        # Звичайний брідж (не валети)
                        self.winner_score_bonus = -50
                        print("📉 Стандартний бонус Бріджу: -50 очок.")
                    
                    return True
        # =================================================

        # 3. ЕФЕКТИ КАРТ (Якщо не оголошено Брідж)
        if last_card.rank == '6':
            self.must_cover_six = True
            print("⚠️ ШІСТКА! Гравець ходить знову.")
        else:
            self.must_cover_six = False

        if last_card.rank == '7':
            penalty = 2 * count
            self.pending_draw += penalty
            self.skip_counter = 1
            print(f"⚔️ СІМКА! Наступний: +{penalty} карт і пропуск.")

        elif last_card.rank == '8':
            penalty = 1 * count
            self.pending_draw += penalty
            print(f"⚔️ ВІСІМКА! Наступний: +{penalty} карт (без пропуску).")

        elif last_card.rank == '9':
            club_nines = sum(1 for c in cards if c.suit == 'clubs')
            if club_nines > 0:
                penalty = 3 * club_nines
                self.pending_draw += penalty
                self.skip_counter = 1
                print(f"♣️ 9 ХРЕСТ! Наступний: +{penalty} карт і пропуск.")
            else:
                print("🛡️ 9-ка чиста.")

        elif last_card.rank == 'A':
            num_players = len(engine.players)
            max_skips = num_players - 1
            skips = min(count, max_skips)
            self.skip_counter = skips
            print(f"⛔ ТУЗ! Пропуск ходу ({skips} гравців).")

        elif last_card.rank == 'J':
            # Логіка фінішу валетами (якщо це НЕ був брідж, але карти скінчились)
            if len(player.hand) == 0:
                print(f"\n🏆 {player.name} закінчує гру ВАЛЕТАМИ!")
                
                calc_multiplier = 0
                jacks_value_sum = 0
                for c in cards:
                    jacks_value_sum += self.scores.get(c.rank, 20)
                    if c.suit == 'spades': calc_multiplier += 4
                    else: calc_multiplier += 2
                
                print(f"💥 Потужність фінішу: Множник x{calc_multiplier} АБО Списання -{jacks_value_sum}")
                
                choice = '1'
                if not hasattr(player, 'think'): 
                    print(f"1. Помножити очки ворогам (x{calc_multiplier})")
                    print(f"2. Відняти собі ({jacks_value_sum} очок)")
                    while True:
                        inp = input("Ваш вибір (1 або 2) > ").strip()
                        if inp in ['1', '2']:
                            choice = inp
                            break
                
                if choice == '1':
                    self.final_jack_multiplier = calc_multiplier
                    print(f"☠️ Обрано МНОЖЕННЯ! Очки лузерів x{calc_multiplier}!")
                else:
                    self.winner_score_bonus = -jacks_value_sum
                    print(f"📉 Обрано СПИСАННЯ! Переможець отримує {self.winner_score_bonus} очок.")

            else:
                print(f"\n🎩 ВАЛЕТ! {player.name}, виберіть масть:")
                print("1. Чирва (♥)  2. Бубна (♦)  3. Хреста (♣)  4. Піка (♠)")
                mapping = {'1': 'hearts', '2': 'diamonds', '3': 'clubs', '4': 'spades'}
                
                if hasattr(player, 'think'):
                    self.forced_suit = random.choice(list(mapping.values()))
                    print(f"🤖 Бот вибрав: {self.forced_suit}")
                else:
                    while True:
                        choice = input("Ваш вибір (1-4): ").strip()
                        if choice in mapping:
                            self.forced_suit = mapping[choice]
                            break
                        print("❌ Невірний вибір.")
                print(f"--> ЗАМОВЛЕНО: {self.forced_suit}")

        return True

    def should_switch_turn(self, action, player, **kwargs):
        engine = kwargs.get('engine')
        
        # Якщо раунд закінчено через Брідж
        if self.round_ended_flag:
            return engine.active_player_idx # Повертаємо будь-що, winner перехопить

        # Шістка - повторний хід
        if self.must_cover_six:
            if len(player.hand) == 0: return True 
            return engine.active_player_idx 
            
        if action == 'take':
            # Після взяття хід НЕ переходить автоматично.
            # Гравець має або походити, або натиснути Pass (який тепер доступний)
            return engine.active_player_idx 

        # Якщо Pass або Хід картою - перехід ходу
        # Спочатку скинемо прапор взяття карти для поточного гравця
        # (Але ми перемикаємось на нового, тому треба скинути для НОВОГО гравця)
        # Це зробимо в _calculate_next_player або просто при початку ходу.
        # Найпростіше: ми скидаємо self.has_taken_card = False ТІЛЬКИ коли реально змінюємо гравця.
        
        return self._calculate_next_player(engine, kwargs.get('table'))

    def _calculate_next_player(self, engine, table):
        # Оскільки ми змінюємо гравця, скидаємо статус "взяв карту"
        self.has_taken_card = False 
        
        current_idx = engine.active_player_idx
        total_players = len(engine.players)
        
        victim_idx = (current_idx + 1) % total_players
        victim_player = engine.players[victim_idx]

        if self.pending_draw > 0:
            print(f"🎁 {victim_player.name} отримує штраф: {self.pending_draw} карт!")
            self._safe_draw(engine, victim_player, self.pending_draw, table)
            self.pending_draw = 0
            
        step = 1 + self.skip_counter
        self.skip_counter = 0 
        
        next_active_idx = (current_idx + step) % total_players
        return next_active_idx

    def get_winner(self, **kwargs):
        players = kwargs.get('players')
        
        # Перевірка на "Брідж"
        if self.round_ended_flag:
            self._calculate_scores(players)
            return "ROUND_OVER" # Спеціальний сигнал для app.py
            
        # Перевірка на пусту руку
        for p in players:
            if len(p.hand) == 0:
                print(f"🎉 {p.name} закінчив карти!")
                self._calculate_scores(players)
                return "ROUND_OVER"
        
        return None

    def _calculate_scores(self, players):
        # Загальний множник = (множник колоди) * (множник валетів, якщо є)
        # Якщо валетів не було, final_jack_multiplier = 1
        final_mult = self.score_multiplier * self.final_jack_multiplier
        
        print(f"\n--- 📊 РАХУНОК (Колода x{self.score_multiplier}, Валети x{self.final_jack_multiplier} -> Разом x{final_mult}) ---")
        
        for p in players:
            # Якщо це переможець (пуста рука)
            if len(p.hand) == 0:
                if self.winner_score_bonus != 0:
                    p.score += self.winner_score_bonus
                    print(f"🏆 {p.name} (Переможець): Списання {self.winner_score_bonus}. (Всього: {p.score})")
                else:
                    print(f"🏆 {p.name} (Переможець): 0 штрафних. (Всього: {p.score})")
                continue

            # Рахуємо очки лузера
            points = 0
            for card in p.hand:
                val = 0
                if card.rank in ['6', '7', '8', '9']: val = 0 
                elif card.rank in ['10', 'Q', 'K']: val = 10
                elif card.rank == 'A': val = 15
                elif card.rank == 'J':
                    if card.suit == 'spades': val = 40
                    else: val = 20
                points += val
            
            # Застосовуємо фінальний множник
            total_points = points * final_mult
            p.score += total_points
            
            print(f"💀 {p.name}: {points} очок * {final_mult} = +{total_points} (Всього: {p.score})")
            
            if p.score == 225:
                print(f"✨ {p.name} набрав 225! Очки згорають до 0!")
                p.score = 0
            elif p.score > 225:
                print(f"💀 {p.name} має > 225 і вилітає!")