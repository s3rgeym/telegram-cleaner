from __future__ import annotations

import asyncio
import logging
from dataclasses import KW_ONLY, dataclass
from os import getenv
from typing import Any, Iterator

from pyrogram import Client, enums, errors, raw, types


@dataclass
class Cleaner:
    _: KW_ONLY
    # За использование данных от приложения Телеграма меня забанили
    # https://qna.habr.com/q/1185562
    client_name: str = "cleaner"
    api_id: str = getenv("TG_API_ID", 24439609)
    api_hash: str = getenv("TG_API_HASH", "425c5e04e10edd2913e971b64a82186d")
    # app_version: str = ""
    # device_model: str = ""
    # system_version: str = ""
    confirm_all: bool = False
    log_level: int | str = logging.DEBUG

    def __post_init__(self) -> None:
        self.setup_logger()
        self.client = Client(
            self.client_name,
            api_id=self.api_id,
            api_hash=self.api_hash,
            # app_version=self.app_version,
            # device_model=self.device_model,
            # system_version=self.system_version,
        )

    def setup_logger(self) -> Cleaner:
        self.log = logging.getLogger(__name__)
        self.log.setLevel(self.log_level)
        return self

    @staticmethod
    def iter_chunks(data: list, chunksize: int = 100) -> Iterator[list]:
        for i in range(0, len(data), chunksize):
            yield data[i : i + chunksize]

    @staticmethod
    def confirm(s: str) -> bool:
        return input(f"{s}? (y/N): ").lower().strip().startswith("y")

    async def delete_contacts(self) -> None:
        if not self.confirm_all and not self.confirm("Delete contacts"):
            self.log.info("Canceled")
            return
        try:
            contacts = await self.client.get_contacts()
            await self.client.delete_contacts([x.id for x in contacts])
            self.log.info("Contacts deleted successfully!")
        except Exception as e:
            self.log.exception(e)

    async def get_chats(self) -> list[types.Chat]:
        rv = []
        dialog: types.Dialog
        async for dialog in self.client.get_dialogs():
            rv.append(dialog.chat)
        return rv

    async def delete_private_chats(self) -> None:
        if not self.confirm_all and not self.confirm("Delete private chats"):
            self.log.warn("Canceled")
            return
        try:
            chats = await self.get_chats()
            for chat in chats:
                if chat.type not in [
                    enums.ChatType.PRIVATE,
                    enums.ChatType.BOT,
                ]:
                    continue
                self.log.debug(
                    "delete private chat: %d (%s)",
                    chat.id,
                    chat.first_name,
                )
                # TODO: нужно ли на всякий случай удалить сообщения?
                # message_ids = []
                # async for message in self.client.get_chat_history(
                #     chat_id=chat.id
                # ):
                #     message_ids.append(message.id)
                # for chunk in self.iter_chunks(message_ids):
                #     await self.client.delete_messages(
                #         chat_id=chat.id, message_ids=chunk, revoke=True
                #     )
                # https://stackoverflow.com/a/72766038
                peer = await self.client.resolve_peer(chat.id)
                self.log.debug(peer)
                await self.client.invoke(
                    raw.functions.messages.DeleteHistory(
                        peer=peer, max_id=0, revoke=True
                    )
                )
            self.log.info("private chats deleted successfully!")
        except Exception as e:
            self.log.exception(e)

    async def get_group_chats(self) -> list[types.Chat]:
        return [
            chat
            for chat in await self.get_chats()
            if chat.type
            in [
                enums.ChatType.GROUP,
                enums.ChatType.SUPERGROUP,
                enums.ChatType.CHANNEL,
            ]
        ]

    async def delete_own_messages(self, chat_id: int | str) -> None:
        self.log.debug("Search own messages group#%s", chat_id)
        message_ids = []
        message: types.Message
        async for message in self.client.search_messages(
            chat_id=chat_id,
            from_user="me",
        ):
            message_ids.append(message.id)
        if message_ids:
            for chunk in self.iter_chunks(message_ids):
                self.log.debug(
                    f"Delete message sequence: {', '.join(map(str, chunk))}"
                )
                await self.client.delete_messages(
                    chat_id=chat_id, message_ids=chunk, revoke=True
                )
            self.log.info(
                "Total deleted messages %s: %d", chat_id, len(message_ids)
            )

    async def delete_group_messages(self) -> None:
        if not self.confirm_all and not self.confirm("Delete group messages"):
            self.log.warn("Canceled")
            return
        try:
            chats = await self.get_group_chats()
            seen = set()
            while chats:
                chat = chats.pop()
                self.log.debug("%s - %s", chat.id, chat.title)
                # Избегаем повторное удаление сообщений в группах с комментариями
                if chat.id in seen:
                    self.log.debug("already seen: %s", chat.id)
                    continue
                seen.add(chat.id)
                try:
                    # Каналы имеют группы с комментариями к постам. В них вступать необязательно, а значит в списке чатов они не видны
                    if chat.type == enums.ChatType.CHANNEL:
                        # linked_chat (Chat (https://docs.pyrogram.org/api/types/Chat#pyrogram.types.Chat), optional) – The linked discussion group (in case of channels) or the linked channel (in case of supergroups). Returned only in get_chat() (https://docs.pyrogram.org/api/methods/get_chat.html#pyrogram.Client.get_chat).only in get_chat() (https://docs.pyrogram.org/api/methods/get_chat.html#pyrogram.Client.get_chat).
                        chat_info = await self.client.get_chat(chat_id=chat.id)
                        if linked_chat := getattr(chat_info, "linked_chat"):
                            # self.log.debug(linked_chat)
                            chats.append(linked_chat)
                        # Flood control
                        await asyncio.sleep(2.0)
                    # {
                    #     "_": "Chat",
                    #     "id": -1001XXXXXXXXX,
                    #     ...
                    #     "permissions": {
                    #         "_": "ChatPermissions",
                    #         "can_send_messages": true,
                    #         "can_send_media_messages": false,
                    #         "can_send_other_messages": false,
                    #         "can_send_polls": true,
                    #         "can_add_web_page_previews": false,
                    #         "can_change_info": false,
                    #         "can_invite_users": false,
                    #         "can_pin_messages": false
                    #     }
                    #     ...
                    # }
                    # if chat.permissions and chat.permissions.can_send_messages:
                    await self.delete_own_messages(chat.id)
                    # else:
                    #     self.log.debug(
                    #         "you dont have permission to send messages in grooup#%s",
                    #         chat.id,
                    #     )
                except errors.ChannelPrivate as e:
                    self.log.warn(e)
            self.log.info("Group messages deleted successfully!")
        except Exception as e:
            self.log.exception(e)

    async def leave_groups(self) -> bool:
        if not self.confirm_all and not self.confirm("Leave groups"):
            self.log.warn("Canceled")
            return
        try:
            chats = await self.get_group_chats()
            for chat in chats:
                self.log.debug(f"Leave group #{chat.id}")
                await self.client.leave_chat(chat.id)
            self.log.info("Groups leaved successfully!")
        except Exception as e:
            self.log.error(e)

    async def run_all(self) -> None:
        await self.delete_contacts()
        await self.delete_group_messages()
        await self.delete_private_chats()
        await self.leave_groups()

    async def print_chats(self) -> None:
        try:
            chats = await self.get_chats()
            for chat in chats:
                print(chat)
        except Exception as e:
            self.log.exception(e)

    async def print_me(self) -> None:
        try:
            print(await self.client.get_me())
        except Exception as e:
            self.log.exception(e)

    async def __aenter__(self) -> Cleaner:
        await self.client.start()
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.client.stop()
