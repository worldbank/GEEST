from qgis.core import (
    QgsProject,
    QgsPrintLayout,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsReadWriteContext,
    QgsLayoutExporter,
    QgsVectorLayer,
)
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtGui import QFont, QColor


class TemplatedStudyAreaReport:
    """
    A class to manage QGIS Print Layouts by loading templates, modifying label text,
    setting map layers, and exporting the final layout to a PDF.

    Attributes:
        project (QgsProject): The QGIS project instance.
        layout (QgsPrintLayout): The print layout instance.
    """

    def __init__(self, template_path):
        """
        Initializes the QGISLayoutManager with a specified template.

        Args:
            template_path (str): The file path to the QPT template.

        Raises:
            FileNotFoundError: If the template file does not exist or cannot be read.
            ValueError: If the template content is invalid or cannot be loaded.
        """
        self.layout = QgsPrintLayout(self.project)
        self.layout.initializeDefaults()

        # Load the QPT template
        try:
            with open(template_path, "r") as template_file:
                template_content = template_file.read()
        except IOError:
            raise FileNotFoundError(
                f"Template file '{template_path}' not found or cannot be read."
            )

        document = QDomDocument()
        if not document.setContent(template_content):
            raise ValueError(
                f"Failed to parse the template content from '{template_path}'."
            )

        context = QgsReadWriteContext()
        if not self.layout.loadFromTemplate(document, context):
            raise ValueError(
                f"Failed to load the template into the layout from '{template_path}'."
            )

    def set_label_text(self, label_id, text, font_name="Arial", font_size=12):
        """
        Sets the text and font properties of a label item in the layout.

        Args:
            label_id (str): The ID of the label item in the template.
            text (str): The text to set for the label.
            font_name (str, optional): The font family for the label text. Defaults to "Arial".
            font_size (int, optional): The font size for the label text. Defaults to 12.

        Raises:
            KeyError: If the label item with the specified ID is not found in the layout.
            TypeError: If the item with the specified ID is not a QgsLayoutItemLabel.
        """
        label = self.layout.itemById(label_id)
        if label is None:
            raise KeyError(f"Label item with ID '{label_id}' not found in the layout.")
        if not isinstance(label, QgsLayoutItemLabel):
            raise TypeError(f"Item with ID '{label_id}' is not a QgsLayoutItemLabel.")

        label.setText(text)
        label.setFont(QFont(font_name, font_size))
        label.adjustSizeToText()

    def set_map_layers(self, map_item_id, layer_paths):
        """
        Sets the layers for a map item in the layout based on provided file paths.

        Args:
            map_item_id (str): The ID of the map item in the template.
            layer_paths (list of str): A list of file paths to the vector layers to be added.

        Raises:
            KeyError: If the map item with the specified ID is not found in the layout.
            TypeError: If the item with the specified ID is not a QgsLayoutItemMap.
            ValueError: If any of the provided layer paths are invalid or the layers cannot be loaded.
        """
        map_item = self.layout.itemById(map_item_id)
        if map_item is None:
            raise KeyError(f"Map item with ID '{map_item_id}' not found in the layout.")
        if not isinstance(map_item, QgsLayoutItemMap):
            raise TypeError(f"Item with ID '{map_item_id}' is not a QgsLayoutItemMap.")

        layers = []
        for path in layer_paths:
            layer = QgsVectorLayer(path, path.split("/")[-1], "ogr")
            if not layer.isValid():
                raise ValueError(f"Failed to load layer from path '{path}'.")
            self.project.addMapLayer(layer)
            layers.append(layer)

        map_item.setLayers(layers)
        if layers:
            map_item.setExtent(layers[0].extent())
        map_item.setFrameEnabled(True)
        map_item.setFrameStrokeColor(QColor(0, 0, 0))
        map_item.setFrameStrokeWidth(0.5)
        map_item.refresh()

    def export_to_pdf(self, output_path):
        """
        Exports the current layout to a PDF file.

        Args:
            output_path (str): The file path where the PDF will be saved.

        Returns:
            bool: True if the export is successful, False otherwise.
        """
        exporter = QgsLayoutExporter(self.layout)
        result = exporter.exportToPdf(
            output_path, QgsLayoutExporter.PdfExportSettings()
        )
        return result == QgsLayoutExporter.Success
