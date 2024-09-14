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
)
from qgis.PyQt.QtCore import QPoint, Qt, QTimer
from qgis.PyQt.QtGui import QMovie
import json
import os
from .geest_treeview import CustomTreeView, JsonTreeModel
from .layer_details_dialog import LayerDetailDialog
from ..utilities import resources_path


class GeestDock(QDockWidget):
    def __init__(self, parent=None, json_file=None):
        super().__init__(parent)

        self.json_file = json_file
        widget = QWidget()
        layout = QVBoxLayout(widget)

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

        self.treeView.setEditTriggers(
            QTreeView.DoubleClicked
        )  # Only allow editing on double-click

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

        add_dimension_button = QPushButton("⭐️ Add Dimension")
        add_dimension_button.clicked.connect(self.add_dimension)

        load_json_button = QPushButton("📂 Load Template")
        load_json_button.clicked.connect(self.load_json_from_file)

        export_json_button = QPushButton("📦️ Save Template")
        export_json_button.clicked.connect(self.export_json_to_file)

        button_bar.addWidget(add_dimension_button)
        button_bar.addStretch()

        self.prepare_button = QPushButton("🛸 Prepare")
        self.prepare_button.clicked.connect(self.process_leaves)
        button_bar.addWidget(self.prepare_button)
        button_bar.addStretch()

        button_bar.addWidget(load_json_button)
        button_bar.addWidget(export_json_button)
        layout.addLayout(button_bar)

        widget.setLayout(layout)
        self.setWidget(widget)

        # Prepare the throbber for the button (hidden initially)
        self.prepare_throbber = QLabel(self)
        movie = QMovie(resources_path("resources", "throbber.gif"))
        self.prepare_throbber.setMovie(movie)
        self.prepare_throbber.setScaledContents(True)
        self.prepare_throbber.setVisible(False)  # Hide initially
        movie.start()

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
        index = self.treeView.indexAt(position)
        if not index.isValid():
            return

        item = index.internalPointer()

        # Check the role of the item directly from the stored role
        if item.role == "dimension":
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

        elif item.role == "factor":
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
            menu.addAction(remove_layer_action)

        # Show the menu at the cursor's position
        menu.exec_(self.treeView.viewport().mapToGlobal(position))

    def show_layer_properties(self, item):
        """Open a dialog showing layer properties and update the tree upon changes."""
        # Get the current layer name and layer data from the item
        layer_name = item.data(0)  # Column 0: layer name
        layer_data = item.data(4)  # Column 4: layer data (stored as a dict)

        # Create and show the LayerDetailDialog
        dialog = LayerDetailDialog(layer_name, layer_data, self)

        # Connect the dialog's dataUpdated signal to handle data updates
        def update_layer_data(updated_data):
            # Update the layer data in the item (column 4)
            item.setData(4, updated_data)

            # Check if the layer name has changed, and if so, update it in column 0
            if updated_data.get('name', layer_name) != layer_name:
                item.setData(0, updated_data.get('name', layer_name))

        # Connect the signal emitted from the dialog to update the item
        dialog.dataUpdated.connect(update_layer_data)

        # Show the dialog (exec_ will block until the dialog is closed)
        dialog.exec_()

    def process_leaves(self):
        """
        This function processes all nodes in the QTreeView that have the 'layer' role.
        It iterates over the entire tree, collecting nodes with the 'layer' role, and
        processes each one by showing an animated icon, waiting for 2 seconds, and 
        then removing the animation.
        """
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
        if item and getattr(item, 'role', None) == 'layer':
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
        movie = QMovie(resources_path("resources", "throbber.gif"))  # Use a valid path to an animated gif
        row_height = self.treeView.rowHeight(node_index)  # Get the height of the current row
        movie.setScaledSize(movie.currentPixmap().size().scaled(row_height, row_height, Qt.KeepAspectRatio))

        label = QLabel()
        label.setMovie(movie)
        movie.start()

        # Set the animated icon in the second column of the node
        self.treeView.setIndexWidget(second_column_index, label)

        # Wait for 2 seconds to simulate processing
        QTimer.singleShot(2000, lambda: self.finish_processing(second_column_index, layer_nodes, index, movie))

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
