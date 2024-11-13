from qgis.core import (
    edit,
    Qgis,
    QgsField,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QVariant
from geest.utilities import log_message


def assign_reclassification_to_polygons(layer: QgsVectorLayer) -> QgsVectorLayer:
    """
    Assign reclassification values to polygons based on their perimeter length.

    A value is assigned according to the perimeter thresholds:
    - Very large blocks: value = 1 (perimeter > 1000)
    - Large blocks: value = 2 (751 <= perimeter <= 1000)
    - Moderate blocks: value = 3 (501 <= perimeter <= 750)
    - Small blocks: value = 4 (251 <= perimeter <= 500)
    - Very small blocks: value = 5 (0 < perimeter <= 250)
    - No intersection or invalid: value = 0

    Args:
        layer (QgsVectorLayer): The input polygon layer.

    Returns:
        QgsVectorLayer: The updated polygon layer with reclassification values assigned.
    """

    with edit(layer):  # Allow editing of the layer
        # Check if the 'value' field exists, if not, create it
        if layer.fields().indexFromName("value") == -1:
            layer.dataProvider().addAttributes([QgsField("value", QVariant.Int)])
            layer.updateFields()
        for feature in layer.getFeatures():
            perimeter = (
                feature.geometry().length()
            )  # Calculate the perimeter of the polygon

            log_message(
                f"Perimeter of polygon {feature.id()}: {perimeter}",
                tag="Geest",
                level=Qgis.Info,
            )

            # Assign reclassification value based on the perimeter
            if perimeter > 1000:  # Very large blocks
                reclass_val = 1
            elif 751 <= perimeter <= 1000:  # Large blocks
                reclass_val = 2
            elif 501 <= perimeter <= 750:  # Moderate blocks
                reclass_val = 3
            elif 251 <= perimeter <= 500:  # Small blocks
                reclass_val = 4
            elif 0 < perimeter <= 250:  # Very small blocks
                reclass_val = 5
            else:
                reclass_val = 0  # No valid perimeter or no intersection

            feature.setAttribute("value", reclass_val)  # Set the 'value' field
            layer.updateFeature(feature)  # Update the feature with the new attribute

    return layer
