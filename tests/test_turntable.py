import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pytest

from turntable import (
    STEPS_PER_DEGREE,
    angle_to_steps,
    wait_for_move_completion,
)


class MockSerial:
    def __init__(self, statuses):
        self.statuses = iter(statuses)

    def readline(self):
        try:
            return next(self.statuses)
        except StopIteration:
            return b""


def test_zero_degrees():
    assert angle_to_steps(0) == 0


def test_positive_angle():
    assert angle_to_steps(90) == round(90 * STEPS_PER_DEGREE)


def test_negative_angle_direction():
    assert angle_to_steps(-45) == -angle_to_steps(45)


def test_full_rotation_matches_steps_per_rev():
    assert angle_to_steps(360) == round(STEPS_PER_DEGREE * 360)


def test_waits_for_running_then_idle():
    ser = MockSerial(
        [
            b'{"running": false}\n',
            b'{"running": true}\n',
            b'{"running": false}\n',
        ]
    )

    wait_for_move_completion(ser, timeout=1)


def test_timeout_when_move_never_completes():
    ser = MockSerial([b'{"running": true}\n'])

    with pytest.raises(TimeoutError, match="completion"):
        wait_for_move_completion(ser, timeout=0.001)


def test_immediately_idle_does_not_count_as_completion():
    ser = MockSerial([b'{"running": false}\n'])

    with pytest.raises(TimeoutError, match="running"):
        wait_for_move_completion(ser, timeout=0.001)


def test_malformed_status_is_actionable():
    ser = MockSerial([b"not-json\n"])

    with pytest.raises(RuntimeError, match="Invalid firmware status JSON"):
        wait_for_move_completion(ser, timeout=1)
