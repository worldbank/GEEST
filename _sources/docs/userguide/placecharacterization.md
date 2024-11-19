### Place Characterization

#### Active Transport

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/AT.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile for crosswalks, polyline shapefiles for cycle paths and for footpaths and polygon shapefile for block lengths.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	Each output factor will be stored in the project folder specified in the “Setup” tab, in the “AT” folder under the “Place Characterization” folder and have the following names AT_street_crossings.tif, AT_cycle_paths.tif, AT_footway.tif and AT_blocks.tif. The user can rename the output file to preferred filename.

5.	Click the “Aggregate” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/Activetransport.tif). The user can rename the output file to preferred filename.


#### Safety

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/SAF.jpg" alt="picture">
</p>

1.	Navigate to and select
   - **streetlight locations** (point shapefile)
   - or, if unavailable, **VIIRS Nighttime Lights dataset (.tif)** may be used as proxy data for streetlight locations
   - alternatively, **Perceived Safety data (polygon shapefile)** can be used if other data is unavailable; select the field containing the numeric value representing data on women's perceived safety at the municipal, district, state, or any other required level. The tool would then standardize these scores, percentages, or statistics on a scale from 0 to 5, where 5 indicates the lowest level of violence or the highest level of perceived safety. Example:

     ```
     Score 5 (Safest): 0 to 1 homicide per 100,000 people
     Score 4: 1.1 to 3 homicides per 100,000 people
     Score 3: 3.1 to 6 homicides per 100,000 people
     Score 2: 6.1 to 10 homicides per 100,000 people
     Score 1: 10.1 to 15 homicides per 100,000 people
     Score 0 (Least Safe): More than 15 homicides per 100,000 people
     ```


2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder set in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/PlaceCharacterization/SAF.tif). The user can rename the output file to preferred filename.


#### Digital Inclusion

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/DIG.jpg" alt="picture">
</p>

1.	Navigate to and select
    - the polygon input shapefile containing a field indicating the percentage of houses with internet access with disaggregated scores at, for example, the municipal or district level; select the field containing the          numeric value representing data on houses with internet access.
    - or a score at the country level as “Internet Access Value”

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/DIG.tif). The user can rename the output file to preferred filename.


#### Environmental Hazards

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/ENV.jpg" alt="picture">
</p>

1. Navigate to and select raster hazard event.
   - **Forest Fire**: Active Fires Density
   - **Flood**: Flood Hazard
   - **Landslide**: Landslide Susceptibility
   - **Tropical Cyclone**: Frequency of Tropical Cyclones
   - **Drought**: Global Drought Hazard based on the Standardized Precipitation Evapotranspiration Index (SPEI)

   Users should be able to select between 1 to 5 of these hazards that are most relevant to their specific context. For each selected hazard, the tool will generate raster cells of 100m x 100m and assign a score ranging from 0 to 5, standardized according to the hazard's scale. A score of 5 represents no hazard, while a score of 0 indicates areas at the highest risk. The final score will be the average of the scores from the selected hazards.

2. Click the “Execute” button to run the algorithm.

3. Status text next to the “Execute” button will appear and let you know once processing is complete.

4. Each output factor will be stored in the project folder specified in the “Setup” tab, in the “ENV” folder under the “Place Characterization” folder and have the following names Hazard_Landslide.tif, Hazard_Fires.tif, Hazard_Floods_100_yrp.tif, Hazard_Tropical_Cyclone.tif, and Hazard_Drought.tif. The user can rename the output file to preferred filename.

5. Click the “Aggregate” button to run the algorithm.

6. Status text next to the “Execute” button will appear and let you know once processing is complete.

7. The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/ENV.tif). The user can rename the output file to preferred filename.


#### Education

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/EDU.jpg" alt="picture">
</p>

1. Navigate to and select

   - the polygon input shapefile containing a field indicating the percentage of women who have achieved a post-secondary education with disaggregated scores at, for example, the municipal or district level; select the field containing the numeric value representing the above percentage.
   - or a score at the country level as “percentage of the labor force comprising women with university degrees in specified field” in Education Level Value.

2. Click the “Execute” button to run the algorithm.

3. Status text next to the “Execute” button will appear and let you know once processing is complete.

4. The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/EDU.tif). The user can rename the output file to preferred filename.


#### Fragility, conflict, and violence (FCV)

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/FCV.jpg" alt="picture">
</p>

1.	Navigate to and select the csv data for Fragility, conflict and violence (FCV-ACLED data).

2.	The default radius of 5km circular buffer can be changed from “Impact Radius in Meters (Optional)” if the impact radius of an event is known.

3.	Click the “Execute” button to run the algorithm.

4.	Status text next to the “Execute” button will appear and let you know once processing is complete.

5.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/FCV.tif). The user can rename the output file to preferred filename.


#### Water Sanitation

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/WAS.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile for water points, catch basins, water valves and fire hydrants.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/WAS.tif). The user can rename the output file to preferred filename.


(pd-aggregation-tab)=
#### Aggregate

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/AGGPD.jpg" alt="picture">
</p>

1.	Load the raster outputs generated in each of the previous factor tabs for the Place Characterization Dimension.
If a factor was executed in the same work session, the file path will automatically be populated after execution.

2.	If factors are missing, adjust the weighting percentage accordingly and ensure it totals to 100%.
If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension. The Auto button will automatically adjust the weights to ensure they sum to 100.

3.	Enter alternate aggregated raster output file name if desired.

4.	Enter an alternate aggregated raster output file name if desired. The standard output file name is Place_score.tif.

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The aggregated layer will be loaded to the QGIS and appear in the table of contents.

8.	The aggregated output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/Place_score.tif). The user can rename the output file to preferred filename.
