# MidiFX

Approximately real-time MIDI manipulation for Python, macOS.

[![build](https://github.com/jvbalen/midifx/actions/workflows/build.yml/badge.svg)](https://github.com/jvbalen/midifx/actions/workflows/build.yml)

This package implements a light-weight modular framework for prototyping real-time MIDI effects in Python, based on [`asyncio`](https://docs.python.org/3/library/asyncio.html) and [`simplecoremidi`](https://github.com/sixohsix/simplecoremidi).

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

Modules can be controlled in real-time using `Parameter` objects that listen to control change messages and update their current `value` within a given range. Similarly, `Switch` objects allow for turning effects on and off. See the [built-in effects](midifx/effects.py) for examples.

More experimentally, modules can also be equipped with randomly evolving parameters and switches. These are randomly updated every time a particular control message is encountered. See again the [`demo.py`](demo.py) script for how this can work.
