# Roadmap

The project is split into sub-projects. Each one gets its own design, plan and
implementation.

## Still wanted

- **Web interface.** A board in the browser. The engine's events drive its
  animation. The first sketch was a FastAPI server with a thin JavaScript
  board. It waits for the engine / session / front-end split ([#4](https://github.com/heindsight/mancala/issues/4)), so that it
  does not have to duplicate what the engine knows.
- **Network play.** Two people playing from different machines: websockets,
  rooms, and a server that holds the authoritative match.
- **Further variants.** More members of the mancala family, such as Congkak
  and Bao.

## Delivered

- **Engine and terminal interface.** Kalah and Oware, playable hot-seat in the
  terminal, with save and resume.
- **Computer players.** Either seat, or both, can be handed to the computer at
  `easy`, `medium` or `hard` difficulty.
