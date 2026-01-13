# -*- coding: utf-8 -*-
"""Study Area Report Generation Task.

This module contains the QgsTask for generating study area reports in the background.
"""
import os
import platform
import subprocess  # nosec B404

from qgis.core import Qgis, QgsTask

from geest.core.reports.study_area_report import StudyAreaReport
from geest.utilities import log_message


class StudyAreaReportTask(QgsTask):
    """Background task for study area report generation."""

    def __init__(self, working_dir: str, gpkg_path: str):
        """Initialize the task.

        Args:
            working_dir: Working directory where report will be saved.
            gpkg_path: Path to the GeoPackage file.
        """
        super().__init__("Generating Study Area Report", QgsTask.CanCancel)
        self.working_dir = working_dir
        self.gpkg_path = gpkg_path
        self.report_path = os.path.join(working_dir, "study_area_report.pdf")
        self.exception = None

    def run(self):
        """Generate the report in background thread.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            log_message("Starting study area report generation...", tag="Geest", level=Qgis.Info)

            report = StudyAreaReport(gpkg_path=self.gpkg_path, report_name="Study Area Summary")
            report.create_layout()
            report.export_pdf(self.report_path)

            log_message(
                f"Study area report generated successfully: {self.report_path}",
                tag="Geest",
                level=Qgis.Info,
            )
            return True

        except Exception as e:
            self.exception = e
            log_message(f"Error generating study area report: {e}", tag="Geest", level=Qgis.Critical)
            return False

    def finished(self, result: bool):
        """Called when task finishes (in main thread).

        Args:
            result: True if task succeeded, False otherwise.
        """
        if result:
            try:
                if os.name == "nt":
                    os.startfile(self.report_path)  # nosec B606
                else:
                    system = platform.system().lower()
                    if system == "darwin":
                        subprocess.run(["open", self.report_path], check=False)  # nosec B603 B607
                    else:
                        subprocess.run(["xdg-open", self.report_path], check=False)  # nosec B603 B607
            except Exception as e:
                log_message(f"Could not open PDF viewer: {e}", tag="Geest", level=Qgis.Warning)
        else:
            log_message("Study area report generation failed.", tag="Geest", level=Qgis.Critical)

    def cancel(self):
        """Called when task is cancelled."""
        log_message("Study area report generation cancelled.", tag="Geest", level=Qgis.Warning)
        super().cancel()
