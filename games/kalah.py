import mgame

class game(mgame.game):
	def __init__(self, pcup=3):
		global games
		mgame.game.__init__(self, pcup, 6)

	def move(self, start):
		if self.cups[self.turn][start] == 0:
			return
		inhand = self.cups[self.turn][start]
		self.cups[self.turn][start] = 0
		i = start
		p = self.turn
		while inhand > 0:
			i = (i + 1) % self.ncups
			if (i == 0):
				if (p == self.turn):
					inhand -= 1
					self.stores[p] += 1
					yield
					if inhand == 0:
						self.remain = map(sum, self.cups)
						return
				p = (p + 1) % 2
			inhand -= 1
			self.cups[p][i] += 1
			yield
		if (p == self.turn) and (self.cups[p][i] == 1)\
				and (self.cups[(p + 1) % 2][self.ncups-1-i] > 0):
			self.stores[p] += self.cups[p][i]
			self.cups[p][i] = 0
			self.stores[p] += self.cups[(p + 1) % 2][self.ncups-1-i]
			self.cups[(p + 1) % 2][self.ncups-1-i] = 0
			yield
		self.remain = map(sum, self.cups)
		self.turn = (self.turn + 1) % 2
		return

	def valid_moves(player, cups, remain):
		return True
	
	def game_over(self):
		return (0 in self.remain) or mgame.game.game_over(self)

mgame.games["kalah"] = game
