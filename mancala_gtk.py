#!/usr/bin/env python

import pygtk
pygtk.require('2.0')
import gtk
from games import *
import time
import threading

class mancala_gtk(object):
	def update_display(self, inmove=False):
		for i in [0,1]:
			self.stores[i].set_text(str(self.game.stores[i]))
			for j in range(self.game.ncups):
				self.buttons[i][j].set_label(str(self.game.cups[i][j]))
			self.plabels[i].set_text(self.players[i])

		if not inmove:
			if not self.status_msg is None:
				self.statusbar.remove(self.status_data, self.status_msg)
			s = ""
			if not self.game.game_over():
				s =  "%s's turn"%self.players[self.game.turn]
			else:
				w = self.game.winner()
				if w > -1:
					s = "%s won!"%self.players[w]
				else:
					s = "Draw"
			self.status_msg = self.statusbar.push(self.status_data, s)

	def make_move(self, start):
		gtk.gdk.threads_enter()
		for i in [0,1]:
			for j in range(self.game.ncups):
				self.buttons[i][j].set_sensitive(False)
		if not self.status_msg is None:
			self.statusbar.remove(self.status_data, self.status_msg)
		s =  "%s is moving "%self.players[self.game.turn]
		self.status_msg = self.statusbar.push(self.status_data, s)
		gtk.gdk.threads_leave()
		i = 0
		for t in self.game.move(start):
			i += 1
			gtk.gdk.threads_enter()
			self.update_display(True)
			gtk.gdk.threads_leave()
			time.sleep(0.5)
		if self.game.game_over():
			self.game.finish_game()
		gtk.gdk.threads_enter()
		self.update_display()
		for i in [0,1]:
			for j in range(self.game.ncups):
				self.buttons[i][j].set_sensitive(True)
		gtk.gdk.threads_leave()

	def button_clicked(self, widget, data=None):
		if data is None or self.game.game_over():
			return
		if data[0] == self.game.turn:
			self.mover = threading.Thread(target = self.make_move, args=(data[1],))
			self.mover.start()

	def destroy_event(self, widget, data=None):
		if (not self.mover is None) and (self.mover.isAlive()):
			self.mover.join()
			self.mover = None
		gtk.main_quit()

	def delete_event(self, widget, event, data=None):
		if (not self.mover is None) and (self.mover.isAlive()):
			self.mover.join()
			self.mover = None
		return False

	def new_game(self, widget, data=None):
		if (not self.mover is None) and (self.mover.isAlive()):
			self.mover.join()
			self.mover = None
		n = int(self.spinner.get_value())
		m = self.combo.get_model()
		a = self.combo.get_active()
		if a < 0:
			return
		type = m[a][0]
		self.game = mgame.games[type](n)
		self.update_display()

	def __init__(self, players, game):
		object.__init__(self)
		self.players = players
		self.game = game
		self.mover = None
		self.stores = map(gtk.Label, map(str, self.game.stores))
		self.buttons = [None, None]
		self.buttons[0] = map(gtk.Button, map(str, self.game.cups[0]))
		self.buttons[1] = map(gtk.Button, map(str, self.game.cups[1]))
		self.plabels = map(gtk.Label, self.players)
		self.statusbar = gtk.Statusbar()
		self.status_msg = None
		self.status_data = self.statusbar.get_context_id("Mancala")

		# create window
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.window.set_title("Mancala")
#		self.window.set_resizable(False)

		vbox = gtk.VBox(False, 0)
		vbox.show()
		self.window.add(vbox)

		hbox = gtk.HBox(False, 10);
		hbox.show()
		vbox.pack_start(hbox, False, False, 0)
		l = gtk.Label("Game type: ")
		l.show()
		hbox.pack_start(l, False, False, 0)
		self.combo = gtk.combo_box_new_text()
		map(self.combo.append_text, mgame.games.keys())
		self.combo.set_active(0)
		self.combo.show()
		hbox.pack_start(self.combo, False, False, 0)
		l = gtk.Label("Stones per cup: ")
		l.show()
		hbox.pack_start(l, False, False, 0)
		self.spinner = gtk.SpinButton( gtk.Adjustment(4, 3, 6, 1))
		self.spinner.show()
		hbox.pack_start(self.spinner, False, False, 0)
		button = gtk.Button("New Game")
		button.connect("clicked", self.new_game)
		button.show()
		hbox.pack_start(button, False, False, 0)

		hbox = gtk.HBox(False, 0)
		hbox.show()
		vbox.pack_start(hbox, True, True, 0)
		self.statusbar.show()
		vbox.pack_start(self.statusbar, False, False, 0)

		for i in [0,1]:
			self.stores[i].set_justify(gtk.JUSTIFY_CENTER)
			self.stores[i].show()
			self.plabels[i].set_justify(gtk.JUSTIFY_CENTER)
			self.plabels[i].show()

		hbox.pack_start(self.stores[0], True, True, 0)
		vbox = gtk.VBox(False, 0)
		vbox.show()
		hbox.pack_start(vbox, True, True, 0)
		hbox.pack_start(self.stores[1], True, True, 0)

		# p1 label
		vbox.pack_start(self.plabels[0], False, True, 0)

		# buttons
		t = [range(self.game.ncups - 1, -1, -1), range(self.game.ncups)]
		for i in [0,1]:
			bbox = gtk.HButtonBox()
			bbox.set_layout(gtk.BUTTONBOX_CENTER)
			bbox.set_spacing(0)
			for j in t[i]:
				self.buttons[i][j].connect("clicked", self.button_clicked, [i,j])
				bbox.add(self.buttons[i][j])
				self.buttons[i][j].show()
			vbox.pack_start(bbox, True, True, 0)
			bbox.show()

		# p2 label
		vbox.pack_start(self.plabels[1], False, True, 0)

		self.window.connect("delete_event", self.delete_event)
		self.window.connect("destroy", self.destroy_event)
		self.window.show()
		self.update_display()

	def playgame(self):
		gtk.gdk.threads_init()
        	gtk.main()
