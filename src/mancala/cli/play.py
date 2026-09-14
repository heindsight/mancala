"""The terminal play loop: asks each seat for a move in turn until the game ends."""

from dataclasses import dataclass
from typing import Protocol, TextIO

from mancala.cli.render import describe_move, describe_result, render_board
from mancala.engine.match import Match
from mancala.engine.rules import IllegalMoveError, Move
from mancala.engine.state import Player
from mancala.session import save
from mancala.session.strategies import Strategy


@dataclass(frozen=True, slots=True)
class SaveGame:
    """The player asked to save the game to `file` instead of moving."""

    file: str


class TerminalPlayer(Protocol):
    """One side of a match played at the terminal."""

    name: str
    spec: str

    def get_move(self, match: Match) -> Move | SaveGame | None:
        """The move to play next; None to abandon, SaveGame to save and exit."""


class HumanPlayer:
    """Prompts at the terminal for a cup to sow."""

    def __init__(self, name: str, stdin: TextIO, stdout: TextIO) -> None:
        self.name = name
        self.spec = name
        self._stdin = stdin
        self._stdout = stdout

    def get_move(self, match: Match) -> Move | SaveGame | None:
        cups = len(match.state.board[match.state.current_player.value])
        return read_move(self.name, cups, self._stdin, self._stdout)


class ComputerPlayer:
    """Picks a move with a strategy and announces it."""

    def __init__(
        self, name: str, strategy: Strategy, stdout: TextIO, spec: str | None = None
    ) -> None:
        self.name = name
        self.spec = spec if spec is not None else name
        self._strategy = strategy
        self._stdout = stdout

    def get_move(self, match: Match) -> Move:
        move = self._strategy.choose(match)
        print(f"{self.name} chooses cup {move + 1}.", file=self._stdout)
        return move


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
        if isinstance(move, SaveGame):
            specs = {side: players[side.value].spec for side in Player}
            try:
                save.dump(match, specs, move.file)
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


def read_move(
    name: str, cups: int, stdin: TextIO, stdout: TextIO
) -> Move | SaveGame | None:
    """Prompt until `name` picks a cup between 1 and `cups` or asks to save the game.

    None means the player quit.
    """
    while True:
        print(
            f"{name}, choose a cup (1-{cups}) or 'save FILE': ",
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
            print(f"{text!r} is not a number between 1 and {cups}.", file=stdout)
            continue
        if 1 <= cup <= cups:
            return cup - 1
        print(f"{cup} is not a number between 1 and {cups}.", file=stdout)
