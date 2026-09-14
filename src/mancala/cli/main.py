"""Entry point for the terminal interface: parses arguments and fills each seat."""

import argparse
import sys
from typing import TextIO

from mancala.cli.play import ComputerPlayer, HumanPlayer, TerminalPlayer, play_match
from mancala.engine import variants
from mancala.engine.match import Match
from mancala.engine.state import Player
from mancala.session import save, strategies

CPU_PREFIX = "cpu:"


def build_player(spec: str, stdin: TextIO, stdout: TextIO) -> TerminalPlayer:
    """A computer for a `cpu:<difficulty>` spec, otherwise a human named `spec`."""
    if spec.startswith(CPU_PREFIX):
        difficulty = spec.removeprefix(CPU_PREFIX)
        return ComputerPlayer(
            f"Computer ({difficulty})", strategies.get(difficulty), stdout, spec
        )
    return HumanPlayer(spec, stdin, stdout)


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="mancala", description="Hot-seat mancala.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    new = subparsers.add_parser("new", help="start a new game")
    new.add_argument(
        "--variant",
        choices=[variant.id for variant in variants.available()],
        default="kalah",
    )
    new.add_argument("--seeds", type=int, help="seeds per cup (kalah: 3-6, default 4)")
    new.add_argument(
        "player1", nargs="?", default="Player 1", help="name, or cpu:<difficulty>"
    )
    new.add_argument(
        "player2", nargs="?", default="Player 2", help="name, or cpu:<difficulty>"
    )
    resume = subparsers.add_parser("resume", help="resume a saved game")
    resume.add_argument("file", help="save file written with 'save FILE'")
    args = parser.parse_args(argv)

    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    if args.command == "resume":
        try:
            variant, match, specs = save.load(args.file)
        except (OSError, save.SaveError) as error:
            resume.error(str(error))
    else:
        variant = variants.get(args.variant)
        options = {} if args.seeds is None else {"seeds_per_cup": args.seeds}
        try:
            match = Match(variant.create(options))
        except ValueError as error:
            new.error(str(error))
        specs = {Player.SOUTH: args.player1, Player.NORTH: args.player2}
    try:
        players = (
            build_player(specs[Player.SOUTH], stdin, stdout),
            build_player(specs[Player.NORTH], stdin, stdout),
        )
    except ValueError as error:
        parser.error(str(error))
    return play_match(variant, match, players, stdout)
