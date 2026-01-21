# gui/utils/GameAdapter.py

import time # <--- Додаємо імпорт часу

from utils.engine import GameEngine, Player
from utils.cards import Deck
from utils.bot import BotPlayer

# Імпортуємо правила
from utils.rule.rules_war import WarRules
from utils.rule.rules_durak import DurakRules
from utils.rule.rules_bridge import BridgeRules

# Імпортуємо конфіг для доступу до BOT_DELAY
from gui.config.Configs import VisualConfig 

class GameAdapter:
    def __init__(self, game_type):
        self.game_type = game_type
        self.engine = None
        self.hero_id = "hero"
        self.command_queue = [] 
        
        # === Таймер для затримки бота ===
        self.bot_next_move_time = 0 
        self.waiting_for_deal = False
        self.waiting_for_throw_confirm = False
        self.pending_bot_action = None
        self.pending_bot_active_idx = None
        self.waiting_for_player_count = False
        self.pending_is_multi_select = True
        self.pending_max_players = 2
        self.pending_rules_settings = None
        self.pending_game_type = game_type
        self._pending_durak_is_defense = None

    def start(self):
        self.command_queue = []

        self.pending_game_type = self.game_type
        self.pending_rules_settings = {
            "mode": "mixed",
            "neighbors_only": True,
            "allow_overthrow": True,
            "first_bout_5": False
        }
        self.pending_max_players = self._get_max_players(self.game_type)
        self.command_queue.append({
            "cmd": "SHOW_PLAYER_COUNT",
            "max_players": self.pending_max_players,
            "default_players": 2,
            "game_type": self.game_type,
            "rules_settings": self.pending_rules_settings
        })
        self.waiting_for_player_count = True
        
        return self._flush_commands()

    def process_input(self, data):
        self.command_queue = [] 

        if data['type'] == 'system':
            if data.get('action') == 'deal_complete':
                self.waiting_for_deal = False
                self.bot_next_move_time = time.time() + VisualConfig.BOT_DELAY
            return self._flush_commands()
        
        if data['type'] == 'ui_action':
            action = data['action']

            if action == 'start_new_round':
                self.start_next_round()
                return self.command_queue
            elif action == 'set_player_count':
                count = data.get('count', 2)
                settings = data.get('rules_settings')
                self._start_game_with_players(count, settings)
                return self._flush_commands()
            elif action == 'throw_more':
                self.waiting_for_throw_confirm = False
                self.pending_bot_action = None
                self.pending_bot_active_idx = None
                return self._flush_commands()
            elif action == 'throw_done':
                if self.pending_bot_action is not None and self.pending_bot_active_idx is not None:
                    self.engine.active_player_idx = self.pending_bot_active_idx
                    pending_player = self.engine.players[self.pending_bot_active_idx]
                    self._pending_durak_is_defense = self._predict_durak_defense(
                        self.pending_bot_action, pending_player
                    )
                    self.engine.play_turn(self.pending_bot_action)
                self.waiting_for_throw_confirm = False
                self.pending_bot_action = None
                self.pending_bot_active_idx = None
                self._check_ui_controls()
                return self._flush_commands()
                
            elif action == 'get_scores':
                scores = [{'name': p.name, 'score': p.score} for p in self.engine.players]
                self.command_queue.append({
                    "cmd": "SHOW_SCORES",
                    "is_round_end": False,
                    "scores": scores
                })
                return self.command_queue
            
            # Popup дії
            if action == 'set_suit':
                self.engine.play_turn({'action': 'set_suit', 'suit': data['suit']})
            elif action == 'set_bonus':
                self.engine.play_turn({'action': 'set_bonus', 'choice': data['choice']})
            
            # Гравець ходить картою
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
                    self._pending_durak_is_defense = self._predict_durak_defense(cards_to_play, hero)
                    success = self.engine.play_turn(cards_to_play)
                    if not success:
                        self._pending_durak_is_defense = None
                        self.command_queue.append({"cmd": "SHOW_ERROR", "text": "Невірний хід!"})
            
            else:
                # take / pass
                self.engine.play_turn(action)
        
        # --- ОНОВЛЕНА ЛОГІКА БОТІВ ---
        if self.waiting_for_player_count:
            return self._flush_commands()
        if self.waiting_for_deal:
            self._check_ui_controls()
            return self._flush_commands()

        current_idx = self.engine.active_player_idx
        current_player = self.engine.players[current_idx]
        
        if isinstance(current_player, BotPlayer) and not self.engine.game_over:
             # Перевіряємо, чи настав час для ходу
             if time.time() > self.bot_next_move_time:
                 action = current_player.think(self.engine)
                 if action:
                     if self._should_ask_for_throw(action):
                         self.pending_bot_action = action
                         self.pending_bot_active_idx = self.engine.active_player_idx
                         self.engine.active_player_idx = 0
                         self.waiting_for_throw_confirm = True
                         self.command_queue.append({"cmd": "ASK_THROW"})
                     else:
                         self._pending_durak_is_defense = self._predict_durak_defense(action, current_player)
                         self.engine.play_turn(action)
                         # Встановлюємо таймер на наступний хід (або наступну дію в серії)
                         self.bot_next_move_time = time.time() + VisualConfig.BOT_DELAY
        else:
             # Якщо зараз хід гравця (або анімація), ми "відсуваємо" таймер бота.
             # Це гарантує, що як тільки хід перейде до бота, він почекає BOT_DELAY
             # перед першою дією.
             self.bot_next_move_time = time.time() + VisualConfig.BOT_DELAY

        self._check_ui_controls()
        return self._flush_commands()
    
    def _check_ui_controls(self):
        # (Код без змін)
        rules = self.engine.rules
        hero_idx = 0
        
        if isinstance(rules, WarRules):
            self.command_queue.append({
                "cmd": "UPDATE_CONTROLS",
                "show_action_btn": False
            })
            return

        if isinstance(rules, DurakRules):
            hero_idx = 0
            current_active = self.engine.active_player_idx
            is_defender = (hero_idx == rules.defender_idx)
            is_attacker = not is_defender
            
            show_btn = False
            btn_text = ""
            
            if is_defender:
                if len(rules.pending_attacks) > 0 or len(self.engine.table) > 0:
                    show_btn = True
                    btn_text = "Взяти"
                if self.engine.active_player_idx != hero_idx:
                    show_btn = False
            else:
                if len(self.engine.table) > 0:
                    show_btn = True
                    btn_text = "Битом"
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
            if self.engine.active_player_idx == hero_idx:
                if rules.has_taken_card and not rules.must_cover_six:
                    show_btn = True
                    btn_text = "Пас"
                else:
                    show_btn = False
            
            self.command_queue.append({
                "cmd": "UPDATE_CONTROLS",
                "show_action_btn": show_btn,
                "btn_text": btn_text
            })
            return

    def _on_engine_event(self, event_type, data):
        # (Код без змін)
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
            
            starting_trump = self.engine.extra_data.get('starting_trump')

            self.command_queue.append({
                "cmd": "INITIAL_DEAL", 
                "hands": deals,
                "deck_count": len(self.engine.deck),
                "trump_card": trump_data,
                "starting_trump": starting_trump
            })

        if event_type == "PLAYER_DRAW_DECK":
            p = data['player']
            cards = data['cards']
            cards_data = []
            for c in cards:
                cards_data.append({"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"})
            
            self.command_queue.append({
                "cmd": "DRAW_CARDS_ANIMATION",
                "player_id": p.player_id,
                "cards": cards_data
            })

        elif event_type == "PLAYER_TOOK_CARDS":
             player = data.get('player')
             p_id = player.player_id if player else self.hero_id
             self.command_queue.append({"cmd": "TAKE_CARDS", "player_id": p_id})
             self.command_queue.append({"cmd": "SYNC_HANDS", "hands": self._get_hands_snapshot()})
             self.command_queue.append({"cmd": "CLEAR_TABLE"})

        elif event_type == "PLAYER_MOVE":
            p = data['player']
            action = data['action'] 
            is_durak = isinstance(self.engine.rules, DurakRules)
            durak_is_defense = False
            if is_durak and not isinstance(action, str):
                if self._pending_durak_is_defense is not None:
                    durak_is_defense = self._pending_durak_is_defense
                else:
                    rules = self.engine.rules
                    player_idx = self.engine.players.index(p)
                    if player_idx == rules.defender_idx and not rules.is_transfer_move:
                        durak_is_defense = True
                self._pending_durak_is_defense = None
            
            if isinstance(action, (list, tuple)):
                for card in action:
                    card_data = {"suit": card.suit, "rank": card.rank, "id": f"{card.rank}_{card.suit}"}
                    self.command_queue.append({
                        "cmd": "PLAY_CARD",
                        "player_id": p.player_id,
                        "card": card_data,
                        "durak_is_defense": durak_is_defense
                    })
            elif hasattr(action, 'suit') and hasattr(action, 'rank'): 
                card_data = {"suit": action.suit, "rank": action.rank, "id": f"{action.rank}_{action.suit}"}
                self.command_queue.append({
                    "cmd": "PLAY_CARD",
                    "player_id": p.player_id,
                    "card": card_data,
                    "durak_is_defense": durak_is_defense
                })
            elif action == "take":
                is_durak = isinstance(self.engine.rules, DurakRules)
                if is_durak:
                    self.command_queue.append({"cmd": "TAKE_CARDS", "player_id": p.player_id})
                    self.command_queue.append({"cmd": "SYNC_HANDS", "hands": self._get_hands_snapshot()})
        
        elif event_type == "TABLE_CLEARED":
            self.command_queue.append({"cmd": "CLEAR_TABLE"})
            
        elif event_type == "GAME_OVER":
            if isinstance(self.engine.rules, BridgeRules):
                scores = [{'name': p.name, 'score': p.score} for p in self.engine.players]
                self.command_queue.append({
                    "cmd": "SHOW_SCORES",
                    "is_round_end": True,
                    "scores": scores
                })
            else:
                self.command_queue.append({"cmd": "SHOW_WINNER", "winner": data['winner']})

        elif event_type == "SHOW_SUIT_SELECTOR":
            self.command_queue.append({"cmd": "SHOW_SUIT_SELECTOR", "player_id": data['player_id']})
            
        elif event_type == "SHOW_BONUS_SELECTOR":
            self.command_queue.append({
                "cmd": "SHOW_BONUS_SELECTOR",
                "player_id": data['player_id'],
                "mult": data['mult'],
                "sub": data['sub']
            })

        elif event_type == "RESHUFFLE_TABLE":
            # Приходить top_card (об'єкт) і new_count (int)
            top = data['top_card']
            
            # Формуємо команду для VisualEngine
            self.command_queue.append({
                "cmd": "ANIMATE_RESHUFFLE",
                "top_card": {
                    "suit": top.suit,
                    "rank": top.rank,
                    "id": f"{top.rank}_{top.suit}"
                },
                "new_count": data['new_count']
            })

        elif event_type == "SUIT_ORDERED":
            self.command_queue.append({
                "cmd": "SHOW_ORDERED_SUIT",
                "suit": data['suit']
            })
            
        elif event_type == "SUIT_CLEARED":
            self.command_queue.append({
                "cmd": "HIDE_ORDERED_SUIT"
            })
        elif event_type == "TURN_SWITCH":
            idx = data.get("active_player_idx")
            if idx is not None and idx < len(self.engine.players):
                p = self.engine.players[idx]
                self.command_queue.append({
                    "cmd": "UPDATE_TURN",
                    "player_id": p.player_id,
                    "player_name": p.name
                })
            
        self._check_ui_controls()

    def _get_hands_snapshot(self):
        res = []
        for p in self.engine.players:
            cards = [{"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"} for c in p.hand]
            res.append({"player_id": p.player_id, "cards_data": cards})
        return res

    def _flush_commands(self):
        res = list(self.command_queue)
        self.command_queue = []
        return res
    
    def _reset_bot_timer(self):
        """Скидає таймер: бот чекатиме BOT_DELAY секунд"""
        self.bot_next_move_time = time.time() + VisualConfig.BOT_DELAY
    
    def _announce_turn(self):
        if not self.engine or not self.engine.players:
            return
        current_idx = self.engine.active_player_idx
        current_player = self.engine.players[current_idx]
        self.command_queue.append({
            "cmd": "UPDATE_TURN",
            "player_id": current_player.player_id,
            "player_name": current_player.name
        })

    def start_next_round(self):
        print("--- ЗАПУСК НОВОГО РАУНДУ ---")
        
        # 1. Скидаємо прапорець кінця гри
        self.engine.game_over = False
        
        # 2. Створюємо нову колоду
        new_deck = Deck()
        self.engine.setup_game(new_deck)
        
        # 3. !!! ВАЖЛИВО !!! 
        # Спочатку відправляємо команду на налаштування столу (вона очистить старе).
        # Це має бути ПЕРЕД start_game(), щоб не стерти нову роздачу.
        self.command_queue.append({
            "cmd": "SETUP_TABLE",
            "game_type": self.game_type,
            "multi_select": self.game_type != "WAR",
            "players": [
                {"id": p.player_id, "name": p.name, "is_hero": (p.player_id == self.hero_id)}
                for p in self.engine.players
            ]
        })
        
        # 4. Тепер запускаємо гру.
        # Всередині спрацює подія DEAL_CARDS, яка додасть правильний INITIAL_DEAL у чергу.
        # Оскільки SETUP_TABLE вже в черзі першим, анімація колоди спрацює поверх чистого столу.
        self.engine.start_game()
        
        # 5. Скидаємо таймер бота
        self._reset_bot_timer()
        self.waiting_for_deal = True
        self._announce_turn()

        # Примітка: Ми більше НЕ додаємо порожній "INITIAL_DEAL" вручну, 
        # бо його додасть обробник подій _on_engine_event автоматично.

        self._check_ui_controls()

    def _get_max_players(self, game_type):
        if game_type == "BRIDGE":
            deck_size = 36
            initial_cards = 6
        else:
            deck_size = len(Deck().cards)
            initial_cards = 6
        return max(2, deck_size // initial_cards)

    def _start_game_with_players(self, count, rules_settings=None):
        max_players = self.pending_max_players or 2
        count = max(2, min(int(count), max_players))
        self.waiting_for_player_count = False
        self.engine = None

        is_multi_select = True
        if self.pending_game_type == "WAR":
            rules = WarRules()
            is_multi_select = False
        elif self.pending_game_type == "BRIDGE":
            rules = BridgeRules()
        else:
            rules = DurakRules(settings=rules_settings)

        self.engine = GameEngine(rules)
        self.engine.on_game_event = self._on_engine_event
        self.pending_is_multi_select = is_multi_select
        self.engine.players = []
        
        hero = Player("Hero", player_id=self.hero_id)
        self.engine.add_player(hero)
        for idx in range(1, count):
            bot = BotPlayer(f"Bot {idx}", player_id=f"bot_{idx}")
            self.engine.add_player(bot)

        deck = Deck()
        self.engine.setup_game(deck)

        setup_cmd = {
            "cmd": "SETUP_TABLE",
            "game_type": self.game_type,
            "multi_select": self.pending_is_multi_select,
            "players": [
                {"id": p.player_id, "name": ("Я" if p.player_id == self.hero_id else p.name), "is_hero": (p.player_id == self.hero_id)}
                for p in self.engine.players
            ]
        }
        self.command_queue.append(setup_cmd)

        self.engine.start_game()
        self.bot_next_move_time = time.time() + VisualConfig.BOT_DELAY
        self.waiting_for_deal = True
        self._announce_turn()

    def _should_ask_for_throw(self, action):
        if not isinstance(self.engine.rules, DurakRules):
            return False
        if action not in ("pass", "take"):
            return False
        rules = self.engine.rules
        hero = self.engine.players[0]
        if self.engine.active_player_idx == 0:
            return False
        if rules.defender_idx == 0:
            return False
        if not self.engine.table:
            return False
        ranks_on_table = {c.rank for c in self.engine.table}
        for c in hero.hand:
            if c.rank in ranks_on_table:
                return True
        return False

    def _predict_durak_defense(self, action, player):
        if not isinstance(self.engine.rules, DurakRules):
            return False
        if isinstance(action, str):
            return False
        rules = self.engine.rules
        try:
            player_idx = self.engine.players.index(player)
        except ValueError:
            return False
        if player_idx != rules.defender_idx:
            return False
        cards_played = action if isinstance(action, (list, tuple)) else [action]
        if not cards_played:
            return False
        can_transfer = rules.settings.get("mode") in ("perevodnoy", "mixed") and rules.transfer_allowed
        if rules.pending_attacks and can_transfer and len(cards_played) == len(rules.pending_attacks):
            match = all(
                cards_played[i].rank == rules.pending_attacks[i].rank
                for i in range(len(cards_played))
            )
            if match:
                return False
        return True
