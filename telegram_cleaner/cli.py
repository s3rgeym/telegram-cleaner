import argparse
import logging
from os import getenv
from typing import Sequence

from .cleaner import Cleaner
from .utils import make_sync


class NameSpace(argparse.Namespace):
    yes_all: bool
    verbosity: int
    command: str


def parse_args(argv: Sequence[str] | None) -> NameSpace:
    parser = argparse.ArgumentParser()
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
        "delete_private_chats": "delete private chat messages",
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
    logging.basicConfig()
    args = parse_args(argv)
    log_lvl = max(logging.DEBUG, logging.WARNING - args.verbosity * 10)
    async with Cleaner(
        api_id=int(getenv("TG_API_ID", 24439609)),
        api_hash=getenv("TG_API_HASH", "425c5e04e10edd2913e971b64a82186d"),
        confirm_all=args.yes,
        log_level=log_lvl,
    ) as cleaner:
        await getattr(cleaner, args.command)()
