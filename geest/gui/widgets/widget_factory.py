from qgis.PyQt.QtWidgets import (
    QDoubleSpinBox,
    QSpinBox,
    QLineEdit,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QFileDialog,
    QWidget,
    QHBoxLayout,
)
from qgis.gui import QgsLayerComboBox
from qgis.core import QgsMapLayer


class WidgetFactory:
    @staticmethod
    def create_widget(widget_type, spec, parent):
        if widget_type == "doublespinbox":
            widget = QDoubleSpinBox(parent)
            widget.setRange(spec.get("min", -1e10), spec.get("max", 1e10))
            widget.setDecimals(spec.get("decimals", 2))
            widget.setValue(spec.get("default", 0.0))
            return widget
        elif widget_type == "spinbox":
            widget = QSpinBox(parent)
            widget.setRange(spec.get("min", -1e9), spec.get("max", 1e9))
            widget.setValue(spec.get("default", 0))
            return widget
        elif widget_type == "lineedit":
            widget = QLineEdit(parent)
            widget.setText(spec.get("default", ""))
            return widget
        elif widget_type == "dropdown":
            widget = QComboBox(parent)
            options = spec.get("options", [])
            widget.addItems(options)
            default = spec.get("default")
            if default in options:
                widget.setCurrentText(default)
            elif options:
                widget.setCurrentText(options[0])
            return widget
        elif widget_type == "radiobutton":
            button_group = QButtonGroup(parent)
            layout = QHBoxLayout()
            container = QWidget(parent)
            container.setLayout(layout)
            for option in spec.get("options", []):
                rb = QRadioButton(option["label"])
                rb.setChecked(option.get("checked", False))
                button_group.addButton(rb, id=option.get("id"))
                layout.addWidget(rb)
            container.button_group = (
                button_group  # Attach the button group for retrieval
            )
            return container
        elif widget_type == "layerselector":
            widget = QgsLayerComboBox(parent)
            layer_type = spec.get("layer_type", "vector")  # can be vector or raster
            if layer_type == "vector":
                widget.setFilters(QgsMapLayer.VectorLayer)
            elif layer_type == "raster":
                widget.setFilters(QgsMapLayer.RasterLayer)
            widget.setCurrentLayer(spec.get("default_layer", None))
            return widget
        # more widgets go here
        else:
            return None

    @staticmethod
    def get_widget_value(widget, spec):
        widget_type = spec.get("type")
        if widget_type in ["doublespinbox", "spinbox"]:
            return widget.value()
        elif widget_type == "lineedit":
            return widget.text()
        elif widget_type == "dropdown":
            return widget.currentText()
        elif widget_type == "radiobutton":
            checked_button = widget.button_group.checkedButton()
            return checked_button.text() if checked_button else None
        elif widget_type == "layerselector":
            layer = widget.currentLayer()
            return layer.name() if layer else None
        else:
            return None
