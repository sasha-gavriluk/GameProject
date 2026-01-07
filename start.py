from server.scode import GameServer
import asyncio

def main():
    # Створюємо об'єкт сервера. За замовчуванням localhost:8765
    server = GameServer()
    try:
        # Запускаємо асинхронну подію
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n🛑 Сервер зупинено вручну.")

if __name__ == "__main__":
    main()