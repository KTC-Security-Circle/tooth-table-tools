import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from turntable import STEPS_PER_DEGREE, angle_to_steps  # noqa: E402


def test_zero_degrees():
    assert angle_to_steps(0) == 0


def test_positive_angle():
    assert angle_to_steps(90) == round(90 * STEPS_PER_DEGREE)


def test_negative_angle_direction():
    assert angle_to_steps(-45) == -angle_to_steps(45)


def test_full_rotation_matches_steps_per_rev():
    assert angle_to_steps(360) == round(STEPS_PER_DEGREE * 360)
