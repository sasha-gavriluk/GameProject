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
        self.final_jack_multiplier = 0  
        self.winner_score_bonus = 0     
        
        # Прапорці очікування (замість input)
        self.waiting_for_suit = False
        self.waiting_for_bonus = False
        self.waiting_for_bridge_choice = False
        
        # Тимчасове сховище для розрахованих бонусів, поки чекаємо вибору
        self.temp_bonus_data = {} 
        self._chain_already_resolved = False
        self._chain_next_active_idx = None
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
        
        self.final_jack_multiplier = 0
        self.winner_score_bonus = 0
        
        self.waiting_for_suit = False
        self.waiting_for_bonus = False
        self.waiting_for_bridge_choice = False
        self.temp_bonus_data = {}
        self._chain_already_resolved = False
        self._chain_next_active_idx = None
        
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
        if getattr(player, "is_eliminated", False):
            return
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
        if self.waiting_for_suit or self.waiting_for_bonus or self.waiting_for_bridge_choice:
            return []

        return ['take', 'pass']

    def _active_player_indexes(self, engine):
        return [i for i, p in enumerate(engine.players) if not getattr(p, "is_eliminated", False)]

    def _next_active_idx(self, engine, from_idx, steps=1):
        total = len(engine.players)
        if total == 0:
            return 0
        steps = max(1, int(steps))
        idx = from_idx % total
        for _ in range(steps):
            found = None
            for hop in range(1, total + 1):
                cand = (idx + hop) % total
                if not getattr(engine.players[cand], "is_eliminated", False):
                    found = cand
                    break
            if found is None:
                return from_idx % total
            idx = found
        return idx

    def get_prompt_message(self, **kwargs):
        if self.waiting_for_suit: return "Оберіть масть (на екрані)..."
        if self.waiting_for_bonus: return "Оберіть бонус (на екрані)..."
        if self.waiting_for_bridge_choice: return "Оберіть: завершити раунд чи продовжити..."

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
        if getattr(player, "is_eliminated", False):
            return False

        # === FIX: Захист від падіння на службових командах ===
        # Якщо прийшов словник (це точно команда налаштування)
        if isinstance(action, dict):
            return True
        
        # Якщо прийшов рядок, який є командою налаштування
        if isinstance(action, str) and action in ['set_suit', 'set_bonus', 'set_bridge_decision', 'play_chain']:
            return True
        # =====================================================

        # Дозволяємо системні команди вибору, коли чекаємо (старий код)
        if self.waiting_for_suit or self.waiting_for_bonus or self.waiting_for_bridge_choice:
            return True

        # Дозволяємо системні команди вибору, коли чекаємо
        if self.waiting_for_suit:
            return True # Валідація буде в execute_move
        if self.waiting_for_bonus:
            return True
        if self.waiting_for_bridge_choice:
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
    
    def _apply_card_effects(self, card, player=None, engine=None, cards_played=None):
        """
        Застосовує ефекти карти/набору карт до стану гри.
        Якщо передано cards_played, ефекти рахуються для всього мультивикиду.
        """
        cards = cards_played if cards_played else [card]
        if not cards:
            return

        # Ефект 6: якщо у викиді є 6-ка, гравець має крити.
        has_six = any(c.rank == '6' for c in cards)
        self.must_cover_six = has_six
        if has_six and player:
            print(f"🔄 {player.name} поклав 6-ку і має ходити знову!")

        seven_count = sum(1 for c in cards if c.rank == '7')
        eight_count = sum(1 for c in cards if c.rank == '8')
        ace_count = sum(1 for c in cards if c.rank == 'A')

        # 7-ки: карти сумуються, пропуск лише один незалежно від кількості 7.
        if seven_count > 0:
            add_draw = 2 * seven_count
            self.pending_draw += add_draw
            self.skip_counter += 1
            if player:
                print(f"⚔️ {player.name} активував {seven_count}x7: наступний +{add_draw} карт і пропуск.")

        # 8-ки: тільки добір, без пропуску.
        if eight_count > 0:
            add_draw = eight_count
            self.pending_draw += add_draw
            if player:
                print(f"⚔️ {player.name} активував {eight_count}x8: наступний +{add_draw} карт.")

        # 9♣: ефект працює лише якщо вона верхня серед усіх викинутих 9.
        nines = [c for c in cards if c.rank == '9']
        if nines and nines[-1].suit == 'clubs':
            self.pending_draw += 3
            self.skip_counter += 1
            if player:
                print(f"♣️ {player.name} активував 9 ХРЕСТА: наступний +3 карти і пропуск!")

        # Тузи: пропуск = кількість тузів, але не більше ніж коло до повернення ходу.
        if ace_count > 0:
            total_players = len(engine.players) if engine and getattr(engine, 'players', None) else 2
            max_skip_to_return = max(1, total_players - 1)
            effective_skip = min(ace_count, max_skip_to_return)
            self.skip_counter += effective_skip
            if player:
                print(f"⛔ {player.name} поклав {ace_count} туз(ів): пропуск ходів = {effective_skip}.")

    def _is_legal_chain_card(self, card, top_card, forced_suit):
        if top_card is None:
            return True
        if card.rank in ['J', '9']:
            return True
        target_suit = forced_suit if forced_suit else top_card.suit
        return bool(card.suit == target_suit or card.rank == top_card.rank)

    def _party_returns_to_player(self, party_cards, engine, from_idx=None):
        if not party_cards:
            return False
        has_six = any(c.rank == '6' for c in party_cards)
        if has_six:
            return True

        skip = 0
        seven_count = sum(1 for c in party_cards if c.rank == '7')
        if seven_count > 0:
            skip += 1

        nines = [c for c in party_cards if c.rank == '9']
        if nines and nines[-1].suit == 'clubs':
            skip += 1

        ace_count = sum(1 for c in party_cards if c.rank == 'A')
        if ace_count > 0:
            total_players = len(engine.players) if engine and getattr(engine, 'players', None) else 2
            max_skip_to_return = max(1, total_players - 1)
            skip += min(ace_count, max_skip_to_return)

        step = 1 + skip
        base_idx = engine.active_player_idx if from_idx is None else from_idx
        next_idx = self._next_active_idx(engine, base_idx, step)
        return bool(next_idx == base_idx)

    def _resolve_chain_parties(self, cards, engine, table):
        top_card = table[-1] if table else None
        forced_suit = self.forced_suit
        parties = []
        valid_prefix = []
        invalid_idx = None
        start = 0
        n = len(cards)

        # 1) Спочатку жорстко перевіряємо легальність всього ланцюжка послідовно.
        for i, c in enumerate(cards):
            if not self._is_legal_chain_card(c, top_card, forced_suit):
                invalid_idx = i
                break
            valid_prefix.append(c)
            if forced_suit:
                forced_suit = None
            top_card = c

        if invalid_idx is not None:
            invalid_card = cards[invalid_idx]
            return [], [], invalid_card, valid_prefix

        # 2) Ланцюжок легальний по картах. Тепер ділимо його на партії:
        # партія завершується при першому поверненні ходу до цього ж гравця;
        # якщо повернення не сталось до кінця - решта карт це фінальна партія.
        top_card = table[-1] if table else None
        forced_suit = self.forced_suit
        current_idx = engine.active_player_idx
        while start < n:
            return_end = None
            party = []
            tmp_top = top_card
            tmp_forced = forced_suit
            start_rank = cards[start].rank

            for j in range(start, n):
                c = cards[j]
                # Поки хід не повернувся, гравець продовжує ту саму партію:
                # зміна номіналу до повернення ходу = злам ланцюжка.
                if c.rank != start_rank and return_end is None:
                    invalid_idx = j
                    break

                party.append(c)
                if tmp_forced:
                    tmp_forced = None
                tmp_top = c

                if self._party_returns_to_player(party, engine, from_idx=current_idx):
                    return_end = j
                    break
            if invalid_idx is not None:
                break

            if return_end is None:
                accepted = cards[start:n]
                parties.append(accepted)
                break

            accepted = cards[start:return_end + 1]
            parties.append(accepted)

            for c in accepted:
                if forced_suit:
                    forced_suit = None
                top_card = c

            # Симулюємо перехід після партії для наступної ітерації.
            if any(x.rank == '6' for x in accepted):
                next_idx = current_idx
            else:
                draw = 0
                skip = 0
                seven_count = sum(1 for x in accepted if x.rank == '7')
                if seven_count > 0:
                    draw += 2 * seven_count
                    skip += 1
                draw += sum(1 for x in accepted if x.rank == '8')
                nines = [x for x in accepted if x.rank == '9']
                if nines and nines[-1].suit == 'clubs':
                    draw += 3
                    skip += 1
                ace_count = sum(1 for x in accepted if x.rank == 'A')
                if ace_count > 0:
                    total_players = len(engine.players) if engine and getattr(engine, 'players', None) else 2
                    skip += min(ace_count, max(1, total_players - 1))
                step = 1 + skip
                next_idx = self._next_active_idx(engine, current_idx, step)
            current_idx = next_idx
            start = return_end + 1

        if invalid_idx is not None:
            valid_cards = cards[:invalid_idx]
            invalid_card = cards[invalid_idx]
            return [], [], invalid_card, valid_cards

        return parties, list(cards), None, list(cards)

    def execute_move(self, action, player, **kwargs):
        table = kwargs.get('table')
        engine = kwargs.get('engine')
        
        # --- БЛОК 1: ОБРОБКА ВІДПОВІДЕЙ ВІД UI (Масть / Бонус) ---
        if isinstance(action, dict):
            if action.get('action') == 'play_chain':
                chain_cards = action.get('cards') or []
                if not chain_cards:
                    return

                parties, valid_cards, invalid_card, keep_cards = self._resolve_chain_parties(chain_cards, engine, table)

                if invalid_card is not None:
                    keep_ids = [f"{c.rank}_{c.suit}" for c in keep_cards]
                    engine.notify("INVALID_CHAIN_CARD", invalid_card=invalid_card, keep_ids=keep_ids)
                    return

                if not valid_cards:
                    return

                current_idx = engine.active_player_idx
                for party in parties:
                    for card in party:
                        if card in player.hand:
                            player.hand.remove(card)
                        table.append(card)

                    if self.forced_suit:
                        self.forced_suit = None
                        engine.notify("SUIT_CLEARED")

                    self._continue_after_card_play(player, party, engine, table)
                    if self.round_ended_flag or self.waiting_for_suit or self.waiting_for_bonus or self.waiting_for_bridge_choice:
                        break

                    if self.must_cover_six:
                        next_idx = current_idx
                    else:
                        victim_idx = self._next_active_idx(engine, current_idx, 1)
                        victim_player = engine.players[victim_idx]
                        if self.pending_draw > 0:
                            self._safe_draw(engine, victim_player, self.pending_draw, table)
                            self.pending_draw = 0
                        step = 1 + self.skip_counter
                        self.skip_counter = 0
                        next_idx = self._next_active_idx(engine, current_idx, step)
                    current_idx = next_idx

                self._chain_already_resolved = True
                self._chain_next_active_idx = current_idx
                engine.extra_data["_resolved_action"] = list(valid_cards)
                return

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

            # Гравець обрав, чи завершувати раунд після "бріджу"
            if action.get('action') == 'set_bridge_decision':
                choice = action.get('choice')
                cards = self.temp_bonus_data.get('bridge_cards', [])
                if choice == 'end':
                    print(f"🏁 {player.name} вирішив завершити раунд після Бріджу.")
                    self._finish_round_with_cards(player, cards, engine)
                    self.waiting_for_bridge_choice = False
                    self.temp_bonus_data.pop('bridge_cards', None)
                    return

                print(f"▶️ {player.name} вирішив продовжити гру після Бріджу.")
                self.waiting_for_bridge_choice = False
                self.temp_bonus_data.pop('bridge_cards', None)
                self._continue_after_card_play(player, cards, engine, table)
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
        is_bridge = False
        if len(table) >= 4:
            last_4 = table[-4:]
            is_bridge = all(c.rank == last_4[0].rank for c in last_4)

        if is_bridge:
            print(f"\n🔥🔥🔥 ЗІБРАВСЯ БРІДЖ !!! (4 карти рангу {table[-1].rank})")
            print(f"🧠 {player.name} може завершити раунд або продовжити гру.")
            if hasattr(player, 'think'):
                self.execute_move({'action': 'set_bridge_decision', 'choice': 'end'}, player, engine=engine, table=table)
                return
            self.waiting_for_bridge_choice = True
            self.temp_bonus_data['bridge_cards'] = list(cards)
            engine.notify("SHOW_BRIDGE_DECISION", player_id=player.player_id)
            return

        self._continue_after_card_play(player, cards, engine, table)

        return True

    def _jack_points(self, card):
        if card.rank != 'J':
            return 0
        return 40 if card.suit == 'spades' else 20

    def _start_jack_bonus_choice(self, player, jack_cards, engine):
        if not jack_cards:
            self.round_ended_flag = True
            return

        jack_sum = sum(self._jack_points(c) for c in jack_cards)
        # Множник валетів: сума очок валетів / 10.
        jack_mult = max(1, jack_sum // 10)
        self.temp_bonus_data = {'mult': jack_mult, 'sub': jack_sum}

        if hasattr(player, 'think'):
            self.execute_move({'action': 'set_bonus', 'choice': 'multiply'}, player, engine=engine)
            return

        self.waiting_for_bonus = True
        engine.notify("SHOW_BONUS_SELECTOR", player_id=player.player_id, mult=jack_mult, sub=jack_sum)

    def _finish_round_with_cards(self, player, cards, engine):
        jack_cards = [c for c in cards if c.rank == 'J']
        if jack_cards:
            self._start_jack_bonus_choice(player, jack_cards, engine)
        else:
            self.round_ended_flag = True

    def _continue_after_card_play(self, player, cards, engine, table):
        if not cards:
            return
        last_card = cards[-1]

        # Ефекти карт застосовуються, якщо раунд не завершуємо.
        self._apply_card_effects(last_card, player, engine, cards_played=cards)

        # Якщо гравець вийшов (0 карт) - раунд завершено.
        if len(player.hand) == 0:
            self._finish_round_with_cards(player, cards, engine)
            return

        # Валет у середині гри -> вибір масті.
        if last_card.rank == 'J':
            print(f"\n🎩 ВАЛЕТ! {player.name} має обрати масть...")
            if hasattr(player, 'think'):
                mapping = ['hearts', 'diamonds', 'clubs', 'spades']
                best_suit = random.choice(mapping)
                self.execute_move({'action': 'set_suit', 'suit': best_suit}, player, engine=engine)
                return
            self.waiting_for_suit = True
            engine.notify("SHOW_SUIT_SELECTOR", player_id=player.player_id)
            return

    def should_switch_turn(self, action, player, **kwargs):
        engine = kwargs.get('engine')

        if isinstance(action, dict) and action.get('action') == 'play_chain':
            if self._chain_already_resolved:
                self._chain_already_resolved = False
                next_idx = self._chain_next_active_idx if self._chain_next_active_idx is not None else engine.active_player_idx
                self._chain_next_active_idx = None
                return next_idx
            # Невалідний ланцюжок: хід лишається у гравця.
            return engine.active_player_idx
        
        # 1. Якщо чекаємо вибору від гравця - хід не передаємо
        if self.waiting_for_suit or self.waiting_for_bonus or self.waiting_for_bridge_choice:
            return engine.active_player_idx

        # 2. Якщо раунд закінчено (оголошено брідж або хтось вийшов) - не перемикаємо
        if self.round_ended_flag:
            return engine.active_player_idx 

        # 3. Якщо лежить ШІСТКА
        if self.must_cover_six:
            # Якщо гравець вийшов (у нього 0 карт), він не може крити -> хід переходить
            if len(player.hand) == 0: 
                return self._next_active_idx(engine, engine.active_player_idx, 1)
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
        
        # Визначаємо "жертву" (наступного активного по колу)
        victim_idx = self._next_active_idx(engine, current_idx, 1)
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
        
        next_active_idx = self._next_active_idx(engine, current_idx, step)
        return next_active_idx

    def _calculate_next_player(self, engine, table):
        self.has_taken_card = False 
        
        current_idx = engine.active_player_idx
        
        victim_idx = self._next_active_idx(engine, current_idx, 1)
        victim_player = engine.players[victim_idx]

        if self.pending_draw > 0:
            print(f"🎁 {victim_player.name} отримує штраф: {self.pending_draw} карт!")
            self._safe_draw(engine, victim_player, self.pending_draw, table)
            self.pending_draw = 0
            
        step = 1 + self.skip_counter
        self.skip_counter = 0 
        
        next_active_idx = self._next_active_idx(engine, current_idx, step)
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
                if getattr(p, "is_eliminated", False):
                    continue
                if len(p.hand) == 0:
                    winner_found = True
                    winner_idx = idx
                    break
        
        if winner_found:
            # Якщо фінальна карта дала штрафний добір (7/8/9♣), спершу застосовуємо
            # його до наступного активного гравця, і лише потім завершуємо раунд.
            if engine and self.pending_draw > 0 and winner_idx is not None:
                victim_idx = self._next_active_idx(engine, winner_idx, 1)
                if victim_idx != winner_idx:
                    victim_player = players[victim_idx]
                    print(f"🎁 Перед завершенням раунду {victim_player.name} добирає {self.pending_draw} карт.")
                    self._safe_draw(engine, victim_player, self.pending_draw, kwargs.get('table'))
                self.pending_draw = 0

            self._calculate_scores(players, winner_idx=winner_idx)
            
            # === ОСЬ ТУТ КЛЮЧОВИЙ МОМЕНТ ===
            if engine and winner_idx is not None:
                # Зберігаємо індекс переможця у engine.dealer_idx
                # Щоб при наступному виклику custom_deal він став дилером
                engine.dealer_idx = winner_idx
                
                winner_name = players[winner_idx].name
                print(f"🏁 ПЕРЕМІГ {winner_name}. Він стає ДИЛЕРОМ на наступну гру!")
                
            return "ROUND_OVER"
            
        return None
    
    def _calculate_scores(self, players, winner_idx=None):
        if self.final_jack_multiplier > 0:
            # За новими правилами: якщо колода не переверталась, діє множник валетів.
            # Якщо переверталась - додаємо множник валетів до поточного множника колоди.
            if self.score_multiplier > 1:
                final_mult = self.score_multiplier + self.final_jack_multiplier
            else:
                final_mult = self.final_jack_multiplier
        else:
            final_mult = self.score_multiplier
        
        print(f"\n--- 📊 РАХУНОК (Колода x{self.score_multiplier}, Валети {self.final_jack_multiplier} -> Разом x{final_mult}) ---")
        
        for idx, p in enumerate(players):
            if getattr(p, "is_eliminated", False):
                print(f"🚫 {p.name} вибув і пропускає підрахунок.")
                continue
            is_winner = (winner_idx is not None and idx == winner_idx) or (winner_idx is None and len(p.hand) == 0)

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

            if is_winner:
                print(f"🏆 {p.name} (Переможець): {points} очок * {final_mult} = +{total_points} (Всього: {p.score})")
            else:
                print(f"💀 {p.name}: {points} очок * {final_mult} = +{total_points} (Всього: {p.score})")

            if is_winner and self.winner_score_bonus != 0:
                p.score += self.winner_score_bonus
                if p.score < 0:
                    p.score = 0
                print(f"🏆 {p.name} (Переможець): Списання {self.winner_score_bonus}. (Всього: {p.score})")
            
            if p.score == 225:
                print(f"✨ {p.name} набрав 225! Очки згорають до 0!")
                p.score = 0
            elif p.score > 225:
                p.is_eliminated = True
                p.hand = []
                print(f"💀 {p.name} має > 225 і вилітає!")

    def custom_deal(self, engine):
        active_idxs = self._active_player_indexes(engine)
        if not active_idxs:
            engine.notify("DEAL_CARDS")
            return

        # 1. Визначаємо Дилера
        if engine.dealer_idx is None or engine.dealer_idx not in active_idxs:
            # Перша гра - рандом
            engine.dealer_idx = random.choice(active_idxs)
            print(f"🎲 [NEW GAME] Випадковий дилер: {engine.players[engine.dealer_idx].name}")
        else:
            # Наступні ігри - переможець (індекс вже встановлено в get_winner)
            # Перевіряємо валідність індексу (раптом гравців стало менше)
            if engine.dealer_idx >= len(engine.players) or engine.dealer_idx not in active_idxs:
                engine.dealer_idx = active_idxs[0]
            print(f"👑 [NEXT ROUND] Дилер (Переможець): {engine.players[engine.dealer_idx].name}")

        dealer_idx = engine.dealer_idx
        dealer = engine.players[dealer_idx]

        # 2. Роздача карт: Всім 5, Дилеру 4
        # Цикл поки є карти і комусь треба
        cards_needed = True
        while cards_needed:
            cards_needed = False
            for i, player in enumerate(engine.players):
                if getattr(player, "is_eliminated", False):
                    player.hand = []
                    continue
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
