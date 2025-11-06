---
marp: true
theme: default
paginate: true
header: 'Benchmarking and Profiling in Python'
footer: 'GEEST Development Team | 2025'
style: |
  section {
    font-size: 28px;
  }
  h1 {
    color: #2c5aa0;
  }
  h2 {
    color: #4a7dc9;
  }
  code {
    background: #f4f4f4;
  }
---

# Benchmarking and Profiling
## Optimizing Performance in Python Applications

**A Practical Guide for the GEEST Development Team**

---

## Today's Agenda

1. **Introduction to Performance Analysis**
2. **Profiling Tools and Techniques**
3. **Benchmarking Strategies**
4. **Memory Analysis**
5. **QGIS-Specific Considerations**
6. **Real-World Examples**
7. **Best Practices and Recommendations**

---

# Part 1: Introduction to Performance Analysis

---

## Why Performance Matters

- **User Experience**: Faster tools = happier users
- **Scalability**: Handle larger datasets efficiently
- **Resource Optimization**: Reduce memory and CPU usage
- **Cost Efficiency**: Lower infrastructure costs

**For GEEST**: Processing spatial data for gender analysis requires efficient algorithms

---

## Profiling vs Benchmarking

### Profiling
- **What**: Analyzing code execution to find bottlenecks
- **When**: During development and optimization
- **Goal**: Understand where time/memory is spent

### Benchmarking
- **What**: Measuring performance under controlled conditions
- **When**: Comparing alternatives, tracking improvements
- **Goal**: Quantify performance objectively

---

## The Performance Optimization Workflow

```
1. Measure (Profile)
   ↓
2. Identify Bottlenecks
   ↓
3. Optimize
   ↓
4. Verify (Benchmark)
   ↓
5. Repeat
```

**Golden Rule**: Never optimize without measuring first!

---

# Part 2: Profiling Tools and Techniques

---

## Python Built-in: cProfile

**The workhorse of Python profiling**

```python
import cProfile
import pstats
from io import StringIO

# Profile a function
profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = process_study_area()

profiler.disable()

# Print stats
s = StringIO()
ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
ps.print_stats(20)  # Top 20 functions
print(s.getvalue())
```

---

## cProfile: Understanding Output

```
   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
     1000    0.045    0.000    0.234    0.000 workflow_job.py:123(process_cell)
     5000    0.120    0.000    0.180    0.000 utilities.py:45(transform_geometry)
      500    0.089    0.000    0.089    0.000 {method 'execute' of 'sqlite3.Cursor'}
```

- **ncalls**: Number of calls
- **tottime**: Total time in function (excluding sub-calls)
- **cumtime**: Total time including sub-calls
- **percall**: Time per call

---

## cProfile: Command Line Usage

```bash
# Profile a script
python -m cProfile -o output.prof your_script.py

# Analyze with pstats
python -m pstats output.prof
% sort cumtime
% stats 20
```

**For GEEST**:
```bash
python -m cProfile -o geest_profile.prof admin.py build
```

---

## line_profiler: Line-by-Line Analysis

**Perfect for finding exact bottleneck lines**

```python
# Install: pip install line_profiler

# Add @profile decorator
@profile
def process_grid_cell(cell_geometry, features):
    """Process a single grid cell."""
    intersecting = []
    for feature in features:  # <- Is this slow?
        if cell_geometry.intersects(feature.geometry()):  # <- Or this?
            intersecting.append(feature)
    return intersecting
```

Run: `kernprof -l -v your_script.py`

---

## line_profiler: Output Example

```
Line #      Hits         Time  Per Hit   % Time  Line Contents
==============================================================
     5                                           @profile
     6                                           def process_grid_cell(cell_geometry, features):
     7         1          2.0      2.0      0.0      intersecting = []
     8      5000       1234.0      0.2     12.3      for feature in features:
     9      5000       8765.0      1.8     87.7          if cell_geometry.intersects(...):
    10       234         12.0      0.1      0.0              intersecting.append(feature)
    11         1          1.0      1.0      0.0      return intersecting
```

**Finding**: 87.7% time in geometry intersection!

---

## py-spy: Sampling Profiler

**Profile running processes without code changes**

```bash
# Install
pip install py-spy

# Sample a running process
py-spy top --pid 12345

# Generate flamegraph
py-spy record -o profile.svg -- python your_script.py

# Profile in real-time
py-spy record --subprocesses -o profile.svg -- python admin.py build
```

**Advantages**: No code modification, works on production systems

---

## Visualization: SnakeViz

**Interactive visualization of cProfile output**

```bash
# Install
pip install snakeviz

# Visualize profile
snakeviz output.prof
```

**Features**:
- Icicle and sunburst diagrams
- Interactive drill-down
- Function call relationships
- Time distribution visualization

---

## Profiling QGIS Plugins

```python
from qgis.core import QgsMessageLog, Qgis
import time
from functools import wraps

def profile_function(func):
    """Decorator to profile functions in QGIS."""
    @wraps(func)
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

---

## Profiling Example: GEEST

```python
class WorkflowJob:
    @profile_function
    def process_study_area(self):
        """Process the study area with profiling."""
        # ... existing code ...
        pass
    
    @profile_function
    def _process_grid(self, grid_layer):
        """Process grid with timing."""
        # ... existing code ...
        pass
```

View results in QGIS Log Panel → Filter by "Geest-Profile"

---

# Part 3: Benchmarking Strategies

---

## timeit: Microbenchmarks

**For comparing small code snippets**

```python
import timeit

# Compare two approaches
setup = """
from shapely.geometry import Point, Polygon
polygon = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
point = Point(0.5, 0.5)
"""

method1 = "polygon.contains(point)"
method2 = "point.within(polygon)"

time1 = timeit.timeit(method1, setup=setup, number=100000)
time2 = timeit.timeit(method2, setup=setup, number=100000)

print(f"Method 1: {time1:.4f}s")
print(f"Method 2: {time2:.4f}s")
print(f"Speedup: {time1/time2:.2f}x")
```

---

## pytest-benchmark

**Integrated benchmarking with pytest**

```python
# Install: pip install pytest-benchmark

def test_geometry_intersection(benchmark):
    """Benchmark geometry intersection."""
    from qgis.core import QgsGeometry
    
    poly1 = QgsGeometry.fromWkt("POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))")
    poly2 = QgsGeometry.fromWkt("POLYGON((0.5 0.5, 1.5 0.5, 1.5 1.5, 0.5 1.5, 0.5 0.5))")
    
    # Benchmark the intersection
    result = benchmark(poly1.intersection, poly2)
    
    assert result is not None
```

Run: `pytest test_benchmarks.py --benchmark-only`

---

## pytest-benchmark: Output

```
--------------------------------- benchmark: 1 tests ---------------------------------
Name (time in us)                    Min       Max      Mean    StdDev    Median
-----------------------------------------------------------------------------------
test_geometry_intersection        45.23    127.89    52.34      8.45     49.12
-----------------------------------------------------------------------------------
```

**Benefits**:
- Automatic statistical analysis
- Comparison across runs
- Regression detection
- Integration with CI/CD

---

## Real-World Benchmark: Grid Processing

```python
def test_grid_processing_benchmark(benchmark):
    """Benchmark grid processing with different cell sizes."""
    
    def process_with_cell_size(cell_size):
        grid = create_grid(bbox, cell_size)
        return process_all_cells(grid, features)
    
    # Benchmark 100m cells
    result = benchmark(process_with_cell_size, 100)
    
    assert result['processed_cells'] > 0
```

Compare: 50m vs 100m vs 250m cell sizes

---

## A/B Testing Approaches

```python
def compare_algorithms(dataset):
    """Compare two algorithms for the same task."""
    
    # Algorithm A: Spatial index
    start = time.perf_counter()
    result_a = process_with_spatial_index(dataset)
    time_a = time.perf_counter() - start
    
    # Algorithm B: Brute force
    start = time.perf_counter()
    result_b = process_brute_force(dataset)
    time_b = time.perf_counter() - start
    
    print(f"Spatial Index: {time_a:.2f}s")
    print(f"Brute Force: {time_b:.2f}s")
    print(f"Speedup: {time_b/time_a:.1f}x")
    
    assert result_a == result_b  # Verify correctness
```

---

## Continuous Benchmarking

**Track performance over time**

```yaml
# .github/workflows/benchmark.yml
name: Performance Benchmarks

on: [push, pull_request]

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run benchmarks
        run: pytest tests/benchmarks/ --benchmark-json=output.json
      - name: Store benchmark result
        uses: benchmark-action/github-action-benchmark@v1
        with:
          tool: 'pytest'
          output-file-path: output.json
```

---

# Part 4: Memory Analysis

---

## Why Memory Matters

**Common Issues in Spatial Processing**:
- Large datasets loaded into memory
- Memory leaks in long-running processes
- Inefficient data structures
- Unnecessary copies

**For GEEST**: Processing multiple layers and features simultaneously

---

## memory_profiler: Track Memory Usage

```python
# Install: pip install memory_profiler

from memory_profiler import profile

@profile
def process_large_dataset(layer_path):
    """Process a large geospatial dataset."""
    layer = QgsVectorLayer(layer_path, "layer", "ogr")
    
    results = []
    for feature in layer.getFeatures():  # Memory grows here?
        processed = process_feature(feature)
        results.append(processed)  # Or here?
    
    return results
```

Run: `python -m memory_profiler your_script.py`

---

## memory_profiler: Output

```
Line #    Mem usage    Increment   Line Contents
================================================
     3     50.0 MiB     50.0 MiB   @profile
     4                             def process_large_dataset(layer_path):
     5     52.1 MiB      2.1 MiB       layer = QgsVectorLayer(...)
     6                                 
     7     52.1 MiB      0.0 MiB       results = []
     8    245.8 MiB    193.7 MiB       for feature in layer.getFeatures():
     9    245.8 MiB      0.0 MiB           processed = process_feature(feature)
    10    245.8 MiB      0.0 MiB           results.append(processed)
    11                                 
    12    245.8 MiB      0.0 MiB       return results
```

**Issue**: 193.7 MiB accumulated in loop!

---

## Memory Optimization Strategies

### 1. Use Generators Instead of Lists

```python
# Bad: Loads all into memory
def get_all_features(layer):
    return [f for f in layer.getFeatures()]

# Good: Yields one at a time
def iterate_features(layer):
    for feature in layer.getFeatures():
        yield feature
```

### 2. Process in Chunks

```python
def process_in_batches(layer, batch_size=1000):
    batch = []
    for feature in layer.getFeatures():
        batch.append(feature)
        if len(batch) >= batch_size:
            yield process_batch(batch)
            batch = []  # Free memory
```

---

## Memory Optimization Strategies (cont.)

### 3. Explicit Cleanup

```python
def process_layers():
    layer = QgsVectorLayer(path, "layer", "ogr")
    
    # Process layer
    results = process(layer)
    
    # Explicit cleanup
    layer = None
    import gc
    gc.collect()
    
    return results
```

### 4. Use Memory-Efficient Data Structures

```python
# Instead of storing full features
features = [f for f in layer.getFeatures()]  # Heavy

# Store only IDs and fetch on demand
feature_ids = [f.id() for f in layer.getFeatures()]  # Light
```

---

## Tracemalloc: Python Built-in

```python
import tracemalloc

# Start tracking
tracemalloc.start()

# Your code
result = process_study_area()

# Get statistics
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

print("[ Top 10 memory consumers ]")
for stat in top_stats[:10]:
    print(stat)

tracemalloc.stop()
```

**Advantages**: No external dependencies, detailed allocation info

---

## Memory Leak Detection

```python
import tracemalloc
import gc

def detect_memory_leak(function, iterations=100):
    """Run function multiple times and check for memory growth."""
    
    tracemalloc.start()
    initial = tracemalloc.get_traced_memory()[0]
    
    for i in range(iterations):
        function()
        if i % 10 == 0:
            gc.collect()
            current = tracemalloc.get_traced_memory()[0]
            growth = (current - initial) / 1024 / 1024  # MB
            print(f"Iteration {i}: {growth:.2f} MB growth")
    
    tracemalloc.stop()
```

---

# Part 5: QGIS-Specific Considerations

---

## QGIS Performance Considerations

1. **Layer Access**: Use spatial indices
2. **Feature Iteration**: Request only needed attributes
3. **Geometry Operations**: Cache expensive calculations
4. **Coordinate Transformations**: Reuse QgsCoordinateTransform
5. **Expression Evaluation**: Compile expressions once

---

## Optimize Feature Iteration

```python
# Slow: Load all attributes
for feature in layer.getFeatures():
    process(feature)

# Fast: Request only needed fields
request = QgsFeatureRequest()
request.setSubsetOfAttributes(['field1', 'field2'], layer.fields())
request.setFlags(QgsFeatureRequest.NoGeometry)  # If geometry not needed

for feature in layer.getFeatures(request):
    process(feature)
```

**Speedup**: Up to 10x faster for large datasets!

---

## Use Spatial Indices

```python
from qgis.core import QgsSpatialIndex

# Build spatial index once
index = QgsSpatialIndex(layer.getFeatures())

# Fast spatial queries
bbox = QgsRectangle(xmin, ymin, xmax, ymax)
nearby_ids = index.intersects(bbox)

# Fetch only relevant features
for fid in nearby_ids:
    feature = layer.getFeature(fid)
    process(feature)
```

**Speedup**: 100x+ faster for spatial queries!

---

## Cache Expensive Operations

```python
class OptimizedProcessor:
    def __init__(self):
        # Cache transform objects
        self._transforms = {}
        # Cache compiled expressions
        self._expressions = {}
    
    def get_transform(self, source_crs, dest_crs):
        key = (source_crs.authid(), dest_crs.authid())
        if key not in self._transforms:
            self._transforms[key] = QgsCoordinateTransform(
                source_crs, dest_crs, QgsProject.instance()
            )
        return self._transforms[key]
```

---

## Profile QGIS Processing Algorithms

```python
from qgis import processing
import time

def benchmark_algorithm(algorithm, parameters):
    """Benchmark a QGIS processing algorithm."""
    
    start = time.perf_counter()
    result = processing.run(algorithm, parameters)
    duration = time.perf_counter() - start
    
    QgsMessageLog.logMessage(
        f"Algorithm '{algorithm}' took {duration:.2f}s",
        tag="Geest-Benchmark",
        level=Qgis.Info
    )
    
    return result, duration
```

---

## QGIS Task Manager Integration

```python
from qgis.core import QgsTask, QgsApplication

class ProfiledTask(QgsTask):
    def __init__(self, description):
        super().__init__(description, QgsTask.CanCancel)
        self.start_time = None
        self.result = None
    
    def run(self):
        self.start_time = time.perf_counter()
        
        # Your processing logic
        self.result = self.process_data()
        
        return True
    
    def finished(self, result):
        duration = time.perf_counter() - self.start_time
        QgsMessageLog.logMessage(
            f"Task completed in {duration:.2f}s",
            tag="Geest", level=Qgis.Info
        )
```

---

# Part 6: Real-World Examples

---

## Example 1: Optimizing Grid Processing

**Scenario**: GEEST processes analysis grids - which approach is faster?

```python
# Approach A: Process all cells at once
def process_all_cells(grid_layer, data_layer):
    results = []
    for cell in grid_layer.getFeatures():
        result = analyze_cell(cell, data_layer)
        results.append(result)
    return results

# Approach B: Use spatial index
def process_with_index(grid_layer, data_layer):
    index = QgsSpatialIndex(data_layer.getFeatures())
    results = []
    for cell in grid_layer.getFeatures():
        nearby = index.intersects(cell.geometry().boundingBox())
        result = analyze_cell_fast(cell, nearby)
        results.append(result)
    return results
```

---

## Example 1: Results

```python
# Benchmark both approaches
dataset = load_test_dataset()

time_a = timeit.timeit(
    lambda: process_all_cells(grid, data),
    number=1
)

time_b = timeit.timeit(
    lambda: process_with_index(grid, data),
    number=1
)

print(f"Without index: {time_a:.2f}s")
print(f"With index: {time_b:.2f}s")
print(f"Speedup: {time_a/time_b:.1f}x")
```

**Results**: 47x speedup with spatial index!

---

## Example 2: Memory-Efficient Layer Processing

**Problem**: Processing large vector layers causes memory issues

```python
# Before: Memory intensive
def process_layer_v1(layer):
    features = list(layer.getFeatures())  # Loads all into memory
    results = [process_feature(f) for f in features]
    return results

# After: Memory efficient
def process_layer_v2(layer):
    for feature in layer.getFeatures():  # Stream features
        result = process_feature(feature)
        yield result  # Generator - constant memory

# Usage
for result in process_layer_v2(layer):
    save_result(result)
```

**Memory reduction**: From 2GB to 50MB!

---

## Example 3: Parallel Processing

**GEEST can benefit from parallel processing for independent cells**

```python
from concurrent.futures import ProcessPoolExecutor
from qgis.core import QgsFeatureRequest

def process_cell_worker(cell_wkt, layer_path):
    """Worker function for parallel processing."""
    # Initialize in worker
    layer = QgsVectorLayer(layer_path, "layer", "ogr")
    cell_geom = QgsGeometry.fromWkt(cell_wkt)
    
    # Process
    result = analyze_cell(cell_geom, layer)
    return result

def parallel_grid_processing(grid_layer, data_layer_path):
    """Process grid cells in parallel."""
    cells = [(f.geometry().asWkt(), data_layer_path) 
             for f in grid_layer.getFeatures()]
    
    with ProcessPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(
            lambda x: process_cell_worker(*x), cells
        ))
    
    return results
```

---

## Example 3: Parallel Processing Results

**Benchmark**: 1000 grid cells, 4 CPU cores

```
Sequential: 240 seconds
Parallel (2 workers): 135 seconds (1.8x speedup)
Parallel (4 workers): 78 seconds (3.1x speedup)
Parallel (8 workers): 72 seconds (3.3x speedup)
```

**Considerations**:
- Overhead of process creation
- QGIS thread safety
- Memory per worker
- Diminishing returns beyond CPU count

---

# Part 7: Best Practices and Recommendations

---

## Best Practices: When to Profile

✅ **DO Profile**:
- When code feels slow
- Before optimizing
- After optimization (verify improvement)
- During code review for critical paths
- For regression testing

❌ **DON'T Profile**:
- Without a performance concern
- In production (use sampling profilers)
- Without understanding the code first

---

## Best Practices: Optimization Strategy

### 1. Measure First
```python
# Always establish baseline
baseline = benchmark(current_implementation)
```

### 2. Focus on Bottlenecks
```python
# Use 80/20 rule: Optimize the 20% that takes 80% of time
profile_data = analyze_with_cprofile()
hotspots = identify_top_functions(profile_data, threshold=0.1)
```

### 3. One Change at a Time
```python
# Version A: Baseline
# Version B: Change 1
# Version C: Change 1 + Change 2
# Measure each separately
```

### 4. Verify Correctness
```python
assert optimized_result == original_result
```

---

## Best Practices: Code Organization

```python
# geest/core/profiling.py
class PerformanceMonitor:
    """Centralized performance monitoring for GEEST."""
    
    def __init__(self):
        self.metrics = {}
    
    def time_operation(self, name):
        """Context manager for timing operations."""
        return TimingContext(name, self.metrics)
    
    def log_metrics(self):
        """Log all collected metrics."""
        for name, duration in self.metrics.items():
            QgsMessageLog.logMessage(
                f"{name}: {duration:.4f}s",
                tag="Geest-Performance",
                level=Qgis.Info
            )
```

---

## Best Practices: Usage

```python
# In workflow_job.py
performance = PerformanceMonitor()

with performance.time_operation("load_layers"):
    layers = load_all_layers()

with performance.time_operation("process_grid"):
    results = process_grid(layers)

with performance.time_operation("save_results"):
    save_to_geopackage(results)

# Log summary
performance.log_metrics()
```

---

## Recommended Tools for GEEST

### Essential Tools
1. **cProfile**: First-line profiler
2. **line_profiler**: Detailed analysis
3. **memory_profiler**: Memory tracking
4. **pytest-benchmark**: Automated benchmarking

### Visualization
1. **SnakeViz**: Interactive profile viewing
2. **py-spy**: Production profiling
3. **Memory Profiler**: Memory timeline graphs

### CI/CD Integration
1. **pytest-benchmark**: Track performance regressions
2. **GitHub Actions**: Automated benchmarks

---

## Setting Up Profiling in GEEST

```bash
# Install profiling dependencies
pip install line_profiler memory_profiler pytest-benchmark snakeviz

# Add to requirements-dev.txt
echo "line_profiler>=3.5.1" >> requirements-dev.txt
echo "memory_profiler>=0.60.0" >> requirements-dev.txt
echo "pytest-benchmark>=4.0.0" >> requirements-dev.txt
echo "snakeviz>=2.2.0" >> requirements-dev.txt

# Create benchmarks directory
mkdir -p test/benchmarks

# Run initial profiling
python -m cProfile -o geest_baseline.prof admin.py build
snakeviz geest_baseline.prof
```

---

## Common Pitfalls to Avoid

1. **Premature Optimization**
   - "Premature optimization is the root of all evil" - Donald Knuth
   - Profile first, optimize later

2. **Optimizing the Wrong Thing**
   - Focus on actual bottlenecks, not perceived ones
   - Use data, not intuition

3. **Breaking Functionality**
   - Always verify correctness after optimization
   - Maintain test coverage

4. **Over-Engineering**
   - Simple solutions often best
   - Complexity has a cost

---

## Performance Testing Checklist

- [ ] Establish baseline measurements
- [ ] Profile with representative data
- [ ] Test with different dataset sizes (small, medium, large)
- [ ] Check memory usage patterns
- [ ] Verify results correctness
- [ ] Document performance characteristics
- [ ] Set performance regression thresholds
- [ ] Integrate into CI/CD pipeline

---

## Quick Reference: Command Cheatsheet

```bash
# Profiling
python -m cProfile -o output.prof script.py
kernprof -l -v script.py
python -m memory_profiler script.py

# Benchmarking
pytest tests/benchmarks/ --benchmark-only
python -m timeit -n 1000 "test_function()"

# Visualization
snakeviz output.prof
py-spy record -o flamegraph.svg -- python script.py

# Analysis
python -m pstats output.prof
```

---

## Resources and Further Reading

### Documentation
- [Python Profilers Documentation](https://docs.python.org/3/library/profile.html)
- [line_profiler GitHub](https://github.com/pyutils/line_profiler)
- [memory_profiler GitHub](https://github.com/pythonprofilers/memory_profiler)

### Books
- "High Performance Python" by Micha Gorelick & Ian Ozsvald
- "Python Performance Tuning" by Oreilly

### Tools
- [py-spy](https://github.com/benfred/py-spy)
- [Scalene](https://github.com/plasma-umass/scalene) - CPU+GPU+Memory profiler
- [Austin](https://github.com/P403n1x87/austin) - Frame stack sampler

---

## Next Steps for GEEST

1. **Establish Baseline**
   - Profile current critical paths (grid processing, layer loading)
   - Document current performance characteristics

2. **Set Up Infrastructure**
   - Add profiling decorators to key functions
   - Create benchmark test suite
   - Integrate with CI/CD

3. **Optimize Iteratively**
   - Start with biggest bottlenecks
   - Measure improvement
   - Document changes

4. **Monitor Continuously**
   - Track performance metrics over time
   - Alert on regressions
   - Regular performance reviews

---

## Practical Exercise

**Your Turn!**

1. Choose a function in GEEST that you think might be slow
2. Profile it with cProfile
3. Identify the bottleneck
4. Try an optimization
5. Benchmark the improvement
6. Share results with the team

**Example**: Profile `workflow_job.py:process_study_area()`

---

## Discussion & Q&A

**Topics for Discussion**:
- What are the current performance pain points in GEEST?
- Which profiling tools should we adopt first?
- How do we integrate benchmarking into our workflow?
- What performance goals should we set?

**Open Floor**: Your questions and experiences

---

## Summary

### Key Takeaways

1. **Always measure before optimizing** - Don't guess, profile!
2. **Focus on bottlenecks** - 80/20 rule applies
3. **Use the right tool** - Different problems need different profilers
4. **Automate benchmarking** - Catch regressions early
5. **Memory matters** - Especially for spatial data processing
6. **QGIS-specific optimizations** - Spatial indices, feature requests
7. **Verify correctness** - Fast but wrong is still wrong

---

## Thank You!

### Questions?

**Resources**:
- This presentation: `docs/presentations/benchmarking-and-profiling.md`
- GEEST Repository: https://github.com/worldbank/GEEST
- Developer Guide: `README-dev.md`

**Contact**: Development Team

---

## Bonus: Advanced Topics

(For those interested in diving deeper)

---

## Bonus: Distributed Profiling

**For large-scale processing**

```python
import multiprocessing as mp
from cProfile import Profile

def profile_worker(func, *args):
    """Profile a worker process."""
    profiler = Profile()
    profiler.enable()
    
    result = func(*args)
    
    profiler.disable()
    profiler.dump_stats(f'worker_{mp.current_process().pid}.prof')
    
    return result
```

Merge profiles with:
```bash
python -m pstats worker_*.prof
```

---

## Bonus: GPU Profiling (for future)

**If GEEST uses GPU acceleration**

```python
# For PyTorch/TensorFlow
import torch.profiler as profiler

with profiler.profile(
    activities=[profiler.ProfilerActivity.CPU, 
                profiler.ProfilerActivity.CUDA]
) as prof:
    result = gpu_accelerated_operation()

print(prof.key_averages().table(sort_by="cuda_time_total"))
```

**Tools**: Nsight Systems, NVIDIA Profiler

---

## Bonus: Custom Profiling Decorators

```python
import functools
import time
from typing import Callable, Any

def profile_slow_functions(threshold_seconds: float = 1.0):
    """Decorator that logs only slow function calls."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            result = func(*args, **kwargs)
            duration = time.perf_counter() - start
            
            if duration > threshold_seconds:
                QgsMessageLog.logMessage(
                    f"SLOW: {func.__name__} took {duration:.2f}s",
                    tag="Geest-Performance",
                    level=Qgis.Warning
                )
            
            return result
        return wrapper
    return decorator
```

---

## Bonus: Performance Regression Tests

```python
# tests/benchmarks/test_performance_regression.py

def test_grid_processing_performance(benchmark):
    """Ensure grid processing doesn't regress."""
    
    result = benchmark(process_test_grid)
    
    # Alert if slower than baseline
    assert result.stats.stats.mean < 5.0, \
        f"Grid processing too slow: {result.stats.stats.mean:.2f}s"
```

**CI/CD Integration**:
- Fails build if performance degrades
- Tracks performance over time
- Automatic alerts

---

## Bonus: Real-time Performance Dashboard

```python
# Example: Flask dashboard for monitoring
from flask import Flask, render_template
import json

app = Flask(__name__)

@app.route('/performance')
def performance_dashboard():
    """Display real-time performance metrics."""
    metrics = load_performance_metrics()
    return render_template('dashboard.html', metrics=metrics)

# Run alongside QGIS for monitoring
```

**Visualization**: Grafana, Prometheus, or custom dashboards

---

# End of Presentation

## Remember: Measure, Optimize, Verify!

Thank you for your attention! 🎉
