import sys
import os
import base64 # Для кодування

from utils.SettingsLoader import SettingsLoader

class GameSettings:
    DEFAULTS = {
        "login": "",
        "password_blob": "", # Змінили назву, щоб не плутати з чистим паролем
        "auto_login": False,
        "volume": 100,
        "server_ip": "127.0.0.1", # Добавимо налаштування сервера
        "server_port": 8765
    }

    def __init__(self):
        self.loader = SettingsLoader("player_config")
        self._ensure_defaults()

    def _ensure_defaults(self):
        updated = False
        for key, default_val in self.DEFAULTS.items():
            if key not in self.loader.settings:
                self.loader.settings[key] = default_val
                updated = True
        if updated:
            self.loader.save_data()

    # --- МЕТОДИ ШИФРУВАННЯ (ОБФУСКАЦІЇ) ---
    def _encode(self, text):
        if not text: return ""
        # Простий трюк: перевертаємо рядок + кодуємо в base64
        # Це не захистить від хакера, але захистить від "цікавого сусіда"
        try:
            sample_string_bytes = text.encode("utf-8")
            base64_bytes = base64.b64encode(sample_string_bytes)
            return base64_bytes.decode("utf-8")
        except:
            return ""

    def _decode(self, text):
        if not text: return ""
        try:
            base64_bytes = text.encode("utf-8")
            sample_string_bytes = base64.b64decode(base64_bytes)
            return sample_string_bytes.decode("utf-8")
        except:
            return ""

    # --- ВЛАСТИВОСТІ ---

    @property
    def login(self):
        return self.loader.settings.get("login", "")

    @login.setter
    def login(self, value):
        self.loader.settings["login"] = value
        self.loader.save_data()

    @property
    def password(self):
        # При отриманні - декодуємо
        blob = self.loader.settings.get("password_blob", "")
        return self._decode(blob)

    @password.setter
    def password(self, value):
        # При записі - кодуємо
        encoded = self._encode(value)
        self.loader.settings["password_blob"] = encoded
        self.loader.save_data()

    @property
    def server_ip(self):
        return self.loader.settings.get("server_ip", "127.0.0.1")
    
    @property
    def server_port(self):
        return self.loader.settings.get("server_port", 9090)

# Глобальний об'єкт
game_settings = GameSettings()