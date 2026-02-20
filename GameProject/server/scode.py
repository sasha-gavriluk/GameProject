import asyncio
import websockets
import json
import uuid
import sys 
import os
import http

from server.api import ServerCommands
from server.database import Database

class Room:
    def __init__(self, room_id, creator_name, db):
        self.db = db
        self.room_id = room_id
        self.host = creator_name # Голова кімнати
        self.clients = {}  # {username: websocket}
        self.players_state = {} # {username: {"ready": False}}
        self.settings = {
            "game_type": "DURAK",
            "countdown": 5,
            "durak_mode": "mixed",
            "deck_size": 36
        }
        self.countdown_task = None
        self.game_started = False

    async def broadcast(self, message):
        if not self.clients: return
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
        """Відправляє всім актуальний стан кімнати"""
        await self.broadcast({
            "type": "ROOM_STATE",
            "host": self.host,
            "players": self.players_state,
            "settings": self.settings
        })

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
                "WebSocket Game Server is running! Use ws:// or wss:// to connect.\n"
            )
        return None

    async def start(self):
        async with websockets.serve(self.handle_connection, self.host, self.port, process_request=self.process_http_request):
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

                # --- Реєстрація та Вхід ---
                if command == ServerCommands.REGISTER:
                    success, msg = self.db.register_user(payload.get('username'), payload.get('password'))
                    await websocket.send(json.dumps({"type": ServerCommands.REGISTRATION_SUCCESS if success else ServerCommands.ERROR, "message": msg}))

                elif command == ServerCommands.LOGIN:
                    success, msg = self.db.authenticate_user(payload.get('username'), payload.get('password'))
                    if success:
                        username = payload.get('username')
                        authenticated = True
                        await websocket.send(json.dumps({"type": ServerCommands.AUTH_SUCCESS, "username": username}))
                    else:
                        await websocket.send(json.dumps({"type": ServerCommands.AUTH_ERROR, "message": msg}))

                # --- Ігрова логіка Лоббі ---
                elif authenticated:
                    if command == ServerCommands.CREATE_ROOM:
                        current_room_id = await self.create_room(websocket, username)
                    
                    elif command == ServerCommands.JOIN_ROOM:
                        payload['username'] = username
                        joined_id = await self.join_room(websocket, payload)
                        if joined_id: current_room_id = joined_id
                    
                    elif command == ServerCommands.SEND_MESSAGE:
                        if current_room_id and current_room_id in self.rooms:
                            await self.rooms[current_room_id].broadcast({
                                "type": ServerCommands.SEND_MESSAGE,
                                "username": username, "message": payload.get("message", "")
                            })

                    elif command == "GET_ROOM_STATE":
                        if current_room_id and current_room_id in self.rooms:
                            await self.rooms[current_room_id].broadcast_state()

                    elif command == "READY_TOGGLE":
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            # Голова завжди готовий автоматично, коли запускає гру, але може теж тицяти
                            current_state = room.players_state[username]["ready"]
                            room.players_state[username]["ready"] = not current_state
                            await room.broadcast_state()

                    elif command == "UPDATE_SETTINGS":
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            if username == room.host: # Лише голова може міняти
                                new_settings = payload.get("settings", {})
                                room.settings.update(new_settings)
                                await room.broadcast({
                                    "type": ServerCommands.SEND_MESSAGE,
                                    "username": "Система", 
                                    "message": f"Голова оновив налаштування: {new_settings}"
                                })
                                await room.broadcast_state()

                    elif command == "START_GAME":
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            if username == room.host:
                                all_ready = all(p["ready"] for u, p in room.players_state.items() if u != room.host)
                                if all_ready or len(room.players_state) == 1: # Дозволяємо старт самому для тестів
                                    if room.countdown_task is None:
                                        room.countdown_task = asyncio.create_task(self.run_countdown(room))
                                else:
                                    await websocket.send(json.dumps({"type": ServerCommands.SEND_MESSAGE, "username": "Система", "message": "Не всі гравці готові!"}))
                
        except Exception as e:
            print(f"З'єднання розірвано: {e}")
            await self.handle_disconnect(username, current_room_id)

    async def handle_disconnect(self, username, room_id):
        if room_id and room_id in self.rooms:
            room = self.rooms[room_id]
            if username in room.clients:
                del room.clients[username]
                del room.players_state[username]
                
                # Передача прав Голови, якщо він вийшов
                if username == room.host and room.clients:
                    room.host = list(room.clients.keys())[0]
                    await room.broadcast({"type": ServerCommands.SEND_MESSAGE, "username": "Система", "message": f"{room.host} тепер новий Голова кімнати!"})
                
                # Якщо кімната пуста - видаляємо
                if not room.clients:
                    del self.rooms[room_id]
                else:
                    await room.broadcast({"type": ServerCommands.SEND_MESSAGE, "username": "Система", "message": f"{username} покинув лоббі."})
                    await room.broadcast_state()

    async def run_countdown(self, room):
        seconds = int(room.settings.get("countdown", 5))
        for i in range(seconds, 0, -1):
            await room.broadcast({"type": ServerCommands.SEND_MESSAGE, "username": "Система", "message": f"Старт через {i}..."})
            await asyncio.sleep(1)
            
        await room.broadcast({"type": ServerCommands.SEND_MESSAGE, "username": "Система", "message": "ГРА ПОЧАЛАСЯ! (Завантаження столу...)"})
        # Тут в майбутньому буде: await room.broadcast({"type": "LOAD_GAME_SCREEN"})
        room.countdown_task = None

    async def create_room(self, websocket, username):
        room_id = str(uuid.uuid4())[:8]
        new_room = Room(room_id, username, self.db)
        new_room.clients[username] = websocket
        new_room.players_state[username] = {"ready": True} # Голова готовий за замовчуванням
        self.rooms[room_id] = new_room
        
        await websocket.send(json.dumps({"type": ServerCommands.ROOM_CREATED, "room_id": room_id}))
        return room_id

    async def join_room(self, websocket, payload):
        room_id = payload.get("room_id")
        username = payload.get("username")

        if room_id in self.rooms:
            room = self.rooms[room_id]
            room.clients[username] = websocket
            room.players_state[username] = {"ready": False}
            
            await websocket.send(json.dumps({"type": ServerCommands.JOIN_ROOM, "message": f"Ви приєднались до {room_id}"}))
            await room.broadcast({"type": ServerCommands.SEND_MESSAGE, "username": "Система", "message": f"{username} приєднався до гри!"})
            await room.broadcast_state()
            return room_id
        else:
            await websocket.send(json.dumps({"type": ServerCommands.ERROR, "message": "Кімнату не знайдено"}))
            return None