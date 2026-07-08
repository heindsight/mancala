#!/usr/bin/env python
import mancala_gtk
from games import *

class Mancala(object):
	def __init__(self, game_type, nstones=None, p1="Player 1", p2="Player 2"):
		object.__init__(self)
		if nstones is None:
			self.game = mgame.games[game_type]()
		else:
			self.game = mgame.games[game_type](nstones)
		self.board = mancala_gtk.mancala_gtk([p1, p2], self.game)

	def play(self):
		self.board.playgame()

if __name__ == "__main__":
	mancala = Mancala(mgame.games.keys()[0],4)
	mancala.play()
# parse cmd line args
# instantiate mancala
# call play
