"""

================================================================================

	mingus - Music theory Python package, FluidSynth support
	Copyright (C) 2008, Bart Spaans

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

================================================================================

   This module provides FluidSynth support for mingus. FluidSynth is a software 
   MIDI synthesizer which allows you to play the containers in mingus.containers 
   real-time. To work with this module, you'll need fluidsynth and a nice 
   instrument collection (look here: http://www.hammersound.net, go to Sounds -> 
   Soundfont Library -> Collections).

   To start using FluidSynth with mingus, do:
{{{
   	>>> from mingus.midi import fluidsynth
	>>> fluidsynth.init("soundfontlocation.sf2")
}}}

   Now you are ready to play Notes, NoteContainers, etc.

================================================================================

"""

from datetime import datetime
from mingus.containers.Instrument import MidiInstrument
import pyFluidSynth as fs
from time import sleep

class MidiSequencer:
	"""A simple MidiSequencer for FluidSynth"""

	output = None


	def __init__(self):
		self.fs = fs.Synth()

	def start_audio_output(self, driver=None):
		"""The optional driver argument can be any of 'alsa', \
'oss', 'jack', 'portaudio', 'sndmgr', 'coreaudio', 'Direct Sound'. \
Not all drivers will be available for every platform."""
		self.fs.start(driver)

	def load_sound_font(self, sf2):
		"""Loads a sound font. This function should be called \
before your audio can be played, since the instruments are kept in the \
sf2 file. Retuns True on success, False on failure."""
		self.sfid = self.fs.sfload(sf2)
		if self.sfid == -1:
			return False
		return True


	def set_instrument(self, channel, instr, bank = 0):
		"""Sets the channel to the instrument _instr_."""
		self.fs.program_select(channel, self.sfid, bank, instr)
		return True

	def control_change(self, channel, control, value):
		if control < 0 or control > 128:
			return False
		if value < 0 or value > 128:
			return False
		self.fs.cc(channel, control, value)
		return True


	def play_Note(self, note, channel = 1, velocity = 100):
		"""Plays a Note object on a channel[1-16] with a \
velocity[0-127]. You can either specify the velocity and channel \
here as arguments or you can set the Note.velocity and Note.channel \
attributes, which will take presedence over the function arguments."""
		if hasattr(note, 'velocity'):
			velocity = note.velocity
		if hasattr(note, 'channel'):
			channel = note.channel
		self.fs.noteon(int(channel), int(note) + 12, int(velocity))
		return True

	def stop_Note(self, note, channel = 1):
		"""Stops a note on a channel. If Note.channel is set, it \
will take presedence over the channel argument given here."""
		if hasattr(note, 'channel'):
			channel = note.channel
		self.fs.noteoff(channel, int(note) + 12)
		return True




	def stop_everything(self):
		"""Stops all the notes on all channels."""
		for x in range(118):
			for c in range(16):
				self.stop_Note(x, c)


	def play_NoteContainer(self, nc, channel = 1, velocity = 100):
		"""Plays the Notes in the NoteContainer nc."""
		for note in nc:
			if not self.play_Note(note, channel, velocity):
				return False
		return True



	def stop_NoteContainer(self, nc, channel = 1):
		"""Stops playing the notes in NoteContainer nc."""
		for note in nc:
			if not self.stop_Note(note, channel):
				return False
		return True



	def play_Bar(self, bar, channel = 1, bpm = 120):
		"""Plays a Bar object. The tempo can be changed by setting \
the bpm attribute on a NoteContainer. Returns a dictionary with \
the bpm lemma set on success, an empty dict on some kind of failure. """

		# length of a quarter note
		qn_length = 60.0 / bpm

		for nc in bar:

			if not self.play_NoteContainer(nc[2], channel, 100):
				return {}

			# Change the quarter note length if the NoteContainer has a bpm attribute
			if hasattr(nc[2], "bpm"):
				bpm = nc[2].bpm
				qn_length = 60.0 / bpm
			
			sleep(qn_length * (4.0 / nc[1]))
			self.stop_NoteContainer(nc[2], channel)

		return {"bpm": bpm}


	def play_Bars(self, bars, channels, bpm = 120):
		"""Plays several bars (a list of Bar objects) at the same time. A list of \
channels should also be provided. The tempo can be changed by providing one or more of \
the NoteContainers with a bpm argument."""

		qn_length = 60.0 / bpm  # length of a quarter note
		tick = 0.0              # place in beat from 0.0 to bar.length
		cur = [0] * len(bars)   # keeps the index of the NoteContainer under investigation in each of the bars
		playing = []            # The NoteContainers being played.


		# The following sequencer is pretty complicated, but that's because we're playing
		# multiple bars at the same time, which in turn can consist of different note values.
		# Getting the timing right is the crucial task and most of the code here is
		# for finding out how long we should sleep between notes. 
		while tick < bars[0].length:

			# Prepare a and play a list of NoteContainers that are ready for it.
			# The list `playing_new` holds both the duration and the NoteContainer.
			playing_new = []
			for n, x in enumerate(cur):
				start_tick, note_length, nc = bars[n][x]
				if start_tick <= tick:
					self.play_NoteContainer(nc, channels[n])
					playing_new.append([note_length, n])
					playing.append([note_length, nc, channels[n], n])

					# Change the length of a quarter note if the NoteContainer has a bpm attribute
					if hasattr(nc, "bpm"):
						bpm = nc.bpm
						qn_length = 60.0 / bpm

			# Sort the list and sleep for the shortest duration
			if len(playing_new) != 0:
				playing_new.sort()
				shortest = playing_new[-1][0]
				sleep(qn_length * (4.0 / shortest))

			# If somehow, playing_new doesn't contain any notes
			# (something that shouldn't happen when the bar was filled
			# properly), we make sure that at least the notes that are 
			# still playing get handled correctly. 
			else:
				if len(playing) != 0:
					playing.sort()
					shortest = playing[-1][0]
					sleep(qn_length * (4.0 / shortest))
				else:
					#warning: this could lead to some strange behaviour.
					# OTOH. Leaving gaps is not the way Bar works.
					# should we do an integrity check on bars first?
					return {}

			# Add shortest interval to tick
			tick += 1.0 / shortest

			# This final piece adjusts the duration in `playing` and
			# checks if a NoteContainer should be stopped.
			new_playing = []
			for length, nc, chan, n in playing:
				duration = 1.0 / length - 1.0 / shortest
				if duration >= 0.00001:
					new_playing.append([1.0 / duration, nc, chan, n])
				else:
					self.stop_NoteContainer(nc, chan)
					if cur[n] < len(bars[n]) - 1:
						cur[n] += 1
			playing = new_playing

			
		# Stop all the notes that are still playing
		for p in playing:
			self.stop_NoteContainer(p[1], p[2])
			playing.remove(p)

		return {"bpm": bpm}


	def play_Track(self, track, channel = 1, bpm = 120):
		"""Plays a Track object."""
		for bar in track:

			res = self.play_Bar(bar, channel, bpm)
			if res != {}:
				bpm = res["bpm"]
			else:
				return {}
		return {"bpm": bpm}

	def play_Tracks(self, tracks, channels, bpm =120):
		"""Plays a list of Tracks. """
		
		# Set the right instruments
		for x in range(len(tracks)):
			instr = tracks[x].instrument
			if isinstance(instr, MidiInstrument):
				try: 
					i = instr.names.index(instr.name)
				except:
					i = 1
				self.set_instrument(channels[x], i)
			else:
				self.set_instrument(channels[x], 1)

		
		current_bar = 0
		max_bar = len(tracks[0])

		# Play the bars
		while current_bar < max_bar:
			playbars = []
			for tr in tracks:
				playbars.append(tr[current_bar])
			res = self.play_Bars(playbars, channels, bpm)
			if res != {}:
				bpm = res["bpm"]
			else:
				return {}
			current_bar += 1

		return {"bpm":bpm}
			

	def play_Composition(self, composition, channels = None, bpm = 120):
		"""Plays a Composition object."""

		if channels == None:
			channels = map(lambda x: x + 1, range(len(composition.tracks)))
		return self.play_Tracks(composition.tracks, channels, bpm)


	## MIDI CONTROLLER TYPE 'SHORTCUTS'

	def modulation(self, channel, value):
		"""Sets the modulation"""
		return self.control_change(channel, 1, value)

	def main_volume(self, channel, value):
		"""Sets the main volume."""
		return self.control_change(channel, 7, value)

	def pan(self, channel, value):
		"""Sets the panning."""
		return self.control_change(channel, 10, value)


midi = MidiSequencer()
initialized = False

def init(sf2, driver = None):
	"""This function needs to be called before you can have any \
audio. The sf2 argument should be the location of a valid soundfont \
file. The optional driver argument can be any of 'alsa', 'oss', 'jack', 'portaudio', \
'sndmgr', 'coreaudio' or 'Direct Sound'. Returns True on success, False on failure."""
	global midi, initialized

	if not initialized:
		midi.start_audio_output(driver)
		if not midi.load_sound_font(sf2):
			return False
		midi.fs.program_reset()
		initialized = True
	return True


def play_Note(note, channel = 1, velocity = 100):
	"""Sends a Note object as midi signal to the fluidsynth server. \
The channel and velocity can be set as Note attributes as well. If that's \
the case those values take presedence over the ones given here as function \
arguments.
{{{
>>> n = Note("C", 4)
>>> n.channel = 9
>>> n.velocity = 50
>>> FluidSynth.play_Note(n)
}}}"""
	return midi.play_Note(note, channel, velocity)


def stop_Note(note, channel = 1):
	"""Stops the Note playing at channel. If a channel attribute is set on the note, \
it will take presedence."""
	return midi.stop_Note(note, channel)


def play_NoteContainer(nc, channel = 1, velocity = 100):
	"""Uses play_Note to play the Notes in the NoteContainer nc."""
	return midi.play_NoteContainer(nc, channel, velocity)

def stop_NoteContainer(nc, channel = 1):
	"""Uses stop_Note to stop the notes in NoteContainer nc."""
	return midi.stop_NoteContainer(nc, channel)

def play_Bar(bar, channel = 1, bpm = 120):
	"""Plays a Bar object using play_NoteContainer and stop_NoteContainer. \
Set a bpm attribute on a NoteContainer to change the tempo."""
	return midi.play_Bar(bar, channel, bpm)

def play_Bars(bars, channels, bpm = 120):
	"""Plays a list of bars on the given list of channels. Set a bpm attribute \
on a NoteContainer to change the tempo."""
	return midi.play_Bars(bars, channels, bpm)

def play_Track(track, channel = 1, bpm = 120):
	"""Uses play_Bar to play a Track object."""
	return midi.play_Track(track, channel, bpm)

def play_Tracks(tracks, channels, bpm = 120):
	"""Uses play_Bars to play a list of Tracks on the given list of channels."""
	return midi.play_Tracks(tracks, channels, bpm)

def play_Composition(composition, channels = None, bpm = 120):
	"""Plays a composition."""
	return midi.play_Composition(composition, channels, bpm)

def control_change(channel, control, value):
	"""Sends a control change event on channel."""
	return midi.control_change(channel, control, value)


def set_instrument(channel, midi_instr):
	"""Sets the midi instrument on channel."""
	return midi.set_instrument(channel, midi_instr)

def stop_everything():
	"""Stops all the playing notes on all channels"""
	return midi.stop_everything()

def modulation(channel, value):
	return midi.modulation(channel, value)

def pan(channel, value):
	return midi.pan(channel, value)

def main_volume(channel, value):
	return midi.main_volume(channel, value)

def set_instrument(channel, instr, bank = 0):
	return midi.set_instrument(channel, instr, bank)
