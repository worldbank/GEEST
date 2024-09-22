from qgis.PyQt.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QRadioButton,
    QLabel,
    QButtonGroup,
    QLineEdit,
    QCheckBox,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QFileDialog,
)
from qgis.PyQt.QtCore import Qt
from qgis.gui import QgsMapLayerComboBox, QgsFileWidget
from qgis.core import QgsMapLayer, QgsMapLayerProxyModel, QgsVectorLayer


class GeestWidgetFactory:
    valid_subtypes = {
        "point": "point",
        "line": "line",
        "polyline": "line",
        "polygon": "polygon",
        "raster": "raster",
        "vector": "vector",
    }

    @staticmethod
    def safe_float(value, default):
        try:
            return float(value) if value != '' else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_int(value, default):
        try:
            return int(float(value)) if value != '' else default
        except (ValueError, TypeError):
            return default

    @staticmethod
    def create_widgets(layer_data: dict, parent=None):
        use_keys_mapping = {
            "Use Default Index Score": {
                "label": "Default Index Score",
                "type": "doublespinbox",
                "min": 0.0,
                "max": 100.0,
                "decimals": 1,
                "default": layer_data.get("Default Index Score", 0.0),
                "tooltip": "The default index score value."
            },
            "Use Multi Buffer Point": {
                "label": "Multi Buffer Distances",
                "type": "lineedit",
                "default": layer_data.get("Default Multi Buffer Distances", ""),
                "tooltip": "Enter comma-separated buffer distances."
            },
            "Use Single Buffer Point": {
                "label": "Single Buffer Distance",
                "type": "spinbox",
                "min": 0,
                "max": 10000,
                "default": layer_data.get("Default Single Buffer Distance", 0),
                "tooltip": "Enter buffer distance."
            },
            "Use Create Grid": {
                "label": "Pixel Size",
                "type": "spinbox",
                "min": 0,
                "max": 10000,
                "default": layer_data.get("Default pixel", 0),
                "tooltip": "Enter pixel size for grid creation."
            },
            "Use Add Layers Manually": {
                "label": "Add Layers Manually",
                "description": "Using this option, you can add layers manually.",
                "type": "layer_selector",
                "layer_type": "vector",
                "tooltip": "Select a vector layer."
            },
            "Use Classify Poly into Classes": {
                "label": "Classify Polygons into Classes",
                "description": "Using this option, you can classify polygons into classes.",
                "type": "polygon_layer_with_field_selector",
                "layer_type": "polygon",
                "tooltip": "Select a polygon layer."
            },
            "Use CSV to Point Layer": {
                "label": "Use CSV File",
                "description": "Using this option, you can convert a CSV file to a point layer.",
                "type": "csv_to_point",
                "tooltip": "Select a CSV file and specify longitude and latitude columns."
            },
            "Use Poly per Cell": {
                "label": "Use Polygon Layer",
                "description": "Using this option, create a polygon per grid cell.",
                "type": "layer_selector",
                "layer_type": "polygon",
                "tooltip": "Select a polygon layer."
            },
            "Use Polyline per Cell": {
                "label": "Use Polyline Layer",
                "description": "Using this option, create a polyline per grid cell.",
                "type": "layer_selector",
                "layer_type": "line",
                "tooltip": "Select a line layer."
            },
            "Use Point per Cell": {
                "label": "Use Points Layer",
                "description": "Using this option, create a point per grid cell.",
                "type": "layer_selector",
                "layer_type": "point",
                "tooltip": "Select a point layer."
            },
            "Use Rasterize Layer": {
                "label": "Rasterize Layer",
                "description": "Using this option, you can rasterize a vector layer.",
                "type": "layer_selector",
                "layer_type": "all",
                "tooltip": "Select a raster layer to rasterize."
            },

            "Use OSM Downloader": {
                "label": "Fetch the data from OSM",
                "description": "Using this option, we will try to fetch the data needed for this indicator directly from OSM.",
                "type": "download_option",
                "tooltip": "Download data from OSM."
            },
            "Use WBL Downloader": {
                "label": "Fetch the data from WBL",
                "description": "Using this option, we will try to fetch the data needed for this indicator directly from WBL.",
                "type": "download_option",
                "tooltip": "Download data from WBL."
            },
            "Use Humdata Downloader": {
                "label": "Fetch the data from HumData",
                "description": "Using this option, we will try to fetch the data needed for this indicator directly from HumData.",
                "type": "download_option",
                "tooltip": "Download data from HumData."
            },
            "Use Mapillary Downloader": {
                "label": "Fetch the data from Mapillary",
                "description": "Using this option, we will try to fetch the data needed for this indicator directly from Mapillary.",
                "type": "download_option",
                "tooltip": "Download data from Mapillary."
            },
            "Use Other Downloader": {
                "label": "Fetch the data from specified source",
                "description": f"Using this option, we will try to fetch the data needed for this indicator directly from {layer_data.get('Use Other Downloader', '')}.",
                "type": "download_option",
                "tooltip": f"Download data from {layer_data.get('Use Other Downloader', 'Other Source')}."
            }
        }

        use_keys_enabled = {k: v for k, v in layer_data.items() if k.startswith("Use") and v}

        if not use_keys_enabled:
            return QWidget()

        container = QWidget(parent)
        main_layout = QVBoxLayout()
        container.setLayout(main_layout)

        radio_group = QButtonGroup(container)
        radio_group.setExclusive(True)

        for idx, (use_key, value) in enumerate(use_keys_enabled.items()):
            mapping = use_keys_mapping.get(use_key)
            if not mapping:
                print(f"No mapping found for key: {use_key}. Skipping.")
                continue

            option_container = QWidget()
            option_layout = QVBoxLayout()
            option_container.setLayout(option_layout)

            radio_button = QRadioButton(mapping["label"])
            radio_button.setProperty("use_key", use_key)  # Set property here
            radio_group.addButton(radio_button, id=idx)
            option_layout.addWidget(radio_button)

            if "description" in mapping:
                description_label = QLabel(mapping["description"])
                description_label.setWordWrap(True)
                option_layout.addWidget(description_label)

            widget = GeestWidgetFactory.create_specific_widget(mapping, layer_data)
            if widget:
                widget.setProperty("use_key", use_key)
                option_layout.addWidget(widget)

            main_layout.addWidget(option_container)

            radio_button.toggled.connect(lambda checked, w=widget: w.setEnabled(checked))
            widget.setEnabled(False)  # Initially disable all widgets

        if radio_group.buttons():
            radio_group.buttons()[0].setChecked(True)

        return container

    @staticmethod
    def create_specific_widget(mapping: dict, layer_data: dict):
        """
        Create a specific widget based on the mapping type.

        :param mapping: Dictionary containing widget specifications.
        :param layer_data: Original layer data dictionary.
        :return: QWidget or subclass instance.
        """
        widget_type = mapping["type"]

        if widget_type == "doublespinbox":
            widget = QDoubleSpinBox()
            widget.setMinimum(GeestWidgetFactory.safe_float(mapping.get("min"), 0.0))
            widget.setMaximum(GeestWidgetFactory.safe_float(mapping.get("max"), 100.0))
            widget.setDecimals(GeestWidgetFactory.safe_int(mapping.get("decimals"), 1))
            widget.setValue(GeestWidgetFactory.safe_float(mapping.get("default"), 0.0))
            widget.setToolTip(mapping.get("tooltip", ""))
            return widget

        elif widget_type == "spinbox":
            widget = QSpinBox()
            widget.setMinimum(GeestWidgetFactory.safe_int(mapping.get("min"), 0))
            widget.setMaximum(GeestWidgetFactory.safe_int(mapping.get("max"), 10000))
            widget.setValue(GeestWidgetFactory.safe_int(mapping.get("default"), 0))
            widget.setToolTip(mapping.get("tooltip", ""))
            return widget

        elif widget_type == "lineedit":
            widget = QLineEdit()
            default_value = mapping.get("default", "")
            widget.setText(str(default_value))
            widget.setToolTip(mapping.get("tooltip", ""))
            return widget

        elif widget_type == "layer_selector":
            widget = QgsMapLayerComboBox()
            layer_type = mapping.get("layer_type", "vector").lower()
            if layer_type == "all":
                widget.setFilters(QgsMapLayerProxyModel.All)
            elif layer_type == "vector":
                widget.setFilters(QgsMapLayerProxyModel.VectorLayer)
            elif layer_type == "raster":
                widget.setFilters(QgsMapLayerProxyModel.RasterLayer)
            elif layer_type in ["polygon", "line", "point"]:
                subtype_mapped = GeestWidgetFactory.valid_subtypes.get(layer_type)
                if subtype_mapped == "polygon":
                    widget.setFilters(QgsMapLayerProxyModel.PolygonLayer)
                elif subtype_mapped == "line":
                    widget.setFilters(QgsMapLayerProxyModel.LineLayer)
                elif subtype_mapped == "point":
                    widget.setFilters(QgsMapLayerProxyModel.PointLayer)
                else:
                    print(f"Invalid layer subtype '{layer_type}' for '{mapping.get('label')}'. Defaulting to all vector layers.")
                    widget.setFilters(QgsMapLayerProxyModel.VectorLayer)
            else:
                print(f"Unknown layer type '{layer_type}' for '{mapping.get('label')}'. Defaulting to all layers.")
                widget.setFilters(QgsMapLayerProxyModel.All)

            # Check if layers are available
            if widget.count() == 0:
                label = QLabel("<No appropriate layer found>")
                return label

            else:
                widget.setToolTip(mapping.get("tooltip", ""))
                return widget

        elif widget_type == "polygon_layer_with_field_selector":
            container = QWidget()
            layout = QVBoxLayout()
            container.setLayout(layout)

            # Layer selector
            layer_label = QLabel("Select Polygon Layer:")
            layout.addWidget(layer_label)
            layer_selector = QgsMapLayerComboBox()
            layer_selector.setFilters(QgsMapLayerProxyModel.PolygonLayer)
            layout.addWidget(layer_selector)

            # Field selector
            field_label = QLabel("Select Field of Interest:")
            layout.addWidget(field_label)
            field_selector = QComboBox()
            layout.addWidget(field_selector)

            # Update field selector when layer changes
            def update_fields():
                field_selector.clear()
                layer = layer_selector.currentLayer()
                if isinstance(layer, QgsVectorLayer):
                    field_selector.addItems([field.name() for field in layer.fields()])

            layer_selector.layerChanged.connect(update_fields)

            # Initial population of fields
            update_fields()

            container.setToolTip(mapping.get("tooltip", ""))
            return container

        elif widget_type == "csv_to_point":
            container = QWidget()
            layout = QVBoxLayout()
            container.setLayout(layout)

            # Create QgsFileWidget
            file_widget = QgsFileWidget(parent=container)
            file_widget.setFilter("CSV Files (*.csv);;All Files (*.*)")
            file_widget.setToolTip(
                mapping.get("tooltip", "Select a CSV file containing longitude and latitude columns."))
            layout.addWidget(file_widget)

            # Create layouts for longitude and latitude columns
            lon_layout = QVBoxLayout()
            lat_layout = QVBoxLayout()

            # Create and add label for Longitude
            lon_label = QLabel("Longitude column")
            lon_layout.addWidget(lon_label)

            # Create ComboBox for Longitude
            longitude_combo = QComboBox()
            longitude_combo.setPlaceholderText("Longitude Column")
            longitude_combo.setEnabled(False)
            longitude_combo.setToolTip("Select the column for longitude.")
            lon_layout.addWidget(longitude_combo)

            # Create and add label for Latitude
            lat_label = QLabel("Latitude column")
            lat_layout.addWidget(lat_label)

            # Create ComboBox for Latitude
            latitude_combo = QComboBox()
            latitude_combo.setPlaceholderText("Latitude Column")
            latitude_combo.setEnabled(False)
            latitude_combo.setToolTip("Select the column for latitude.")
            lat_layout.addWidget(latitude_combo)

            # Add the longitude and latitude layouts to the main layout
            layout.addLayout(lon_layout)
            layout.addLayout(lat_layout)

            # Connect file selection to populate and auto-fill combo boxes
            file_widget.fileChanged.connect(
                lambda path: GeestWidgetFactory.populate_csv_columns(path, longitude_combo, latitude_combo)
            )
            return container

        elif widget_type == "download_option":
            container = QWidget()
            layout = QVBoxLayout()
            container.setLayout(layout)
            return container

        else:
            print(f"Unknown widget type: {widget_type}")
            return None

    @staticmethod
    def populate_csv_columns(file_path: str, lon_combo: QComboBox, lat_combo: QComboBox):
        """
        Populate the longitude and latitude combo boxes based on the CSV file's headers.
        Auto-select columns if 'longitude'/'lon' and 'latitude'/'lat' are found.
        """
        import csv

        if not file_path:
            return

        try:
            with open(file_path, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                headers = next(reader)
                lon_combo.clear()
                lat_combo.clear()
                lon_combo.addItems(headers)
                lat_combo.addItems(headers)

                # Auto-select longitude column
                lon_candidates = ['longitude', 'lon']
                selected_lon = next((header for header in headers if header.lower() in lon_candidates), None)
                if selected_lon:
                    index = headers.index(selected_lon)
                    lon_combo.setCurrentIndex(index)

                # Auto-select latitude column
                lat_candidates = ['latitude', 'lat']
                selected_lat = next((header for header in headers if header.lower() in lat_candidates), None)
                if selected_lat:
                    index = headers.index(selected_lat)
                    lat_combo.setCurrentIndex(index)

                lon_combo.setEnabled(True)
                lat_combo.setEnabled(True)
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            lon_combo.clear()
            lat_combo.clear()
            lon_combo.setEnabled(False)
            lat_combo.setEnabled(False)
