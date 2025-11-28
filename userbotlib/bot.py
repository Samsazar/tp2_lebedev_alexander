import asyncio
from collections.abc import Callable
from mailbox import Message
from typing import Optional

from client import TdClient
from service_tools import Singleton

class Bot(metaclass=Singleton):
    def __init__(self, api_id: int | str, api_hash: str):
        self._td_client : TdClient = TdClient(api_id, api_hash)
        self._handlers : list[dict] = []

        self._listener_task : Optional[asyncio.Task] = None

    async def start_polling(self):
        print("Now you can start receiving updates!")

        await self._td_client.start()
        self._listener_task = asyncio.create_task(self._message_listener_loop())
        try:
            await self._listener_task
        except asyncio.CancelledError:
            pass


    async def stop(self):
        """Stop listener"""
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

    async def _message_listener_loop(self):
        while True:
            update = await self._td_client.update_queue.get()
            # print(update)
            if update["@type"] == "updateNewMessage":
                await self._handle_new_message(update["message"])
            # yield update


    def on_message(self, from_user: int | None = None, chat_id: int | None = None):
        def decorator(func):
            self._handlers.append({
                "func": func,
                "from_user": from_user,
                "chat_id": chat_id,
            })
            return func
        return decorator


    async def _handle_new_message(self, message):
        sender = message["sender_id"]
        chat = message["chat_id"]

        for handler in self._handlers:
            # Filter checks
            if handler["from_user"] and handler["from_user"] != sender:
                continue

            if handler["chat_id"] and handler["chat_id"] != chat:
                continue

            # Run handler
            await handler["func"](self, message)
