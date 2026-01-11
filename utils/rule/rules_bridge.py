# Code/utils/rule/rules_bridge.py
import random
from utils.engine import GameRules

class BridgeRules(GameRules):
    def __init__(self):
        self.initial_cards_count = 6
        self.deck = None
        
        # Очки за карти (Оригінальна логіка)
        self.scores = {
            '6': 0, '7': 0, '8': 0, '9': 0, 
            '10': 10, 'J': 20, 'Q': 10, 'K': 10, 'A': 15
        }
        
        # СТАН РАУНДУ
        self.forced_suit = None       
        self.pending_draw = 0         
        self.skip_counter = 0         
        self.must_cover_six = False   
        self.round_ended_flag = False 
        self.round_winner_name = None
        
        # СТАН ХОДУ
        self.has_taken_card = False   
        
        # МНОЖНИК (перевертання колоди)
        self.score_multiplier = 1

        # --- НОВІ ЗМІННІ ДЛЯ ВАЛЕТІВ ТА ПОПАПІВ ---
        self.final_jack_multiplier = 1  
        self.winner_score_bonus = 0     
        
        # Прапорці очікування (замість input)
        self.waiting_for_suit = False
        self.waiting_for_bonus = False
        
        # Тимчасове сховище для розрахованих бонусів, поки чекаємо вибору
        self.temp_bonus_data = {} 
        # ------------------------------------------

    def on_game_start(self, **kwargs):
        engine = kwargs.get('engine')
        self.deck = engine.deck
        players = engine.players
        
        # === 1. ОЧИЩЕННЯ СТОЛУ (ВАЖЛИВО) ===
        # Якщо від попереднього раунду залишились карти, видаляємо їх з логіки
        engine.table.clear()
        
        # Скидання змінних раунду
        self.forced_suit = None
        self.pending_draw = 0
        self.skip_counter = 0
        self.must_cover_six = False
        self.round_ended_flag = False
        self.round_winner_name = None
        self.has_taken_card = False
        self.score_multiplier = 1
        
        self.final_jack_multiplier = 1
        self.winner_score_bonus = 0
        
        self.waiting_for_suit = False
        self.waiting_for_bonus = False
        self.temp_bonus_data = {}
        
        # === 2. ФОРМУВАННЯ КОЛОДИ БРІДЖУ ===
        # Беремо повну колоду (52), яку передав engine, і залишаємо тільки 6..A
        all_cards = self.deck.cards[:]
        
        # Примітка: logic engine.setup_game() вже очистив руки гравців, 
        # тому all_cards це просто нова чиста колода.
        
        valid_ranks = ['6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        bridge_deck = [c for c in all_cards if c.rank in valid_ranks]
        
        self.deck.cards = bridge_deck
        self.deck.shuffle()
        
        print(f"=== НОВИЙ РАУНД БРІДЖ! Карт: {len(self.deck.cards)}. Множник x1 ===")

    def _safe_draw(self, engine, player, count, table):
        """
        Безпечне взяття карт з авто-перемішуванням.
        """
        for _ in range(count):
            # 1. Якщо колода пуста ДО взяття — пробуємо перевернути
            if len(engine.deck.cards) == 0:
                self._flip_deck(engine, table)
            
            # 2. Якщо карти є — беремо одну
            if len(engine.deck.cards) > 0:
                engine.draw_cards(player, 1)
            
            # 3. === ГОЛОВНА ЗМІНА === 
            # Перевіряємо колоду ПІСЛЯ взяття.
            # Якщо вона стала пустою саме зараз, і на столі є карти для мішання (>=2),
            # то перевертаємо одразу ж! Не чекаємо наступного кліку.
            if len(engine.deck.cards) == 0 and len(table) >= 2:
                print("⚡ Колода спорожніла! Авто-перемішування...")
                self._flip_deck(engine, table)

    def _flip_deck(self, engine, table):
        if not table or len(table) < 2:
            print("(!) Колода пуста, і на столі нема карт для перемішування!")
            return

        # 1. Беремо верхню карту (вона лишається на столі)
        top_card = table.pop()
        
        # 2. Решту карт забираємо в нову колоду
        new_cards = table[:]
        table.clear()
        
        # 3. Повертаємо верхню карту на стіл
        table.append(top_card) 
        
        # 4. Оновлюємо колоду двигуна
        engine.deck.cards = new_cards
        engine.deck.shuffle()
        
        self.score_multiplier *= 2
        print(f"\n♻️ КОЛОДА ЗАКІНЧИЛАСЬ! Перевертаємо стіл. МНОЖНИК ОЧКІВ: x{self.score_multiplier} ♻️")
        
        # === ВИПРАВЛЕНО ТУТ ===
        # Передаємо дані як іменовані аргументи, а не як словник
        engine.notify("RESHUFFLE_TABLE", top_card=top_card, new_count=len(new_cards))

    def get_allowed_commands(self, **kwargs):
        # Якщо чекаємо вибору від гравця - блокуємо інші команди
        if self.waiting_for_suit or self.waiting_for_bonus:
            return []

        return ['take', 'pass']

    def get_prompt_message(self, **kwargs):
        if self.waiting_for_suit: return "Оберіть масть (на екрані)..."
        if self.waiting_for_bonus: return "Оберіть бонус (на екрані)..."

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
        if self.has_taken_card and not self.must_cover_six:
            cmds += ", 'pass'"
        
        return f"{base_msg}\n({cmds})"

    def is_legal_move(self, action, player, **kwargs):

        # === FIX: Захист від падіння на службових командах ===
        # Якщо прийшов словник (це точно команда налаштування)
        if isinstance(action, dict):
            return True
        
        # Якщо прийшов рядок, який є командою налаштування
        if isinstance(action, str) and action in ['set_suit', 'set_bonus']:
            return True
        # =====================================================

        # Дозволяємо системні команди вибору, коли чекаємо (старий код)
        if self.waiting_for_suit or self.waiting_for_bonus:
            return True

        # Дозволяємо системні команди вибору, коли чекаємо
        if self.waiting_for_suit:
            return True # Валідація буде в execute_move
        if self.waiting_for_bonus:
            return True

        # Стандартна перевірка
        table = kwargs.get('table')
        
        if action == 'take': return True 
        
        if action == 'pass':
            if self.must_cover_six: return False
            return True

        cards_played = action if isinstance(action, list) else [action]
        if not cards_played: return False

        first_card = cards_played[0]
        if not all(c.rank == first_card.rank for c in cards_played):
            return False

        if not table: return True

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
        
        # ==========================================================
        # 1. ОБРОБКА ВІДПОВІДЕЙ З POPUP (Замість input)
        # ==========================================================
        
        # Обробка вибору масті
        if action == 'set_suit' or (isinstance(action, dict) and action.get('action') == 'set_suit'):
            suit = action['suit'] if isinstance(action, dict) else kwargs.get('suit')
            self.forced_suit = suit
            self.waiting_for_suit = False
            print(f"--> ЗАМОВЛЕНО: {self.forced_suit}")
        
            engine.notify("SUIT_ORDERED", suit=self.forced_suit)
            return

        # Обробка вибору бонусу (множення або списання)
        if action == 'set_bonus' or (isinstance(action, dict) and action.get('action') == 'set_bonus'):
            choice = action['choice'] if isinstance(action, dict) else kwargs.get('choice')
            
            # Дістаємо збережені розрахунки
            mult_val = self.temp_bonus_data.get('mult', 1)
            sub_val = self.temp_bonus_data.get('sub', 0)
            
            if choice == 'multiply':
                self.final_jack_multiplier = mult_val
                print(f"☠️ БРІДЖ-МНОЖЕННЯ! Очки лузерів x{self.final_jack_multiplier}!")
            else:
                self.winner_score_bonus = -sub_val
                print(f"📉 БРІДЖ-СПИСАННЯ! Переможець отримує {self.winner_score_bonus} очок.")
            
            self.waiting_for_bonus = False
            self.round_ended_flag = True # Це завжди кінець гри/раунду
            return

        # ==========================================================
        # 2. СТАНДАРТНИЙ ХІД
        # ==========================================================

        if action == 'take':
            self._safe_draw(engine, player, 1, table)
            self.has_taken_card = True
            print(f"➕ {player.name} бере карту.")
            return

        if action == 'pass':
            print(f"⏩ {player.name} пасує.")
            # ТУТ БУЛА ВИДАЧА КАРТИ - ЇЇ ТРЕБА ПРИБРАТИ
            # Ми просто скидаємо прапорець 6-ки і виходимо.
            self.must_cover_six = False
            return
        
        # Кладемо карти на стіл
        cards = action if isinstance(action, list) else [action]
        for card in cards:
            player.hand.remove(card)
            table.append(card)
        
        last_card = cards[-1]
        count = len(cards)
        print(f"🃏 {player.name} поклав: {cards}")
        
        # Якщо була замовлена масть - скасовуємо її, бо хід зроблено
        if self.forced_suit:
            self.forced_suit = None 
            # СПОВІЩАЄМО UI, ЩО ЗАМОВЛЕННЯ ЗНЯТО
            engine.notify("SUIT_CLEARED")

        # === ПРІОРИТЕТНА ПЕРЕВІРКА: БРІДЖ (4 карти) ===
        if len(table) >= 4:
            last_4 = table[-4:]
            if all(c.rank == last_4[0].rank for c in last_4):
                print(f"\n🔥🔥🔥 ЗІБРАВСЯ БРІДЖ !!! (4 {last_4[0].rank})")
                
                # Автоматично оголошуємо Брідж (щоб не блокувати input-ом)
                print(f"🏆 {player.name} ОГОЛОСИВ БРІДЖ!")
                player.hand = [] # Очищаємо руку (перемога)

                # --- ПЕРЕВІРКА НА ВАЛЕТІВ (Оригінальна логіка) ---
                if last_4[0].rank == 'J':
                    print(f"🃏 Це БРІДЖ ВАЛЕТАМИ! Спеціальні умови!")
                    
                    # 1. Рахуємо варіанти
                    calc_multiplier = 0
                    jacks_value_sum = 0
                    for c in last_4:
                        jacks_value_sum += self.scores.get(c.rank, 20)
                        if c.suit == 'spades': calc_multiplier += 4
                        else: calc_multiplier += 2
                    
                    # 2. Зберігаємо у temp
                    self.temp_bonus_data = {'mult': calc_multiplier, 'sub': jacks_value_sum}
                    
                    # 3. Якщо це бот -> вибирає сам
                    if hasattr(player, 'think'):
                        # Бот завжди множить
                        self.execute_move({'action': 'set_bonus', 'choice': 'multiply'}, player, engine=engine)
                        return
                    
                    # 4. Якщо людина -> показуємо POPUP і чекаємо
                    self.waiting_for_bonus = True
                    engine.notify("SHOW_BONUS_SELECTOR", 
                                  player_id=player.player_id, 
                                  mult=calc_multiplier, 
                                  sub=jacks_value_sum)
                    return # ЗУПИНЯЄМО ВИКОНАННЯ, ЧЕКАЄМО ВИБОРУ
                    
                else:
                    # Звичайний брідж (не валети)
                    self.winner_score_bonus = -50
                    print("📉 Стандартний бонус Бріджу: -50 очок.")
                    self.round_ended_flag = True
                    return
        # =================================================

        # ЕФЕКТИ КАРТ (Якщо не оголошено Брідж)
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
                
                # 1. Рахуємо варіанти
                calc_multiplier = 0
                jacks_value_sum = 0
                for c in cards:
                    jacks_value_sum += self.scores.get(c.rank, 20)
                    if c.suit == 'spades': calc_multiplier += 4
                    else: calc_multiplier += 2
                
                # 2. Зберігаємо
                self.temp_bonus_data = {'mult': calc_multiplier, 'sub': jacks_value_sum}

                # 3. Бот чи Людина?
                if hasattr(player, 'think'):
                    self.execute_move({'action': 'set_bonus', 'choice': 'multiply'}, player, engine=engine)
                    return
                
                # 4. Показуємо POPUP
                self.waiting_for_bonus = True
                engine.notify("SHOW_BONUS_SELECTOR", 
                                player_id=player.player_id, 
                                mult=calc_multiplier, 
                                sub=jacks_value_sum)
                return # ЧЕКАЄМО

            else:
                # Звичайний валет - вибір масті
                print(f"\n🎩 ВАЛЕТ! {player.name}, обирає масть...")
                
                if hasattr(player, 'think'):
                    # Бот вибирає масть
                    mapping = ['hearts', 'diamonds', 'clubs', 'spades']
                    best_suit = random.choice(mapping) 
                    self.execute_move({'action': 'set_suit', 'suit': best_suit}, player, engine=engine)
                    return

                # Людина - POPUP
                self.waiting_for_suit = True
                engine.notify("SHOW_SUIT_SELECTOR", player_id=player.player_id)
                return # ЧЕКАЄМО

        return True

    def should_switch_turn(self, action, player, **kwargs):
        engine = kwargs.get('engine')
        
        # === ВАЖЛИВО: ЯКЩО ЧЕКАЄМО ВИБОРУ, ХІД НЕ ЗМІНЮЄТЬСЯ ===
        if self.waiting_for_suit or self.waiting_for_bonus:
            return engine.active_player_idx
        # ========================================================

        if self.round_ended_flag:
            return engine.active_player_idx 

        if self.must_cover_six:
            if len(player.hand) == 0: return True 
            return engine.active_player_idx 
            
        if action == 'take':
            return engine.active_player_idx 

        # Якщо ми тільки що встановили масть - це кінець ходу валета, переходимо далі
        if action == 'set_suit' or (isinstance(action, dict) and action.get('action') == 'set_suit'):
             return self._calculate_next_player(engine, kwargs.get('table'))

        return self._calculate_next_player(engine, kwargs.get('table'))

    def _calculate_next_player(self, engine, table):
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
        
        if self.round_ended_flag:
            self._calculate_scores(players)
            return "ROUND_OVER" 
            
        for p in players:
            if len(p.hand) == 0:
                print(f"🎉 {p.name} закінчив карти!")
                self._calculate_scores(players)
                return "ROUND_OVER"
        
        return None

    def _calculate_scores(self, players):
        final_mult = self.score_multiplier * self.final_jack_multiplier
        
        print(f"\n--- 📊 РАХУНОК (Колода x{self.score_multiplier}, Валети x{self.final_jack_multiplier} -> Разом x{final_mult}) ---")
        
        for p in players:
            if len(p.hand) == 0:
                if self.winner_score_bonus != 0:
                    p.score += self.winner_score_bonus
                    print(f"🏆 {p.name} (Переможець): Списання {self.winner_score_bonus}. (Всього: {p.score})")
                else:
                    print(f"🏆 {p.name} (Переможець): 0 штрафних. (Всього: {p.score})")
                continue

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
            
            total_points = points * final_mult
            p.score += total_points
            
            print(f"💀 {p.name}: {points} очок * {final_mult} = +{total_points} (Всього: {p.score})")
            
            if p.score == 225:
                print(f"✨ {p.name} набрав 225! Очки згорають до 0!")
                p.score = 0
            elif p.score > 225:
                print(f"💀 {p.name} має > 225 і вилітає!")