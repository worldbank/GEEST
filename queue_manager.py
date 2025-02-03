"""
GEEST Plugin

Author: Your Name
Copyright: 2024, Your Organization
License: GPL-3.0-only

This file is part of the GEEST QGIS Plugin. It is available under the terms of the GNU General Public License v3.0 only.
See the LICENSE file in the project root for more information.
"""

from qgis.core import QgsApplication
from .task import GEESTTask


class QueueManager:
    """
    Manages the queue of tasks for processing GEEST nodes.
    """

    def __init__(self, nodes, model, progress_callback):
        self.nodes = nodes
        self.model = model
        self.progress_callback = progress_callback
        self.tasks = []
        self.completed_tasks = 0

    def generate_tasks(self):
        for node in self.nodes:
            task = GEESTTask(f"Processing {node['name']}", node)
            task.finished.connect(self.on_task_finished)
            task.error.connect(self.on_task_error)
            self.tasks.append(task)

    def process_tasks(self):
        self.generate_tasks()
        for task in self.tasks:
            self.model.update_node_status(task.node, "running")
            QgsApplication.taskManager().addTask(task)

    def cancel_tasks(self):
        for task in self.tasks:
            if not task.isCanceled():
                task.cancel()
            self.model.update_node_status(task.node, "idle")

    def on_task_finished(self, result):
        self.completed_tasks += 1
        status = "success" if result else "error"
        self.model.update_node_status(self.sender().node, status)
        self.progress_callback(self.completed_tasks, len(self.tasks))

    def on_task_error(self):
        self.completed_tasks += 1
        self.model.update_node_status(self.sender().node, "error")
        self.progress_callback(self.completed_tasks, len(self.tasks))
