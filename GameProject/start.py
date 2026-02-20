from server.scode import GameServer
import asyncio

def main():
    # Створюємо об'єкт сервера. Слухаємо всі інтерфейси для локальної мережі.
    server = GameServer(host="0.0.0.0")
    try:
        # Запускаємо асинхронну подію
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n🛑 Сервер зупинено вручну.")

if __name__ == "__main__":
    main()
