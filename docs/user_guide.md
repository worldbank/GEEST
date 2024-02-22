# Gender Enabling Environments Spatial Tool (GEEST) User Manual
This tool employs a multicriteria evaluation (MCE) framework to spatially describe womens' access to formal employment and business opportunities in the renewable energy sector in Small Island Developing States (SIDS). The MCE framework allows for the incorporation and assessment of dimensions, factors, and indicators to identify where the enabling environments (or lack thereof) are located for women to secure employment opportunities in SIDS.

- The spatial GDBs for all SIDS can be accessed [here](https://datacatalog.worldbank.org/search/collections/genderspatial).
- The methodology report can be accessed [here](https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099121123091527675/p1792120dc820d04409928040a279022b42).

## User Manual

[**Gender Enabling Environments Spatial Tool (GEEST) User Manual**](#gender-enabling-environments-spatial-tool-geest-user-manual)
- 1. [Install QGIS](#install-qgis)
- 2. [Install Open Route Service (ORS) plugin](#install-open-route-service-ors-plugin)
- 3. [Installing Plugin on local device](#installing-plugin-on-local-device)
- 4. [Using the Plugin](#using-the-plugin)
  - 4.1. [SETUP TAB](#setup-tab)
  - 4.2. [INDIVIDUAL TAB](#individual-tab)
    - 4.2.1. [Education](#education)
    - 4.2.2. [Care Responsibilities](#care-responsibilities)
    - 4.2.3. [Domestic Violence](#domestic-violence)
    - 4.2.4. [Aggregate](#id-aggregation-tab)
  - 4.3. [CONTEXTUAL TAB](#contextual-tab)
    - 4.3.1. [Policy and Legal Protection](#policy-and-legal-protection)
    - 4.3.2. [Access to Finance](#access-to-finance)
    - 4.3.3. [Aggregate](#cd-aggregation-tab)
  - 4.4. [ACCESSIBILITY TAB](#accessibility-tab)
    - 4.4.1. [Women's Travel Patterns](#women-s-travel-patterns)
    - 4.4.2. [Access to Public Transport](#access-to-public-transport)
    - 4.4.3. [Access to Education and Training Facilities](#access-to-education-and-training-facilities)
    - 4.4.4. [Access to Jobs in the RE sector](#access-to-jobs-in-the-re-sector)
    - 4.4.5. [Access to Health Facilities](#access-to-health-facilities)
    - 4.4.6. [Access to Financial Facilities](#access-to-financial-facilities)
    - 4.4.7. [Aggregate](#ad-aggregation-tab)
  - 4.5. [PLACE CHARACTERIZATION TAB](#place-characterization-tab)
    - 4.5.1. [Active Transport](#active-transport)
    - 4.5.2. [Availability of Public Transport](#availability-of-public-transport)
    - 4.5.3. [Safe Urban Design](#safe-urban-design)
  - 4.5.4. [Security](#security)
    - 4.5.5. [Income Level](#income-level)
    - 4.5.6. [Electricity Access](#electricity-access)
    - 4.5.7. [Level of Urbanization](#level-of-urbanization)
    - 4.5.8. [Size of Housing](#size-of-housing)
    - 4.5.9. [Digital Inclusion](#digital-inclusion)
    - 4.5.10. [Natural Environment and Climatic Factors](#natural-environment-and-climatic-factors)
    - 4.5.11. [Aggregate](#pd-aggregation-tab)
  - 4.6. [DIMENSION AGGREGATION TAB](#dimension-aggregation-tab)
  - 4.7. [ABOUT TAB](#about-tab)
  - 4.8. [INSIGHTS TAB](#insights-tab)
    - 4.8.1. [Enablement](#enablement)
    - 4.8.2. [RE Zone Raster Locations](#re-zone-raster-locations)
    - 4.8.3. [RE Point Locations](#re-point-locations)
- 5. [Troubleshooting](#troubleshooting)
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

1. The link below will take you to the QGIS website where you will be able to download the QGIS installation file. Note that it is possible to use older versions of QGIS, e.g. Version 3.28.

QGIS website: [https://www.qgis.org/en/site/](https://www.qgis.org/en/site/)

![image](https://github.com/worldbank/GEEST/assets/120469484/e0448baf-9a0b-475e-9bc2-c883868318d2)

2. Once the installation file is downloaded run the installation file.

3. A pop-up window as seen in the image below should show up. Follow the prompts and leave all settings on default.

![image](https://github.com/worldbank/GEEST/assets/120469484/52464df3-b408-4d05-af88-c6ef4a55c599)


## 2 Install Open Route Service (ORS) plugin

1. Open QGIS, navigate to the "Plugins" tab and select the "Manage and Install Plugins…" option from the drop-down menu.

![image](https://github.com/worldbank/GEEST/assets/120469484/1a2b1b0c-2a6f-49a6-b3d3-6e48386b7b22)

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
Examples of files that can be used as input at a particular step as per the Pilot Country Database will be indicated at the end of the step. The following format will be used:

**Input File:** *Folder/file_name* --> *AccessFinance/Access_to_finance.shp*

### 4.1 SETUP TAB

![image](https://github.com/worldbank/GEEST/assets/120469484/6ff06edc-198a-4807-a59f-038f1b401d43)

1. Create a project folder that will be used to store all tool outputs.

3. Set the output directory to the project folder created in the previous step.

5. Set the country boundary layer by navigating to and selecting the **Admin 0** country boundary polygon shapefile for the country you want to analyze.

   **Input File:** *AdminBoundaries/Admin0.shp*

7. Select the appropriate coordinate reference system (CRS) from the QGIS CRS database.

**Appendix A**  _lists all the CRS to be used for the SIDS countries._

5. Copy and paste the EPSG code for your specific country and paste it in the Filter bar as seen in the image below.

![image](https://github.com/worldbank/GEEST/assets/120469484/5e9d2066-c641-4129-8e4c-a876b19da8a2)

6. Select the CRS from the list and click "OK".

7. Set your preferred output raster output resolution in meters squared.

### 4.2 INDIVIDUAL TAB

#### 4.2.1 Education

![image](https://github.com/worldbank/GEEST/assets/120469484/783752ba-77a9-4c37-95ad-d5ffb34b9bf7)

1. Navigate to and select the polygon input shapefile containing a field reporting the percentage of women who have achieved a post-secondary education.

   **Input File:** *Education/Level_of_education*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of women who have achieved a post-secondary education.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/EDU_Raster_output.tif*)

#### 4.2.2 Care Responsibilities

![image](https://github.com/worldbank/GEEST/assets/120469484/a22a693d-7979-442a-9e6d-b485417d8fad)

1. Navigate to and select the polygon input shapefile containing a field reporting the percentage of time women spend on care responsibilities or household activities.

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of time women spend on care responsibilities or household activities.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/CRE_Raster_output.tif*)

#### 4.2.3 Domestic Violence

![image](https://github.com/worldbank/GEEST/assets/120469484/b2b9e9e9-cb5c-4251-b495-2ee10ea8f404)

1. Navigate to and select the polygon input shapefile containing a field reporting the percentage of women who have suffered domestic violence.

   **Input File:** *DomesticViolence/Prevalence_of_domestic_violence.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of women who have suffered domestic violence.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/DOV_Raster_output.tif*)

(id-aggregation-tab)=
#### 4.2.4 Aggregate

![image](https://github.com/worldbank/GEEST/assets/120469484/e9e14c68-2111-4377-9ea2-bc73c6241fc1)

1. Load the raster outputs generated in each of the previous factor tabs for the Individual Dimension.

_If a factor was executed in the same work session, its file path will automatically be populated after execution._

2. If factors are missing adjust the weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter an alternate aggregated raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/AGG_Raster_output.tif*)

### 4.3 CONTEXTUAL TAB

#### 4.3.1 Policy and Legal Protection

![image](https://github.com/worldbank/GEEST/assets/120469484/ab6797a8-b09e-4a6e-92c8-6e2b664d17c0)

1. Navigate to and select polygon input shapefile containing a field reporting a percentage representing the level of protective policies afforded to women.

   **Input File:** *PolicyLegal/Regulatory_Framework_Law_agg.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing a percentage representing the level of protective policies afforded to women.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Contextual/PLP_Raster_output.tif*)

#### 4.3.2 Access to Finance

![image](https://github.com/worldbank/GEEST/assets/120469484/2e4050cd-d458-4b19-9876-b434431b68c7)

1. Navigate to and select polygon input shapefile containing a field reporting the percentage of women who have a bank account.

   **Input File:** *AccessFinance/Access_to_finance.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of women who have a bank account.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Contextual/FIN_Raster_output.tif*)

(cd-aggregation-tab)=
#### 4.3.3 Aggregate

![image](https://github.com/worldbank/GEEST/assets/120469484/bcf2260d-5db0-4be5-a583-ac9d0537e35c)

1. Load the raster outputs generated in each of the previous factor tabs for the Contextual Dimension.

_If a factor was executed in the same work session, its file path will automatically be populated after execution._

2. If factors are missing adjust the weighting percentage accordingly and ensure it totals to 100%.

If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension.

3. Enter an alternate aggregated raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Contextual/AGG_Raster_output.tif*)

### 4.4 ACCESSIBILITY TAB

#### 4.4.1 Women's Travel Patterns

![image](https://github.com/worldbank/GEEST/assets/120469484/6541477e-2ff8-4878-8962-3abb48e4ce43)

1. Navigate to and select point shapefile input of facilities related to women's role as caregivers. This includes:
  - Childcare facilities
  - Primary and secondary schools
  - Markets
  - Grocery stores
  - Recreational areas

      **Input File:** *Amenities/Daycares_elementary_schools.shp*

      **Input File:** *Amenities/Grocery_stores.shp*

2. Select the mode of travel (Walking OR Driving).

3. Select the method of measurement (Distance OR Time).

4. Specify travel distance or time increments in meters or time respectively using comma delimitation.

5. Edit the facility raster output file name for each unique type of facility.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be stored in the project folder specified in the "Setup" tab, in the "WTP" folder under the "Accessibility" folder. (*Project_Folder/Accessibility/WTP/Facility_Raster_output.tif*)

**Steps 1 – 8 will have to be repeated for all facility types**.

9. Once all facilities have completed the processing, move on to the next step and enter the aggregated raster output file name.

10. Click the "Aggregate" button to run the algorithm.

11. Status text next to the "Execute" button will appear and let you know once processing is complete.

12. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Accessibility/WTP_Raster_output.tif*)

#### 4.4.2 Access to Public Transport

![image](https://github.com/worldbank/GEEST/assets/120469484/ade68b40-f9f4-477c-a631-3ed137b71e27)

1. Navigate to and select point shapefile input for public transport stops.

   **Input File:** *PubTransportStops/Public_transportation_stops.shp*

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delimitation.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Accessibility" folder (*Project_Folder/Accessibility/PBT_Raster_output.tif*).

#### 4.4.3 Access to Education and Training Facilities

![image](https://github.com/worldbank/GEEST/assets/120469484/0899eb4e-9547-4d7a-9a30-95082ebb71dc)

1. Navigate to and select point shapefile input of education and training facilities.

   **Input File:** *EducationFacilities/Techncal_schools.shp*

   **Input File:** *EducationFacilities/Universities.shp*

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delimitation.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (*Project_Folder/Accessibility/ETF_Raster_output.tif*).

#### 4.4.4 Access to Jobs in the RE sector

![image](https://github.com/worldbank/GEEST/assets/120469484/572b704c-830a-40c4-96f0-6dceb7e6100d)

1. Navigate to and select point shapefile input of jobs or job facilities.

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delamination.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (*Project_Folder/Accessibility/JOB_Raster_output.tif*).

#### 4.4.5 Access to Health Facilities

![image](https://github.com/worldbank/GEEST/assets/120469484/c38e5cb6-2264-4bd3-8e53-56c19d8213e4)

1. Navigate to and select point shapefile input of health care facilities.

   **Input File:** *HealthFacilities/Hospitals.shp*

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delimitation.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder. (*Project_Folder/Accessibility/HEA_Raster_output.tif*)

#### 4.4.6 Access to Financial Facilities

![image](https://github.com/worldbank/GEEST/assets/120469484/bd2bace8-e569-4b23-a4c0-a6024fe2adf6)

1. Navigate to and select point shapefile input of financial facilities.

   **Input File:** *FinancialFacilities/Financial_Facilities.shp*

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delamination.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (*Project_Folder/Accessibility/FIF_Raster_output.tif*).

(ad-aggregation-tab)=
#### 4.4.7 Aggregate

![image](https://github.com/worldbank/GEEST/assets/120469484/ba3c884c-5940-4255-9ca5-9e202ae106b8)

1. Load the raster outputs generated in each of the previous factor tabs for the Accessibility Dimension.

_If a factor was executed in the same work session, the file path will automatically be populated after execution._

2. If factors are missing, adjust the weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter alternate aggregated raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Accessibility/AGG_Raster_output.tif*).

### 4.5 PLACE CHARACTERIZATION TAB

#### 4.5.1 Active Transport

![image](https://github.com/worldbank/GEEST/assets/120469484/bf89b9ad-7ecc-460c-a7d9-38f1a894176a)

1. Navigate to and select polyline road network shapefile.

   **Input File:** *Roads/Roads.shp*

3. Click the "Set" button to extract all the fields from the polyline input layer.

4. Select the field containing the road type categorical values.

5. Click the "Unique Values" button to extract all the unique road type values.

6. Score each of the extracted road types from 1 to 5 based on local knowledge, where 5 is a road type that is very safe for walking and cycling and 1 is an unsafe road type.

7. Enter an alternate raster output file name if desired.

8. Click the "Execute" button to run the algorithm.

9. Status text next to the "Execute" button will appear and let you know once processing is complete.

10. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/WLK_Raster_output.tif*).

#### 4.5.2 Availability of Public Transport

!![image](https://github.com/worldbank/GEEST/assets/120469484/8dd068ae-b4dd-447c-bef0-0e57c8f4db17)

1. Navigate to and select point shapefile input for public transport stops.

   **Input File:** *PubTransportStops/Public_transportation_stops.shp*

3. Set hexagon grid size. The default is 1km.

The smaller size the more computationally intensive the algorithm will be.

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/APT_Raster_output.tif*).

#### 4.5.3 Safe Urban Design

![image](https://github.com/worldbank/GEEST/assets/120469484/2ab8874d-50cb-4445-9bac-3231b8328fb7)

1. Navigate to and select nighttime lights raster input.

   **Input File:** *Electricity/Nighttime_Lights_2021.tif*

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/SAF_Raster_output.tif*).

### 4.5.4 Security

![image](https://github.com/worldbank/GEEST/assets/120469484/10d4eb39-51b9-421d-b105-46466f4b3ba9)

1. Navigate to and select the crime rate polygon input shapefile containing a field reporting the crime rate for a specific incident.

   **Input File:** *Security/Crime_Incidence_Serious_Assaults.shp*

   **Input File:** *Security/Crime_Incidence_Sexual_Violence.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the crime rate.

5. Enter the raster output file name for the crime type.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be stored in the project folder specified in the "Setup" tab, in the "SEC" folder under the "Accessibility" folder (*Project_Folder/Place Characterization/SEC/Incidents_Raster_output.tif*).

**Steps 1 – 8 will have to be repeated for all facility types**.

8. Once all crime types have completed the processing, enter the aggregated raster output file name.

9. Click the "Aggregate" button to run the algorithm.

10. Status text next to the "Execute" button will appear and let you know once processing is complete.

11. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Place Characterization/SEC_Raster_output.tif*)

#### 4.5.5 Income Level

![image](https://github.com/worldbank/GEEST/assets/120469484/c1a88898-25a9-47ba-83a3-567bbf525f1a)

1. Navigate to and select the wealth index polygon input shapefile containing a field with the wealth index.

   **Input File:** *Income/Wealth_Index.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the wealth index.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/INC_Raster_output.tif*).

#### 4.5.6 Electricity Access

![image](https://github.com/worldbank/GEEST/assets/120469484/1a37676f-d82f-44bd-a554-9fcb854ce42d)

1. Navigate to and select electricity access polygon input shapefile containing a field indicating the percentage of individuals that have access to electricity.

   **Input File:** *Electricity/Electrification_rate.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of individuals that have access to electricity.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/ELC_Raster_output.tif*).

OR

1. Navigate to and select nighttime lights raster input.

   **Input File:** *Electricity/Nighttime_Lights_2021.tif*

3. Enter the raster output file name.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/ELC_Raster_output.tif*).

**N.B. If nighttime lights raster data is used for the "Safe Urban Design" factor it should not be used in the "Electrical Access" factor and vice-versa**

#### 4.5.7 Level of Urbanization

![image](https://github.com/worldbank/GEEST/assets/120469484/8776fd6c-8f40-4584-b517-a8610b867dd6)

1. Navigate to and select GHS-SMOD raster input.

   **Input File:** *Urbanization/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0_R7_C12.tif*

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/LOU_Raster_output.tif*).

#### 4.5.8 Size of Housing

![image](https://github.com/worldbank/GEEST/assets/120469484/b50b4538-6610-438b-b90a-4ee0c9462dc4)

1. Navigate to and select the building footprints polygon shapefile.

   **Input File:** *Housing/Building_footprint.shp*

3. Set hexagon grid size. The default is 1 km.

The smaller size the more computationally intensive the algorithm will be.

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/QUH_Raster_output.tif*).

#### 4.5.9 Digital Inclusion

![image](https://github.com/worldbank/GEEST/assets/120469484/de34e9da-6e68-4d09-bec5-84755bb35545)

1. Navigate to and select the polygon input shapefile containing a field indicating the percentage of houses with internet access.

   **Input File:** *Digital/Access_to_broadband_rates_community.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of houses with Internet access

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/DIG_Raster_output.tif*).

#### 4.5.10 Natural Environment and Climatic Factors

![image](https://github.com/worldbank/GEEST/assets/120469484/2b0a1b43-6f34-436e-a790-5516027d291a)

1. Navigate to and select polygon hazard shapefile.

   **Input File:** *Environment/Flood_risk.shp*

3. Click the "Set" button to extract all the fields from the polyline input layer.

4. Select the field containing the descriptive risk level values.

5. Click the "Unique Values" button to extract all the unique risk level values.

6. Score each of the extracted risk levels from 1 to 5, where 5 is the lowest risk and 1 is the highest risk.

7. Enter hazard type raster output file name.

8. Click the "Execute" button to run the algorithm.

9. Status text next to the "Execute" button will appear and let you know once processing is complete.

10. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder. (*Project_Folder/Place Characterization/ENV/Hazard_Raster_output.tif*)

**Steps 1 – 9 will have to be repeated for all hazard types**.

10. Once all hazard types have been processed, enter the aggregated raster output file name.

11. Click the "Aggregate" button to run the algorithm.

12. Status text next to the "Execute" button will appear and let you know once processing is complete.

13. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/ENV_Raster_output.tif*).

(pd-aggregation-tab)=
#### 4.5.11 Aggregate

![image](https://github.com/worldbank/GEEST/assets/120469484/bedf9d85-63c5-4cd9-857a-c726ef77a89a)

1. Load the raster outputs generated in each of the previous factor tabs for the Place Characterization Dimension.

_If a factor was executed in the same work session, its file path will automatically be populated after execution._

2. If factors are missing, adjust the weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter the aggregated raster output file name.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/AGG_Raster_output.tif*).

### 4.6 DIMENSION AGGREGATION TAB

![image](https://github.com/worldbank/GEEST/assets/120469484/651ed053-e36a-4fa1-b44d-6759fc5b60d8)

1. Load each dimension's aggregated raster outputs.

_If a dimension's factor aggregation was executed in the same work session, its file path will automatically be populated after execution._

2. If dimensions are missing, adjust the weighting percentage accordingly and ensure it totals up to 100%.

_If a dimension is missing it needs to be given a weighting of 0%._

3. Enter aggregated dimensions raster output file name.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated dimensional layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Final\_output" folder (*Project_Folder/Final_Output/Final_AGG_Raster_output.tif_).

### 4.7 ABOUT TAB

![image](https://github.com/worldbank/GEEST/assets/120469484/a949054b-1b8e-46f6-9279-fdd2b54212de)

Information on the tool its framework, scoring system, and how results should or can be interpreted.

### 4.8 INSIGHTS TAB
#### 4.8.1 Enablement

![image](https://github.com/worldbank/GEEST/assets/120469484/e0e94c47-bf17-462c-a41c-5023f96ab642)

**Classify into discrete classes**

1. Navigate to and select the enablement score input raster file. This can be the final aggregate score, a dimension aggregate score, or even a single factor output layer.

2. Click the "Classify" button under the "Enablement Score Input layer" field to run the algorithm.

3. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Insights/1) Level of Enablement Classification" folder. (*Project_Folder/Insights/1) Level of Enablement Classification/Level_of_Enablement.tif*)

4. Navigate to and select the population input raster file.

   **Input File:** *Population/Female_population_35_39.tif* (**Any of the age ranges can be used as input**)

6. Click the "Classify" button under the "Population Input layer" field to run the algorithm.

7. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Insights/2) Relative Population Count Classification" folder. (*Project_Folder/Insights/2) Relative Population Count Classification/Relative_Population_Count.tif*)

**Combine score and population classifications**

8. Navigate to and select the "Level of Enablement" output raster file produced in **step 2**. This file path will be automatically populated if **step 2** was executed in the same work session.

9. Navigate to and select the "Relative Population Count" output raster file produced in **step 6**. This file path will be automatically populated if **step 6** was executed in the same work session.

10. Click the "Combine Classification" button to run the algorithm combining the "Level of Enablement" and "Relative Population Count" raster layers.

11. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Insights/3) Combined Level of Enablement & Relative Population Count Classification" folder. (*Project_Folder/Insights/3) Combined Level of Enablement & Relative Population Count Classification/Enablement_&_Population_Combined_classification.tif*)

**Aggregation**

12. Navigate to and select the "Combine Classification" output raster file produced in **step 10**. This file path will be automatically populated if **step 10** was executed in the same work session.

13. Navigate to and select the aggregation input shapefile. This can be any polygon layer representing boundaries of interest for aggregation (e.g. municipal boundary layer)

    **Input File:** *AdminBoundaries/Admin6.shp* (**Any admin level can be used as input**)

14. Enter aggregated "Combine Classification" shapefiles output file name.

15.  Click the "Execute" button to run the algorithm.

16.  The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Insights/4) Aggregation" folder. (*Project_Folder/Insights/4) Aggregation/Aggregation_.tif*)

#### 4.8.2 RE Zone Raster Locations

![image](https://github.com/worldbank/GEEST/assets/120469484/612670ce-b60f-48a1-b085-7c6478c5b5f8)

1. Navigate to and select the combined classification input file produced in **step 10** of the "Enablement" tab. This file path will be automatically populated if **step 10** of the "Enablement" tab was executed in the same work session.

2. Navigate to and select the aggregated combined classification input file produced in **step 15** of the "Enablement" tab. This file path will be automatically populated if **step 15** of the "Enablement" tab was executed in the same work session.

3. Navigate to and select the potential RE zones input raster file. (Zones in the region that have no RE potential need to be represented with "no data" or "inf" values in the raster file)

   **Input File:** *RE/WBG_REZoning_DOM_score_wind.tif*

   **Input File:** *RE/WBG_REZoning_DOM_score_solar.tif*

4. Enter the "RE zones" raster file and shapefile prefix for the output file name.

5. Click the "Execute" button to run the algorithm.

6. The 2 output files will be stored in the project folder specified in the "Setup" tab, under the "Insights/5) RE Zone Raster Locations" folder. (*Project_Folder/Insights/5) RE Zone Raster Locations/RE_zone_.tif* **&** *Project_Folder/Insights/5) RE Zone Raster Locations/RE_zone_admin_units.shp*)


#### 4.8.3 RE Point Locations

![image](https://github.com/worldbank/GEEST/assets/120469484/55ae3e3a-2b0a-463c-a2d1-c76d37605e17)

1. Navigate to and select the combined classification input file produced in **step 10** of the "Enablement" tab. This file path will be automatically populated if **step 10** of the "Enablement" tab was executed in the same work session.

2. Navigate to and select the aggregated combined classification input file produced in **step 15** of the "Enablement" tab. This file path will be automatically populated if **step 15** of the "Enablement" tab was executed in the same work session.

3. Navigate to and select the RE point locations input shapefile of interest. (These could be existing RE job locations or other points of interest)

4. Set buffer radial distance in meters.

5. Enter the "RE point location" shapefiles prefix for the output file names.

5. Click the "Execute" button to run the algorithm.

6. The 2 output shapefiles will be stored in the project folder specified in the "Setup" tab, under the "Insights/6) RE Point Locations" folder. (*Project_Folder/Insights/6) RE Point Locations/RE_point_buffer_.shp* **&** *Project_Folder/Insights/6) RE Point Locations/RE_point_admin_units_buffer_.shp*)

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
