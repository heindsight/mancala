import mgame

class game(mgame.game):
	def __init__(self, pcup=3):
		global games
		mgame.game.__init__(self, pcup, 6)

	def can_capture(self, victim, i):
		first = max(filter(lambda j:self.cups[victim][j] not in [2,3], range(i+1))+[-1])
		return self.remain[victim] > sum(self.cups[victim][j] for j in range(first+1,i+1))

	def move(self, start):
		if (self.remain[(self.turn + 1) % 2] == 0) and (self.cups[self.turn][start] + start < 6):
			return
		elif self.cups[self.turn][start] == 0:
			return
		inhand = self.cups[self.turn][start]
		self.cups[self.turn][start] = 0
		i = start
		p = self.turn
		while inhand > 0:
			i = (i + 1) % self.ncups
			if i == 0:
				p = (p + 1) % 2
			if (i == start) and (p == self.turn):
				continue
			inhand -= 1
			self.cups[p][i] += 1
			yield
		self.remain = map(sum, self.cups)
		if (p != self.turn) and self.can_capture(p, i):
			while (i >= 0) and (self.cups[p][i] in [2,3]):
				self.remain[p] -= self.cups[p][i]
				self.stores[self.turn] += self.cups[p][i]
				self.cups[p][i] = 0
				i -= 1
				yield
		self.turn = (self.turn + 1) % 2
		return

	def valid_moves(self):
		if self.remain[(self.turn + 1) % 2] == 0:
			reach = [(self.cups[self.turn][i] + i >= self.ncups) for i in range(self.ncups)]
			return True in reach
		else:
			return True

	def game_over(self):
		return mgame.game.game_over(self) or not self.valid_moves()

mgame.games["oware"] = game
