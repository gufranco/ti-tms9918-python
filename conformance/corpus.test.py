import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import census, corpus  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "corpus.json").read_text())


def sound() -> dict[str, Any]:
    return {
        "listings": 3,
        "images": 2,
        "gated": 1,
        "frames": 600,
        "properties": dict.fromkeys(census.PROPERTIES, 0),
        "modes": {"graphics1": 2},
        "sprites": {"size 8 x1": 1},
        "registers": {"1": {"0x40": 2}},
        "lost": {"retail": 0, "other": 0},
        "silent": 0,
    }


def run_main(held: dict[str, Any]) -> tuple[int, str]:
    where = Path(tempfile.mkdtemp()) / "corpus.json"
    where.write_text(json.dumps(held))
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = corpus.main(where)
    return code, said.getvalue()


class ReplayTest(unittest.TestCase):
    def test_the_corpus_here_breaks_no_property(self) -> None:
        # Arrange
        held = HELD

        # Act
        broken = corpus.broken(held)

        # Assert
        self.assertEqual(broken, [])

    def test_and_holds_together(self) -> None:
        # Arrange
        held = HELD

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, [])

    def test_and_names_every_property_the_census_gates_on(self) -> None:
        # Arrange
        gated = list(census.PROPERTIES)

        # Act
        named = list(HELD["properties"])

        # Assert
        self.assertEqual(named, gated)

    def test_and_counts_the_retail_images_it_was_taken_over(self) -> None:
        # Arrange
        held = HELD

        # Act
        counted = (held["gated"] > 0, held["images"] >= held["gated"])

        # Assert
        self.assertEqual(counted, (True, True))


class CheckTest(unittest.TestCase):
    def test_a_sound_corpus_passes(self) -> None:
        # Arrange
        held = sound()

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, said.splitlines()[0]), (0, "2 images, 1 retail, 600 frames each"))

    def test_a_broken_property_fails(self) -> None:
        # Arrange
        held = {**sound(), "properties": {**sound()["properties"], census.DISPLAYS: 1}}

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, f"{census.DISPLAYS}: 1 broken" in said), (1, True))

    def test_a_mode_counted_on_more_images_than_there_are_fails(self) -> None:
        # Arrange
        held = {**sound(), "modes": {"graphics1": 3}}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, ["mode graphics1 on 3 of 2 images"])

    def test_a_register_value_counted_on_more_images_than_there_are_fails(self) -> None:
        # Arrange
        held = {**sound(), "registers": {"7": {"0x1F": 5}}}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, ["register 7 value 0x1F on 5 of 2 images"])

    def test_more_retail_images_than_images_fails(self) -> None:
        # Arrange
        held = {**sound(), "gated": 3, "silent": 3}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, ["3 retail of 2 images", "3 silent of 2 images"])

    def test_an_inconsistent_corpus_fails_the_run(self) -> None:
        # Arrange
        held = {**sound(), "gated": 3}

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, "3 retail of 2 images" in said), (1, True))


if __name__ == "__main__":
    unittest.main()
