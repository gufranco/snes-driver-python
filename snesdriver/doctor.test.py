import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from snesdriver import doctor, walk, windows


class Complaint(Exception):
    pass


def a_directory(names: tuple[str, ...] = ()) -> Path:
    where = Path(tempfile.mkdtemp())
    for name in names:
        (where / name).write_bytes(b"\x00" * 16)
    return where


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


class PythonTest(unittest.TestCase):
    def test_it_reports_the_python_it_is_running_on(self) -> None:
        one = doctor._python()

        self.assertTrue(one.ok, one.detail)

    def test_and_names_the_package(self) -> None:
        one = doctor._package()

        self.assertEqual(one.name, "snesdriver")


class WindowTest(unittest.TestCase):
    def test_every_published_pair_has_a_window(self) -> None:
        unwell = [
            f"{part} under {layout}"
            for part, layouts in windows.WINDOWS.items()
            for layout in layouts
            if not doctor._window(part, layout).ok
        ]

        self.assertEqual(unwell, [])

    def test_the_version_is_read_out_of_the_file_rather_than_imported(self) -> None:
        from snesdriver.version import VERSION

        self.assertEqual(doctor.VERSION, VERSION)

    def test_a_version_file_naming_nothing_reads_as_unknown(self) -> None:
        where = Path(tempfile.mkdtemp()) / "version.py"
        where.write_text("NOTHING = 1\n")

        self.assertEqual(doctor._version(where), "unknown")

    def test_a_pair_with_no_window_is_reported_as_a_defect_here(self) -> None:
        one = doctor._window("dsp", "exhirom")

        self.assertFalse(one.ok, one.detail)

    def test_and_a_part_the_package_refuses_reports_what_it_said(self) -> None:
        one = doctor._window("no such part", "lorom")

        self.assertIn("UnknownPart", one.detail)


class WalkingTest(unittest.TestCase):
    def test_a_conversation_is_walked_out_of_bytes_assembled_here(self) -> None:
        one = doctor._walking()

        self.assertTrue(one.ok, one.detail)

    def test_the_routine_it_assembles_stores_into_the_window(self) -> None:
        found = windows.window_for(doctor.PROBE_PART, doctor.PROBE_LAYOUT)
        assert found is not None

        held = doctor._routine(found)

        self.assertIn(found.data & 0xFF, held)

    def test_a_walker_that_refuses_is_reported_as_what_it_said(self) -> None:
        def refuse(*_: Any, **__: Any) -> Any:
            raise Complaint("no")

        with unittest.mock.patch.object(walk, "through", refuse):
            one = doctor._walking()

        self.assertIn("Complaint", one.detail)

    def test_and_a_routine_that_walks_to_nothing_is_not_well(self) -> None:
        with unittest.mock.patch.object(walk, "through", lambda *_, **__: iter(())):
            one = doctor._walking()

        self.assertFalse(one.ok, one.detail)


class SubmoduleTest(unittest.TestCase):
    def test_every_submodule_this_repository_carries_is_checked_out(self) -> None:
        absent = [name for name in doctor.SUBMODULES if not doctor._submodule(name).ok]

        self.assertEqual(absent, [])

    def test_a_submodule_that_is_not_there_is_reported(self) -> None:
        one = doctor._submodule("absent", Path(tempfile.mkdtemp()))

        self.assertIn("is not there", one.detail)

    def test_a_directory_git_left_empty_is_reported_as_empty(self) -> None:
        where = Path(tempfile.mkdtemp())
        (where / "hollow").mkdir()

        one = doctor._submodule("hollow", where)

        self.assertIn("is empty", one.detail)

    def test_and_neither_is_well_because_the_checks_will_skip(self) -> None:
        one = doctor._submodule("absent", Path(tempfile.mkdtemp()))

        self.assertFalse(one.ok)


class ManifestTest(unittest.TestCase):
    def test_the_manifest_beside_the_package_names_cartridges(self) -> None:
        one = doctor._manifest()

        self.assertTrue(one.ok, one.detail)

    def test_a_manifest_that_is_not_there_is_reported(self) -> None:
        one = doctor._manifest(Path(tempfile.mkdtemp()) / "absent.json")

        self.assertFalse(one.ok)

    def test_a_manifest_that_is_not_json_is_reported_differently(self) -> None:
        one = doctor._manifest(a_file("{"))

        self.assertIn("not readable as JSON", one.detail)

    def test_a_manifest_naming_nothing_is_not_well(self) -> None:
        one = doctor._manifest(a_file('{"cartridges": []}'))

        self.assertFalse(one.ok)


class LookingTest(unittest.TestCase):
    def test_a_named_directory_is_reported_as_named(self) -> None:
        found = doctor._looking({doctor.DIRECTORY_VARIABLE: "/somewhere"})

        self.assertIn("set to /somewhere", found[0].detail)

    def test_and_it_is_the_one_chosen_even_when_it_is_not_there(self) -> None:
        found = doctor._looking({doctor.DIRECTORY_VARIABLE: "/somewhere"})

        self.assertEqual(found[-1].detail, "/somewhere")

    def test_an_unset_variable_says_the_places_are_tried_in_order(self) -> None:
        found = doctor._looking({})

        self.assertIn("tried in order", found[0].detail)

    def test_and_the_chosen_place_is_one_of_the_places_looked_in(self) -> None:
        found = doctor._looking({})

        self.assertIn(found[-1].detail, found[1].detail)

    def test_the_real_environment_is_read_when_none_is_given(self) -> None:
        found = doctor._looking()

        self.assertEqual(len(found), 3)

    def test_the_default_is_chosen_when_no_place_exists(self) -> None:
        held = Path(tempfile.mkdtemp()) / "absent"
        with (
            unittest.mock.patch.object(doctor, "DEFAULT_DIRECTORY", held),
            unittest.mock.patch.object(doctor, "ALONGSIDE", held),
        ):
            found = doctor._looking({})

        self.assertEqual(found[-1].detail, str(held))


class LibraryTest(unittest.TestCase):
    def test_a_library_that_is_not_there_is_reported_as_absent_not_broken(self) -> None:
        one = doctor._library(Path(tempfile.mkdtemp()) / "absent")

        self.assertTrue(one.ok, one.detail)

    def test_and_says_the_check_against_cartridges_will_skip(self) -> None:
        one = doctor._library(Path(tempfile.mkdtemp()) / "absent")

        self.assertIn("skip rather than run", one.detail)

    def test_a_library_holding_images_counts_them(self) -> None:
        one = doctor._library(a_directory(("a.sfc", "b.smc")))

        self.assertIn("2 images", one.detail)

    def test_and_is_well(self) -> None:
        one = doctor._library(a_directory(("a.sfc",)))

        self.assertTrue(one.ok, one.detail)

    def test_a_directory_that_is_there_and_empty_is_not_well(self) -> None:
        one = doctor._library(a_directory())

        self.assertFalse(one.ok, one.detail)

    def test_because_that_is_what_a_run_over_nothing_looks_like(self) -> None:
        one = doctor._library(a_directory(("notes.txt",)))

        self.assertIn("holds nothing", one.detail)

    def test_a_library_that_cannot_be_read_is_reported_as_what_it_said(self) -> None:
        where = a_directory()

        def refuse(*_: Any, **__: Any) -> Any:
            raise OSError("permission denied")

        with unittest.mock.patch.object(Path, "rglob", refuse):
            one = doctor._library(where)

        self.assertIn("permission denied", one.detail)


class ExamineTest(unittest.TestCase):
    def test_the_examination_produces_findings(self) -> None:
        found = doctor.examine()

        self.assertTrue(all(isinstance(one, doctor.Finding) for one in found))

    def test_it_looks_at_every_published_part_under_every_layout(self) -> None:
        named = {one.name for one in doctor.examine()}
        wanted = {
            f"{part} under {layout}"
            for part, layouts in windows.WINDOWS.items()
            for layout in layouts
        }

        self.assertTrue(wanted <= named, named)

    def test_and_at_the_library_last_because_that_is_the_answer(self) -> None:
        found = doctor.examine()

        self.assertEqual(found[-1].name, "library")


class ImportFailureTest(unittest.TestCase):
    def test_a_package_that_will_not_import_is_reported_as_one_finding(self) -> None:
        def refuse() -> Any:
            raise Complaint("no")

        with unittest.mock.patch.object(doctor, "_loaded", refuse):
            named = [one.name for one in doctor.examine() if one.name == "windows"]

        self.assertEqual(named, ["windows"])

    def test_and_the_pairs_below_it_are_not_reported_at_all(self) -> None:
        def refuse() -> Any:
            raise Complaint("no")

        with unittest.mock.patch.object(doctor, "_loaded", refuse):
            found = doctor.examine()

        self.assertEqual([one for one in found if " under " in one.name], [])

    def test_the_repository_is_put_on_the_path_when_it_is_not_already_there(self) -> None:
        held = [one for one in sys.path if one != str(doctor.ROOT)]

        with unittest.mock.patch.object(sys, "path", held):
            doctor._loaded()

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
        """A report, not a verdict that the machine is well.

        Asserting a clean exit here would make the suite require exactly the
        machine the doctor exists to report on. CI has no cartridges, and a
        doctor that says so is working. What has to hold on every machine is
        that it examines everything and prints a line for each finding.
        """
        said: list[str] = []

        code = doctor.main((), doctor.examine, said.append)

        self.assertIn(code, (0, 1))
        self.assertGreaterEqual(len(said), len(doctor.examine()))


if __name__ == "__main__":
    unittest.main()
