"""
GEEST Plugin

Author: Your Name
Copyright: 2024, Your Organization
License: GPL-3.0-only

This file is part of the GEEST QGIS Plugin. It is available under the terms of the GNU General Public License v3.0 only.
See the LICENSE file in the project root for more information.
"""

from qgis.core import QgsTask, QgsMessageLog, Qgis
from PyQt5.QtCore import pyqtSignal
import os


class GEESTTask(QgsTask):
    """
    Custom task for running GEEST plugin operations as a background job.
    """

    finished = pyqtSignal(bool)
    error = pyqtSignal()

    def __init__(self, description, node):
        super().__init__(description)
        self.node = node

    def run(self):
        """
        Executes the task. This is the main work method that performs the background operation.
        """
        try:
            output_path = self.node["output_path"]
            if self.node.get("processed", False) and os.path.exists(output_path):
                QgsMessageLog.logMessage(
                    f"{self.node['name']} already processed",
                    "Geest",
                    Qgis.Info,
                )
                self.finished.emit(True)
                return True

            # Simulate processing
            self.process_node()
            self.node["processed"] = True
            QgsMessageLog.logMessage(
                f"Processed {self.node['name']}", "Geest", Qgis.Info
            )
            self.finished.emit(True)
            return True
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Task failed for {self.node['name']}: {str(e)}",
                "Geest",
                Qgis.Critical,
            )
            self.error.emit()
            return False

    def process_node(self):
        """
        Simulates the processing of the node.
        """
        output_path = self.node["output_path"]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(f"Processed output for {self.node['name']}")

    def cancel(self):
        """
        Handles task cancellation.
        """
        QgsMessageLog.logMessage(
            f"{self.node['name']} task was cancelled", "GEEST", Qgis.Info
        )
        super().cancel()
