# -*- coding: utf-8 -*-
"""📦 Workflow Base module.

This module contains functionality for workflow base.
"""

import datetime
import os
import sqlite3
import traceback
from abc import abstractmethod
from typing import Optional

from qgis import processing
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeedback,
    QgsGeometry,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingFeedback,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QObject, QSettings, pyqtSignal

from geest.core import JsonTreeItem, setting
from geest.core.algorithms import (
    AreaIterator,
    GHSLDownloader,
    GHSLProcessor,
    check_and_reproject_layer,
    combine_rasters_to_vrt,
    geometry_to_memory_layer,
    subset_vector_layer,
)
from geest.core.constants import GDAL_OUTPUT_DATA_TYPE
from geest.core.grid_column_utils import (
    rasterize_grid_column,
    write_raster_values_to_grid,
)
from geest.utilities import log_layer_count, log_message, resources_path


class WorkflowBase(QObject):
    """
    Abstract base class for all workflows.
    Every workflow must accept an attributes dictionary and a QgsFeedback object.
    """

    # Signal for progress changes - will be propagated to the task that owns this workflow
    progressChanged = pyqtSignal(float)
    # Signal for status message changes - shows what step is currently running
    statusChanged = pyqtSignal(str)
    # Signal emitted when the workflow fails - propagated to the UI as an error notification
    workflowError = pyqtSignal(str)

    def __init__(
        self,
        item: JsonTreeItem,
        cell_size_m: float,
        analysis_scale: str,  # local or national
        feedback: QgsFeedback,
        context: QgsProcessingContext,
        working_directory: Optional[str],
    ):
        """
        Initialize the workflow with attributes and feedback.

        Args:
            item: JsonTreeItem object representing the task.
            cell_size_m: The cell size in meters for the analysis.
            analysis_scale: Analysis scale string to determine the workflow e.g. local, national.
            feedback: QgsFeedback object for progress reporting and cancellation.
            context: QgsProcessingContext object for processing. This can be used to pass objects to the thread. e.g. the QgsProject Instance
            working_directory: Folder containing study_area.gpkg and where the outputs will be placed. If not set will be taken from QSettings.

        Raises:
            ValueError: If working directory is not set or study area geopackage is not found.
        """
        super().__init__()
        log_layer_count()  # For performance tuning, write the number of open layers to a log file
        # we will log the layer count again at then end of the workflow
        self.item = item  # ⭐️ This is a reference - whatever you change in this item will directly update the tree
        self.cell_size_m = cell_size_m
        self.analysis_scale = analysis_scale
        self.feedback = feedback  # we connect this to the QgsTask progressUpdated signal
        self.context = context  # QgsProcessingContext
        self.workflow_name = None  # This is set in the concrete class
        # This is set in the setup panel
        self.settings = QSettings()
        # This is the top level folder for work files
        if working_directory:
            log_message(f"Working directory set to {working_directory}")
            self.working_directory = working_directory
        else:
            log_message("Working directory not set. Using last working directory from settings.")
            self.working_directory = self.settings.value("last_working_directory", "")
        if not self.working_directory:
            raise ValueError("Working directory not set.")
        # This is the lower level directory for this workflow's outputs
        self.workflow_directory = self._create_workflow_directory()
        self.gpkg_path: str = os.path.join(self.working_directory, "study_area", "study_area.gpkg")
        if not os.path.exists(self.gpkg_path):
            raise ValueError(f"Study area geopackage not found at {self.gpkg_path}.")
        self.bbox_layer = QgsVectorLayer(f"{self.gpkg_path}|layername=study_area_bbox", "study_area_bbox", "ogr")
        self.bboxes_layer = QgsVectorLayer(f"{self.gpkg_path}|layername=study_area_bboxes", "study_area_bboxes", "ogr")
        self.areas_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_polygons",
            "study_area_polygons",
            "ogr",
        )
        self.clip_areas_layer = QgsVectorLayer(
            f"{self.gpkg_path}|layername=study_area_clip_polygons",
            "study_area_clip_polygons",
            "ogr",
        )
        self.grid_layer = QgsVectorLayer(f"{self.gpkg_path}|layername=study_area_grid", "study_area_grid", "ogr")
        self.features_layer = None  # set in concrete class if needed
        self.raster_layer = None  # set in concrete class if needed
        self.target_crs = self._resolve_target_crs()

        self.result_file_key = "result_file"
        self.result_key = "result"

        # Will be populated by the workflow - use atomic update for thread safety
        self.attributes = self.item.attributes()
        with self.item.atomicAttributeUpdate() as attrs:
            attrs["error"] = None
            attrs["error_file"] = None
            attrs["execution_start_time"] = None
            attrs["execution_end_time"] = None
        # Add prefix based on item role to avoid namespace collisions
        raw_id = self.attributes.get("id", "").lower().replace(" ", "_")
        role = self.item.role if hasattr(self.item, "role") else ""
        if role == "dimension":
            self.layer_id = f"dim_{raw_id}"
        elif role == "factor":
            self.layer_id = f"fac_{raw_id}"
        else:
            self.layer_id = raw_id  # indicators keep raw ID
        self.aggregation = False
        self.analysis_mode = self.item.attribute("analysis_mode", "")
        # Grid-first mode: if True, skip raster-to-grid sampling since grid is already populated
        self.use_grid_first = False
        self.updateProgress(0.0)
        self.output_filename = self.attributes.get("output_filename", "")
        self.feedback.progressChanged.connect(self.updateProgress)

    def _study_area_bbox(self) -> QgsRectangle:
        """
        Get the study area bounding box geometry.

        Returns:
            The bounding box QgsRectangle.
        """

        bbox = self.bbox_layer.extent()

        return bbox

    def _study_area_bbox_4326(self) -> QgsRectangle:
        """
        Get the study area bounding box geometry in EPSG:4326.

        Returns:
            The bounding box QgsRectangle.
        """
        transform = QgsCoordinateTransform(
            self.bbox_layer.crs(),
            QgsCoordinateReferenceSystem("EPSG:4326"),
            QgsProject.instance(),
        )
        bbox = self.bbox_layer.extent()
        bbox = QgsCoordinateTransform.transformBoundingBox(transform, bbox)
        return bbox

    def _resolve_target_crs(self) -> QgsCoordinateReferenceSystem:
        """Resolve the target CRS from the study area GeoPackage.

        First tries ``self.bboxes_layer.crs()``.  If the QGIS OGR provider
        returns an invalid/empty CRS (which can happen when WAL journal files
        leave stale shared-memory state), falls back to reading the CRS
        directly from the ``gpkg_geometry_columns`` / ``gpkg_spatial_ref_sys``
        metadata tables via OGR SQL.
        """
        crs = self.bboxes_layer.crs()
        if crs.isValid() and crs.authid():
            return crs

        log_message(
            "bboxes_layer CRS is invalid or empty — reading CRS from gpkg metadata",
            tag="GeoE3",
            level=Qgis.Warning,
        )
        try:
            from osgeo import ogr

            ds = ogr.Open(self.gpkg_path, 0)
            if ds:
                result = ds.ExecuteSQL(
                    "SELECT gc.srs_id, srs.organization, srs.organization_coordsys_id "
                    "FROM gpkg_geometry_columns gc "
                    "JOIN gpkg_spatial_ref_sys srs ON gc.srs_id = srs.srs_id "
                    "WHERE gc.table_name = 'study_area_bboxes' LIMIT 1"
                )
                if result:
                    feat = result.GetNextFeature()
                    if feat:
                        org = feat.GetField("organization")
                        org_id = feat.GetField("organization_coordsys_id")
                        if org and org_id:
                            crs = QgsCoordinateReferenceSystem(f"{org}:{org_id}")
                            log_message(
                                f"Recovered CRS from gpkg metadata: {crs.authid()}",
                                tag="GeoE3",
                                level=Qgis.Info,
                            )
                    ds.ReleaseResultSet(result)
                ds = None
        except Exception as e:
            log_message(
                f"Failed to read CRS from gpkg metadata: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )

        if not crs.isValid():
            integrity_status = self._quick_check_gpkg()
            raise ValueError(
                f"Could not determine CRS for study area from {self.gpkg_path}. "
                f"GeoPackage integrity check: {integrity_status}."
            )
        return crs

    def _quick_check_gpkg(self) -> str:
        """Run SQLite quick_check on the study area GeoPackage."""
        try:
            connection = sqlite3.connect(self.gpkg_path)
            try:
                cursor = connection.cursor()
                cursor.execute("PRAGMA quick_check;")
                row = cursor.fetchone()
                result = row[0] if row else "unknown"
                return str(result)
            finally:
                connection.close()
        except Exception as error:
            return f"failed ({error})"

    def _check_ghsl_layer_exists(self) -> bool:
        """Check if the GHSL settlements layer exists in the study area GeoPackage.

        Returns:
            True if GHSL layer exists and has features, False otherwise.
        """
        ghsl_layer_path = f"{self.gpkg_path}|layername=ghsl_settlements"
        ghsl_layer = QgsVectorLayer(ghsl_layer_path, "ghsl_check", "ogr")
        if ghsl_layer.isValid() and ghsl_layer.featureCount() > 0:
            log_message(f"GHSL layer found with {ghsl_layer.featureCount()} features")
            return True
        log_message("GHSL layer not found or empty in study_area.gpkg", level="WARNING")
        return False

    def _download_ghsl_data(self) -> bool:
        """Download and process GHSL data for the study area if not already present.

        This method will download GHSL tiles that intersect the study area,
        process them, and add the results to the study_area.gpkg.

        Returns:
            True if GHSL data was successfully downloaded/processed, False otherwise.
        """
        try:
            log_message("Attempting to download GHSL data...")

            # Get study area extent in EPSG:4326 for GHSL download
            extent_4326 = self._study_area_bbox_4326()
            log_message(f"Study area extent (EPSG:4326): {extent_4326.toString()}")

            study_area_dir = os.path.join(self.working_directory, "study_area")

            # Download GHSL tiles
            downloader = GHSLDownloader(
                extents=extent_4326,
                output_path=study_area_dir,
                filename="ghsl_temp",
                use_cache=True,
                delete_existing=False,  # Don't delete if already exists
                feedback=self.feedback,
            )

            tiles = downloader.tiles_intersecting_bbox()
            if not tiles:
                log_message("No GHSL tiles intersect study area", level="WARNING")
                return False

            log_message(f"Downloading {len(tiles)} GHSL tiles...")
            tile_paths = []
            for tile_id in tiles:
                paths = downloader.download_and_unpack_tile(tile_id)
                tile_paths.extend(paths)

            if not tile_paths:
                log_message("No GHSL tiles downloaded", level="WARNING")
                return False

            # Process tiles
            log_message("Processing GHSL tiles...")
            processor = GHSLProcessor(input_raster_paths=tile_paths)

            # Reclassify
            reclassified = processor.reclassify_rasters(suffix="reclass")

            # Polygonize
            polygonized = processor.polygonize_rasters(reclassified)

            # Get extent in Mollweide for combining
            transform_to_mollweide = QgsCoordinateTransform(
                QgsCoordinateReferenceSystem("EPSG:4326"),
                QgsCoordinateReferenceSystem("ESRI:54009"),
                QgsProject.instance(),
            )
            extent_mollweide = transform_to_mollweide.transformBoundingBox(extent_4326)

            # Combine to temporary file
            temp_parquet = os.path.join(study_area_dir, "ghsl_temp.parquet")
            processor.combine_vectors(polygonized, temp_parquet, extent=extent_mollweide)

            # Import to GeoPackage using GDAL
            from osgeo import gdal, ogr

            ghsl_layer_name = "ghsl_settlements"
            translate_options = gdal.VectorTranslateOptions(
                format="GPKG",
                accessMode="append",
                srcSRS="ESRI:54009",
                dstSRS=self.target_crs.authid(),
                layerName=ghsl_layer_name,
                geometryType="PROMOTE_TO_MULTI",
            )

            result = gdal.VectorTranslate(
                self.gpkg_path,
                temp_parquet,
                options=translate_options,
            )

            if result is None:
                log_message("GDAL VectorTranslate failed for GHSL", level="WARNING")
                return False

            result = None  # Close to flush

            # Cleanup temp file
            try:
                if os.path.exists(temp_parquet):
                    os.remove(temp_parquet)
            except OSError:
                pass

            # Verify layer was created
            ds = ogr.Open(self.gpkg_path, 0)
            if ds:
                layer = ds.GetLayerByName(ghsl_layer_name)
                if layer:
                    feature_count = layer.GetFeatureCount()
                    log_message(f"Successfully added {feature_count} GHSL features to GeoPackage")
                    ds = None
                    return True
                ds = None

            return False

        except Exception as e:
            log_message(f"Error downloading GHSL data: {str(e)}", level="WARNING")
            log_message(traceback.format_exc(), level="WARNING")
            return False

    def ensure_ghsl_data(self) -> bool:
        """Ensure GHSL data is available, downloading if necessary.

        This is a public method that workflows can call to ensure GHSL data
        is present before processing.

        Returns:
            True if GHSL data is available, False otherwise.
        """
        if self._check_ghsl_layer_exists():
            return True

        log_message("GHSL data not found, attempting to download...")
        self.updateStatus("Downloading GHSL settlement data...")

        if self._download_ghsl_data():
            return self._check_ghsl_layer_exists()

        log_message("Could not obtain GHSL data", level="WARNING")
        return False

    def updateProgress(self, progress: float):
        """
        Used by the workflow to set the progress of the task.

        Args:
            progress: The progress value
        """
        log_message(f"Progress in workflow is : {progress}")  # noqa E203
        self.progressChanged.emit(progress)

    def updateStatus(self, status: str):
        """
        Used by the workflow to set the status message for the task.

        Args:
            status: A short description of the current operation
        """
        log_message(f"Status: {status}")
        self.statusChanged.emit(status)

    #
    # Every concrete subclass needs to implement these three methods
    #

    @abstractmethod
    def _process_features_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_features: QgsVectorLayer,
        index: int,
        area_name: Optional[str] = None,
    ) -> str:
        """
        Executes the actual workflow logic for a single area
        Must be implemented by subclasses.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Current area but expanded to coincide with grid cell boundaries.
            current_bbox: Bounding box of the above area.
            area_features: A vector layer of features to analyse that includes only features in the study area.
            index: Iteration / number of area being processed.
            area_name: Name of the area being processed (for grid-first mode).

        Returns:
            A raster layer file path if processing completes successfully, False if canceled or failed.
        """
        pass

    @abstractmethod
    def _process_raster_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        area_raster: str,
        index: int,
        area_name: Optional[str] = None,
    ):
        """
        Executes the actual workflow logic for a single area using a raster.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Polygon to clip the raster to which is aligned to cell edges.
            current_bbox: Bounding box of the above area.
            area_raster: A raster layer of features to analyse that includes only bbox pixels in the study area.
            index: Index of the current area.
            area_name: Name of the area being processed (for grid-first mode).

        Returns:
            Path to the reclassified raster.
        """
        pass

    @abstractmethod
    def _process_aggregate_for_area(
        self,
        current_area: QgsGeometry,
        clip_area: QgsGeometry,
        current_bbox: QgsGeometry,
        index: int,
        area_name: Optional[str] = None,
    ):
        """
        Executes the actual workflow logic for a single area using an aggregate.

        Args:
            current_area: Current polygon from our study area.
            clip_area: Polygon to clip the raster to which is aligned to cell edges.
            current_bbox: Bounding box of the above area.
            index: Index of the current area.
            area_name: Name of the area being processed (for grid-first mode).

        Returns:
            Path to the reclassified raster.
        """
        pass

    # ------------------- END OF ABSTRACT METHODS -------------------

    def execute(self) -> bool:
        """
        Main function to iterate over areas from the GeoPackage and perform the analysis for each area.

        This function processes areas (defined by polygons and bounding boxes) from the GeoPackage using
        the provided input layers (features, grid). It applies the steps of selecting intersecting
        features, then passes them to process area for further processing.

        Returns:
            True if the workflow completes successfully, False if canceled or failed.
        """

        # Do this here rather than in the ctor in case the result key is changed
        # in the concrete class
        self.attributes[self.result_key] = "Not Run"

        log_message(f"Executing {self.workflow_name}")
        log_message("----------------------------------")
        verbose_mode = int(setting(key="verbose_mode", default=0))
        if verbose_mode:
            log_message(self.item.attributesAsMarkdown())
            log_message("----------------------------------")

        with self.item.atomicAttributeUpdate() as attrs:
            attrs["execution_start_time"] = datetime.datetime.now().isoformat()

        log_message("Processing Started")
        self.updateStatus(f"Starting {self.workflow_name}")

        feedback = QgsProcessingFeedback()
        output_rasters = []

        try:
            if self.features_layer and type(self.features_layer) is QgsVectorLayer:
                self.updateStatus("Reprojecting features layer...")
                log_message(f"Features layer for {self.workflow_name} is {self.features_layer.source()}")
                self.features_layer = check_and_reproject_layer(self.features_layer, self.target_crs)
        except Exception as e:
            error_file = os.path.join(self.workflow_directory, "error.txt")
            if os.path.exists(error_file):
                os.remove(error_file)
            # Write the traceback to error.txt in the workflow_directory
            error_path = os.path.join(self.workflow_directory, "error.txt")
            with open(error_path, "w") as f:
                f.write(f"Failed to process {self.workflow_name}: {e}\n")
                f.write(traceback.format_exc())

            log_message(
                f"Failed to reproject features layer for {self.workflow_name}: {e}",
                tag="GeoE3",
                level=Qgis.Critical,
            )
            log_message(
                traceback.format_exc(),
                tag="GeoE3",
                level=Qgis.Critical,
            )
            with self.item.atomicAttributeUpdate() as attrs:
                attrs[self.result_key] = f"{self.workflow_name} Workflow Error"
                attrs[self.result_file_key] = ""
                attrs["error_file"] = error_path
                attrs["error"] = f"Failed to reproject features layer for {self.workflow_name}: {e}"
            return False

        # Use AreaIterator as context manager to ensure cleanup
        with AreaIterator(self.gpkg_path) as area_iterator:
            log_layer_count()  # For performance tuning, write the number of open layers to a log file

            areas_processed = 0

            try:
                total_areas = area_iterator.area_count()
                for index, (current_area, clip_area, current_bbox, progress, area_name) in enumerate(area_iterator):
                    areas_processed += 1
                    message = f"{self.workflow_name} Processing area {index} with progress {progress:.2f}%"  # noqa E231
                    self.updateStatus(f"Processing area {index + 1}/{total_areas}")
                    feedback.pushInfo(message)
                    log_message(message)
                    if self.feedback.isCanceled():
                        log_message(
                            f"{self.class_name} Processing was canceled by the user.",
                            tag="GeoE3",
                            level=Qgis.Warning,
                        )
                    raster_output = None
                    # Step 1: Select features that intersect with the current area
                    if self.features_layer:  # we are processing a vector input
                        area_features = self._subset_vector_layer(
                            current_area,
                            output_prefix=f"{self.layer_id}_area_features_{index}",
                        )
                        # Some workflows do not take in vector data (a features layer)
                        # but are not raster based. e.g. index_score_workflow
                        # Logic below is a check for that
                        if (
                            not isinstance(self.features_layer, bool)  # noqa W503
                            and area_features.featureCount() == 0  # noqa W503
                        ):
                            log_message(
                                "No area features ... skipping",
                                tag="GeoE3",
                                level=Qgis.Warning,
                            )
                            continue

                        # Step 2: Process the area features - work happens in concrete class
                        raster_output = self._process_features_for_area(
                            current_area=current_area,
                            clip_area=clip_area,
                            current_bbox=current_bbox,
                            area_features=area_features,
                            index=index,
                            area_name=area_name,
                        )
                    elif not self.aggregation:  # assumes we are processing a raster input
                        area_raster = self._subset_raster_layer(bbox=current_bbox, index=index)
                        raster_output = self._process_raster_for_area(
                            current_area=current_area,
                            clip_area=clip_area,
                            current_bbox=current_bbox,
                            area_raster=area_raster,
                            index=index,
                            area_name=area_name,
                        )
                    elif self.aggregation:  # we are processing an aggregate
                        raster_output = self._process_aggregate_for_area(
                            current_area=current_area,
                            clip_area=clip_area,
                            current_bbox=current_bbox,
                            index=index,
                            area_name=area_name,
                        )

                    if not raster_output:
                        raise RuntimeError(
                            f"{self.workflow_name} produced no raster output for area {area_name} (index {index})."
                        )

                    # clip the area by its matching mask layer in study_area geopackage
                    self.updateStatus(f"Masking area {index + 1}...")
                    masked_layer = self._mask_raster(
                        raster_path=raster_output,
                        area_geometry=clip_area,
                        index=index,
                    )
                    output_rasters.append(masked_layer)

                    # Write raster values to grid for this area
                    # Skip this step for grid-first workflows since grid was already populated
                    if not self.use_grid_first and masked_layer and os.path.exists(masked_layer):
                        self.updateStatus(f"Writing grid values for area {index + 1}...")
                        updated_cells = write_raster_values_to_grid(
                            gpkg_path=self.gpkg_path,
                            raster_path=masked_layer,
                            column_name=self.layer_id,
                            area_name=area_name,
                        )
                        if updated_cells >= 0:
                            log_message(
                                f"Updated {updated_cells} grid cells for {self.layer_id} in area {area_name}",
                                tag="GeoE3",
                                level=Qgis.Info,
                            )
                        else:
                            log_message(
                                f"Failed to update grid cells for {self.layer_id} in area {area_name}",
                                tag="GeoE3",
                                level=Qgis.Warning,
                            )

                    # Note: We don't emit area iterator progress here because it would
                    # override the sub-task progress in the Task Progress bar.
                    # The sub-task progress (0-100%) is more useful to the user.
                # Combine all area rasters into a VRT
                self.updateStatus("Combining area rasters...")
                vrt_filepath = self._combine_rasters_to_vrt(output_rasters)
                with self.item.atomicAttributeUpdate() as attrs:
                    attrs[self.result_file_key] = vrt_filepath
                    attrs[self.result_key] = f"{self.workflow_name} Workflow Completed"

                self.updateStatus(f"{self.workflow_name} complete")
                log_message(
                    f"{self.workflow_name} Completed. Output VRT: {vrt_filepath}",
                    tag="GeoE3",
                    level=Qgis.Info,
                )

                # Log processing summary
                if areas_processed > 0:
                    log_message(
                        f"Processing Summary - Areas processed: {areas_processed}",
                        tag="GeoE3",
                        level=Qgis.Info,
                    )
                with self.item.atomicAttributeUpdate() as attrs:
                    attrs["execution_end_time"] = datetime.datetime.now().isoformat()
                    attrs["error_file"] = None
                log_layer_count()  # For performance tuning, write the number of open layers to a log file
                return True

            except Exception as e:
                # remove error.txt if it exists
                error_file = os.path.join(self.workflow_directory, "error.txt")
                if os.path.exists(error_file):
                    os.remove(error_file)

                log_message(
                    f"Failed to process {self.workflow_name}: {e}",
                    tag="GeoE3",
                    level=Qgis.Critical,
                )
                log_message(
                    traceback.format_exc(),
                    tag="GeoE3",
                    level=Qgis.Critical,
                )
                with self.item.atomicAttributeUpdate() as attrs:
                    attrs[self.result_key] = f"{self.workflow_name} Workflow Error"
                    attrs[self.result_file_key] = ""

                # Write the traceback to error.txt in the workflow_directory
                error_path = os.path.join(self.workflow_directory, "error.txt")
                with open(error_path, "w") as f:
                    f.write(f"Failed to process {self.workflow_name}: {e}\n")
                    f.write(traceback.format_exc())
                with self.item.atomicAttributeUpdate() as attrs:
                    attrs["error_file"] = error_path
                    attrs["error"] = f"Failed to process {self.workflow_name}: {e}"
                log_layer_count()  # For performance tuning, write the number of open layers to a log file
                self.workflowError.emit(f"Failed to process {self.workflow_name}: {e}")
                return False

    def _create_workflow_directory(self) -> str:
        """
        Creates the directory for this workflow if it doesn't already exist.
        It will be in the scheme of working_dir/dimension/factor/indicator

        Returns:
            The path to the workflow directory
        """
        paths = self.item.getPaths()
        directory = os.path.join(self.working_directory, *paths)
        # Create the directory if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        return directory

    def _subset_vector_layer(self, area_geom: QgsGeometry, output_prefix: str) -> QgsVectorLayer:
        """
        Select features from the features layer that intersect with the given area geometry.

        Args:
            area_geom (QgsGeometry): The current area geometry for which intersections are evaluated.
            output_prefix (str): A name for the output temporary layer to store selected features.

        Returns:
            QgsVectorLayer: A new temporary layer containing features that intersect with the given area geometry.
        """
        if type(self.features_layer) is not QgsVectorLayer:
            return None
        log_message(
            f"{self.workflow_name} Select Features Started",
            tag="GeoE3",
            level=Qgis.Info,
        )
        layer = subset_vector_layer(self.workflow_directory, self.features_layer, area_geom, output_prefix)
        return layer

    def _subset_raster_layer(self, bbox: QgsGeometry, index: int):
        """Reproject and clip the raster to the bounding box of the current area.

        Args:
            bbox: The bounding box of the current area.
            index: The index of the current area.

        Returns:
            The path to the reprojected and clipped raster.

        Raises:
            QgsProcessingException: If raster layer is None or invalid.
        """
        # Validate raster layer before processing
        if self.raster_layer is None:
            raise QgsProcessingException(
                f"Raster layer is not set for workflow '{self.workflow_name}'. "
                "Please configure the raster layer in the workflow settings."
            )

        # Check if raster layer is valid (either QgsRasterLayer or path string)
        from qgis.core import QgsRasterLayer

        if isinstance(self.raster_layer, QgsRasterLayer):
            if not self.raster_layer.isValid():
                raise QgsProcessingException(
                    f"Raster layer '{self.raster_layer.source()}' is not valid for workflow '{self.workflow_name}'. "
                    "Please check that the file exists and is a valid raster format."
                )
        elif isinstance(self.raster_layer, str):
            if not os.path.exists(self.raster_layer):
                raise QgsProcessingException(
                    f"Raster file '{self.raster_layer}' does not exist for workflow '{self.workflow_name}'. "
                    "Please check the file path in the workflow settings."
                )

        # Convert the bbox to QgsRectangle
        bbox = bbox.boundingBox()

        reprojected_raster_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_clipped_and_reprojected_{index}.tif",
        )

        params = {
            "INPUT": self.raster_layer,
            "TARGET_CRS": self.target_crs,
            "RESAMPLING": 0,
            "TARGET_RESOLUTION": self.cell_size_m,
            "NODATA": -9999,
            "OUTPUT": "TEMPORARY_OUTPUT",
            "TARGET_EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",  # noqa E231
        }

        aoi = processing.run(
            "gdal:warpreproject",
            params,
            context=self.context,
            feedback=QgsProcessingFeedback(),
        )["OUTPUT"]

        params = {
            "INPUT": aoi,
            "BAND": 1,
            "FILL_VALUE": 0,
            "OUTPUT": reprojected_raster_path,
        }
        processing.run(
            "native:fillnodata",
            params,
            context=self.context,
            feedback=QgsProcessingFeedback(),
        )
        return reprojected_raster_path

    def _rasterize(
        self,
        input_layer: QgsVectorLayer,
        bbox: QgsGeometry,
        index: int,
        value_field: str = "value",
        default_value: int = 0,
    ) -> str:
        """

        ⭐️🚩⭐️ Warning this is not DRY - almost same function exists in study_area.py

        Rasterize the grid layer based on the 🔴'value'🔴 attribute field.

        Nodata will be set to 255

        On-land pixels will be set to 0 or whatever is specified in the default_value parameter.

        Args:
            input_layer (QgsVectorLayer): The layer to rasterize.
            bbox (QgsGeometry): The bounding box for the raster extents.
            index (int): The current index used for naming the output raster.
            value_field (str): The field to use for rasterization.
            default_value (int): The default value to use for the raster.

        Returns:
            str: The file path to the rasterized output.
        """
        log_message("--- Rasterizing geometry")
        log_message(f"--- bbox {bbox}")
        log_message(f"--- index {index}")
        if not input_layer or not input_layer.isValid():
            log_message("--- ERROR: Feature layer is not valid!")
            return ""
        log_message(f"--- input_layer {input_layer.source()}")

        output_path = os.path.join(
            self.workflow_directory,
            f"{self.layer_id}_{index}.tif",
        )
        if not input_layer.isValid():
            log_message(f"Layer failed to load! {input_layer}")
            return ""
        else:
            log_message(f"Rasterizing {input_layer}")

        # Ensure resolution parameters are properly formatted as float values
        # For Regional scale (H3 L6), use smaller cell size for better resolution
        if hasattr(self, "analysis_scale") and self.analysis_scale == "regional":
            x_res = 500  # Smaller cell size for H3 hexagons (H3 L6 edge ~3229m)
            y_res = 500
        else:
            x_res = self.cell_size_m  # pixel size in X direction
            y_res = self.cell_size_m  # pixel size in Y direction
        bbox = bbox.boundingBox()
        # Define rasterization parameters for the temporary layer
        params = {
            "INPUT": input_layer,
            "FIELD": f"{value_field}",
            "BURN": 0,
            "USE_Z": False,
            "UNITS": 1,
            "WIDTH": x_res,
            "HEIGHT": y_res,
            "EXTENT": f"{bbox.xMinimum()},{bbox.xMaximum()},{bbox.yMinimum()},{bbox.yMaximum()} [{self.target_crs.authid()}]",  # noqa E231
            "NODATA": 255,
            "OPTIONS": "",
            "DATA_TYPE": GDAL_OUTPUT_DATA_TYPE,
            "INIT": default_value,  # will set all cells to this value if not otherwise set
            "INVERT": False,
            "EXTRA": f"-a_srs {self.target_crs.authid()} -at",  # Assign all touched pixels
            "OUTPUT": output_path,
            "PROGRESS": self.feedback,
        }
        log_message(f"Rasterize parameters: {params}")
        # 'OUTPUT':'TEMPORARY_OUTPUT'})

        processing.run(
            "gdal:rasterize",
            params,
            context=self.context,
            feedback=QgsProcessingFeedback(),
        )
        log_message(f"Rasterize Parameter: {params}")
        log_message(f"Rasterize complete for: {output_path}")
        log_message(f"Created raster: {output_path}")
        return output_path

    def _mask_raster(self, raster_path: str, area_geometry: QgsGeometry, index: int) -> Optional[str]:
        """
        Multiply the raster by the area geometry to mask the raster to the area.

        Args:
            raster_path: The path to the raster file.
            area_geometry: The geometry to use as a mask.
            index: The index of the current area.

        Returns:
            The path to the masked raster or None if there is an error.

        Raises:
            QgsProcessingException: If the raster file is not found at the specified path.
        """
        if not raster_path:
            return None
        output_name = f"{self.layer_id}_masked_{index}.tif"
        output_path = os.path.join(self.workflow_directory, output_name)
        log_message(
            f"Masking raster {raster_path} for area {index} to {output_path}",
            tag="GeoE3",
            level=Qgis.Info,
        )
        # verify the raster path exists
        if not os.path.exists(raster_path):
            log_message(
                f"Raster file not found at {raster_path}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            raise QgsProcessingException(f"Raster file not found at {raster_path}")
        # Convert the geometry to a memory layer in the self.target_crs
        log_message(f"Creating mask layer for area from polygon {index}")
        mask_layer = geometry_to_memory_layer(area_geometry, self.target_crs, f"mask_layer_{index}")
        log_message(f"Mask layer created: {mask_layer}")
        # Clip the raster by the mask layer
        params = {
            "INPUT": f"{raster_path}",
            "MASK": mask_layer,
            "OUTPUT": f"{output_path}",
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "TARGET_EXTENT": None,
            "NODATA": 255,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": False,
            "SET_RESOLUTION": False,
            "X_RESOLUTION": None,
            "Y_RESOLUTION": None,
            "MULTITHREADING": False,
            "OPTIONS": "",
            "DATA_TYPE": GDAL_OUTPUT_DATA_TYPE,
            "EXTRA": "",
        }
        processing.run(
            "gdal:cliprasterbymasklayer",
            params,
            context=self.context,
            feedback=QgsProcessingFeedback(),
        )
        log_message(f"Masked raster created: {output_path}")
        return output_path

    def _combine_rasters_to_vrt(self, rasters: list) -> None:
        """
        Combine all the rasters into a single VRT file.

        Args:
            rasters: The rasters to combine into a VRT.

        Returns:
            vrtpath (str): The file path to the VRT file.
        """

        vrt_filepath = os.path.join(
            self.workflow_directory,
            f"{self.output_filename}_combined.vrt",
        )
        role = self.item.role
        source_qml = resources_path("resources", "qml", f"{role}.qml")
        vrt_filepath = combine_rasters_to_vrt(rasters, self.target_crs, vrt_filepath, source_qml)
        # if debug mode is off, remove all intermediate files
        if not int(setting(key="developer_mode", default=0)):
            log_message("Debug mode is off. Removing intermediate files, keeping only VRT-referenced rasters.")
            # Build set of TIF filenames referenced by VRTs in this directory
            # VRTs are locally generated XML — extract SourceFilename values via regex
            import re

            referenced_tifs = set()
            all_files = os.listdir(self.workflow_directory)
            source_pattern = re.compile(r"<SourceFilename[^>]*>([^<]+)</SourceFilename>")
            for file in all_files:
                if file.endswith(".vrt"):
                    try:
                        vrt_path = os.path.join(self.workflow_directory, file)
                        with open(vrt_path, "r") as f:
                            for match in source_pattern.finditer(f.read()):
                                referenced_tifs.add(os.path.basename(match.group(1)))
                    except Exception:  # nosec B110
                        pass  # If VRT can't be read, keep all TIFs as fallback

            for file in all_files:
                file_path = os.path.join(self.workflow_directory, file)
                # Keep: VRTs, QMLs, error logs, and TIFs referenced by VRTs
                if file.endswith(".vrt") or file.endswith(".qml") or file.endswith("error.txt"):
                    continue
                if file.endswith(".tif") and file in referenced_tifs:
                    continue
                # Skip subdirectories — they contain child workflow outputs
                if os.path.isdir(file_path):
                    continue
                # Delete intermediate files (unreferenced TIFs, shapefiles, etc.)
                log_message(f"Removing {file_path}")
                try:
                    os.remove(file_path)
                except Exception as e:
                    log_message(
                        f"Failed to remove {file_path}: {e}",
                        tag="GeoE3",
                        level=Qgis.Warning,
                    )
        else:
            log_message("Debug mode is on. Keeping all files in the workflow directory.")

        return vrt_filepath

    def _rasterize_grid_column(
        self,
        column_name: str,
        bbox: QgsGeometry,
        area_name: str,
        index: int,
        nodata: float = -9999.0,
    ) -> Optional[str]:
        """Rasterize a grid column to create a raster output.

        This method creates a raster from the study_area_grid column using
        gdal_rasterize. It is used for grid-first workflows where results
        are written to grid columns first, then rasterized for VRT generation.

        Args:
            column_name: Name of the grid column to rasterize.
            bbox: Bounding box geometry for the output raster extent.
            area_name: Name of the area being processed.
            index: Index of the area being processed (for output filename).
            nodata: NoData value for the output raster.

        Returns:
            Path to the output raster, or None on error.
        """
        output_path = os.path.join(
            self.workflow_directory,
            f"{column_name}_from_grid_{index}.tif",
        )

        # Get extent from bbox
        rect = bbox.boundingBox()
        extent = (rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum())

        log_message(
            f"Rasterizing grid column {column_name} for area {area_name}",
            tag="GeoE3",
            level=Qgis.Info,
        )

        success = rasterize_grid_column(
            gpkg_path=self.gpkg_path,
            column_name=column_name,
            output_raster_path=output_path,
            cell_size=self.cell_size_m,
            extent=extent,
            nodata=nodata,
            area_name=area_name,
        )

        if success:
            log_message(
                f"Rasterized grid column {column_name} to {output_path}",
                tag="GeoE3",
                level=Qgis.Info,
            )
            return output_path
        else:
            log_message(
                f"Failed to rasterize grid column {column_name}",
                tag="GeoE3",
                level=Qgis.Warning,
            )
            return None
