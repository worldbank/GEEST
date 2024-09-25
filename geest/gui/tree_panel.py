import json
import os
from qgis.PyQt.QtWidgets import (
    QDockWidget,
    QTreeView,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QMenu,
    QAction,
    QMessageBox,
    QFileDialog,
    QHeaderView,
    QTreeView,
    QMenu,
    QCheckBox,  # Add QCheckBox for Edit Toggle
)
from qgis.PyQt.QtCore import QPoint, Qt, QTimer
from qgis.PyQt.QtGui import QMovie
from qgis.core import QgsMessageLog, Qgis, QgsLogger
from .geest_treeview import CustomTreeView, JsonTreeModel
from .setup_panel import SetupPanel
from .layer_detail_dialog import LayerDetailDialog
from geest.utilities import resources_path
from geest.core import set_setting, setting
from geest.core.workflow_queue_manager import WorkflowQueueManager


class TreePanel(QWidget):
    def __init__(self, parent=None, json_file=None):
        super().__init__(parent)

        # Initialize the QueueManager
        self.queue_manager = WorkflowQueueManager(pool_size=1)

        self.json_file = json_file
        self.tree_view_visible = True

        layout = QVBoxLayout()

        if json_file:
            # Load JSON data
            self.load_json()
        else:
            self.json_data = {"dimensions": []}

        # Create a CustomTreeView widget to handle editing and reverts
        self.treeView = CustomTreeView()
        self.treeView.setDragDropMode(QTreeView.InternalMove)
        self.treeView.setDefaultDropAction(Qt.MoveAction)

        # Create a model for the QTreeView using custom JsonTreeModel
        self.model = JsonTreeModel(self.json_data)
        self.treeView.setModel(self.model)

        # Only allow editing on double-click (initially enabled)
        self.treeView.setEditTriggers(QTreeView.DoubleClicked)

        # Enable custom context menu
        self.treeView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeView.customContextMenuRequested.connect(self.open_context_menu)

        # Expand the whole tree by default
        self.treeView.expandAll()

        # Set the second and third columns to the exact width of the 🔴 character and weighting
        self.treeView.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.treeView.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # Expand the first column to use the remaining space and resize with the dialog
        self.treeView.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.treeView.header().setStretchLastSection(False)

        # Set layout
        layout.addWidget(self.treeView)

        button_bar = QHBoxLayout()

        # "Add Dimension" button (initially enabled)
        self.add_dimension_button = QPushButton("⭐️ Add Dimension")
        self.add_dimension_button.clicked.connect(self.add_dimension)

        # Load and Save buttons
        self.load_json_button = QPushButton("📂 Load")
        self.load_json_button.clicked.connect(self.load_json_from_file)

        self.export_json_button = QPushButton("💾 Save")
        self.export_json_button.clicked.connect(self.export_json_to_file)

        # Prepare the throbber for the button (hidden initially)
        self.prepare_throbber = QLabel(self)
        movie = QMovie(resources_path("resources", "throbber-small.gif"))
        self.prepare_throbber.setMovie(movie)
        self.prepare_throbber.setVisible(False)  # Hide initially
        button_bar.addWidget(self.prepare_throbber)

        self.prepare_button = QPushButton("▶️ Prepare")
        self.prepare_button.clicked.connect(self.process_leaves)
        movie.start()

        # Add Edit Toggle checkbox
        self.edit_toggle = QCheckBox("Edit")
        self.edit_toggle.setChecked(False)
        self.edit_toggle.stateChanged.connect(self.toggle_edit_mode)
        edit_mode = int(setting(key="edit_mode", default=0))
        if edit_mode:
            self.edit_toggle.setVisible(True)
        else:
            self.edit_toggle.setVisible(False)

        button_bar.addWidget(self.add_dimension_button)
        button_bar.addStretch()

        button_bar.addWidget(self.prepare_button)
        button_bar.addStretch()

        button_bar.addWidget(self.load_json_button)
        button_bar.addWidget(self.export_json_button)
        button_bar.addWidget(self.edit_toggle)  # Add the edit toggle
        layout.addLayout(button_bar)
        self.setLayout(layout)

    def edit(self, index, trigger, event):
        """
        Override the edit method to enable editing only on the column that was clicked.
        """
        # Get the column that was clicked
        column = index.column()

        # Only allow editing on specific columns (e.g., column 0, 1, etc.)
        if column == 0:  # Only make the first column editable
            return super().edit(index, trigger, event)
        elif column == 2:  # And the third column editable
            return super().edit(index, trigger, event)

        # Return False if the column shouldn't be editable
        return False

    def load_json(self):
        """Load the JSON data from the file."""
        with open(self.json_file, "r") as f:
            self.json_data = json.load(f)

    def load_json_from_file(self):
        """Prompt the user to load a JSON file and update the tree."""
        json_file, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", os.getcwd(), "JSON Files (*.json);;All Files (*)"
        )
        if json_file:
            self.json_file = json_file
            self.load_json()
            self.model.loadJsonData(self.json_data)
            self.treeView.expandAll()

    def export_json_to_file(self):
        """Export the current tree data to a JSON file."""
        json_data = self.model.to_json()
        with open("export.json", "w") as f:
            json.dump(json_data, f, indent=4)
        QMessageBox.information(self, "Export Success", "Tree exported to export.json")

    def add_dimension(self):
        """Add a new dimension to the model."""
        self.model.add_dimension()

    def open_context_menu(self, position: QPoint):
        """Handle right-click context menu."""
        editing = self.edit_toggle.isChecked()

        index = self.treeView.indexAt(position)
        if not index.isValid():
            return

        item = index.internalPointer()

        # Check the role of the item directly from the stored role
        if item.role == "dimension" and editing:
            # Context menu for dimensions
            add_factor_action = QAction("Add Factor", self)
            remove_dimension_action = QAction("Remove Dimension", self)

            # Connect actions
            add_factor_action.triggered.connect(lambda: self.model.add_factor(item))
            remove_dimension_action.triggered.connect(
                lambda: self.model.remove_item(item)
            )

            # Add actions to menu
            menu = QMenu(self)
            menu.addAction(add_factor_action)
            menu.addAction(remove_dimension_action)

        elif item.role == "factor" and editing:
            # Context menu for factors
            add_layer_action = QAction("Add Layer", self)
            remove_factor_action = QAction("Remove Factor", self)
            clear_action = QAction("Clear Layer Weightings", self)
            auto_assign_action = QAction("Auto Assign Layer Weightings", self)

            # Connect actions
            add_layer_action.triggered.connect(lambda: self.model.add_layer(item))
            remove_factor_action.triggered.connect(lambda: self.model.remove_item(item))
            clear_action.triggered.connect(
                lambda: self.model.clear_layer_weightings(item)
            )
            auto_assign_action.triggered.connect(
                lambda: self.model.auto_assign_layer_weightings(item)
            )

            # Add actions to menu
            menu = QMenu(self)
            menu.addAction(add_layer_action)
            menu.addAction(remove_factor_action)
            menu.addAction(clear_action)
            menu.addAction(auto_assign_action)

        elif item.role == "layer":
            # Context menu for layers
            show_properties_action = QAction("🔘 Show Properties", self)
            remove_layer_action = QAction("❌ Remove Layer", self)

            # Connect actions
            show_properties_action.triggered.connect(
                lambda: self.show_layer_properties(item)
            )
            remove_layer_action.triggered.connect(lambda: self.model.remove_item(item))

            # Add actions to menu
            menu = QMenu(self)
            menu.addAction(show_properties_action)
            if editing:
                menu.addAction(remove_layer_action)

        # Show the menu at the cursor's position
        menu.exec_(self.treeView.viewport().mapToGlobal(position))

    def show_layer_properties(self, item):
        """Open a dialog showing layer properties and update the tree upon changes."""
        editing = self.edit_toggle.isChecked()
        # Get the current layer name and layer data from the item
        layer_name = item.data(0)  # Column 0: layer name
        layer_data = item.data(3)  # Column 3: layer data (stored as a dict)

        # Create and show the LayerDetailDialog
        dialog = LayerDetailDialog(
            layer_name, layer_data, item, editing=editing, parent=self
        )

        # Connect the dialog's dataUpdated signal to handle data updates
        def update_layer_data(updated_data):
            # Update the layer data in the item (column 4)
            item.setData(3, updated_data)

            # Check if the layer name has changed, and if so, update it in column 0
            if updated_data.get("name", layer_name) != layer_name:
                item.setData(0, updated_data.get("name", layer_name))

        # Connect the signal emitted from the dialog to update the item
        dialog.dataUpdated.connect(update_layer_data)

        # Show the dialog (exec_ will block until the dialog is closed)
        dialog.exec_()

    def toggle_edit_mode(self):
        """Enable or disable edit mode based on the 'Edit' toggle state."""
        edit_mode = self.edit_toggle.isChecked()

        # Enable or disable the "Add Dimension" button
        self.add_dimension_button.setVisible(edit_mode)

        # Enable or disable double-click editing in the tree view
        if edit_mode:
            self.treeView.setEditTriggers(QTreeView.DoubleClicked)
        else:
            self.treeView.setEditTriggers(QTreeView.NoEditTriggers)

    def start_workflows(self):
        """Start a workflow for each 'layer' node in the tree."""
        self._start_workflows_from_tree(self.treeView.model().rootItem)

    def _start_workflows_from_tree(self, parent_item):
        """Recursively start workflows for each 'layer' in the tree."""
        for i in range(parent_item.childCount()):
            child_item = parent_item.child(i)

            # If the child is a layer, we queue a workflow task
            if child_item.role == "layer":
                self.queue_manager.add_task(child_item.data(3))

            # Recursively process children (dimensions, factors)
            self._start_workflows_from_tree(child_item)

    def on_task_started(self, message):
        print(message)

    def on_task_completed(self, message, success):
        status = "Success" if success else "Failure"
        print(f"{message}: {status}")

    def process_leaves(self):
        """
        This function processes all nodes in the QTreeView that have the 'layer' role.
        It iterates over the entire tree, collecting nodes with the 'layer' role, and
        processes each one by showing an animated icon, waiting for 2 seconds, and
        then removing the animation.
        """
        self.start_workflows()
        self.queue_manager.start_processing()

        # old implementation to be removed soone
        # follows below.

        model = self.treeView.model()  # Get the model from the tree_view

        # Disable the prepare button and show the throbber during processing
        self.prepare_button.setEnabled(False)
        self.prepare_throbber.setVisible(True)

        # Iterate over all items in the tree and find nodes with the 'layer' role
        layer_nodes = []
        row_count = model.rowCount()

        for row in range(row_count):
            parent_index = model.index(row, 0)  # Start from the root level
            self.collect_layer_nodes(model, parent_index, layer_nodes)

        # Process each 'layer' node
        self.process_each_layer(layer_nodes, 0)

    def collect_layer_nodes(self, model, parent_index, layer_nodes):
        """
        Recursively collects all 'layer' nodes from the tree starting from the given parent index.
        Nodes with the 'layer' role are added to the layer_nodes list.
        """
        # Get the item from the model
        item = parent_index.internalPointer()

        # If the item is a 'layer', add it to the list of nodes to process
        if item and getattr(item, "role", None) == "layer":
            layer_nodes.append(parent_index)

        # Process all child items recursively
        for row in range(model.rowCount(parent_index)):
            child_index = model.index(row, 0, parent_index)
            self.collect_layer_nodes(model, child_index, layer_nodes)

    def process_each_layer(self, layer_nodes, index):
        """
        Processes each 'layer' node by showing an animated icon, waiting for 2 seconds,
        and then removing the animation.
        """
        # Base case: if all nodes are processed, enable the button and hide the throbber
        if index >= len(layer_nodes):
            self.prepare_button.setEnabled(True)
            self.prepare_throbber.setVisible(False)
            return

        # Get the current 'layer' node index
        node_index = layer_nodes[index]
        model = self.treeView.model()

        # Create a QModelIndex for the second column of the current row
        second_column_index = model.index(node_index.row(), 1, node_index.parent())

        # Set an animated icon (using a QLabel and QMovie to simulate animation)
        movie = QMovie(
            resources_path("resources", "throbber.gif")
        )  # Use a valid path to an animated gif
        row_height = self.treeView.rowHeight(
            node_index
        )  # Get the height of the current row
        movie.setScaledSize(
            movie.currentPixmap()
            .size()
            .scaled(row_height, row_height, Qt.KeepAspectRatio)
        )

        label = QLabel()
        label.setMovie(movie)
        movie.start()

        # Set the animated icon in the second column of the node
        self.treeView.setIndexWidget(second_column_index, label)

        # Wait for 2 seconds to simulate processing
        QTimer.singleShot(
            2000,
            lambda: self.finish_processing(
                second_column_index, layer_nodes, index, movie
            ),
        )

    def finish_processing(self, second_column_index, layer_nodes, index, movie):
        """
        Finishes processing by removing the animated icon and proceeds to the next node.
        """
        model = self.treeView.model()

        # Stop the animation and remove the animated icon
        movie.stop()
        self.treeView.setIndexWidget(second_column_index, None)

        # Move to the next 'layer' node
        self.process_each_layer(layer_nodes, index + 1)
