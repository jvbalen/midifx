"""
An effect chain with randomly evolving effect parameters, and feedback

To write to a file:
  python -m midifx.demo --in-path data/scale.mid --out-dir generated --max-out 1000

To send over MIDI:
  python -m midifx.demo --in-path data/scale.mid --send "MidiFX out"
"""
from argparse import ArgumentParser

from midifx.constants import ControlNumbers
from midifx.core import RandomParameter, ExponentialRandomParameter, RandomSwitch
from midifx.effects import BufferDelay, Delay, Mirror, PitchShift, VelocityShift
from midifx.io import Chain, ReadMIDI, SendMIDI, MIDILogger
from midifx.note import ControlChange
from midifx.util import configure_logging

PHRASE_START = ControlChange(start=None, number=ControlNumbers.START_MESSAGE, value=120)
PHRASE_END = ControlChange(start=None, number=ControlNumbers.END_MESSAGE, value=0)


parser = ArgumentParser()
parser.add_argument("--send", type=str, default=None)
parser.add_argument("--in-path", type=str, default=None)
parser.add_argument("--out-dir", type=str, default=None)
parser.add_argument("--max-out", type=int, default=None)
parser.add_argument("--debug", "-d", action="store_true")
args = parser.parse_args()
configure_logging(debug=args.debug)

modules = [
    PitchShift(
        amount=RandomParameter(
            initial_value=0,
            minimum=-5,
            maximum=5,
            control_number=PHRASE_START.number,
            name="Pitch shift",
        ),
    ),
    VelocityShift(
        amount=RandomParameter(
            initial_value=0,
            minimum=-0.5,
            maximum=0.5,
            control_number=PHRASE_START.number,
            name="Velocity shift",
        ),
    ),
    Mirror(
        on=RandomSwitch(probability=0.2, control_number=PHRASE_START.number, name="Mirror (on/off)")
    ),
    Delay(
        delay=ExponentialRandomParameter(
            control_number=PHRASE_START.number, median=0.5, name="Gap (s)"
        )
    ),
    BufferDelay(control_message=PHRASE_END),
    ReadMIDI(path=args.in_path, start_message=PHRASE_START, end_message=PHRASE_END),
]
if args.send:
    modules.append(SendMIDI(name=f"{args.send}"))
if args.out_dir:
    modules.append(MIDILogger(override_channel=1, max_messages=args.max_out))

chain = Chain(*modules, log_dir=args.out_dir, loop=True)
chain.run()
