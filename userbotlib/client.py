import json
import os
import sys
import asyncio
from ctypes import CDLL, c_char_p, c_double, c_int
from typing import Any, Dict, Optional


class TdClient:
    def __init__(self, api_id: int = None, api_hash: str = None):
        self.api_id = api_id
        self.api_hash = api_hash

        self._load_library()
        self._setup_functions()

        self.client_id = self._td_create_client_id()

        # Disable logs
        self.execute({
            "@type": "setLogVerbosityLevel",
            "new_verbosity_level": 0
        })

        # Async queue for updates
        self.update_queue: asyncio.Queue = asyncio.Queue()

        # Receiver task placeholder
        self._receiver_task: Optional[asyncio.Task] = None

    def _load_library(self):
        """TDLib loading"""
        tdjson_path = os.path.join(os.path.dirname(__file__), "libtdjson.dylib")

        if not os.path.exists(tdjson_path):
            sys.exit("Cannot find libtdjson.dylib")

        self.tdjson = CDLL(tdjson_path)

    def _setup_functions(self):
        """Turn cpp functions to class methods
        """
        # now i rest restype and argtypes, because of using it in tdlib example
        self._td_create_client_id = self.tdjson.td_create_client_id
        self._td_create_client_id.restype = c_int

        self._td_receive = self.tdjson.td_receive
        self._td_receive.restype = c_char_p
        self._td_receive.argtypes = [c_double]

        self._td_send = self.tdjson.td_send
        self._td_send.restype = None
        self._td_send.argtypes = [c_int, c_char_p]

        self._td_execute = self.tdjson.td_execute
        self._td_execute.restype = c_char_p
        self._td_execute.argtypes = [c_char_p]


    def execute(self, query: Dict[str, Any]):
        """sync execute telegram command
        :param query:
        :return:
        """
        data = json.dumps(query).encode("utf-8")
        result = self._td_execute(data)
        return json.loads(result.decode("utf-8")) if result else None


    async def send(self, query: Dict[str, Any]):
        """async send query to telegram
        :param query:
        :return:
        """
        data = json.dumps(query).encode("utf-8")
        self._td_send(self.client_id, data)

    async def _receiver_loop(self):
        """background receiver. Always update data from telegram"""
        while True:
            result = self._td_receive(1.0)
            if result:
                event = json.loads(result.decode("utf-8"))
                await self.update_queue.put(event)
            await asyncio.sleep(0)
            # change to other coroutines


    async def start(self):
        """Start background receiver"""
        self._receiver_task = asyncio.create_task(self._receiver_loop())

    async def stop(self):
        """Stop background receiver"""
        if self._receiver_task:
            self._receiver_task.cancel()
            try:
                await self._receiver_task
            except asyncio.CancelledError:
                pass


    async def login(self):
        """async login"""
        print("Starting Telegram authentication...")

        await self.send({"@type": "getAuthorizationState"})

        while True:
            event = await self.update_queue.get()

            if event["@type"] != "updateAuthorizationState":
                continue

            state = event["authorization_state"]
            t = state["@type"]

            # TODO: как такое оптимизировать? Много бесполезных функций перегружают класс
            if t == "authorizationStateWaitTdlibParameters":
                await self._auth_parameters()

            elif t == "authorizationStateWaitPhoneNumber":
                await self._auth_phone()

            elif t == "authorizationStateWaitEmailAddress":
                await self._auth_email()

            elif t == "authorizationStateWaitEmailCode":
                await self._auth_email_code()

            elif t == "authorizationStateWaitCode":
                await self._auth_sms_code()

            elif t == "authorizationStateWaitPassword":
                await self._auth_password()

            elif t == "authorizationStateWaitRegistration":
                await self._auth_register()

            elif t == "authorizationStateReady":
                print("Logged in successfully!")
                return

            elif t == "authorizationStateClosed":
                print("Authorization closed")
                return


    async def _auth_parameters(self):
        """parameters of the user bot"""
        print("Setting TDLib parameters...")
        await self.send({
            "@type": "setTdlibParameters",
            "database_directory": "tdlib_data",
            "use_message_database": True,
            "use_secret_chats": True,
            "api_id": self.api_id,
            "api_hash": self.api_hash,
            "system_language_code": "en",
            "device_model": "Python Async Client",
            "application_version": "1.1",
        })

    async def _auth_phone(self):
        phone = input("Enter phone: ")
        await self.send({"@type": "setAuthenticationPhoneNumber", "phone_number": phone})

    async def _auth_sms_code(self):
        code = input("Enter SMS code: ")
        await self.send({"@type": "checkAuthenticationCode", "code": code})

    async def _auth_email(self):
        email = input("Enter email: ")
        await self.send({
            "@type": "setAuthenticationEmailAddress",
            "email_address": email
        })

    async def _auth_email_code(self):
        code = input("Enter email code: ")
        await self.send({
            "@type": "checkAuthenticationEmailCode",
            "code": {"@type": "emailAddressAuthenticationCode", "code": code}
        })

    async def _auth_password(self):
        password = input("Enter cloud password: ")
        await self.send({
            "@type": "checkAuthenticationPassword",
            "password": password
        })

    async def _auth_register(self):
        first = input("First name: ")
        last = input("Last name: ")
        await self.send({
            "@type": "registerUser",
            "first_name": first,
            "last_name": last
        })

