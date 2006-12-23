import logging
import os
import time
import gtk
from abiword import Canvas
from toolbar import Toolbar
from sugar.activity.Activity import Activity

class AbiWordActivity (Activity):

	def __init__ (self):
		Activity.__init__ (self)
		self.set_title ("AbiWord")

		vbox = gtk.VBox(False, 0)
		self.add(vbox)
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
