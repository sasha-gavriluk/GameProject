import asyncio
import http
import json
import uuid
from collections import deque

import websockets

from server.database import Database
from utils.api import ServerCommands
from utils.cards import Deck
from utils.engine import GameEngine, Player
from utils.rule.rules_bridge import BridgeRules
from utils.rule.rules_durak import DurakRules
from utils.rule.rules_war import WarRules


class RoomGameSession:
    """Server-authoritative game session for one lobby room."""

    def __init__(self, room):
        self.room = room
        self.engine = None
        self.player_order = []
        self.player_by_username = {}
        self._pending_durak_is_defense = None
        self._event_queue = deque()
        self._event_busy = False
        self._round_transition_busy = False

    async def start(self):
        game_type = self.room.settings.get("game_type", "DURAK")
        deck_size = int(self.room.settings.get("deck_size", 36))

        # Stable player order: host first, then join order.
        users = list(self.room.clients.keys())
        if self.room.host in users:
            users.remove(self.room.host)
            users.insert(0, self.room.host)
        self.player_order = users

        if game_type == "WAR":
            rules = WarRules()
            if len(self.player_order) > 2:
                self.player_order = self.player_order[:2]
        elif game_type == "BRIDGE":
            rules = BridgeRules()
            deck_size = 36
        else:
            durak_mode = self.room.settings.get("durak_mode", "mixed")
            neighbors_only = bool(self.room.settings.get("neighbors_only", True))
            allow_overthrow = bool(self.room.settings.get("allow_overthrow", True))
            first_bout_5 = bool(self.room.settings.get("first_bout_5", False))
            rules = DurakRules(
                settings={
                    "mode": durak_mode,
                    "neighbors_only": neighbors_only,
                    "allow_overthrow": allow_overthrow,
                    "first_bout_5": first_bout_5,
                }
            )

        self.engine = GameEngine(rules)
        self.engine.on_game_event = self.on_engine_event

        for username in self.player_order:
            p = Player(name=username, player_id=username)
            self.player_by_username[username] = p
            self.engine.add_player(p)

        deck = Deck(size=deck_size)
        if isinstance(rules, WarRules):
            rules.initial_cards_count = max(1, deck_size // max(1, len(self.engine.players)))

        self.engine.setup_game(deck)

        # Notify room that online game is starting.
        await self.room.broadcast(
            {
                "type": ServerCommands.GAME_STARTED,
                "room_id": self.room.room_id,
                "game_type": game_type,
                "online": True,
            }
        )

        # Initial setup is per-client, because each player must see only own cards face up.
        for username in self.player_order:
            await self._send_setup_table(username)

        self.engine.start_game()
        await self._announce_turn()
        await self._send_controls_all()

    def on_engine_event(self, event_type, data):
        self._event_queue.append((event_type, data))
        if not self._event_busy:
            asyncio.create_task(self._drain_events())

    async def _drain_events(self):
        if self._event_busy:
            return
        self._event_busy = True
        try:
            while self._event_queue:
                event_type, data = self._event_queue.popleft()
                await self._handle_engine_event(event_type, data)
        finally:
            self._event_busy = False

    async def _handle_engine_event(self, event_type, data):
        if not self.engine:
            return

        if event_type == "DEAL_CARDS":
            trump_card = self.engine.extra_data.get("trump")
            trump_data = None
            if trump_card:
                trump_data = {
                    "suit": trump_card.suit,
                    "rank": trump_card.rank,
                    "id": f"{trump_card.rank}_{trump_card.suit}",
                }

            starting_trump = self.engine.extra_data.get("starting_trump")
            deck_count = len(self.engine.deck.cards) if self.engine.deck else 0

            for username in self.player_order:
                await self.room.send_to(
                    username,
                    {
                        "type": ServerCommands.GAME_INSTRUCTION,
                        "instruction": {
                            "cmd": "INITIAL_DEAL",
                            "hands": self._hands_snapshot_for(username),
                            "deck_count": deck_count,
                            "trump_card": trump_data,
                            "starting_trump": starting_trump,
                        },
                    },
                )

        elif event_type == "PLAYER_DRAW_DECK":
            player = data["player"]
            cards = data["cards"]
            for username in self.player_order:
                cards_payload = []
                if username == player.player_id:
                    cards_payload = [
                        {"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"}
                        for c in cards
                    ]
                else:
                    cards_payload = [
                        {"suit": "spades", "rank": "A", "id": f"hidden_{i}"}
                        for i, _ in enumerate(cards)
                    ]

                await self.room.send_to(
                    username,
                    {
                        "type": ServerCommands.GAME_INSTRUCTION,
                        "instruction": {
                            "cmd": "DRAW_CARDS_ANIMATION",
                            "player_id": player.player_id,
                            "cards": cards_payload,
                        },
                    },
                )

        elif event_type == "PLAYER_MOVE":
            player = data["player"]
            action = data["action"]
            durak_is_defense = self._resolve_durak_defense(player, action)

            if isinstance(action, (list, tuple)):
                cards = list(action)
            elif hasattr(action, "suit") and hasattr(action, "rank"):
                cards = [action]
            else:
                cards = []

            if cards:
                is_durak = isinstance(self.engine.rules, DurakRules)
                if is_durak:
                    for c in cards:
                        await self.room.broadcast(
                            {
                                "type": ServerCommands.GAME_INSTRUCTION,
                                "instruction": {
                                    "cmd": "PLAY_CARD",
                                    "player_id": player.player_id,
                                    "card": {"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"},
                                    "durak_is_defense": durak_is_defense,
                                },
                            }
                        )
                else:
                    await self.room.broadcast(
                        {
                            "type": ServerCommands.GAME_INSTRUCTION,
                            "instruction": {
                                "cmd": "PLAY_CARDS",
                                "player_id": player.player_id,
                                "cards": [{"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"} for c in cards],
                            },
                        }
                    )

        elif event_type == "PLAYER_TOOK_CARDS":
            player = data.get("player")
            if player:
                await self.room.broadcast(
                    {
                        "type": ServerCommands.GAME_INSTRUCTION,
                        "instruction": {"cmd": "TAKE_CARDS", "player_id": player.player_id},
                    }
                )

        elif event_type == "TABLE_CLEARED":
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {"cmd": "CLEAR_TABLE"},
                }
            )

        elif event_type == "RESHUFFLE_TABLE":
            top = data["top_card"]
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {
                        "cmd": "ANIMATE_RESHUFFLE",
                        "top_card": {"suit": top.suit, "rank": top.rank, "id": f"{top.rank}_{top.suit}"},
                        "new_count": data.get("new_count", 0),
                    },
                }
            )

        elif event_type == "SUIT_ORDERED":
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {"cmd": "SHOW_ORDERED_SUIT", "suit": data.get("suit")},
                }
            )

        elif event_type == "SUIT_CLEARED":
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {"cmd": "HIDE_ORDERED_SUIT"},
                }
            )

        elif event_type == "SHOW_SUIT_SELECTOR":
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {"cmd": "SHOW_SUIT_SELECTOR", "player_id": data.get("player_id")},
                }
            )

        elif event_type == "SHOW_BONUS_SELECTOR":
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {
                        "cmd": "SHOW_BONUS_SELECTOR",
                        "player_id": data.get("player_id"),
                        "mult": data.get("mult"),
                        "sub": data.get("sub"),
                    },
                }
            )
        elif event_type == "SHOW_DURAK_DEFENSE_CHOICE":
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {
                        "cmd": "SHOW_DURAK_DEFENSE_CHOICE",
                        "player_id": data.get("player_id"),
                    },
                }
            )
        elif event_type == "SHOW_BRIDGE_DECISION":
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {
                        "cmd": "SHOW_BRIDGE_DECISION",
                        "player_id": data.get("player_id"),
                    },
                }
            )
        elif event_type == "INVALID_CHAIN_CARD":
            bad = data.get("invalid_card")
            bad_id = f"{bad.rank}_{bad.suit}" if bad else None
            await self.room.broadcast(
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {
                        "cmd": "INVALID_CHAIN_CARD",
                        "invalid_id": bad_id,
                        "keep_ids": data.get("keep_ids", []),
                    },
                }
            )

        elif event_type == "GAME_OVER":
            if isinstance(self.engine.rules, BridgeRules):
                active_players = [p for p in self.engine.players if not getattr(p, "is_eliminated", False)]
                if len(active_players) > 1:
                    scores = [{"name": p.name, "score": p.score} for p in self.engine.players]
                    await self.room.broadcast(
                        {
                            "type": ServerCommands.GAME_INSTRUCTION,
                            "instruction": {
                                "cmd": "SHOW_SCORES",
                                "is_round_end": True,
                                "scores": scores,
                            },
                        }
                    )
                else:
                    winner_name = active_players[0].name if active_players else "Невідомо"
                    await self.room.broadcast(
                        {
                            "type": ServerCommands.GAME_INSTRUCTION,
                            "instruction": {
                                "cmd": "SHOW_WINNER",
                                "winner": winner_name,
                                "online": True,
                            },
                        }
                    )
                    await self._finish_match_and_return_to_room()
            else:
                await self.room.broadcast(
                    {
                        "type": ServerCommands.GAME_INSTRUCTION,
                        "instruction": {
                            "cmd": "SHOW_WINNER",
                            "winner": data.get("winner", "Невідомо"),
                            "online": True,
                        },
                    }
                )
                await self._finish_match_and_return_to_room()

        elif event_type == "TURN_SWITCH":
            await self._announce_turn()

        # Keep controls in sync and hands private after every state-changing event.
        if event_type in {
            "PLAYER_MOVE",
            "PLAYER_TOOK_CARDS",
            "TABLE_CLEARED",
            "PLAYER_DRAW_DECK",
            "TURN_SWITCH",
            "DEAL_CARDS",
            "RESHUFFLE_TABLE",
        }:
            await self._sync_hands_all()
            await self._send_controls_all()

    async def _send_setup_table(self, username):
        is_multi_select = self.room.settings.get("game_type", "DURAK") != "WAR"
        players_payload = []
        for p in self.engine.players:
            players_payload.append(
                {
                    "id": p.player_id,
                    "name": "Я" if p.player_id == username else p.name,
                    "is_hero": p.player_id == username,
                }
            )

        await self.room.send_to(
            username,
            {
                "type": ServerCommands.GAME_INSTRUCTION,
                "instruction": {
                    "cmd": "SETUP_TABLE",
                    "game_type": self.room.settings.get("game_type", "DURAK"),
                    "online": True,
                    "multi_select": is_multi_select,
                    "players": players_payload,
                },
            },
        )

    async def send_full_snapshot(self, username):
        if username not in self.player_order:
            return

        game_type = self.room.settings.get("game_type", "DURAK")
        is_multi_select = game_type != "WAR"
        players_payload = []
        for p in self.engine.players:
            players_payload.append(
                {
                    "id": p.player_id,
                    "name": "Я" if p.player_id == username else p.name,
                    "is_hero": p.player_id == username,
                }
            )

        trump_card = self.engine.extra_data.get("trump")
        trump_data = None
        if trump_card:
            trump_data = {
                "suit": trump_card.suit,
                "rank": trump_card.rank,
                "id": f"{trump_card.rank}_{trump_card.suit}",
            }
        starting_trump = self.engine.extra_data.get("starting_trump")
        deck_count = len(self.engine.deck.cards) if self.engine.deck else 0

        controls = self._controls_for_player(username, self.engine.rules)
        turn_player = self.engine.players[self.engine.active_player_idx] if self.engine.players else None

        instructions = [
            {
                "cmd": "SETUP_TABLE",
                "game_type": game_type,
                "online": True,
                "multi_select": is_multi_select,
                "players": players_payload,
            },
            {
                "cmd": "INITIAL_DEAL",
                "hands": self._hands_snapshot_for(username),
                "deck_count": deck_count,
                "trump_card": trump_data,
                "starting_trump": starting_trump,
            },
            {
                "cmd": "UPDATE_CONTROLS",
                "show_action_btn": controls["show_action_btn"],
                "btn_text": controls["btn_text"],
            },
        ]
        if turn_player:
            instructions.append(
                {
                    "cmd": "UPDATE_TURN",
                    "player_id": turn_player.player_id,
                    "player_name": turn_player.name,
                }
            )

        await self.room.send_to(
            username,
            {
                "type": ServerCommands.GAME_BATCH,
                "instructions": instructions,
            },
        )

    def _hands_snapshot_for(self, username):
        snapshot = []
        for p in self.engine.players:
            if p.player_id == username:
                cards_data = [
                    {"suit": c.suit, "rank": c.rank, "id": f"{c.rank}_{c.suit}"}
                    for c in p.hand
                ]
            else:
                cards_data = [
                    {"suit": "spades", "rank": "A", "id": f"hidden_{i}"}
                    for i, _ in enumerate(p.hand)
                ]

            snapshot.append(
                {
                    "player_id": p.player_id,
                    "cards_data": cards_data,
                    "is_eliminated": bool(getattr(p, "is_eliminated", False)),
                }
            )
        return snapshot

    async def _sync_hands_all(self):
        for username in self.player_order:
            await self.room.send_to(
                username,
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {"cmd": "SYNC_HANDS", "hands": self._hands_snapshot_for(username)},
                },
            )

    async def _announce_turn(self):
        if not self.engine or not self.engine.players:
            return
        idx = self.engine.active_player_idx
        current = self.engine.players[idx]
        await self.room.broadcast(
            {
                "type": ServerCommands.GAME_INSTRUCTION,
                "instruction": {
                    "cmd": "UPDATE_TURN",
                    "player_id": current.player_id,
                    "player_name": current.name,
                },
            }
        )

    async def _send_controls_all(self):
        if not self.engine:
            return

        rules = self.engine.rules
        for username in self.player_order:
            cmd = self._controls_for_player(username, rules)
            await self.room.send_to(
                username,
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {
                        "cmd": "UPDATE_CONTROLS",
                        "show_action_btn": cmd["show_action_btn"],
                        "btn_text": cmd["btn_text"],
                    },
                },
            )

    async def _start_next_round(self):
        if not self.engine or self._round_transition_busy:
            return False

        if not self.engine.game_over:
            return False

        if isinstance(self.engine.rules, BridgeRules):
            active_players = [p for p in self.engine.players if not getattr(p, "is_eliminated", False)]
            if len(active_players) <= 1:
                return False

        self._round_transition_busy = True
        try:
            game_type = self.room.settings.get("game_type", "DURAK")
            deck_size = int(self.room.settings.get("deck_size", 36))
            if game_type == "BRIDGE":
                deck_size = 36

            self.engine.game_over = False
            new_deck = Deck(size=deck_size)
            if isinstance(self.engine.rules, WarRules):
                self.engine.rules.initial_cards_count = max(1, deck_size // max(1, len(self.engine.players)))

            self.engine.setup_game(new_deck)

            for username in self.player_order:
                await self._send_setup_table(username)

            self.engine.start_game()
            await self._announce_turn()
            await self._send_controls_all()
            return True
        finally:
            self._round_transition_busy = False

    async def _finish_match_and_return_to_room(self):
        self.room.game_started = False
        if self.room.game_session is self:
            self.room.game_session = None

        # Після завершення матчу повертаємо готовність у стан лобі:
        # хост готовий, решта мають підтвердити готовність знову.
        for username, state in self.room.players_state.items():
            state["ready"] = bool(username == self.room.host)
        await self.room.broadcast_state()

    def _controls_for_player(self, username, rules):
        hero_idx = self.player_order.index(username)
        hero_player = self.engine.players[hero_idx] if hero_idx < len(self.engine.players) else None
        if hero_player and getattr(hero_player, "is_eliminated", False):
            return {"show_action_btn": False, "btn_text": ""}

        if isinstance(rules, WarRules):
            return {"show_action_btn": False, "btn_text": ""}

        if isinstance(rules, DurakRules):
            is_defender = hero_idx == rules.defender_idx
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

            return {"show_action_btn": show_btn, "btn_text": btn_text}

        if isinstance(rules, BridgeRules):
            show_btn = False
            btn_text = ""
            if self.engine.active_player_idx == hero_idx:
                if rules.has_taken_card and not rules.must_cover_six:
                    show_btn = True
                    btn_text = "Пас"
            return {"show_action_btn": show_btn, "btn_text": btn_text}

        return {"show_action_btn": False, "btn_text": ""}

    def _resolve_durak_defense(self, player, action):
        is_durak = isinstance(self.engine.rules, DurakRules)
        if not is_durak or isinstance(action, str):
            return False

        durak_is_defense = False
        if self._pending_durak_is_defense is not None:
            durak_is_defense = self._pending_durak_is_defense
        else:
            rules = self.engine.rules
            if hasattr(rules, "defender_idx"):
                player_idx = self.engine.players.index(player)
                if player_idx == rules.defender_idx and not rules.is_transfer_move:
                    durak_is_defense = True
        self._pending_durak_is_defense = None
        return durak_is_defense

    async def handle_action(self, username, payload):
        if not self.engine:
            return

        if username not in self.player_order:
            await self.room.send_to(username, {"type": ServerCommands.GAME_ERROR, "message": "Гравця не знайдено"})
            return

        action = payload.get("action")
        if action == "get_scores":
            scores = [{"name": p.name, "score": p.score} for p in self.engine.players]
            await self.room.send_to(
                username,
                {
                    "type": ServerCommands.GAME_INSTRUCTION,
                    "instruction": {
                        "cmd": "SHOW_SCORES",
                        "is_round_end": False,
                        "scores": scores,
                    },
                },
            )
            return

        if action == "start_new_round":
            started = await self._start_next_round()
            if not started:
                await self.room.send_to(
                    username,
                    {
                        "type": ServerCommands.GAME_ERROR,
                        "message": "Новий раунд зараз недоступний",
                    },
                )
            return

        player_idx = self.player_order.index(username)
        if player_idx != self.engine.active_player_idx:
            await self.room.send_to(username, {"type": ServerCommands.GAME_ERROR, "message": "Зараз не ваш хід"})
            return

        current_player = self.engine.players[self.engine.active_player_idx]
        if getattr(current_player, "is_eliminated", False):
            await self.room.send_to(username, {"type": ServerCommands.GAME_ERROR, "message": "Ви вибули з гри"})
            return

        engine_action = None
        if action == "play":
            card_ids = payload.get("cards", [])
            cards = []
            for cid in card_ids:
                found = next((c for c in current_player.hand if f"{c.rank}_{c.suit}" == cid), None)
                if found:
                    cards.append(found)
            if not cards:
                await self.room.send_to(username, {"type": ServerCommands.GAME_ERROR, "message": "Карта не знайдена"})
                return
            mixed_ranks = len({c.rank for c in cards}) > 1
            if isinstance(self.engine.rules, BridgeRules) and len(cards) > 1 and mixed_ranks:
                engine_action = {"action": "play_chain", "cards": cards}
            else:
                self._pending_durak_is_defense = self._predict_durak_defense(cards, current_player)
                engine_action = cards if len(cards) > 1 else cards[0]

        elif action in {"take", "pass"}:
            engine_action = action

        elif action == "set_suit":
            engine_action = {"action": "set_suit", "suit": payload.get("suit")}

        elif action == "set_bonus":
            engine_action = {"action": "set_bonus", "choice": payload.get("choice")}
        elif action == "set_durak_defense_choice":
            engine_action = {"action": "set_durak_defense_choice", "choice": payload.get("choice")}
        elif action == "set_bridge_decision":
            engine_action = {"action": "set_bridge_decision", "choice": payload.get("choice")}

        else:
            await self.room.send_to(username, {"type": ServerCommands.GAME_ERROR, "message": "Невідома дія"})
            return

        ok = self.engine.play_turn(engine_action)
        if not ok:
            self._pending_durak_is_defense = None
            await self.room.send_to(username, {"type": ServerCommands.GAME_ERROR, "message": "Невірний хід"})

    def _predict_durak_defense(self, action, player):
        rules = self.engine.rules
        if not isinstance(rules, DurakRules):
            return False
        if isinstance(action, str):
            return False
        player_idx = self.engine.players.index(player)
        if player_idx != rules.defender_idx:
            return False
        cards_played = action if isinstance(action, (list, tuple)) else [action]
        if not cards_played:
            return False
        can_transfer = rules.settings.get("mode") in ("perevodnoy", "mixed") and rules.transfer_allowed
        if rules.pending_attacks and can_transfer and 0 < len(cards_played) <= len(rules.pending_attacks):
            if all(c.rank == rules.pending_attacks[0].rank for c in cards_played):
                return False
        return not rules.is_transfer_move


class Room:
    def __init__(self, room_id, creator_name, db):
        self.db = db
        self.room_id = room_id
        self.host = creator_name
        self.clients = {}  # {username: websocket}
        self.players_state = {}  # {username: {"ready": False}}
        self.settings = {
            "game_type": "DURAK",
            "countdown": 5,
            "durak_mode": "mixed",
            "deck_size": 36,
            "neighbors_only": True,
            "allow_overthrow": True,
            "first_bout_5": False,
        }
        self.countdown_task = None
        self.game_started = False
        self.game_session = None

    async def send_to(self, username, message):
        ws = self.clients.get(username)
        if not ws:
            return
        try:
            await ws.send(json.dumps(message))
        except Exception:
            if username in self.clients:
                del self.clients[username]

    async def broadcast(self, message):
        if not self.clients:
            return
        disconnected_users = []
        for username, ws in self.clients.items():
            try:
                await ws.send(json.dumps(message))
            except Exception:
                disconnected_users.append(username)

        for user in disconnected_users:
            if user in self.clients:
                del self.clients[user]

    async def broadcast_state(self):
        await self.broadcast(
            {
                "type": ServerCommands.ROOM_STATE,
                "host": self.host,
                "players": self.players_state,
                "settings": self.settings,
            }
        )


class GameServer:
    def __init__(self, host="localhost", port=8080):
        self.host = host
        self.port = port
        self.db = Database()
        self.rooms = {}

    def process_http_request(self, connection, request):
        upgrade_header = request.headers.get("Upgrade", "")
        if upgrade_header.lower() != "websocket":
            return connection.respond(
                http.HTTPStatus.OK,
                "WebSocket Game Server is running! Use ws:// or wss:// to connect.\n",
            )
        return None

    async def start(self):
        async with websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            process_request=self.process_http_request,
        ):
            print(f"🚀 Сервер запущено на ws://{self.host}:{self.port}")
            await asyncio.Future()

    async def handle_connection(self, websocket):
        username = None
        authenticated = False
        current_room_id = None

        try:
            async for message in websocket:
                data = json.loads(message)
                command = data.get("command")
                payload = data.get("payload", {})

                if command == ServerCommands.REGISTER:
                    success, msg = self.db.register_user(payload.get("username"), payload.get("password"))
                    await websocket.send(
                        json.dumps(
                            {
                                "type": ServerCommands.REGISTRATION_SUCCESS if success else ServerCommands.ERROR,
                                "message": msg,
                            }
                        )
                    )

                elif command == ServerCommands.LOGIN:
                    success, msg = self.db.authenticate_user(payload.get("username"), payload.get("password"))
                    if success:
                        username = payload.get("username")
                        authenticated = True
                        await websocket.send(json.dumps({"type": ServerCommands.AUTH_SUCCESS, "username": username}))
                    else:
                        await websocket.send(json.dumps({"type": ServerCommands.AUTH_ERROR, "message": msg}))

                elif authenticated:
                    if command == ServerCommands.CREATE_ROOM:
                        current_room_id = await self.create_room(websocket, username)

                    elif command == ServerCommands.JOIN_ROOM:
                        payload["username"] = username
                        joined_id = await self.join_room(websocket, payload)
                        if joined_id:
                            current_room_id = joined_id

                    elif command == ServerCommands.SEND_MESSAGE:
                        if current_room_id and current_room_id in self.rooms:
                            await self.rooms[current_room_id].broadcast(
                                {
                                    "type": ServerCommands.SEND_MESSAGE,
                                    "username": username,
                                    "message": payload.get("message", ""),
                                }
                            )

                    elif command == ServerCommands.GET_ROOM_STATE:
                        if current_room_id and current_room_id in self.rooms:
                            await self.rooms[current_room_id].broadcast_state()

                    elif command == ServerCommands.READY_TOGGLE:
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            if room.game_started:
                                await room.send_to(
                                    username,
                                    {"type": ServerCommands.ERROR, "message": "Гра вже розпочата"},
                                )
                                continue
                            current_state = room.players_state[username]["ready"]
                            room.players_state[username]["ready"] = not current_state
                            await room.broadcast_state()

                    elif command == ServerCommands.UPDATE_SETTINGS:
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            if username == room.host and not room.game_started:
                                new_settings = payload.get("settings", {})
                                room.settings.update(new_settings)
                                await room.broadcast(
                                    {
                                        "type": ServerCommands.SEND_MESSAGE,
                                        "username": "Система",
                                        "message": f"Голова оновив налаштування: {new_settings}",
                                    }
                                )
                                await room.broadcast_state()

                    elif command == ServerCommands.START_GAME:
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            if username == room.host:
                                all_ready = all(
                                    p["ready"] for u, p in room.players_state.items() if u != room.host
                                )
                                if all_ready or len(room.players_state) == 1:
                                    if room.countdown_task is None:
                                        room.countdown_task = asyncio.create_task(self.run_countdown(room))
                                else:
                                    await room.send_to(
                                        username,
                                        {
                                            "type": ServerCommands.SEND_MESSAGE,
                                            "username": "Система",
                                            "message": "Не всі гравці готові!",
                                        },
                                    )

                    elif command == ServerCommands.GAME_ACTION:
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            if not room.game_session:
                                await room.send_to(
                                    username,
                                    {"type": ServerCommands.GAME_ERROR, "message": "Гра ще не стартувала"},
                                )
                            else:
                                await room.game_session.handle_action(username, payload)

                    elif command == ServerCommands.GET_GAME_SNAPSHOT:
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            if room.game_session:
                                await room.game_session.send_full_snapshot(username)

        except Exception as e:
            print(f"З'єднання розірвано: {e}")
        finally:
            await self.handle_disconnect(username, current_room_id)

    async def handle_disconnect(self, username, room_id):
        if room_id and room_id in self.rooms and username:
            room = self.rooms[room_id]
            if username in room.clients:
                del room.clients[username]
            if username in room.players_state:
                del room.players_state[username]

            if username == room.host and room.clients:
                room.host = list(room.clients.keys())[0]
                await room.broadcast(
                    {
                        "type": ServerCommands.SEND_MESSAGE,
                        "username": "Система",
                        "message": f"{room.host} тепер новий Голова кімнати!",
                    }
                )

            if not room.clients:
                del self.rooms[room_id]
            else:
                await room.broadcast(
                    {
                        "type": ServerCommands.SEND_MESSAGE,
                        "username": "Система",
                        "message": f"{username} покинув лоббі.",
                    }
                )
                await room.broadcast_state()

    async def run_countdown(self, room):
        seconds = int(room.settings.get("countdown", 5))
        for i in range(seconds, 0, -1):
            await room.broadcast(
                {
                    "type": ServerCommands.SEND_MESSAGE,
                    "username": "Система",
                    "message": f"Старт через {i}...",
                }
            )
            await asyncio.sleep(1)

        await room.broadcast(
            {
                "type": ServerCommands.SEND_MESSAGE,
                "username": "Система",
                "message": "ГРА ПОЧАЛАСЯ!",
            }
        )
        await self.start_game_session(room)
        room.countdown_task = None

    async def start_game_session(self, room):
        if room.game_session:
            return
        room.game_started = True
        room.game_session = RoomGameSession(room)
        await room.game_session.start()

    async def create_room(self, websocket, username):
        room_id = str(uuid.uuid4())[:8]
        new_room = Room(room_id, username, self.db)
        new_room.clients[username] = websocket
        new_room.players_state[username] = {"ready": True}
        self.rooms[room_id] = new_room

        await websocket.send(json.dumps({"type": ServerCommands.ROOM_CREATED, "room_id": room_id}))
        return room_id

    async def join_room(self, websocket, payload):
        room_id = payload.get("room_id")
        username = payload.get("username")

        if room_id not in self.rooms:
            await websocket.send(json.dumps({"type": ServerCommands.ERROR, "message": "Кімнату не знайдено"}))
            return None

        room = self.rooms[room_id]
        if room.game_started:
            await websocket.send(
                json.dumps({"type": ServerCommands.ERROR, "message": "Гра вже стартувала, підключення заборонене"})
            )
            return None

        room.clients[username] = websocket
        room.players_state[username] = {"ready": False}

        await websocket.send(
            json.dumps({"type": ServerCommands.JOIN_ROOM, "message": f"Ви приєднались до {room_id}"})
        )
        await room.broadcast(
            {
                "type": ServerCommands.SEND_MESSAGE,
                "username": "Система",
                "message": f"{username} приєднався до гри!",
            }
        )
        await room.broadcast_state()
        return room_id
