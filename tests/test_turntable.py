import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import pytest

from turntable import (
    STEPS_PER_DEGREE,
    angle_to_steps,
    main,
    send_move,
    wait_for_move_completion,
)


class MockSerial:
    def __init__(self, statuses):
        self.statuses = iter(statuses)
        self.writes = []

    def write(self, data):
        self.writes.append(data)

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


def test_waits_for_move_ack_then_idle():
    ser = MockSerial([b'{"ack":"move"}\n', b'{"running": false}\n'])

    wait_for_move_completion(ser)


def test_idle_before_move_ack_is_not_completion():
    ser = MockSerial(
        [
            b'{"running": false}\n',
            b'{"ack":"move"}\n',
            b'{"running": false}\n',
        ]
    )

    wait_for_move_completion(ser)


@pytest.mark.parametrize("steps", [0, 1])
def test_zero_or_short_move_can_ack_without_running_status(steps):
    ser = MockSerial([b'{"ack":"move"}\n', b'{"running": false}\n'])

    send_move(ser, steps)
    wait_for_move_completion(ser)
    assert ser.writes == [f"move={steps}\n".encode()]


def test_malformed_status_is_actionable():
    ser = MockSerial([b"not-json\n"])

    with pytest.raises(RuntimeError, match="Invalid firmware status JSON"):
        wait_for_move_completion(ser)


def test_stop_waits_for_stop_ack_then_idle():
    ser = MockSerial([b'{"ack":"stop"}\n', b'{"running": false}\n'])
    wait_for_move_completion(ser, "stop")


@pytest.mark.parametrize("option", ["--steps", "--zero", "--stop"])
def test_angle_cannot_be_combined_with_action_options(monkeypatch, option):
    arguments = ["turntable", "45", option]
    if option == "--steps":
        arguments.append("10")
    monkeypatch.setattr(sys, "argv", arguments)

    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 2
