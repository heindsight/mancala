"""Terminal interface for hot-seat mancala."""

import argparse
import sys
from typing import Protocol, TextIO

from mancala import strategies, variants
from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.match import Match
from mancala.rules import IllegalMoveError, Move
from mancala.state import GameState, Player
from mancala.strategies import Strategy


class TerminalPlayer(Protocol):
    """One side of a match played at the terminal."""

    name: str

    def get_move(self, match: Match) -> Move | None:
        """The move to play next; None to abandon the game."""


class HumanPlayer:
    """Prompts at the terminal for a cup to sow."""

    def __init__(self, name: str, stdin: TextIO, stdout: TextIO) -> None:
        self.name = name
        self._stdin = stdin
        self._stdout = stdout

    def get_move(self, match: Match) -> Move | None:
        del match  # the human reads the position off the board on screen
        return read_move(self.name, self._stdin, self._stdout)


class ComputerPlayer:
    """Picks a move with a strategy and announces it."""

    def __init__(self, name: str, strategy: Strategy, stdout: TextIO) -> None:
        self.name = name
        self._strategy = strategy
        self._stdout = stdout

    def get_move(self, match: Match) -> Move:
        move = self._strategy.choose(match)
        print(f"{self.name} chooses cup {move + 1}.", file=self._stdout)
        return move


CPU_PREFIX = "cpu:"


def build_player(spec: str, stdin: TextIO, stdout: TextIO) -> TerminalPlayer:
    """A computer for a `cpu:<difficulty>` spec, otherwise a human named `spec`."""
    if spec.startswith(CPU_PREFIX):
        difficulty = spec.removeprefix(CPU_PREFIX)
        return ComputerPlayer(
            f"Computer ({difficulty})", strategies.get(difficulty), stdout
        )
    return HumanPlayer(spec, stdin, stdout)


def main(
    argv: list[str] | None = None,
    *,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
) -> int:
    parser = argparse.ArgumentParser(prog="mancala", description="Hot-seat mancala.")
    parser.add_argument("--variant", choices=variants.available(), default="kalah")
    parser.add_argument(
        "--seeds", type=int, default=4, help="seeds per cup (kalah: 3-6)"
    )
    parser.add_argument(
        "player1", nargs="?", default="Player 1", help="name, or cpu:<difficulty>"
    )
    parser.add_argument(
        "player2", nargs="?", default="Player 2", help="name, or cpu:<difficulty>"
    )
    args = parser.parse_args(argv)

    rules = variants.get(args.variant)
    stdin = stdin if stdin is not None else sys.stdin
    stdout = stdout if stdout is not None else sys.stdout
    try:
        match = Match(rules, rules.initial_state(args.seeds))
        south = build_player(args.player1, stdin, stdout)
        north = build_player(args.player2, stdin, stdout)
    except ValueError as error:
        parser.error(str(error))
    return play_match(match, (south, north), stdout)


def play_match(
    match: Match, players: tuple[TerminalPlayer, TerminalPlayer], stdout: TextIO
) -> int:
    """Run the interactive loop: 0 when the game is played out, 1 when abandoned.

    `players` is indexed by `Player.value`, so south moves first.
    """
    names = {side: players[side.value].name for side in Player}
    while not match.is_over:
        print(file=stdout)
        print(render_board(match.state, names), file=stdout)
        mover = match.state.current_player
        move = players[mover.value].get_move(match)
        if move is None:
            print(file=stdout)
            print("Game abandoned.", file=stdout)
            return 1
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


def read_move(name: str, stdin: TextIO, stdout: TextIO) -> Move | None:
    """Prompt until `name` picks a cup between 1 and 6; None means the player quit."""
    while True:
        print(f"{name}, choose a cup (1-6): ", end="", file=stdout, flush=True)
        try:
            line = stdin.readline()
        except KeyboardInterrupt:
            return None
        if not line:
            return None
        text = line.strip()
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
