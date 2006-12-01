import logging
import os
import time
import gtk
from abiword import Canvas

from sugar.activity.Activity import Activity

from toolbar import Toolbar

class AbiWordActivity (Activity):

	def __init__ (self):
		Activity.__init__ (self)
	
		self.set_title ("AbiWord")

		hbox = gtk.HBox(False, 0)
		self.add(hbox)
		hbox.show()

		abiword_canvas = Canvas()

		toolbar = Toolbar(abiword_canvas)
		hbox.pack_start(toolbar, False)
		toolbar.show()

		hbox.add(abiword_canvas)
		abiword_canvas.set_property("load-file", "")
		abiword_canvas.show()
