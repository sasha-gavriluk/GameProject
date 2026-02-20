import asyncio
import websockets
import json
import aioconsole
import sys
from server.api import ServerCommands

class GameClient:
    def __init__(self, uri="wss://carts.to"):
        self.uri = uri
        self.websocket = None
        self.username = None
        self.is_authenticated = False

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            print("✅ Підключено до сервера.")
            
            # Спершу проходимо етап авторизації
            await self.auth_menu()
            
            # Якщо авторизація успішна, запускаємо основні цикли
            if self.is_authenticated:
                await asyncio.gather(
                    self.receive_loop(),
                    self.input_loop()
                )
        except Exception as e:
            print(f"❌ Помилка підключення: {e}")

    async def auth_menu(self):
        while not self.is_authenticated:
            print("\n--- МЕНЮ АВТОРИЗАЦІЇ ---")
            print("1. Увійти (Login)")
            print("2. Реєстрація (Register)")
            print("3. Вийти")
            
            choice = await aioconsole.ainput("> ")
            
            if choice == "3":
                sys.exit()
            
            username = await aioconsole.ainput("Нікнейм: ")
            password = await aioconsole.ainput("Пароль: ")

            if choice == "1":
                await self.send(ServerCommands.LOGIN, {"username": username, "password": password})
            elif choice == "2":
                await self.send(ServerCommands.REGISTER, {"username": username, "password": password})
            
            # Чекаємо відповідь від сервера щодо авторизації
            response = await self.websocket.recv()
            await self.handle_auth_response(json.loads(response))

    async def handle_auth_response(self, data):
        msg_type = data.get("type")
        message = data.get("message", "")

        if msg_type == ServerCommands.AUTH_SUCCESS:
            self.username = data.get("username")
            self.is_authenticated = True
            print(f"\n✅ Успішний вхід! Вітаємо, {self.username}.")
            await self.room_menu()
        elif msg_type == ServerCommands.REGISTRATION_SUCCESS:
            print(f"\n🎉 {message}. Тепер ви можете увійти.")
        elif msg_type in [ServerCommands.AUTH_ERROR, ServerCommands.ERROR]:
            print(f"\n❌ Помилка: {message}")

    async def room_menu(self):
        print("\n--- ГОЛОВНЕ МЕНЮ ---")
        print("1. Створити нову кімнату")
        print("2. Приєднатися за ключем")
        
        choice = await aioconsole.ainput("> ")
        if choice == "1":
            await self.send(ServerCommands.CREATE_ROOM, {})
        else:
            room_id = await aioconsole.ainput("Введіть ключ кімнати: ")
            await self.send(ServerCommands.JOIN_ROOM, {"room_id": room_id})

    async def send(self, command, payload):
        message = json.dumps({"command": command, "payload": payload})
        await self.websocket.send(message)

    async def receive_loop(self):
        """Обробка всіх вхідних повідомлень від сервера під час гри"""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == ServerCommands.ROOM_CREATED:
                    print(f"\n🔑 Кімната створена! КЛЮЧ: {data['room_id']}")
                elif msg_type == ServerCommands.SEND_MESSAGE:
                    print(f"\n[ЧАТ]: {data['text']}")
                elif msg_type == ServerCommands.AUTH_SUCCESS and "message" in data:
                    print(f"\n[СИСТЕМА]: {data['message']}")
                elif msg_type == ServerCommands.ERROR:
                    print(f"\n❌ Помилка сервера: {data['message']}")
        except websockets.exceptions.ConnectionClosed:
            print("\n🔌 З'єднання з сервером розірвано.")

    async def input_loop(self):
        """Обробка вводу повідомлень або ігрових команд"""
        while True:
            text = await aioconsole.ainput("")
            if text.lower() == "/exit":
                break
            # Поки що просто відправляємо як чат-повідомлення
            await self.send(ServerCommands.SEND_MESSAGE, {"text": text})

if __name__ == "__main__":
    client = GameClient()
    asyncio.run(client.connect())