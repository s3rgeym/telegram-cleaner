import argparse
import logging
from os import getenv
from typing import Sequence

from .cleaner import Cleaner
from .utils import make_sync
from .color_handler import AnsiColorHandler


class NameSpace(argparse.Namespace):
    keep_chats: list[str | int]
    yes: bool
    verbosity: int
    command: str


def normalize_identifier(s: str) -> str | int:
    try:
        return int(s)
    except ValueError:
        return (s := s.strip())[s.startswith("@") :]


def parse_identifiers(v: str) -> list[str | int]:
    return list(map(normalize_identifier, v.split(",")))


def parse_args(argv: Sequence[str] | None) -> NameSpace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--keep-chats",
        help="keep chats with specified identifiers/usernames eg. 1234567890,@foobar",
        type=parse_identifiers,
        default=[],
    )
    parser.add_argument(
        "-y",
        "--yes",
        help="confirm all",
        action=argparse.BooleanOptionalAction,
    )
    parser.add_argument(
        "-v",
        "--verbosity",
        help="increase verbosity",
        action="count",
        default=0,
    )
    parser.set_defaults(command="clean")

    command_methods = {
        "delete_contacts": "delete contacts",
        "delete_group_messages": "delete any type messages in groups including own posts",
        "leave_groups": "leave groups",
        "delete_private_chats": "delete private chats",
        "clear_private_chats": "clear private chat messages",
        "dump_chats": "dump chats debug info",
        "dump_me": "dump loggined user debug info",
        "logout": "terminate current session",
    }

    subparsers = parser.add_subparsers(help="commands")

    for name, description in command_methods.items():
        _parser = subparsers.add_parser(name, help=description)
        _parser.set_defaults(command=name)
    return parser.parse_args(argv)


@make_sync
async def cli(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    log_level = max(logging.DEBUG, logging.WARNING - args.verbosity * 10)
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    handler = AnsiColorHandler()
    # [C] Critical Error Occurred
    handler.setFormatter(logging.Formatter("[%(levelname).1s] %(message)s"))
    logger.addHandler(handler)
    async with Cleaner(
        api_id=int(getenv("TG_API_ID", 24439609)),
        api_hash=getenv("TG_API_HASH", "425c5e04e10edd2913e971b64a82186d"),
        keep_chats=args.keep_chats,
        confirm_all=args.yes,
        logger=logger,
    ) as cleaner:
        await getattr(cleaner, args.command)()
