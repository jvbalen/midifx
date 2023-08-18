# MidiFX

Approximately real-time MIDI manipulation for Python, macOS.

[![build](https://github.com/jvbalen/midifx/actions/workflows/build.yml/badge.svg)](https://github.com/jvbalen/midifx/actions/workflows/build.yml)

This package implements a modular framework for real-time MIDI effects in Python, based on [`asyncio`](https://docs.python.org/3/library/asyncio.html) and [`simplecoremidi`](https://github.com/sixohsix/simplecoremidi).

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
