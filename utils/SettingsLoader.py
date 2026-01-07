import json
import os

class SettingsLoader:
    def __init__(self, module_name):
        """
        Ініціалізація класу налаштувань для конкретного модуля.

        :param module_name: Назва модуля, для якого створюється файл налаштувань.
        """
        self.module_name = module_name
        self.base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data', 'Settings'))
        self.ensure_directory_exists(self.base_dir)
        self.settings_file = os.path.join(self.base_dir, f"{module_name}.json")

        # Завантажуємо або створюємо файл налаштувань
        self.settings = self.load_data()

    def load_data(self):
        """
        Завантажує дані з файлу налаштувань або створює новий файл, якщо його немає.

        :return: Дані з файлу у вигляді словника.
        """
        if not os.path.exists(self.settings_file):
            print(f"Файл {self.settings_file} не знайдено. Створюється новий файл.")
            with open(self.settings_file, 'w', encoding="utf-8") as file:
                json.dump({}, file)  # Створюємо порожній файл JSON
            return {}

        try:
            with open(self.settings_file, 'r', encoding="utf-8") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Помилка завантаження даних: {e}")
            return {}
        
    def reload(self):
        self.settings = self.load_data()

    def save_data(self):
        """
        Зберігає поточні дані в файл налаштувань.
        """
        try:
            with open(self.settings_file, 'w') as file:
                json.dump(self.settings, file, indent=4)
        except Exception as e:
            print(f"Помилка збереження даних: {e}")

    def get_nested_setting(self, keys, default=None):
        """
        Отримує значення налаштувань з багаторівневої структури за допомогою списку ключів.

        :param keys: Список ключів, які вказують на вкладену структуру.
        :param default: Значення за замовчуванням, якщо ключі не знайдено.
        :return: Значення налаштувань або значення за замовчуванням.
        """
        value = self.settings
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default

    def update_nested_setting(self, keys, value):
        """
        Оновлює значення у багаторівневих налаштуваннях за допомогою списку ключів.

        :param keys: Список ключів для оновлення.
        :param value: Нове значення.
        """
        d = self.settings
        try:
            for key in keys[:-1]:
                d = d.setdefault(key, {})
            d[keys[-1]] = value
            self.save_data()
        except Exception as e:
            print(f"Помилка оновлення налаштувань: {e}")

    def add_settings_to_class(self, class_name, key_name, new_settings):
        """
        Додає або оновлює налаштування для вказаного класу з вказаною назвою ключа.

        :param class_name: Назва класу, до якого додаються налаштування.
        :param key_name: Назва ключа, під яким будуть додані нові налаштування.
        :param new_settings: Нові налаштування у вигляді словника або списку.
        """
        if class_name not in self.settings:
            self.settings[class_name] = {}  # Створюємо пустий словник для класу, якщо його ще немає

        if key_name not in self.settings[class_name]:
            # Створюємо пустий словник або список для ключа, якщо його ще немає
            if isinstance(new_settings, dict):
                self.settings[class_name][key_name] = {}
            elif isinstance(new_settings, list):
                self.settings[class_name][key_name] = []

        existing_settings = self.settings[class_name][key_name]

        # Якщо нові налаштування є словником
        if isinstance(new_settings, dict):
            for new_key, new_value in new_settings.items():
                if new_key in existing_settings:
                    if existing_settings[new_key] != new_value:
                        print(f"Оновлюємо параметри для {new_key}.")
                        existing_settings[new_key] = new_value
                else:
                    print(f"Додаємо новий індикатор/паттерн {new_key}.")
                    existing_settings[new_key] = new_value

        # Якщо нові налаштування є списком
        elif isinstance(new_settings, list):
            for item in new_settings:
                if item not in existing_settings:
                    existing_settings.append(item)
                else:
                    print(f"Елемент {item} вже існує в списку.")

        # Зберігаємо оновлені налаштування
        self.save_data()

    def get_settings_from_class(self, class_name, key_name):
        """
        Отримує налаштування для вказаного класу та ключа.

        :param class_name: Назва класу, з якого витягуються налаштування.
        :param key_name: Назва ключа, під яким зберігаються налаштування.
        :return: Налаштування у вигляді словника або списку, або None, якщо не знайдено.
        """
        if class_name in self.settings and key_name in self.settings[class_name]:
            return self.settings[class_name][key_name]
        else:
            print(f"Налаштування для {class_name} або {key_name} не знайдено.")
            return None
        
    def delete_nested_setting(self, keys):
        """
        Видаляє ключ у багаторівневих налаштуваннях за списком ключів.
        :param keys: список ключів (для вкладеності)
        """
        d = self.settings
        try:
            for key in keys[:-1]:
                d = d[key]
            if keys[-1] in d:
                del d[keys[-1]]
                self.save_data()
                print(f"Ключ {'.'.join(keys)} видалено.")
            else:
                print(f"Ключ {'.'.join(keys)} не знайдено для видалення.")
        except (KeyError, TypeError) as e:
            print(f"Помилка при видаленні {'.'.join(keys)}: {e}")

    def ensure_directory_exists(self, directory):
        if not os.path.exists(directory):
            os.makedirs(directory)