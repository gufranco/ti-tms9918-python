import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import cartridges  # noqa: E402

HELD = json.loads(cartridges.BOARDS.read_text())

PINNED = "dc00cf3517eef30587b33efbf1e1c63ad3531b58"


def table(rom: bytes, board: str) -> Path:
    where = Path(tempfile.mkdtemp()) / "boards.json"
    entry = {
        "sha1": hashlib.sha1(rom, usedforsecurity=False).hexdigest(),
        "board": board,
        "title": "a test image",
    }
    where.write_text(json.dumps({"source": HELD["source"], "boards": [entry]}))
    return where


class LayoutTest(unittest.TestCase):
    def test_a_plain_board_repeats_its_kilobyte_up_to_ffff(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS[cartridges.PLAIN]

        # Act
        placed = (layout.locate(0xC010), layout.locate(0xFC10))

        # Assert
        self.assertEqual(placed, (0x010, 0x010))

    def test_a_plain_board_has_no_ram_below_c000(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS[cartridges.PLAIN]

        # Act
        placed = [layout.locate(address) for address in (0x0000, 0x2000, 0x8000, 0xBFFF)]

        # Assert
        self.assertEqual(placed, [None, None, None, None])

    def test_othello_repeats_two_kilobytes_across_8000_to_9fff(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS["othello"]

        # Act
        placed = (layout.locate(0x8001), layout.locate(0x8801), layout.locate(0xA000))

        # Assert
        self.assertEqual(placed, (0x401, 0x401, None))

    def test_othello_keeps_the_console_kilobyte_apart(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS["othello"]

        # Act
        placed = (layout.locate(0xC001), layout.size)

        # Assert
        self.assertEqual(placed, (0x001, 0xC00))

    def test_the_castle_holds_eight_kilobytes_at_8000(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS["castle"]

        # Act
        placed = (layout.locate(0x8000), layout.locate(0x9FFF), layout.locate(0xA000))

        # Assert
        self.assertEqual(placed, (0x400, 0x23FF, None))

    def test_level_three_holds_sixteen_kilobytes_up_to_bfff(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS["level3"]

        # Act
        placed = (layout.locate(0x8000), layout.locate(0xBFFF), layout.locate(0xC000))

        # Assert
        self.assertEqual(placed, (0x400, 0x43FF, 0x000))

    def test_dahjee_type_a_puts_eight_kilobytes_at_2000(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS["dahjee_typea"]

        # Act
        placed = (layout.locate(0x1FFF), layout.locate(0x2000), layout.locate(0x3FFF))

        # Assert
        self.assertEqual(placed, (None, 0x0000, 0x1FFF))

    def test_and_replaces_the_console_kilobyte_with_its_own(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS["dahjee_typea"]

        # Act
        placed = (layout.locate(0xC000), layout.locate(0xFFFF), layout.size)

        # Assert
        self.assertEqual(placed, (0x2000, 0x23FF, 0x2400))

    def test_dahjee_type_b_repeats_eight_kilobytes_from_c000(self) -> None:
        # Arrange
        layout = cartridges.LAYOUTS["dahjee_typeb"]

        # Act
        placed = (layout.locate(0xC000), layout.locate(0xDFFF), layout.locate(0xE000))

        # Assert
        self.assertEqual(placed, (0x0000, 0x1FFF, 0x0000))

    def test_every_window_lands_inside_its_board(self) -> None:
        # Arrange
        layouts = cartridges.LAYOUTS.values()

        # Act
        outside = [
            (layout, address)
            for layout in layouts
            for address in range(0x10000)
            if (placed := layout.locate(address)) is not None and placed >= layout.size
        ]

        # Assert
        self.assertEqual(outside, [])


class TableTest(unittest.TestCase):
    def test_the_table_names_its_source_at_the_pinned_commit(self) -> None:
        # Arrange
        source = HELD["source"]

        # Act
        named = (source["file"], source["commit"])

        # Assert
        self.assertEqual(named, ("hash/sg1000.xml", PINNED))

    def test_every_board_in_the_table_has_a_layout(self) -> None:
        # Arrange
        named = {entry["board"] for entry in HELD["boards"]}

        # Act
        missing = named - set(cartridges.LAYOUTS)

        # Assert
        self.assertEqual(missing, set())

    def test_every_digest_is_a_whole_sha1(self) -> None:
        # Arrange
        digests = [entry["sha1"] for entry in HELD["boards"]]

        # Act
        malformed = [one for one in digests if len(one) != 40 or set(one) - set("0123456789abcdef")]

        # Assert
        self.assertEqual((malformed, len(digests), len(set(digests))), ([], 21, 21))

    def test_no_plain_board_is_listed(self) -> None:
        # Arrange
        named = [entry["board"] for entry in HELD["boards"]]

        # Act
        plain = named.count(cartridges.PLAIN)

        # Assert
        self.assertEqual(plain, 0)


class LookupTest(unittest.TestCase):
    def test_an_image_the_table_lists_gets_its_board(self) -> None:
        # Arrange
        rom = bytes(range(256)) * 4
        where = table(rom, "othello")

        # Act
        layout = cartridges.layout_for(rom, where)

        # Assert
        self.assertIs(layout, cartridges.LAYOUTS["othello"])

    def test_an_image_the_table_does_not_list_is_plain(self) -> None:
        # Arrange
        where = table(b"\x00" * 1024, "othello")

        # Act
        layout = cartridges.layout_for(b"\xff" * 1024, where)

        # Assert
        self.assertIs(layout, cartridges.LAYOUTS[cartridges.PLAIN])

    def test_a_board_the_table_names_without_a_layout_is_refused(self) -> None:
        # Arrange
        rom = b"\x01" * 1024
        where = table(rom, "terebi")

        # Act
        with self.assertRaises(KeyError) as raised:
            cartridges.layout_for(rom, where)

        # Assert
        self.assertEqual(raised.exception.args, ("terebi",))


if __name__ == "__main__":
    unittest.main()
