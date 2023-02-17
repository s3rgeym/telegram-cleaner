import argparse
import asyncio
import logging
from typing import Sequence

from .cleaner import Cleaner


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
    parser.set_defaults(command="run_all")

    additional_commands = {
        "delete_contacts": "delete contacts",
        "delete_group_messages": "delete group messages",
        "leave_groups": "leave groups",
        "delete_private_chats": "delete private chats",
        "print_chats": "print chats information",
        "print_me": "print loggined user",
    }

    subp = parser.add_subparsers(help="commands")

    for k, v in additional_commands.items():
        p = subp.add_parser(k, help=v)
        p.set_defaults(command=k)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    logging.basicConfig()
    args = parse_args(argv)
    lvl = max(logging.DEBUG, logging.WARNING - args.verbosity * 10)

    async def run() -> None:
        async with Cleaner(confirm_all=args.yes, log_level=lvl) as cleaner:
            await getattr(cleaner, args.command)()

    asyncio.run(run())
