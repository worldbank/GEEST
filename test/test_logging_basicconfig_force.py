# -*- coding: utf-8 -*-
"""Regression test: geest/__init__.py's logging.basicConfig() must always win.

logging.basicConfig() is a no-op if the root logger already has handlers
attached - and by the time geest/__init__.py calls it, it already does:
the .core/.gui/.gui.overlays/.utilities imports immediately above it
transitively load grid_column_utils.py, whose module-level log_message()
banner call is, if verbose_mode is on, the first logging.info/warning()
call in the process - which implicitly self-configures the root logger
with the bare stderr "lastResort" handler before geest/__init__.py's own
explicit basicConfig() call ever runs. Without force=True, that explicit
call silently does nothing, so nothing ever reaches the configured log
file (worldbank/GeoE3 field report, 2026-10-23: "my expectation is that
logs will be written to ~/GEOE3.log").

This test exercises the exact mechanism (not geest/__init__.py itself,
which already ran its own module-level logging setup once at process
import time, with no QGIS dependency, so it stays independent of the
Docker/QGIS test harness) and proves force=True restores control of the
root logger regardless of what configured it first.
"""
import logging
import os
import tempfile
import unittest


class TestBasicConfigForceOverridesPriorHandlers(unittest.TestCase):
    def setUp(self):
        self._original_handlers = list(logging.root.handlers)
        self._original_level = logging.root.level
        for handler in list(logging.root.handlers):
            logging.root.removeHandler(handler)

        self.temp_dir = tempfile.mkdtemp(prefix="test_logging_force_")
        self.log_path = os.path.join(self.temp_dir, "test.log")

    def tearDown(self):
        for handler in list(logging.root.handlers):
            logging.root.removeHandler(handler)
            handler.close()
        for handler in self._original_handlers:
            logging.root.addHandler(handler)
        logging.root.setLevel(self._original_level)

    def test_without_force_a_prior_handler_silently_blocks_ours(self):
        """Demonstrates the bug: simulate the implicit self-configuration
        (a bare logging.warning() call with zero handlers present) that
        happens when grid_column_utils' module-level banner fires before
        our own basicConfig() - then show a plain basicConfig() call
        afterward does nothing."""
        logging.warning("simulated: some import-time call before our own basicConfig()")
        self.assertTrue(logging.root.handlers, "the implicit self-configuration should have attached a handler")

        logging.basicConfig(filename=self.log_path, filemode="a", level=logging.DEBUG)

        self.assertFalse(
            os.path.exists(self.log_path),
            "without force=True, basicConfig() must be a no-op here - proving the bug this test guards against",
        )

    def test_with_force_our_file_handler_always_wins(self):
        logging.warning("simulated: some import-time call before our own basicConfig()")
        self.assertTrue(logging.root.handlers)

        logging.basicConfig(
            filename=self.log_path,
            filemode="a",
            format="%(asctime)s [%(levelname)s] %(message)s",
            level=logging.DEBUG,
            force=True,
        )
        logging.info("this must land in the file")

        self.assertTrue(os.path.exists(self.log_path), "force=True must make our FileHandler take effect")
        with open(self.log_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("this must land in the file", content)


if __name__ == "__main__":
    unittest.main()
