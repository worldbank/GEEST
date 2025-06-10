# Welcome to GEEST

<p align="justify">
 Developed by the World Bank, <strong>GEEST (The Gender Enabling Environments Spatial Tool)</strong> is a powerful and user-friendly open-source spatial mapping tool that enables a comprehensive analysis of how various spatial factors influence women's employment and business opportunities in any geographic area of interest. 
 
 By using this tool, you can identify key areas for intervention, make data-driven decisions, and ultimately work toward creating more equitable job opportunities for women across different regions.

<p align="center">
  <img src="https://github.com/worldbank/GEEST/blob/main/docs/images/new%20images/framework.png?raw=true" height=600 alt="GEEST Framework" style="border-radius:10px;">
</p>

## Performance Optimization 🚀

GEEST incorporates performance monitoring and optimization using timing and caching mechanisms. This section explains how to use these features in your contributions.

### Timing and Performance Measurement ⏱️

We use a hierarchical timing system to track execution time across operations:

#### Method-Level Timing

```python
from geest.core.timer import timed

class YourWorkflowClass:
    
    @timed
    def some_method(self, arg1, arg2):
        """Add timing to method execution."""
        # Method implementation
        pass
```

#### Context Manager Timing

For more complex operations, use the `Timer` context manager for granular timing:

```python
from geest.core.timer import Timer

def complex_method(self):
    # Overall operation
    with Timer("🔍 operation_name"):
        # Sub-operation 1
        with Timer("⚙️ sub_operation_1"):
            # Code for sub-operation 1
            pass
        
        # Sub-operation 2
        with Timer("🔧 sub_operation_2"):
            # Code for sub-operation 2
            pass
```

### Caching for Performance

To enhance performance, especially for resource-intensive operations, GEEST utilizes caching mechanisms. Caching stores the results of expensive function calls and returns the cached result when the same inputs occur again.

#### Method-Level Caching

For caching at the method level, you can use the `@lru_cache` decorator from `functools`. This is useful for methods where you want to cache results based on the input parameters.

```python
from functools import lru_cache

class SomeWorkflow:
    
    @lru_cache(maxsize=128)
    def expensive_calculation(self, param1, param2):
        """Cache results of expensive operations."""
        # Expensive calculation
        return result
```

#### Manual Caching

In some cases, you might want to implement manual caching, where you have more control over the caching mechanism. This can be done using a simple dictionary to store and retrieve cached results.

```python
class AnotherWorkflow:
    
    def __init__(self):
        self._cache = {}
    
    def manual_cache_method(self, key):
        """Manual caching implementation."""
        if key in self._cache:
            return self._cache[key]  # Return cached result
        else:
            result = self._expensive_operation(key)
            self._cache[key] = result  # Store in cache
            return result
    
    def _expensive_operation(self, key):
        """Simulate an expensive operation."""
        # Expensive operation code
        return result
```

### Implementation Guidelines
#### When to Use @timed Decorator:

* Apply to all public methods in workflow and algorithm classes
* Especially useful for entry points and major processing steps
* Example methods to decorate:
  * run()
  * execute()
  * process_data()
  * calculate_result()

#### When to Use Timer Context Manager:

* Use inside methods with multiple distinct operations
* Helps identify bottlenecks within complex methods
* Use descriptive names with emojis for better log visibility
* Examples:

```python
with Timer("🔄 data_loading"):
    # Data loading code

with Timer("📊 analysis"):
    # Analysis code
```

### When to Apply LRU Cache:
* Best for pure functions (same inputs always produce same outputs)
* Useful for methods that:
  1. Are called repeatedly with the same parameters
  2. Have computationally expensive operations
  3. Return values rather than modifying state
  4. Have parameters that can be hashed
* Good candidates:
  * Geometry calculations
  * Feature counts
  * Configuration lookups
  * Validation methods

#### Recommended maxsize Values:

* Small lookup functions: maxsize=32
* Medium complexity functions: maxsize=128
* Large data processing functions: maxsize=256 or higher
* Consider memory impact for very large caches

### Performance Analysis 📊

The Timer module automatically generates hierarchical performance reports that look like:

```
╭─────────────────────────────────────────╮
│  🚀 PERFORMANCE SUMMARY 📊              │
╰─────────────────────────────────────────╯
├── 🔥 calculate_network: 2.35s (95.2%) - 1 calls
│   ├── ⏱️ _clip_network: 0.82s (34.9%) - 1 calls
│   │   └── 🌱 network_clipping_operation: 0.81s - 1 calls
│   └── ⚡ _process_isochrones: 1.48s (63.0%) - 1 calls
      ├── 🌱 _calculate_service_area: 0.44s (29.7%) - 3 calls
      │   └── 🚗 service_area_500: 0.15s (10.1%) - 1 calls
      └── 🌱 _create_concave_hull: 0.37s (25.0%) - 3 calls
          └── 🔷 concave_hull_500: 0.12s (8.1%) - 1 calls
┌─────────────────────────────────────────┐
│  ⏱️  Total execution time: 2.47s        │
└─────────────────────────────────────────┘
```

This report helps identify:

* 🔥 Hot/slow operations (>50% of total time)
* ⏱️ Medium operations (20-50% of total time)
* ⚡ Fast operations (5-20% of total time)
* 🌱 Tiny operations (<5% of total time)

See the NativeNetworkAnalysisProcessor class for a comprehensive example of both timing and caching implementation.

See the NativeNetworkAnalysisProcessor class for a comprehensive example of both timing and caching implementation.