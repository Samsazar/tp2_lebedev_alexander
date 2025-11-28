import asyncio
from bot import Bot
import dotenv

async def main():
    config = dotenv.dotenv_values(".env")
    api_id = config["API_ID"]
    api_hash = config["API_HASH"]

    bot = Bot(api_id, api_hash)

    @bot.on_message()
    async def echo(bot_instance, message):
        print("GET MESSAGE:", message)

    await bot.start_polling()
    # await bot.stop()

asyncio.run(main())
