# GeoE3 Workflow Analysis: Raster vs Vector Processing

This document analyzes all workflows in the GeoE3 plugin to identify which can be migrated from raster-based processing to pure vector/SQL operations on the study_area_grid layer.

## Workflow Analysis Table

| Type                                 | ID                                                      | Workflow Option                          | Raster Only (Current) | Vector-Only Possible? | Notes                               |
| ------------------------------------ | ------------------------------------------------------- | ---------------------------------------- | --------------------- | --------------------- | ----------------------------------- | --- |
| **CONTEXTUAL DIMENSION**             |                                                         |                                          |                       |                       |                                     |     |
| Dimension                            | contextual                                              | Dimension aggregation                    | Yes                   | **Yes**               | `SUM(factor * weight)` SQL          |
| Factor                               | eplex                                                   | Factor aggregation                       | Yes                   | **Yes**               | `SUM(indicator * weight)` SQL       |
| Factor                               | workplace_discrimination                                | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | regulatory_frameworks                                   | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | financial_inclusion                                     | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Indicator                            | eplex_score_indicator                                   | use_eplex_score                          | No                    | **Yes**               | Uniform scalar → set attribute      |
| Indicator                            | eplex_score_indicator                                   | use_index_score                          | No                    | **Yes**               | Uniform scalar                      |
| Indicator                            | eplex_score_indicator                                   | use_contextual_index_score               | No                    | **Yes**               | Rescaled scalar                     |
| Indicator                            | Workplace_Index                                         | use_contextual_index_score               | No                    | **Yes**               | Rescaled scalar                     |
| Indicator                            | Pay_Parenthood_Index                                    | use_contextual_index_score               | No                    | **Yes**               | Rescaled scalar                     |
| Indicator                            | Entrepreneurship_Index                                  | use_contextual_index_score               | No                    | **Yes**               | Rescaled scalar                     |
| **ACCESSIBILITY DIMENSION**          |                                                         |                                          |                       |                       |                                     |     |
| Dimension                            | accessibility                                           | Dimension aggregation                    | Yes                   | **Yes**               | `SUM(factor * weight)` SQL          |
| Factor                               | women_s_travel_patterns                                 | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted avg of 5 indicators    |
| Factor                               | access_to_public_transport                              | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | access_to_health_facilities                             | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | access_to_education_and_training_facilities             | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | access_to_financial_facilities                          | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Indicator                            | Kindergartens_Location                                  | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join: grid ∩ buffers        |
| Indicator                            | Kindergartens_Location                                  | use_single_buffer_point                  | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Kindergartens_Location                                  | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Primary_School_Location                                 | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Primary_School_Location                                 | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Groceries_Location                                      | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Groceries_Location                                      | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Pharmacies_Location                                     | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Pharmacies_Location                                     | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Green_Space_location                                    | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Green_Space_location                                    | use_polygon_per_cell                     | No                    | **Yes**               | Polygon intersection                |
| Indicator                            | Public_Transport_location                               | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Public_Transport_location                               | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Hospital_Location                                       | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Hospital_Location                                       | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Universities_Location                                   | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Universities_Location                                   | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Banks_Location                                          | use_multi_buffer_point                   | No                    | **Yes**               | Spatial join                        |
| Indicator                            | Banks_Location                                          | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| **PLACE CHARACTERIZATION DIMENSION** |                                                         |                                          |                       |                       |                                     |     |
| Dimension                            | place_characterization                                  | Dimension aggregation                    | Yes                   | **Yes**               | `SUM(factor * weight)` SQL          |
| Factor                               | active_transport                                        | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | safety_perception                                       | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | fcv                                                     | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | education                                               | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | digital_inclusion                                       | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Factor                               | environmental_hazards                                   | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted avg of 5 hazards       |
| Factor                               | water_sanitation                                        | Factor aggregation                       | Yes                   | **Yes**               | SQL weighted average                |
| Indicator                            | Active_Transport_Network                                | use_polyline_per_cell                    | No                    | **Yes**               | Polyline length per cell            |
| Indicator                            | Active_Transport_Network                                | use_osm_transport_polyline_per_cell      | No                    | **Yes**               | OSM highway scoring per cell        |
| Indicator                            | Street_Lights                                           | use_nighttime_lights                     | **Yes**               | No                    | GHSL nighttime lights raster        |
| Indicator                            | Street_Lights                                           | use_street_lights                        | Maybe                 | Maybe                 | Point buffers=vector, raster=raster |
| Indicator                            | Street_Lights                                           | use_classify_safety_polygon_into_classes | No                    | **Yes**               | Polygon classification              |
| Indicator                            | FCV                                                     | use_csv_to_point_layer                   | No                    | **Yes**               | CSV→points→buffer→intersect         |
| Indicator                            | FCV                                                     | use_single_buffer_point                  | No                    | **Yes**               | Spatial join with buffer            |
| Indicator                            | FCV                                                     | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| Indicator                            | Education                                               | use_index_score_with_ghsl                | **Yes**               | No                    | Requires GHSL raster mask           |
| Indicator                            | Education                                               | use_classify_polygon_into_classes        | No                    | **Yes**               | Polygon classification              |
| Indicator                            | Digital_Inclusion                                       | use_index_score_with_ookla               | **Yes**               | No                    | Requires Ookla raster               |
| Indicator                            | Digital_Inclusion                                       | use_classify_polygon_into_classes        | No                    | **Yes**               | Polygon classification              |
| Indicator                            | Fire                                                    | use_environmental_hazards                | **Yes**               | No                    | Hazard raster input                 |
| Indicator                            | Flood                                                   | use_environmental_hazards                | **Yes**               | No                    | Hazard raster input                 |
| Indicator                            | Landslide                                               | use_environmental_hazards                | **Yes**               | No                    | Hazard raster input                 |
| Indicator                            | Cyclone                                                 | use_environmental_hazards                | **Yes**               | No                    | Hazard raster input                 |
| Indicator                            | Drought                                                 | use_environmental_hazards                | **Yes**               | No                    | Hazard raster input                 |
| Indicator                            | Water_Sanitation                                        | use_single_buffer_point                  | No                    | **Yes**               | Spatial join with 3km buffer        |
| Indicator                            | Water_Sanitation                                        | use_point_per_cell                       | No                    | **Yes**               | Count points in cell                |
| **ANALYSIS RESULTS**                 |                                                         |                                          |                       |                       |                                     |     |
| Analysis                             | geoe3_score                                             | Analysis aggregation                     | Yes                   | **Yes**               | `SUM(dimension * weight)` SQL       |
| Analysis                             | geoe3_by_population                                     | Population weighting                     | Yes                   | **Yes**               | `geoe3_score * population` SQL      |
| Analysis                             | geoe3_score_ghsl_masked                                 | GHSL masking                             | **Yes**               | No                    | Requires GHSL settlement raster     |
| Analysis                             | geoe3_by_population_ghsl_masked                         | GHSL + population                        | **Yes**               | No                    | Requires GHSL settlement raster     |
| Analysis                             | geoe3_score_subnational_aggregation                     | Subnational stats                        | Yes                   | **Yes**               | SQL GROUP BY subnational unit       |
| Analysis                             | geoe3_by_population_subnational_aggregation             | Subnational + pop                        | Yes                   | **Yes**               | SQL GROUP BY with population        |
| Analysis                             | geoe3_score_ghsl_masked_subnational_aggregation         | GHSL + subnational                       | **Yes**               | No                    | Requires GHSL raster first          |
| Analysis                             | geoe3_by_population_ghsl_masked_subnational_aggregation | All combined                             | **Yes**               | No                    | Requires GHSL raster first          |
| Analysis                             | geoe3_by_population_by_opportunities_mask               | Opportunities mask                       | **Yes**               | No                    | Requires opportunities raster       |
| Analysis                             | population                                              | Population per cell                      | **Yes**               | No                    | Sample population raster            |

---

## Summary by Type

| Type      | Total                 | Raster Required   | Vector-Only Possible      |
| --------- | --------------------- | ----------------- | ------------------------- |
| Dimension | 3                     | 3 (current impl)  | **3** (all migratable)    |
| Factor    | 16                    | 16 (current impl) | **16** (all migratable)   |
| Indicator | 21 IDs, ~40 workflows | 8 workflows       | **32+ workflows**         |
| Analysis  | 10                    | 5                 | **5** (partial migration) |
| **TOTAL** | ~70 workflows         | ~32               | **~56 migratable**        |

---

## Raster-Only Dependencies

The following workflows genuinely require raster data and cannot be converted to pure vector operations:

| Workflow                       | Raster Data Required                     | Reason                            |
| ------------------------------ | ---------------------------------------- | --------------------------------- |
| use_nighttime_lights           | GHSL Nighttime Lights                    | Input is raster imagery           |
| use_environmental_hazards (5x) | Fire, Flood, Landslide, Cyclone, Drought | Input hazard data is raster       |
| use_index_score_with_ghsl      | GHSL Settlement Layer                    | Mask requires raster intersection |
| use_index_score_with_ookla     | Ookla Internet Coverage                  | Coverage data is raster           |
| population                     | Population Raster                        | WorldPop/GHSL population grids    |
| geoe3\_\*\_ghsl_masked         | GHSL Settlement Layer                    | Masking requires raster           |
| geoe3\_\*\_opportunities_mask  | Opportunities Raster                     | Masking requires raster           |

---

## SQL Examples for Vector-Only Workflows

### Indicator: Index Score (Uniform Value)

```sql
-- Set a uniform score across all grid cells
UPDATE study_area_grid
SET eplex_score_indicator = 3.5
WHERE area_name = 'Study Area 1';
```

### Indicator: Multi-Buffer Point (Spatial Join)

```sql
-- Score grid cells based on proximity to points (e.g., kindergartens)
-- Assumes buffers have been pre-computed with scores
UPDATE study_area_grid g
SET kindergartens_location = COALESCE(
    (SELECT MAX(b.score)
     FROM kindergarten_buffers b
     WHERE ST_Intersects(g.geom, b.geom)),
    0
)
WHERE area_name = 'Study Area 1';
```

### Indicator: Point Per Cell (Count)

```sql
-- Count features within each grid cell
UPDATE study_area_grid g
SET water_sanitation = (
    SELECT COUNT(*)
    FROM water_points p
    WHERE ST_Contains(g.geom, p.geom)
)
WHERE area_name = 'Study Area 1';
```

### Indicator: Polyline Per Cell (Length/Score)

```sql
-- Calculate walkability score based on road types in cell
UPDATE study_area_grid g
SET active_transport_network = COALESCE(
    (SELECT MAX(
        CASE
            WHEN r.highway IN ('footway', 'pedestrian', 'cycleway') THEN 5
            WHEN r.highway IN ('residential', 'living_street') THEN 4
            WHEN r.highway IN ('tertiary', 'unclassified') THEN 3
            WHEN r.highway IN ('secondary') THEN 2
            WHEN r.highway IN ('primary', 'trunk') THEN 1
            ELSE 0
        END
    )
     FROM osm_roads r
     WHERE ST_Intersects(g.geom, r.geom)),
    0
)
WHERE area_name = 'Study Area 1';
```

### Factor Aggregation (Weighted Average)

```sql
-- Aggregate indicators into factor score
UPDATE study_area_grid
SET women_s_travel_patterns = (
    kindergartens_location * 0.2 +
    primary_school_location * 0.2 +
    groceries_location * 0.2 +
    pharmacies_location * 0.2 +
    green_space_location * 0.2
)
WHERE area_name = 'Study Area 1';
```

### Dimension Aggregation (Weighted Average)

```sql
-- Aggregate factors into dimension score
UPDATE study_area_grid
SET accessibility = (
    women_s_travel_patterns * 0.2 +
    access_to_public_transport * 0.2 +
    access_to_health_facilities * 0.2 +
    access_to_education_and_training_facilities * 0.2 +
    access_to_financial_facilities * 0.2
)
WHERE area_name = 'Study Area 1';
```

### Analysis: GeoE3 Score (Final Aggregation)

```sql
-- Calculate final GeoE3 score from dimensions
UPDATE study_area_grid
SET geoe3_score = (
    contextual * 0.1 +
    accessibility * 0.45 +
    place_characterization * 0.45
)
WHERE area_name = 'Study Area 1';
```

### Analysis: Population Weighted Score

```sql
-- Calculate population-weighted score
UPDATE study_area_grid
SET geoe3_by_population = geoe3_score * population
WHERE area_name = 'Study Area 1';
```

### Analysis: Subnational Aggregation

```sql
-- Aggregate scores by subnational unit
SELECT
    subnational_unit,
    AVG(geoe3_score) as avg_score,
    SUM(geoe3_by_population) / SUM(population) as pop_weighted_avg,
    MIN(geoe3_score) as min_score,
    MAX(geoe3_score) as max_score,
    COUNT(*) as cell_count
FROM study_area_grid
WHERE area_name = 'Study Area 1'
GROUP BY subnational_unit;
```

---

## Migration Benefits

Converting from raster-based to vector-based processing provides:

1. **Performance**: SQL operations on indexed vector tables are significantly faster than pixel-by-pixel raster sampling
2. **Simplicity**: No intermediate raster files to manage
3. **Accuracy**: Values stored directly in grid cells without resampling artifacts
4. **Storage**: Reduced disk usage (no duplicate raster outputs)
5. **Queryability**: Results immediately available for SQL analysis and reporting

---

## Implementation Priority

### Phase 1: Aggregation Workflows (Highest Impact)

- Factor aggregation (16 workflows)
- Dimension aggregation (3 workflows)
- Analysis aggregation (geoe3_score, geoe3_by_population)

### Phase 2: Vector-Based Indicators

- Index score workflows (uniform values)
- Multi-buffer point workflows (spatial joins)
- Single-buffer point workflows
- Point/polyline/polygon per cell workflows

### Phase 3: Hybrid Workflows

- Workflows requiring both raster sampling AND vector output
- Environmental hazards (sample raster → write to grid)
- Population (sample raster → write to grid)

---

_Document generated: 2026-03-30_

_Made with 💗 by [Kartoza](https://kartoza.com) | [Donate](https://github.com/sponsors/worldbank/GEOE3) | [GitHub](https://github.com/worldbank/GEOE3)_
