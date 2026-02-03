# -*- coding: utf-8 -*-
"""Analysis Report Generation Task.

This module contains the QgsTask for generating analysis reports in the background.
"""

import os
import platform
import subprocess  # nosec B404

from qgis.core import Qgis, QgsTask

from geest.core.reports.analysis_report import AnalysisReport
from geest.utilities import log_message


class AnalysisReportTask(QgsTask):
    """Background task for analysis report generation."""

    def __init__(self, working_dir: str, model_path: str):
        """Initialize the task.

        Args:
            working_dir: Working directory where report will be saved.
            model_path: Path to the model JSON file.
        """
        super().__init__("Generating Analysis Report", QgsTask.CanCancel)
        self.working_dir = working_dir
        self.model_path = model_path
        self.pdf_path = os.path.join(working_dir, "analysis_report.pdf")
        self.qpt_path = os.path.join(working_dir, "analysis_report.qpt")
        self.exception = None

    def run(self):
        """Generate the report in background thread.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            log_message("Starting analysis report generation...", tag="Geest", level=Qgis.Info)

            report = AnalysisReport(
                model_path=self.model_path,
                working_directory=self.working_dir,
                report_name="Study Area Summary",
            )
            report.create_layout()
            report.export_pdf(self.pdf_path)
            report.export_qpt(self.qpt_path)

            log_message(
                f"Analysis report generated successfully: {self.pdf_path}",
                tag="Geest",
                level=Qgis.Info,
            )
            return True

        except Exception as e:
            self.exception = e
            log_message(f"Error generating analysis report: {e}", tag="Geest", level=Qgis.Critical)
            return False

    def finished(self, result: bool):
        """Called when task finishes (in main thread).

        Args:
            result: True if task succeeded, False otherwise.
        """
        if result:
            try:
                # Open the PDF using the system PDF viewer
                if os.name == "nt":  # Windows
                    os.startfile(self.pdf_path)  # nosec B606
                else:  # macOS and Linux
                    system = platform.system().lower()
                    if system == "darwin":  # macOS
                        subprocess.run(["open", self.pdf_path], check=False)  # nosec B603 B607
                    else:  # Linux
                        subprocess.run(["xdg-open", self.pdf_path], check=False)  # nosec B603 B607
            except Exception as e:
                log_message(f"Could not open PDF viewer: {e}", tag="Geest", level=Qgis.Warning)
        else:
            log_message("Analysis report generation failed.", tag="Geest", level=Qgis.Critical)

    def cancel(self):
        """Called when task is cancelled."""
        log_message("Analysis report generation cancelled.", tag="Geest", level=Qgis.Warning)
        super().cancel()
