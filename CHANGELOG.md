# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Version policy: the version here and in `config.json`/`geest/metadata.txt`
stays exactly one semver step ahead of the last version actually tagged
and released on GitHub - never bumped again per commit after that. All
work since the last release accumulates under that single pending
version (upgrading patch->minor->major in place if a later change needs
a bigger bump) until a release is cut and tagged, at which point the next
single step begins.

## [Unreleased]

## [2.1.0] - 2026-10-16

Everything below accumulated on top of the last tagged release, v2.0.6;
none of it has been released yet, so it is kept under this single pending
version per the policy above.

### Added

- Each minimap in the analysis report (dimension/factor/indicator grids)
  now shows a small 5-bar sparkline beneath it, giving the distribution of
  that layer's scored cell values (1-5) coloured with the same
  `SCORE_LEGEND_COLORS` ramp every result map already uses. Score 0
  (masked/excluded cells) is excluded from the count - it's typically the
  overwhelming majority of cells outside the populated/opportunity area,
  and including it would flatten the 1-5 distribution the sparkline
  exists to show. New generic `BaseReport._draw_sparkline()` primitive and
  `AnalysisReport._raster_score_histogram()`/`_draw_minimap_sparkline()`.
- Indicator/factor configuration dialogs' value-range|index-score mapping
  tables (the reference table shown while picking an analysis mode, e.g.
  Contextual Index Score, Street Lights, Multi/Single Buffer, Safety
  Raster, ACLED CSV, OSM Transport highway/cycleway classification) now
  show a "Legend" column with a solid colour swatch for each row, matching
  the same 5-class colour ramp (`#d7191c`→`#2c7bb6`) every result
  map/raster already uses (`resources/qml/indicator.qml`/`factor.qml`), so
  a user can see at a glance which map colour a given score corresponds to
  without cross-referencing the separate map legend. New shared
  `geest.core.constants.SCORE_LEGEND_COLORS` and
  `legend_cell_html()`/`legend_color_for_score()` helpers in
  `base_configuration_widget.py`, reused by every affected widget rather
  than hand-rolling the colour lookup per table. Left out: Safety
  Polygon's classification table (user-editable 0-100 values, not a
  read-only 1-5 score reference) and the plain Index Score widget (has no
  mapping table at all).
- `admin.py generate-zip` now bundles `h3` into the release zip by
  default (`VENDORED_PACKAGES = ["h3==4.4.2"]`), wired automatically into
  `build()` rather than requiring a separate manual `bundle-deps` step
  beforehand - the previous default (`VENDORED_PACKAGES = []`, with CI
  passing `--packages "h3==4.4.2"` as an override) meant a plain local
  `generate-zip` silently shipped a plugin that would fail to import h3
  wherever the end user's own QGIS Python doesn't already have it.
  `.github/workflows/release.yml`'s now-redundant explicit "Bundle
  dependencies" step was removed.
  Also fixed two real gaps found while verifying this: `WHEEL_PLATFORMS`
  never requested a `cp313` wheel for Windows/macOS at all (only Linux
  had it - any Windows/macOS user on QGIS 4.x, which ships Python 3.13,
  would have hit an ImportError), and macOS Intel/ARM wheels were
  silently clobbering each other at extraction time (h3 publishes no
  universal2 wheel, and macOS wheel filenames don't encode architecture
  the way manylinux's do, so both unpack to the identical path) - every
  bundled macOS `.so` was actually arm64 only despite Intel also being
  requested. `WHEEL_PLATFORMS` now targets cp312/cp313 only
  (Linux/Windows/macOS-arm64), dropping cp311/cp314 and Intel macOS -
  this was also necessary to fit under the plugin zip's 15MB hard limit
  on QGIS's plugin repository infrastructure (see below), which a
  correctly-complete bundle would otherwise have exceeded.
- `generate-zip` now refuses to produce a zip over 15MB (`MAX_ZIP_SIZE_MB`),
  QGIS's plugin repository hard limit, and always prints a small ASCII
  dashboard breaking the zip's compressed size down by top-level plugin
  area (`extlibs`, `core`, `gui`, `resources`, ...) with a bar chart, so
  it's obvious at a glance what's actually driving the size - not just
  the final pass/fail total.
- `bundle_deps()` now strips build-time-only files after extracting each
  wheel (Cython `.pyx`/`.pxd` source, C headers, static libs, CMake
  config) - never needed to just `import h3` at runtime, pure dead
  weight in every release before now.
- `admin.py`'s packaging excludes a short list of dev-only files that were
  previously swept into every release zip for no runtime benefit
  (`EXCLUDE_FILES`): `generate_model.py`/`geoe3.ods` (the
  spreadsheet-to-`model.json` tooling invoked only by
  `scripts/import-ods-to-model.sh`, never imported by the plugin itself),
  `geoe3_styling.xlsx` (a design reference, not loaded by any code),
  `ghs-mod-2023-tile-scheme.qmd` (a QGIS-authored metadata sidecar for the
  GHSL tile scheme layer, not read back - the plugin only ever loads the
  sibling `.parquet`/`.gpkg`), and `insights.model3` (an unused QGIS
  Processing model with no code reference).
- `analysis_summary_report_template.qpt`'s two picture items were
  embedding base64 copies of `geest/resources/images/geoe3-bg.png` and
  `geest/resources/geoe3-banner.png` (QGIS's own "Embedded" picture
  save mode) - byte-for-byte duplicates (confirmed via SHA256) of files
  the plugin already ships separately, inflating the template from ~20KB
  to ~3.9MB for no reason. The template's `file=` attributes now hold
  placeholder tokens (`PLUGIN_RESOURCE:...`) that
  `BaseReport.load_template()` (`geest/core/reports/base_report.py`)
  substitutes for the real resolved resource path before parsing, so the
  template file itself never needs to hardcode an absolute,
  install-location-specific path.
- The four largest shipped background PNGs
  (`geoe3-bg.png`, `geoe3-page-header-bg.png`, `geoe3-page-footer-bg.png`,
  `geoe3-page-no-bg.png`) are flat-colour illustration with a subtle
  grain texture, not photographic content, so they compress far better
  as a restricted 256-colour palette than as 8-bit-per-channel truecolor
  - re-saved as 256-colour palette PNGs (same filenames/format, no code
  changes needed) for a combined 3.75MB -> 1.14MB (~70% smaller), with
  RMSE under 0.7% against the originals (visually indistinguishable).
- Safety Perception's nighttime lights indicator can now download its own
  raster directly in-app at local/national scale (worldbank/GeoE3#452),
  following the same button/`QgsTask` pattern as the existing S2S
  downloaders. The source is the annual VIIRS nighttime lights composite
  (OpenGeoHub/Hengl mirror on Zenodo, CC-BY 4.0, 2000-2024, no login
  required - the authoritative EOG source now gates all downloads behind
  free account registration, which this avoids). The global composite
  (~60 MB) is downloaded with `QgsNetworkAccessManager`'s blocking GET
  (the same pattern `S2SClient` already uses) rather than GDAL's
  `/vsicurl/` driver reading it remotely - some network/proxy environments
  block the HTTP Range requests `/vsicurl/` needs, so a plain synchronous
  download is more portable even though it means fetching the whole file;
  cropping to the study area then happens locally. `SafetyRasterWorkflow`
  needed no changes: the download writes to the same
  `nighttime_lights_raster` attribute the manual file picker already
  populated.
- All five environmental hazard indicators (fire, flood, landslide, cyclone,
  drought) can now download their own raster directly in-app at
  local/national scale, the same button/`QgsTask` pattern as the nighttime
  lights downloader above - previously only a manual "visit the source page
  and download it yourself" link was offered. Each hazard's source is its
  direct, no-login World Bank Data Catalog (DDH) file
  (`ENV_HAZARD_DOWNLOAD_URLS` in `geest/core/constants.py`), downloaded in
  full via `QgsNetworkAccessManager`'s blocking GET and then cropped locally
  to the study area. The download/crop logic shared with the nighttime
  lights downloader was extracted into `geest.core.tasks.raster_download_utils`
  rather than duplicated. Source files range from ~3 MB (fire, cyclone) to
  ~1 GB (drought); the button warns and asks for confirmation before
  starting any download at or above 100 MB.
- New "Download all resources" option on the Run button's dropdown menu:
  walks every indicator, and for any backed by a downloadable external
  resource, checks for an existing cached file under
  `working_directory/study_area/` and downloads it only if missing, then
  sets it as that indicator's configured source - the same attribute each
  resource's own in-app "Download ..." button would write. Covers
  nighttime lights and environmental hazard rasters, and OSM-matched
  buffer-point indicators (schools, health facilities, pharmacies, grocery
  stores, financial services, kindergartens, green spaces, water points,
  public transport - the same keyword-matched categories the in-dialog
  "Download from OSM" button already offers, now extracted into
  `geest.core.osm_downloaders.resolve_point_osm_download_type` as a single
  source of truth shared by both). Unlike the raster resources, an OSM
  indicator's configured source is an actual QGIS project layer, not a
  file path - the downloaded GeoPackage is loaded and added to the
  project, then wired up via the same `{widget_key}_layer_*` attributes
  `VectorDataSourceWidget.update_attributes()` itself writes. It also
  covers environmental hazard indicators left at "Do Not Use" (the
  unconfigured default) but checked on in their factor's aggregation
  dialog - status "Required and not configured" - rather than only ones
  that already had a datasource mode explicitly picked: if such an
  indicator's id matches a known hazard type, downloading its data also
  switches its mode to "Environmental Hazard" at the same time, so it
  comes out "ready to run" instead of staying stuck on "required". While a
  download is in progress, its indicator's row shows the same animated
  throbber a normal single-indicator run already shows, and the tree view
  is refreshed via `layoutChanged` (not a full model reset) once
  downloads/wiring finish, so newly-configured indicators immediately show
  their updated status without collapsing every expanded node or losing
  the current selection/scroll position. Deliberately not covered yet
  (documented in `geest/core/download_all_resources.py`'s module
  docstring): GHSL/Ookla, transport/generic polyline/point modes, and the
  regional S2S-backed equivalents of nighttime lights/environmental
  hazards.
- `pyarrow` added to the nix dev shell (devShell tooling and the
  QGIS-bundled Python both). A benchmark comparing GeoPackage, Shapefile,
  FlatGeobuf and GeoParquet writes/reads found the file format made
  almost no difference to speed - the bottleneck was GDAL/OGR's
  per-feature Python API (`CreateFeature()`/feature iteration), not the
  on-disk format - so rather than migrate formats, the plugin's biggest
  bulk vector writes now try GDAL's columnar Arrow-batch API
  (`Layer.WritePyArrow()`) first, which got ~1.75x faster writes on the
  SAME GeoPackage files. New `geest/core/arrow_batch_writer.py` helper:
  if pyarrow isn't importable (not every QGIS install bundles it, though
  OSGeo4W's Windows installer does by default), it returns `False` and
  every call site falls straight back to its original per-feature
  `CreateFeature()` loop - no format change, no hard dependency. Wired
  into `UnifiedWriterThread._write_grid_batch`/`_write_geometry_batch`
  (`study_area_processing_task.py`) - the base study-area grid write, the
  biggest cell counts every study area creation produces.
- Separately, H3 grid generation's `bbox_to_wgs84()`/
  `transform_wgs84_to_target()` (`geest/core/h3_utils.py`) were rebuilding
  a fresh `osr.CoordinateTransformation` on every single call - and both
  run once per grid cell, tens to hundreds of thousands of times per
  study area. Benchmarked ~20-30x slower than reusing one for the same
  EPSG pair; now cached thread-locally (keyed by source/target EPSG),
  cutting H3 grid generation time roughly 4x in testing.

### Fixed

- **Re-running or clearing a single indicator left its factor, dimension, and
  analysis still showing a stale "Completed successfully" with the old
  aggregate value.** Nothing ever told an ancestor its cached aggregate was
  computed from a now-changed child. `JsonTreeItem.invalidateAncestors()`
  clears every ancestor's `result`/`result_file` on a successful workflow
  run and when an item is cleared via "Clear Item", so the tree honestly
  falls back to "Configured, not run" until the aggregate is recomputed.
- **`study_area_grid` could silently gain a permanent, unnamed, all-NULL
  column.** An item with an empty/missing `id` attribute reached the grid
  column creation code with a blank column name. `_ensure_column_exists()`
  and `add_model_columns_to_grid()` now refuse to create a blank-named
  column.
- **Three dead aggregate columns (`contextual_score`, `accessibility_score`,
  `place_characterization_score`) were added to every study area's grid.**
  Confirmed via git history that these were reserved alongside
  `wee_score`/`wee_by_population` (since renamed to `geoe3`/
  `geoe3_by_population`) but never implemented - removed from
  `get_aggregate_column_names()`.
- **Logging never reached `~/GEOE3.log`.** A module-level diagnostic
  banner in `grid_column_utils.py` could fire before `geest/__init__.py`'s
  own `logging.basicConfig()` call, implicitly self-configuring the root
  logger first and making our call a silent no-op (console showed the
  bare `WARNING:root:...` fallback format instead). `basicConfig()` now
  passes `force=True` so our file handler always wins.
- **Analysis-level processing required a population raster even though it's
  optional.** Leaving it unset errored with "Select a valid population
  raster before running the analysis" and aborted the whole analysis
  post-processing step. The GeoE3 x Population Score is now skipped
  (like the opportunities mask already was) when no population raster or
  S2S demographics are configured, and everything else still runs.
- **GHSL-filtered (unpopulated) areas were reprocessed on every single run.**
  Study area creation already skips grid generation for an area with no
  GHSL settlements, but `AreaIterator` never checked for that - every
  indicator workflow ran its full per-area pipeline on these areas anyway,
  every run, only to find nothing to write. `AreaIterator` now skips any
  area with zero `study_area_grid` cells up front, determined directly
  from the grid itself so it works immediately on existing projects too.
- **Running multiple indicators concurrently (the "concurrent tasks"
  setting) could silently lose grid writes - an indicator reported
  "Completed" with no error, yet its own `study_area_grid` column stayed
  NULL (or an aggregating factor/dimension read it as 0).** Confirmed
  against a real project: three Contextual-dimension indicators started
  within 6ms of each other (genuinely concurrent, not sequential), and only
  one of the three actually persisted its value. Reproduced reliably with a
  new test (`test_grid_column_concurrent_writes.py`) that fires several
  threads at the same GeoPackage the way concurrent indicator workflows do
  - each opens its own independent `ogr.Open(gpkg_path, 1)` connection and
  writes a different column with a raw SQL `UPDATE`; under true
  concurrency, most of those writes failed outright even though each one's
  own `StartTransaction()`/`CommitTransaction()` reported success -
  SQLite's own locking does not fully protect independent GDAL/OGR dataset
  handles writing to the same file from different threads in the same
  process. Fixed by funnelling every `study_area_grid` write (11 functions
  in `grid_column_utils.py`: the uniform-value writer index-score
  indicators use, the aggregation writer factors/dimensions use, spatial
  joins, buffers, percentage scores, etc.) through one process-wide lock
  (`@_serialize_grid_writes`) - only the actual database write is
  serialized; the slow, genuinely parallelizable work (loading features,
  generating rasters) is unaffected.
- **Windows crash running a whole dimension (#447, #448):** every indicator's
  workflow opened its own `AreaIterator` (three fresh `QgsVectorLayer` reads)
  against `study_area.gpkg` while `grid_column_utils` concurrently wrote to
  the same file - safe in isolation, but running many indicators back-to-back
  (a whole dimension/factor/analysis) raised the odds of hitting a GDAL/OGR
  SQLite handle corruption window, surfacing on Windows as an access
  violation inside `getFeatures()`. The SQLite write-safety hardening (WAL
  journal + `SQLITE_USE_OGR_VFS=NO`) that already fixed this exact class of
  corruption for study-area *creation* was explicitly scoped out of the later
  analysis/workflow *execution* phase - closed that gap by applying the same
  hardening around `WorkflowQueueManager`'s run lifecycle (extracted into a
  shared `geest.utilities` helper so both call sites share one
  implementation).
- **One bad area no longer aborts the whole indicator.** `WorkflowBase`'s
  per-area loop wrapped all ~27 areas in a single `try/except`, so any
  unhandled exception from one area (a degenerate geometry, a transient
  data-source hiccup, ...) discarded every area already processed and
  skipped every area still to come - the "hard to reproduce, whole run just
  fails" shape of several field reports. Each area is now isolated in its
  own `try/except`: a failure is logged clearly against that specific area
  and the run continues; the final result records which areas (if any) were
  skipped. If literally every area fails, that's still reported as a real
  failure, not a false "Completed". Also: a user-cancelled run previously
  kept processing all remaining areas regardless (the cancellation flag was
  checked but never acted on) - it now stops promptly.
- **Local-scale (100m grid) analysis could take 7.5+ hours and still not
  finish, versus 7 minutes at national (1000m) scale on the same country
  (#445) - roughly 100x more grid cells causing a much-worse-than-linear
  slowdown.** Root cause: `write_spatial_join_to_grid` (environmental
  hazards, GHSL/Ookla masking, vector-fallback nighttime lights) re-queried
  the features layer with `SetSpatialFilter` for *every* grid cell instead
  of indexing once; `write_percentage_scores_to_grid` (multi-buffer
  accessibility scoring, the WTP dimension from #448) ran a full exact GEOS
  intersection against the dissolved buffer polygon for *every* grid cell
  with no cheap bounding-box reject first. Both now build/check a spatial
  index once and do indexed lookups per cell, matching the pattern
  `write_buffer_values_to_grid` already used correctly. Also found and fixed
  the same anti-pattern in dead code (`write_point_count_to_grid`, unused -
  removed rather than fixed, per YAGNI).
- `multi_buffer_distances_native_workflow.py` (the WTP/accessibility
  workflow) reopened the road network file and re-ran a full-layer CRS
  reprojection from scratch for every area (up to 27x per indicator, times
  every indicator in the dimension), even though the network and its CRS
  don't change between areas. Now loaded and reprojected once and cached.
- Five workflows (`polyline_per_cell`, `polygon_per_cell`,
  `osm_transport_polyline_per_cell`, `classified_polygon`, `safety_polygon`)
  loaded their input layer without checking `.isValid()`, unlike every other
  per-cell workflow - a corrupt or no-longer-reachable source file didn't
  fail loudly; it surfaced as "0 features in every area", silently absorbed
  by the empty-features fallback into an all-zero result with nothing
  pointing at the real cause. Now raises a clear `WorkflowNotConfiguredError`
  naming the broken path, matching the existing `point_per_cell` pattern.
- The S2S Education-proxy grid update (`polygon_per_cell_workflow.py`) used
  a raw `ogr.Open`/`ExecuteSQL` call with no retry on a transient "database
  is locked" error, unlike every other grid-writing function in this
  codebase. Now goes through the same `_open_gpkg_for_write`/
  `_execute_sql_with_retry` helpers as everything else.
- OSM point and mixed-to-point downloads (health facilities, schools,
  pharmacies, financial services, kindergartens, grocery stores, green
  spaces, public transport, water points) now retain the OSM `name` tag
  as an entity name attribute, instead of only the feature `id`. Polygon
  downloads gain the same `name` attribute (#453).
- S2S download is no longer offered for flood hazards at local or
  national analysis scale. Flood now follows the same regional-only S2S
  gating as every other environmental hazard (#449).
- A broken/missing road network layer reference could linger silently in
  `model.json` forever: when the Road Network panel detected the file was
  gone it tried to clear the stored path, but the clear signal's value was
  discarded by the receiving slot (which re-fetched the combo box selection
  instead) and the slot also silently ignored empty/`None` values, so the
  stale path was never actually removed. Setting the road network layer now
  validates the file exists before storing it (showing a clear error if
  not), clearing is no longer a no-op, and a missing file detected on
  restore now also surfaces a message-bar warning instead of only a log
  line.
- Contextual index-score indicators (e.g. workplace discrimination) could
  fail with "VRT Layer generation failed" when a study area contained a
  sliver/island fragment too small to have been assigned any
  `study_area_grid` cells. `rasterize_grid_column` silently fell back to
  rasterizing the whole study area's extent for such an area (burning
  nothing, since no grid rows matched), producing a degenerate raster that
  broke downstream masking and VRT combination - either aborting the whole
  indicator or corrupting its combined output depending on exact pixel
  rounding. `rasterize_grid_column` now detects the zero-matching-cells
  case up front and refuses to rasterize, and
  `ContextualIndexScoreWorkflow` treats that as "no features for this
  area" and falls back to a neutral (zero) raster for just that one area,
  matching the existing fallback behaviour used elsewhere for areas with
  no input features. A single, un-partitioned study area can legitimately
  leave `area_name` NULL on every `study_area_grid` row while still naming
  the area itself - that case is distinguished from a genuinely missing
  sliver (grid cells exist for other areas, just not this one) so it still
  rasterizes normally instead of being skipped.
- Masking a raster to a geometrically thin area (a narrow coastal strip or
  sliver islet, not necessarily a small one) could fail entirely:
  `gdal:cliprasterbymasklayer` with `CROP_TO_CUTLINE` snaps the crop window
  to pixel boundaries, which can round down to zero rows or columns even
  when the source raster is perfectly valid, so `gdalwarp` refused to
  create a 0-sized dataset and no masked file was written. `_mask_raster`
  silently returned that nonexistent path anyway, so the area vanished from
  the combined VRT with no error reported (seen as `entrepreneurship_index`
  dropping several Cabo Verde islands while still reporting success).
  `_mask_raster` now detects a failed/degenerate crop and retries without
  `CROP_TO_CUTLINE`, keeping the source raster's own (already-valid) extent
  and masking only the pixel values - and raises clearly if that still
  doesn't produce a valid raster, instead of returning a bogus path.
- `factor_aggregation` and `dimension_aggregation` (the workflows behind
  every factor/dimension/analysis rollup, e.g. workplace discrimination's
  factor score) aborted the *entire* indicator with "produced no raster
  output for area cv_part20" whenever one area had no matching
  `study_area_grid` cells - the same sliver-area condition fixed above,
  but `AggregationWorkflowBase` lacked the `supports_empty_features_fallback`
  flag that lets a single ungridded area fall back to a neutral raster
  instead of failing the whole run. It now sets that flag like the other
  grid-first workflows, so one gridless sliver no longer blocks the
  factor/dimension/analysis score for the other 26 areas.
- **The `supports_empty_features_fallback` safety net above had a second,
  much more damaging side effect: it could silently wipe an indicator's,
  factor's or dimension's entire `study_area_grid` column back to NULL
  after a real, successful write** - seen as values present in the log
  ("Executing: UPDATE study_area_grid SET workplace_index = 2") and gone
  moments later ("Clearing column: UPDATE study_area_grid SET
  workplace_index = NULL"), with every downstream indicator/factor/
  dimension layer rendering as empty/red. `_apply_grid_column_zero_fallback()`
  fires for *any* area with zero matching grid cells or zero input
  features (not just slivers - an area simply having no OSM points/hazard
  polygons/etc. for this particular indicator is routine), and the first
  time it runs per workflow instance it unconditionally issued
  `UPDATE study_area_grid SET col = NULL` with no `WHERE` clause - every
  row, every area. Nine grid-first workflows each tracked their own
  separate "have I cleared this column yet" flag (`_column_cleared` on
  `PointPerCellWorkflow`/`PolygonPerCellWorkflow`/`PolylinePerCellWorkflow`/
  `SinglePointBufferWorkflow`/`MultiBufferDistancesNativeWorkflow`;
  `_grid_value_written`/`_grid_aggregated` on
  `ContextualIndexScoreWorkflow`/`IndexScoreWorkflow`/
  `AggregationWorkflowBase`) that was never synchronised with the base
  class's own `_grid_column_cleared` flag the fallback actually checks -
  so whichever area first had no features/cells (commonly *after* several
  other areas had already written real data) triggered the fallback's
  clear regardless of whether the column had, in fact, already been fully
  and correctly written. All nine now set `self._grid_column_cleared =
  True` immediately after their own successful write, so the fallback
  correctly limits itself to filling in the one empty area instead of
  wiping every other area's result.
- Every grid-write function in `grid_column_utils.py` now wraps its SQL
  `UPDATE`(s) in an explicit `StartTransaction()`/`CommitTransaction()`
  pair, checking the commit's return code and raising loudly if it fails,
  instead of relying on an unchecked `PRAGMA wal_checkpoint` + dataset
  close to persist the write (`gpkg_doctor.checkpoint_dataset()` swallows
  all exceptions by design, on the assumption that `GDALClose()` would
  still flush on its own - this codebase has already hit cases where that
  assumption doesn't hold, see the Windows GDALClose/access-violation fix
  above). Not the root cause of the data-loss symptom described above,
  but a real gap worth closing defensively.
- **Clearing a single indicator/factor/dimension left its on-disk outputs,
  `study_area_grid` column, and map layer behind.** `clear_item()` only
  reset the item's own status/result attributes - its masked rasters stayed
  on disk, its grid column kept its last value, and its layer stayed in the
  legend. Now also deletes the files directly inside the item's own
  workflow directory (never recursing into child subdirectories, so
  clearing a factor doesn't touch its indicators' outputs or vice versa),
  blanks the item's own grid column (new `JsonTreeItem.gridColumnName()`,
  matching the sanitisation `add_model_columns_to_grid()` used to create
  it), and removes the item's own layer(s) from the legend/registry via a
  new `geest.core.utilities.remove_from_map()` - which leaves the subgroup
  holding the item's children's layers/groups completely untouched.
- **Clearing a single-indicator factor's row cleared the indicator but left
  the factor itself untouched** - found against a real project (Cabo
  Verde): clearing the Contextual dimension correctly blanked
  `dim_contextual`, but each of its three single-indicator factors kept
  their stale "Completed" `fac_*` column/result/rasters after being
  "cleared". Root cause: `JsonTreeModel.data()` hides a factor with exactly
  one child indicator from the tree entirely, promoting that indicator's
  row to display in the factor's place labeled with the factor's name - so
  the one row a user sees and right-clicks ("Workplace Discrimination")
  really represents two tree items (the factor and its indicator) sharing
  a single visible row, and `index.internalPointer()` for that row returns
  the indicator, not the factor. `clear_item()` now also clears the hidden
  parent factor whenever the selected item is an indicator behind one
  (recursion still stops there - a factor with multiple, independently
  selectable children is untouched by clearing one of them, as before).
- **Rasterized output was entirely empty for every single-area (un-
  partitioned) project, even though the underlying `study_area_grid`
  column held the correct values** - found via a new end-to-end test
  driving the real clear/edit/run flow and sampling the actual raster
  pixels, not just checking the result file existed.
  `rasterize_grid_column()` builds a `WHERE area_name = '...'` clause, then
  has fallback logic for projects that never populate `area_name` on their
  grid rows at all (a single, un-partitioned area): it correctly detects
  that case and drops the attribute filter used to compute the raster's
  *extent*, but never dropped the same `where_clause` string handed to the
  actual GDAL burn - which still matched zero rows, so `gdal.Rasterize()`
  wrote nothing but its `nodata` fill value everywhere. The grid column
  (written directly over SQL, unaffected) was always correct; only the
  rasterized/combined-VRT output was empty. Both now derive from the same
  decision.
- **A plain Run (no Shift) on a dimension/factor silently kept using an
  indicator's OLD index score after it was edited**, when that indicator
  is hidden behind its single-child factor row and so can never be cleared
  directly from the tree: `queue_workflow_task()`'s "skip if already
  complete" check only looks at the item's own `result_file`, which
  editing `index_score` alone never touched. Fixed in
  `FixedValueDataSourceWidget.update_attributes()` - changing the value now
  blanks the indicator's own `result`/`result_file`, so the normal
  skip-if-already-complete check correctly recognises it needs to run
  again, without the user needing to know to hold Shift.

### Changed

- Grid-first workflows (`ContextualIndexScoreWorkflow`, `AggregationWorkflowBase`
  - index scores, factor/dimension/analysis aggregation) wrote their value
  to `study_area_grid` with one whole-table SQL `UPDATE` per area, even
  though that SQL has no area filter and produces an identical result every
  time - for a 27-area study area that meant running the same multi-second
  `UPDATE` 27 times over. It now runs once per workflow; per-area
  rasterizing, masking, and VRT-combining (needed to keep the output raster
  sparse rather than one dense bounding-box raster) are unchanged.

## [2.0.6] - 2026-10-13

### Added

- Reverse-engineered Software Requirements Specification under `srs/`
  (branded Word + PDF deliverables, 18 UML diagrams as SVG, one-shot
  `srs/build.sh` pipeline writing directly into the Kartoza Word template).
- SRS build toolchain in the dev shell (plantuml, python-docx, pillow,
  libreoffice, Lato).
- GeoPackage corruption causal analysis
  (`docs/gpkg-corruption-causal-analysis.md`).
- SRS chapter 8 "Shipped model catalogue", generated from
  `geest/resources/model.json` at build time
  (`srs/scripts/gen_model_catalogue.py`): a page per dimension and per
  factor, every indicator with its defaults, brand-styled WBS tree diagrams
  per dimension, and an indicator × processor capability matrix rendered as
  SVG/PNG.
- QGIS launcher scripts now symlink the working-tree plugin into the GEOE3
  profile's `python/plugins` folder before launching
  (`scripts/ensure_plugin_link.sh`).
- Launcher scripts pin QGIS to a light palette even when the desktop is in
  dark mode (`scripts/qgis_light_theme_startup.py` via `PYQGIS_STARTUP`;
  Qt 6.8+ colour-scheme override with a light-Fusion-palette fallback).
- GeoPackage write-path hardening (causal analysis §5, all four items):
  chunk tiles now go through the single unified writer connection, every
  WAL checkpoint in the process is serialised behind one lock, all layers
  (including `chunks`) are pre-created before worker threads start, and
  map refreshes are deferred while the writer is active.
- `admin.py generate-zip` now runs pre-flight checks before packaging:
  aborts if the version in `config.json` is already published on
  plugins.qgis.org, or if the checked-in `geest/metadata.txt` has drifted
  from `config.json` (`--skip-checks` to bypass for local iteration).
- Categorised `nix develop` command reference covering the full plugin
  lifecycle (`scripts/dev-help.sh`), replacing the old ad-hoc banner text.

### Changed

- The analysis report has been completely redesigned: a flat, World Bank-
  appropriate visual language (navy/cyan bands, hairline footers, page
  numbers), a proper horizontal bar chart for processing times, clean map
  neatlines with outside-frame coordinate annotations, and minimap grids —
  the overview page shows the overall score plus dimension minimaps, each
  dimension page its factor minimaps, and each factor page its indicator
  minimaps. Funding/attribution moved to a styled closing page, blank pages
  are impossible (layer validity is checked first), the cover typo is fixed,
  and report maps no longer depend on the project CRS (which also hung
  report generation when no project CRS was set). `export_pdf` gained an
  optional dpi override for fast draft exports.
- The flake now sources QGIS from nixpkgs: `qgis` 4.x (latest) and
  `qgis-ltr` 3.44.x; the geospatial-nix and qgis-source inputs were removed
  and `flake.lock` updated accordingly. nixpkgs is pinned to the last
  revision with binary-cached QGIS builds.
- Dev shell Qt tooling moved from Qt 5 to Qt 6 (`kdePackages.*`) to match
  QGIS 4.x — nixpkgs rejects mixed Qt shells; each QGIS variant now gets the
  matching PyQt WebEngine binding (PyQt6 for 4.x, PyQt5 for LTR).
- The dev shell recreates `.venv` automatically when the nix python
  interpreter changes (a stale venv made pip write into the read-only
  store).
- All pre-commit hook tooling (`black`, `flake8` + `flake8-docstrings` +
  `pydocstyle`, `isort`, and the `pre-commit-hooks` basics) is now
  provisioned by the nix flake instead of pre-commit fetching its own
  copies from PyPI/GitHub on every machine; the dev shell reinstalls the
  git hook on every `nix develop` so a nixpkgs pin bump can no longer leave
  a hook with a dangling store-path shebang.

### Fixed

- GeoE3 by population yields no result in national-scale analyses (#455).
- A disabled factor no longer re-enables itself unexpectedly (#450).
- The indicator description window now updates dynamically when switching
  indicators (#446).
- A broken or missing data source on one indicator no longer aborts a
  multi-indicator run with a raw Python traceback: workflow start-up
  errors are trapped at the queue boundary, the indicator's status icon
  flips to failed with an accessible explanation in its tooltip, and the
  rest of the queue continues. The known config-validation raises
  (multi-buffer, point-per-cell, OSM transport) now produce plain-language
  messages.
- GHSL tile download failures now raise a descriptive `GhslDownloadError`
  instead of surfacing later as a bare `FileNotFoundError` from zipfile;
  corrupt cached zips are removed so the next attempt re-downloads. The
  GHSL integration tests skip (rather than error) when the JRC service is
  unreachable, so CI no longer fails on network flakiness.
- SRS PDF conversion silently substituted DejaVu for the brand fonts and
  dropped bold: `srs/build.sh` now provisions Lato and JetBrains Mono via a
  throwaway fontconfig so PlantUML and LibreOffice embed the correct faces.
- GeoPackage self-healing hardening: locked/busy check results are now
  classified as "could not assess" instead of corruption, so the healer can
  never rebuild-and-swap a healthy database that is merely held by an active
  writer (regression tests added).
- QGIS 4 / PyQt6 crash in the open-project panel: `event.Resize` instance
  enum access replaced with `QEvent.Type.Resize` (works on PyQt5 too).
- QGIS 4 / PyQt6 plugin-load failures: all remaining unscoped Qt enum
  accesses (`QTreeView.InternalMove`/`NoEditTriggers`,
  `QFileDialog.ExistingFile`/`AcceptSave`, `QDockWidget.DockWidget*`,
  `QScrollArea.NoFrame`, `QAbstractScrollArea.AdjustToContents`,
  `QAbstractSpinBox.UpDownArrows`) replaced with their scoped forms — every
  Qt attribute reference in the package is now mechanically verified against
  both PyQt5 and PyQt6 by a new regression test
  (`test/test_qt_enum_compliance.py`), so this bug class is caught by the
  suite instead of at plugin load.
- QGIS 4 / PyQt6 crash when resizing data-source widgets: three widgets
  read `PM_DefaultFrameWidth` off a style *instance* — replaced with
  `QStyle.PixelMetric.PM_DefaultFrameWidth`, and the enum compliance test
  now also bans instance enum-member access (`style().PM_*`, `event.X`).
- Active Transport skipped as "unconfigured" although a layer was set: the
  polyline workflow now accepts the layer under any of its sibling mode
  keys (`osm_transport_polyline_per_cell_*`, `road_network_layer_path`),
  so switching analysis mode no longer orphans a configured layer; the
  decline log lists exactly which data-source keys are present. A new
  end-to-end suite (`test/test_workflow_job_e2e.py`) runs a real indicator
  through the production queue → job → factory → workflow chain on both
  QGIS images, covering the run path unit tests missed.
- Crash when running an indicator with no data source configured: six
  workflow `__init__` methods did `return False` on missing/invalid
  sources, which Python rejects with `TypeError: __init__() should return
  None`. They now raise `WorkflowNotConfiguredError`; the queue manager
  skips the job with a log entry and the tree panel shows a message-bar
  hint naming the unconfigured indicator. An AST regression test
  (`test/test_workflow_init_hygiene.py`) bans value-returns in workflow
  `__init__` methods.
- Plugin reloads no longer stack duplicate dock widgets: `unload()`
  reparents the dock before the queued deletion, and `initGui()` sweeps
  stale `GeoE3DockWidget` instances left by a crashed previous load.
- Plugin reloads no longer stack duplicate toolbar buttons ("GeoE3
  Settings" et al.): every unload phase is individually guarded so one
  failing step cannot abort the cleanup, all toolbar actions carry
  objectNames, and `initGui()` sweeps stale instances before creating new
  ones.
- QGIS 4 / PyQt6 plugin-load failure: the dock area persisted in QSettings
  is an int, which PyQt6 no longer auto-converts to `Qt.DockWidgetArea` —
  now normalised through `_to_dock_widget_area()` (invalid values fall back
  to the right dock) at every `addDockWidget` call, and the enum-vs-int
  dock-area comparison that silently broke tabifying is fixed. A new test
  (`test/test_geoe3_dock_construction.py`) builds the complete dock — all
  panels — on both PyQt5 and PyQt6 images so constructor-time porting
  regressions fail the suite instead of plugin load.

## [2.0.5] - 2026-09-01

### Added

- Environmental-hazard indicators now expose a clickable link to the source
  dataset in the World Bank Data Catalog for the selected hazard (fire,
  flood, landslide, cyclone, drought) (#398).
- Regional analyses now pull population demographics automatically from S2S
  when the population source is S2S — new population-vector processing task
  plus a population-source UI in the analysis aggregation dialog (#431).
- Nighttime Lights supports NOAA threshold classification (fixed Black
  Marble value ranges, 5 classes) alongside Jenks Natural Breaks; the binary
  option was replaced by the NOAA thresholds option (#396).

### Changed

- Flood data sources now work at both analysis scales: the raster (DDH
  0–900) path is available in regional analyses and the S2S path in
  national/local ones, with the S2S join using intersection-MAX; the source
  is auto-derived from the indicator configuration (#423).
- Tree headings are now consistently Title Case (acronym/apostrophe-safe),
  normalised at render time so existing projects' stored model.json is
  unaffected.

### Fixed

- GHSL masking (#420, #421): the GHSL options mask now uses the
  `ghsl_settlements` layer already stored in the study-area GeoPackage
  (clipped and reprojected at project setup) instead of depending on the
  `ghsl_settlements_layer.parquet` download path, so masked scoring no
  longer fails when that file is missing or empty.
- Landslide environmental-hazard scoring in regional analyses was reversed
  and is now corrected (#428).
- Regional S2S Nighttime Lights scoring was inaccurate: NTL classification
  now derives six dynamic classes from the data's own min–max range instead
  of Jenks breaks, so every cell value maps to a class and nothing renders
  unclassified (#424).
- Indicator dropdowns in the factor and dimension aggregation dialogs no
  longer shift left when toggling between indicators (vertical scrollbar
  pinned).
- Environmental-hazards datasource rows are better balanced: the source link
  sits beside the file selector, the layer combo is width-capped, and rows
  no longer hug the table border.
- Clicking the GeoE3 Score node now re-shows the last run result — the masked
  score when a mask is active — instead of always reverting to the raw
  score.

## [2.1.0] - 2026-07-13

### Added

- GeoPackage self-healing module (`geest.core.gpkg_doctor`) that detects and
  repairs, in place, the corruption classes seen in the field: stale WAL
  journals, duplicated schema objects (`trigger ... already exists` /
  malformed database schema errors caused by historic write races), and
  structural btree damage (repaired via a rebuild, keeping the corrupt
  original as a `.corrupt-<timestamp>.bak` file).
- Automatic GeoPackage health checks (run in a background task so the UI
  never blocks): on project open, after every workflow run completes, and at
  the end of study area creation.
- Self-heal-and-retry in workflow CRS resolution, so an analysis run against
  a corrupted study area GeoPackage repairs it and continues instead of
  failing with "Could not determine CRS for study area".
- Unit tests for the self-healing module (`test/test_gpkg_doctor.py`).

### Fixed

- Root cause of study area GeoPackage corruption: `SQLITE_USE_OGR_VFS=YES`
  was set process-wide during study area creation. The OGR VSI file layer
  does not implement SQLite file locking, so concurrent write connections
  could interleave page writes unprotected, producing duplicated
  `sqlite_master` pages ("trigger rtree_..._delete already exists"). The
  option is now forced off.

## [2.0.4] - earlier

- See git history for changes prior to the introduction of this changelog.
