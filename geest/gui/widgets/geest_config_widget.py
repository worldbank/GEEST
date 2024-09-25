from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QRadioButton,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QButtonGroup,
    QLayout,
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
from qgis.core import QgsProviderRegistry, QgsVectorLayer, QgsMessageLog, Qgis

from .geest_widget_factory import GeestWidgetFactory


class GeestConfigWidget(QWidget):
    stateChanged = pyqtSignal(dict)

    def __init__(self, config_dict):
        super().__init__()
        self.original_config = config_dict
        self.modified_config = config_dict.copy()
        self.widgets = {}
        QgsMessageLog.logMessage(f"Initializing GeestConfigWidget with config: {config_dict}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        self.create_widgets()
        self.setup_connections()

    def create_widgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        QgsMessageLog.logMessage("Calling GeestWidgetFactory.create_widgets",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        widgets_container = GeestWidgetFactory.create_widgets(
            self.original_config, self
        )

        if widgets_container is None:
            QgsMessageLog.logMessage("GeestWidgetFactory.create_widgets returned None",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)
            return

        if not isinstance(widgets_container, QWidget):
            QgsMessageLog.logMessage(f"GeestWidgetFactory.create_widgets returned unexpected type:"
                                     f" {type(widgets_container)}",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)
            return

        if widgets_container.layout() is None:
            QgsMessageLog.logMessage("widgets_container has no layout",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)
            return

        if widgets_container.layout().count() > 0:
            QgsMessageLog.logMessage(f"Adding container with {widgets_container.layout().count()} items",
                                     "GeestConfigWidget",
                                     level=Qgis.Info)
            layout.addWidget(widgets_container)
            self.find_and_store_widgets(widgets_container)
        else:
            QgsMessageLog.logMessage("No widgets were created by GeestWidgetFactory",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)

        QgsMessageLog.logMessage(self.dump_widget_hierarchy(widgets_container),
                                 "GeestConfigWidget",
                                 level=Qgis.Info)

    def find_and_store_widgets(self, container):
        QgsMessageLog.logMessage("Starting to find and store widgets",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        self.recursive_find_and_store_widgets(container)
        QgsMessageLog.logMessage(f"Total widgets stored: {len(self.widgets)}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)

    def recursive_find_and_store_widgets(self, widget, depth=0):
        QgsMessageLog.logMessage("  " * depth + f"Examining widget: {type(widget).__name__}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        use_key = widget.property("use_key")
        if use_key:
            if use_key not in self.widgets:
                self.widgets[use_key] = {}
            if isinstance(widget, QRadioButton):
                self.widgets[use_key]["radio"] = widget
                QgsMessageLog.logMessage("  " * depth + f"Stored QRadioButton for key: {use_key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
            elif isinstance(
                widget,
                (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QgsMapLayerComboBox),
            ):
                self.widgets[use_key]["widget"] = widget
                QgsMessageLog.logMessage("  " * depth + f"Stored {type(widget).__name__} for key: {use_key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
            elif (
                isinstance(widget, QWidget)
                and widget.property("widget_type") == "multibuffer"
            ):
                self.widgets[use_key]["widget"] = widget
                QgsMessageLog.logMessage("  " * depth + f"Stored multibuffer widget for key: {use_key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
            elif (
                isinstance(widget, QWidget)
                and widget.property("widget_type") == "classify_poly_into_classes"
            ):
                self.widgets[use_key]["widget"] = widget
                QgsMessageLog.logMessage("  " * depth + f"Stored classify_poly_into_classes widget for key: {use_key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
            elif (
                isinstance(widget, QWidget)
                and widget.findChild(QgsMapLayerComboBox)
                and widget.findChild(QComboBox)
            ):
                self.widgets[use_key]["widget"] = widget
                QgsMessageLog.logMessage("  " * depth + f"Stored composite widget (polygon_layer_with_field_selector) "
                                                        f"for key: {use_key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)

        # Check if the widget has a layout
        layout = widget.layout() if callable(getattr(widget, "layout", None)) else None
        if layout:
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    self.recursive_find_and_store_widgets(item.widget(), depth + 1)

        QgsMessageLog.logMessage(f"Current widgets dictionary: {self.widgets}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)

    def setup_connections(self):
        QgsMessageLog.logMessage("Setting up connections",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        for key, widgets in self.widgets.items():
            radio = widgets.get("radio")
            widget = widgets.get("widget")

            # Always set up the radio button connection
            if radio:
                radio.toggled.connect(
                    lambda checked, k=key: self.handle_option_change(k, checked)
                )
                QgsMessageLog.logMessage(f"Set up radio connection for {key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)

            # Retrieve the widget_type property, if set
            widget_type = widget.property("widget_type") if widget else None

            # Handle specific widget types
            if widget_type == "classify_poly_into_classes":
                QgsMessageLog.logMessage(f"Setting up specific connections for widget_type: {widget_type} "
                                         f"(key: {key})",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
                if hasattr(widget, "selectionsChanged"):
                    # Connect the custom signal to update_classify_poly_config
                    widget.selectionsChanged.connect(
                        lambda k=key: self.update_classify_poly_config(k)
                    )
                    QgsMessageLog.logMessage(f"Connected selectionsChanged signal for key: {key}",
                                             "GeestConfigWidget",
                                             level=Qgis.Info)

            # Existing generic connection logic
            if widget:
                QgsMessageLog.logMessage(f"Setting up connection for widget type: {type(widget).__name__} for "
                                         f"key: {key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
                if isinstance(widget, QgsMapLayerComboBox):
                    widget.layerChanged.connect(
                        lambda layer, k=key: self.update_layer_path(k, layer)
                    )
                elif isinstance(widget, QLineEdit):
                    widget.textChanged.connect(
                        lambda text, k=key: self.update_sub_widget_state(k, text)
                    )
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.valueChanged.connect(
                        lambda value, k=key: self.update_sub_widget_state(k, value)
                    )
                elif isinstance(widget, QComboBox):
                    widget.currentTextChanged.connect(
                        lambda text, k=key: self.update_sub_widget_state(k, text)
                    )
                elif (
                    isinstance(widget, QWidget)
                    and widget.findChild(QgsMapLayerComboBox)
                    and widget.findChild(QComboBox)
                    and not widget_type == "classify_poly_into_classes"
                ):
                    layer_selector = widget.findChild(QgsMapLayerComboBox)
                    field_selector = widget.findChild(QComboBox)

                    def update_fields(layer):
                        QgsMessageLog.logMessage(f"[setup_connections] populate_field_selector called for"
                                                 f" key: {key} with layer: {layer.name() if layer else 'None'}",
                                                 "GeestConfigWidget",
                                                 level=Qgis.Info)
                        self.populate_field_selector(layer, field_selector)
                        self.update_polygon_layer_and_field(key, layer, field_selector)

                    layer_selector.layerChanged.connect(update_fields)
                    field_selector.currentTextChanged.connect(
                        lambda text, k=key, ls=layer_selector: self.update_polygon_layer_and_field(
                            k, ls.currentLayer(), field_selector
                        )
                    )
                elif widget_type == "multibuffer":
                    travel_mode_group = widget.travel_mode_group
                    measurement_group = widget.measurement_group
                    increment_edit = widget.increment_edit

                    travel_mode_group.buttonClicked.connect(
                        lambda btn, k=key: self.update_multibuffer_state(k)
                    )
                    measurement_group.buttonClicked.connect(
                        lambda btn, k=key: self.update_multibuffer_state(k)
                    )
                    increment_edit.textChanged.connect(
                        lambda text, k=key: self.update_multibuffer_state(k)
                    )

                QgsMessageLog.logMessage(f"Set up widget connection for {key}: {type(widget).__name__}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)

    @staticmethod
    def populate_field_selector(layer, field_selector):
        if isinstance(layer, QgsVectorLayer):
            field_selector.clear()
            field_selector.addItems([field.name() for field in layer.fields()])
            QgsMessageLog.logMessage(
                f"Populated field selector with: {[field.name() for field in layer.fields()]}",
                "GeestConfigWidget",
                level=Qgis.Info
            )
        else:
            QgsMessageLog.logMessage(f"Invalid layer type for populating field selector: {type(layer)}",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)

    def update_polygon_layer_and_field(self, key, layer, field):
        QgsMessageLog.logMessage(f"update_polygon_layer_and_field called for {key}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        QgsMessageLog.logMessage(f"Layer: {layer.name() if layer else 'None'}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        QgsMessageLog.logMessage(f"Field: {field}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)

        if layer and isinstance(layer, QgsVectorLayer) and field:
            provider_key = layer.providerType()
            uri = layer.dataProvider().dataSourceUri()
            QgsMessageLog.logMessage(f"Layer URI: {uri}",
                                     "GeestConfigWidget",
                                     level=Qgis.Info)
            decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
            QgsMessageLog.logMessage(f"Decoded URI: {decoded}",
                                     "GeestConfigWidget",
                                     level=Qgis.Info)
            path = decoded.get("path") or decoded.get("url") or decoded.get("layerName")

            if path:
                value = f"{path};{field}"
                QgsMessageLog.logMessage(f"Setting {key} to {value}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
                self.modified_config[key] = value
            else:
                QgsMessageLog.logMessage(
                    f"Unable to determine path for layer {layer.name()} with provider {provider_key}",
                    "GeestConfigWidget",
                    level=Qgis.Warning
                )
                self.modified_config[key] = ""
        else:
            QgsMessageLog.logMessage(f"No valid layer or field selected for {key}",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)
            self.modified_config[key] = ""

        QgsMessageLog.logMessage(
            f"Modified config after update_polygon_layer_and_field: {self.modified_config}",
            "GeestConfigWidget",
            level=Qgis.Info
        )
        self.stateChanged.emit(self.get_state())

    def update_classify_poly_config(self, key):
        QgsMessageLog.logMessage(f"update_classify_poly_config called for {key}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        widget = self.widgets[key].get("widget")
        if widget and widget.property("widget_type") == "classify_poly_into_classes":
            layer, field = widget.get_selections()
            if layer and field:
                provider_key = layer.providerType()
                uri = layer.dataProvider().dataSourceUri()
                QgsMessageLog.logMessage(f"Layer URI: {uri}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
                decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
                QgsMessageLog.logMessage(f"Decoded URI: {decoded}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
                path = (
                        decoded.get("path")
                        or decoded.get("url")
                        or decoded.get("layerName")
                )

                if path:
                    value = f"{path};{field}"
                    QgsMessageLog.logMessage(f"Setting {key} to {value}",
                                             "GeestConfigWidget",
                                             level=Qgis.Info)
                    self.modified_config[key] = value
                else:
                    QgsMessageLog.logMessage(
                        f"Unable to determine path for layer {layer.name()} with provider {provider_key}",
                        "GeestConfigWidget",
                        level=Qgis.Warning
                    )
                    self.modified_config[key] = ""
            else:
                QgsMessageLog.logMessage(f"No layer or field selected for {key}",
                                         "GeestConfigWidget",
                                         level=Qgis.Warning)
                self.modified_config[key] = ""
        else:
            QgsMessageLog.logMessage(f"Widget for {key} is not a ClassifyPolyIntoClassesWidget",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)
            self.modified_config[key] = ""
        QgsMessageLog.logMessage(
            f"Modified config after update_classify_poly_config: {self.modified_config}",
            "GeestConfigWidget",
            level=Qgis.Info
        )
        self.stateChanged.emit(self.get_state())

    def update_layer_path(self, key, layer):
        QgsMessageLog.logMessage(f"update_layer_path called for {key}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        if layer:
            provider_key = layer.providerType()
            uri = layer.dataProvider().dataSourceUri()
            QgsMessageLog.logMessage(f"Layer URI: {uri}",
                                     "GeestConfigWidget",
                                     level=Qgis.Info)
            decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
            QgsMessageLog.logMessage(f"Decoded URI: {decoded}",
                                     "GeestConfigWidget",
                                     level=Qgis.Info)
            path = decoded.get("path") or decoded.get("url") or decoded.get("layerName")
            if path:
                QgsMessageLog.logMessage(f"Path found: {path}",
                                         "GeestConfigWidget",
                                         level=Qgis.Info)
                self.update_sub_widget_state(key, path)
            else:
                QgsMessageLog.logMessage(
                    f"Unable to determine path for layer {layer.name()} with provider {provider_key}",
                    "GeestConfigWidget",
                    level=Qgis.Warning
                )
                self.update_sub_widget_state(key, uri)  # Fallback to using the full URI
        else:
            QgsMessageLog.logMessage(f"No layer selected for {key}",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)
            self.update_sub_widget_state(key, None)

    def handle_option_change(self, option, checked):
        QgsMessageLog.logMessage(f"handle_option_change called for {option}, checked={checked}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        if checked:
            for key, widgets in self.widgets.items():
                widget = widgets.get("widget")
                if key == option:
                    if widget is None:
                        QgsMessageLog.logMessage(f"No widget found for {key}",
                                                 "GeestConfigWidget",
                                                 level=Qgis.Warning)
                        self.modified_config[key] = 1
                    elif isinstance(widget, QWidget) and hasattr(widget, "get_selections"):
                        QgsMessageLog.logMessage(f"Handling polygon_layer_with_field_selector for {key}",
                                                 "GeestConfigWidget",
                                                 level=Qgis.Info)
                        layer, field = widget.get_selections()
                        if layer and field:
                            self.update_polygon_layer_and_field(key, layer, field)
                        else:
                            QgsMessageLog.logMessage(f"No layer or field selected for {key}",
                                                     "GeestConfigWidget",
                                                     level=Qgis.Warning)
                    elif isinstance(widget, QgsMapLayerComboBox):
                        QgsMessageLog.logMessage(f"Handling QgsMapLayerComboBox for {key}",
                                                 "GeestConfigWidget",
                                                 level=Qgis.Info)
                        self.update_layer_path(key, widget.currentLayer())
                    elif isinstance(widget, QWidget) and widget.property("widget_type") == "multibuffer":
                        QgsMessageLog.logMessage(f"Handling multibuffer for {key}",
                                                 "GeestConfigWidget",
                                                 level=Qgis.Info)
                        self.update_multibuffer_state(key)
                    elif isinstance(widget, QWidget) and widget.property("widget_type") == "classify_poly_into_classes":
                        QgsMessageLog.logMessage(f"Handling ClassifyPolyIntoClassesWidget for {key}",
                                                 "GeestConfigWidget",
                                                 level=Qgis.Info)
                        self.update_classify_poly_config(key)
                    else:
                        QgsMessageLog.logMessage(f"Setting {key} to 1",
                                                 "GeestConfigWidget",
                                                 level=Qgis.Info)
                        self.modified_config[key] = 1
                else:
                    QgsMessageLog.logMessage(f"Setting {key} to 0",
                                             "GeestConfigWidget",
                                             level=Qgis.Info)
                    self.modified_config[key] = 0
        else:
            QgsMessageLog.logMessage(f"Setting {option} to 0 (unchecked)",
                                     "GeestConfigWidget",
                                     level=Qgis.Info)
            self.modified_config[option] = 0
        QgsMessageLog.logMessage(f"Modified config after handle_option_change: {self.modified_config}",
                                 "GeestConfigWidget",
                                 level=Qgis.Info)
        self.stateChanged.emit(self.get_state())

    def update_sub_widget_state(self, option, value):
        if value is not None:
            self.modified_config[option] = value
            self.stateChanged.emit(self.get_state())
        else:
            QgsMessageLog.logMessage(f"Received None value for option: {option}",
                                     "GeestConfigWidget",
                                     level=Qgis.Warning)
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
        output = ["  " * level + f"{widget.__class__.__name__}"]

        layout = widget.layout() if callable(getattr(widget, "layout", None)) else getattr(widget, "layout", None)

        if isinstance(layout, QLayout):
            for i in range(layout.count()):
                item = layout.itemAt(i)
                if item.widget():
                    output.append(self.dump_widget_hierarchy(item.widget(), level + 1))
        return "\n".join(output)