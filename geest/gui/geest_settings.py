# coding=utf-8
"""This module has the main settings interaction logic for Geest."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

from qgis.PyQt.QtGui import QIcon
from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory
from geest.core import set_setting, setting
from geest.utilities import get_ui_class, resources_path

FORM_CLASS = get_ui_class("geest_settings_base.ui")


class GeestSettings(FORM_CLASS, QgsOptionsPageWidget):
    """Dialog implementation class Geest class."""

    def __init__(self, parent=None):
        """Constructor for the settings buffer dialog.

        :param parent: Parent widget of this dialog.
        :type parent: QWidget

        """
        QgsOptionsPageWidget.__init__(self, parent)
        self.setupUi(self)
        # We need this so we can open the settings to our own
        # page from the plugin button bar.
        self.setObjectName("geest")
        # The maximum number of concurrent threads to allow
        # during rendering. Probably setting to the same number
        # of CPU cores you have would be a good conservative approach
        # You could probably run 100 or more on a decently specced machine
        self.spin_thread_pool_size.setValue(
            int(setting(key="concurrent_tasks", default=1))
        )

        # This is intended for developers to attach to the plugin using a
        # remote debugger so that they can step through the code. Do not
        # enable it if you do not have a remote debugger set up as it will
        # block QGIS startup until a debugger is attached to the process.
        # Requires restart after changing.
        debug_mode = int(setting(key="debug_mode", default=0))
        if debug_mode:
            self.debug_mode_checkbox.setChecked(True)
        else:
            self.debug_mode_checkbox.setChecked(False)
        # Adds verbose log message, useful for diagnostics
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            self.verbose_mode_checkbox.setChecked(True)
        else:
            self.verbose_mode_checkbox.setChecked(False)
        # ORS API key
        ors_key = setting(key="ors_key", default="")
        if ors_key:
            self.ors_key_line_edit.setText(ors_key)
        else:
            self.ors_key_line_edit.setPlaceholderText("Enter your ORS API key here")
        ors_request_size = int(setting(key="ors_request_size", default=5))
        self.ors_request_size.setValue(ors_request_size)

        chunk_size = int(setting(key="chunk_size", default=50))
        self.chunk_size.setValue(chunk_size)

        zero_default = bool(setting(key="default_raster_to_0", default=0))
        self.default_raster_to_0.setChecked(bool(zero_default))

        show_layer_on_click = setting(key="show_layer_on_click", default=False)
        self.show_layer_on_click.setChecked(bool(show_layer_on_click))

    def apply(self):
        """Process the animation sequence.

        .. note:: This is called on OK click.
        """
        set_setting(
            key="concurrent_tasks",
            value=self.spin_thread_pool_size.value(),
        )

        if self.debug_mode_checkbox.isChecked():
            set_setting(key="debug_mode", value=1)
        else:
            set_setting(key="debug_mode", value=0)

        if self.verbose_mode_checkbox.isChecked():
            set_setting(key="verbose_mode", value=1)
        else:
            set_setting(key="verbose_mode", value=0)

        set_setting(key="ors_key", value=self.ors_key_line_edit.text())
        set_setting(key="ors_request_size", value=self.ors_request_size.value())
        set_setting(key="chunk_size", value=self.chunk_size.value())
        set_setting(
            key="default_raster_to_0", value=self.default_raster_to_0.isChecked()
        )
        set_setting(
            key="show_layer_on_click", value=self.show_layer_on_click.isChecked()
        )


class GeestOptionsFactory(QgsOptionsWidgetFactory):
    """
    Factory class for Geest options widget
    """

    def __init__(self):  # pylint: disable=useless-super-delegation
        super().__init__()
        self.setTitle("Geest")

    def icon(self):  # pylint: disable=missing-function-docstring
        return QIcon(resources_path("resources", "geest-settings.svg"))

    def createWidget(self, parent):  # pylint: disable=missing-function-docstring
        return GeestSettings(parent)
