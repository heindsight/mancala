"""Terminal interface for hot-seat mancala."""

from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
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
                    f"{names[by]} captures {_seeds(seeds)} from {names[owner]}'s cup {cup + 1}."
                )
            case Captured(by=by, cup=cup, seeds=seeds):
                lines.append(f"{names[by]} collects {_seeds(seeds)} from cup {cup + 1}.")
            case ExtraTurn(player=player):
                lines.append(f"{names[player]} gets an extra turn!")
            case GameOver():
                lines.append("The game is over.")
    return lines


def describe_result(state: GameState, winner: Player | None, names: dict[Player, str]) -> str:
    south, north = state.stores
    if winner is None:
        return f"It's a draw, {south}-{north}."
    return f"{names[winner]} wins {max(south, north)}-{min(south, north)}!"
