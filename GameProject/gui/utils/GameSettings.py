import sys
import os
import base64 # Для кодування

from jnius import autoclass

from utils.SettingsLoader import SettingsLoader
from kivy.core.window import Window
from kivy.utils import platform

class GameSettings:
    DEFAULTS = {
        "login": "",
        "password_blob": "", # Змінили назву, щоб не плутати з чистим паролем
        "auto_login": False,
        "volume": 100,
        "server_ip": "carts.to", # Добавимо налаштування сервера
        "server_port": 8765,
        "orientation": "portrait",
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
        return self.loader.settings.get("server_ip", "carts.to")
    
    @server_ip.setter
    def server_ip(self, value):
        self.loader.settings["server_ip"] = value
        self.loader.save_data()
    
    @property
    def server_port(self):
        return self.loader.settings.get("server_port", 9090)

    @server_port.setter
    def server_port(self, value):
        self.loader.settings["server_port"] = value
        self.loader.save_data()

    @property
    def orientation(self):
        return self.loader.settings.get("orientation", "landscape")

    @orientation.setter
    def orientation(self, value):
        self.loader.settings["orientation"] = value
        self.loader.save_data()

    def apply_orientation(self):
        if self.orientation == "portrait":
            Window.rotation = 0
        elif self.orientation == "landscape":
            Window.rotation = 90
        else:
            Window.rotation = 0
        self._apply_android_orientation()

    def _apply_android_orientation(self):
        if platform != "android":
            return
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            ActivityInfo = autoclass("android.content.pm.ActivityInfo")
            activity = PythonActivity.mActivity
            if self.orientation == "portrait":
                activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_PORTRAIT)
            elif self.orientation == "landscape":
                activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE)
            else:
                activity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR)
        except Exception:
            # На випадок відсутності jnius або проблем з Android API
            return

    def reload(self):
        self.loader.reload()
        self._ensure_defaults()

# Глобальний об'єкт
game_settings = GameSettings()
