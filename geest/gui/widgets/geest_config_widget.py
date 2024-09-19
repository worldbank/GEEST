from qgis.PyQt.QtWidgets import (
    QWidget, QVBoxLayout, QRadioButton, QLineEdit,
    QSpinBox, QDoubleSpinBox, QComboBox
)
from qgis.PyQt.QtCore import pyqtSignal
from qgis.gui import QgsMapLayerComboBox
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
            if isinstance(widget, QRadioButton):
                self.widgets[use_key] = {"radio": widget}
                print("  " * depth + f"Stored QRadioButton for key: {use_key}")
            elif isinstance(widget, (QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QgsMapLayerComboBox)):
                if use_key in self.widgets:
                    self.widgets[use_key]["widget"] = widget
                    print("  " * depth + f"Stored {type(widget).__name__} for key: {use_key}")
                else:
                    print(f"Found widget for {use_key} but no associated radio button")

        if widget.layout():
            for i in range(widget.layout().count()):
                item = widget.layout().itemAt(i)
                if item.widget():
                    self.recursive_find_and_store_widgets(item.widget(), depth + 1)

    def setup_connections(self):
        print("Setting up connections")
        for key, widgets in self.widgets.items():
            radio = widgets.get("radio")
            widget = widgets.get("widget")
            if radio:
                radio.toggled.connect(lambda checked, k=key: self.handle_option_change(k, checked))
            if widget:
                if isinstance(widget, QLineEdit):
                    widget.textChanged.connect(lambda text, k=key: self.update_sub_widget_state(k, text))
                elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                    widget.valueChanged.connect(lambda value, k=key: self.update_sub_widget_state(k, value))
                elif isinstance(widget, (QComboBox, QgsMapLayerComboBox)):
                    widget.currentIndexChanged.connect(
                        lambda index, k=key: self.update_sub_widget_state(k, widget.currentText()))
            print(f"Set up connection for {key}")

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
        self.modified_config[option] = value
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

    def dump_widget_hierarchy(self, widget, level=0):
        output = []
        output.append("  " * level + f"{widget.__class__.__name__}")
        if hasattr(widget, 'layout') and widget.layout():
            for i in range(widget.layout().count()):
                item = widget.layout().itemAt(i)
                if item.widget():
                    output.append(self.dump_widget_hierarchy(item.widget(), level + 1))
        return "\n".join(output)