# Gender Enabling Environments Spatial Tool (GEEST) User Manual

This tool employs a multicriteria evaluation (MCE) framework to spatially describe womens' access to formal employment and business opportunities in the renewable energy sector in Small Island Developing States (SIDS). The MCE framework allows for the incorporation and assessment of dimensions, factors, and indicators to identify where the enabling environments (or lack thereof) are located for women to secure employment opportunities in SIDS.

- The spatial GDBs for all SIDS can be accessed [here](https://datacatalog.worldbank.org/search/collections/genderspatial).
- The methodology report can be accessed [here](https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099121123091527675/p1792120dc820d04409928040a279022b42).

## User Manual

[**Gender Enabling Environments Spatial Tool (GEEST) User Manual**](#gender-enabling-environments-spatial-tool-geest-user-manual)
1. [Install QGIS](#install-qgis)
2. [Install Open Route Service (ORS) plugin](#install-open-route-service-ors-plugin)
3. [Installing Plugin on local device](#installing-plugin-on-local-device)
4. [Using the Plugin](#using-the-plugin)
  - 4.1. [SETUP TAB](#setup-tab)
  - 4.2. [CONTEXTUAL TAB](#contextual-tab)
    - 4.2.1. [Workplace Discrimination](#workplace-discrimination)
    - 4.2.2. [Regulatory Frameworks](#regulatory-frameworks)
    - 4.2.3. [Financial Inclusion](#financial-inclusion)
    - 4.2.4. [Aggregate](#aggregate)
  - 4.3. [ACCESSIBILITY TAB](#accessibility-tab)
    - 4.3.1. [Women's Travel Patterns](#women-s-travel-patterns)
    - 4.3.2. [Access to Public Transport](#access-to-public-transport)
    - 4.3.3. [Access to Education and Training Facilities](#access-to-education-and-training-facilities)
    - 4.3.4. [Access to Health Facilities](#access-to-health-facilities)
    - 4.3.5. [Access to Financial Facilities](#access-to-financial-facilities)
    - 4.3.6. [Aggregate](#ad-aggregation-tab)
  - 4.4. [PLACE CHARACTERIZATION TAB](#place-characterization-tab)
    - 4.4.1. [Active Transport](#active-transport)
    - 4.4.2. [Safety](#safety)
    - 4.4.3. [Digital Inclusion](#digital-inclusion)
    - 4.4.4. [Environmental Hazards](#environmental-hazards)
    - 4.4.5. [Education](#education)
    - 4.4.6. [Fragility, conflict, and violence (FCV)](#fragility-conflict-and-violence-fcv)
    - 4.4.7. [Water Sanitation](#water-sanitation)
    - 4.4.8. [Aggregate](#pd-aggregation-tab)
  - 4.5. [DIMENSION AGGREGATION TAB](#dimension-aggregation-tab)
  - 4.6. [ABOUT TAB](#about-tab)
  - 4.7. [INSIGHTS TAB](#insights-tab)
    - 4.7.1. [Enablement](#enablement)
    - 4.7.2. [RE Zone Raster Locations](#re-zone-raster-locations)
    - 4.7.3. [RE Point Locations](#re-point-locations)
5. [Troubleshooting](#troubleshooting)
  - 5.1. [ACCESSIBILTY TABS PERMISSIONS ERROR](#accessibilty-permissions-error)
  - 5.2. [QGIS PLUGIN/INTERFACE WIDGETS AND TEXT ARE DISTORTED AND SCALED INCORRECTLY](#distorted)
  - 5.3. [RASTER OUTPUTS NOT BEING LOADED AND DISPLAYING CORRECTLY](#raster-outputs)
  - 5.4. [ERROR: OUTPUT DIRECTORY NOT SET](#output-directory)
  - 5.5. [ERROR: COUNTRY BOUNDARY POLYGON NOT SET](#country-boundary)
  - 5.6. [ERROR: CO-ORDINATE REFERENCE SYSTEM (CRS) NOT SET](#crs)
  - 5.7. [ALTERNATIVE WAY TO REFRESH THE PLUGIN IF IT FREEZES OR DOES NOT RUN AS EXPECTED](#alternative)
- [List of CRSs for SIDS](#list-of-crss-for-sids)
- [License](#license)

## 1 Install QGIS

1. 1.	The link below will take you to the QGIS website where you will be able to download the QGIS installation file. Note that it is possible to use older versions of QGIS, e.g. Version 3.32 - Lima. 

QGIS website: [https://www.qgis.org/en/site/](https://www.qgis.org/en/site/)

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/installQGIS.jpg" alt="Install QGIS">
</p>


2. Once the installation file is downloaded run the installation file.

3. A pop-up window as seen in the image below should show up. Follow the prompts and leave all settings on default.

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/qgis-setup.jpg" alt="QGIS Setup">
</p>


## 2 Install Open Route Service (ORS) plugin

1. Open QGIS, navigate to the "Plugins" tab and select the "Manage and Install Plugins…" option from the drop-down menu.

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/installORS.jpg" alt="install ORS">
</p>

2. The "Plugins" pop-up window should appear as seen in the image below.

3. In the search bar type "ORS", select the "ORS Tool" from the list of plugins, and select the install button to install the plugin.

![image](https://github.com/worldbank/GEEST/assets/120469484/6274c002-9b56-4374-8fd4-9278d2246afb)

4. You will now have to set up an account on the Open Route Service website which can be accessed by clicking the link below.

ORS website: [https://openrouteservice.org/](https://openrouteservice.org/)

ORS Sign up: [https://openrouteservice.org/dev/#/signup](https://openrouteservice.org/dev/#/signup)

![image](https://github.com/worldbank/GEEST/assets/120469484/79728902-e5ba-49c1-a262-32cd9df628a6)

5. Fill in all the necessary fields to sign up and then log into your account.

6. Request a standard token and provide a name for the Token.

![image](https://github.com/worldbank/GEEST/assets/120469484/72eb8f24-84b5-42e9-8da7-e19bf96d410a)

7. Once the token has been created, navigate to the Dashboard tab and click on the API key as seen in the image below. The API key should now be copied to the clipboard.

![image](https://github.com/worldbank/GEEST/assets/120469484/26564e04-4520-4022-9930-4b791df8e63f)

8. In the QGIS window navigate the ORS tool and select "Provider Settings".

![image](https://github.com/worldbank/GEEST/assets/120469484/45a45354-8478-45df-b212-c477a99b2c9a)

9. The provider settings pop-up window should now appear as seen in the image below.

10. Past the API key that has been copied to the clipboard into the API Key field and press "OK".

![image](https://github.com/worldbank/GEEST/assets/120469484/b255a792-4d46-42ef-a0ff-79edb1e2fd19)

**N.B.** Additional credits can be requested on the ORS site by applying for the collaborative plan as described [here](https://openrouteservice.org/plans/). You will have to provide a brief motivation, however, if your application is in a humanitarian, academic, governmental, or not-for-profit organization, you should be eligible for the collaborative plan.

This email address can also be used for further assistance:

support@openrouteservice.heigit.org

## 3 Installing Plugin on local device

1. Click on the green "Code" button and select the "Download ZIP" option.

![image](https://github.com/worldbank/GEEST/assets/120469484/af517d0b-8b32-43b6-a664-0bb250a1d620)

2. Once the download has been completed extract the contents of the ZIP file.

3. Navigate to your extracted ZIP folder and copy the _requirements.txt_ file.

![image](https://github.com/worldbank/GEEST/assets/120469484/6adea1a2-e63c-4067-9052-346811697828)

4. Navigate to the QGIS program folder and paste the _requirements.txt_ file into it. The file path would be similar to this: _C:\Program Files\QGIS 3.32.0_ as seen in the image under **step 5**.

5. Run the _OSGeo4W_ batch file.

![image](https://github.com/worldbank/GEEST/assets/120469484/9a8376bb-dc50-41fa-a3fd-f3e0757a3850)

6. A command line pop-up window will appear as seen in the image below.

7. Type the following into it and press Enter.
```pip install -r requirements.txt```

![image](https://github.com/worldbank/GEEST/assets/120469484/ed373467-0f80-4b75-8931-9c9e2d03d013)

8. All the Python libraries that the Plugin is dependent on will now be installed. This can take a few minutes to install.

9. Once the installations are complete you can close the command line pop-up window.

10. Open QGIS, navigate to the "Plugins" tab and select the "Manage and Install Plugins…" option from the drop-down menu.

![image](https://github.com/worldbank/GEEST/assets/120469484/39e233a5-15de-4471-9560-028cd8cde839)

11. In the plugin pop-up window navigate to the "Install from ZIP" tab.

![image](https://github.com/worldbank/GEEST/assets/120469484/9ed559bc-5672-4631-a33d-714710440819)

12. From the "Install from ZIP" tab navigate back to your extracted ZIP folder and select the "gender\_indicator\_tool" compressed (zipped) folder as seen in the image below.

![image](https://github.com/worldbank/GEEST/assets/120469484/f2e81343-1bb4-4dc1-b593-38c26726f767)

13. Once the ZIP file has been selected click on "Install Plugin".

14. Once the plugin has been installed navigate to the "All" tab.

15. In the search bar type "GEEST" and click the check box next to the "Gender Enabling Environments Spatial Tool (GEEST)" to install the plugin.

![image](https://github.com/worldbank/GEEST/assets/120469484/aac4db6e-3585-40dc-9e73-d0eb3a8bc247)

16. The plugin is now installed and you should now be able to access it in your toolbar or under the Plugin's tab as seen in the image below.

![image](https://github.com/worldbank/GEEST/assets/120469484/eceaf443-ff8b-4be0-9282-a1236a03bb86)

## 4 Using the Plugin
Examples of files that can be used as input at a particular step as per the Pilot Country Database will be indicated at the end of the step.

### 4.1 SETUP TAB

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/setupTab.jpg" alt="Setup Tab">
</p>

1.	Create a project folder that will be used to store all tool outputs.

2.	Set the output directory to the project folder created in the previous step.

3.	Set the country boundary layer by navigating to and selecting the **Admin0** country boundary polygon shapefile for the country you want to analyze.

**Input File: AdminBoundaries/Admin0.shp**

4.	Select the appropriate coordinate reference system (CRS) from the QGIS CRS database. Appendix A lists all the CRS to be used for the SIDS countries.

5.	Copy and paste the EPSG code for your specific country and paste it in the Filter bar as seen in the image below.

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/CRS.jpg" alt="CRS">
</p>

6.	Select the CRS from the list and click “OK”.

7.	Set your preferred output raster output resolution in meters squared.


### 4.2 CONTEXTUAL TAB

#### 4.2.1 Workplace Discrimination

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/WD.jpg" alt="picture">
</p>

1.	Navigate to the WBL (Women, Business and the Law) report and input the WBL index score representing the value from 0 to 100. This value represents data at the national level and must be standardized on a scale ranging from 0 to 5. This indicator is composed by the Workplace Index score of the WBL. The data is already formatted on a scale from 1 to 100. 

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder. (Project_Folder/Contextual/WD.tif). The user can rename the output file to preferred filename.


#### 4.2.2 Regulatory Frameworks

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/RF.jpg" alt="picture">
</p>

1.	Navigate to the WBL (Women, Business and the Law) report and input the WBL Pay and Parenthood index scores, values ranging from 0 to 100. This value represents data at the national level and must be standardized on a scale ranging from 0 to 5. This indicator is composed by aggregating the Parenthood and Pay Index scores of the WBL. The data is already formatted on a scale from 1 to 100.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder (Project_Folder/Contextual/RF.tif). The user can rename the output file to preferred filename.

#### 4.2.3 Financial Inclusion

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/FI.jpg" alt="picture">
</p>

1.	Navigate to the WBL (Women, Business and the Law) report and input the WBL Entrepreneurship index score, value ranging from 0 to 100. This value represents data at the national level and must be standardized on a scale ranging from 0 to 5. The data is already formatted on a scale from 1 to 100. It comes from the Entrepreneurship rating of the WBL Index.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder (Project_Folder/Contextual/FIN.tif). The user can rename the output file to preferred filename.

#### 4.2.4 Aggregate

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/WDAG.jpg" alt="picture">
</p>

1.	Load the raster outputs generated in each of the previous factor tabs for the Contextual Dimension.
If a factor was executed in the same work session, its file path will automatically be populated after execution.

2.	If factors are missing adjust the weighting percentage accordingly and ensure it totals to 100%.

3.	If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weights.

4.	Enter an alternate aggregated raster output file name if desired. The standard output file name is Contextual_score.tif

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The aggregated layer will be loaded to the QGIS and appear in the table of contents.

8.	The aggregated output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder. (Project_Folder/Contextual/ Contextual_score.tif). The user can rename the output file to preferred filename.


### 4.3 ACCESSIBILITY TAB

#### 4.3.1 Women's Travel Patterns

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/WTP.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile input of facilities related to women’s role as caregivers. This includes green spaces, grocery stores, pharmacies, kindergartens and schools.

2.	Select the mode of travel (Walking OR Driving).

3.	Select the method of measurement (Distance OR Time).

4.	Specify travel distance or time increments in meters or time respectively using comma delimitation.

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	Each output factor will be stored in the project folder specified in the “Setup” tab, in the “WTP” folder under the “Accessibility” folder and have the following names WTP_Walking_Green_spaces.tif, WTP_Walking_Groceries.tif, WTP_Walking_Pharmacies.tif and WTP_Walking_Kindergartens_and_Schools.tif. The user can rename the output file to preferred filename.

8.	Click the “Aggregate” button to run the algorithm.

9.	Status text next to the “Execute” button will appear and let you know once processing is complete.

10.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Accessibility” folder. (Project_Folder/Accessibility/WTP.tif). The user can rename the output file to preferred filename.


#### 4.3.2 Access to Public Transport

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/APT.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile input for public transport stops, including both land and maritime stops.

2.	Select the mode of travel (Walking OR Driving).

3.	Select the method of measurement (Distance OR Time).

4.	Specify travel distance or time increments in meters or time respectively using comma delimitation.

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The output raster file will be stored in the project folder set in the “Setup” tab, under the “Accessibility” folder (Project_Folder/Accessibility/PBT.tif). The user can rename the output file to preferred filename.


#### 4.3.3 Access to Education and Training Facilities

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/ETF.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile input of education and training facilities (colleges, training facilities and universities).

2.	Select the mode of travel (Walking OR Driving).

3.	Select the method of measurement (Distance OR Time).

4.	Specify travel distance or time increments in meters or time respectively using comma delimitation.

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Accessibility” folder (Project_Folder/Accessibility/ETF.tif). The user can rename the output file to preferred filename.


#### 4.3.4 Access to Health Facilities

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/HEF.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile input of health facilities (hospitals and clinics as the points of interest).

2.	Select the mode of travel (Walking OR Driving).

3.	Select the method of measurement (Distance OR Time).

4.	Specify travel distance or time increments in meters or time respectively using comma delamination.

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Accessibility” folder (Project_Folder/Accessibility/HEF.tif). The user can rename the output file to preferred filename.


#### 4.3.5 Access to Financial Facilities

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/FIF.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile input of financial facilities (location of banks and other financial facilities except for ATMs).

2.	Select the mode of travel (Walking OR Driving).

3.	Select the method of measurement (Distance OR Time).

4.	Specify travel distance or time increments in meters or time respectively using comma delimitation.

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Accessibility” folder. (Project_Folder/Accessibility/FIF.tif). The user can rename the output file to preferred filename.


(ad-aggregation-tab)=
#### 4.3.6 Aggregate

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/AGGACC.jpg" alt="picture">
</p>

1.	Load the raster outputs generated in each of the previous factor tabs for the Accessibility Dimension.
*If a factor was executed in the same work session, the file path will automatically be populated after execution.*

2.	If factors are missing, adjust the weighting percentage accordingly and ensure it totals to 100%.
*If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension.*

3.	Enter alternate aggregated raster output file name if desired.

4.	Enter an alternate aggregated raster output file name if desired. The standard output file name is Accessibility_score.tif.

5.	Click the “Execute” button to run the algorithm.

6.	Status text next to the “Execute” button will appear and let you know once processing is complete.

7.	The aggregated layer will be loaded to the QGIS and appear in the table of contents.

8.	The aggregated output raster file will be stored in the project folder specified in the “Setup” tab, under the “Accessibility” folder (Project_Folder/Accessibility/Accessibility_score.tif). The user can rename the output file to preferred filename.


### 4.4 PLACE CHARACTERIZATION TAB

#### 4.4.1 Active Transport

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


#### 4.4.2 Safety

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


#### 4.4.3 Digital Inclusion

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/DIG.jpg" alt="picture">
</p>

1.	Navigate to and select
    - the polygon input shapefile containing a field indicating the percentage of houses with internet access with disaggregated scores at, for example, the municipal or district level; select the field containing the          numeric value representing data on houses with internet access.
    - or a score at the country level as “Internet Access Value”

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/DIG.tif). The user can rename the output file to preferred filename. 


#### 4.4.4 Environmental Hazards

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


#### 4.4.5 Education

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/EDU.jpg" alt="picture">
</p>

1. Navigate to and select

   - the polygon input shapefile containing a field indicating the percentage of women who have achieved a post-secondary education with disaggregated scores at, for example, the municipal or district level; select the field containing the numeric value representing the above percentage.
   - or a score at the country level as “percentage of the labor force comprising women with university degrees in specified field” in Education Level Value.

2. Click the “Execute” button to run the algorithm.

3. Status text next to the “Execute” button will appear and let you know once processing is complete.

4. The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/EDU.tif). The user can rename the output file to preferred filename.


#### 4.4.6 Fragility, conflict, and violence (FCV)

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/FCV.jpg" alt="picture">
</p>

1.	Navigate to and select the csv data for Fragility, conflict and violence (FCV-ACLED data).

2.	The default radius of 5km circular buffer can be changed from “Impact Radius in Meters (Optional)” if the impact radius of an event is known.

3.	Click the “Execute” button to run the algorithm.

4.	Status text next to the “Execute” button will appear and let you know once processing is complete.

5.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/FCV.tif). The user can rename the output file to preferred filename.


#### 4.4.7 Water Sanitation

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/WAS.jpg" alt="picture">
</p>

1.	Navigate to and select point shapefile for water points, catch basins, water valves and fire hydrants.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Place Characterization” folder (Project_Folder/Place Characterization/WAS.tif). The user can rename the output file to preferred filename.


(pd-aggregation-tab)=
#### 4.4.8 Aggregate

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


### 4.5 DIMENSION AGGREGATION TAB

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/AGGALL.jpg" alt="picture">
</p>

1.	Load each dimension’s aggregated raster outputs of previous domains (Contextual, Accessibility and Place Characterization).

If a dimension’s factor aggregation was executed in the same work session, its file path will automatically be populated after execution.

2.	If dimensions are missing, adjust the weighting percentage accordingly and ensure it totals up to 100%.
If a dimension is missing it needs to be given a weighting of 0%. All domains should have equal weighting within the aggregation tab.

3.	Enter aggregated dimensions raster output file name.

4.	Click the “Execute” button to run the algorithm.

5.	Status text next to the “Execute” button will appear and let you know once processing is complete.

6.	The aggregated dimensional layer will be loaded to the QGIS and appear in the table of contents.

7.	The aggregated output raster file will be stored in the project folder specified in the “Setup” tab, under the “Final_output” folder (*Project_Folder/Final_Output/WEE.tif). The user can rename the output file to preferred filename.


### 4.6 ABOUT TAB

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/abou.jpg" alt="picture">
</p>

Information on the tool, its framework, scoring system, and how results should or can be interpreted.

### 4.7 INSIGHTS TAB
#### 4.7.1 Enablement

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


#### 4.7.2 RE Zone Raster Locations

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


#### 4.7.3 RE Point Locations

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/REpoint.jpg" alt="picture">
</p>

1.	Navigate to and select the combined classification input file produced in step 2.3 of the “Enablement” tab (WEE_pop_score.tif). This file path will be automatically populated if step 2.3 of the “Enablement” tab was executed in the same work session.

2.	Navigate to and select the aggregated combined classification input file produced in step 3.3 of the “Enablement” tab (WEE_pop_adm_score.shp). This file path will be automatically populated if step 3.3 of the “Enablement” tab was executed in the same work session.

3.	Navigate to and select the RE point locations input shapefile of interest. (These could be existing RE job locations or other points of interest)

4.	Set radial buffer distance in meters.

5.	Click the “Execute” button to run the algorithm.

6.	The 2 output shapefiles will be stored in the project folder specified in the “Setup” tab, Locations/POI_WEE_score.shp & Project_Folder/Insights/6) RE Point Locations/POI_WEE_score.shp). The user can rename the output file to preferred filename.


## 5 Troubleshooting

### 5.1 ACCESSIBILTY TABS PERMISSIONS ERROR

![image](https://github.com/worldbank/GEEST/assets/120469484/63edfc18-8294-478c-bcc5-1a4f28c07711)

This error occurs when some of the shapefiles produced in the temp folder of the working directory are trying to be overwritten or deleted but can't because it's still being stored in QGIS's memory. This can occurs even when the layer is removed from the QGIS table of contents.

**This error may also occur when the tool runs correctly so first check if the desired output file was produced in the working directory.**

If the file is not produced you can try the following:
- Delete the *temp* folder in the working directory
- If you cannot delete the *temp* folder you will have to close QGIS and open it again, complete the setup tab, go back to the tab where the error occurred and re-run the tab again.

### 5.2 QGIS PLUGIN/INTERFACE WIDGETS AND TEXT ARE DISTORTED AND SCALED INCORRECTLY
![image](https://github.com/worldbank/GEEST/assets/120469484/e195416b-ee86-4998-9ca5-a4784f7c724e)

This is a problem linked to display settings caused by the connection of multiple monitors and/or varying display scales and resolutions, rather than a QGIS or plugin-related issue. This is backed by a Microsoft support post, linked [here](https://support.microsoft.com/en-gb/topic/windows-scaling-issues-for-high-dpi-devices-508483cd-7c59-0d08-12b0-960b99aa347d), highlighting the issues that may be experienced when using a high-DPI device, such as a 4k monitor. Additionally, in the scaling display setting, Microsoft indicates that entering a custom scaling size between 100% - 500% is not recommended as "...it can cause text and apps to become unreadable."

![image](https://github.com/worldbank/GEEST/assets/120469484/248fde5c-dd1a-41d0-94ad-2ace20a74f95)

Possible solutions to this are:
- Adjust the scale for all monitors to 100%.
- Ensure that the display resolution is the same for both monitors. i.e. If the smallest monitor is set to 1920 x 1080 set the 4k monitor to this display resolution as well.

### 5.3 RASTER OUTPUTS NOT BEING LOADED AND DISPLAYING CORRECTLY

![image](https://github.com/worldbank/GEEST/assets/120469484/10de6c72-f8f6-47b8-adb3-930f5c625f66)

Occasionally, some of the outputs automatically loaded to the QGIS table of contents do not display correctly. To correct this, try removing the layer that is displayed incorrectly and add it again to QGIS.

### 5.4 ERROR: OUTPUT DIRECTORY NOT SET

![image](https://github.com/worldbank/GEEST/assets/120469484/b2f2959e-85c4-4e89-8493-dac2b9a20f07)

If you see the following error message, please check if your output directory has been set in the "Setup" tab.

### 5.5 ERROR: COUNTRY BOUNDARY POLYGON NOT SET

![image](https://github.com/worldbank/GEEST/assets/120469484/75882e9d-a9af-43fc-9f68-0293c75b49b3)

If you see the following error message, please check if you're country boundary polygon layer has been set in the "Setup" tab.

### 5.6 ERROR: CO-ORDINATE REFERENCE SYSTEM (CRS) NOT SET

![image](https://github.com/worldbank/GEEST/assets/120469484/120c0cf9-e526-4d8b-adff-de3a9d2f7fb8)

If you see the following error message, please check if you're CRS has been set in the "Setup" tab.

### 5.7 ALTERNATIVE WAY TO REFRESH THE PLUGIN IF IT FREEZES OR DOES NOT RUN AS EXPECTED

1. Install the "Plugin Reloader" plugin.

   1.1 Navigate to and open “Manage and Install Plugins…” under the plugins tab in QGIS.

   1.2 In the search bar type “plugin reloader”.

   1.3 Select the “Plugin Reloader” plugin and click on the install button.


![image](https://github.com/worldbank/GEEST/assets/120469484/801db189-92ca-4755-a79f-8898b2e43a2f)

 1.4 Navigate to the "Plugin Reloader" configuration window under the Plugins tab.

*Plugins* → *Plugin Reloader* → *Configure*

 1.5 From the drop-down list select the "gender\_indicator\_tool" plugin and press "OK".

![image](https://github.com/worldbank/GEEST/assets/120469484/3dc21c04-2ebe-4b33-92bc-1020746ee9e3)

  1.6 If you encounter an unexpected error in the tool that has not been mentioned in any of the previous troubleshooting sections you can try runing the "plugin reload" tool

![image](https://github.com/worldbank/GEEST/assets/120469484/80e1ae57-8608-4392-8df2-46e5b5d4789e)

**OR**

**If the "Plugin Reloader" does not resolve the error close QGIS, restart it again, and re-run the process you were trying to execute.**

# List of CRSs for SIDS

| **Country** | **WGS84 / UTM CRS** | **EPSG** |
| --- | --- | --- |
| Antigua and Barbuda | WGS 84 / UTM zone 20N | 32620 |
| Belize | WGS 84 / UTM zone 16N | 32616 |
| Cabo Verde | WGS 84 / UTM zone 26N | 32626 |
| Comoros | WGS 84 / UTM zone 38S | 32738 |
| Dominica | WGS 84 / UTM zone 20N | 32620 |
| Dominican Republic | WGS 84 / UTM zone 19N | 32619 |
| Fiji | WGS 84 / UTM zone 60S | 32760 |
| Grenada | WGS 84 / UTM zone 20N | 32620 |
| Guinea-Bissau | WGS 84 / UTM zone 28N | 32628 |
| Guyana | WGS 84 / UTM zone 21N | 32621 |
| Haiti | WGS 84 / UTM zone 18N | 32618 |
| Jamaica | WGS 84 / UTM zone 17N | 32617 |
| Kiribati | WGS 84 / UTM zone 1N | 32601 |
| Maldives | WGS 84 / UTM zone 43N | 32643 |
| Marshall Islands | WGS 84 / UTM zone 58N | 32658 |
| Mauritius | WGS 84 / UTM zone 40S | 32740 |
| Micronesia (Federated States of) | WGS 84 / UTM zone 57N | 32657 |
| Nauru | WGS 84 / UTM zone 58N | 32658 |
| Niue | WGS 84 / UTM zone 1S | 32701 |
| Palau | WGS 84 / UTM zone 53N | 32653 |
| Papua New Guinea | WGS 84 / UTM zone 55S | 32755 |
| Samoa | WGS 84 / UTM zone 2S | 32702 |
| Sao Tomé and Principe | WGS 84 / UTM zone 32N | 32632 |
| Solomon Islands | WGS 84 / UTM zone 57S | 32757 |
| St. Lucia | WGS 84 / UTM zone 20N | 32620 |
| St. Vincent and the Grenadines | WGS 84 / UTM zone 20N | 32620 |
| Suriname | WGS 84 / UTM zone 21N | 32621 |
| Timor-Leste | WGS 84 / UTM zone 52S | 32752 |
| Tonga | WGS 84 / UTM zone 60S | 32760 |
| Tuvalu | WGS 84 / UTM zone 60S | 32760 |
| Vanuatu | WGS 84 / UTM zone 59S | 32759 |

# License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
