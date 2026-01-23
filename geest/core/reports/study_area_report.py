# -*- coding: utf-8 -*-
"""📦 Study Area Report module.

This module contains functionality for study area report.
"""

from qgis.core import (
    QgsLayout,
    QgsLayoutItemLabel,
    QgsLayoutPoint,
    QgsProject,
    QgsUnitTypes,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QFont

from geest.utilities import log_message, resources_path

from .base_report import BaseReport


class StudyAreaReport(BaseReport):
    """
    A class to generate a PDF report from a GeoPackage table of study area creation status data.

    The report computes summary statistics (based on the field "geom_total_duration_secs")
    and creates a QGIS layout (report) that is then exported to PDF.
    """

    def __init__(self, gpkg_path: str, report_name="Study Area Creation Report"):
        """
        Initialize the report.

        Parameters:
            layer_input (str): A file path to the GeoPackage (from which the
                layer "study_area_creation_status" and other layers will be loaded).
            report_name (str): The title to use for the report.

        Raises:
            ValueError: If the layer cannot be loaded from the given file path.
            TypeError: If layer_input is neither a string nor a QgsVectorLayer.
        """
        template_path = resources_path("resources", "qpt", "study_area_report_template.qpt")
        super().__init__(template_path, report_name)

        self.layers = None  # Will hold the loaded layers from the GeoPackage

        uri = f"{gpkg_path}|layername=study_area_creation_status"
        self.gpkg_path = gpkg_path
        layer = QgsVectorLayer(uri, "study_area_creation_status", "ogr")
        if not layer.isValid():
            raise ValueError("Failed to load layer from the given file path.")

        self.report_name = report_name
        self.load_layers_from_gpkg()
        self.template_path = resources_path("resources", "qpt", "study_area_report_template.qpt")
        self.page_descriptions = {}
        self.page_descriptions[
            "study_area_bbox"
        ] = """
        The study area bounding box (bbox) is the outer extent of the entire study area.
        The bounding box width and height is guaranteed to be a factor of the
        analysis dimension. All other data products are then aligned to this bbox.
        """
        self.page_descriptions[
            "study_area_bboxes"
        ] = """
        The study area bboxes are a set of smaller bounding boxes that surround each
        polygon in the study area. They are grid aligned such that the origin and
        furthest corners are guaranteed to be a factor of the analysis dimension
        apart.
        """
        self.page_descriptions[
            "study_area_polygons"
        ] = """
        The study area polygons are the single part form of all polygons in the
        study area. Any invalid geometries will have been discarded.
        """
        self.page_descriptions[
            "study_area_grid"
        ] = """
        The study area grid is a set of polygon squares that each have the
        x and y dimension of the analysis cell size. They are guaranteed to
        be aligned to the study area bbox and bboxes layers. The grid is used
        to create a version of the study_area_polygons that have been expanded
        out so that the edges align exactly to the grid.

        The grid is also used to perform certain types of spatial analysis such as
        the Active Transport layer analyses.
        """
        self.page_descriptions[
            "chunks"
        ] = """
        The chunks are the result of splitting the study area grid into smaller
        chunks that are used to process the study area more efficiently. Each chunk
        is labelled as to whether it is inside, on the edge of, or outside the
        geometry of a study area polygon. Grid cells in chunks that are 'inside' can be processed
        more efficiently as we can skip the intersection test with the study area polygons.
        """
        self.page_descriptions[
            "study_area_clip_polygons"
        ] = """
        The study area clip polygons are the original polygon areas but expanded so that the edges
        of the polygon exactly coincide with the edges of the grid. This will ensure that all analysis
        results are coherant with the grid."""
        self.page_descriptions[
            "study_area_creation_status"
        ] = """
        The study area creation status is a record of the time taken to process each part of the study area.
        """
        self.page_descriptions[
            "ghsl_settlements"
        ] = """
        The Global Human Settlement Layer is used to identify settled areas within the study region. Study area polygons are marked with whether they intersect GHSL settlement data, which is used in various analysis workflows.
        """
        self._cleanup_done = False

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures cleanup happens."""
        self.cleanup()
        return False  # Don't suppress exceptions

    def cleanup(self):
        """
        Explicitly clean up layers. Call this when done with the report,
        or use the context manager pattern.
        """
        if self._cleanup_done:
            return
        if self.layers:
            for layer_name, layer in self.layers.items():
                if layer and layer.isValid():
                    try:
                        QgsProject.instance().removeMapLayer(layer.id())
                        log_message(f"Layer '{layer_name}' removed from project.")
                    except Exception as e:
                        log_message(f"Could not remove layer '{layer_name}': {e}")
            self.layers = None
        self._cleanup_done = True

    def compute_ghsl_statistics(self):
        """
        Compute GHSL intersection statistics from the study_area_polygons layer.

        Returns:
            dict: A dictionary containing 'total', 'intersects', 'percentage', and 'has_ghsl'.
                  Returns None if GHSL data is not available.
        """
        uri = f"{self.gpkg_path}|layername=study_area_polygons"
        layer = QgsVectorLayer(uri, "study_area_polygons", "ogr")

        if not layer.isValid():
            return None

        # Check if intersects_ghsl field exists
        field_names = [field.name() for field in layer.fields()]
        if "intersects_ghsl" not in field_names:
            return None

        total_count = 0
        intersects_count = 0

        for feat in layer.getFeatures():
            total_count += 1
            intersects_ghsl = feat["intersects_ghsl"]
            if intersects_ghsl == 1:
                intersects_count += 1

        if total_count == 0:
            return None

        percentage = (intersects_count / total_count) * 100

        return {
            "total": total_count,
            "intersects": intersects_count,
            "percentage": percentage,
            "has_ghsl": True,
        }

    def compute_study_area_creation_statistics(self, field_name="geom_total_duration_secs"):
        """
        Compute statistical summary for a given field in the layer.

        Parameters:
            field_name (str): The attribute field on which to compute statistics.

        Returns:
            dict: A dictionary containing 'count', 'min', 'max', 'mean', 'sum', and 'std_dev'.
        """
        values = []
        uri = f"{self.gpkg_path}|layername=study_area_creation_status"
        layer = QgsVectorLayer(uri, "study_area_creation_status", "ogr")
        for feat in layer.getFeatures():
            val = feat[field_name]
            if val is not None:
                values.append(val)
        if not values:
            raise ValueError(f"No valid data found for field '{field_name}'.")

        count_val = len(values)
        sum_val = sum(values)
        min_val = min(values)
        max_val = max(values)
        mean_val = sum_val / count_val
        # Compute population standard deviation
        var = sum((x - mean_val) ** 2 for x in values) / count_val
        std_dev = var**0.5

        return {
            "count": count_val,
            "min": min_val,
            "max": max_val,
            "mean": mean_val,
            "sum": sum_val,
            "std_dev": std_dev,
        }

    def add_ghsl_info_to_page(self, current_page):
        """
        Add GHSL statistics and acknowledgements to ghsl page.

        Parameters:
            current_page (int): The page number where the GHSL info should be added.
        """
        ghsl_stats = self.compute_ghsl_statistics()
        if ghsl_stats:
            info_text = (
                f"GHSL Statistics:\n"
                f"Total polygons: {ghsl_stats['total']}\n"
                f"With settlements: {ghsl_stats['intersects']}\n"
                f"Percentage: {ghsl_stats['percentage']:.1f}%\n\n"
                f"Source: Copernicus/EC JRC\n"
                f"Product: GHS-SMOD R2023A\n"
                f"License: CC BY 4.0"
            )

            info_label = QgsLayoutItemLabel(self.layout)
            info_label.setText(info_text)
            info_label.setFont(QFont("Arial", 12))
            info_label.adjustSizeToText()
            info_label.attemptMove(QgsLayoutPoint(10, 60, QgsUnitTypes.LayoutMillimeters), page=current_page)
            self.layout.addLayoutItem(info_label)

    def create_layout(self):
        """
        Create a QGIS layout (report) that includes a title and a label with summary statistics.

        The layout is stored in the attribute self.layout.
        """
        project = QgsProject.instance()
        self.layout = QgsLayout(project)
        self.layout.initializeDefaults()
        self.load_template()

        # Compute statistics and add a summary label
        stats = self.compute_study_area_creation_statistics()
        summary_text = (
            f"Total parts: {stats['count']}\n"  # noqa E231
            f"Minimum processing time: {stats['min']:.3f} sec\n"  # noqa E231
            f"Maximum processing time: {stats['max']:.3f} sec\n"  # noqa E231
            f"Average processing time: {stats['mean']:.3f} sec\n"  # noqa E231
            f"Total processing time: {stats['sum']:.3f} sec\n"  # noqa E231
            f"Standard Deviation: {stats['std_dev']:.3f} sec"  # noqa E231
        )
        summary_label = QgsLayoutItemLabel(self.layout)
        summary_label.setText(summary_text)
        summary_label.setFont(QFont("Arial", 12))
        summary_label.adjustSizeToText()
        summary_label.attemptMove(QgsLayoutPoint(80, 200, QgsUnitTypes.LayoutMillimeters), page=0)
        self.layout.addLayoutItem(summary_label)

        # Compute and add summary statistics for each layer on separate pages
        current_page = 1
        for page_number, (layer_name, layer) in enumerate(self.layers.items()):
            # Add a new page for each layer
            page = self.make_page(
                title=layer_name, description_key=layer_name, current_page=current_page, show_header_and_footer=True
            )
            del page

            # Add summary label to the current page
            summary_label = QgsLayoutItemLabel(self.layout)
            summary_label.setText(summary_text)
            summary_label.setFont(QFont("Arial", 12))
            summary_label.adjustSizeToText()
            # Position the label on the current page
            summary_label.attemptMove(
                QgsLayoutPoint(120, 60, QgsUnitTypes.LayoutMillimeters),
                page=current_page,
            )
            self.layout.addLayoutItem(summary_label)

            if layer_name == "study_area_creation_status":
                self.make_text_table(
                    vector_layer=layer,
                    sort_column="geom_total_duration_secs",
                    current_page=current_page,
                )
            else:
                layers = [layer]
                crs = layer.crs()
                self.make_map(
                    layers=layers,
                    current_page=current_page,
                    crs=crs,
                )

            # Add GHSL statistics and acknowledgements to the ghsl_settlements page
            if layer_name == "ghsl_settlements":
                self.add_ghsl_info_to_page(current_page)

            current_page += 1
