# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

from gettext import gettext as _

from gi.repository import Gtk

from sugar3.graphics.toolbutton import ToolButton
from sugar3.speech import SpeechManager


class SpeechToolbar(Gtk.Toolbar):

    def __init__(self, activity):
        Gtk.Toolbar.__init__(self)
        self._activity = activity
        self._speech = SpeechManager()

        self._speech.connect('play', self._play_cb)
        self._speech.connect('stop', self._stop_cb)
        self._speech.connect('pause', self._pause_cb)

        def make_button(icon, callback, tip):
            button = ToolButton(icon)
            button.show()
            button.connect('clicked', callback)
            self.insert(button, -1)
            button.set_tooltip(tip)
            return button

        self._play_button = make_button(
            'media-playback-start', self._play_clicked_cb, _('Play'))

        self._pause_button = make_button(
            'media-playback-pause', self._pause_clicked_cb, _('Pause'))

        self._stop_button = make_button(
            'media-playback-stop', self._stop_clicked_cb, _('Stop'))

        self._stop_cb(None)

    def _play_cb(self, speech):
        self._play_button.set_sensitive(False)
        self._pause_button.set_sensitive(True)
        self._stop_button.set_sensitive(True)

    def _pause_cb(self, speech):
        self._play_button.set_sensitive(True)
        self._pause_button.set_sensitive(False)
        self._stop_button.set_sensitive(True)

    def _stop_cb(self, speech):
        self._play_button.set_sensitive(True)
        self._pause_button.set_sensitive(False)
        self._stop_button.set_sensitive(False)

    def _play_clicked_cb(self, widget):
        if not self._speech.get_is_paused():
            abi = self._activity.abiword_canvas
            text = abi.get_content("text/plain", None)
            self._speech.say_text(text[0])
        else:
            self._speech.restart()

    def _pause_clicked_cb(self, widget):
        self._speech.pause()

    def _stop_clicked_cb(self, widget):
        self._speech.stop()
