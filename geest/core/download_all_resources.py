# -*- coding: utf-8 -*-
"""Walk every indicator and download any missing cached external resource.

Used by TreePanel's "Download all resources" run-button option: instead of
running the whole analysis, this walks the tree once, and for every
indicator backed by a downloadable external resource, checks whether a
cached copy already exists in the working directory. If not, it downloads
it and sets it as that indicator's configured source, exactly as the
matching in-app "Download ..." button in the indicator's own configuration
dialog would. If a cached copy already exists but the indicator's own
source attribute doesn't point at it yet (sync_cached_resource_attributes()
- e.g. a duplicated indicator, or a resource a sibling indicator already
downloaded), it is wired up directly with no download needed.

Covers three kinds of indicator:

- Nighttime lights / environmental hazard rasters: a fixed output filename
  under working_directory/study_area/, and a generic
  "{cleaned_analysis_mode}_raster" attribute key, matching JsonTreeItem's
  own qgis_layer_raster_key derivation.
- OSM point layers (buffer-point indicators whose id/name/text matches a
  known OSM category - schools, health facilities, pharmacies, etc., see
  geest.core.osm_downloaders.resolve_point_osm_download_type, the same
  keyword-matching rule VectorDataSourceWidget's own "Download from OSM"
  button uses): downloaded as a GeoPackage, loaded as a QgsVectorLayer,
  added to the project, and wired up via the "{widget_key}_layer_*"
  attributes VectorDataSourceWidget.update_attributes() itself writes -
  a raw file-path attribute would not be enough, since that widget reads
  its configured source from an actual project layer, not a path.
- Environmental hazard indicators left at "Do Not Use" (the unconfigured
  default) but checked on in their factor's aggregation dialog - status
  "Required and not configured" per JsonTreeItem.getStatus(), driven by
  factor_weighting > 0. These are intended to be used even though no
  datasource mode was ever explicitly picked, so resource_spec_for_indicator()
  infers "use_environmental_hazards" from a known hazard id match and sets
  it (ResourceSpec.mode_to_set) alongside downloading the data, turning the
  indicator from "required" into "ready to run" in one step.

Deliberately NOT covered yet, each for a different reason:

- GHSL settlements / Ookla broadband: study-area-wide resources with no
  standalone "ensure downloaded" entry point outside constructing a full
  workflow instance (ensure_ghsl_data()/._download_ookla_data() are
  WorkflowBase/IndexScoreWithOoklaWorkflow methods) - GHSL is normally
  already downloaded at study-area creation time anyway, and Ookla's own
  workflow already does its own cache-check inline when it runs.
- Transport/generic polyline/point-per-cell indicators (use_polyline_per_cell,
  use_point_per_cell, use_osm_transport_polyline_per_cell, use_street_lights):
  VectorDataSourceWidget never offers an automatic OSM download for these
  modes either (only use_multi_buffer_point/use_single_buffer_point are
  keyword-matched) - there genuinely is no "known datasource" to fetch;
  a user-chosen layer (e.g. a road network) is required.
- Regional (S2S-backed) equivalents of nighttime lights/environmental
  hazards: a different downloader (S2SDownloaderTask) and attribute
  convention - a follow-up once this base version is confirmed working.
"""

import os
from typing import Callable, List, Optional
from urllib.parse import quote, unquote

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsRectangle,
    QgsTask,
    QgsVectorLayer,
)

from geest.core.constants import ENV_HAZARD_SOURCE_URLS
from geest.core.osm_downloaders import resolve_point_osm_download_type
from geest.core.tasks.env_hazard_downloader_task import EnvHazardDownloaderTask
from geest.core.tasks.ntl_downloader_task import NTLDownloaderTask
from geest.core.tasks.osm_downloader_task import OSMDownloaderTask
from geest.utilities import log_message

# Buffer-point modes VectorDataSourceWidget keyword-matches against a known
# OSM category - see resolve_point_osm_download_type().
OSM_ELIGIBLE_MODES = ("use_multi_buffer_point", "use_single_buffer_point")


class ResourceSpec:
    """Describes one indicator's downloadable resource.

    kind is "raster" (a single file path attribute, e.g.
    environmental_hazards_raster) or "vector" (an OSM-downloaded
    GeoPackage that must be loaded as a project layer and wired up via
    widget_key's "_layer_*" attributes - see
    _configure_vector_resource_attributes()). attribute_key is only set
    for "raster"; widget_key is only set for "vector". mode_to_set, when
    given, is written to the item's "analysis_mode" attribute alongside
    the resource attributes - see resource_spec_for_indicator()'s
    "Do Not Use" + "Required and not configured" handling: the indicator
    was checked on in its factor's aggregation dialog (so it is intended
    to be used) but its own datasource mode was never actually picked,
    which this resolves at the same time as downloading its data.
    """

    def __init__(
        self,
        label: str,
        filename: str,
        build_task: Callable,
        kind: str = "raster",
        attribute_key: Optional[str] = None,
        widget_key: Optional[str] = None,
        mode_to_set: Optional[str] = None,
    ):
        self.label = label
        self.filename = filename
        self.build_task = build_task
        self.kind = kind
        self.attribute_key = attribute_key
        self.widget_key = widget_key
        self.mode_to_set = mode_to_set


def resource_spec_for_indicator(item) -> Optional[ResourceSpec]:
    """Return this indicator's downloadable-resource spec, or None.

    Args:
        item: An indicator JsonTreeItem.

    Returns:
        A ResourceSpec if this indicator is one of the currently-supported
        types (nighttime lights, environmental hazards, or an OSM-matched
        buffer-point indicator, local/national scale only), otherwise None.
    """
    attrs = item.attributes()
    mode = attrs.get("analysis_mode", "")
    mode_to_set = None

    if mode == "Do Not Use":
        # "Do Not Use" is just the unconfigured default, not necessarily
        # "exclude this". An indicator checked on in its factor's
        # aggregation dialog (positive factor_weighting) but never pointed
        # at a specific data source shows as "Required and not
        # configured", not "Excluded from analysis" - see
        # JsonTreeItem.getStatus(). If its id matches a known
        # environmental hazard type, infer that as the intended mode,
        # exactly as if the user had picked it themselves, and switch the
        # indicator on at the same time as downloading its data.
        if item.getStatus() != "Required and not configured":
            return None
        hazard_id_candidate = str(attrs.get("id", "")).strip().lower()
        if hazard_id_candidate not in ENV_HAZARD_SOURCE_URLS:
            return None
        mode = "use_environmental_hazards"
        mode_to_set = "use_environmental_hazards"

    # Regional uses a different (S2S-backed) downloader/attribute
    # convention entirely - not covered here, see module docstring.
    if attrs.get("analysis_scale") == "regional":
        return None

    indicator_id = str(attrs.get("id", item.guid))

    if mode == "use_nighttime_lights":
        return ResourceSpec(
            label=f"{indicator_id} (Nighttime Lights)",
            attribute_key="nighttime_lights_raster",
            filename="nighttime_lights_annual",
            mode_to_set=mode_to_set,
            build_task=lambda extent, crs_authid, working_dir: NTLDownloaderTask(
                extent=extent,
                extent_crs_authid=crs_authid,
                working_dir=working_dir,
                filename="nighttime_lights_annual",
                delete_existing=False,
            ),
        )

    if mode == "use_environmental_hazards":
        hazard_id = str(attrs.get("id", "")).strip().lower()
        return ResourceSpec(
            label=f"{indicator_id} (Environmental Hazard)",
            attribute_key="environmental_hazards_raster",
            filename=f"{hazard_id}_hazard",
            mode_to_set=mode_to_set,
            build_task=lambda extent, crs_authid, working_dir, hazard_id=hazard_id: EnvHazardDownloaderTask(
                hazard_id=hazard_id,
                extent=extent,
                extent_crs_authid=crs_authid,
                working_dir=working_dir,
                delete_existing=False,
            ),
        )

    if mode in OSM_ELIGIBLE_MODES:
        item_id = str(attrs.get("id", "")).lower()
        item_name = str(attrs.get("name", "")).lower()
        indicator_text = str(attrs.get("indicator", "")).lower()
        osm_type = resolve_point_osm_download_type(item_id, item_name, indicator_text)
        if osm_type is None:
            return None
        label = osm_type.name.replace("_", " ").title()
        return ResourceSpec(
            label=f"{indicator_id} ({label})",
            filename=f"osm_{osm_type.value}",
            kind="vector",
            widget_key=mode[4:],  # strip "use_" - matches datasource_widget_factory's cleaned_key
            build_task=lambda extent, crs_authid, working_dir, osm_type=osm_type: OSMDownloaderTask(
                osm_download_type=osm_type,
                extents=_extent_to_wgs84(extent, crs_authid),
                output_path=os.path.join(working_dir, "study_area", f"osm_{osm_type.value}.gpkg"),
                crs=QgsCoordinateReferenceSystem("EPSG:4326"),
                use_cache=False,
                delete_gpkg=True,
            ),
        )

    return None


def _extent_to_wgs84(extent: QgsRectangle, extent_crs_authid: str) -> QgsRectangle:
    """Transform extent to EPSG:4326 - OSMDownloaderTask requires WGS84 extents."""
    source_crs = QgsCoordinateReferenceSystem(extent_crs_authid)
    if source_crs.authid() == "EPSG:4326":
        return extent
    transform = QgsCoordinateTransform(source_crs, QgsCoordinateReferenceSystem("EPSG:4326"), QgsProject.instance())
    return transform.transformBoundingBox(extent)


def resource_output_path(spec: ResourceSpec, working_directory: str) -> str:
    """Return the deterministic on-disk path this resource downloads to."""
    extension = "gpkg" if spec.kind == "vector" else "tif"
    return os.path.join(working_directory, "study_area", f"{spec.filename}.{extension}")


def resource_is_cached(spec: ResourceSpec, working_directory: str) -> bool:
    """Return True if spec's resource already has a non-empty cached file.

    Args:
        spec: The resource spec to check.
        working_directory: The project's working directory.

    Returns:
        True if working_directory/study_area/{filename}.tif already exists
        and is non-empty.
    """
    output_path = resource_output_path(spec, working_directory)
    return os.path.exists(output_path) and os.path.getsize(output_path) > 0


def collect_missing_resources(root_item, working_directory: str) -> List[tuple]:
    """Walk every indicator and return those whose resource is missing.

    Args:
        root_item: The tree's root JsonTreeItem (or any ancestor to scope
            the walk to).
        working_directory: The project's working directory.

    Returns:
        List of (item, ResourceSpec) tuples for indicators whose resource
        has no cached file yet. Indicators with no downloadable resource,
        or whose resource is already cached, are omitted.
    """
    missing = []
    for item in root_item.getDescendantIndicators(include_completed=True, include_disabled=True):
        spec = resource_spec_for_indicator(item)
        if spec is None:
            continue
        if not resource_is_cached(spec, working_directory):
            missing.append((item, spec))
    return missing


def _configure_vector_resource_attributes(item, spec: ResourceSpec, output_path: str) -> bool:
    """Load output_path as a project layer and wire it up via widget_key's "_layer_*" attributes.

    Mirrors VectorDataSourceWidget.update_attributes() exactly, since that
    is what the properties dialog reads back the next time it is opened -
    a vector indicator's configured source is a project layer (referenced
    by id), not a raw file path.

    Args:
        item: The indicator JsonTreeItem.
        spec: Its "vector"-kind ResourceSpec.
        output_path: Path to the downloaded GeoPackage.

    Returns:
        True if the file loaded as a valid layer and attributes were set.
    """
    layer_name = os.path.splitext(os.path.basename(output_path))[0]
    layer = QgsVectorLayer(output_path, layer_name, "ogr")
    if not layer.isValid():
        log_message(f"Downloaded OSM layer could not be loaded: {output_path}", level=Qgis.Warning)
        return False
    QgsProject.instance().addMapLayer(layer)
    with item.atomicAttributeUpdate() as attrs:
        attrs[f"{spec.widget_key}_layer_name"] = layer.name()
        attrs[f"{spec.widget_key}_layer_source"] = layer.source()
        attrs[f"{spec.widget_key}_layer_provider_type"] = layer.providerType()
        attrs[f"{spec.widget_key}_layer_crs"] = layer.crs().authid()
        attrs[f"{spec.widget_key}_layer_wkb_type"] = layer.wkbType()
        attrs[f"{spec.widget_key}_layer_id"] = layer.id()
        if spec.mode_to_set:
            attrs["analysis_mode"] = spec.mode_to_set
    return True


def _resource_already_configured(item, spec: ResourceSpec, working_directory: str) -> bool:
    """Return True if item's attributes already point at spec's cached resource."""
    if spec.mode_to_set and item.attribute("analysis_mode") != spec.mode_to_set:
        return False
    if spec.kind == "vector":
        layer_id = item.attribute(f"{spec.widget_key}_layer_id")
        if not layer_id:
            return False
        return QgsProject.instance().mapLayer(layer_id) is not None
    current = item.attribute(spec.attribute_key)
    if not current:
        return False
    return unquote(current) == resource_output_path(spec, working_directory)


def _configure_resource_attributes(item, spec: ResourceSpec, output_path: str) -> bool:
    """Wire up item's attributes to point at output_path, dispatching on spec.kind.

    Returns:
        True on success, False if a vector resource failed to load as a layer.
    """
    if spec.kind == "vector":
        return _configure_vector_resource_attributes(item, spec, output_path)
    with item.atomicAttributeUpdate() as attrs:
        attrs[spec.attribute_key] = quote(output_path)
        if spec.mode_to_set:
            attrs["analysis_mode"] = spec.mode_to_set
    return True


def sync_cached_resource_attributes(root_item, working_directory: str) -> List[tuple]:
    """Wire up every indicator whose resource is already cached but not configured.

    collect_missing_resources() only ever looks at indicators whose cached
    file does not exist yet - an indicator whose file IS already cached
    (e.g. a duplicated indicator, an attribute that got cleared, or a
    resource a sibling indicator already downloaded) is invisible to it
    and would otherwise stay unconfigured forever, even though the data it
    needs is sitting right there on disk. This walks every indicator with
    a downloadable resource spec and, for any that isn't already
    configured, wires it up - no download needed, nothing queued.

    Args:
        root_item: The tree's root JsonTreeItem (or any ancestor to scope
            the walk to).
        working_directory: The project's working directory.

    Returns:
        List of (item, ResourceSpec) tuples that were just configured.
    """
    configured = []
    for item in root_item.getDescendantIndicators(include_completed=True, include_disabled=True):
        spec = resource_spec_for_indicator(item)
        if spec is None:
            continue
        if not resource_is_cached(spec, working_directory):
            continue
        if _resource_already_configured(item, spec, working_directory):
            continue
        output_path = resource_output_path(spec, working_directory)
        if _configure_resource_attributes(item, spec, output_path):
            configured.append((item, spec))
    return configured


class DownloadAllResourcesController:
    """Sequentially downloads every missing resource found by collect_missing_resources().

    One QgsTask at a time (download tasks already hit the same network/
    disk resources a parallel run would contend over), reporting progress
    through the given callbacks so the caller can drive its own progress
    bar/status label without this class knowing about any UI widgets.
    """

    def __init__(
        self,
        items_and_specs: List[tuple],
        working_directory: str,
        extent: QgsRectangle,
        extent_crs_authid: str,
        on_item_started: Optional[Callable] = None,
        on_item_progress: Optional[Callable] = None,
        on_item_finished: Optional[Callable] = None,
        on_all_finished: Optional[Callable] = None,
    ):
        """Initialize the controller.

        Args:
            items_and_specs: List of (item, ResourceSpec) tuples to download.
            working_directory: The project's working directory.
            extent: Bounding box to crop each download to.
            extent_crs_authid: CRS authid (e.g. "EPSG:32626") of extent.
            on_item_started: Optional callable(item, spec).
            on_item_progress: Optional callable(item, spec, message).
            on_item_finished: Optional callable(item, spec, success, message).
            on_all_finished: Optional callable(succeeded, failed) - called
                once every item has been attempted, with lists of
                (item, spec) tuples.
        """
        self._queue = list(items_and_specs)
        self._working_directory = working_directory
        self._extent = extent
        self._extent_crs_authid = extent_crs_authid
        self._on_item_started = on_item_started
        self._on_item_progress = on_item_progress
        self._on_item_finished = on_item_finished
        self._on_all_finished = on_all_finished
        self._current_task: Optional[QgsTask] = None
        self._succeeded: List[tuple] = []
        self._failed: List[tuple] = []
        self._cancelled = False

    def start(self) -> None:
        """Start processing the queue, one resource at a time."""
        self._advance()

    def cancel(self) -> None:
        """Cancel the current download and stop processing further items."""
        self._cancelled = True
        if self._current_task is not None:
            self._current_task.cancel()

    def _advance(self) -> None:
        if self._cancelled or not self._queue:
            if self._on_all_finished:
                self._on_all_finished(self._succeeded, self._failed)
            return

        item, spec = self._queue.pop(0)
        if self._on_item_started:
            self._on_item_started(item, spec)

        from qgis.core import QgsApplication

        task = spec.build_task(self._extent, self._extent_crs_authid, self._working_directory)
        self._current_task = task

        def _progress(message, item=item, spec=spec):
            if self._on_item_progress:
                self._on_item_progress(item, spec, message)

        # error_occurred only logs/reports progress - run() always returns
        # False after emitting it, so taskTerminated fires right after and
        # is the single place that records the failure and advances the
        # queue. Recording it here too would double-count the failure.
        last_error_message = [""]

        def _error(message, spec=spec):
            last_error_message[0] = message
            log_message(f"Download failed for {spec.label}: {message}", level=Qgis.Warning)

        def _completed(item=item, spec=spec):
            # Computed from spec rather than read off the task object:
            # different downloader task classes name this attribute
            # differently (output_path vs gpkg_path), but the output path
            # is deterministic from the spec alone either way.
            output_path = resource_output_path(spec, self._working_directory)
            if not os.path.exists(output_path):
                self._failed.append((item, spec))
                if self._on_item_finished:
                    self._on_item_finished(item, spec, False, "Output file not found")
            elif not _configure_resource_attributes(item, spec, output_path):
                self._failed.append((item, spec))
                if self._on_item_finished:
                    self._on_item_finished(item, spec, False, "Downloaded file could not be loaded as a layer")
            else:
                self._succeeded.append((item, spec))
                if self._on_item_finished:
                    self._on_item_finished(item, spec, True, output_path)
            self._current_task = None
            self._advance()

        def _terminated(item=item, spec=spec):
            # Fires both for a real failure (run() returned False, after
            # error_occurred already reported why) and for cancellation
            # (no error_occurred first) - distinguish by whether an error
            # message was captured.
            self._failed.append((item, spec))
            if self._on_item_finished:
                self._on_item_finished(item, spec, False, last_error_message[0] or "Cancelled")
            self._current_task = None
            self._advance()

        task.progress_updated.connect(_progress)
        task.error_occurred.connect(_error)
        task.taskCompleted.connect(_completed)
        task.taskTerminated.connect(_terminated)
        QgsApplication.taskManager().addTask(task)
