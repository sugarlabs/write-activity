# Copyright (C) 2009 Aleksey S. Lim
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

import gst
import logging

import speech

_logger = logging.getLogger('read-etexts-activity')


def get_all_voices():
    all_voices = {}
    for voice in gst.element_factory_make('espeak').props.voices:
        name, language, dialect = voice
        if dialect != 'none':
            all_voices[language + '_' + dialect] = name
        else:
            all_voices[language] = name
    return all_voices


def _message_cb(bus, message, pipe):
    if message.type == gst.MESSAGE_EOS:
        pipe.set_state(gst.STATE_NULL)
        if speech.end_text_cb != None:
            speech.end_text_cb()
    if message.type == gst.MESSAGE_ERROR:
        pipe.set_state(gst.STATE_NULL)
        if pipe is play_speaker[1]:
            speech.reset_cb()
    elif message.type == gst.MESSAGE_ELEMENT and \
            message.structure.get_name() == 'espeak-mark':
        mark = message.structure['mark']
        speech.highlight_cb(int(mark))


def _create_pipe():
    pipe = gst.Pipeline('pipeline')

    source = gst.element_factory_make('espeak', 'source')
    pipe.add(source)

    sink = gst.element_factory_make('autoaudiosink', 'sink')
    pipe.add(sink)
    source.link(sink)

    bus = pipe.get_bus()
    bus.add_signal_watch()
    bus.connect('message', _message_cb, pipe)

    return (source, pipe)


def _speech(speaker, words):
    speaker[0].props.pitch = speech.pitch
    speaker[0].props.rate = speech.rate
    speaker[0].props.voice = speech.voice[1]
    speaker[0].props.text = words
    speaker[1].set_state(gst.STATE_NULL)
    speaker[1].set_state(gst.STATE_PLAYING)


info_speaker = _create_pipe()
play_speaker = _create_pipe()
play_speaker[0].props.track = 2


def voices():
    return info_speaker[0].props.voices


def say(words):
    _speech(info_speaker, words)


def play(words):
    _speech(play_speaker, words)


def pause():
    play_speaker[1].set_state(gst.STATE_PAUSED)


def continue_play():
    play_speaker[1].set_state(gst.STATE_PLAYING)


def is_stopped():
    for i in play_speaker[1].get_state():
        if isinstance(i, gst.State) and i == gst.STATE_NULL:
            return True
    return False


def stop():
    play_speaker[1].set_state(gst.STATE_NULL)
