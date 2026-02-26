# -*- coding: utf-8 -*-
# flake8: noqa
# isort: skip_file
# black: skip-file
"""📦 Tasks module.

This module contains functionality for tasks.
"""

from .grid_from_bbox_task import GridFromBboxTask
from .grid_from_bbox_h3_task import GridFromBboxH3Task
from .ors_checker_task import OrsCheckerTask
from .osm_downloader_task import OSMDownloaderTask
from .study_area_processing_task import StudyAreaProcessingTask
from .study_area_report_task import StudyAreaReportTask
from .analysis_report_task import AnalysisReportTask
from .ghsl_downloader_task import GHSLDownloaderTask
