from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QRadioButton,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QButtonGroup,
    QLayout
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsProviderRegistry, QgsVectorLayer

from .geest_widget_factory import GeestWidgetFactory


class GeestConfigWidget(QWidget):
    stateChanged = pyqtSignal(dict)

    def __init__(self, config_dict):
        super().__init__()
        self.original_config = config_dict
        self.modified_config = config_dict.copy()
        self.widgets = {}
        print(f"Initializing GeestConfigWidget with config: {config_dict}")
        self.create_widgets()
        self.setup_connections()

    def create_widgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        print("Calling GeestWidgetFactory.create_widgets")
        widgets_container = GeestWidgetFactory.create_widgets(self.original_config, self)

        if widgets_container is None:
            print("GeestWidgetFactory.create_widgets returned None")
            return

        if not isinstance(widgets_container, QWidget):
            print(f"GeestWidgetFactory.create_widgets returned unexpected type: {type(widgets_container)}")
            return

        if widgets_container.layout() is None:
            print("widgets_container has no layout")
            return

        if widgets_container.layout().count() > 0:
            print(f"Adding container with {widgets_container.layout().count()} items")
            layout.addWidget(widgets_container)
            self.find_and_store_widgets(widgets_container)
        else:
            print("No widgets were created by GeestWidgetFactory")

        print(self.dump_widget_hierarchy(widgets_container))

    def find_and_store_widgets(self, container):
        print("Starting to find and store widgets")
        self.recursive_find_and_store_widgets(container)
        print(f"Total widgets stored: {len(self.widgets)}")

    def recursive_find_and_store_widgets(self, widget, depth=0):
        print("  " * depth + f"Examining widget: {type(widget).__name__}")
        use_key = widget.property("use_key")
        if use_key:
            if use_key not in self.widgets:
                self.widgets[use_key] = {}
            if isinstance(widget, QRadioButton):
                self.widgets[use_key]["radio"] = widget
                print("  " * depth + f"Stored QRadioButton for key: {use_key}")
            elif isinstance(widget, (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QgsMapLayerComboBox)):
                self.widgets[use_key]["widget"] = widget
                print("  " * depth + f"Stored {type(widget).__name__} for key: {use_key}")
            elif isinstance(widget, QWidget) and widget.property("widget_type") == "multibuffer":
                self.widgets[use_key]["widget"] = widget
                print("  " * depth + f"Stored multibuffer widget for key: {use_key}")
            elif isinstance(widget, QWidget) and widget.property("widget_type") == "classify_poly_into_classes":
                self.widgets[use_key]["widget"] = widget
                print("  " * depth + f"Stored classify_poly_into_classes widget for key: {use_key}")
            elif isinstance(widget, QWidget) and widget.findChild(QgsMapLayerComboBox) and widget.findChild(QComboBox):
                self.widgets[use_key]["widget"] = widget
                print("  " * depth + f"Stored composite widget (polygon_layer_with_field_selector) for key: {use_key}")

        # Check if the widget has a layout
        layout = widget.layout() if callable(getattr(widget, 'layout', None)) else None
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    self.recursive_find_and_store_widgets(item.widget(), depth + 1)

        print(f"Current widgets dictionary: {self.widgets}")

    def setup_connections(self):
        print("Setting up connections")
        for key, widgets in self.widgets.items():
            radio = widgets.get("radio")
            widget = widgets.get("widget")

            # Always set up the radio button connection
            if radio:
                radio.toggled.connect(lambda checked, k=key: self.handle_option_change(k, checked))
                print(f"Set up radio connection for {key}")

            # Retrieve the widget_type property, if set
            widget_type = widget.property("widget_type") if widget else None

            # Handle specific widget types
            if widget_type == "classify_poly_into_classes":
                print(f"Setting up specific connections for widget_type: {widget_type} (key: {key})")
                if hasattr(widget, 'selectionsChanged'):
                    # Connect the custom signal to update_classify_poly_config
                    widget.selectionsChanged.connect(lambda k=key: self.update_classify_poly_config(k))
                    print(f"Connected selectionsChanged signal for key: {key}")

            # Existing generic connection logic
            if widget:
                print(f"Setting up connection for widget type: {type(widget).__name__} for key: {key}")
                if isinstance(widget, QgsMapLayerComboBox):
                    widget.layerChanged.connect(lambda layer, k=key: self.update_layer_path(k, layer))
                elif isinstance(widget, QLineEdit):
                    widget.textChanged.connect(lambda text, k=key: self.update_sub_widget_state(k, text))
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.valueChanged.connect(lambda value, k=key: self.update_sub_widget_state(k, value))
                elif isinstance(widget, QComboBox):
                    widget.currentTextChanged.connect(lambda text, k=key: self.update_sub_widget_state(k, text))
                elif isinstance(widget, QWidget) and widget.findChild(QgsMapLayerComboBox) and widget.findChild(
                        QComboBox):
                    layer_selector = widget.findChild(QgsMapLayerComboBox)
                    field_selector = widget.findChild(QComboBox)

                    def update_fields(layer):
                        print(
                            f"[setup_connections] populate_field_selector called for key: {key} with layer: {layer.name() if layer else 'None'}")
                        self.populate_field_selector(layer, field_selector)
                        self.update_polygon_layer_and_field(key, layer, field_selector)

                    layer_selector.layerChanged.connect(update_fields)
                    field_selector.currentTextChanged.connect(
                        lambda text, k=key, ls=layer_selector: self.update_polygon_layer_and_field(k, ls.currentLayer(),
                                                                                                   field_selector))
                elif widget_type == "multibuffer":
                    travel_mode_group = widget.travel_mode_group
                    measurement_group = widget.measurement_group
                    increment_edit = widget.increment_edit

                    travel_mode_group.buttonClicked.connect(lambda btn, k=key: self.update_multibuffer_state(k))
                    measurement_group.buttonClicked.connect(lambda btn, k=key: self.update_multibuffer_state(k))
                    increment_edit.textChanged.connect(lambda text, k=key: self.update_multibuffer_state(k))

                print(f"Set up widget connection for {key}: {type(widget).__name__}")

    @staticmethod
    def populate_field_selector(layer, field_selector):
        if isinstance(layer, QgsVectorLayer):
            field_selector.clear()
            field_selector.addItems([field.name() for field in layer.fields()])
            print(f"Populated field selector with: {[field.name() for field in layer.fields()]}")
        else:
            print(f"Invalid layer type for populating field selector: {type(layer)}")

    def update_polygon_layer_and_field(self, key, layer, field):
        print(f"update_polygon_layer_and_field called for {key}")
        print(f"Layer: {layer.name() if layer else 'None'}")
        print(f"Field: {field}")

        if layer and isinstance(layer, QgsVectorLayer) and field:
            provider_key = layer.providerType()
            uri = layer.dataProvider().dataSourceUri()
            print(f"Layer URI: {uri}")
            decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
            print(f"Decoded URI: {decoded}")
            path = decoded.get('path') or decoded.get('url') or decoded.get('layerName')

            if path:
                value = f"{path};{field}"
                print(f"Setting {key} to {value}")
                self.modified_config[key] = value
            else:
                print(f"Unable to determine path for layer {layer.name()} with provider {provider_key}")
                self.modified_config[key] = ""
        else:
            print(f"No valid layer or field selected for {key}")
            self.modified_config[key] = ""

        print(f"Modified config after update_polygon_layer_and_field: {self.modified_config}")
        self.stateChanged.emit(self.get_state())

    def update_classify_poly_config(self, key):
        print(f"update_classify_poly_config called for {key}")
        widget = self.widgets[key].get("widget")
        if widget and widget.property("widget_type") == "classify_poly_into_classes":
            layer, field = widget.get_selections()
            if layer and field:
                provider_key = layer.providerType()
                uri = layer.dataProvider().dataSourceUri()
                print(f"Layer URI: {uri}")
                decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
                print(f"Decoded URI: {decoded}")
                path = decoded.get('path') or decoded.get('url') or decoded.get('layerName')

                if path:
                    value = f"{path};{field}"
                    print(f"Setting {key} to {value}")
                    self.modified_config[key] = value
                else:
                    print(f"Unable to determine path for layer {layer.name()} with provider {provider_key}")
                    self.modified_config[key] = ""
            else:
                print(f"No layer or field selected for {key}")
                self.modified_config[key] = ""
        else:
            print(f"Widget for {key} is not a ClassifyPolyIntoClassesWidget")
            self.modified_config[key] = ""
        print(f"Modified config after update_classify_poly_config: {self.modified_config}")
        self.stateChanged.emit(self.get_state())

    def update_layer_path(self, key, layer):
        print(f"update_layer_path called for {key}")  # Debug print
        if layer:
            provider_key = layer.providerType()
            uri = layer.dataProvider().dataSourceUri()
            print(f"Layer URI: {uri}")
            decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
            print(f"Decoded URI: {decoded}")
            path = decoded.get('path') or decoded.get('url') or decoded.get('layerName')
            if path:
                print(f"Path found: {path}")
                self.update_sub_widget_state(key, path)
            else:
                print(f"Unable to determine path for layer {layer.name()} with provider {provider_key}")
                self.update_sub_widget_state(key, uri)  # Fallback to using the full URI
        else:
            print(f"No layer selected for {key}")
            self.update_sub_widget_state(key, None)

    def handle_option_change(self, option, checked):
        print(f"handle_option_change called for {option}, checked={checked}")
        if checked:
            for key, widgets in self.widgets.items():
                widget = widgets.get("widget")
                if key == option:
                    if widget is None:
                        print(f"No widget found for {key}")
                        self.modified_config[key] = 1
                    elif isinstance(widget, QWidget) and hasattr(widget, 'get_selections'):
                        print(f"Handling polygon_layer_with_field_selector for {key}")
                        layer, field = widget.get_selections()
                        if layer and field:
                            self.update_polygon_layer_and_field(key, layer, field)
                        else:
                            print(f"No layer or field selected for {key}")
                    elif isinstance(widget, QgsMapLayerComboBox):
                        print(f"Handling QgsMapLayerComboBox for {key}")
                        self.update_layer_path(key, widget.currentLayer())
                    elif isinstance(widget, QWidget) and widget.property("widget_type") == "multibuffer":
                        print(f"Handling multibuffer for {key}")
                        self.update_multibuffer_state(key)
                    elif isinstance(widget, QWidget) and widget.property("widget_type") == "classify_poly_into_classes":
                        print(f"Handling ClassifyPolyIntoClassesWidget for {key}")
                        self.update_classify_poly_config(key)
                    else:
                        print(f"Setting {key} to 1")
                        self.modified_config[key] = 1
                else:
                    print(f"Setting {key} to 0")
                    self.modified_config[key] = 0
        else:
            print(f"Setting {option} to 0 (unchecked)")
            self.modified_config[option] = 0
        print(f"Modified config after handle_option_change: {self.modified_config}")
        self.stateChanged.emit(self.get_state())

    def update_sub_widget_state(self, option, value):
        if value is not None:
            self.modified_config[option] = value
            self.stateChanged.emit(self.get_state())
        else:
            print(f"Received None value for option: {option}")
            self.modified_config[option] = "0"
            self.stateChanged.emit(self.get_state())

    def update_multibuffer_state(self, key):
        widget = self.widgets[key]["widget"]
        travel_mode = "Driving" if widget.travel_mode_group.checkedButton().text() == "Driving" else "Walking"
        measurement = "Distance" if widget.measurement_group.checkedButton().text() == "Distance" else "Time"
        increments = widget.increment_edit.text()

        # If increments is empty, use the default value
        if not increments:
            increments = self.original_config.get("Default Multi Buffer Distances", "")

        self.modified_config[key] = f"{travel_mode};{measurement};{increments}"
        self.stateChanged.emit(self.get_state())

    def get_state(self):
        return self.modified_config.copy()

    def dump_widget_hierarchy(self, widget, level=0):
        output = []
        output.append("  " * level + f"{widget.__class__.__name__}")

        layout = widget.layout() if callable(getattr(widget, 'layout', None)) else getattr(widget, 'layout', None)

        if isinstance(layout, QLayout):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    output.append(self.dump_widget_hierarchy(item.widget(), level + 1))
        return "\n".join(output)
