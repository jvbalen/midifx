import os

import pretty_midi

from midifx.io import Chain, ReadMIDI, MIDILogger, notes_from_prettymidi
from midifx.effects import PitchShift

EXAMPLE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "scale.mid")
print(EXAMPLE_FILE)


def test_read_pitch_shift_write(tmpdir, shift: int = 12):

    chain = Chain(
        ReadMIDI(EXAMPLE_FILE),
        PitchShift(amount=shift, on=True),
        MIDILogger(max_messages=7),  # make sure this is <= length EXAMPLE_FILE
        log_dir=tmpdir,
    )
    chain.run()

    res_file = os.path.join(tmpdir, os.listdir(tmpdir)[0])
    print(EXAMPLE_FILE, res_file)
    res_notes = notes_from_prettymidi(pretty_midi.PrettyMIDI(res_file))
    ref_notes = notes_from_prettymidi(pretty_midi.PrettyMIDI(EXAMPLE_FILE))
    for ref_note, res_note in zip(ref_notes, res_notes):
        assert res_note.pitch - ref_note.pitch == shift
