from server.client import GameClient
import asyncio

if __name__ == "__main__":
    client = GameClient()
    asyncio.run(client.connect())