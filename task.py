# -*- coding: utf-8 -*-
"""
GEOE3 Plugin

Author: Your Name
Copyright: 2024, Your Organization
License: GPL-3.0-only

This file is part of the GEOE3 QGIS Plugin. It is available under the terms of the GNU General Public License v3.0 only.
See the LICENSE file in the project root for more information.
"""

import os

from qgis.core import Qgis, QgsMessageLog, QgsTask
from qgis.PyQt.QtCore import pyqtSignal


class GeoE3Task(QgsTask):
    """
    Custom task for running GEOE3 plugin operations as a background job.
    """

    finished = pyqtSignal(bool)
    error = pyqtSignal()

    def __init__(self, description: str, node: dict):
        """🏗️ Initialize the instance.

        Args:
            description (str): Description of the task.
            node (dict): Node containing task data.
        """
        super().__init__(description)
        self.node = node

    def run(self) -> bool:
        """
        Executes the task. This is the main work method that performs the background operation.

        Returns:
            bool: True if task completed successfully, False otherwise.
        """
        try:
            output_path = self.node["output_path"]
            if self.node.get("processed", False) and os.path.exists(output_path):
                QgsMessageLog.logMessage(
                    f"{self.node['name']} already processed",
                    "GeoE3",
                    Qgis.Info,
                )
                self.finished.emit(True)
                return True

            # Simulate processing
            self.process_node()
            self.node["processed"] = True
            QgsMessageLog.logMessage(f"Processed {self.node['name']}", "GeoE3", Qgis.Info)
            self.finished.emit(True)
            return True
        except Exception as e:
            QgsMessageLog.logMessage(
                f"Task failed for {self.node['name']}: {str(e)}",
                "GeoE3",
                Qgis.Critical,
            )
            self.error.emit()
            return False

    def process_node(self) -> None:
        """
        Simulates the processing of the node.
        """
        output_path = self.node["output_path"]
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(f"Processed output for {self.node['name']}")

    def cancel(self) -> None:
        """
        Handles task cancellation.
        """
        QgsMessageLog.logMessage(f"{self.node['name']} task was cancelled", "GEOE3", Qgis.Info)
        super().cancel()
