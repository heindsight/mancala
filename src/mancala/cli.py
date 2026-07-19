"""Terminal interface for hot-seat mancala."""

import argparse
import sys
from dataclasses import dataclass
from typing import TextIO

from mancala import save, variants
from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.match import Match
from mancala.rules import IllegalMoveError, Move
from mancala.state import GameState, Player


@dataclass(frozen=True, slots=True)
class SaveGame:
    """The player asked to save the game to `file` instead of moving."""

    file: str


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="mancala", description="Hot-seat mancala.")
    parser.add_argument("--variant", choices=variants.available())
    parser.add_argument(
        "--seeds", type=int, help="seeds per cup (kalah: 3-6, default 4)"
    )
    parser.add_argument("--load", metavar="FILE", help="resume a saved game")
    parser.add_argument("player1", nargs="?", help="Player 1 name")
    parser.add_argument("player2", nargs="?", help="Player 2 name")
    args = parser.parse_args(argv)

    if args.load is not None:
        if (args.variant, args.seeds, args.player1, args.player2) != (None,) * 4:
            parser.error(
                "--load cannot be combined with --variant, --seeds, or player names"
            )
        try:
            match, names = save.load(args.load)
        except (OSError, save.SaveError) as error:
            parser.error(str(error))
    else:
        rules = variants.get(args.variant if args.variant is not None else "kalah")
        seeds = args.seeds if args.seeds is not None else 4
        try:
            match = Match(rules, rules.initial_state(seeds))
        except ValueError as error:
            parser.error(str(error))
        names = {
            Player.SOUTH: args.player1 if args.player1 is not None else "Player 1",
            Player.NORTH: args.player2 if args.player2 is not None else "Player 2",
        }
    return play_match(
        match,
        names,
        stdin if stdin is not None else sys.stdin,
        stdout if stdout is not None else sys.stdout,
    )


def play_match(
    match: Match, names: dict[Player, str], stdin: TextIO, stdout: TextIO
) -> int:
    """Run the interactive loop: 0 when the game is played out, 1 when abandoned."""
    while not match.is_over:
        print(file=stdout)
        print(render_board(match.state, names), file=stdout)
        mover = match.state.current_player
        move = read_move(names[mover], stdin, stdout)
        if move is None:
            print(file=stdout)
            print("Game abandoned.", file=stdout)
            return 1
        if isinstance(move, SaveGame):
            try:
                save.dump(match, names, move.file)
            except (OSError, save.SaveError) as error:
                print(f"Could not save: {error}.", file=stdout)
                continue
            print(f"Game saved to {move.file}.", file=stdout)
            return 0
        try:
            result = match.play(move)
        except IllegalMoveError as error:
            print(f"{str(error).capitalize()}.", file=stdout)
            continue
        print("\n".join(describe_move(mover, move, result.events, names)), file=stdout)
    print(file=stdout)
    print(render_board(match.state, names), file=stdout)
    print(describe_result(match.state, match.winner, names), file=stdout)
    return 0


def read_move(name: str, stdin: TextIO, stdout: TextIO) -> Move | SaveGame | None:
    """Prompt until `name` picks a cup between 1 and 6 or asks to save the game.

    None means the player quit.
    """
    while True:
        print(
            f"{name}, choose a cup (1-6) or 'save FILE': ",
            end="",
            file=stdout,
            flush=True,
        )
        try:
            line = stdin.readline()
        except KeyboardInterrupt:
            return None
        if not line:
            return None
        text = line.strip()
        command, _, argument = text.partition(" ")
        if command == "save":
            if file := argument.strip():
                return SaveGame(file)
            print("Say where to save the game: 'save FILE'.", file=stdout)
            continue
        try:
            cup = int(text)
        except ValueError:
            print(f"{text!r} is not a number between 1 and 6.", file=stdout)
            continue
        if 1 <= cup <= variants.CUPS:
            return cup - 1
        print(f"{cup} is not a number between 1 and 6.", file=stdout)


def describe_move(
    mover: Player, move: Move, events: tuple[Event, ...], names: dict[Player, str]
) -> list[str]:
    sown = sum(isinstance(e, SeedSown | SeedStored) for e in events)
    lines = [f"{names[mover]} sows {_seeds(sown)} from cup {move + 1}."]
    for event in events:
        match event:
            case Captured(by=by, owner=owner, cup=cup, seeds=seeds) if by is not owner:
                lines.append(
                    f"{names[by]} captures {_seeds(seeds)} "
                    f"from {names[owner]}'s cup {cup + 1}."
                )
            case Captured(by=by, cup=cup, seeds=seeds):
                lines.append(
                    f"{names[by]} collects {_seeds(seeds)} from cup {cup + 1}."
                )
            case ExtraTurn(player=player):
                lines.append(f"{names[player]} gets an extra turn!")
            case GameOver():
                lines.append("The game is over.")
    return lines


def _seeds(n: int) -> str:
    return f"{n} seed" if n == 1 else f"{n} seeds"


def render_board(state: GameState, names: dict[Player, str]) -> str:
    """Current player's cups on the bottom row, sowing left to right."""
    bottom = state.current_player
    top = bottom.opponent
    return "\n".join(
        [
            f"{names[top]} (store: {state.stores[top.value]})",
            _cells([f"({i}) " for i in range(6, 0, -1)]),
            _cells([f"[{n:>2}]" for n in reversed(state.board[top.value])]),
            _cells([f"[{n:>2}]" for n in state.board[bottom.value]]),
            _cells([f"({i}) " for i in range(1, 7)]),
            f"{names[bottom]} (store: {state.stores[bottom.value]})",
        ]
    )


def _cells(values: list[str]) -> str:
    return ("    " + "  ".join(values)).rstrip()


def describe_result(
    state: GameState, winner: Player | None, names: dict[Player, str]
) -> str:
    south, north = state.stores
    if winner is None:
        return f"It's a draw, {south}-{north}."
    return f"{names[winner]} wins {max(south, north)}-{min(south, north)}!"
