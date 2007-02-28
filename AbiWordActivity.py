import logging
import os
import time
import gtk
import hippo
from abiword import Canvas
from toolbar import AbiToolbar
from sugar.activity import activity

class AbiWordActivity (activity.Activity):

	def __init__ (self, handle):
		activity.Activity.__init__ (self, handle)
		self.set_title ("Write")

		hippoCanvasBox = hippo.CanvasBox()
		self.set_root(hippoCanvasBox)

		# create our main abiword canvas
		self.abiword_canvas = Canvas()

		# create and add a toolbar for our window, which listens to our canvas
		abiToolbar = AbiToolbar(hippoCanvasBox, self.abiword_canvas)

		# create a hippo container to embed our canvas in
		abiwordCanvasContainer = hippo.CanvasWidget()
		abiwordCanvasContainer.props.widget = self.abiword_canvas

		# add the controls to our window
		hippoCanvasBox.append(abiwordCanvasContainer, hippo.PACK_EXPAND)

		# show the abiword canvas and have it open a blank file
		self.abiword_canvas.load_file("")
		self.abiword_canvas.show()

	def execute(self, command, args):
		if(command == 'open_document'):
			self.abiword_canvas.load_file('file://' + args[0])
			
			return True
		else:
			return False
