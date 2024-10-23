from qgis.PyQt.QtWidgets import QVBoxLayout, QWidget, QPushButton
from qgis.PyQt.QtCore import QUrl, pyqtSignal
from PyQt5.QtWebEngineWidgets import QWebEngineView


class HelpPanel(QWidget):
    switch_to_previous_tab = pyqtSignal()

    def __init__(self):
        super().__init__()

        # Set up the layout and web engine view
        self.layout = QVBoxLayout(self)
        self.web_view = QWebEngineView()

        # Load the URL
        self.web_view.setUrl(QUrl("https://worldbank.github.io/GEEST/README.html"))

        # Add the web view to the layout
        self.layout.addWidget(self.web_view)

        back_button = QPushButton("Back")
        back_button.clicked.connect(self.switch_to_previous_tab)
        self.layout.addWidget(back_button)

        # Set the layout for the widget
        self.setLayout(self.layout)
