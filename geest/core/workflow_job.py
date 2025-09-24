# -*- coding: utf-8 -*-
import cProfile
import inspect
import io
import pstats
from functools import lru_cache, wraps

from qgis.core import Qgis, QgsApplication, QgsFeedback, QgsProcessingContext, QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from geest.core.settings import setting
from geest.utilities import log_message

from .json_tree_item import JsonTreeItem
from .workflow_factory import WorkflowFactory


# Utility functions for caching support
def make_hashable(obj):
    """Convert an unhashable object to a hashable representation for caching."""
    if isinstance(obj, (str, int, float, bool, tuple, type(None))):
        return obj
    elif isinstance(obj, (list, set)):
        return tuple(make_hashable(i) for i in obj)
    elif isinstance(obj, dict):
        return tuple(sorted((k, make_hashable(v)) for k, v in obj.items()))
    elif hasattr(obj, "__dict__"):
        # Get object's relevant state for hashing
        return (obj.__class__.__name__, make_hashable(vars(obj)))
    else:
        # Fall back to string representation
        return str(obj)


def cacheable(maxsize=128, typed=False):
    """
    Decorator factory that applies lru_cache with additional handling for unhashable objects.

    Args:
        maxsize: Max size of the LRU cache
        typed: Whether to treat different argument types as distinct

    Returns:
        A decorator that can be applied to methods
    """

    def decorator(func):
        # Get function signature to know which args are self/cls
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        # Create a wrapper that makes arguments hashable
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check if debug mode and caching are enabled
            developer_mode = int(setting(key="developer_mode", default=0))
            cache_enabled = int(setting(key="enable_caching", default=1))

            if not cache_enabled:
                # If caching disabled, just call the function directly
                return func(*args, **kwargs)

            # Convert args to hashable form (skipping self/cls)
            hashable_args = list(args)
            if param_names and param_names[0] in ("self", "cls"):
                hashable_args[0] = id(args[0])  # Replace self/cls with object id

            try:
                hashable_args = tuple(make_hashable(arg) for arg in hashable_args)
                hashable_kwargs = make_hashable(kwargs)

                # Generate cache key
                cache_key = (func.__name__, hashable_args, hashable_kwargs)

                # Check if result is in cache
                if cache_key in wrapper.cache:
                    if developer_mode:
                        log_message(f"🔄 Cache hit for {func.__name__}", level=Qgis.Info)
                    return wrapper.cache[cache_key]

                # Not in cache, call function
                result = func(*args, **kwargs)

                # Store in cache
                wrapper.cache[cache_key] = result

                # Manage cache size
                if len(wrapper.cache) > wrapper.maxsize:
                    # Remove oldest entry
                    wrapper.cache.pop(next(iter(wrapper.cache)))

                return result
            except (TypeError, ValueError):
                # If hashing fails, just call the function directly
                if developer_mode:
                    log_message(
                        f"⚠️ Cannot cache call to {func.__name__} - unhashable arguments",
                        level=Qgis.Warning,
                    )
                return func(*args, **kwargs)

        # Initialize cache dict and settings
        wrapper.cache = {}
        wrapper.maxsize = maxsize
        wrapper.hits = 0
        wrapper.misses = 0

        # Add clear cache method
        def clear_cache():
            wrapper.cache.clear()

        wrapper.clear_cache = clear_cache

        return wrapper

    return decorator


class WorkflowJob(QgsTask):
    """
    Represents an individual workflow task. Uses QgsFeedback for progress reporting
    and cancellation, and the WorkflowFactory to create the appropriate workflow.
    """

    # Class-level profiling statistics
    _combined_profiler = None
    _profiling_enabled = False
    _profiling_initialized = False
    _jobs_profiled = 0
    _cache_registry = []  # Registry of all cached methods

    @classmethod
    @lru_cache(maxsize=1)
    def initialize_profiling(cls):
        """Initialize profiling if debug mode is enabled and not already initialized."""
        if not cls._profiling_initialized:
            developer_mode = int(setting(key="developer_mode", default=0))
            cls._profiling_enabled = developer_mode > 0
            if cls._profiling_enabled:
                cls._combined_profiler = pstats.Stats()
                log_message("🔍 WorkflowJob profiling enabled", level=Qgis.Info)
            cls._profiling_initialized = True

    @classmethod
    @lru_cache(maxsize=1)
    def get_profiling_stats(cls):
        """Get the combined profiling statistics."""
        return cls._combined_profiler if cls._profiling_enabled else None

    @classmethod
    def save_profiling_stats(cls, output_file=None):
        """
        Save the accumulated profiling stats to a file in a format compatible with profiling tools.

        Args:
            output_file: Path to save stats. If None, will save to a default location.

        Returns:
            Path to the saved file or None if profiling is disabled
        """
        if not cls._profiling_enabled or not cls._combined_profiler:
            return None

        if output_file is None:
            # Use a default location in the QGIS user profile directory
            import datetime
            from pathlib import Path

            profile_dir = Path(QgsApplication.qgisSettingsDirPath()) / "geest" / "profiles"
            profile_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = str(profile_dir / f"workflow_profile_{timestamp}.prof")  # Use .prof extension

        # Save the stats in binary format
        cls._combined_profiler.dump_stats(output_file)

        log_message(f"📊 WorkflowJob profiling stats saved to {output_file}", level=Qgis.Info)
        return output_file

    @classmethod
    @lru_cache(maxsize=1)
    def print_profiling_summary(cls):
        """Print a summary of the profiling stats to the log."""
        if not cls._profiling_enabled or not cls._combined_profiler:
            log_message("⚠️ WorkflowJob profiling is not enabled", level=Qgis.Warning)
            return

        log_message(
            f"📊 WorkflowJob Profiling Summary ({cls._jobs_profiled} jobs)",
            level=Qgis.Info,
        )
        log_message("=" * 50)

        s = io.StringIO()
        cls._combined_profiler.sort_stats("cumulative")
        cls._combined_profiler.print_stats(20, 0.1, s)  # Print top 20 functions, min 10% of total time
        log_message(s.getvalue())
        log_message("=" * 50)

    @classmethod
    def clear_all_caches(cls):
        """Clear all registered method caches."""
        cleared_count = 0
        for cached_method in cls._cache_registry:
            if hasattr(cached_method, "cache_clear"):
                cached_method.cache_clear()
                cleared_count += 1
            elif hasattr(cached_method, "clear_cache"):
                cached_method.clear_cache()
                cleared_count += 1

        log_message(f"🧹 Cleared {cleared_count} method caches", level=Qgis.Info)

    @classmethod
    @lru_cache(maxsize=16)
    def get_workflow_factory(cls):
        """Get a cached workflow factory instance."""
        return WorkflowFactory()

    # Signals for task lifecycle
    job_queued = pyqtSignal()
    job_started = pyqtSignal()
    job_canceled = pyqtSignal()
    # Custom signal to emit when the job is finished
    job_finished = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        description: str,
        context: QgsProcessingContext,
        item: JsonTreeItem,
        cell_size_m: float = 100.0,
    ):
        """
        Initialize the workflow job.
        :param description: Task description
        :param context: QgsProcessingContext object - we will use this to pass any QObjects in to the thread
                to keep things thread safe
        :param item: JsonTreeItem object representing the task - this is a reference
              so it will update the tree directly when modified
        :param cell_size_m: Cell size in meters for raster operations
        """
        super().__init__(description)
        self.context = context  # QgsProcessingContext object used to pass objects to the thread
        self._item = item  # ⭐️ This is a reference - whatever you change in this item will directly update the tree
        self._cell_size_m = cell_size_m  # Cell size in meters for raster operations
        self._feedback = QgsFeedback()  # Feedback object for progress and cancellation

        # Use cached factory
        workflow_factory = self.__class__.get_workflow_factory()
        self._workflow = workflow_factory.create_workflow(
            item=self._item,
            cell_size_m=self._cell_size_m,
            feedback=self._feedback,
            context=self.context,
        )  # Create the workflow
        self.setProgress(0.0)  # always use float
        # This should be automatic see https://qgis.org/pyqgis/3.40/core/QgsTask.html#qgis.core.QgsTask.setProgress
        self._workflow.progressChanged.connect(self.updateProgress)

        # Initialize the class-level profiling if needed
        self.__class__.initialize_profiling()

        # Per-instance profiler
        self._profiler = None

        # Emit the 'queued' signal upon initialization
        self.job_queued.emit()

        # Cache for intra-job method calls
        self._method_cache = {}

    @cacheable(maxsize=64)
    def updateProgress(self, progress: float):
        """
        Used by the workflow to set the progress of the task.
        :param progress: The progress value
        """
        log_message(f"Progress in workflow job is: {progress}")
        self.setProgress(progress)

    # Don't cache run - this is the main execution method and should always run
    def run(self) -> bool:
        """
        Executes the workflow created by the WorkflowFactory. Uses the QgsFeedback
        object for progress reporting and cancellation.
        :return: True if the task was successful, False otherwise
        """
        # Set up profiling if enabled
        if self.__class__._profiling_enabled:
            self._profiler = cProfile.Profile()
            self._profiler.enable()
            log_message(
                f"🔍 Profiling started for workflow: {self.description()}",
                level=Qgis.Info,
            )

        if not self._workflow:
            log_message(
                f"Error: No workflow assigned to {self.description()}",
                tag="Geest",
                level=Qgis.Critical,
            )
            return False

        try:
            log_message(f"Running workflow: {self.description()}")

            # Emit the 'started' signal before running the workflow
            self.job_started.emit()
            result = self._workflow.execute()
            log_message(
                f"WorkflowJob {self.description()} attributes.",
                tag="Geest",
                level=Qgis.Info,
            )
            # attributes = self._item.attributes()
            log_message(f"{self._item.attributesAsMarkdown()}")
            if result:
                log_message(
                    f"Workflow {self.description()} completed.",
                    tag="Geest",
                    level=Qgis.Info,
                )
                return True
            else:
                log_message(
                    f"Workflow {self.description()} did not complete successfully.",
                    tag="Geest",
                    level=Qgis.Info,
                )
                return False

        except Exception as e:
            log_message(f"Error during task execution: {e}", level=Qgis.Critical)
            import traceback

            log_message(
                f"{traceback.format_exc()}",
                tag="Geest",
                level=Qgis.Critical,
            )
            error_message = f"Error in {self.description()}: {str(e)}"
            self.error_occurred.emit(error_message)
            return False

        finally:
            # Stop profiling and accumulate stats if enabled
            if self.__class__._profiling_enabled and self._profiler:
                self._profiler.disable()

                # Add this profile to the combined stats
                stats = pstats.Stats(self._profiler)
                if self.__class__._combined_profiler is None:
                    self.__class__._combined_profiler = stats
                else:
                    self.__class__._combined_profiler.add(stats)

                self.__class__._jobs_profiled += 1

                # Log a brief summary
                s = io.StringIO()
                stats.sort_stats("cumulative")
                stats.print_stats(10, 0.3, s)  # Top 10 functions, min 30% of total time

                log_message(
                    f"🔍 Profiling results for workflow: {self.description()}",
                    level=Qgis.Info,
                )
                log_message(f"Total jobs profiled so far: {self.__class__._jobs_profiled}")
                # Only log detailed stats in verbose mode
                verbose_mode = int(setting(key="verbose_mode", default=0))
                if verbose_mode:
                    log_message(s.getvalue())

                # Save profiling stats to a file
                output_file = self.__class__.save_profiling_stats()
                if output_file:
                    log_message(
                        f"Profiling stats saved to {output_file}",
                        level=Qgis.Info,
                    )

    @lru_cache(maxsize=8)
    def feedback(self) -> QgsFeedback:
        """
        Returns the feedback object, allowing external systems to monitor progress and cancellation.
        :return: QgsFeedback object
        """
        return self._feedback

    @cacheable(maxsize=8)  # Simple method can be cached with our custom decorator
    def finished(self, success: bool) -> None:
        """
        Override the finished method to emit a custom signal when the task is finished.
        :param success: True if the task was completed successfully, False otherwise
        """
        log_message(
            "0000000000000 🏁 Job Finished 000000000000000000",
            tag="Geest",
            level=Qgis.Info,
        )
        # Emit the custom signal job_finished with the success state
        self.job_finished.emit(success)

    # Register decorators with class registry for cache management
    _cache_registry.extend(
        [
            initialize_profiling,
            get_profiling_stats,
            print_profiling_summary,
            get_workflow_factory,
        ]
    )
