import asyncio
import websockets
import json
import uuid
import sys 
import os

from server.api import ServerCommands
from server.database import Database

class Room:
    def __init__(self, room_id, creator_name, db):
        self.db = db
        self.room_id = room_id
        self.creator_name = creator_name
        self.clients = {}  # {username: websocket}
        self.game_started = False

    async def broadcast(self, message):
        """
        Розсилає повідомлення всім клієнтам у кімнаті.
        Використовує безпечний try-except для видалення відключених клієнтів.
        """
        if not self.clients:
            return

        # Список користувачів, яких треба видалити (якщо відправка не вдалась)
        disconnected_users = []

        for username, ws in self.clients.items():
            try:
                # Просто пробуємо відправити
                await ws.send(json.dumps(message))
            except Exception:
                # Якщо помилка (сокет закритий або інше) - додаємо в список на видалення
                disconnected_users.append(username)

        # Очищаємо список клієнтів від мертвих з'єднань
        for user in disconnected_users:
            if user in self.clients:
                del self.clients[user]

class GameServer:
    def __init__(self, host="localhost", port=8765):
        self.host = host
        self.port = port
        self.db = Database()
        self.rooms = {}  # {room_id: Room object}

    async def start(self):
        async with websockets.serve(self.handle_connection, self.host, self.port):
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
                    response_type = ServerCommands.REGISTRATION_SUCCESS if success else ServerCommands.ERROR
                    await websocket.send(json.dumps({"type": response_type, "message": msg}))

                elif command == ServerCommands.LOGIN:
                    success, msg = self.db.authenticate_user(payload.get('username'), payload.get('password'))
                    if success:
                        username = payload.get('username')
                        authenticated = True
                        await websocket.send(json.dumps({"type": ServerCommands.AUTH_SUCCESS, "username": username}))
                    else:
                        await websocket.send(json.dumps({"type": ServerCommands.AUTH_ERROR, "message": msg}))

                # --- Ігрова логіка ---
                elif authenticated:
                    if command == ServerCommands.CREATE_ROOM:
                        current_room_id = await self.create_room(websocket, username)
                    
                    elif command == ServerCommands.JOIN_ROOM:
                        payload['username'] = username
                        joined_id = await self.join_room(websocket, payload)
                        if joined_id:
                            current_room_id = joined_id
                    
                    elif command == ServerCommands.SEND_MESSAGE:
                        if current_room_id and current_room_id in self.rooms:
                            room = self.rooms[current_room_id]
                            msg_text = payload.get("message", "")
                            
                            # === ПРАВКА 1: Використовуємо SEND_MESSAGE ===
                            await room.broadcast({
                                "type": ServerCommands.SEND_MESSAGE,
                                "username": username,
                                "message": msg_text
                            })
                        else:
                            await websocket.send(json.dumps({"type": ServerCommands.ERROR, "message": "Ви не в кімнаті"}))
                
                else:
                    await websocket.send(json.dumps({"type": ServerCommands.ERROR, "message": "Спочатку авторизуйтесь"}))

        except Exception as e:
            # === ПРАВКА 2: Ловимо будь-які помилки з'єднання ===
            print(f"З'єднання з {username or 'анонімом'} розірвано: {e}")
            if current_room_id and current_room_id in self.rooms:
                room = self.rooms[current_room_id]
                if username in room.clients:
                    del room.clients[username]
                    # Сповіщаємо інших про вихід
                    await room.broadcast({
                        "type": ServerCommands.SEND_MESSAGE, 
                        "username": "System", 
                        "message": f"{username} покинув гру."
                    })

    async def create_room(self, websocket, username):
        room_id = str(uuid.uuid4())[:8]
        new_room = Room(room_id, username, self.db)
        new_room.clients[username] = websocket
        self.rooms[room_id] = new_room
        
        await websocket.send(json.dumps({
            "type": ServerCommands.ROOM_CREATED,
            "room_id": room_id
        }))
        print(f"Кімната {room_id} створена гравцем {username}")
        return room_id

    async def join_room(self, websocket, payload):
        room_id = payload.get("room_id")
        username = payload.get("username")

        if room_id in self.rooms:
            room = self.rooms[room_id]
            room.clients[username] = websocket
            
            await websocket.send(json.dumps({"type": ServerCommands.JOIN_ROOM, "message": f"Ви приєднались до {room_id}"}))
            
            # Використовуємо SEND_MESSAGE для сповіщення
            await room.broadcast({
                "type": ServerCommands.SEND_MESSAGE, 
                "username": "System",
                "message": f"{username} приєднався до гри!"
            })
            return room_id
        else:
            await websocket.send(json.dumps({"type": ServerCommands.ERROR, "message": "Кімнату не знайдено"}))
            return None