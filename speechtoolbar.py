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
from gi.repository import GConf

from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from sugar3.graphics.combobox import ComboBox
from sugar3.graphics.toolcombobox import ToolComboBox

import speech


class SpeechToolbar(Gtk.Toolbar):

    def __init__(self, activity):
        GObject.GObject.__init__(self)
        self._activity = activity
        if not speech.supported:
            return
        self.is_paused = False
        self._cnf_client = GConf.Client.get_default()
        self.load_speech_parameters()

        self.sorted_voices = [i for i in speech.voices()]
        self.sorted_voices.sort(self.compare_voices)
        default = 0
        for voice in self.sorted_voices:
            if voice[0] == speech.voice[0]:
                break
            default = default + 1

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

        self.voice_combo = ComboBox()
        for voice in self.sorted_voices:
            self.voice_combo.append_item(voice, voice[0])
        self.voice_combo.set_active(default)

        self.voice_combo.connect('changed', self.voice_changed_cb)
        combotool = ToolComboBox(self.voice_combo)
        self.insert(combotool, -1)
        combotool.show()
        speech.reset_cb = self.reset_buttons_cb
        speech.end_text_cb = self.reset_buttons_cb

    def compare_voices(self,  a,  b):
        if a[0].lower() == b[0].lower():
            return 0
        if a[0] .lower() < b[0].lower():
            return -1
        if a[0] .lower() > b[0].lower():
            return 1

    def voice_changed_cb(self, combo):
        speech.voice = combo.props.value
        speech.say(speech.voice[0])
        self.save_speech_parameters()

    def load_speech_parameters(self):
        speech_parameters = {}
        data_path = os.path.join(self._activity.get_activity_root(), 'data')
        data_file_name = os.path.join(data_path, 'speech_params.json')
        if os.path.exists(data_file_name):
            f = open(data_file_name, 'r')
            try:
                speech_parameters = json.load(f)
                speech.voice = speech_parameters['voice']
            finally:
                f.close()
        else:
            speech.voice = self.get_default_voice()
            logging.error('Default voice %s', speech.voice)

        self._cnf_client.add_dir('/desktop/sugar/speech',
                                 GConf.ClientPreloadType.PRELOAD_NONE)
        speech.pitch = self._cnf_client.get_int('/desktop/sugar/speech/pitch')
        speech.rate = self._cnf_client.get_int('/desktop/sugar/speech/rate')
        self._cnf_client.notify_add('/desktop/sugar/speech/pitch',
                                    self.__conf_changed_cb, None)
        self._cnf_client.notify_add('/desktop/sugar/speech/rate',
                                    self.__conf_changed_cb, None)

    def get_default_voice(self):
        """Try to figure out the default voice, from the current locale
           ($LANG)
           Fall back to espeak's voice called Default."""
        voices = speech.get_all_voices()

        locale = os.environ.get('LANG', '')
        language_location = locale.split('.', 1)[0].lower()
        language = language_location.split('_')[0]
        variant = ''
        if language_location.find('_') > -1:
            variant = language_location.split('_')[1]
        # if the language is es but not es_es default to es_la (latin voice)
        if language == 'es' and language_location != 'es_es':
            language_location = 'es_la'

        best = voices.get(language_location) or voices.get(language) \
            or 'default'
        logging.debug('Best voice for LANG %s seems to be %s',
                      locale, best)
        return [best, language, variant]

    def __conf_changed_cb(self, client, connection_id, entry, args):
        key = entry.get_key()
        value = client.get_int(key)
        if key == '/desktop/sugar/speech/pitch':
            speech.pitch = value
        if key == '/desktop/sugar/speech/rate':
            speech.rate = value

    def save_speech_parameters(self):
        speech_parameters = {}
        speech_parameters['voice'] = speech.voice
        data_path = os.path.join(self._activity.get_activity_root(), 'data')
        data_file_name = os.path.join(data_path, 'speech_params.json')
        f = open(data_file_name, 'w')
        try:
            json.dump(speech_parameters, f)
        finally:
            f.close()

    def reset_buttons_cb(self):
        logging.error('reset buttons')
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
            logging.error('Paused %s', self.is_paused)
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
                speech.play(text)
            else:
                logging.error('Continue play')
                speech.continue_play()
        else:
            self.play_btn.set_icon_name('media-playback-start')
            self.is_paused = True
            speech.pause()

    def stop_cb(self, widget):
        self.stop_btn.set_sensitive(False)
        self.play_btn.set_icon_name('media-playback-start')
        self.play_btn.set_active(False)
        self.is_paused = False
        speech.stop()
