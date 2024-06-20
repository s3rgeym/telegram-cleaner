from __future__ import annotations

import asyncio
import logging
from dataclasses import KW_ONLY, dataclass, field
from pathlib import Path
from typing import Any, Iterator

from pyrogram import (
    Client,
    enums,
    errors,
    raw,
    types,
)


@dataclass
class Cleaner:
    api_id: int | str
    api_hash: str
    _: KW_ONLY
    keep_chats: list[str | int] = field(default_factory=list)
    confirm_all: bool = False
    logger: logging.Logger = logging.root

    def __post_init__(self) -> None:
        self.client = Client(
            __package__,
            api_id=self.api_id,
            api_hash=self.api_hash,
            workdir=str(Path.cwd()),
            # app_version=self.app_version,
            # device_model=self.device_model,
            # system_version=self.system_version,
        )

    @staticmethod
    def iter_chunks(data: list, chunksize: int = 100) -> Iterator[list]:
        for i in range(0, len(data), chunksize):
            yield data[i : i + chunksize]

    @staticmethod
    def confirm(s: str) -> bool:
        return input(f"{s}? (y/N): ").lower().strip().startswith("y")

    async def delete_contacts(self) -> None:
        if not self.confirm_all and not self.confirm("Delete contacts"):
            self.logger.info("Canceled")
            return
        try:
            contacts = await self.client.get_contacts()
            await self.client.delete_contacts([x.id for x in contacts])
            self.logger.info("Contacts deleted successfully!")
        except Exception as ex:
            self.logger.exception(ex)

    async def get_chats(self) -> list[types.Chat]:
        rv = []
        dialog: types.Dialog
        async for dialog in self.client.get_dialogs():
            rv.append(dialog.chat)
        return rv

    async def get_private_chats(
        self,
    ) -> list[types.Chat]:
        return [
            chat
            for chat in await self.get_chats()
            if chat.type in [enums.ChatType.PRIVATE, enums.ChatType.BOT]
        ]

    def keep_chat(self, chat: types.Chat) -> bool:
        return (
            chat.id in self.keep_chats
            # govnofix для cli
            or str(chat.id) in self.keep_chats
            # Попытка очистить ответы приводит к убийству ВСЕХ СЕССИЙ
            or getattr(chat, "username", None) in [*self.keep_chats, "replies"]
            # Аккаунт поддержки имеет ID#777000, удаление диалога с ним выглядит как взлом
            or getattr(chat, "is_support", False)
        )

    async def delete_private_chats(self) -> None:
        if not self.confirm_all and not self.confirm("Delete private chats"):
            self.logger.warning("Canceled")
            return
        try:
            for chat in await self.get_private_chats():
                if self.keep_chat(chat):
                    continue
                self.logger.debug(
                    "delete private chat: %d (%s)",
                    chat.id,
                    chat.first_name,
                )
                # https://stackoverflow.com/a/72766038
                peer = await self.client.resolve_peer(chat.id)
                self.logger.debug(peer)
                await self.client.invoke(
                    raw.functions.messages.DeleteHistory(
                        peer=peer,
                        max_id=0,
                        revoke=True,
                    )
                )
            self.logger.info("private chats deleted successfully!")
        except Exception as ex:
            self.logger.exception(ex)

    async def clear_private_chats(self) -> None:
        if not self.confirm_all and not self.confirm("Clear private chats"):
            self.logger.warning("Canceled")
            return
        try:
            for chat in await self.get_private_chats():
                if self.keep_chat(chat):
                    continue
                self.logger.debug(
                    "clear private chat: %d (%s)",
                    chat.id,
                    chat.first_name,
                )
                message_ids = []
                async for message in self.client.get_chat_history(
                    chat_id=chat.id
                ):
                    message_ids.append(message.id)
                for chunk in self.iter_chunks(message_ids):
                    await self.client.delete_messages(
                        chat_id=chat.id, message_ids=chunk, revoke=True
                    )
            self.logger.info("private chats cleared successfully!")
        except Exception as ex:
            self.logger.exception(ex)

    async def get_group_chats(
        self,
    ) -> list[types.Chat]:
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
        self.logger.debug(
            "Search own messages group#%s",
            chat_id,
        )
        message_ids = []
        message: types.Message
        async for message in self.client.search_messages(
            chat_id=chat_id,
            from_user="me",
        ):
            message_ids.append(message.id)
        if message_ids:
            for chunk in self.iter_chunks(message_ids):
                self.logger.debug(
                    f"Delete message sequence: {', '.join(map(str, chunk))}"
                )
                await self.client.delete_messages(
                    chat_id=chat_id,
                    message_ids=chunk,
                    revoke=True,
                )
            self.logger.info(
                "Total deleted messages %s: %d",
                chat_id,
                len(message_ids),
            )

    async def get_linked_chat(self, chat: types.Chat) -> types.Chat | None:
        if chat.type != enums.ChatType.CHANNEL:
            return None
        chat_info = await self.client.get_chat(chat_id=chat.id)
        return getattr(chat_info, "linked_chat", None)

    async def get_reply_chats(self):
        raise NotImplementedError

    async def delete_group_messages(self) -> None:
        # TODO: очищать чаты, где есть ответы см get_reply_chats
        if not self.confirm_all and not self.confirm("Delete group messages"):
            self.logger.warning("Canceled")
            return
        try:
            chats = await self.get_group_chats()
            seen = set()
            while chats:
                chat = chats.pop()
                if self.keep_chat(chat):
                    continue
                self.logger.debug("%s - %s", chat.id, chat.title)
                # Избегаем повторное удаление сообщений в группах с комментариями
                if chat.id in seen:
                    self.logger.debug(
                        "already seen: %s",
                        chat.id,
                    )
                    continue
                seen.add(chat.id)
                try:
                    # Каналы имеют группы с комментариями к постам. В них вступать необязательно, а значит в списке чатов они не видны
                    if linked_chat := await self.get_linked_chat(chat):
                        # self.logger.debug(linked_chat)
                        chats.append(linked_chat)
                        # Flood control
                        await asyncio.sleep(2.0)
                    # if chat.permissions and chat.permissions.can_send_messages:
                    await self.delete_own_messages(chat.id)
                    # else:
                    #     self.logger.debug(
                    #         "you dont have permission to send messages in grooup#%s",
                    #         chat.id,
                    #     )
                except errors.ChannelPrivate as ex:
                    self.logger.warning(ex)
            self.logger.info("Group messages deleted successfully!")
        except Exception as ex:
            self.logger.exception(ex)

    async def leave_groups(self) -> None:
        if not self.confirm_all and not self.confirm("Leave groups"):
            self.logger.warning("Canceled")
            return
        try:
            chats = await self.get_group_chats()
            for chat in chats:
                if self.keep_chat(chat):
                    continue
                self.logger.debug(f"Leave group #{chat.id}")
                await self.client.leave_chat(chat.id)
            self.logger.info("Groups leaved successfully!")
        except Exception as ex:
            self.logger.error(ex)

    async def clean(self) -> None:
        await self.delete_contacts()
        await self.delete_group_messages()
        await self.delete_private_chats()
        await self.leave_groups()

    async def dump_chats(self) -> None:
        try:
            chats = await self.get_chats()
            print(
                "[" + ",".join(map(str, chats)) + "]",
                flush=True,
            )
        except Exception as ex:
            self.logger.exception(ex)

    async def dump_me(self) -> None:
        try:
            print(await self.client.get_me())
        except Exception as ex:
            self.logger.exception(ex)

    async def logout(self) -> None:
        try:
            print(await self.client.log_out())
        except Exception as ex:
            self.logger.exception(ex)

    async def __aenter__(self) -> Cleaner:
        await self.client.start()
        return self

    async def __aexit__(self, *args: Any, **kwargs: Any) -> None:
        await self.client.stop()
