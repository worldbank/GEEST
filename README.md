# Gender Enabling Environments Spatial Tool (GEEST)
This tool employs a multicriteria evaluation (MCE) framework to spatially describe womens' access to formal employment and business opportunities in the renewable energy sector in Small Island Developing States (SIDS). The MCE framework allows for the incorporation and assessment of dimensions, factors, and indicators to identify where the enabling environments (or lack thereof) are located for women to secure employment opportunities in SIDS.
## User Manual

- [1 Install QGIS](#1-install-qgis)

- [2 Install Open Route Service (ORS) plugin](#2-install-open-route-service-ors-plugin)

- [3 Installing Plugin on local device](#3-installing-plugin-on-local-device)

- [4 Using the Plugin](#4-using-the-plugin)
   - [4.1 Setup Tab](#setup-tab)
   - [4.2 Indivdual Tab](#indivdual-tab)
      - [4.2.1 Education](#education-tab)
      - [4.2.2 Care Responsibilities](#care-responsibilities-tab)
      - [4.2.3 Domestic Violence](#domestic-violence-tab)
      - [4.2.4 Aggregation](#id-aggregation-tab)
   - [4.3 Contextual Tab](#contextual-tab)
      - [4.3.1 Policy and Legal Protection](#policy-and-legal-protection-tab)
      - [4.3.2 Access to Finance](#access-to-finance-tab)
      - [4.3.3 Aggregation](#cd-aggregation-tab)
   - [4.4 Accessibility Tab](#accessibility-tab)
      - [4.4.1 Women's Travel Patterns](#womens-travel-patterns-tab)
      - [4.4.2 Access to Public Transport](#access-to-public-transport-tab)
      - [4.4.3 Education and Training Facilities](#education-and-training-facilities-tab)
      - [4.4.4 Jobs](#jobs-tab)
      - [4.4.5 Health Facilites](#health-facilities-tab)
      - [4.4.6 Financial Facilities](#financial-facilities-tab)
      - [4.4.7 Aggregation](#ad-aggregation-tab)
   - [4.5 Place Characterization Tab](#place-charaterization-tab)
      - [4.5.1 Active Transport](#active-transport-tab)
      - [4.5.2 Availability of Public Transport](#availability-of-public-transport-tab)
      - [4.5.3 Safe Urban Design](#safe-urban-design-tab)
      - [4.5.4 Security](#security-tab)
      - [4.5.5 Income Level](#income-level-tab)
      - [4.5.6 Electricity Access](#electricity-access-tab)
      - [4.5.7 Level of Urbanization](#level-of-urbanization-tab)
      - [4.5.8 Size of Housing](#size-of-housing-tab)
      - [4.5.9 Digital Inclusion](#digital-inculsion-tab)
      - [4.5.10 Natural Environment and Climatic Factors](#natural-environment-and-climatic-factors-tab)
      - [4.5.11 Aggregation](#pd-aggregation-tab)
   - [4.6 Dimension Aggregation Tab](#dimension-aggregation-tab)
   - [4.7 About Tab](#about-tab)
   - [4.8 Insights Tab](#insights-tab)
      - [4.8.1 Enablement](#enablement-tab)
      - [4.8.2 RE Zone Raster Locations](#re-zone-raster-locations-tab)
      - [4.8.3 RE Point Locations](#re-point-locations-tab) 

- [5 Troubleshooting](#5-troubleshooting)
   - [5.1 ERROR: Accessibility tabs permission error](#accessibility-permissions-error)
   - [5.2 QGIS plugin/interface widgets and text are distorted and scaled incorrectly](#distorted)
   - [5.3 Raster outputs not being loaded and displayed correctly](#raster-outputs)
   - [5.4 ERROR: Output directory not set](#output-directory)
   - [5.5 ERROR: Country boundary polygon not set](#country-boundary)
   - [5.6 ERROR: Co-ordinate reference system (CRS) not set](#crs)
   - [5.7 Alternative way to refresh the plugin if it freezes or does not run as expected](#alternative)
     
- [List of CRSs for SIDS](#sids-crs)

## 1 Install QGIS

1. The link below will take you to the QGIS website where you will be able to download the QGIS installation file. Note that it is possible to use older versions of QGIS, e.g. Version 3.28.

QGIS website: [https://www.qgis.org/en/site/](https://www.qgis.org/en/site/)

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/7a171161-f091-4b53-a7eb-3d644b241bd8)


2. Once the installation file is downloaded run the installation file.

3. A pop-up window as seen in the image below should show up. Follow the prompts and leave all settings on default.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/9cf1103d-c112-46ef-8c83-b866b25796e0)


## 2 Install Open Route Service (ORS) plugin

1. Open QGIS, navigate to the "Plugins" tab and select the "Manage and Install Plugins…" option from the drop-down menu.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/8bb04beb-4649-49a7-ad2a-c062cd818692)

2. The "Plugins" pop-up window should appear as seen in the image below.

3. In the search bar type "ORS", select the "ORS Tool" from the list of plugins, and select the install button to install the plugin.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/d0e22d26-4dfa-47a7-89a7-fab42ecea2a6)

4. You will now have to set up an account on the Open Route Service website which can be accessed by clicking the link below.

ORS website: [https://openrouteservice.org/](https://openrouteservice.org/)

ORS Sign up: [https://openrouteservice.org/dev/#/signup](https://openrouteservice.org/dev/#/signup)

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/0cdb2ccd-8a19-46ba-9afa-1406074a222f)

5. Fill in all the necessary fields to sign up and then log into your account.

6. Request a standard token and provide a name for the Token.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/efe9f9ab-1f29-4c28-81ec-73c8268b0e5e)

7. Once the token has been created, navigate to the Dashboard tab and click on the API key as seen in the image below. The API key should now be copied to the clipboard.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/5d0e7d0d-561b-46bd-980d-d9ef7059148e)


9. In the QGIS window navigate the ORS tool and select "Provider Settings".

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/7234b8ac-99a6-4668-8867-a0f4b29efb6a)

9. The provider settings pop-up window should now appear as seen in the image below.

10. Past the API key that has been copied to the clipboard into the API Key field and press "OK".

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/6cdf18f4-5908-46ef-a6c7-f36fb3d07048)

**N.B.** Additional credits can be requested on the ORS site by applying for the collaborative plan as described [here](https://openrouteservice.org/plans/). You will have to provide a brief motivation, however, if your application is in a humanitarian, academic, governmental, or not-for-profit organization, you should be eligible for the collaborative plan.

This email address can also be used for further assistance:

support@openrouteservice.heigit.org

## 3 Installing Plugin on local device

1. Click on the green "Code" button and select the "Download ZIP" option.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/72d7dc34-eb53-417b-9748-462e6fcc1c0c)

2. Once the download has been completed extract the contents of the ZIP file.

3. Navigate to your extracted ZIP folder and copy the _requirements.txt_ file.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/702bfc4a-388d-4da7-99fd-c7cfe30e9106)

4. Navigate to the QGIS program folder and paste the _requirements.txt_ file into it. The file path would be similar to this: _C:\Program Files\QGIS 3.32.0_ as seen in the image under **step 5**.

5. Run the _OSGeo4W_ batch file.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/0d0c609c-0278-4dde-abb8-81a44f62a033)

6. A command line pop-up window will appear as seen in the image below.

7. Type the following into it and press Enter.
```pip install -r requirements.txt```

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/506d8ec2-3d81-45c3-9234-1b95673cb9c8)

8. All the Python libraries that the Plugin is dependent on will now be installed. This can take a few minutes to install.

9. Once the installations are complete you can close the command line pop-up window.

10. Open QGIS, navigate to the "Plugins" tab and select the "Manage and Install Plugins…" option from the drop-down menu.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/17d610e1-c989-435c-ba10-187657d853b7)

11. In the plugin pop-up window navigate to the "Install from ZIP" tab.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/34ed8ae1-d533-43af-8dc7-17645189201a)

12. From the "Install from ZIP" tab navigate back to your extracted ZIP folder and select the "gender\_indicator\_tool" compressed (zipped) folder as seen in the image below.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/2cc9b67e-a990-4375-953a-2131f801dfcc)

13. Once the ZIP file has been selected click on "Install Plugin".

14. Once the plugin has been installed navigate to the "All" tab.

15. In the search bar type "GEEST" and click the check box next to the "Gender Enabling Environments Spatial Tool (GEEST)" to install the plugin.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/93ba70f0-1eca-48a4-aaad-cc68872d01f7)

16. The plugin is now installed and you should now be able to access it in your toolbar or under the Plugin's tab as seen in the image below.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/aba6f895-bb9a-4148-83a3-5a1fc82c5834)

## 4 Using the Plugin
Examples of files that can be used as input at a particular step as per the Pilot Country Database will be indicated at the end of the step. The following format will be used:

**Input File:** *Folder/file_name* --> *AccessFinance/Access_to_finance.shp*

### <a name="setup-tab"></a> 4.1 SETUP TAB

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/525515fd-3f45-494e-8d9a-2cb4256eee04)

1. Create a project folder that will be used to store all tool outputs.
   
3. Set the output directory to the project folder created in the previous step.
   
5. Set the country boundary layer by navigating to and selecting the **Admin 0** country boundary polygon shapefile for the country you want to analyze.

   **Input File:** *AdminBoundaries/Admin0.shp*

7. Select the appropriate coordinate reference system (CRS) from the QGIS CRS database.

**Appendix A**  _lists all the CRS to be used for the SIDS countries._

5. Copy and paste the EPSG code for your specific country and paste it in the Filter bar as seen in the image below.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/2a318f46-e78d-4f89-b6ee-cb291ad07e18)

6. Select the CRS from the list and click "OK".

7. Set your preferred output raster output resolution in meters squared.

### <a name="indivdual-tab"></a>4.2 INDIVIDUAL TAB

#### <a name="education-tab"></a>4.2.1 Education

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/68baff0a-cf3d-4045-b62b-432d505117bf)

1. Navigate to and select the polygon input shapefile containing a field reporting the percentage of women who have achieved a post-secondary education.

   **Input File:** *Education/Level_of_education*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of women who have achieved a post-secondary education.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/EDU_Raster_output.tif*)

#### <a name="care-responsibilities-tab"></a>4.2.2 Care Responsibilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/4b6f1c50-96fc-4ea2-985f-e226f41ab005)

1. Navigate to and select the polygon input shapefile containing a field reporting the percentage of time women spend on care responsibilities or household activities.

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of time women spend on care responsibilities or household activities.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/CRE_Raster_output.tif*)

#### <a name="domestic-violence-tab"></a>4.2.3 Domestic Violence

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/2adef90d-03ee-48ae-a16d-d7055939f636)

1. Navigate to and select the polygon input shapefile containing a field reporting the percentage of women who have suffered domestic violence.

   **Input File:** *DomesticViolence/Prevalence_of_domestic_violence.shp*
   
3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of women who have suffered domestic violence.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/DOV_Raster_output.tif*)

#### <a name="id-aggregation-tab"></a>4.2.4 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/a6cc36ed-377b-4c9d-933a-a8556832494e)

1. Load the raster outputs generated in each of the previous factor tabs for the Individual Dimension.

_If a factor was executed in the same work session, its file path will automatically be populated after execution._

2. If factors are missing adjust the weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter an alternate aggregated raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Individual" folder. (*Project_Folder/Individual/AGG_Raster_output.tif*)

### <a name="contextual-tab"></a>4.3 CONTEXTUAL TAB

#### <a name="policy-and-legal-protection-tab"></a>4.3.1 Policy and Legal Protection

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/049629e3-2a15-4701-8015-970cde23c4d3)

1. Navigate to and select polygon input shapefile containing a field reporting a percentage representing the level of protective policies afforded to women.

   **Input File:** *PolicyLegal/Regulatory_Framework_Law_agg.shp*
   
3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing a percentage representing the level of protective policies afforded to women.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Contextual/PLP_Raster_output.tif*)

#### <a name="access-to-finance-tab"></a>4.3.2 Access to Finance

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/1558ae32-4794-4c27-b64f-2c1872681083)

1. Navigate to and select polygon input shapefile containing a field reporting the percentage of women who have a bank account.

   **Input File:** *AccessFinance/Access_to_finance.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of women who have a bank account.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Contextual/FIN_Raster_output.tif*)

#### <a name="cd-aggregation-tab"></a>4.3.3 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/732852d1-27bc-42b5-bfe7-6165a70cf0b6)

1. Load the raster outputs generated in each of the previous factor tabs for the Contextual Dimension.

_If a factor was executed in the same work session, its file path will automatically be populated after execution._

2. If factors are missing adjust the weighting percentage accordingly and ensure it totals to 100%.

If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension.

3. Enter an alternate aggregated raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (*Project_Folder/Contextual/AGG_Raster_output.tif*)

### <a name="accessibility-tab"></a>4.4 ACCESSIBILITY TAB

#### <a name="womens-travel-patterns-tab"></a>4.4.1 Women's Travel Patterns

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/03498688-42b3-44fd-9d81-5dd0ca491c19)

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

#### <a name="access-to-public-transport-tab"></a>4.4.2 Access to Public Transport

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/7f02cf8a-8396-4641-80db-89f02356b37f)

1. Navigate to and select point shapefile input for public transport stops.

   **Input File:** *PubTransportStops/Public_transportation_stops.shp*

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delimitation.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Accessibility" folder (*Project_Folder/Accessibility/PBT_Raster_output.tif*).

#### <a name="education-and-training-facilities-tab"></a>4.4.3 Access to Education and Training Facilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/eceec2f6-b03e-4a18-9c02-3f9463b26492)

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

#### <a name="jobs-tab"></a>4.4.4 Access to Jobs in the RE sector

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/810b7d62-3174-4b49-9495-0675a78fa8ac)

1. Navigate to and select point shapefile input of jobs or job facilities.

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delamination.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (*Project_Folder/Accessibility/JOB_Raster_output.tif*).

#### <a name="health-facilities-tab"></a>4.4.5 Access to Health Facilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/93d48ded-25b4-409a-88c5-7de4f02092dd)

1. Navigate to and select point shapefile input of health care facilities.

   **Input File:** *HealthFacilities/Hospitals.shp*

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delimitation.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder. (*Project_Folder/Accessibility/HEA_Raster_output.tif*)

#### <a name="financial-facilities-tab"></a>4.4.6 Access to Financial Facilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/5bd4a772-6fc2-48e7-96b9-f2967f6f4865)

1. Navigate to and select point shapefile input of financial facilities.

   **Input File:** *FinancialFacilities/Financial_Facilities.shp*

3. Select the mode of travel (Walking OR Driving).

4. Select the method of measurement (Distance OR Time).

5. Specify travel distance or time increments in meters or time respectively using comma delamination.

6. Enter an alternate raster output file name if desired.

7. Click the "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (*Project_Folder/Accessibility/FIF_Raster_output.tif*).

#### <a name="ad-aggregation-tab"></a>4.4.7 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/e9f843dd-d374-42e3-b2e3-fbaf28c4d1be)

1. Load the raster outputs generated in each of the previous factor tabs for the Accessibility Dimension.

_If a factor was executed in the same work session, the file path will automatically be populated after execution._

2. If factors are missing, adjust the weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter alternate aggregated raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Accessibility/AGG_Raster_output.tif*).

### <a name="place-charaterization-tab"></a>4.5 PLACE CHARACTERIZATION TAB

#### <a name="active-transport-tab"></a>4.5.1 Active Transport

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/288bd781-ef45-4f2f-92a5-e312d82be340)

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

#### <a name="availability-of-public-transport-tab"></a>4.5.2 Availability of Public Transport

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/2a2dbb36-9f9a-42a4-8834-805969081e54)

1. Navigate to and select point shapefile input for public transport stops.

   **Input File:** *PubTransportStops/Public_transportation_stops.shp*

3. Set hexagon grid size. The default is 1km.

The smaller size the more computationally intensive the algorithm will be.

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/APT_Raster_output.tif*).

#### <a name="safe-urban-design-tab"></a>4.5.3 Safe Urban Design

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/1e73b47a-1717-441d-a2db-cb6ca7683165)

1. Navigate to and select nighttime lights raster input.

   **Input File:** *Electricity/Nighttime_Lights_2021.tif*

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/SAF_Raster_output.tif*).

### <a name="security-tab"></a>4.5.4 Security

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/b9f6c3c8-be8e-45f6-b351-cf76327b8b40)

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

#### <a name="income-level-tab"></a>4.5.5 Income Level

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/effab4d6-77fd-42b6-b27c-c674ca6a26a3)

1. Navigate to and select the wealth index polygon input shapefile containing a field with the wealth index.

   **Input File:** *Income/Wealth_Index.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the wealth index.

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/INC_Raster_output.tif*).

#### <a name="electricity-access-tab"></a>4.5.6 Electricity Access

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/7344c605-f7ce-4e15-bd73-2a75d84c6b69)

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

#### <a name="level-of-urbanization-tab"></a>4.5.7 Level of Urbanization

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/ac63f69e-c2c2-4176-aeb6-bfd983c8d2d1)

1. Navigate to and select GHS-SMOD raster input.

   **Input File:** *Urbanization/GHS_SMOD_E2020_GLOBE_R2023A_54009_1000_V1_0_R7_C12.tif*

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/LOU_Raster_output.tif*).

#### <a name="size-of-housing-tab"></a>4.5.8 Size of Housing

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/b3dc8615-2d17-48e1-9f13-3f65b5dfc70e)

1. Navigate to and select the building footprints polygon shapefile.

   **Input File:** *Housing/Building_footprint.shp*

3. Set hexagon grid size. The default is 1 km.

The smaller size the more computationally intensive the algorithm will be.

3. Enter an alternate raster output file name if desired.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (*Project_Folder/Place Characterization/QUH_Raster_output.tif*).

#### <a name="digital-inculsion-tab"></a>4.5.9 Digital Inclusion

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/19abbdf1-9804-43c5-8fb9-6548b13b70eb)

1. Navigate to and select the polygon input shapefile containing a field indicating the percentage of houses with internet access.

   **Input File:** *Digital/Access_to_broadband_rates_community.shp*

3. Click the "Set" button to extract all the fields from the polygon input layer.

4. Select the field containing the numeric value representing the percentage of houses with Internet access

5. Enter an alternate raster output file name if desired.

6. Click the "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/DIG_Raster_output.tif*).

#### <a name="natural-environment-and-climatic-factors-tab"></a>4.5.10 Natural Environment and Climatic Factors

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/fe2db337-b616-48ee-b20e-2be5a2296f64)

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

#### <a name="pd-aggregation-tab"></a>4.5.11 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/bd009d18-8a6c-4d8b-9d40-56fb38e81148)

1. Load the raster outputs generated in each of the previous factor tabs for the Place Characterization Dimension.

_If a factor was executed in the same work session, its file path will automatically be populated after execution._

2. If factors are missing, adjust the weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter the aggregated raster output file name.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (*Project_Folder/Place Characterization/AGG_Raster_output.tif*).

### <a name="dimension-aggregation-tab"></a>4.6 DIMENSION AGGREGATION TAB

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/8d2787d9-78ac-4774-9b70-6bee722bfe0a)

1. Load each dimension's aggregated raster outputs.

_If a dimension's factor aggregation was executed in the same work session, its file path will automatically be populated after execution._

2. If dimensions are missing, adjust the weighting percentage accordingly and ensure it totals up to 100%.

_If a dimension is missing it needs to be given a weighting of 0%._

3. Enter aggregated dimensions raster output file name.

4. Click the "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated dimensional layer will be loaded to the QGIS and appear in the table of contents.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Final\_output" folder (*Project_Folder/Final_Output/Final_AGG_Raster_output.tif_).

### <a name="about-tab"></a>4.7 ABOUT TAB

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/4064c4f2-75a9-4c6c-8727-6c0674699b2c)

Information on the tool its framework, scoring system, and how results should or can be interpreted. 

### <a name="insights-tab"></a>4.8 INSIGHTS TAB
#### <a name="enablement-tab"></a>4.8.1 Enablement

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/11389ee3-9835-4a97-a570-8f7c9efdeca1)

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

#### <a name="re-zone-raster-locations-tab"></a>4.8.2 RE Zone Raster Locations

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/b1f6b997-b126-46d5-903c-7a94b93bbf90)

1. Navigate to and select the combined classification input file produced in **step 10** of the "Enablement" tab. This file path will be automatically populated if **step 10** of the "Enablement" tab was executed in the same work session.

2. Navigate to and select the aggregated combined classification input file produced in **step 15** of the "Enablement" tab. This file path will be automatically populated if **step 15** of the "Enablement" tab was executed in the same work session.

3. Navigate to and select the potential RE zones input raster file. (Zones in the region that have no RE potential need to be represented with "no data" or "inf" values in the raster file)

   **Input File:** *RE/WBG_REZoning_DOM_score_wind.tif*

   **Input File:** *RE/WBG_REZoning_DOM_score_solar.tif*

4. Enter the "RE zones" raster file and shapefile prefix for the output file name.

5. Click the "Execute" button to run the algorithm.

6. The 2 output files will be stored in the project folder specified in the "Setup" tab, under the "Insights/5) RE Zone Raster Locations" folder. (*Project_Folder/Insights/5) RE Zone Raster Locations/RE_zone_.tif* **&** *Project_Folder/Insights/5) RE Zone Raster Locations/RE_zone_admin_units.shp*)


#### <a name="re-point-locations-tab"></a>4.8.3 RE Point Locations

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/22fd5d42-25a9-4253-9a76-2c64c53e95c4)


## 5 Troubleshooting

### <a name="accessibility-permissions-error"></a>5.1 ACCESSIBILTY TABS PERMISSIONS ERROR

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/9fbabc46-48c8-49db-b8b8-a82d96a5b2db)

This error occurs when some of the shapefiles produced in the temp folder of the working directory are trying to be overwritten or deleted but can't because it's still being stored in QGIS's memory. This can occurs even when the layer is removed from the QGIS table of contents.

**This error may also occur when the tool runs correctly so first check if the desired output file was produced in the working directory.**

If the file is not produced you can try the following:
- Delete the *temp* folder in the working directory
- If you cannot delete the *temp* folder you will have to close QGIS and open it again, complete the setup tab, go back to the tab where the error occurred and re-run the tab again.

### <a name="distorted"></a>5.2 QGIS PLUGIN/INTERFACE WIDGETS AND TEXT ARE DISTORTED AND SCALED INCORRECTLY
![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/83c37f7b-d95f-4bbe-b4a7-9040be5ddce1)

This is a problem linked to display settings caused by the connection of multiple monitors and/or varying display scales and resolutions, rather than a QGIS or plugin-related issue. This is backed by a Microsoft support post, linked [here](https://support.microsoft.com/en-gb/topic/windows-scaling-issues-for-high-dpi-devices-508483cd-7c59-0d08-12b0-960b99aa347d), highlighting the issues that may be experienced when using a high-DPI device, such as a 4k monitor. Additionally, in the scaling display setting, Microsoft indicates that entering a custom scaling size between 100% - 500% is not recommended as "...it can cause text and apps to become unreadable."

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/d30c84da-4371-487e-b0e6-811ae76e821b)

Possible solutions to this are:
- Adjust the scale for all monitors to 100%.
- Ensure that the display resolution is the same for both monitors. i.e. If the smallest monitor is set to 1920 x 1080 set the 4k monitor to this display resolution as well.

### <a name="raster-outputs"></a>5.3 RASTER OUTPUTS NOT BEING LOADED AND DISPLAYING CORRECTLY

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/383081b1-4b8b-41c7-8c4b-bf3fe09b5215)

Occasionally, some of the outputs automatically loaded to the QGIS table of contents do not display correctly. To correct this, try removing the layer that is displayed incorrectly and add it again to QGIS.

## <a name="output-directory"></a>5.4 ERROR: OUTPUT DIRECTORY NOT SET

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/9ae44237-e6f8-4bb9-ac4d-ba9081cc83b9)

If you see the following error message, please check if your output directory has been set in the "Setup" tab.

### <a name="country-boundary"></a>5.5 ERROR: COUNTRY BOUNDARY POLYGON NOT SET

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/8c92f6df-07b3-4953-bf7b-0a57a3c10072)

If you see the following error message, please check if you're country boundary polygon layer has been set in the "Setup" tab.

### <a name="crs"></a>5.6 ERROR: CO-ORDINATE REFERENCE SYSTEM (CRS) NOT SET

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/fd3baffa-6b3f-4ef7-a89a-8168b57cd7be)

If you see the following error message, please check if you're CRS has been set in the "Setup" tab.

### <a name="alternative"></a>5.7 ALTERNATIVE WAY TO REFRESH THE PLUGIN IF IT FREEZES OR DOES NOT RUN AS EXPECTED

1. Install the "Plugin Reloader" plugin.

   1.1 Navigate to and open “Manage and Install Plugins…” under the plugins tab in QGIS.

   1.2 In the search bar type “plugin reloader”.

   1.3 Select the “Plugin Reloader” plugin and click on the install button. 
   

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/da85a4b2-f16c-4fb0-a9a5-3acaa42b768f)

 1.4 Navigate to the "Plugin Reloader" configuration window under the Plugins tab.

*Plugins* → *Plugin Reloader* → *Configure*

 1.5 From the drop-down list select the "gender\_indicator\_tool" plugin and press "OK".

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/3019b00e-46ac-490d-854c-5c7f61ee6a2e)

  1.6 If you encounter an unexpected error in the tool that has not…

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/b3b0f393-d4ff-4d92-8ea5-d54540070ae9)

**OR**

**If the "Plugin Reloader" does not resolve the error close QGIS, restart it again, and re-run the process you were trying to execute.**

# <a name="sids-crs"></a>List of CRSs for SIDS

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

