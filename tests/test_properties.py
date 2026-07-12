from hypothesis import given, settings
from hypothesis import strategies as st

from mancala import variants
from mancala.events import Captured, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.match import Match
from mancala.rules import MoveResult
from mancala.state import GameState, Player


@st.composite
def _variant_and_seeds(draw: st.DrawFn) -> tuple[str, int]:
    """A variant with a seed count it actually supports (oware is 4-only)."""
    name = draw(st.sampled_from(["kalah", "oware"]))
    seeds = draw(st.sampled_from([3, 4, 5, 6])) if name == "kalah" else 4
    return name, seeds


def _board_empty(state: GameState) -> bool:
    return not any(state.board[0]) and not any(state.board[1])


def _replay(state: GameState, move: int, events: tuple[object, ...]) -> GameState:
    """Rebuild the post-move board/stores purely from the emitted events.

    If the events faithfully describe the move, replaying them onto the
    pre-move position (with the played cup emptied) reproduces the returned
    board and stores. Missing, extra, or misdirected events break this.
    """
    board = [list(row) for row in state.board]
    stores = list(state.stores)
    board[state.current_player.value][move] = 0  # seeds are picked up
    for event in events:
        match event:
            case SeedSown(player=player, cup=cup):
                board[player.value][cup] += 1
            case SeedStored(player=player):
                stores[player.value] += 1
            case Captured(by=by, owner=owner, cup=cup, seeds=seeds):
                assert board[owner.value][cup] == seeds
                stores[by.value] += seeds
                board[owner.value][cup] = 0
    return GameState(
        board=(tuple(board[0]), tuple(board[1])),
        stores=(stores[0], stores[1]),
        current_player=state.current_player,  # placeholder; caller checks turn
    )


def _check_move(name: str, total: int, state: GameState, move: int, result: MoveResult):
    mover = state.current_player
    new = result.state
    events = result.events

    # Seeds are conserved and never negative.
    assert all(seeds >= 0 for row in new.board for seeds in row)
    assert sum(new.stores) + sum(sum(row) for row in new.board) == total

    # The board and stores are reconstructable from the event stream alone.
    reconstructed = _replay(state, move, events)
    assert new.board == reconstructed.board
    assert new.stores == reconstructed.stores

    game_overs = sum(isinstance(event, GameOver) for event in events)
    extra_turns = sum(isinstance(event, ExtraTurn) for event in events)
    assert game_overs <= 1
    assert extra_turns <= 1
    if game_overs:
        assert isinstance(events[-1], GameOver)  # GameOver is always last
    for event in events:
        if isinstance(event, SeedSown):
            assert 0 <= event.cup < 6
        elif isinstance(event, SeedStored):
            assert name == "kalah"  # oware has no store during sowing
            assert event.player is mover
        elif isinstance(event, Captured):
            assert 0 <= event.cup < 6
            assert event.seeds > 0
            # A real capture (mover takes the opponent) or a self-sweep.
            assert event.by in (event.owner, mover)
        elif isinstance(event, ExtraTurn):
            assert name == "kalah"  # oware never grants extra turns
            assert event.player is mover

    # A GameOver event corresponds exactly to a swept-empty terminal board.
    terminal = _board_empty(new)
    assert (game_overs == 1) == terminal
    if terminal:
        assert extra_turns == 0
        assert new.current_player is mover.opponent
    else:
        assert new.current_player is (mover if extra_turns else mover.opponent)


@settings(deadline=None)
@given(config=_variant_and_seeds(), data=st.data())
def test_random_playout_invariants(config: tuple[str, int], data: st.DataObject):
    name, seeds = config
    rules = variants.get(name)
    match = Match(rules, rules.initial_state(seeds))
    total = 2 * 6 * seeds

    game_over_events = 0
    moves_played = 0
    while not match.is_over:
        moves_played += 1
        assert moves_played < 10_000, "game did not terminate"
        state = match.state
        legal = rules.legal_moves(state)
        assert legal, "a non-terminal state must have legal moves"

        # Every legal move is accepted and satisfies the move invariants, and
        # apply_move is pure (it does not disturb the state it was handed).
        for candidate in legal:
            _check_move(
                name, total, state, candidate, rules.apply_move(state, candidate)
            )
            assert match.state == state

        # apply_move is deterministic.
        move = data.draw(st.sampled_from(legal))
        assert rules.apply_move(state, move) == rules.apply_move(state, move)

        result = match.play(move)  # advances the match, threading real history
        assert match.state == result.state
        _check_move(name, total, state, move, result)
        overs = sum(isinstance(event, GameOver) for event in result.events)
        game_over_events += overs
        assert overs == (1 if match.is_over else 0)

    # The game ended, exactly once, on an empty board with a consistent winner.
    assert game_over_events == 1
    assert match.state.board == ((0,) * 6, (0,) * 6)
    assert sum(match.state.stores) == total
    south, north = match.state.stores
    expected = (
        None if south == north else Player.SOUTH if south > north else Player.NORTH
    )
    assert match.winner is expected
