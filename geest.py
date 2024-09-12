"""
GEEST Plugin

Author: Your Name
Copyright: 2024, Your Organization
License: GPL-3.0-only

This file is part of the GEEST QGIS Plugin. It is available under the terms of the GNU General Public License v3.0 only.
See the LICENSE file in the project root for more information.
"""

from PyQt5.QtWidgets import (
    QDockWidget,
    QTreeView,
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QPushButton,
    QWidget,
    QLabel,
    QProgressBar,
)
from PyQt5.QtCore import Qt
from PyQt5 import uic
from qgis.core import QgsApplication
from .tree_view_model import TreeViewModel
from .queue_manager import QueueManager


class GEEST:
    """
    The main plugin class for GEEST.

    Attributes:
        iface (QgisInterface): The QGIS interface.
        dock_widget (QDockWidget): The dock widget for the plugin.
        config_dialog (QDialog): The configuration dialog.
        tree_view (QTreeView): The tree view widget.
        model (TreeViewModel): The custom model for the tree view.
        action_button (QPushButton): The button to run or cancel the process.
        progress_label (QLabel): The label showing progress status.
        progress_bar (QProgressBar): The progress bar showing task completion.
        queue_manager (QueueManager): Manages task queue.
    """

    def __init__(self, iface):
        """
        Initializes the GEEST plugin.

        Args:
            iface (QgisInterface): The QGIS interface.
        """
        self.iface = iface
        self.dock_widget = None
        self.config_dialog = None
        self.tree_view = None
        self.model = None
        self.action_button = None
        self.progress_label = None
        self.progress_bar = None
        self.queue_manager = None

    def initGui(self):
        """
        Sets up the GUI for the plugin.
        """
        self.dock_widget = QDockWidget("GEEST", self.iface.mainWindow())
        container_widget = QWidget()
        layout = QVBoxLayout(container_widget)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)

        self.tree_view = QTreeView()
        self.tree_view.setItemDelegate(AnimatedIconDelegate(self.tree_view))
        scroll_area.setWidget(self.tree_view)

        layout.addWidget(scroll_area)

        self.action_button = QPushButton("Run")
        self.action_button.setEnabled(False)
        self.action_button.clicked.connect(self.on_action_button_clicked)
        layout.addWidget(self.action_button)

        self.progress_label = QLabel("0 tasks remaining")
        layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.dock_widget.setWidget(container_widget)
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dock_widget)

        schema_files = {
            "group": "path/to/group_schema.json",
            "factor": "path/to/factor_schema.json",
            "sub-factor": "path/to/sub_factor_schema.json",
        }

        self.model = TreeViewModel("path/to/your/json_file.json", schema_files)
        self.tree_view.setModel(self.model)

        self.model.layoutChanged.connect(self.update_action_button_state)

    def show_config_dialog(self, node_name):
        """
        Shows the configuration dialog for the selected node.

        Args:
            node_name (str): The name of the node for which the dialog is shown.
        """
        self.config_dialog = QDialog(self.iface.mainWindow())
        uic.loadUi("path/to/config_dialog.ui", self.config_dialog)

        # Set the banner text
        banner_label = self.config_dialog.findChild(QLabel, "bannerLabel")
        if banner_label:
            banner_label.setText(f"{node_name} Configuration")

        self.config_dialog.exec_()

    def on_node_clicked(self, index):
        """
        Handles node click events in the tree view.

        Args:
            index (QModelIndex): The index of the clicked node.
        """
        node_name = index.data()
        self.show_config_dialog(node_name)

    def on_action_button_clicked(self):
        """
        Handles the action button click event to run or cancel tasks.
        """
        if self.action_button.text() == "Run":
            self.run_tasks()
        else:
            self.cancel_tasks()

    def run_tasks(self):
        """
        Schedules tasks for each node and updates the UI for running tasks.
        """
        nodes = self.model.get_nodes()  # Implement a method to retrieve nodes
        self.queue_manager = QueueManager(nodes, self.model, self.update_progress)
        self.queue_manager.process_tasks()
        self.action_button.setText("Cancel")
        self.progress_bar.setMaximum(len(nodes))
        self.update_progress(0, len(nodes))

    def cancel_tasks(self):
        """
        Cancels all running tasks and updates the UI.
        """
        if self.queue_manager:
            self.queue_manager.cancel_tasks()
        self.action_button.setText("Run")
        self.progress_label.setText("Tasks cancelled")
        self.progress_bar.setValue(0)

    def update_progress(self, completed, total):
        """
        Updates the progress indicator and label.

        Args:
            completed (int): Number of completed tasks.
            total (int): Total number of tasks.
        """
        self.progress_label.setText(f"{total - completed} tasks remaining")
        self.progress_bar.setValue(completed)

        if completed == total:
            self.action_button.setText("Run")

    def update_action_button_state(self):
        """
        Updates the state of the action button based on the validation rules.
        """
        self.action_button.setEnabled(self.model.is_valid())

    def unload(self):
        """
        Unloads the plugin from QGIS.
        """
        self.iface.removeDockWidget(self.dock_widget)
