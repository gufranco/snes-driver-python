import subprocess
import sys
import tempfile
import types
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import snesdriver
from snesdriver import doctor


class Complaint(Exception):
    pass


def a_file(body: str) -> Path:
    where = Path(tempfile.mkdtemp()) / "held.json"
    where.write_text(body)
    return where


class FindingTest(unittest.TestCase):
    def test_a_finding_says_what_was_checked(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertEqual(one.name, "python")

    def test_a_healthy_finding_prints_with_a_mark_that_says_so(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertIn("ok", one.line)

    def test_and_an_unhealthy_one_prints_differently(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertNotIn("ok", one.line)

    def test_an_unhealthy_finding_says_what_to_do_about_it(self) -> None:
        one = doctor.Finding("python", False, "3.9", "upgrade")

        self.assertIn("upgrade", one.report)

    def test_a_healthy_one_keeps_its_advice_to_itself(self) -> None:
        one = doctor.Finding("python", True, "3.14", "upgrade")

        self.assertNotIn("upgrade", one.report)

    def test_and_so_does_an_unhealthy_one_with_none_to_give(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertEqual(one.report, one.line)

    def test_a_finding_prints_as_itself(self) -> None:
        one = doctor.Finding("python", False, "3.9")

        self.assertEqual(repr(one), "<Finding python not ok>")

    def test_and_says_so_when_it_is_well(self) -> None:
        one = doctor.Finding("python", True, "3.14")

        self.assertEqual(repr(one), "<Finding python ok>")


def refusing(*_: Any, **__: Any) -> Any:
    raise Complaint("no")


def loading(walk: Any = None, windows: Any = snesdriver) -> Any:
    return lambda: (walk if walk is not None else snesdriver, windows)


class PythonTest(unittest.TestCase):
    def test_it_reports_the_python_it_is_running_on(self) -> None:
        # Arrange
        oldest = doctor.OLDEST_PYTHON

        # Act
        one = doctor.check_python()

        # Assert
        self.assertEqual(one.ok, sys.version_info[:2] >= oldest, one.detail)

    def test_and_names_the_package_with_its_version(self) -> None:
        # Arrange
        version = snesdriver.VERSION

        # Act
        one = doctor.check_package()

        # Assert
        self.assertEqual((one.name, one.detail), ("snesdriver", f"version {version}"))


class WindowTest(unittest.TestCase):
    def test_every_published_pair_has_a_window(self) -> None:
        # Arrange
        pairs = [
            (part, layout) for part, layouts in snesdriver.WINDOWS.items() for layout in layouts
        ]

        # Act
        unwell = [pair for pair in pairs if not doctor.check_window(*pair).ok]

        # Assert
        self.assertEqual(unwell, [])

    def test_a_window_is_described_by_its_banks_and_registers(self) -> None:
        # Arrange
        part, layout = "dsp", "hirom"

        # Act
        one = doctor.check_window(part, layout)

        # Assert
        self.assertEqual(one.detail, "banks 0x00 to 0x0f, data 0x6000, status 0x7000")

    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        # Arrange
        where = Path(doctor.__file__).resolve().parent / "version.py"

        # Act
        found = doctor.installed_version(where)

        # Assert
        self.assertEqual((found, doctor.VERSION), (snesdriver.VERSION, snesdriver.VERSION))

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        # Act
        found = doctor.installed_version(where)

        # Assert
        self.assertEqual(found, "unknown")

    def test_a_pair_with_no_window_is_reported_as_a_defect_here(self) -> None:
        # Arrange
        part, layout = "dsp", "exhirom"

        # Act
        one = doctor.check_window(part, layout)

        # Assert
        self.assertEqual(
            (one.ok, one.detail), (False, "no window, and every published pair should have one")
        )

    def test_and_a_part_the_package_refuses_reports_what_it_said(self) -> None:
        # Arrange
        part = "no such part"

        # Act
        one = doctor.check_window(part, "lorom")

        # Assert
        self.assertEqual((one.ok, one.detail.split(":")[0]), (False, "UnknownPart"))


class WalkingTest(unittest.TestCase):
    def test_a_conversation_is_walked_out_of_bytes_assembled_here(self) -> None:
        # Arrange
        part, layout = doctor.PROBE_PART, doctor.PROBE_LAYOUT

        # Act
        one = doctor.check_walking(part, layout)

        # Assert
        self.assertEqual((one.ok, one.detail), (True, "4 steps read out of 9 bytes assembled here"))

    def test_the_routine_it_assembles_stores_to_data_and_polls_status(self) -> None:
        # Arrange
        window = snesdriver.WINDOWS["dsp"]["lorom"]

        # Act
        held = doctor.probe_routine(window)

        # Assert
        self.assertEqual(held, bytes((0xA9, 0x42, 0x8D, 0x00, 0x80, 0xAD, 0x00, 0xC0, 0x60)))

    def test_a_walker_that_refuses_is_reported_as_what_it_said(self) -> None:
        # Arrange
        load = loading(walk=types.SimpleNamespace(through=refusing))

        # Act
        one = doctor.check_walking(load=load)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, "Complaint: no"))

    def test_and_a_routine_that_walks_to_nothing_is_not_well(self) -> None:
        # Arrange
        load = loading(walk=types.SimpleNamespace(through=lambda *_, **__: iter(())))

        # Act
        one = doctor.check_walking(load=load)

        # Assert
        self.assertEqual(
            (one.ok, one.detail), (False, "0 steps read out of 9 bytes assembled here")
        )

    def test_and_a_part_with_no_window_under_the_layout_is_not_walked(self) -> None:
        # Arrange
        layout = "exhirom"

        # Act
        one = doctor.check_walking(layout=layout)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, "no dsp window under exhirom"))


class SubmoduleTest(unittest.TestCase):
    def test_every_submodule_this_repository_carries_is_checked_out(self) -> None:
        # Arrange
        names = doctor.SUBMODULES

        # Act
        absent = [name for name in names if not doctor.check_submodule(name).ok]

        # Assert
        self.assertEqual(absent, [])

    def test_a_submodule_that_is_not_there_is_reported_and_not_well(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())

        # Act
        one = doctor.check_submodule("absent", where)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, f"{where / 'absent'} is not there"))

    def test_a_directory_git_left_empty_is_reported_as_empty(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        (where / "hollow").mkdir()

        # Act
        one = doctor.check_submodule("hollow", where)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, f"{where / 'hollow'} is empty"))


class ManifestTest(unittest.TestCase):
    def test_the_manifest_beside_the_package_names_cartridges(self) -> None:
        # Arrange
        where = doctor.MANIFEST

        # Act
        one = doctor.check_manifest(where)

        # Assert
        self.assertTrue(one.ok, one.detail)

    def test_a_manifest_that_is_not_there_is_reported(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "absent.json"

        # Act
        one = doctor.check_manifest(where)

        # Assert
        self.assertEqual((one.ok, one.detail.startswith("could not be read")), (False, True))

    def test_a_manifest_that_is_not_json_is_reported_differently(self) -> None:
        # Arrange
        where = a_file("{")

        # Act
        one = doctor.check_manifest(where)

        # Assert
        self.assertEqual((one.ok, one.detail.startswith("is not readable as JSON")), (False, True))

    def test_a_manifest_naming_nothing_is_not_well(self) -> None:
        # Arrange
        where = a_file('{"cartridges": []}')

        # Act
        one = doctor.check_manifest(where)

        # Assert
        self.assertEqual((one.ok, one.detail), (False, "0 cartridges named"))


class ExamineTest(unittest.TestCase):
    def test_it_looks_at_every_published_part_under_every_layout_then_the_library(self) -> None:
        # Arrange
        wanted = {
            f"{part} under {layout}"
            for part, layouts in snesdriver.WINDOWS.items()
            for layout in layouts
        }

        # Act
        found = doctor.examine()

        # Assert
        self.assertEqual((wanted <= {one.name for one in found}, found[-1].name), (True, "library"))


class ImportFailureTest(unittest.TestCase):
    def test_a_package_that_will_not_import_is_reported_as_one_finding(self) -> None:
        # Arrange
        load = refusing

        # Act
        found = doctor.examine(load=load)

        # Assert
        self.assertEqual([one.detail for one in found if one.name == "windows"], ["Complaint: no"])

    def test_and_the_pairs_below_it_are_not_reported_at_all(self) -> None:
        # Arrange
        load = refusing

        # Act
        found = doctor.examine(load=load)

        # Assert
        self.assertEqual([one for one in found if " under " in one.name], [])

    def test_every_model_is_put_on_the_path_when_none_of_them_is_there(self) -> None:
        # Arrange
        wanted = {str(doctor.ROOT / one) for one in doctor.SUBMODULES}
        held = [one for one in sys.path if one not in wanted and one != str(doctor.ROOT)]

        # Act
        with unittest.mock.patch.object(sys, "path", held):
            doctor.load_modules()

        # Assert
        self.assertEqual(wanted - set(held), set())

    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        # Arrange
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        # Act
        with unittest.mock.patch.object(sys, "path", held):
            doctor.load_modules()

        # Assert
        self.assertIn(str(doctor.ROOT), held)


class ReportTest(unittest.TestCase):
    def test_a_clean_examination_says_there_is_nothing_to_report(self) -> None:
        lines = doctor.report([doctor.Finding("one", True, "fine")])

        self.assertIn("nothing to report", lines[-1])

    def test_and_a_dirty_one_counts_what_did_not_pass(self) -> None:
        lines = doctor.report(
            [doctor.Finding("one", True, "fine"), doctor.Finding("two", False, "not")]
        )

        self.assertIn("1 of 2", lines[-1])


class MainTest(unittest.TestCase):
    def test_a_clean_machine_exits_zero(self) -> None:
        code = doctor.main((), lambda: [doctor.Finding("one", True, "fine")], lambda _: None)

        self.assertEqual(code, 0)

    def test_and_a_machine_with_a_finding_exits_one(self) -> None:
        code = doctor.main((), lambda: [doctor.Finding("one", False, "not")], lambda _: None)

        self.assertEqual(code, 1)

    def test_the_report_is_said_rather_than_returned(self) -> None:
        said: list[str] = []

        doctor.main((), lambda: [doctor.Finding("one", True, "fine")], said.append)

        self.assertTrue(any("nothing to report" in one for one in said))

    def test_it_runs_end_to_end_whatever_this_machine_holds(self) -> None:
        said: list[str] = []

        code = doctor.main((), doctor.examine, said.append)

        self.assertIn(code, (0, 1))
        self.assertGreaterEqual(len(said), len(doctor.examine()))


class RunAsTheReadmeSaysTest(unittest.TestCase):
    def test_run_as_a_file_from_outside_the_repository_it_reports_rather_than_raises(
        self,
    ) -> None:
        # Arrange
        script = Path(doctor.__file__).resolve()
        outside = tempfile.mkdtemp()

        # Act
        finished = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            check=False,
            text=True,
            cwd=outside,
            timeout=120,
        )

        # Assert
        self.assertEqual(finished.stderr, "")
        self.assertIn(finished.returncode, (0, 1))
        self.assertRegex(finished.stdout.splitlines()[-1], r"checks(, nothing to report| did not)")


if __name__ == "__main__":
    unittest.main()
