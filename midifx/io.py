import asyncio
import dataclasses
import logging
import os
from asyncio import PriorityQueue
from datetime import datetime
from collections import defaultdict
from time import time, sleep
from typing import Iterable, List, Optional, Set

import pretty_midi
from simplecoremidi import MIDIDestination, MIDISource

from midifx.constants import MAX_QUEUE_SIZE, PROGRAMS
from midifx.core import Module
from midifx.note import ControlChange, Message, NoteParser, Note

PADDING = 0.05  # between start_message <-> notes and notes <-> end_message

MIDI_LOGS: List[Message] = []


class StopChain(Exception):
    pass


class Chain:
    def __init__(self, *modules: Module, loop: bool = False, log_dir: Optional[str] = None) -> None:
        """
        Args:
        - list of Module objects that poll an `input` queue and/or put events on one or
          more `outputs` queues
        - loop: whether or not to feed output of the last module back into the first
        """
        self.modules = modules
        self.loop = loop
        self.log_dir = log_dir
        connect_modules(*self.modules)
        if self.loop:
            connect_modules(self.modules[-1], self.modules[0])

    def run(self, restart_on_interrupt: bool = False) -> None:
        while True:
            try:
                asyncio.run(self.await_all(), debug=False)
            except (KeyboardInterrupt, StopChain):
                logging.info("Interrupted...")
                if self.log_dir:
                    self.write_midi_logs()
                if not restart_on_interrupt:
                    logging.info("Stopped.")
                    break
                logging.info("Restarting... Press again now to stop.")
                sleep(2.0)

    async def await_all(self) -> None:
        """Main loop consisting of asynchronous tasks, one for each module."""
        tasks = [asyncio.create_task(task()) for module in self.modules for task in module.tasks]
        await asyncio.gather(*tasks)

    def write_midi_logs(self) -> None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        path = os.path.join(self.log_dir, timestamp + ".mid")
        logging.info(f"Writing MIDI to {path}")
        write_midi(path, MIDI_LOGS)  # TODO: should MIDI_LOGS be a more async-friendly object?


class ReceiveMIDI(Module):
    def __init__(self, name: str, resolution: float = 0.001):
        super().__init__("Receive MIDI")
        self.resolution = resolution
        self.midi_in = MIDIDestination(name)
        self.bytes_queue = asyncio.PriorityQueue(maxsize=2 * MAX_QUEUE_SIZE)
        self.parser = NoteParser()
        self.tasks = [self.receive_bytes, self.run]
        logging.debug(f"Creating MIDIDestination with name {name}")
        sleep(2.0)  # give the MIDI port a few seconds to start

    async def receive_bytes(self) -> None:
        while True:
            t = time()
            byte_stream = self.midi_in.recv()
            if byte_stream:
                messages = self.parser.parse_stream(t, byte_stream)
                await self.send(messages)
            await asyncio.sleep(self.resolution)


class ReadMIDI(Module):
    def __init__(
        self,
        path: str,
        start_message: Optional[ControlChange] = None,
        end_message: Optional[ControlChange] = None,
        max_notes: Optional[int] = None,
        level: float = 1.0,
    ):
        super().__init__("Read MIDI")
        self.pretty_midi = pretty_midi.PrettyMIDI(path)
        self.start_message = start_message
        self.end_message = end_message
        self.max_notes = max_notes
        self.level = level
        self.tasks = [self.read_bytes, self.run]

    async def read_bytes(self) -> None:
        notes = notes_from_prettymidi(
            self.pretty_midi,
            t_start=time(),
            end_message=self.end_message,
            start_message=self.start_message,
            level=self.level,
        )
        await self.send(notes)


class SendMIDI(Module):
    def __init__(
        self,
        name: str = "MidiFX out",
        resolution: float = 0.001,
        override_channel: Optional[int] = None,
    ):
        super().__init__("Send MIDI")
        self.bytes_queue = PriorityQueue(maxsize=2 * MAX_QUEUE_SIZE)
        self.midi_out = MIDISource(name)
        self.resolution = resolution
        self.override_channel = override_channel
        self.tasks = [self.run, self.send_bytes]
        logging.debug(f"Creating MIDISource with name {name}")
        sleep(2.0)  # give the MIDI port a few seconds to start

    async def run(self) -> None:
        """Poll `input` for message, and convert to MIDI events (bytes)"""
        while True:
            _, message = await self.input.get()
            message_copy = dataclasses.replace(message)
            if self.override_channel is not None:
                message_copy.channel = self.override_channel
            for t, event in message_copy.to_bytes():
                logging.debug(f"Queuing bytes {event} from {message_copy}...")
                await self.bytes_queue.put((t, event))
            await super().send([message])  # in case there's other outputs

    async def send_bytes(self) -> None:
        """Poll `bytes_queue` for events, and send as MIDI"""
        logging.info(f"Running {self.name}/send_bytes...")
        max_late = 0.0
        while True:
            t, event = await self.bytes_queue.get()
            late = time() - t
            if late > -self.resolution / 2:
                log_fn = logging.warning if late > max_late else logging.debug
                log_fn(f"Sending event {event}, {1000 * late:.1f}ms late")
                self.midi_out.send(event)
                if late > max_late:
                    max_late = late
            else:
                await self.bytes_queue.put((t, event))
                await asyncio.sleep(self.resolution)


class MIDILogger(Module):
    def __init__(self, override_channel: Optional[int] = None, max_messages: Optional[int] = None):
        super().__init__("MIDILogger")
        self.override_channel = override_channel
        self.max_messages = max_messages

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        for message in messages:
            message_copy = dataclasses.replace(message)
            if self.override_channel is not None:
                message_copy.channel = self.override_channel
            MIDI_LOGS.append(message_copy)
            if self.max_messages is not None and len(MIDI_LOGS) >= self.max_messages:
                raise StopChain
            yield message


class SendPulse(Module):
    def __init__(
        self,
        ioi: float = 0.25,
        pitch: int = 69,
        velocity: int = 64,
        duration: float = 0.1,
        resolution: float = 0.001,
    ):
        super().__init__("Send pulse")
        self.ioi = ioi
        self.pitch = pitch
        self.velocity = velocity
        self.duration = duration
        self.resolution = resolution
        self.tasks = [self.generate, self.run]

    async def generate(self) -> None:
        t = time() + self.ioi
        while True:
            t += self.ioi
            message = Note(
                t, pitch=self.pitch, velocity=self.velocity, duration=self.duration, ioi=self.ioi
            )
            await self.send([message])


def connect_modules(*modules: List[Module]):
    prev_module = modules[0]
    for module in modules[1:]:
        prev_module.outputs.append(module.input)
        prev_module = module


def notes_from_prettymidi(
    midi_file: pretty_midi.PrettyMIDI,
    t_start: float = 0.0,
    start_message: Optional[Message] = None,
    end_message: Optional[Message] = None,
    all_keys: bool = False,
    max_notes: Optional[int] = None,
    level: float = 1.0,
) -> Iterable[Message]:
    """Convert PrettyMidi to list of Notes"""
    notes = filter_and_sort_prettymidi(midi_file)[:max_notes]
    transpositions = range(-6, 6) if all_keys else [0]
    for transpose in transpositions:
        if start_message is not None:
            yield dataclasses.replace(start_message, start=t_start)
        t_last = t_start
        t_end = t_start
        for note in notes:
            t = t_start + note.start - notes[0].start + PADDING
            yield Note(
                start=t,
                pitch=note.pitch + transpose,
                velocity=int(note.velocity * level),
                duration=note.end - note.start,  # use note.duration?
                ioi=t - t_last,
            )
            t_last = t
            t_end = max(t_end, t + note.duration)
        if end_message is not None:
            yield dataclasses.replace(end_message, start=t_end + PADDING)


def filter_and_sort_prettymidi(
    midi_file: pretty_midi.PrettyMIDI,
    programs: Optional[Set[int]] = PROGRAMS,
) -> List[pretty_midi.Note]:
    """Filter the notes in a midi file, as PrettyMIDI object, to include only selected programs,
    e.g. to keep only piano data (program 0). Then sort notes by start time and pitch (low to high)
    """
    notes = []
    for instrument in midi_file.instruments:
        if programs is None or instrument.program in programs:
            notes.extend(instrument.notes)
    notes = (note for note in notes if note.end >= note.start)
    return sorted(notes, key=lambda note: (note.start, note.pitch))


def write_midi(path: str, messages: Iterable[Message], program: int = 0) -> None:
    messages = sorted(messages, key=lambda message: message.start)
    try:
        start_time = messages[0].start
    except IndexError:
        logging.info("No events were logged... Skipping writing MIDI file.")
        return

    instruments = defaultdict(lambda: pretty_midi.Instrument(program=program, is_drum=False))
    for message in messages:
        match message:
            case Note(start, pitch, velocity, duration, channel=channel):
                start -= start_time
                if pitch >= 127 or velocity > 127:
                    logging.info(f"Note with large pitch/vel value in write_midi: {message}")
                pretty_note = pretty_midi.Note(velocity, pitch, start, start + duration)
                instruments[channel].notes.append(pretty_note)
            case ControlChange(start, number, value, channel):
                start -= start_time
                instruments[channel].control_changes.append(
                    pretty_midi.ControlChange(number, value, start)
                )
            case _:
                continue

    pm = pretty_midi.PrettyMIDI()
    pm.instruments.extend(instruments.values())
    try:
        pm.write(path)
    except ValueError as e:
        print(f"Error while writing PrettyMidi data to file: {pm}")
        raise e
