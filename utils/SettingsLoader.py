import json
import os
from kivy.utils import platform
from kivy.app import App

class SettingsLoader:
    def __init__(self, module_name):
        self.module_name = module_name
        self._base_dir = None  # Внутрішня змінна для кешування шляху
        # Завантажуємо дані. Якщо App ще не готовий, повернеться пустий словник, 
        # але програма не впаде.
        self.settings = self.load_data()

    @property
    def base_dir(self):
        """
        Повертає шлях до папки налаштувань.
        Реалізує 'Lazy Loading': визначає шлях тільки в момент звернення.
        """
        # 1. Якщо ми вже знайшли і запам'ятали правильний шлях - повертаємо його
        if self._base_dir:
            return self._base_dir

        # 2. Логіка для Android
        if platform == 'android':
            app = App.get_running_app()
            if app:
                # Якщо додаток вже запущено, ми можемо безпечно отримати user_data_dir
                data_dir = app.user_data_dir
                self._base_dir = os.path.join(data_dir, 'Settings')
                self.ensure_directory_exists(self._base_dir)
                return self._base_dir
            else:
                # !!! КРИТИЧНИЙ МОМЕНТ !!!
                # Якщо App ще None (це буває при імпорті), ми НЕ зберігаємо результат в _base_dir,
                # а просто повертаємо поточну папку ".".
                # Це дозволяє програмі запуститися без помилок. 
                # Наступного разу, коли ми викличемо base_dir, App вже буде існувати.
                print("[SettingsLoader] Waiting for App initialization...")
                return "." 
        
        # 3. Логіка для ПК (Windows/Linux)
        else:
            # На ПК шлях стабільний, обчислюємо відносно файлу скрипта
            self._base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'Settings'))
            self.ensure_directory_exists(self._base_dir)
            return self._base_dir

    @property
    def settings_file(self):
        """Динамічно формує повний шлях до файлу налаштувань"""
        return os.path.join(self.base_dir, f"{self.module_name}.json")

    def ensure_directory_exists(self, directory):
        """Створює папку, якщо її немає (і це не коренева папка)"""
        if directory and directory != "." and not os.path.exists(directory):
            try:
                os.makedirs(directory)
            except OSError as e:
                print(f"[SettingsLoader] Error creating directory {directory}: {e}")

    def load_data(self):
        """Безпечне завантаження даних"""
        path = self.settings_file
        
        if not os.path.exists(path):
            # Якщо ми на Android і App ще не готовий (path == "./config.json"),
            # ми не намагаємось створити файл, щоб не отримати помилку прав доступу.
            if platform == 'android' and self.base_dir == ".":
                return {}
            
            # В інших випадках створюємо пустий файл
            try:
                with open(path, 'w', encoding="utf-8") as file:
                    json.dump({}, file)
            except Exception as e:
                print(f"[SettingsLoader] Failed to create settings file at {path}: {e}")
                return {}
            return {}

        try:
            with open(path, 'r', encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            print(f"[SettingsLoader] Failed to load settings: {e}")
            return {}

    def save_data(self):
        """Безпечне збереження даних"""
        # Якщо App ще не ініціалізовано на Android, пропускаємо збереження,
        # щоб не писати в системний корінь.
        if platform == 'android' and self.base_dir == ".":
            print("[SettingsLoader] Skipping save: App not initialized.")
            return

        path = self.settings_file
        try:
            with open(path, 'w', encoding="utf-8") as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            print(f"[SettingsLoader] Failed to save settings to {path}: {e}")

    def reload(self):
        """
        Цей метод варто викликати після старту App (наприклад, в on_start),
        щоб перечитати налаштування з правильної папки Android.
        """
        self._base_dir = None # Скидаємо кеш шляху
        self.settings = self.load_data()

    # --- Стандартні методи для роботи зі словником налаштувань ---

    def get_nested_setting(self, keys, default=None):
        value = self.settings
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def update_nested_setting(self, keys, value):
        d = self.settings
        try:
            for key in keys[:-1]:
                d = d.setdefault(key, {})
            d[keys[-1]] = value
            self.save_data()
        except Exception as e:
            print(f"Error updating nested setting: {e}")

    def add_settings_to_class(self, class_name, key_name, new_settings):
        if class_name not in self.settings:
            self.settings[class_name] = {}
        if key_name not in self.settings[class_name]:
            if isinstance(new_settings, dict):
                self.settings[class_name][key_name] = {}
            elif isinstance(new_settings, list):
                self.settings[class_name][key_name] = []

        existing_settings = self.settings[class_name][key_name]

        if isinstance(new_settings, dict):
            for new_key, new_value in new_settings.items():
                if new_key not in existing_settings or existing_settings[new_key] != new_value:
                    existing_settings[new_key] = new_value
        elif isinstance(new_settings, list):
            for item in new_settings:
                if item not in existing_settings:
                    existing_settings.append(item)
        
        self.save_data()

    def get_settings_from_class(self, class_name, key_name):
        if class_name in self.settings and key_name in self.settings[class_name]:
            return self.settings[class_name][key_name]
        return None
        
    def delete_nested_setting(self, keys):
        d = self.settings
        try:
            for key in keys[:-1]:
                d = d[key]
            if keys[-1] in d:
                del d[keys[-1]]
                self.save_data()
        except (KeyError, TypeError) as e:
            print(f"Error deleting setting: {e}")