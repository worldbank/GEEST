from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QRadioButton,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox

from qgis.core import QgsProviderRegistry, QgsMessageLog, Qgis
from .geest_widget_factory import GeestWidgetFactory


class GeestConfigWidget(QWidget):
    stateChanged = pyqtSignal(dict)

    def __init__(self, config_dict):
        super().__init__()
        self.original_config = config_dict
        self.modified_config = config_dict.copy()
        self.widgets = {}
        self.create_widgets()
        self.setup_connections()

    def create_widgets(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        widgets_container = GeestWidgetFactory.create_widgets(
            self.original_config, self
        )

        if widgets_container is None:
            QgsMessageLog.logMessage(
                "GeestWidgetFactory.create_widgets returned None",
                "GeestConfigWidget",
                Qgis.Warning,
            )
            return

        if not isinstance(widgets_container, QWidget):
            QgsMessageLog.logMessage(
                f"GeestWidgetFactory.create_widgets returned unexpected type: {type(widgets_container)}",
                "GeestConfigWidget",
                Qgis.Warning,
            )
            return

        if widgets_container.layout() is None:
            QgsMessageLog.logMessage(
                "widgets_container has no layout",
                "GeestConfigWidget",
                Qgis.Warning,
            )
            return

        if widgets_container.layout().count() > 0:
            layout.addWidget(widgets_container)
            self.recursive_find_and_store_widgets(widgets_container)
        else:
            QgsMessageLog.logMessage(
                "No widgets were created by GeestWidgetFactory",
                "GeestConfigWidget",
                Qgis.Warning,
            )

    def recursive_find_and_store_widgets(self, widget, depth=0):
        use_key = widget.property("use_key")
        if use_key:
            if isinstance(widget, QRadioButton):
                if use_key not in self.widgets:
                    self.widgets[use_key] = {}
                self.widgets[use_key]["radio"] = widget
            elif isinstance(
                widget,
                (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QgsMapLayerComboBox),
            ):
                if use_key not in self.widgets:
                    self.widgets[use_key] = {}
                self.widgets[use_key]["widget"] = widget

        if widget.layout():
            for i in range(widget.layout().count()):
                item = widget.layout().itemAt(i)
                if item.widget():
                    self.recursive_find_and_store_widgets(item.widget(), depth + 1)

    def setup_connections(self):
        for key, widgets in self.widgets.items():
            radio = widgets.get("radio")
            widget = widgets.get("widget")
            if radio:
                radio.toggled.connect(
                    lambda checked, k=key: self.handle_option_change(k, checked)
                )
            if widget:
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
                QgsMessageLog.logMessage(
                    f"Set up widget connection for {key}: {type(widget).__name__}",
                    "GeestConfigWidget",
                    Qgis.Info,
                )

    def update_layer_path(self, key, layer):
        if layer:
            provider_key = layer.providerType()
            uri = layer.dataProvider().dataSourceUri()
            decoded = QgsProviderRegistry.instance().decodeUri(provider_key, uri)
            path = decoded.get("path") or decoded.get("url") or decoded.get("layerName")
            if path:
                self.update_sub_widget_state(key, path)
            else:
                QgsMessageLog.logMessage(
                    f"Unable to determine path for layer {layer.name()} with provider {provider_key}",
                    "GeestConfigWidget",
                    Qgis.Warning,
                )
                self.update_sub_widget_state(key, uri)  # Fallback to using the full URI
        else:
            QgsMessageLog.logMessage(
                f"No layer selected for {key}",
                "GeestConfigWidget",
                Qgis.Warning,
            )
            self.update_sub_widget_state(key, None)

    def handle_option_change(self, option, checked):
        if checked:
            for key, widgets in self.widgets.items():
                widget = widgets.get("widget")
                if widget:
                    widget.setEnabled(key == option)

            for key in self.widgets.keys():
                self.modified_config[key] = 1 if key == option else 0

        self.stateChanged.emit(self.get_state())

    def update_sub_widget_state(self, option, value):
        if value is not None:
            self.modified_config[option] = value
            self.stateChanged.emit(self.get_state())
        else:
            QgsMessageLog.logMessage(
                f"Received None value for option: {option}",
                "GeestConfigWidget",
                Qgis.Warning,
            )
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
                        widget.setValue(
                            float(value)
                            if isinstance(widget, QDoubleSpinBox)
                            else int(value)
                        )
                    elif isinstance(widget, (QComboBox, QgsMapLayerComboBox)):
                        widget.setCurrentText(str(value))

    def dump_widget_hierarchy(self, widget, level=0):
        output = []
        output.append("  " * level + f"{widget.__class__.__name__}")
        if hasattr(widget, "layout") and widget.layout():
            for i in range(widget.layout().count()):
                item = widget.layout().itemAt(i)
                if item.widget():
                    output.append(self.dump_widget_hierarchy(item.widget(), level + 1))
        return "\n".join(output)
