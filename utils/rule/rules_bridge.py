# Code/utils/rule/rules_bridge.py
import random
from utils.engine import GameRules

class BridgeRules(GameRules):
    def __init__(self):
        self.initial_cards_count = 5
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
    
    def _apply_card_effects(self, card, player=None, engine=None):
        """
        Застосовує ефекти карти до стану гри (Штрафи, Пропуски, Шістки).
        Викликається і при звичайному ході, і при роздачі 'на стіл'.
        """
        # 1. Шістка - треба крити (ходити ще раз)
        if card.rank == '6':
            self.must_cover_six = True
            # Якщо це відбувається під час гри, можна вивести лог
            if player:
                print(f"🔄 {player.name} поклав 6-ку і має ходити знову!")
        else:
            self.must_cover_six = False

        # 2. Сімка - наступний бере 2 карти і пропускає хід
        if card.rank == '7':
            self.pending_draw += 2
            self.skip_counter = 1
            if player:
                print(f"⚔️ {player.name} активував 7-ку: наступний +2 карти і пропуск.")

        # 3. Вісімка - наступний бере 1 карту (але ходить)
        elif card.rank == '8':
            self.pending_draw += 1
            if player:
                print(f"⚔️ {player.name} активував 8-ку: наступний +1 карта.")

        # 4. Дев'ятка чирва (або хреста, залежно від правил) - наприклад, +3 карти
        # У вашому коді було згадування про спец. 9-ку. Припустимо це 9 Хреста.
        elif card.rank == '9' and card.suit == 'clubs':
            self.pending_draw += 3
            self.skip_counter = 1
            if player:
                print(f"♣️ {player.name} активував 9 ХРЕСТА: наступний +3 карти і пропуск!")

        # 5. Туз - пропуск ходу
        elif card.rank == 'A':
            self.skip_counter = 1
            if player:
                print(f"⛔ {player.name} поклав ТУЗА: наступний пропускає хід.")

        # 6. Валет - ефект вибору масті тут не обробляється, 
        # бо він вимагає взаємодії з UI (це робиться в execute_move).

    def execute_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        engine = kwargs.get('engine')
        
        # --- БЛОК 1: ОБРОБКА ВІДПОВІДЕЙ ВІД UI (Масть / Бонус) ---
        if isinstance(action, dict):
            # Гравець обрав масть (через UI або бот)
            if action.get('action') == 'set_suit':
                suit = action.get('suit')
                self.forced_suit = suit
                self.waiting_for_suit = False
                print(f"--> ГРАВЕЦЬ {player.name} ЗАМОВИВ МАСТЬ: {self.forced_suit}")
                engine.notify("SUIT_ORDERED", suit=self.forced_suit)
                return

            # Гравець обрав бонус (Брідж Валетів)
            if action.get('action') == 'set_bonus':
                choice = action.get('choice')
                mult_val = self.temp_bonus_data.get('mult', 1)
                sub_val = self.temp_bonus_data.get('sub', 0)
                
                if choice == 'multiply':
                    self.final_jack_multiplier = mult_val
                    print(f"☠️ БРІДЖ-МНОЖЕННЯ! Очки лузерів будуть помножені на x{self.final_jack_multiplier}!")
                else:
                    self.winner_score_bonus = -sub_val
                    print(f"📉 БРІДЖ-СПИСАННЯ! Переможець списує собі {self.winner_score_bonus} очок.")
                
                self.waiting_for_bonus = False
                self.round_ended_flag = True # Раунд завершується після вибору бонусу
                return

        # --- БЛОК 2: ВЗЯТТЯ КАРТИ (TAKE) ---
        if action == 'take':
            # Використовуємо безпечне взяття (з перевертанням колоди якщо треба)
            self._safe_draw(engine, player, 1, table)
            self.has_taken_card = True
            print(f"➕ {player.name} бере карту з колоди.")
            return

        # --- БЛОК 3: ПАС (PASS) ---
        if action == 'pass':
            print(f"⏩ {player.name} пасує.")
            self.must_cover_six = False # Якщо спасував, вимога крити 6 знімається (хід переходить)
            return
        
        # --- БЛОК 4: ГРА КАРТОЮ (АБО КАРТАМИ) ---
        cards = action if isinstance(action, list) else [action]
        
        # Переміщуємо карти з руки на стіл
        for card in cards:
            if card in player.hand:
                player.hand.remove(card)
            table.append(card)
        
        last_card = cards[-1]
        print(f"🃏 {player.name} поклав: {[str(c) for c in cards]}")
        
        # Якщо була замовлена масть - вона "виконується" і скидається
        if self.forced_suit:
            self.forced_suit = None 
            engine.notify("SUIT_CLEARED")

        # --- БЛОК 5: ПЕРЕВІРКА НА КОМБІНАЦІЮ "БРІДЖ" (4 карти) ---
        if len(table) >= 4:
            last_4 = table[-4:]
            # Перевіряємо, чи всі 4 карти одного рангу
            if all(c.rank == last_4[0].rank for c in last_4):
                print(f"\n🔥🔥🔥 ЗІБРАВСЯ БРІДЖ !!! (4 карти рангу {last_4[0].rank})")
                print(f"🏆 {player.name} ОГОЛОСИВ БРІДЖ!")
                
                # Гравець скидає всі карти (перемога)
                player.hand = [] 

                # Спеціальна логіка для Валетів
                if last_4[0].rank == 'J':
                    print(f"🃏 Це БРІДЖ ВАЛЕТАМИ! Вибір: помножити очки інших чи списати собі.")
                    
                    # Розрахунок потенційного множника та суми списання
                    calc_multiplier = 0
                    jacks_value_sum = 0
                    for c in last_4:
                        jacks_value_sum += self.scores.get(c.rank, 20)
                        # Валет пік дає x4 (або більше), інші x2 - приклад логіки
                        if c.suit == 'spades': calc_multiplier += 4
                        else: calc_multiplier += 2
                    
                    self.temp_bonus_data = {'mult': calc_multiplier, 'sub': jacks_value_sum}

                    # Якщо бот - вибирає автоматично (множення)
                    if hasattr(player, 'think'):
                        self.execute_move({'action': 'set_bonus', 'choice': 'multiply'}, player, engine=engine)
                        return
                    
                    # Якщо людина - показуємо меню вибору
                    self.waiting_for_bonus = True
                    engine.notify("SHOW_BONUS_SELECTOR", player_id=player.player_id, mult=calc_multiplier, sub=jacks_value_sum)
                    return 
                
                else:
                    # Звичайний Брідж (не Валети) -> Стандартний бонус -50 очок
                    self.winner_score_bonus = -50
                    print("📉 Стандартний бонус Бріджу: -50 очок.")
                    self.round_ended_flag = True
                    return

        # --- БЛОК 6: ЗАСТОСУВАННЯ ЕФЕКТІВ КАРТИ ---
        self._apply_card_effects(last_card, player, engine)
        
        # --- БЛОК 7: ЛОГІКА ВАЛЕТА (ЗАМОВЛЕННЯ МАСТІ) ---
        if last_card.rank == 'J':
             # Якщо це була остання карта гравця -> він виграв, вибирати масть не треба
             if len(player.hand) == 0:
                print(f"🎉 {player.name} вийшов з гри Валетом!")
                # Можна додати логіку вибору бонусу, як у Бріджі, але зазвичай просто кінець
                self.round_ended_flag = True
                return 

             else:
                # Гра продовжується, треба замовити масть
                print(f"\n🎩 ВАЛЕТ! {player.name} має обрати масть...")
                
                if hasattr(player, 'think'):
                    # Бот вибирає масть, якої в нього найбільше
                    mapping = ['hearts', 'diamonds', 'clubs', 'spades']
                    # Спрощена логіка: рандом
                    best_suit = random.choice(mapping) 
                    self.execute_move({'action': 'set_suit', 'suit': best_suit}, player, engine=engine)
                    return
                else:
                    # Людина: ставимо прапорець і чекаємо
                    self.waiting_for_suit = True
                    engine.notify("SHOW_SUIT_SELECTOR", player_id=player.player_id)
                    return 

        return True

    def should_switch_turn(self, action, player, **kwargs):
        engine = kwargs.get('engine')
        
        # 1. Якщо чекаємо вибору від гравця - хід не передаємо
        if self.waiting_for_suit or self.waiting_for_bonus:
            return engine.active_player_idx

        # 2. Якщо раунд закінчено (оголошено брідж або хтось вийшов) - не перемикаємо
        if self.round_ended_flag:
            return engine.active_player_idx 

        # 3. Якщо лежить ШІСТКА
        if self.must_cover_six:
            # Якщо гравець вийшов (у нього 0 карт), він не може крити -> хід переходить
            if len(player.hand) == 0: 
                return (engine.active_player_idx + 1) % len(engine.players)
            # Інакше він мусить ходити знову
            return engine.active_player_idx 
            
        # 4. Якщо гравець взяв карту (take) - хід залишається у нього
        if action == 'take':
            return engine.active_player_idx 

        # 5. Якщо set_suit (замовлення масті) - це частина ходу, треба розрахувати наступного
        # (Продовжуємо виконання коду нижче)

        # 6. РОЗРАХУНОК НАСТУПНОГО ГРАВЦЯ
        self.has_taken_card = False # Скидаємо прапорець "брав карту" для нового гравця
        
        current_idx = engine.active_player_idx
        total_players = len(engine.players)
        
        # Визначаємо "жертву" (наступного по колу)
        victim_idx = (current_idx + 1) % total_players
        victim_player = engine.players[victim_idx]

        # 7. ОБРОБКА ШТРАФІВ (7-ка, 8-ка, 9-ка)
        if self.pending_draw > 0:
            print(f"🎁 {victim_player.name} отримує штраф: {self.pending_draw} карт!")
            # Видаємо карти жертві
            self._safe_draw(engine, victim_player, self.pending_draw, kwargs.get('table'))
            self.pending_draw = 0
            
        # 8. ОБРОБКА ПРОПУСКУ ХОДУ (Туз, 7-ка)
        # step = 1 (звичайний перехід) + skip_counter (пропуски)
        step = 1 + self.skip_counter
        self.skip_counter = 0 # Скидаємо лічильник пропусків
        
        next_active_idx = (current_idx + step) % total_players
        return next_active_idx

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
        engine = kwargs.get('engine')
        
        winner_found = False
        winner_idx = None # Індекс переможця

        # Перевірка умови закінчення
        if self.round_ended_flag:
            winner_found = True
            if engine:
                winner_idx = engine.active_player_idx
        else:
            for idx, p in enumerate(players):
                if len(p.hand) == 0:
                    winner_found = True
                    winner_idx = idx
                    break
        
        if winner_found:
            self._calculate_scores(players)
            
            # === ОСЬ ТУТ КЛЮЧОВИЙ МОМЕНТ ===
            if engine and winner_idx is not None:
                # Зберігаємо індекс переможця у engine.dealer_idx
                # Щоб при наступному виклику custom_deal він став дилером
                engine.dealer_idx = winner_idx
                
                winner_name = players[winner_idx].name
                print(f"🏁 ПЕРЕМІГ {winner_name}. Він стає ДИЛЕРОМ на наступну гру!")
                
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

    def custom_deal(self, engine):
        # 1. Визначаємо Дилера
        if engine.dealer_idx is None:
            # Перша гра - рандом
            engine.dealer_idx = random.randint(0, len(engine.players) - 1)
            print(f"🎲 [NEW GAME] Випадковий дилер: {engine.players[engine.dealer_idx].name}")
        else:
            # Наступні ігри - переможець (індекс вже встановлено в get_winner)
            # Перевіряємо валідність індексу (раптом гравців стало менше)
            if engine.dealer_idx >= len(engine.players):
                engine.dealer_idx = 0
            print(f"👑 [NEXT ROUND] Дилер (Переможець): {engine.players[engine.dealer_idx].name}")

        dealer_idx = engine.dealer_idx
        dealer = engine.players[dealer_idx]

        # 2. Роздача карт: Всім 5, Дилеру 4
        # Цикл поки є карти і комусь треба
        cards_needed = True
        while cards_needed:
            cards_needed = False
            for i, player in enumerate(engine.players):
                # Цільова кількість карт
                target = 4 if i == dealer_idx else 5
                
                if len(player.hand) < target and engine.deck.cards:
                    player.receive_card(engine.deck.deal())
                    cards_needed = True

        # 3. 5-та карта Дилера летить на стіл
        if engine.deck.cards:
            start_card = engine.deck.deal()
            engine.table.append(start_card)
            print(f"🃏 Дилер {dealer.name} відкриває стіл картою: {start_card}")

            # ВАЖЛИВО: Щоб логіка думала, що це походив Дилер,
            # ми тимчасово ставимо active_player_idx на нього.
            engine.active_player_idx = dealer_idx

            # 4. Візуалізація
            # Показуємо карти в руках
            engine.notify("DEAL_CARDS")
            # Показуємо анімацію, що дилер кинув карту
            engine.notify("PLAYER_MOVE", player=dealer, action=[start_card])

            # 5. Застосовуємо ефекти (7, 8, Туз, 6)
            self._apply_card_effects(start_card, player=dealer)

            # 6. Розраховуємо, хто ходить наступним (відносно Дилера)
            context = {"table": engine.table, "engine": engine}
            
            # Викликаємо should_switch_turn, ніби дилер щойно поклав [start_card]
            next_idx = self.should_switch_turn([start_card], dealer, **context)
            
            # Встановлюємо реального гравця, який має ходити/бити/брати
            if isinstance(next_idx, int):
                engine.active_player_idx = next_idx
            
            print(f"👉 Хід переходить до: {engine.players[engine.active_player_idx].name}")
            engine.notify("TURN_SWITCH", active_player_idx=engine.active_player_idx)

        else:
            # На випадок збою (пуста колода)
            engine.notify("DEAL_CARDS")