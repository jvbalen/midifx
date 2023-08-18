from enum import Enum

# MIDI file parsing default: keep only keys
PROGRAMS = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9}


# maximum size of queues between modules
MAX_QUEUE_SIZE = 100


# default control numbers used for end-of-phrase messages and built-in effects
class ControlNumbers(int, Enum):
    START_MESSAGE = 4  # 4 is also the convention for "foot pedal"
    END_MESSAGE = 4
