import logging
import random
from typing import Iterable

from midifx.core import as_parameter, Module, Parameter, Switch
from midifx.note import ControlChange, Message, Note


class Delay(Module):
    """Delay effect that applies a fixed time delay to each incoming event. The delay
    time can be MIDI-controlled by assigning Parameter to the `delay` attribute.
    """

    def __init__(self, delay: float | Parameter = 2.0, on: bool | Switch = True):
        super().__init__("Delay", on=on)
        self.delay = as_parameter(delay)

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        for message in messages:
            message.start += self.delay.value
            yield message


class Mirror(Module):
    """Mirror a note's pitch around a given center pitch"""

    def __init__(self, center_pitch: int = 69, on: bool | Switch = True):
        super().__init__("Mirror", on=on)
        self.center_pitch = Parameter(center_pitch, minimum=57, maximum=81, name="center_pitch")

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        for message in messages:
            if isinstance(message, Note):
                message.pitch = clip_pitch(2 * int(round(self.center_pitch.value)) - message.pitch)
            yield message


class PitchShift(Module):
    """Shift pitches up or down."""

    def __init__(self, amount: int | Parameter = 2, on: bool | Switch = True):
        super().__init__("PitchShift", on=on)
        self.amount = as_parameter(amount)

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        for message in messages:
            if isinstance(message, Note):
                message.pitch = clip_pitch(message.pitch + int(round(self.amount.value)))
            yield message


class VelocityShift(Module):
    """Shift velocities up or down.

    Amount can be a value in the open interval (-1, 1).
    """

    def __init__(self, amount: float | Parameter = 0.2, on: bool | Switch = True):
        super().__init__(name="VelocityShift", on=on)
        self.amount = as_parameter(amount)

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        for message in messages:
            if isinstance(message, Note):
                if self.amount.value > 0:
                    message.velocity += int(self.amount.value * (128 - message.velocity))
                else:
                    message.velocity += int(self.amount.value * message.velocity)
            yield message


class Dropout(Module):
    """Drop random notes."""

    def __init__(self, amount: float | Parameter = 0.5, on: bool | Switch = True):
        super().__init__("Dropout", on=on)
        self.amount = as_parameter(amount)

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        for message in messages:
            if not isinstance(message, Note) or random.random() > self.amount.value:
                yield message


class BufferDelay(Module):
    """Delay effect that accumulates events in a buffer and starts replaying the buffer
    when a control change event with a given control number is encountered
    """

    def __init__(self, control_message: ControlChange, gap: float | Parameter = 0.0) -> None:
        super().__init__("Buffer delay")
        self.buffer = []
        self.control_message = control_message
        self.gap = as_parameter(gap)

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        for message in messages:
            if self.buffer and message.start < self.buffer[-1].start:
                logging.warn("Buffer encountered message with non-monotonic start time")
            self.buffer.append(message)
            if (
                isinstance(message, ControlChange)
                and message.number == self.control_message.number
                and message.value == self.control_message.value
            ):
                yield from self.flush(message.start)

    def flush(self, start: float):
        logging.debug(f"Emptying buffer of length {len(self.buffer)}...")
        delay = start - self.buffer[0].start + self.gap.value
        for message in self.buffer:
            message.start += delay
            yield message
        self.buffer = []


def clip_pitch(pitch: int) -> int:
    while pitch >= 127:
        pitch -= 12
    while pitch < 0:
        pitch += 12
    return pitch
