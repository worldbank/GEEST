# -*- coding: utf-8 -*-
"""Walk every indicator and download any missing cached external resource.

Used by TreePanel's "Download all resources" run-button option: instead of
running the whole analysis, this walks the tree once, and for every
indicator backed by a downloadable external resource, checks whether a
cached copy already exists in the working directory and - if not -
downloads it and sets it as that indicator's configured source, exactly
as the matching in-app "Download ..." button in the indicator's own
configuration dialog would.

Currently covers nighttime lights and environmental hazard rasters - the
two indicator types with a clean, single-widget, deterministic download
path (a fixed output filename under working_directory/study_area/, and a
generic "{cleaned_analysis_mode}_raster" attribute key, matching
JsonTreeItem's own qgis_layer_raster_key derivation). Deliberately NOT
covered yet, each for a different reason:

- OSM vector layers: eligibility is decided by heuristic keyword-matching
  on the indicator's id/name/text (see
  geest.gui.widgets.datasource_widgets.vector_datasource_widget), not a
  single fixed analysis_mode, so a safe generic rule is a larger follow-up.
- GHSL settlements / Ookla broadband: study-area-wide resources with no
  standalone "ensure downloaded" entry point outside constructing a full
  workflow instance (ensure_ghsl_data()/._download_ookla_data() are
  WorkflowBase/IndexScoreWithOoklaWorkflow methods) - GHSL is normally
  already downloaded at study-area creation time anyway, and Ookla's own
  workflow already does its own cache-check inline when it runs.
- Regional (S2S-backed) equivalents of nighttime lights/environmental
  hazards: a different downloader (S2SDownloaderTask) and attribute
  convention - a follow-up once this base version is confirmed working.
"""

import os
from typing import Callable, List, Optional
from urllib.parse import quote

from qgis.core import Qgis, QgsRectangle, QgsTask

from geest.core.tasks.env_hazard_downloader_task import EnvHazardDownloaderTask
from geest.core.tasks.ntl_downloader_task import NTLDownloaderTask
from geest.utilities import log_message


class ResourceSpec:
    """Describes one indicator's downloadable resource."""

    def __init__(self, label: str, attribute_key: str, filename: str, build_task: Callable):
        self.label = label
        self.attribute_key = attribute_key
        self.filename = filename
        self.build_task = build_task


def resource_spec_for_indicator(item) -> Optional[ResourceSpec]:
    """Return this indicator's downloadable-resource spec, or None.

    Args:
        item: An indicator JsonTreeItem.

    Returns:
        A ResourceSpec if this indicator is one of the currently-supported
        types (nighttime lights or environmental hazards, local/national
        scale only), otherwise None.
    """
    attrs = item.attributes()
    mode = attrs.get("analysis_mode", "")
    if mode == "Do Not Use":
        return None
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
            build_task=lambda extent, crs_authid, working_dir, hazard_id=hazard_id: EnvHazardDownloaderTask(
                hazard_id=hazard_id,
                extent=extent,
                extent_crs_authid=crs_authid,
                working_dir=working_dir,
                delete_existing=False,
            ),
        )

    return None


def resource_output_path(spec: ResourceSpec, working_directory: str) -> str:
    """Return the deterministic on-disk path this resource downloads to."""
    return os.path.join(working_directory, "study_area", f"{spec.filename}.tif")


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

        def _completed(item=item, spec=spec, task=task):
            output_path = getattr(task, "output_path", None)
            if not output_path or not os.path.exists(output_path):
                self._failed.append((item, spec))
                if self._on_item_finished:
                    self._on_item_finished(item, spec, False, "Output file not found")
            else:
                with item.atomicAttributeUpdate() as attrs:
                    attrs[spec.attribute_key] = quote(output_path)
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
