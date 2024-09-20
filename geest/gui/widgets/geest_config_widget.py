from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QRadioButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
#from qgis.core import QgsVectorLayer, QgsRasterLayer
from qgis.core import QgsProviderRegistry
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
            elif isinstance(widget, QWidget) and widget.findChild(QgsMapLayerComboBox) and widget.findChild(QComboBox):
                self.widgets[use_key]["widget"] = widget
                print("  " * depth + f"Stored composite widget (polygon_layer_with_field_selector) for key: {use_key}")
        if widget.layout():
            for i in range(widget.layout().count()):
                item = widget.layout().itemAt(i)
                if item.widget():
                    self.recursive_find_and_store_widgets(item.widget(), depth + 1)
        print(f"Current widgets dictionary: {self.widgets}")

    def setup_connections(self):
        print("Setting up connections")
        for key, widgets in self.widgets.items():
            radio = widgets.get("radio")
            widget = widgets.get("widget")
            if radio:
                radio.toggled.connect(lambda checked, k=key: self.handle_option_change(k, checked))
                print(f"Set up radio connection for {key}")
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
                    layer_selector.layerChanged.connect(
                        lambda layer, k=key: self.update_polygon_layer_and_field(k, layer, field_selector))
                    field_selector.currentTextChanged.connect(
                        lambda text, k=key, ls=layer_selector: self.update_polygon_layer_and_field(k, ls.currentLayer(),
                                                                                                   field_selector))
                print(f"Set up widget connection for {key}: {type(widget).__name__}")

    def update_polygon_layer_and_field(self, key, layer, field_selector):
        print(f"update_polygon_layer_and_field called for {key}")
        if layer:
            provider_key = layer.providerType()
            uri = layer.dataProvider().dataSourceUri()
            print(f"Layer URI: {uri}")
            decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
            print(f"Decoded URI: {decoded}")
            path = decoded.get('path') or decoded.get('url') or decoded.get('layerName')
            field = field_selector.currentText()
            print(f"Selected field: {field}")
            if path:
                value = f"{path};{field}"
                print(f"Setting {key} to {value}")
                self.modified_config[key] = value
            else:
                print(f"Unable to determine path for layer {layer.name()} with provider {provider_key}")
                value = f"{uri};{field}"
                print(f"Setting {key} to {value}")
                self.modified_config[key] = value
        else:
            print(f"No layer selected for {key}")
            self.modified_config[key] = ""

        print(f"Modified config after update_polygon_layer_and_field: {self.modified_config}")
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
                if widget:
                    widget.setEnabled(key == option)
                    print(f"Enabled widget for {key}: {key == option}")
            for key in self.widgets.keys():
                if key == option:
                    widget = self.widgets[key].get("widget")
                    if widget:
                        print(f"Widget type for {key}: {type(widget)}")
                        if isinstance(widget, QWidget) and widget.findChild(QgsMapLayerComboBox) and widget.findChild(
                                QComboBox):
                            print(f"Handling polygon_layer_with_field_selector for {key}")
                            layer_selector = widget.findChild(QgsMapLayerComboBox)
                            field_selector = widget.findChild(QComboBox)
                            self.update_polygon_layer_and_field(key, layer_selector.currentLayer(), field_selector)
                        elif isinstance(widget, QgsMapLayerComboBox):
                            print(f"Handling QgsMapLayerComboBox for {key}")
                            self.update_layer_path(key, widget.currentLayer())
                        else:
                            print(f"Setting {key} to 1")
                            self.modified_config[key] = 1
                    else:
                        print(f"No widget found for {key}, setting to 1")
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

    def get_state(self):
        return self.modified_config.copy()

    def reset_to_original(self):
        self.modified_config = self.original_config.copy()
        self.update_widgets_from_config()
        self.stateChanged.emit(self.get_state())

    def update_widgets_from_config(self):
        for key, value in self.modified_config.items():
            if key in self.widgets:
                widgets = self.widgets[key]
                radio = widgets.get("radio")
                widget = widgets.get("widget")
                if radio:
                    radio.setChecked(bool(value))
                if widget:
                    if isinstance(widget, QLineEdit):
                        widget.setText(str(value))
                    elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                        widget.setValue(float(value) if isinstance(widget, QDoubleSpinBox) else int(value))
                    elif isinstance(widget, (QComboBox, QgsMapLayerComboBox)):
                        widget.setCurrentText(str(value))
                    elif isinstance(widget, QWidget) and widget.findChild(QgsMapLayerComboBox) and widget.findChild(QComboBox):
                        # Handle polygon_layer_with_field_selector widget
                        if value and ';' in value:
                            layer_path, field = value.split(';')
                            field_selector = widget.findChild(QComboBox)
                            # Set layer --- maybe necessary?
                            # layer_selector = widget.findChild(QgsMapLayerComboBox)
                            # layer_selector.setLayer(layer_path)
                            field_selector.setCurrentText(field)

    def dump_widget_hierarchy(self, widget, level=0):
        output = []
        output.append("  " * level + f"{widget.__class__.__name__}")
        if hasattr(widget, 'layout') and widget.layout():
            for i in range(widget.layout().count()):
                item = widget.layout().itemAt(i)
                if item.widget():
                    output.append(self.dump_widget_hierarchy(item.widget(), level + 1))
        return "\n".join(output)