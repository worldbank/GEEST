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

- Pyramid refresh (`grid_pyramid_utils.refresh_pyramid_column()` and
  `h3_pyramid_utils.refresh_h3_pyramid_column()`) now skips the real
  per-level aggregation entirely when a column's base-grid values are all
  exactly the same (or all NULL) - a flood-filled result with no spatial
  variation. A single `SELECT MIN/MAX/COUNT` up front already tells us
  every coarser level's MIN would be that identical constant too, so each
  level gets one flat `UPDATE level SET col = constant` instead of the
  square grid's correlated-subquery-per-row aggregation or the H3 path's
  read-every-child-into-Python-then-CASE-WHEN-batch approach. New shared
  `grid_pyramid_utils._uniform_column_value()` helper, reused by both grid
  types. Deliberately conservative: any NULL mixed with non-NULL values
  falls straight back to the real aggregation unchanged.
- "Add Study Area to Map" (analysis node context menu) now adds
  `study_area_grid` as a scale-dependent pyramid group - one layer per
  resolution, switching over at zoom - the same mechanism an indicator's
  own result layers already use, instead of one flat layer covering every
  cell at every zoom level (previously "slow to draw"). Regional analyses
  keep the single flat layer (H3's 7-child hierarchy has no pyramid).
  Falls back to the flat layer for local/national projects too if their
  pyramid scaffold was never built (projects predating the eager scaffold
  build). `geest/core/utilities.py` gained
  `add_study_area_grid_pyramid_to_map()`, reusing the same
  `_build_pyramid_level_group()` helper `add_pyramid_layer_to_map()` uses,
  now generalized to support a column-agnostic group (no score to
  symbolize or filter by - every level just shows the grid's own
  geometry).
- New local/national study areas default to an H3 hexagonal analysis grid
  instead of the square grid, with the H3 resolution automatically picked
  to match the chosen cell size by hexagon area. A new "Use an H3
  hexagonal grid for this analysis" checkbox on the Create Project page
  (checked by default) lets this be a per-project choice - uncheck it to
  use the classic square grid instead. This is additive - grid type is
  recorded once in `model.json`'s `grid_type` key at study-area creation
  time and never migrated afterwards, so every existing project (which
  has no `grid_type` key at all) keeps resolving to "square" and is
  completely unaffected; regional analyses are untouched too, and keep
  using a fixed-resolution H3 grid as before. Map visualization for
  H3-grid local/national projects gets the same scale-dependent
  multi-resolution pyramid as square-grid projects
  (`geest/core/h3_pyramid_utils.py`), cascading coarser H3 resolutions via
  `h3.cell_to_parent()` MIN-aggregation instead of 2x2 quad aggregation.
- GeoE3 Options panel gained a "Grid Pyramid Visualization Options" group
  with separate "National" and "Local" zoom-level settings (default 3
  each), since the two scales typically want different values. Replaces
  the previous hardcoded 4-step depth shared by both.
- "Download all resources" now also covers OSM-backed point indicators
  (schools, health facilities, pharmacies, grocery stores, financial
  services, kindergartens, green spaces, water points, public transport -
  the same keyword-matched categories the in-dialog "Download from OSM"
  button already offered), not just nighttime lights and environmental
  hazard rasters. Unlike those raster resources, an OSM indicator's
  configured source is an actual QGIS project layer, not a file path - the
  downloaded GeoPackage is loaded and added to the project, then wired up
  via the same `{widget_key}_layer_*` attributes
  `VectorDataSourceWidget.update_attributes()` itself writes, so the
  properties dialog shows it correctly configured afterward. While a
  download is in progress, its indicator's row now shows the same
  animated throbber a normal single-indicator run already shows, and the
  tree view is refreshed via `layoutChanged` (not a full model reset) once
  downloads/wiring finish, so newly-configured indicators immediately show
  their updated status without collapsing every expanded node or losing
  the current selection/scroll position. It also now covers environmental
  hazard indicators left at "Do Not Use" (the unconfigured default) but
  checked on in their factor's aggregation dialog - status "Required and
  not configured" - rather than only ones that already had a datasource
  mode explicitly picked. If such an indicator's id matches a known
  hazard type, downloading its data also switches its mode to
  "Environmental Hazard" at the same time, so it comes out "ready to run"
  instead of staying stuck on "required".
- `pyarrow` added to the nix dev shell. A benchmark comparing GeoPackage,
  Shapefile, FlatGeobuf and GeoParquet writes/reads found the file format
  made almost no difference to speed - the bottleneck was GDAL/OGR's
  per-feature Python API (`CreateFeature()`/feature iteration), not the
  on-disk format - so rather than migrate formats, the plugin's biggest
  bulk vector writes now try GDAL's columnar Arrow-batch API
  (`Layer.WritePyArrow()`/`GetArrowStreamAsPyArrow()`) first, which got
  ~2x faster writes and ~10x faster reads on the SAME GeoPackage files.
  New `geest/core/arrow_batch_writer.py` helper: if pyarrow isn't
  importable (not every QGIS install bundles it, though OSGeo4W's
  Windows installer does by default), it returns `False` and every call
  site falls straight back to its original per-feature `CreateFeature()`
  loop - no format change, no hard dependency, same `.gpkg` files every
  downstream reader already expects. Wired into the base grid write
  (`UnifiedWriterThread._write_grid_batch`/`_write_geometry_batch` in
  `study_area_processing_task.py`, the biggest cell counts - every study
  area creation) and both pyramid scaffold builders
  (`grid_pyramid_utils.py`/`h3_pyramid_utils.py`'s
  `_ensure_level_table_scaffold`/`_ensure_h3_level_table_scaffold`).
- Fixed a bug where `grid_type`/`analysis_h3_resolution` were silently
  dropped from `model.json` on the first save after study-area creation
  (`JsonTreeModel.loadJsonData()` only carried forward a fixed list of
  known analysis-level keys), reverting H3-grid projects back to the
  square-grid pyramid code path on every subsequent run.
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

### Fixed

- **H3 pyramid level geometry was corrupted by a GDAL axis-order bug:**
  `transform_wgs84_to_target()`/`bbox_to_wgs84()` built a WGS84<->target-CRS
  transform without pinning an explicit axis order; GDAL 3+'s default
  authority-compliant order for EPSG:4326 is (lat, lon), not (lon, lat), so
  coordinates were silently swapped - every coarser pyramid level table
  (`study_area_grid_h3_res<N>`) landed millions of metres away in the wrong
  UTM zone/hemisphere. The base `study_area_grid` layer happened to render
  correctly anyway, purely by coincidence: its own writer had an
  independent, compensating lat/lon-unpack bug that cancelled the first one
  out. Both are now fixed consistently (forcing
  `OAMS_TRADITIONAL_GIS_ORDER`), so the base grid is correct for the right
  reason instead of by accident.
- H3 pyramid level tables (coarser than the base) now honor the project's
  edge-hexagon clipping setting - previously only the base grid clipped to
  `study_area_clip_polygons`; coarser levels always kept full, unclipped
  parent hexagons regardless.
- `download_all_resources()` crashed with `AttributeError` on every
  early-exit path (no working directory, nothing to download) - it called
  a method that was never actually defined on `TreePanel`. It also now
  wires up any indicator whose resource file is already cached on disk but
  not yet configured as that indicator's source (e.g. a duplicated
  indicator, or a file a sibling indicator already downloaded) - no
  download needed.
- Clicking an indicator that has never run no longer opens the study area
  GeoPackage at all (previously every click attempted a pointless pyramid
  lookup for a column that doesn't exist yet).
- The status label now updates before each completed item's map layer
  group is built during a batch "Run all" - building it is synchronous and
  previously gave no feedback of its own, so a long batch run looked
  frozen at the same progress value for however long each item took.
- `defusedxml` is now a properly-provisioned dependency instead of
  silently falling back to `xml.etree.ElementTree` with a warning on every
  plugin load.
- Fixed a benign `ResourceWarning` ("subprocess is still running") from
  the detached report-viewer process on every report open.
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

### Changed

- Grid pyramid aggregation (both the square-grid and H3 engines) switched
  from MAX to MIN: a coarse cell now shows the worst score among its
  children, not the best, so zooming out never hides a poor result behind
  a better neighbor.
- Pyramid geometry scaffolds (square-grid and H3) now build eagerly, right
  after the base grid is written during study area creation - not lazily
  on an indicator's first run or first properties-dialog open. Only the
  score column itself (plain SQL) is still built lazily per indicator.
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
