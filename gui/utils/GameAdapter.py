# gui/utils/GameAdapter.py

from utils.engine import GameEngine, Player
from utils.cards import Deck
from utils.bot import BotPlayer

# Імпортуємо правила
from utils.rule.rules_war import WarRules
from utils.rule.rules_durak import DurakRules
from utils.rule.rules_bridge import BridgeRules

class GameAdapter:
    def __init__(self, game_type):
        self.game_type = game_type
        self.engine = None
        self.hero_id = "hero"
        self.command_queue = [] 

    def start(self):
        self.command_queue = []
        
        rules = DurakRules()
        # Визначаємо налаштування для UI
        is_multi_select = True
        
        if self.game_type == "WAR": 
            rules = WarRules()
            is_multi_select = False # <--- Війна: тільки одна карта
        elif self.game_type == "BRIDGE": 
            rules = BridgeRules()
            # У Бріджі теж зазвичай ходять по одній, але якщо правила дозволяють скидати пари - можна True.
            # Поки залишимо True (або False, як вирішите, для класичного бріджу часто False).
            # Давайте для Бріджу теж поки залишимо True, раптом ви захочете мульти-хід.
        
        self.engine = GameEngine(rules)
        
        hero = Player("Hero", player_id=self.hero_id)
        bot = BotPlayer("Bot", player_id="bot_1")
        
        self.engine.add_player(hero)
        self.engine.add_player(bot)
        
        self.engine.on_game_event = self._on_engine_event
        
        deck = Deck()
        self.engine.setup_game(deck)
        
        setup_cmd = {
            "cmd": "SETUP_TABLE",
            "game_type": self.game_type,
            "multi_select": is_multi_select, # <--- Передаємо параметр у візуал
            "players": [
                {"id": self.hero_id, "name": "Я", "is_hero": True},
                {"id": "bot_1", "name": "Бот", "is_hero": False}
            ]
        }
        self.command_queue.append(setup_cmd)
        
        self.engine.start_game()
        
        return self._flush_commands()

    def process_input(self, data):
        self.command_queue = [] 
        
        if data['type'] == 'ui_action':
            action = data['action']

            if action == 'start_new_round':
                self.start_next_round()
                return self.command_queue # Повертаємо чергу команд (SETUP_TABLE і т.д.)
                
            elif action == 'get_scores':
                scores = [{'name': p.name, 'score': p.score} for p in self.engine.players]
                self.command_queue.append({
                    "cmd": "SHOW_SCORES",
                    "is_round_end": False, # Просто показати
                    "scores": scores
                })
                return self.command_queue
            
            # === ВАЖЛИВО: Обробка команд від Popups ===
            if action == 'set_suit':
                # Перетворюємо рядок у словник для engine
                self.engine.play_turn({'action': 'set_suit', 'suit': data['suit']})
                
            elif action == 'set_bonus':
                # Перетворюємо рядок у словник для engine
                self.engine.play_turn({'action': 'set_bonus', 'choice': data['choice']})
            # ==========================================
            
            elif action == 'play':
                card_ids = data.get('cards', [])
                hero = self.engine.players[0]
                cards_to_play = []
                for cid in card_ids:
                    for c in hero.hand:
                        if f"{c.rank}_{c.suit}" == cid:
                            cards_to_play.append(c)
                            break
                if cards_to_play:
                    success = self.engine.play_turn(cards_to_play)
                    if not success:
                        self.command_queue.append({"cmd": "SHOW_ERROR", "text": "Невірний хід!"})
            
            else:
                # take / pass
                self.engine.play_turn(action)
        
        # Хід ботів
        current_idx = self.engine.active_player_idx
        current_player = self.engine.players[current_idx]
        if isinstance(current_player, BotPlayer) and not self.engine.game_over:
             action = current_player.think(self.engine)
             if action:
                 self.engine.play_turn(action)

        self._check_ui_controls()
        return self._flush_commands()
    
    def _check_ui_controls(self):
        """Визначає, чи потрібно показувати кнопку 'Взяти' або 'Битом'"""
        rules = self.engine.rules
        hero_idx = 0
        
        # Якщо гра Війна - кнопок немає
        if isinstance(rules, WarRules):
            self.command_queue.append({
                "cmd": "UPDATE_CONTROLS",
                "show_action_btn": False
            })
            return

        # Якщо Дурак
        if isinstance(rules, DurakRules):
            hero_idx = 0 # Hero завжди 0 в нашому сетапі
            current_active = self.engine.active_player_idx
            
            # Якщо хід не мій і я не захищаюсь - кнопки ховаємо (грубо, але для початку піде)
            # Але в Дураку система складна: 
            # 1. Атакуючий ходить (активний).
            # 2. Захисник (активний) відбивається.
            
            # Тому перевіряємо роль героя
            is_defender = (hero_idx == rules.defender_idx)
            is_attacker = not is_defender # (в дуелі)
            
            show_btn = False
            btn_text = ""
            
            # Ситуація: Я ЗАХИСНИК
            if is_defender:
                # Якщо на столі є карти (атака йде), я можу "Взяти"
                if len(rules.pending_attacks) > 0 or len(self.engine.table) > 0:
                    show_btn = True
                    btn_text = "Взяти"
                # Але треба перевірити, чи зараз мій хід (чи чекаємо поки атакуючий підкине)
                # У простій реалізації active_player перемикається на захисника, коли треба бити.
                if self.engine.active_player_idx != hero_idx:
                    show_btn = False

            # Ситуація: Я АТАКУЮЧИЙ
            else:
                # Якщо на столі є карти, і я можу сказати "Битом" (завершити хід)
                if len(self.engine.table) > 0:
                    show_btn = True
                    btn_text = "Битом"
                    
                # Якщо зараз хід захисника (він думає), я не можу нажати "Битом" поки він не поб'є або не візьме
                # Хоча в деяких версіях можна сказати "Все, я більше не кидаю".
                # Для спрощення: показуємо "Битом", тільки якщо active_player == hero (я ходжу)
                if self.engine.active_player_idx != hero_idx:
                    show_btn = False

            self.command_queue.append({
                "cmd": "UPDATE_CONTROLS",
                "show_action_btn": show_btn,
                "btn_text": btn_text
            })

        if isinstance(rules, BridgeRules):
            show_btn = False
            btn_text = ""
            
            # Перевіряємо, чи зараз хід Героя
            if self.engine.active_player_idx == hero_idx:
                # Кнопка "Пас" з'являється ТІЛЬКИ якщо гравець вже взяв карту
                # і не зобов'язаний крити 6-ку
                if rules.has_taken_card and not rules.must_cover_six:
                    show_btn = True
                    btn_text = "Пас"
                else:
                    # Якщо карту ще не брав -> кнопка схована (треба клікати на колоду або ходити)
                    show_btn = False
            
            self.command_queue.append({
                "cmd": "UPDATE_CONTROLS",
                "show_action_btn": show_btn,
                "btn_text": btn_text
            })
            return

    def _on_engine_event(self, event_type, data):
        
        if event_type == "DEAL_CARDS":
            deals = []
            for p in self.engine.players:
                p_cards = []
                for c in p.hand:
                    p_cards.append({"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"})
                deals.append({"player_id": p.player_id, "cards_data": p_cards})
            
            trump_data = None
            trump_card = self.engine.extra_data.get('trump')
            if trump_card:
                trump_data = {"suit": trump_card.suit, "rank": trump_card.rank, "id": f"{trump_card.rank}_{trump_card.suit}"}

            self.command_queue.append({
                "cmd": "INITIAL_DEAL", 
                "hands": deals,
                "deck_count": len(self.engine.deck),
                "trump_card": trump_data 
            })

        # === ДОДАЄМО ОБРОБКУ НОВОЇ ПОДІЇ ===
        if event_type == "PLAYER_DRAW_DECK":
            p = data['player']
            cards = data['cards']
            
            # Підготовка даних карт для візуалу
            cards_data = []
            for c in cards:
                cards_data.append({"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"})
            
            self.command_queue.append({
                "cmd": "DRAW_CARDS_ANIMATION",
                "player_id": p.player_id,
                "cards": cards_data
            })
            # SYNC_HANDS тут не викликаємо одразу, щоб не збити анімацію. 
            # Карти додадуться в руку в процесі анімації.
        # ===================================

        elif event_type == "PLAYER_TOOK_CARDS":
             player = data.get('player')
             p_id = player.player_id if player else self.hero_id
             
             # ВАЖЛИВО: Ця команда йде ПЕРШОЮ (анімація польоту)
             self.command_queue.append({
                 "cmd": "TAKE_CARDS", 
                 "player_id": p_id
             })
             
             # ВАЖЛИВО: Ця команда йде ДРУГОЮ (оновлення руки даними)
             self.command_queue.append({"cmd": "SYNC_HANDS", "hands": self._get_hands_snapshot()})
             
             # Очищення столу (логічне)
             self.command_queue.append({"cmd": "CLEAR_TABLE"})

        elif event_type == "PLAYER_MOVE":
            p = data['player']
            action = data['action'] 
            
            # 1. Перевіряємо, чи це список (або кортеж) карт
            if isinstance(action, (list, tuple)):
                for card in action:
                    card_data = {"suit": card.suit, "rank": card.rank, "id": f"{card.rank}_{card.suit}"}
                    self.command_queue.append({
                        "cmd": "PLAY_CARD",
                        "player_id": p.player_id,
                        "card": card_data
                    })
            
            # 2. Якщо це одна карта (об'єкт Card)
            elif hasattr(action, 'suit') and hasattr(action, 'rank'): 
                card_data = {"suit": action.suit, "rank": action.rank, "id": f"{action.rank}_{action.suit}"}
                self.command_queue.append({
                    "cmd": "PLAY_CARD",
                    "player_id": p.player_id,
                    "card": card_data
                })
            
            # === 3. ВИПРАВЛЕННЯ: Обробка текстової команди "take" ===
            elif action == "take":
                # Перевіряємо, чи це Дурень (або інша гра, де "take" = забрати стіл)
                is_durak = isinstance(self.engine.rules, DurakRules)
                
                if is_durak:
                    # Для Дурня: анімація забору зі столу
                    self.command_queue.append({
                        "cmd": "TAKE_CARDS",
                        "player_id": p.player_id
                    })
                    self.command_queue.append({"cmd": "SYNC_HANDS", "hands": self._get_hands_snapshot()})
                
                else:
                    # Для Бріджу: нічого не робимо тут.
                    # Брідж сам відправить подію PLAYER_DRAW_DECK, 
                    # яка запустить анімацію з колоди.
                    pass
                
        # ===============================================
        
        elif event_type == "TABLE_CLEARED":
            self.command_queue.append({"cmd": "CLEAR_TABLE"})
            
        elif event_type == "GAME_OVER":
            # Перевіряємо, чи це Брідж
            if isinstance(self.engine.rules, BridgeRules):
                # Формуємо дані про очки
                scores = [{'name': p.name, 'score': p.score} for p in self.engine.players]
                
                self.command_queue.append({
                    "cmd": "SHOW_SCORES",
                    "is_round_end": True,
                    "scores": scores
                })
            else:
                # Стара логіка для інших ігор
                self.command_queue.append({"cmd": "SHOW_WINNER", "winner": data['winner']})

        elif event_type == "SHOW_SUIT_SELECTOR":
            self.command_queue.append({
                "cmd": "SHOW_SUIT_SELECTOR",
                "player_id": data['player_id']
            })
            
        elif event_type == "SHOW_BONUS_SELECTOR":
            self.command_queue.append({
                "cmd": "SHOW_BONUS_SELECTOR",
                "player_id": data['player_id'],
                "mult": data['mult'],
                "sub": data['sub']
            })
            
        # Оновлюємо кнопки після кожної події
        self._check_ui_controls()

    def _get_hands_snapshot(self):
        """Допоміжний метод для SYNC_HANDS"""
        res = []
        for p in self.engine.players:
            cards = [{"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"} for c in p.hand]
            res.append({"player_id": p.player_id, "cards_data": cards})
        return res

    def _flush_commands(self):
        res = list(self.command_queue)
        self.command_queue = []
        return res
    
    def start_next_round(self):
        """Перезапускає гру зі збереженням очок гравців"""
        print("--- ЗАПУСК НОВОГО РАУНДУ ---")
        
        # 1. Скидаємо руки гравців
        for p in self.engine.players:
            p.hand = []
            
        # 2. Скидаємо колоду і стіл
        # === ВИПРАВЛЕННЯ ТУТ ===
        self.engine.start_game() # Було self.engine.start(), що викликало помилку
        # =======================
        
        # 3. Відправляємо команди на перемальовування столу
        self.command_queue.append({
            "cmd": "SETUP_TABLE",
            "game_type": self.game_type,
            "multi_select": self.game_type != "WAR", # Або логіка з start()
            "players": [
                {"id": p.player_id, "name": p.name, "is_hero": (p.player_id == self.hero_id)}
                for p in self.engine.players
            ]
        })
        self.command_queue.append({"cmd": "INITIAL_DEAL"})
        self._check_ui_controls()