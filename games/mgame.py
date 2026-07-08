games = {}

class game(object):
	def __init__(self, pcup, ncups):
		object.__init__(self)
		self.ncups = ncups
		self.pcup = pcup
		self.cups = [[self.pcup] * self.ncups, [self.pcup] * self.ncups]
		self.remain = [self.pcup * self.ncups] * 2
		self.stores = [0]*2
		self.turn = 0

	def move(self, start):
		pass

	def valid_moves(player, cups, remain):
		pass

	def game_over(self):
		return True in [s > self.pcup * self.ncups for s in self.stores]

	def finish_game(self):
		self.cups = [[0] * self.ncups, [0] * self.ncups]
		for i in [0,1]:
			self.stores[i] += self.remain[i]
			self.remain[i] = 0

	def winner(self):
		if self.stores[0] == self.stores[1]:
			return -1
		else:
			return max([0,1], key = lambda p:self.stores[p])
