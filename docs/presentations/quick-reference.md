# Benchmarking and Profiling Quick Reference

A companion guide to the "Benchmarking and Profiling" presentation.

## Essential Commands

### Profiling

```bash
# cProfile - Standard profiling
python -m cProfile -o output.prof your_script.py
python -m pstats output.prof

# line_profiler - Line-by-line profiling
kernprof -l -v your_script.py

# memory_profiler - Memory usage
python -m memory_profiler your_script.py

# py-spy - Sampling profiler (no code changes)
py-spy top --pid 12345
py-spy record -o profile.svg -- python your_script.py
```

### Benchmarking

```bash
# timeit - Quick microbenchmarks
python -m timeit -n 1000 "test_function()"

# pytest-benchmark
pytest tests/benchmarks/ --benchmark-only
pytest tests/benchmarks/ --benchmark-compare
```

### Visualization

```bash
# SnakeViz - Interactive profile viewer
snakeviz output.prof

# Generate flamegraph
py-spy record -o flamegraph.svg -- python your_script.py
```

## Code Examples

### Basic Profiling Decorator

```python
import time
import functools
from qgis.core import QgsMessageLog, Qgis

def profile_function(func):
    """Simple profiling decorator for QGIS."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        
        QgsMessageLog.logMessage(
            f"{func.__name__} took {duration:.4f}s",
            tag="Geest-Profile",
            level=Qgis.Info
        )
        return result
    return wrapper
```

### Context Manager for Timing

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(name):
    """Time a code block."""
    start = time.perf_counter()
    yield
    duration = time.perf_counter() - start
    print(f"{name}: {duration:.4f}s")

# Usage
with timer("Load layers"):
    layers = load_all_layers()
```

### Memory Tracking

```python
import tracemalloc

def track_memory(func):
    """Track memory usage of a function."""
    def wrapper(*args, **kwargs):
        tracemalloc.start()
        result = func(*args, **kwargs)
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        print(f"Current memory: {current / 1024 / 1024:.2f} MB")
        print(f"Peak memory: {peak / 1024 / 1024:.2f} MB")
        return result
    return wrapper
```

## QGIS-Specific Optimizations

### Optimize Feature Requests

```python
from qgis.core import QgsFeatureRequest

# Request only needed attributes
request = QgsFeatureRequest()
request.setSubsetOfAttributes(['field1', 'field2'], layer.fields())

# Skip geometry if not needed
request.setFlags(QgsFeatureRequest.NoGeometry)

# Use spatial filter
bbox = QgsRectangle(xmin, ymin, xmax, ymax)
request.setFilterRect(bbox)

# Iterate efficiently
for feature in layer.getFeatures(request):
    process(feature)
```

### Use Spatial Index

```python
from qgis.core import QgsSpatialIndex

# Build spatial index
index = QgsSpatialIndex(layer.getFeatures())

# Fast spatial queries
nearby_ids = index.intersects(bbox)
for fid in nearby_ids:
    feature = layer.getFeature(fid)
    process(feature)
```

### Cache Transformations

```python
from qgis.core import QgsCoordinateTransform, QgsProject

class TransformCache:
    def __init__(self):
        self._cache = {}
    
    def get(self, source_crs, dest_crs):
        key = (source_crs.authid(), dest_crs.authid())
        if key not in self._cache:
            self._cache[key] = QgsCoordinateTransform(
                source_crs, dest_crs, QgsProject.instance()
            )
        return self._cache[key]
```

## Benchmarking Template

```python
import timeit
import statistics

def benchmark(func, *args, runs=10, **kwargs):
    """Simple benchmarking function."""
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        func(*args, **kwargs)
        times.append(time.perf_counter() - start)
    
    return {
        'mean': statistics.mean(times),
        'median': statistics.median(times),
        'stdev': statistics.stdev(times) if len(times) > 1 else 0,
        'min': min(times),
        'max': max(times),
    }

# Usage
results = benchmark(process_grid, grid_layer, data_layer, runs=5)
print(f"Mean: {results['mean']:.4f}s")
print(f"Std Dev: {results['stdev']:.4f}s")
```

## pytest-benchmark Example

```python
def test_geometry_intersection_benchmark(benchmark):
    """Benchmark geometry intersection operations."""
    from qgis.core import QgsGeometry
    
    poly1 = QgsGeometry.fromWkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    poly2 = QgsGeometry.fromWkt("POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))")
    
    # Benchmark the operation
    result = benchmark(poly1.intersection, poly2)
    
    assert result is not None
    assert not result.isEmpty()
```

## Memory Optimization Patterns

### Use Generators

```python
# Bad: Loads all into memory
def get_all_features(layer):
    return [f for f in layer.getFeatures()]

# Good: Stream features
def iterate_features(layer):
    for feature in layer.getFeatures():
        yield feature
```

### Process in Batches

```python
def process_in_batches(layer, batch_size=1000):
    """Process features in batches to control memory."""
    batch = []
    for feature in layer.getFeatures():
        batch.append(feature)
        if len(batch) >= batch_size:
            yield process_batch(batch)
            batch.clear()  # Free memory
    
    # Process remaining
    if batch:
        yield process_batch(batch)
```

### Explicit Cleanup

```python
import gc

def process_layer():
    layer = QgsVectorLayer(path, "layer", "ogr")
    
    try:
        results = process(layer)
        return results
    finally:
        # Explicit cleanup
        layer = None
        gc.collect()
```

## Performance Monitoring Class

```python
class PerformanceMonitor:
    """Monitor performance across multiple operations."""
    
    def __init__(self):
        self.metrics = {}
    
    @contextmanager
    def measure(self, name):
        """Measure a code block."""
        start = time.perf_counter()
        yield
        duration = time.perf_counter() - start
        
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(duration)
    
    def report(self):
        """Generate performance report."""
        print("\n=== Performance Report ===")
        for name, times in self.metrics.items():
            print(f"{name}:")
            print(f"  Total: {sum(times):.4f}s")
            print(f"  Count: {len(times)}")
            print(f"  Mean: {statistics.mean(times):.4f}s")
        print("=" * 30)

# Usage
monitor = PerformanceMonitor()

with monitor.measure("load_layers"):
    layers = load_layers()

with monitor.measure("process_grid"):
    results = process_grid(layers)

monitor.report()
```

## Installation Commands

### Core Tools

```bash
# Install profiling tools
pip install line_profiler memory_profiler pytest-benchmark

# Install visualization tools
pip install snakeviz py-spy

# Install in development environment
pip install -r requirements-dev.txt
```

### Add to requirements-dev.txt

```text
line_profiler>=3.5.1
memory_profiler>=0.60.0
pytest-benchmark>=4.0.0
snakeviz>=2.2.0
py-spy>=0.3.14
```

## Common Profiling Patterns for GEEST

### Profile Grid Processing

```python
@profile_function
def process_study_area(self):
    """Process study area with profiling."""
    with timer("Load grid"):
        grid = self.load_grid()
    
    with timer("Process cells"):
        for cell in grid.getFeatures():
            self.process_cell(cell)
    
    with timer("Save results"):
        self.save_results()
```

### Benchmark Different Cell Sizes

```python
def test_cell_size_benchmark(benchmark):
    """Compare performance with different cell sizes."""
    cell_sizes = [50, 100, 250]
    
    for size in cell_sizes:
        result = benchmark(
            process_with_cell_size,
            bbox=test_bbox,
            cell_size=size
        )
        print(f"{size}m cells: {result.stats.stats.mean:.2f}s")
```

### Memory Profile Layer Processing

```python
@profile  # from memory_profiler
def process_large_layer(layer_path):
    """Process large layer with memory tracking."""
    layer = QgsVectorLayer(layer_path, "layer", "ogr")
    
    # Process in batches to control memory
    for batch in process_in_batches(layer, batch_size=1000):
        save_batch(batch)
```

## Troubleshooting

### High CPU Usage

1. Profile with cProfile to find hotspots
2. Check for nested loops
3. Consider spatial indexing
4. Look for repeated calculations

### High Memory Usage

1. Use memory_profiler to track allocations
2. Check for memory leaks in loops
3. Process data in batches
4. Use generators instead of lists

### Slow Geometry Operations

1. Use spatial indices for queries
2. Simplify geometries if possible
3. Cache coordinate transformations
4. Request only needed attributes

## Resources

- [Python Profilers Documentation](https://docs.python.org/3/library/profile.html)
- [line_profiler GitHub](https://github.com/pyutils/line_profiler)
- [memory_profiler GitHub](https://github.com/pythonprofilers/memory_profiler)
- [py-spy GitHub](https://github.com/benfred/py-spy)
- [pytest-benchmark Docs](https://pytest-benchmark.readthedocs.io/)
- [QGIS PyQGIS Cookbook](https://docs.qgis.org/latest/en/docs/pyqgis_developer_cookbook/)

## Next Steps for GEEST

1. **Baseline Performance**
   - Profile key operations
   - Document current metrics
   - Identify bottlenecks

2. **Setup Infrastructure**
   - Add profiling decorators
   - Create benchmark tests
   - Setup CI/CD monitoring

3. **Optimize Iteratively**
   - Focus on biggest bottlenecks
   - Measure improvements
   - Document changes

4. **Monitor Continuously**
   - Track performance over time
   - Alert on regressions
   - Regular reviews
