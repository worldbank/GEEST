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

        # Add a button bar at the bottom with a Close button and Add Dimension button
        button_bar = QHBoxLayout()
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.close)

        add_dimension_button = QPushButton("⭐️ Add Dimension")
        add_dimension_button.clicked.connect(self.add_dimension)

        load_json_button = QPushButton("📂 Load Template")
        load_json_button.clicked.connect(self.load_json_from_file)

        export_json_button = QPushButton("📦️ Save Template")
        export_json_button.clicked.connect(self.export_json_to_file)

        button_bar.addWidget(add_dimension_button)
        button_bar.addStretch()

        prepare_button = QPushButton("🛸 Prepare")
        prepare_button.clicked.connect(self.process_leaves)
        button_bar.addWidget(prepare_button)
        button_bar.addStretch()

        button_bar.addWidget(load_json_button)
        button_bar.addWidget(export_json_button)
        button_bar.addStretch()
        button_bar.addWidget(close_button)
        layout.addLayout(button_bar)

        widget.setLayout(layout)
        self.setWidget(widget)

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
        """Open a dialog showing layer properties."""
        layer_name = item.data(0)
        layer_data = item.data(4)  # The 4th column stores the whole layer data dict
        dialog = LayerDetailDialog(layer_name, layer_data, self)
        dialog.exec_()

    def process_leaves(self):
        """
        This function processes all the leaf nodes in the QTreeView.
        Each leaf node is processed by changing its text to red, showing an animated icon,
        waiting for 2 seconds, and then reverting the text color back to black.
        """
        model = self.treeView.model()  # Get the model from the tree_view

        # Find all leaf nodes
        leaf_nodes = []

        def find_leaves(index):
            """Recursively find all leaf nodes starting from the given index."""
            if model.hasChildren(index):
                for row in range(model.rowCount(index)):
                    child_index = model.index(row, 0, index)
                    find_leaves(child_index)
            else:
                leaf_nodes.append(index)

        # Populate the leaf_nodes list
        # Start from the root index of the model
        root_index = model.index(0, 0)
        for row in range(model.rowCount()):
            find_leaves(model.index(row, 0, root_index))

        # Process each leaf node
        self.process_each_leaf(leaf_nodes, 0)

    def process_each_leaf(self, leaf_nodes, index):
        """
        Processes each leaf node by changing the text to red, showing an animated icon,
        waiting for 2 seconds, and then reverting the text color to black.
        """
        # Base case: if all nodes are processed, return
        if index >= len(leaf_nodes):
            return

        # Get the current leaf node index
        node_index = leaf_nodes[index]
        model = self.treeView.model()

        # Create a QModelIndex for the second column of the current row
        second_column_index = model.index(node_index.row(), 1, node_index.parent())
        # Set an animated icon (using a QLabel and QMovie to simulate animation)
        movie = QMovie("throbber.gif")  # Use a valid path to an animated gif
        # Get the height of the current row
        row_height = self.treeView.rowHeight(node_index)
        # Scale the movie to the row height
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
                second_column_index, leaf_nodes, index, movie
            ),
        )

    def finish_processing(self, second_column_index, leaf_nodes, index, movie):
        """
        Finishes processing by reverting text color to black and removing the animated icon.
        Then it proceeds to the next node.
        """
        model = self.treeView.model()
        # Stop the animation and remove the animated icon
        movie.stop()
        self.treeView.setIndexWidget(second_column_index, None)

        # Move to the next node
        self.process_each_leaf(leaf_nodes, index + 1)
