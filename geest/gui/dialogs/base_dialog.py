from abc import ABC, abstractmethod
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from qgis.PyQt.QtCore import Qt

from GEEST2.geest.gui.widgets.widget_factory import WidgetFactory


class BaseDialog(QDialog, ABC):
    def __init__(self, input_specs: dict, on_accept_callback, parent=None):
        """
        Initialize the base dialog.

        :param input_specs: Dictionary containing dialog specifications.
        :param on_accept_callback: Callback function to handle inputs upon acceptance.
        :param parent: Parent widget.
        """
        super().__init__(parent)
        self.input_specs = input_specs
        self.widgets = {}
        self.on_accept_callback = on_accept_callback
        self.init_ui()

    def init_ui(self):
        # Set dialog properties
        self.setWindowTitle(self.input_specs.get("title", "Dialog"))
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Iterate over input specifications to create widgets
        for element in self.input_specs.get("elements", []):
            widget_type = element.get("type")
            label_text = element.get("label", "")
            widget = self.create_widget(widget_type, element)

            if label_text:
                label = QLabel(label_text)
                label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.layout.addWidget(label)

            if widget:
                self.layout.addWidget(widget)
                self.widgets[element.get("name")] = widget

        # Add dialog buttons
        self.add_buttons()

    def add_buttons(self):
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.handle_accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(button_layout)

    def create_widget(self, widget_type, spec):
        return WidgetFactory.create_widget(widget_type, spec, self)

    def get_inputs(self):
        inputs = {}
        for name, widget in self.widgets.items():
            spec = next(
                (elem for elem in self.input_specs["elements"] if elem["name"] == name),
                None,
            )
            if spec:
                inputs[name] = WidgetFactory.get_widget_value(widget, spec)
        return inputs

    def handle_accept(self):
        if self.validate_inputs():
            inputs = self.get_inputs()
            self.on_accept_callback(inputs)
            self.accept()
        else:
            # handle validation failure
            pass

    @staticmethod
    def validate_inputs():
        # input validation happens here
        return True

    @abstractmethod
    def process_inputs(self, inputs: dict):
        """
        This must be implemented by derived classes!
        """
        pass
