import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ast  # noqa: E402
import unittest  # noqa: E402

import tms9918  # noqa: E402

SOURCE = ROOT / "tms9918" / "errors.py"


def defined_errors() -> list[str]:
    tree = ast.parse(SOURCE.read_text())
    return [node.name for node in tree.body if isinstance(node, ast.ClassDef)]


def imported_modules(tree: ast.Module) -> list[str]:
    from_imports = [
        node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    ]
    plain = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    return from_imports + plain


class SurfaceTest(unittest.TestCase):
    def test_it_defines_at_least_one_error(self) -> None:
        # Arrange
        source = SOURCE

        # Act
        found = defined_errors()

        # Assert
        self.assertGreater(len(found), 0, source.name)

    def test_every_error_it_defines_is_exported_from_the_package(self) -> None:
        # Arrange
        exported = tms9918.__all__

        # Act
        missing = [name for name in defined_errors() if name not in exported]

        # Assert
        self.assertEqual(missing, [])

    def test_what_the_package_exports_under_each_name_is_that_error(self) -> None:
        # Arrange
        names = defined_errors()

        # Act
        found = {name: getattr(tms9918, name).__module__ for name in names}

        # Assert
        self.assertEqual(found, dict.fromkeys(names, "tms9918.errors"))

    def test_every_exported_error_is_an_exception(self) -> None:
        # Arrange
        names = defined_errors()

        # Act
        kinds = [issubclass(getattr(tms9918, name), Exception) for name in names]

        # Assert
        self.assertEqual(kinds, [True] * len(names))

    def test_it_defines_each_name_exactly_once(self) -> None:
        # Arrange
        named = defined_errors()

        # Act
        distinct = sorted(set(named))

        # Assert
        self.assertEqual(sorted(named), distinct)


class NoCycleTest(unittest.TestCase):
    def test_it_imports_nothing_from_its_own_package(self) -> None:
        # Arrange
        tree = ast.parse(SOURCE.read_text())

        # Act
        reached = imported_modules(tree)

        # Assert
        self.assertEqual([one for one in reached if one.startswith("tms9918")], [])

    def test_it_reaches_for_nothing_relative_either(self) -> None:
        # Arrange
        tree = ast.parse(SOURCE.read_text())

        # Act
        relative = [
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.level
        ]

        # Assert
        self.assertEqual(relative, [])


class RaisingTest(unittest.TestCase):
    def test_a_caller_can_catch_a_name_no_model_goes_by(self) -> None:
        # Arrange
        def attempt() -> Any:
            return tms9918.Chip("tms9938")

        # Act
        with self.assertRaises(tms9918.UnknownModelError) as raised:
            attempt()

        # Assert
        self.assertIn("tms9938", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
