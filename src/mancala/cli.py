"""Terminal interface for hot-seat mancala."""

import argparse
import sys
from typing import TextIO

from mancala import variants
from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.match import Match
from mancala.rules import IllegalMoveError
from mancala.state import GameState, Player


def _cells(values: list[str]) -> str:
    return ("    " + "  ".join(values)).rstrip()


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


def _seeds(n: int) -> str:
    return f"{n} seed" if n == 1 else f"{n} seeds"


def describe_move(
    mover: Player, move: int, events: tuple[Event, ...], names: dict[Player, str]
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


def describe_result(
    state: GameState, winner: Player | None, names: dict[Player, str]
) -> str:
    south, north = state.stores
    if winner is None:
        return f"It's a draw, {south}-{north}."
    return f"{names[winner]} wins {max(south, north)}-{min(south, north)}!"


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout

    parser = argparse.ArgumentParser(prog="mancala", description="Hot-seat mancala.")
    parser.add_argument("--variant", choices=variants.available(), default="kalah")
    parser.add_argument(
        "--seeds", type=int, default=4, help="seeds per cup (kalah: 3-6)"
    )
    parser.add_argument("names", nargs="*", default=[], help="player names (up to two)")
    args = parser.parse_args(argv)
    if len(args.names) > 2:
        parser.error("at most two player names")

    padded = [*args.names, *["Player 1", "Player 2"][len(args.names) :]]
    names = {Player.SOUTH: padded[0], Player.NORTH: padded[1]}
    rules = variants.get(args.variant)
    try:
        match = Match(rules, rules.initial_state(args.seeds))
    except ValueError as error:
        parser.error(str(error))

    def out(text: str = "") -> None:
        stdout.write(text + "\n")

    while not match.is_over:
        out()
        out(render_board(match.state, names))
        mover = match.state.current_player
        stdout.write(f"{names[mover]}, choose a cup (1-6): ")
        stdout.flush()
        line = stdin.readline()
        if not line:
            out()
            out("Game abandoned.")
            return 1
        text = line.strip()
        try:
            cup = int(text)
        except ValueError:
            out(f"{text!r} is not a number between 1 and 6.")
            continue
        if not 1 <= cup <= 6:
            out(f"{cup} is not a number between 1 and 6.")
            continue
        try:
            result = match.play(cup - 1)
        except IllegalMoveError as error:
            out(f"{str(error).capitalize()}.")
            continue
        for message in describe_move(mover, cup - 1, result.events, names):
            out(message)

    out()
    out(render_board(match.state, names))
    out(describe_result(match.state, match.winner, names))
    return 0
