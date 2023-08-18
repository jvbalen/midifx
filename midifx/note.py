from __future__ import annotations

import logging
import math
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple


NOTE_ON = 9 * 16
NOTE_OFF = 8 * 16
CONTROL_CHANGE = 11 * 16
SYSTEM_MESSAGE = 15 * 16

MAX_PITCH = 144
MAX_VELOCITY = 128
MIN_DURATION = 0.025
MAX_DURATION = 6.400
DURATION_BPO = 4
DURATION_BINS = int(DURATION_BPO * math.log2(MAX_DURATION / MIN_DURATION))


@dataclass(order=True)
class Message:
    """Abstract class for MIDI messages"""

    start: float

    def to_bytes(self) -> Iterable[Tuple[float, Tuple[int]]]:
        raise NotImplementedError()

    def __str__(self) -> str:
        var_str = ", ".join(
            f"{k}={v % 86400:.3f}" if isinstance(v, float) and v > 0.0 else f"{k}={v}"
            for k, v in vars(self).items()
        )
        return f"{type(self).__name__}({var_str})"


@dataclass(order=True)
class Note(Message):
    """MIDI note. Like a pretty_midi Note but with channel data

    Args:
    - start (float): start time
    - pitch (int): pitch, as note number
    - velocity (int): velocity, in [0, 128]
    - duration (float)
    - channel (int)
    """

    start: float
    pitch: Optional[int] = None
    velocity: Optional[int] = None
    duration: Optional[float] = None
    ioi: Optional[float] = None
    channel: int = 0

    def to_bytes(self) -> Iterable[Tuple[float, Tuple[int]]]:
        event_on = NOTE_ON + self.channel, self.pitch, self.velocity
        event_off = NOTE_OFF + self.channel, self.pitch, self.velocity
        yield self.start, event_on
        yield self.start + self.duration, event_off


@dataclass(order=True)
class ControlChange(Message):
    """Control change message

    Args:
    - start (float): start time
    - number (int)
    - value (int)
    - channel (int)
    """

    start: float
    number: int
    value: int = 0
    channel: int = 0

    def to_bytes(self) -> Iterable[Tuple[float, Tuple[int]]]:
        yield self.start, (CONTROL_CHANGE + self.channel, self.number, self.value)


@dataclass(order=True)
class SystemMessage(Message):
    start: float
    number: float


class NoteParser:
    """(Incomplete) MIDI Parser

    This parser implements a subset of the MIDI specifications as described in e.g. [1]

    [1] http://www.music-software-development.com/midi-tutorial.html
    """

    def __init__(self) -> None:
        self.notes_on = defaultdict(dict)  # channel -> pitch -> note

    def parse_stream(self, t: float, byte_stream: Iterable[int]) -> Iterable[Message]:
        """Convert a timestamp + MIDI bytes to an iterable of `Message`
        e.g. `Note`, `ControlChange`, `SystemMessage`
        """

        byte_stream = iter(byte_stream)
        while True:
            try:
                status_byte = next(byte_stream)
                match (status_byte // 16, status_byte % 16):
                    case (9, channel):
                        # note on
                        pitch, velocity = next(byte_stream), next(byte_stream)
                        note = Note(t, pitch, velocity, channel=channel)
                        self.notes_on[channel][pitch] = note
                    case (8, channel):
                        # note off
                        pitch, _ = next(byte_stream), next(byte_stream)
                        try:
                            note = self.notes_on[channel].pop(pitch)
                            note.duration = t - note.start
                            yield note
                        except KeyError:
                            logging.warning(f"Note off for pitch {pitch} that isn't on")
                    case (11, channel):
                        # control change
                        number, value = next(byte_stream), next(byte_stream)
                        yield ControlChange(t, number, value, channel=channel)
                    case (10 | 14, _):
                        # other status message with two data bytes
                        data_bytes = next(byte_stream), next(byte_stream)
                        logging.warning(
                            f"Unparsed bytes with number {status_byte} and data {data_bytes}"
                        )
                    case (12 | 13, _):
                        # other status message with one data byte
                        data_byte = next(byte_stream)
                        logging.warning(
                            f"Unparsed bytes with number {status_byte} and data {data_byte}"
                        )
                    case (15, number):
                        # system message
                        yield SystemMessage(t, number)
                    case (status_byte, _):
                        logging.warning(f"Unparsed bytes with number {status_byte}")
            except StopIteration:
                break
