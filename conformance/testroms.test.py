import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import harness, testroms  # noqa: E402

READY = harness.why_not() is None

ROW = 0x0100

SETUP = bytes(
    [
        0xF3,
        *(0x31, 0xF0, 0xC3),
        *(0xDB, 0xBF),
        *(0x3E, 0x00, 0xD3, 0xBF, 0x3E, 0x80, 0xD3, 0xBF),
        *(0x3E, 0xC0, 0xD3, 0xBF, 0x3E, 0x81, 0xD3, 0xBF),
        *(0x3E, 0x0E, 0xD3, 0xBF, 0x3E, 0x82, 0xD3, 0xBF),
        *(0x3E, 0x00, 0xD3, 0xBF, 0x3E, 0x78, 0xD3, 0xBF),
        *(0x21, ROW & 0xFF, ROW >> 8),
        *(0x06, 0x20),
        *(0x7E, 0xD3, 0xBE, 0x23, 0x10, 0xFA),
        *(0x18, 0xFE),
    ]
)


def a_program(row: str) -> bytes:
    image = bytearray(0x2000)
    image[: len(SETUP)] = SETUP
    image[ROW : ROW + 32] = row.ljust(32).encode()
    return bytes(image)


A_PROGRAM = a_program("  MEMORY OK")


def a_record(folder: Path, *images: bytes, verdict: list[str] | None = None) -> Path:
    listed: list[dict[str, Any]] = [
        {
            "id": f"probe-{index}",
            "sha256": hashlib.sha256(image).hexdigest(),
            "outcome": "run",
            "frames": 2,
            "every": 1,
            "verdict": verdict,
        }
        for index, image in enumerate(images)
    ]
    listed.append({"id": "waits", "sha256": "ab" * 32, "outcome": "hosted", "needs": "x"})
    path = folder / "testroms.json"
    path.write_text(json.dumps({"cartridges": listed}))
    return path


def held_in(folder: Path, image: bytes, name: str = "probe.sg") -> Path:
    path = folder / name
    path.write_bytes(image)
    return path


class RecordedVerdictTest(unittest.TestCase):
    def test_the_check_program_finds_its_ram_and_video_memory_good(self) -> None:
        # Arrange
        held = testroms.entry("sg-1000-m2-check")

        # Act
        found = [line for line in held["verdict"] if line.endswith(("OK", "ALL IC OK"))]

        # Assert
        self.assertEqual(found, ["SCRATCH RAM OK", "VDP V-RAM ALL IC OK"])

    def test_and_reports_bad_only_the_port_for_a_device_the_board_lacks(self) -> None:
        # Arrange
        held = testroms.entry("sg-1000-m2-check")

        # Act
        found = [line for line in held["verdict"] if "BAD" in line]

        # Assert
        self.assertEqual(found, ["EXTENSION PORT BAD"])

    def test_and_runs_through_its_colour_sound_and_input_screens(self) -> None:
        # Arrange
        held = testroms.entry("sg-1000-m2-check")

        # Act
        found = [line for line in held["verdict"] if line.endswith("TEST")]

        # Assert
        self.assertEqual(found, ["COLOR TEST", "SOUND TEST", "I / O   TEST"])

    def test_an_id_the_record_does_not_hold_is_refused(self) -> None:
        # Arrange
        name = "never-recorded"

        # Act
        attempt = lambda: testroms.entry(name)  # noqa: E731

        # Assert
        self.assertRaisesRegex(AssertionError, name, attempt)

    def test_a_record_that_is_not_an_object_is_refused(self) -> None:
        # Arrange
        path = Path(tempfile.mkdtemp()) / "testroms.json"
        path.write_text("[]")

        # Act
        attempt = lambda: testroms.record(path)  # noqa: E731

        # Assert
        self.assertRaises(AssertionError, attempt)


class ReportedTest(unittest.TestCase):
    def test_a_row_of_words_is_a_report(self) -> None:
        # Arrange
        row = "   SCRATCH RAM OK   "

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertTrue(found)

    def test_a_row_holding_an_unprintable_byte_is_not(self) -> None:
        # Arrange
        row = "SCRATCH\x00RAM"

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertFalse(found)

    def test_a_row_without_a_letter_is_not(self) -> None:
        # Arrange
        row = " [ )(&%$  1984 "

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertFalse(found)

    def test_a_row_of_one_repeated_letter_is_a_fill_pattern_not_a_report(self) -> None:
        # Arrange
        row = "U" * 32

        # Act
        found = testroms.reported(row)

        # Assert
        self.assertFalse(found)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class RunTest(unittest.TestCase):
    def test_what_the_program_prints_is_read_off_the_name_table(self) -> None:
        # Arrange
        image = A_PROGRAM

        # Act
        found = testroms.verdict(image, frames=2, every=1)

        # Assert
        self.assertEqual(found, ["MEMORY OK"])


class FindingImagesTest(unittest.TestCase):
    def test_an_image_inside_a_zip_inside_a_folder_is_found_by_digest(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        with zipfile.ZipFile(folder / "held.zip", "w") as archive:
            archive.writestr("inner.sg", A_PROGRAM)
        held_in(folder, b"something else", "other.sg")
        digest = hashlib.sha256(A_PROGRAM).hexdigest()

        # Act
        found = testroms.images([folder], {digest})

        # Assert
        self.assertEqual(list(found), [digest])

    def test_a_place_that_is_not_there_holds_nothing(self) -> None:
        # Arrange
        place = Path(tempfile.mkdtemp()) / "absent"

        # Act
        found = testroms.images([place], {"ab" * 32})

        # Assert
        self.assertEqual(found, {})


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class MainTest(unittest.TestCase):
    def test_a_program_that_prints_its_recorded_verdict_exits_zero(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, A_PROGRAM, verdict=["MEMORY OK"])

        # Act
        code = testroms.main([str(held_in(folder, A_PROGRAM))], record)

        # Assert
        self.assertEqual(code, 0)

    def test_a_verdict_that_differs_from_the_record_exits_one(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        image = a_program("  MEMORY BAD")
        record = a_record(folder, image, verdict=["MEMORY OK"])

        # Act
        code = testroms.main([str(held_in(folder, image))], record)

        # Assert
        self.assertEqual(code, 1)

    def test_writing_keeps_the_verdict_measured(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, A_PROGRAM)

        # Act
        testroms.main(["--write", str(held_in(folder, A_PROGRAM))], record)

        # Assert
        self.assertEqual(testroms.entry("probe-0", record)["verdict"], ["MEMORY OK"])

    def test_an_image_absent_while_another_is_held_is_skipped_not_failed(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        other = a_program("  OTHER")
        record = a_record(folder, A_PROGRAM, other, verdict=["MEMORY OK"])

        # Act
        code = testroms.main([str(held_in(folder, A_PROGRAM))], record)

        # Assert
        self.assertEqual(code, 0)

    def test_the_places_can_come_from_the_environment(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        record = a_record(folder, A_PROGRAM, verdict=["MEMORY OK"])
        held_in(folder, A_PROGRAM)

        # Act
        with mock.patch.dict(os.environ, {testroms.PLACES: str(folder)}):
            code = testroms.main([], record)

        # Assert
        self.assertEqual(code, 0)


class NothingToRunTest(unittest.TestCase):
    def test_with_no_image_anywhere_it_exits_two(self) -> None:
        # Arrange
        environment = {k: v for k, v in os.environ.items() if k != testroms.PLACES}

        # Act
        with mock.patch.dict(os.environ, environment, clear=True):
            code = testroms.main([])

        # Assert
        self.assertEqual(code, testroms.NOTHING_TO_RUN)

    def test_an_option_it_does_not_know_is_a_usage_error(self) -> None:
        # Arrange
        argv = ["--jobs"]

        # Act
        code = testroms.main(argv)

        # Assert
        self.assertEqual(code, testroms.USAGE_ERROR)


if __name__ == "__main__":
    unittest.main()
