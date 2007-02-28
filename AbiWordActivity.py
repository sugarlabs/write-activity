import logging
import os
import time
import gtk
import hippo
from abiword import Canvas
from toolbar import Toolbar
from sugar.activity import activity

class AbiWordActivity (hippo.CanvasBox):

	def __init__ (self, handle):
		activity.Activity.__init__ (self, handle)
		self.set_title ("Write")

		vbox = gtk.VBox(False, 0)
		vbox_item = hippo.CanvasWidget(widget=vbox)
		self.set_root(vbox_item)
		vbox.show()

		# create the main abiword canvas
		self.abiword_canvas = Canvas()

		# add a toolbar to our window, which listens to our canvas
		toolbar = Toolbar(self.abiword_canvas)
		vbox.pack_start(toolbar, False)
		toolbar.show()

		# add the canvas to the window, and have it open a blank file
		self.abiword_canvas.load_file("")
		self.abiword_canvas.show()
		vbox.add(self.abiword_canvas)

	def execute(self, command, args):
		if(command == 'open_document'):
			self.abiword_canvas.load_file('file://' + args[0])
			
			return True
		else:
			return False
