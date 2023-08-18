from __future__ import annotations

import asyncio
import logging
import random
from typing import Iterable

from midifx.constants import MAX_QUEUE_SIZE
from midifx.note import Message, ControlChange


class Module:
    def __init__(self, name: str, on: bool | Switch = True):
        self.name = name
        self.on = as_parameter(on)
        self.input = asyncio.PriorityQueue(maxsize=MAX_QUEUE_SIZE)
        self.outputs = []
        self.tasks = [self.run]

    async def run(self) -> None:
        while True:
            _, message = await self.input.get()
            logging.debug(f"Incoming message on {self.name}: {message}")
            if isinstance(message, ControlChange):
                self.control_change(message.number, message.value)
            messages = self.process([message]) if self.on.value else [message]
            await self.send(messages)

    async def send(self, messages: Iterable[Message]) -> None:
        for message in messages:
            if self.outputs:
                logging.debug(f"Queuing message from {self.name}: {message}")
            for queue in self.outputs:
                await queue.put((message.start, message))

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        return messages

    def control_change(self, number: int, value: int) -> None:
        for var in vars(self).values():
            if isinstance(var, Parameter):
                var.control_change(number, value)


class Parameter:
    """Module parameter. Add as an attribute of a `Module` to equip the module
    with an int or float parameter that can be controlled in real time via a MIDI
    "control change."

    Exposes a `value` that is initialized to `initial_value`. When a control change
    with control number `control_number` is encountered, the accompanying
    `control_value` is mapped to (`minimum`, `maximum`) and used as the new `value`.
    """

    def __init__(
        self,
        initial_value: float | None = None,
        control_number: int | None = None,
        minimum: float = 0.0,
        maximum: float = 128.0,
        name: str = "parameter",
    ) -> None:
        if control_number is not None and (
            not isinstance(control_number, int) or not (0 <= control_number <= 127)
        ):
            raise ValueError(
                f"Control number must be an integer in (0, 127) but got {control_number}"
            )
        initial_value = minimum if initial_value is None else initial_value
        self.control_number = control_number
        self.minimum = minimum
        self.range = maximum - minimum
        self.value = initial_value
        self.name = name

    def control_change(self, number: int, value: int) -> None:
        if number != self.control_number:
            return
        new_value = self.minimum + value / 128.0 * self.range
        logging.info(f"Updating parameter '{self.name}' from {self.value:.3g} to {new_value:.3g}")
        self.value = new_value


class Switch(Parameter):
    def __init__(
        self,
        initial_value: bool = False,
        control_number: int | None = None,
        threshold: float = 0.5,
        name: str = "switch",
    ) -> None:
        super().__init__(initial_value, control_number, name=name)
        self.threshold = threshold

    def control_change(self, number: int, value: int) -> None:
        if number != self.control_number:
            return
        self.value = value / 128 >= self.threshold
        logging.info(f"Updating switch '{self.name}' to {'ON' if self.value else 'OFF'}")


class RandomParameter(Parameter):
    def control_change(self, number: int, value: int) -> None:
        if number != self.control_number or value == 0:
            return
        value = random.randint(0, 128)
        super().control_change(number, value)


class ExponentialRandomParameter(Parameter):
    def __init__(
        self,
        initial_value: float | None = None,
        control_number: int | None = None,
        median: float = 1.0,
        minimum: float = 0.0,
        maximum: float = 128.0,
        name: str = "exponential random parameter",
    ) -> None:
        self.median = median
        initial_value = median if initial_value is None else initial_value
        super().__init__(initial_value, control_number, minimum, maximum, name)

    def control_change(self, number: int, value: int) -> None:
        if number != self.control_number or value == 0:
            return
        new_value = random.expovariate(0.693 / self.median)
        new_value = min(new_value, self.minimum + self.range)
        new_value = max(new_value, self.minimum)
        logging.info(f"Updating parameter '{self.name}' from {self.value:.3g} to {new_value:.3g}")
        self.value = new_value


class RandomSwitch(Switch):
    def __init__(
        self,
        initial_value: bool = False,
        control_number: int | None = None,
        probability: float = 0.5,
        name: str = "random switch",
    ):
        super().__init__(initial_value=initial_value, control_number=control_number, name=name)
        self.probability = probability

    def control_change(self, number: int, value: int) -> None:
        if number != self.control_number or value == 0:
            return
        value = 127 if random.random() < self.probability else 0
        super().control_change(number, value)


def as_parameter(x: int | float | Parameter) -> Parameter:
    if isinstance(x, Parameter):
        return x
    elif isinstance(x, bool):
        return Switch(x, control_number=None)
    else:
        return Parameter(x, control_number=None)
