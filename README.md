# MidiFX

Approximately real-time MIDI manipulation for Python, macOS.

[![build](https://github.com/jvbalen/midifx/actions/workflows/build.yml/badge.svg)](https://github.com/jvbalen/midifx/actions/workflows/build.yml)

A light-weight modular framework for prototyping real-time MIDI effects in Python, based on [`asyncio`](https://docs.python.org/3/library/asyncio.html) and [`simplecoremidi`](https://github.com/sixohsix/simplecoremidi).

## Installation

> Note: this package requires macOS, and Python >= 3.10.

Clone this repository and install using `pip install .` in the cloned directory.

## Usage

To instantiate a chain of MIDI effects, including optional MIDI input and output, create a `Chain` and add modules to it. E.g.:

```python
from midifx.io import Chain, ReceiveMIDI, SendMIDI
from midifx.effects import Delay, PitchShift

chain = Chain(
    ReceiveMIDI(name="MidiFX in"),
    Delay(delay=2.0),
    PitchShift(amount=12),
    SendMIDI(name="MidiFX out"),
)
chain.run()
```

For a more elaborate example, see [`demo.py`](demo.py).

## Features

Create a real-time MIDI effect chain by chaining together I/O modules and effects.
* I/O modules include reading and writing MIDI from a file, and sending and receiving MIDI over a MIDI port.
* A few simple MIDI effects, including delay, pitch shift and velocity changes, are also included.
* New effects should be relatively easy to implement by subclassing `Module` and implementing `process`.

> Note: 'note on' and 'note off' events are combined in into 'note' events before processing, after the 'note off' event is registered. In some cases, this adds an intrinsic latency stemming from the duration of a note.

Modules can be controlled in real-time using `Parameter` objects that listen to control change messages and update their current `value` within a given range. Similarly, `Switch` objects allow for turning effects on and off. See the [built-in effects](midifx/effects.py) for examples.

More experimentally, modules can also be equipped with randomly evolving parameters and switches. These are randomly updated every time a particular control message is encountered. See again the [`demo.py`](demo.py) script for how this can work.

## Custom effect template

```python
from typing import Iterable

from midifx.core import as_parameter, Module, Parameter, Switch
from midifx.note import Message, Note


class MyEffect(Module):
    """Custom MIDI effect. Has one parameter and an on/off attribute, which can be
    MIDI-controlled by passing a Parameter and Switch object to the constructor.
    These will automatically listen to the relevant respective control messages
    as implemented in Module.
    """

    def __init__(self, parameter: float | Parameter = 2.0, on: bool | Switch = True):
        super().__init__("My Effect", on=on)
        self.parameter = as_parameter(parameter)

    def process(self, messages: Iterable[Message]) -> Iterable[Message]:
        """Receive 0 or 1 messages (e.g. notes or control messages), and return 0 or 1
        messages. For most use cases, only notes need actual processing; control message
        need not be handled (but you will very probably want to pass them on).
        """
        for message in messages:
            if isinstance(message, Note):
                pass  # add your logic here, modifying `message` based on `self.parameter.value`
            yield message
```
