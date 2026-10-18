# -*- coding: utf-8 -*-
"""Opening documents/folders must never block the QGIS main thread.

subprocess.run(['xdg-open', pdf]) on the main thread freezes the QGIS
event loop until the viewer exits (the UI appears focus-locked behind the
viewer), and force-closing the viewer can take the whole process group —
QGIS included — down with it. Every open-with-system-handler call must go
through geest.utilities.open_with_system_handler, which launches the
handler detached in its own session.
"""

import os
import re
import unittest
from unittest import mock

from geest import utilities
from geest.utilities import open_with_system_handler

PACKAGE_ROOT = os.path.dirname(os.path.abspath(utilities.__file__))

BLOCKING_OPEN_RE = re.compile(r"subprocess\.run\(\s*\[\s*\"(?:xdg-open|open)\"")
STARTFILE_RE = re.compile(r"os\.startfile\(")


def _python_sources():
    for root, dirs, files in os.walk(PACKAGE_ROOT):
        dirs[:] = [d for d in dirs if d not in {"__pycache__", "extlibs"}]
        for name in files:
            if name.endswith(".py"):
                yield os.path.join(root, name)


class TestOpenWithSystemHandler(unittest.TestCase):
    def test_launches_detached_in_new_session(self):
        """The handler is spawned with Popen in its own session, not run()."""
        with mock.patch.object(utilities.subprocess, "Popen") as popen:
            with mock.patch.object(utilities.os, "name", "posix"):
                open_with_system_handler("/tmp/report.pdf")  # nosec B108
        popen.assert_called_once()
        args, kwargs = popen.call_args
        self.assertIn(args[0][0], ("xdg-open", "open"))
        self.assertEqual(args[0][1], "/tmp/report.pdf")  # nosec B108
        self.assertTrue(kwargs.get("start_new_session"), "viewer must not join QGIS's process group")

    def test_never_raises(self):
        """A failing launcher degrades to a log message, never an exception."""
        with mock.patch.object(utilities.subprocess, "Popen", side_effect=OSError("no xdg-open")):
            with mock.patch.object(utilities.os, "name", "posix"):
                open_with_system_handler("/tmp/report.pdf")  # nosec B108

    def test_keeps_a_reference_to_the_launched_process(self):
        """The Popen object must not be discarded immediately.

        Letting it go out of scope right away makes it eligible for GC
        while the detached viewer is often still open, which triggers a
        spurious "subprocess is still running" ResourceWarning.
        """
        utilities._detached_processes.clear()
        fake_process = mock.Mock(poll=mock.Mock(return_value=None))
        with mock.patch.object(utilities.subprocess, "Popen", return_value=fake_process):
            with mock.patch.object(utilities.os, "name", "posix"):
                open_with_system_handler("/tmp/report.pdf")  # nosec B108
        self.assertIn(fake_process, utilities._detached_processes)

    def test_finished_processes_are_pruned_on_next_call(self):
        """A process that has already exited must not linger in the list forever."""
        utilities._detached_processes.clear()
        finished_process = mock.Mock(poll=mock.Mock(return_value=0))
        utilities._detached_processes.append(finished_process)
        new_process = mock.Mock(poll=mock.Mock(return_value=None))
        with mock.patch.object(utilities.subprocess, "Popen", return_value=new_process):
            with mock.patch.object(utilities.os, "name", "posix"):
                open_with_system_handler("/tmp/report.pdf")  # nosec B108
        self.assertNotIn(finished_process, utilities._detached_processes)
        self.assertIn(new_process, utilities._detached_processes)

    def test_no_blocking_open_calls_in_package(self):
        """No file may open documents with blocking subprocess.run/startfile.

        os.startfile is only legitimate inside utilities.py (it is
        non-blocking on Windows); subprocess.run with xdg-open/open is
        never legitimate.
        """
        offenders = []
        for path in _python_sources():
            with open(path, "r", encoding="utf-8") as handle:
                source = handle.read()
            rel = os.path.relpath(path, PACKAGE_ROOT)
            if BLOCKING_OPEN_RE.search(source):
                offenders.append(f"{rel}: blocking subprocess.run open call")
            if rel != "utilities.py" and STARTFILE_RE.search(source):
                offenders.append(f"{rel}: os.startfile outside utilities.open_with_system_handler")
        self.assertEqual(offenders, [], "Use geest.utilities.open_with_system_handler:\n" + "\n".join(offenders))


if __name__ == "__main__":
    unittest.main()
