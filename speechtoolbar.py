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

import os
import json
from gettext import gettext as _
import logging

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.combobox import ComboBox
from sugar3.graphics.toolcombobox import ToolComboBox
from sugar3.speech import SpeechManager


class SpeechToolbar(Gtk.Toolbar):

    def __init__(self, activity):
        GObject.GObject.__init__(self)
        self._activity = activity
        self._voice = None
        self.is_paused = False
        self.load_speech_parameters()
        
        self._speech = SpeechManager()        
        self.all_voices = self._speech.get_all_voices()

        # Play button
        self.play_btn = ToggleToolButton('media-playback-start')
        self.play_btn.show()
        self.play_toggled_handler = self.play_btn.connect(
            'toggled', self.play_cb)
        self.insert(self.play_btn, -1)
        self.play_btn.set_tooltip(_('Play / Pause'))

        # Stop button
        self.stop_btn = ToolButton('media-playback-stop')
        self.stop_btn.show()
        self.stop_btn.connect('clicked', self.stop_cb)
        self.stop_btn.set_sensitive(False)
        self.insert(self.stop_btn, -1)
        self.stop_btn.set_tooltip(_('Stop'))

        default = 0
        self.voice_combo = ComboBox()
        for lang_code, name in self.all_voices.items():
            language = lang_code
            dialect = None
            if('_' in lang_code):
                language = lang_code.split('_')[0]
                dialect = lang_code.split('_')[1]
            self.voice_combo.append_item([name, language, dialect], name)
            if([name, language, dialect] == self._voice):
                self.voice_combo.set_active(default)
            default += 1
                    
        self.voice_combo.connect('changed', self.voice_changed_cb)
        combotool = ToolComboBox(self.voice_combo)
        self.insert(combotool, -1)
        combotool.show()
        self._speech.connect('stop', self._reset_buttons_cb)

    def compare_voices(self,  a,  b):
        if a[0].lower() == b[0].lower():
            return 0
        if a[0] .lower() < b[0].lower():
            return -1
        if a[0] .lower() > b[0].lower():
            return 1

    def voice_changed_cb(self, combo):
        self._voice = combo.props.value
        self._speech.say_text(self._voice[0])
        self.save_speech_parameters()

    def load_speech_parameters(self):
        speech_parameters = {}
        data_path = os.path.join(self._activity.get_activity_root(), 'data')
        data_file_name = os.path.join(data_path, 'speech_params.json')
        if os.path.exists(data_file_name):
            f = open(data_file_name, 'r')
            try:
                speech_parameters = json.load(f)
                self._voice = speech_parameters['voice']
            finally:
                f.close()

    def save_speech_parameters(self):
        speech_parameters = {}
        speech_parameters['voice'] = self._voice
        data_path = os.path.join(self._activity.get_activity_root(), 'data')
        data_file_name = os.path.join(data_path, 'speech_params.json')
        f = open(data_file_name, 'w')
        try:
            json.dump(speech_parameters, f)
        finally:
            f.close()

    def _reset_buttons_cb(self,a):
        logging.debug('reset buttons')
        self.play_btn.set_icon_name('media-playback-start')
        self.stop_btn.set_sensitive(False)
        self.play_btn.handler_block(self.play_toggled_handler)
        self.play_btn.set_active(False)
        self.play_btn.handler_unblock(self.play_toggled_handler)
        self.is_paused = False

    def play_cb(self, widget):
        self.stop_btn.set_sensitive(True)
        if widget.get_active():
            self.play_btn.set_icon_name('media-playback-pause')
            logging.debug('Paused %s', self.is_paused)
            if not self.is_paused:
                # get the text to speech, if there are a selection,
                # play selected text, if not, play all
                abi = self._activity.abiword_canvas
                selection = abi.get_selection('text/plain')
                if not selection or selection[0] is None or selection[1] == 0:
                    # nothing selected
                    abi.select_all()
                    text = abi.get_selection('text/plain')[0]
                    abi.moveto_bod()
                else:
                    text = selection[0]
                self._speech.say_text(text, lang_code=self._voice)
            else:
                logging.debug('Continue play')
                self._speech.restart()
        else:
            self.play_btn.set_icon_name('media-playback-start')
            self.is_paused = True
            self._speech.pause()

    def stop_cb(self, widget):
        self.stop_btn.set_sensitive(False)
        self.play_btn.set_icon_name('media-playback-start')
        self.play_btn.set_active(False)
        self.is_paused = False
        self._speech.stop()
