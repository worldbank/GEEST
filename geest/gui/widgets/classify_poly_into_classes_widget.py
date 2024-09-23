from qgis.PyQt.QtWidgets import QWidget, QVBoxLayout, QLabel, QComboBox
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer


class ClassifyPolyIntoClassesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.setLayout(self.layout)

        # Set the widget type property
        self.setProperty("widget_type", "classify_poly_into_classes")

        # Layer selector
        self.layer_label = QLabel("Select Polygon Layer:")
        self.layout.addWidget(self.layer_label)
        self.layer_selector = QgsMapLayerComboBox()
        self.layer_selector.setFilters(QgsMapLayerProxyModel.PolygonLayer)
        self.layout.addWidget(self.layer_selector)

        # Field selector
        self.field_label = QLabel("Select Field of Interest:")
        self.layout.addWidget(self.field_label)
        self.field_selector = QComboBox()
        self.layout.addWidget(self.field_selector)

        # Connect the layer changed signal
        self.layer_selector.layerChanged.connect(self.update_fields)

        # Initial update
        initial_layer = self.layer_selector.currentLayer()
        if initial_layer:
            self.update_fields(initial_layer)
        else:
            print("No initial layer selected")

    def update_fields(self, layer):
        print(f"Updating fields for layer: {layer.name() if layer else 'None'}")
        self.field_selector.clear()
        if isinstance(layer, QgsVectorLayer):
            fields = [field.name() for field in layer.fields()]
            self.field_selector.addItems(fields)
            print(f"Fields added: {fields}")
        else:
            print("Layer is not a vector layer")

    def get_selections(self):
        return self.layer_selector.currentLayer(), self.field_selector.currentText()

    def set_tooltip(self, tooltip):
        self.setToolTip(tooltip)

    def set_use_key(self, use_key):
        self.setProperty("use_key", use_key)
