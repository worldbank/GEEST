### Insights

#### Enablement

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/ENA.jpg" alt="picture">
</p>

### Step 1: Classify into discrete classes

1.1 Navigate to and select the enablement score input raster file. This can be the final aggregate score (WEE.tif), a dimension aggregate score, or even a single factor output layer.

1.2 Click the “Classify” button under the “Enablement Score Input layer” field to run the algorithm.

1.3 The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Insights/1) Level of Enablement Classification” folder. (Project_Folder/Insights/1) Level of Enablement Classification/WEE_score.tif). The user can rename the output file to the preferred filename.

1.4 Navigate to and select the population input raster file.
   - E.g., Input File: Population/Female_population_35_39.tif (Any of the age ranges can be used as input).

1.5 Click the “Classify” button under the “Population Input layer” field to run the algorithm.

1.6 The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Insights/2) Relative Population Count Classification” folder. (Project_Folder/Insights/2) Relative Population Count Classification/Population.tif). The user can rename the output file to the preferred filename.

### Step 2: Combine score and population classifications

2.1 Navigate to and select the “Level of Enablement” output raster file produced in step 1.2 (WEE_score.tif). This file path will be automatically populated if step 1.2 was executed in the same work session.

2.2 Navigate to and select the “Relative Population Count” output raster file produced in step 1.5 (Population.tif). This file path will be automatically populated if step 1.5 was executed in the same work session.

2.3 Click the “Combine Classification” button to run the algorithm combining the “Level of Enablement” and “Relative Population Count” raster layers.

2.4 The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Insights/3) Combined Level of Enablement & Relative Population Count Classification” folder. (Project_Folder/Insights/3) Combined Level of Enablement & Relative Population Count Classification/WEE_pop_score.tif). The user can rename the output file to the preferred filename.

### Step 3: Aggregation

3.1 Navigate to and select the “Combine Classification” output raster file produced in step 2.3. This file path will be automatically populated if step 2.3 was executed in the same work session.

3.2 Navigate to and select the aggregation input shapefile. This can be any polygon layer representing boundaries of interest for aggregation (e.g., municipal boundary layer).
   - E.G., Input File: AdminBoundaries/Admin2.shp (Any admin level can be used as input)

3.3 Click the “Execute” button to run the algorithm.

3.4 The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Insights/4) Aggregation” folder. (Project_Folder/Insights/4) Aggregation/WEE_pop_adm_score.shp). The user can rename the output file to the preferred filename.


#### RE Zone Raster Locations

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/REzone.jpg" alt="picture">
</p>

1. Navigate to and select the combined classification input file produced in step 2.3 of the “Enablement” tab (WEE_pop_score.tif). This file path will be automatically populated if step 2.3 of the “Enablement” tab was executed in the same work session.

2. Navigate to and select the aggregated combined classification input file produced in step 3.3 of the “Enablement” tab (WEE_pop_adm_score.shp). This file path will be automatically populated if step 3.3 of the “Enablement” tab was executed in the same work session.

3. Navigate to and select the potential RE zones input raster file. (Zones in the region that have no RE potential need to be represented with “no data” or “inf” values in the raster file).
   - E.G. Input File: RE/WBG_REZoning_DOM_score_wind.tif
   - E.G. Input File: RE/WBG_REZoning_DOM_score_solar.tif

4. Click the “Execute” button to run the algorithm.

5. The 2 output files will be stored in the project folder specified in the “Setup” tab, under Raster Locations/AOI_WEE_score.tif & Project_Folder/Insights/5) RE Zone Raster Locations/AOI_WEE_score.shp). The user can rename the output file to the preferred filename.


#### RE Point Locations

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/REpoint.jpg" alt="picture">
</p>

1.	Navigate to and select the combined classification input file produced in step 2.3 of the “Enablement” tab (WEE_pop_score.tif). This file path will be automatically populated if step 2.3 of the “Enablement” tab was executed in the same work session.

2.	Navigate to and select the aggregated combined classification input file produced in step 3.3 of the “Enablement” tab (WEE_pop_adm_score.shp). This file path will be automatically populated if step 3.3 of the “Enablement” tab was executed in the same work session.

3.	Navigate to and select the RE point locations input shapefile of interest. (These could be existing RE job locations or other points of interest)

4.	Set radial buffer distance in meters.

5.	Click the “Execute” button to run the algorithm.

6.	The 2 output shapefiles will be stored in the project folder specified in the “Setup” tab, Locations/POI_WEE_score.shp & Project_Folder/Insights/6) RE Point Locations/POI_WEE_score.shp). The user can rename the output file to preferred filename.