# Copyright (C) 2008 James D. Simmons
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

from gi.repository import Gdk
import time
import threading
import speechd
import logging

import speech

_logger = logging.getLogger('read-etexts-activity')

done = True


def voices():
    try:
        client = speechd.SSIPClient('readetextstest')
        voices = client.list_synthesis_voices()
        client.close()
        return voices
    except Exception as e:
        _logger.warning('speech dispatcher not started: %s' % e)
        return []


def say(words):
    try:
        client = speechd.SSIPClient('readetextstest')
        client.set_rate(int(speech.rate))
        client.set_pitch(int(speech.pitch))
        client.set_language(speech.voice[1])
        client.speak(words)
        client.close()
    except Exception as e:
        _logger.warning('speech dispatcher not running: %s' % e)


def is_stopped():
    return done


def stop():
    global done
    done = True


def play(words):
    global thread
    thread = EspeakThread(words)
    thread.start()


class EspeakThread(threading.Thread):

    def __init__(self, words):
        threading.Thread.__init__(self)
        self.words = words

    def run(self):
        "This is the code that is executed when the start() method is called"
        self.client = None
        try:
            self.client = speechd.SSIPClient('readetexts')
            self.client._conn.send_command('SET', speechd.Scope.SELF,
                                           'SSML_MODE', "ON")
            if speech.voice:
                self.client.set_language(speech.voice[1])
                self.client.set_rate(speech.rate)
                self.client.set_pitch(speech.pitch)
            self.client.speak(self.words, self.next_word_cb,
                              (speechd.CallbackType.INDEX_MARK,
                               speechd.CallbackType.END))
            global done
            done = False
            while not done:
                time.sleep(0.1)
            self.cancel()
            self.client.close()
        except Exception as e:
            _logger.warning('speech-dispatcher client not created: %s' % e)

    def cancel(self):
        if self.client:
            try:
                self.client.cancel()
            except Exception as e:
                _logger.warning('speech dispatcher cancel failed: %s' % e)

    def next_word_cb(self, type, **kargs):
        if type == speechd.CallbackType.INDEX_MARK:
            mark = kargs['index_mark']
            word_count = int(mark)
            Gdk.threads_enter()
            speech.highlight_cb(word_count)
            Gdk.threads_leave()
        elif type == speechd.CallbackType.END:
            Gdk.threads_enter()
            speech.reset_cb()
            Gdk.threads_leave()
            global done
            done = True
