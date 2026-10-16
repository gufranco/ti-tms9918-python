import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ast  # noqa: E402
import unittest  # noqa: E402

import tms9918  # noqa: E402
from tms9918 import errors  # noqa: E402

SOURCE = ROOT / "tms9918" / "errors.py"


def defined_errors() -> list[str]:
    return [
        name
        for name in dir(errors)
        if not name.startswith("_")
        and isinstance(getattr(errors, name), type)
        and issubclass(getattr(errors, name), Exception)
    ]


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
        module = errors

        # Act
        found = defined_errors()

        # Assert
        self.assertGreater(len(found), 0, module.__name__)

    def test_every_error_it_defines_is_exported_from_the_package(self) -> None:
        # Arrange
        exported = tms9918.__all__

        # Act
        missing = [name for name in defined_errors() if name not in exported]

        # Assert
        self.assertEqual(missing, [])

    def test_the_package_exports_the_class_and_not_a_name_that_shadows_it(self) -> None:
        # Arrange
        names = defined_errors()

        # Act
        rebound = [
            name for name in names if getattr(tms9918, name, None) is not getattr(errors, name)
        ]

        # Assert
        self.assertEqual(rebound, [])

    def test_it_defines_each_name_exactly_once(self) -> None:
        # Arrange
        tree = ast.parse(SOURCE.read_text())

        # Act
        named = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]

        # Assert
        self.assertEqual(sorted(named), sorted(set(named)))


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
        name = "tms9938"

        # Act
        attempt = lambda: tms9918.Chip(name)  # noqa: E731

        # Assert
        self.assertRaises(errors.UnknownModelError, attempt)


if __name__ == "__main__":
    unittest.main()
