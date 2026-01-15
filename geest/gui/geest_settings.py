# coding=utf-8
"""This module has the main settings interaction logic for Geest."""

__copyright__ = "Copyright 2022, Tim Sutton"
__license__ = "GPL version 3"
__email__ = "tim@kartoza.com"
__revision__ = "$Format:%H$"

import os

from qgis.core import QgsApplication
from qgis.gui import QgsOptionsPageWidget, QgsOptionsWidgetFactory
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QFileDialog
from qgis.PyQt.QtCore import QSettings

from geest.core.constants import APPLICATION_NAME
from geest.core.settings import set_setting, setting
from geest.utilities import get_ui_class, log_message, resources_path

FORM_CLASS = get_ui_class("geest_settings_base.ui")


class GeestSettings(FORM_CLASS, QgsOptionsPageWidget):
    """Dialog implementation class Geest class."""

    def __init__(self, parent=None):
        """Constructor for the settings buffer dialog.

        Args:
            parent: Parent widget of this dialog.
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
        self.spin_thread_pool_size.setValue(int(setting(key="concurrent_tasks", default=1)))

        # This provides more verbose logging output
        # and keeps intermediate working files around
        developer_mode = int(setting(key="developer_mode", default=0))
        if developer_mode:
            self.developer_mode_checkbox.setChecked(True)
        else:
            self.developer_mode_checkbox.setChecked(False)
        # Adds verbose log message, useful for diagnostics
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            self.verbose_mode_checkbox.setChecked(True)
        else:
            self.verbose_mode_checkbox.setChecked(False)

        chunk_size = int(setting(key="chunk_size", default=50))
        self.chunk_size.setValue(chunk_size)

        grid_creation_workers = int(setting(key="grid_creation_workers", default=4))
        self.grid_creation_workers.setValue(grid_creation_workers)

        zero_default = bool(setting(key="default_raster_to_0", default=0))
        self.default_raster_to_0.setChecked(bool(zero_default))

        show_layer_on_click = setting(key="show_layer_on_click", default=True)
        self.show_layer_on_click.setChecked(bool(show_layer_on_click))

        show_overlay = setting(key="show_overlay", default=True)
        self.show_overlay.setChecked(bool(show_overlay))

        show_pie_overlay = setting(key="show_pie_overlay", default=False)
        self.show_pie_overlay.setChecked(bool(show_pie_overlay))
        experimental_features = int(os.getenv("GEEST_EXPERIMENTAL", 0))
        log_message(f"GEEST_EXPERIMENTAL environment variable is set to: {experimental_features}")
        self.show_pie_overlay.hide()

        if experimental_features:
            log_message("Experimental features are enabled.")
            self.show_pie_overlay.show()
        else:
            log_message("Experimental features are disabled.")

        # Ookla threshold settings
        ookla_use_thresholds = bool(setting(key="ookla_use_thresholds", default=False))
        self.ookla_use_thresholds.setChecked(ookla_use_thresholds)

        ookla_mobile_threshold = float(setting(key="ookla_mobile_threshold", default=0.0))
        self.ookla_mobile_threshold.setValue(ookla_mobile_threshold)

        ookla_fixed_threshold = float(setting(key="ookla_fixed_threshold", default=0.0))
        self.ookla_fixed_threshold.setValue(ookla_fixed_threshold)

        settings_key_cache = f"{APPLICATION_NAME}/ookla_use_local_cache"
        qsettings = QSettings()
        if not qsettings.contains(settings_key_cache):
            set_setting(key="ookla_use_local_cache", value=True)
        ookla_use_local_cache = bool(setting(key="ookla_use_local_cache", default=True))
        self.ookla_use_local_cache.setChecked(ookla_use_local_cache)

        settings_key_cache_dir = f"{APPLICATION_NAME}/ookla_local_cache_dir"
        ookla_cache_dir = setting(key="ookla_local_cache_dir", default="")
        if not ookla_cache_dir:
            ookla_cache_dir = os.path.join(
                QgsApplication.qgisSettingsDirPath(), "python", "ookla_cache", "parquet"
            )
            if not qsettings.contains(settings_key_cache_dir):
                set_setting(key="ookla_local_cache_dir", value=ookla_cache_dir)
        self.ookla_cache_dir.setText(ookla_cache_dir)
        self.ookla_cache_dir_browse.clicked.connect(self._select_ookla_cache_dir)

        # GHSL filter setting
        filter_study_areas_by_ghsl = bool(setting(key="filter_study_areas_by_ghsl", default=True))
        self.filter_study_areas_by_ghsl.setChecked(filter_study_areas_by_ghsl)

    def apply(self):
        """Process the animation sequence.

        .. note:: This is called on OK click.
        """
        set_setting(
            key="concurrent_tasks",
            value=self.spin_thread_pool_size.value(),
        )

        if self.developer_mode_checkbox.isChecked():
            set_setting(key="developer_mode", value=1)
        else:
            set_setting(key="developer_mode", value=0)

        if self.verbose_mode_checkbox.isChecked():
            set_setting(key="verbose_mode", value=1)
        else:
            set_setting(key="verbose_mode", value=0)

        set_setting(key="chunk_size", value=self.chunk_size.value())
        set_setting(key="grid_creation_workers", value=self.grid_creation_workers.value())
        set_setting(key="default_raster_to_0", value=self.default_raster_to_0.isChecked())
        set_setting(key="show_layer_on_click", value=self.show_layer_on_click.isChecked())
        set_setting(key="show_overlay", value=self.show_overlay.isChecked())
        set_setting(key="show_pie_overlay", value=self.show_pie_overlay.isChecked())
        set_setting(key="ookla_use_thresholds", value=self.ookla_use_thresholds.isChecked())
        set_setting(key="ookla_mobile_threshold", value=self.ookla_mobile_threshold.value())
        set_setting(key="ookla_fixed_threshold", value=self.ookla_fixed_threshold.value())
        set_setting(key="ookla_use_local_cache", value=self.ookla_use_local_cache.isChecked())
        set_setting(key="ookla_local_cache_dir", value=self.ookla_cache_dir.text())
        set_setting(key="filter_study_areas_by_ghsl", value=self.filter_study_areas_by_ghsl.isChecked())

    def _select_ookla_cache_dir(self):
        """Select local cache directory for Ookla parquet files."""
        current_dir = self.ookla_cache_dir.text()
        directory = QFileDialog.getExistingDirectory(self, "Select Ookla Cache Directory", current_dir)
        if directory:
            self.ookla_cache_dir.setText(directory)


class GeestOptionsFactory(QgsOptionsWidgetFactory):
    """
    Factory class for Geest options widget
    """

    def __init__(self):  # pylint: disable=useless-super-delegation
        """🏗️ Initialize the instance."""
        super().__init__()
        self.setTitle("Geest")

    def icon(self):  # pylint: disable=missing-function-docstring
        """⚙️ Icon.

        Returns:
            The result of the operation.
        """
        return QIcon(resources_path("resources", "geest-settings.svg"))

    def createWidget(self, parent):  # pylint: disable=missing-function-docstring
        """⚙️ Createwidget.

        Args:
            parent: Parent.

        Returns:
            The result of the operation.
        """
        return GeestSettings(parent)
