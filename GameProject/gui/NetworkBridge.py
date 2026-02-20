import ssl
import certifi
import asyncio
import json
import websockets
import socket
from gui.utils.GameSettings import game_settings

# Імпортуємо команди з твого серверного API, щоб не писати рядки вручну

from utils.api import ServerCommands

class NetworkBridge:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NetworkBridge, cls).__new__(cls)
            cls._instance.ws = None
            cls._instance.is_auth = False
            cls._instance.listen_task = None # Змінна для зберігання задачі слухача
            cls._instance.on_message_callback = None # Функція, яку ми будемо викликати при нових повідомленнях
        return cls._instance

    async def _ensure_connection(self):
        """Внутрішній метод для перевірки/створення з'єднання"""
        if self.ws is not None:
            return

        host = str(game_settings.server_ip).strip()
        port = game_settings.server_port

        # Розумне формування адреси:
        if host.startswith("ws://") or host.startswith("wss://"):
            uri = host
        elif any(c.isalpha() for c in host) and host != "localhost":
            uri = f"wss://{host}"
        else:
            uri = f"ws://{host}:{port}"

        print(f"[Network] Спроба підключення до {uri}...")

        # Налаштування SSL для Android (wss)
        ssl_context = None
        if uri.startswith("wss://"):
            # Використовуємо сертифікати з certifi
            ssl_context = ssl.create_default_context(cafile=certifi.where())

        # Підключаємось (якщо звичайний ws://, ssl_context буде None)
        self.ws = await websockets.connect(uri, ssl=ssl_context)
        
    async def send_request(self, command, payload_data):
        """Універсальний метод відправки запиту на сервер"""
        try:
            # 1. Гарантуємо підключення
            await self._ensure_connection()

            # 2. Формуємо пакет
            full_package = {
                "command": command,
                "payload": payload_data
            }

            # 3. Відправка
            await self.ws.send(json.dumps(full_package))
            
            # 4. Отримання відповіді
            response = await self.ws.recv()
            data = json.loads(response)
            return True, data

        except (ConnectionRefusedError, OSError):
            self.ws = None # Скидаємо з'єднання
            return False, {"message": "Сервер не доступний (Connection Refused)"}
        except websockets.exceptions.ConnectionClosed:
            print("[Network] З'єднання розірвано. Перепідключення...")
            self.ws = None
            # Можна спробувати рекурсивно викликати один раз
            # return await self.send_request(command, payload_data) 
            return False, {"message": "З'єднання розірвано"}
        except Exception as e:
            print(f"[Network Error] {e}")
            self.ws = None
            return False, {"message": f"Помилка: {str(e)}"}

    async def _send_and_wait(self, command, payload_data, expected_types):
        try:
            await self._ensure_connection()
            full_package = {
                "command": command,
                "payload": payload_data
            }
            await self.ws.send(json.dumps(full_package))
            while True:
                response = await self.ws.recv()
                data = json.loads(response)
                msg_type = data.get("type")
                if msg_type in expected_types:
                    return True, data
                if msg_type == ServerCommands.ERROR:
                    return True, data
                if self.on_message_callback:
                    self.on_message_callback(data)
        except (ConnectionRefusedError, OSError):
            self.ws = None
            return False, {"message": "Сервер не доступний (Connection Refused)"}
        except websockets.exceptions.ConnectionClosed:
            print("[Network] З'єднання розірвано. Перепідключення...")
            self.ws = None
            return False, {"message": "З'єднання розірвано"}
        except Exception as e:
            print(f"[Network Error] {e}")
            self.ws = None
            return False, {"message": f"Помилка: {str(e)}"}

    async def _send_only(self, command, payload_data):
        try:
            await self._ensure_connection()
            full_package = {
                "command": command,
                "payload": payload_data
            }
            await self.ws.send(json.dumps(full_package))
            return True
        except Exception as e:
            print(f"[Network Error] {e}")
            return False

    async def connect_and_login(self):
        login = game_settings.login
        # Отримуємо "чистий" пароль (GameSettings його декодує з файлу)
        password = game_settings.password 

        if not login:
            return False, "Логін не вказано"

        # === DEBUG: ВИВІД ПАРОЛЯ ===
        print(f"DEBUG: Відправляємо логін='{login}', пароль='{password}'")
        # ===========================

        success, data = await self.send_request(
            ServerCommands.LOGIN, 
            {"username": login, "password": password}
        )

        if success and data.get("type") == ServerCommands.AUTH_SUCCESS:
            self.is_auth = True
            return True, data.get("message", "Вхід успішний")
        else:
            self.is_auth = False
            return False, data.get("message", "Помилка входу")

    async def register(self, username, password):
        """Реєстрація нового користувача"""
        print(f"DEBUG: Реєстрація юзера='{username}', пароль='{password}'")
        
        success, data = await self.send_request(
            ServerCommands.REGISTER,
            {"username": username, "password": password}
        )

        if success and data.get("type") == ServerCommands.REGISTRATION_SUCCESS:
            return True, data.get("message", "Реєстрація успішна")
        else:
            return False, data.get("message", "Помилка реєстрації")
        
    async def create_room(self):
        """
        Відправляє запит на створення кімнати.
        Повертає: (Success: bool, RoomID/Error: str)
        """
        # Payload пустий, бо сервер сам генерує ID
        success, data = await self._send_and_wait(
            ServerCommands.CREATE_ROOM,
            {},
            {ServerCommands.ROOM_CREATED}
        )

        if success and data.get("type") == ServerCommands.ROOM_CREATED:
            room_id = data.get("room_id")
            print(f"[Network] Кімната створена: {room_id}")
            return True, room_id
        else:
            return False, data.get("message", "Не вдалося створити кімнату")
        
    async def send_chat(self, message):
        """Відправляє повідомлення в чат поточної кімнати"""
        # Перевірка на пусте повідомлення
        if not message or not message.strip():
            return False

        # Формуємо payload. 
        # room_id сервер знає з контексту з'єднання, або можна передати явно, якщо треба
        payload = {
            "message": message
        }

        # Відправляємо (використовуємо універсальний метод, але нам не обов'язково чекати відповіді)
        # Хоча для надійності можна чекати підтвердження від сервера
        try:
            await self._ensure_connection()
            
            full_package = {
                "command": ServerCommands.SEND_MESSAGE,
                "payload": payload
            }
            
            await self.ws.send(json.dumps(full_package))
            return True
        except Exception as e:
            print(f"[Chat Error] {e}")
            return False
        
    async def join_room(self, room_id):
        """
        Відправляє запит на приєднання до кімнати.
        """
        if not room_id:
            return False, "Введіть ID кімнати"

        print(f"[Network] Спроба приєднання до кімнати: {room_id}")

        success, data = await self._send_and_wait(
            ServerCommands.JOIN_ROOM,
            {"room_id": room_id},
            {ServerCommands.JOIN_ROOM}
        )

        # Сервер має відповісти типом ROOM_JOINED або error
        if success and data.get("type") == ServerCommands.JOIN_ROOM:
            return True, data.get("message", "Успішно приєднано")
        else:
            return False, data.get("message", "Не вдалося знайти кімнату")

    async def request_room_state(self):
        """Запит поточного стану кімнати"""
        return await self._send_only(ServerCommands.GET_ROOM_STATE, {})

    async def update_room_settings(self, settings):
        """Оновлення налаштувань кімнати (тільки власник)"""
        return await self._send_only(ServerCommands.UPDATE_SETTINGS, {"settings": settings})

    async def toggle_ready(self):
        """Перемикає готовність гравця"""
        return await self._send_only(ServerCommands.READY_TOGGLE, {})

    async def send_game_action(self, payload):
        """Відправляє дію гравця на сервер"""
        return await self._send_only(ServerCommands.GAME_ACTION, payload)

    async def find_local_server(self, port=8765, timeout=1.0):
        """Шукає сервер у локальній мережі через UDP discovery. Повертає IP або None."""
        return await asyncio.to_thread(self._udp_discover, port, timeout)

    def _get_local_ip(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        finally:
            sock.close()

    def _udp_discover(self, port, timeout):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(timeout)
            sock.sendto(b"DISCOVER_SERVER", ("255.255.255.255", port))
            data, addr = sock.recvfrom(1024)
            if data.startswith(b"SERVER_HERE"):
                return addr[0]
        except Exception:
            return None
        finally:
            sock.close()

    def start_listener(self, callback):
        """Запускає фоновий процес прослуховування"""
        self.on_message_callback = callback
        if self.listen_task is None:
            self.listen_task = asyncio.create_task(self._listen_loop())
            print("[Network] Слухач запущено.")

    def stop_listener(self):
        """Зупиняє фоновий процес"""
        if self.listen_task:
            self.listen_task.cancel()
            self.listen_task = None
            print("[Network] Слухач зупинено.")
        self.on_message_callback = None

    async def _listen_loop(self):
        """Нескінченний цикл читання повідомлень від сервера"""
        try:
            while True:
                if self.ws:
                    try:
                        # Чекаємо повідомлення
                        message = await self.ws.recv()
                        data = json.loads(message)
                        
                        # Якщо у нас є callback (це метод в GameScreen), передаємо дані туди
                        if self.on_message_callback:
                            self.on_message_callback(data)
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("[Network] З'єднання закрито сервером.")
                        break
                    except Exception as e:
                        print(f"[Listener Error] {e}")
                        # Невелика пауза, щоб не заспамити консоль при помилці
                        await asyncio.sleep(1)
                else:
                    await asyncio.sleep(1) # Чекаємо відновлення з'єднання
        except asyncio.CancelledError:
            print("[Network] Слухач скасовано.")

    def close(self):
        if self.ws:
            asyncio.create_task(self.ws.close())
            self.ws = None

# Глобальний об'єкт
net = NetworkBridge()
