import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import override

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import census, harness  # noqa: E402

READY = harness.why_not() is None

LD_A = 0x3E

OUT = 0xD3

JR = 0x18

DI = 0xF3


def program(*parts: int) -> bytes:
    image = bytearray(0x2000)
    image[: len(parts)] = bytes(parts)
    return bytes(image)


def register_write(register: int, value: int) -> tuple[int, ...]:
    return (LD_A, value, OUT, 0xBF, LD_A, 0x80 | register, OUT, 0xBF)


SHOWS = program(*register_write(1, 0x40), DI, JR, 0xFE)

SILENT = program(DI, JR, 0xFE)


def archive(folder: Path, name: str, members: dict[str, bytes]) -> Path:
    where = folder / name
    with zipfile.ZipFile(where, "w") as bundle:
        for member, data in members.items():
            bundle.writestr(member, data)
    return where


def run_main(argv: list[str], into: Path) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = census.main(argv, into=into)
    return code, said.getvalue()


class ImagesTest(unittest.TestCase):
    def test_images_inside_an_archive_are_read_with_the_set_they_came_from(
        self,
    ) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SHOWS, "notes.txt": b"x"})

        # Act
        found = list(census.images_in(where))

        # Assert
        self.assertEqual(found, [("1 Japan.zip", "a.sg", SHOWS)])

    def test_a_directory_is_walked_for_images(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        (folder / "b.sc").write_bytes(SILENT)

        # Act
        found = list(census.images_in(folder))

        # Assert
        self.assertEqual(found, [(folder.name, "b.sc", SILENT)])

    def test_a_lone_image_is_read_as_its_own_set(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        lone = folder / "c.sg"
        lone.write_bytes(SILENT)

        # Act
        found = list(census.images_in(lone))

        # Assert
        self.assertEqual(found, [(folder.name, "c.sg", SILENT)])

    def test_a_directory_opens_its_archives_and_passes_over_other_files(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        archive(folder, "2 Taiwan.zip", {"d.sg": SHOWS})
        (folder / "readme.txt").write_bytes(b"x")

        # Act
        found = list(census.images_in(folder))

        # Assert
        self.assertEqual(found, [("2 Taiwan.zip", "d.sg", SHOWS)])

    def test_a_lone_file_that_is_no_image_yields_nothing(self) -> None:
        # Arrange
        lone = Path(tempfile.mkdtemp()) / "notes.txt"
        lone.write_bytes(b"x")

        # Act
        found = list(census.images_in(lone))

        # Assert
        self.assertEqual(found, [])


class GatingTest(unittest.TestCase):
    def test_a_retail_sg_1000_image_is_gated(self) -> None:
        # Arrange
        pairs = [("2 Taiwan.zip", "x.sg"), ("3 Other Regions.zip", "y.sg")]

        # Act
        gated = [census.gated(where, name) for where, name in pairs]

        # Assert
        self.assertEqual(gated, [True, True])

    def test_hacks_homebrew_and_other_machines_only_report(self) -> None:
        # Arrange
        pairs = [
            ("4 Palette Hacks.zip", "x.sg"),
            ("4 Homebrew.zip", "y.sg"),
            ("1 Japan.zip", "[BIOS] z.sg"),
            ("1 Japan.zip", "Choplifter (Japan) (Beta).sg"),
            ("1 Japan.zip", "w.sc"),
        ]

        # Act
        gated = [census.gated(where, name) for where, name in pairs]

        # Assert
        self.assertEqual(gated, [False, False, False, False, False])


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class TakeTest(unittest.TestCase):
    def test_a_census_counts_images_once_by_digest(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SHOWS, "copy.sg": SHOWS})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual((taken["listings"], taken["images"], taken["gated"]), (2, 1, 1))

    def test_a_gated_image_that_never_shows_a_display_breaks_a_property(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SILENT})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual(taken["properties"][census.DISPLAYS], 1)

    def test_the_same_image_outside_a_gated_set_only_reports(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "4 Homebrew.zip", {"a.sg": SILENT})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual((taken["properties"][census.DISPLAYS], taken["silent"]), (0, 1))

    def test_the_modes_and_register_values_reached_are_counted(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SHOWS})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual((taken["modes"], taken["registers"]["1"]["0x40"]), ({"graphics1": 1}, 1))

    def test_workers_give_the_same_answer_as_one_process(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SHOWS, "b.sg": SILENT})

        # Act
        alone, shared = census.take([where], 2, 1), census.take([where], 2, 2)

        # Assert
        self.assertEqual(alone, shared)


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class Raising(harness.Board):
    @override
    def run_frames(self, count: int) -> None:
        raise IndexError("planted")


@unittest.skipUnless(READY, "zilog-z80-python is not checked out")
class FaultTest(unittest.TestCase):
    def test_an_image_the_model_raises_on_is_reported_with_what_it_raised(self) -> None:
        # Arrange
        job = (SHOWS, 2)

        # Act
        found = census.examine(job, Raising)

        # Assert
        self.assertEqual(found["raised"], "IndexError: planted at frame 0")

    def test_and_counted_against_the_property_and_named(self) -> None:
        # Arrange
        images = [(False, SHOWS, "a.sg")]
        results = [census.examine((SHOWS, 2), Raising)]

        # Act
        broken = census.tally(images, results)["properties"][census.RAISES_NOTHING]
        named = census.culprits(images, results)[census.RAISES_NOTHING]

        # Assert
        self.assertEqual((broken, named), (1, ["a.sg: IndexError: planted at frame 0"]))

    def test_the_names_behind_a_broken_property_are_printed_but_not_kept(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"silent.sg": SILENT})
        into = folder / "corpus.json"

        # Act
        code, said = run_main([str(where), "--frames", "2", "--jobs", "1"], into)

        # Assert
        self.assertEqual((code, "         silent.sg" in said), (1, True))
        self.assertNotIn("culprits", json.loads(into.read_text()))


class MainTest(unittest.TestCase):
    def test_a_census_writes_its_corpus_and_reports_what_it_examined(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SHOWS})
        into = folder / "corpus.json"

        # Act
        code, said = run_main([str(where), "--frames", "2", "--jobs", "1"], into)

        # Assert
        self.assertEqual((code, json.loads(into.read_text())["images"]), (0, 1))
        self.assertIn("1 distinct images", said)

    def test_a_broken_property_fails_the_run(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SILENT})

        # Act
        code, said = run_main([str(where), "--frames", "2"], folder / "corpus.json")

        # Assert
        self.assertEqual((code, census.DISPLAYS in said), (1, True))


class ReportTest(unittest.TestCase):
    def test_lost_accesses_are_reported_by_image_without_failing_anything(self) -> None:
        # Arrange
        images = [(True, SHOWS, "a.sg")]
        results = [
            {"modes": ["graphics1"], "registers": [], "sprites": [], "lost": 3, "raised": None}
        ]
        taken = {
            "listings": 1,
            "images": 1,
            "gated": 1,
            "frames": 2,
            **census.tally(images, results),
            "culprits": census.culprits(images, results),
        }

        # Act
        lines = census.report(taken)

        # Assert
        self.assertEqual(lines[-2:], [f"  observed  {census.LOST}: 1 images", "         a.sg: 3"])
        self.assertEqual(sum(taken["properties"].values()), 0)


class UsageTest(unittest.TestCase):
    def test_no_path_prints_the_usage(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main([], into)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))

    def test_an_absent_path_is_named_and_examines_nothing(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main(["/nonexistent/library"], into)

        # Assert
        self.assertEqual((code, "absent: /nonexistent/library" in said), (1, True))
        self.assertIn("0 distinct images", said)

    def test_a_bad_option_prints_the_usage(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main(["x", "--frames"], into)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))


if __name__ == "__main__":
    unittest.main()
