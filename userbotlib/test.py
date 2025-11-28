import asyncio
from client import TdClient
import dotenv

# here i try to test my lib to understand how convenient is my lib
async def main():
    config = dotenv.dotenv_values(".env")
    api_id = config["API_ID"]
    api_hash = config["API_HASH"]

    client = TdClient(api_id, api_hash)

    await client.start()     # start receiver thread
    await client.login()     # do authentication

    print("Now you can start receiving updates!")

    # example listener:
    while True:
        update = await client.update_queue.get()
        print(update)


if __name__ == "__main__":
    asyncio.run(main())
