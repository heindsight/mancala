from typing import NamedTuple

from hypothesis import assume, given
from hypothesis import strategies as st

from mancala import variants
from mancala.events import Captured, Event, ExtraTurn, GameOver, SeedSown, SeedStored
from mancala.match import Match
from mancala.rules import Move, MoveResult, Rules
from mancala.state import GameState, Player

_VARIANTS = ("kalah", "oware")
_MAX_PLIES = 2_000

type Position = tuple[tuple[tuple[int, ...], tuple[int, ...]], tuple[int, int]]


class Playout(NamedTuple):
    match: Match
    total: int


class PlayedMove(NamedTuple):
    rules: Rules
    state: GameState
    move: Move
    result: MoveResult
    seen: frozenset[GameState]
    """The states seen up to and including `state` — what Match passes as history."""


@st.composite
def playouts(draw: st.DrawFn, names: tuple[str, ...] = _VARIANTS) -> Playout:
    name = draw(st.sampled_from(names))
    seeds = draw(st.integers(min_value=3, max_value=6)) if name == "kalah" else 4
    rules = variants.get(name)
    match = Match(rules, rules.initial_state(seeds))
    while not match.is_over and len(match.history) < _MAX_PLIES:
        match.play(draw(st.sampled_from(rules.legal_moves(match.state))))
    return Playout(match, total=2 * 6 * seeds)


def _moves_of(match: Match) -> list[PlayedMove]:
    states = [state for state, _, _ in match.history] + [match.state]
    return [
        PlayedMove(
            match.rules,
            state,
            move,
            MoveResult(after, events),
            frozenset(states[: index + 1]),
        )
        for index, ((state, move, events), after) in enumerate(
            zip(match.history, states[1:], strict=True)
        )
    ]


@st.composite
def played_moves(draw: st.DrawFn, names: tuple[str, ...] = _VARIANTS) -> PlayedMove:
    """A position reached in a random game, paired with any legal move from it.

    Sampling the move independently of the playout covers the legal moves the
    game did not take; those results are built with the same history a Match
    diverging at that point would supply.
    """
    played = draw(st.sampled_from(_moves_of(draw(playouts(names)).match)))
    move = draw(st.sampled_from(played.rules.legal_moves(played.state)))
    if move == played.move:
        return played
    result = played.rules.apply_move(played.state, move, played.seen)
    return played._replace(move=move, result=result)


@st.composite
def game_events[E: Event](
    draw: st.DrawFn, event_type: type[E], names: tuple[str, ...] = _VARIANTS
) -> tuple[PlayedMove, E]:
    moves = _moves_of(draw(playouts(names)).match)
    occurrences = [
        (move, event)
        for move in moves
        for event in move.result.events
        if isinstance(event, event_type)
    ]
    assume(occurrences)
    return draw(st.sampled_from(occurrences))


def total_seeds(state: GameState) -> int:
    return sum(state.stores) + sum(sum(row) for row in state.board)


def smallest_cup(state: GameState) -> int:
    return min(min(row) for row in state.board)


def events_of_type[E: Event](
    events: tuple[Event, ...], event_type: type[E]
) -> tuple[E, ...]:
    return tuple(event for event in events if isinstance(event, event_type))


def replay(state: GameState, move: Move, events: tuple[Event, ...]) -> Position:
    """Rebuild the post-move board and stores from the emitted events alone."""
    board = [list(row) for row in state.board]
    stores = list(state.stores)
    board[state.current_player.value][move] = 0
    for event in events:
        match event:
            case SeedSown(player=player, cup=cup):
                board[player.value][cup] += 1
            case SeedStored(player=player):
                stores[player.value] += 1
            case Captured(by=by, owner=owner, cup=cup, seeds=seeds):
                stores[by.value] += seeds
                board[owner.value][cup] = 0
    return (tuple(board[0]), tuple(board[1])), (stores[0], stores[1])


def replayed_positions(match: Match) -> list[Position]:
    return [
        replay(played.state, played.move, played.result.events)
        for played in _moves_of(match)
    ]


def actual_positions(match: Match) -> list[Position]:
    return [
        (played.result.state.board, played.result.state.stores)
        for played in _moves_of(match)
    ]


@given(played=played_moves())
def test_a_move_conserves_the_seed_total(played: PlayedMove) -> None:
    assert total_seeds(played.result.state) == total_seeds(played.state)


@given(played=played_moves())
def test_a_move_never_leaves_a_negative_seed_count(played: PlayedMove) -> None:
    assert smallest_cup(played.result.state) >= 0
    assert min(played.result.state.stores) >= 0


@given(played=played_moves())
def test_apply_move_is_deterministic(played: PlayedMove) -> None:
    first = played.rules.apply_move(played.state, played.move)
    second = played.rules.apply_move(played.state, played.move)
    assert first == second


@given(played=played_moves())
def test_replaying_a_move_with_its_history_reproduces_the_result(
    played: PlayedMove,
) -> None:
    replayed = played.rules.apply_move(played.state, played.move, played.seen)
    assert replayed == played.result


@given(playout=playouts())
def test_the_events_alone_rebuild_every_position(playout: Playout) -> None:
    assert replayed_positions(playout.match) == actual_positions(playout.match)


@given(played=played_moves())
def test_a_move_emits_game_over_exactly_when_it_ends_the_game(
    played: PlayedMove,
) -> None:
    game_overs = events_of_type(played.result.events, GameOver)
    assert len(game_overs) <= 1
    assert bool(game_overs) == played.rules.is_over(played.result.state)


@given(played=played_moves())
def test_the_turn_passes_unless_an_extra_turn_is_granted(played: PlayedMove) -> None:
    assume(not events_of_type(played.result.events, ExtraTurn))
    assert played.result.state.current_player is played.state.current_player.opponent


@given(played=played_moves())
def test_a_move_grants_at_most_one_extra_turn(played: PlayedMove) -> None:
    assert len(events_of_type(played.result.events, ExtraTurn)) <= 1


@given(pick=game_events(SeedSown))
def test_every_seed_is_sown_into_a_real_cup(pick: tuple[PlayedMove, SeedSown]) -> None:
    _, sown = pick
    assert sown.cup in range(6)


@given(pick=game_events(Captured))
def test_a_capture_takes_at_least_one_seed(pick: tuple[PlayedMove, Captured]) -> None:
    _, captured = pick
    assert captured.seeds > 0


@given(pick=game_events(Captured))
def test_a_capture_empties_a_real_cup(pick: tuple[PlayedMove, Captured]) -> None:
    _, captured = pick
    assert captured.cup in range(6)


@given(pick=game_events(Captured))
def test_a_capture_credits_the_mover_or_sweeps_seeds_home(
    pick: tuple[PlayedMove, Captured],
) -> None:
    played, captured = pick
    assert captured.by in (played.state.current_player, captured.owner)


@given(pick=game_events(GameOver))
def test_game_over_is_always_the_final_event(
    pick: tuple[PlayedMove, GameOver],
) -> None:
    played, over = pick
    assert played.result.events[-1] is over


@given(pick=game_events(GameOver))
def test_the_game_over_event_names_the_winner(
    pick: tuple[PlayedMove, GameOver],
) -> None:
    played, over = pick
    assert over.winner is played.rules.winner(played.result.state)


@given(pick=game_events(GameOver))
def test_a_game_ending_move_grants_no_extra_turn(
    pick: tuple[PlayedMove, GameOver],
) -> None:
    played, _ = pick
    assert events_of_type(played.result.events, ExtraTurn) == ()


@given(pick=game_events(SeedStored, names=("kalah",)))
def test_kalah_stores_seeds_only_for_the_mover(
    pick: tuple[PlayedMove, SeedStored],
) -> None:
    played, stored = pick
    assert stored.player is played.state.current_player


@given(pick=game_events(ExtraTurn, names=("kalah",)))
def test_a_kalah_extra_turn_belongs_to_the_mover(
    pick: tuple[PlayedMove, ExtraTurn],
) -> None:
    played, extra = pick
    assert extra.player is played.state.current_player


@given(pick=game_events(ExtraTurn, names=("kalah",)))
def test_a_kalah_extra_turn_keeps_the_mover_on_turn(
    pick: tuple[PlayedMove, ExtraTurn],
) -> None:
    played, _ = pick
    assert played.result.state.current_player is played.state.current_player


@given(played=played_moves(names=("oware",)))
def test_oware_never_stores_seeds_while_sowing(played: PlayedMove) -> None:
    assert events_of_type(played.result.events, SeedStored) == ()


@given(played=played_moves(names=("oware",)))
def test_oware_never_grants_an_extra_turn(played: PlayedMove) -> None:
    assert events_of_type(played.result.events, ExtraTurn) == ()


@given(playout=playouts())
def test_a_random_game_terminates(playout: Playout) -> None:
    assert playout.match.is_over


@given(playout=playouts())
def test_a_finished_game_ends_with_an_empty_board(playout: Playout) -> None:
    assert playout.match.state.board == ((0,) * 6, (0,) * 6)


@given(playout=playouts())
def test_a_finished_game_banks_every_seed(playout: Playout) -> None:
    assert sum(playout.match.state.stores) == playout.total


@given(playout=playouts())
def test_a_finished_game_offers_no_further_moves(playout: Playout) -> None:
    assert playout.match.rules.legal_moves(playout.match.state) == ()


@given(playout=playouts())
def test_the_winner_is_the_player_with_the_fuller_store(playout: Playout) -> None:
    south, north = playout.match.state.stores
    outcomes = {
        Player.SOUTH: south > north,
        Player.NORTH: north > south,
        None: south == north,
    }
    assert outcomes[playout.match.winner]
