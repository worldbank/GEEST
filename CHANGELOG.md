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

### Fixed

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
