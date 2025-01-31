from PyQt5.QtWidgets import (
    QWidget,
)
from qgis.PyQt.QtCore import QUrl, pyqtSignal
from qgis.PyQt.QtGui import QPixmap, QDesktopServices, QFont
from qgis.PyQt.QtWidgets import QMessageBox
from geest.core.tasks import OrsCheckerTask
from geest.utilities import (
    get_ui_class,
    resources_path,
    log_message,
    linear_interpolation,
)
from geest.core import setting, set_setting
from geest.core import WorkflowQueueManager
from geest.gui.widgets import CustomBannerLabel

FORM_CLASS = get_ui_class("ors_panel_base.ui")


class OrsPanel(FORM_CLASS, QWidget):
    switch_to_next_tab = pyqtSignal()  # Signal to notify the parent to switch tabs
    switch_to_previous_tab = pyqtSignal()  # Signal to notify the parent to switch tabs

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GEEST")
        # Dynamically load the .ui file
        self.setupUi(self)
        log_message(f"Loading ORS panel")
        self.initUI()
        self.queue_manager = WorkflowQueueManager(pool_size=1)
        self.set_font_size()

    def initUI(self):
        self.custom_label = CustomBannerLabel(
            "The Gender Enabling Environments Spatial Tool",
            resources_path("resources", "geest-banner.png"),
        )
        parent_layout = self.banner_label.parent().layout()
        parent_layout.replaceWidget(self.banner_label, self.custom_label)
        self.banner_label.deleteLater()
        parent_layout.update()

        self.status_label.setPixmap(
            QPixmap(resources_path("resources", "images", "ors-not-configured.png"))
        )
        self.next_button.clicked.connect(self.on_next_button_clicked)
        # Connect the rich text label's linkActivated signal to open URLs in browser
        self.description.linkActivated.connect(self.open_link_in_browser)
        self.check_key_button.clicked.connect(self.check_ors_key)
        ors_key = setting("ors_key", "")
        self.ors_key_line_edit.setText(ors_key)

    def check_ors_key(self):
        """Check the ORS API key."""
        ors_key = self.ors_key_line_edit.text()
        if not ors_key:
            QMessageBox.critical(self, "Error", "Please enter an ORS API key.")
            return
        set_setting("ors_key", ors_key)
        try:
            checker = OrsCheckerTask(url="https://api.openrouteservice.org")
            task = self.queue_manager.add_task(checker)
            task.job_finished.connect(lambda success: self.task_completed(success))
            self.queue_manager.start_processing()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error checking ORS key: {e}")
            return

    def task_completed(self, result):
        """Handle the result of the ORS key check."""
        if result:
            # Get the icon from the resource_path
            self.status_label.setPixmap(
                QPixmap(resources_path("resources", "images", "ors-ok.png"))
            )
        else:
            self.status_label.setPixmap(
                QPixmap(resources_path("resources", "images", "ors-error.png"))
            )

    def open_link_in_browser(self, url: str):
        """Open the given URL in the user's default web browser using QDesktopServices."""
        QDesktopServices.openUrl(QUrl(url))

    def on_next_button_clicked(self):
        self.switch_to_next_tab.emit()

    def on_previous_button_clicked(self):
        self.switch_to_previous_tab.emit()

    def resizeEvent(self, event):
        self.set_font_size()
        super().resizeEvent(event)

    def set_font_size(self):
        # Scale the font size to fit the text in the available space
        # log_message(f"Label Width: {self.description.rect().width()}")
        # scale the font size linearly from 16 pt to 8 ps as the width of the panel decreases
        font_size = int(
            linear_interpolation(self.description.rect().width(), 12, 16, 400, 600)
        )
        # log_message(f"Label Font Size: {font_size}")
        self.description.setFont(QFont("Arial", font_size))
