# Gender Enabling Environments Spatial Tool (GEEST)

## User Manual December 2023

[1 Install QGIS](#1-install-qgis)

[2 Install Open Route Service (ORS) plugin](#2-install-open-route-service-ors-plugin)

[3 Installing Plugin on local device](#3-installing-plugin-on-local-device)

[4 Using the Plugin](#4-using-the-plugin)

[5 Troubleshooting](#5-troubleshooting)

## 1 Install QGIS

1. The link below will take you to the QGIS website where you will be able to download the QGIS installation file. Note that it is possible to use older versions of QGIS, e.g. Version 3.28.

QGIS website: [https://www.qgis.org/en/site/](https://www.qgis.org/en/site/)

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/7a171161-f091-4b53-a7eb-3d644b241bd8)


2. Once the installation file is downloaded run the installation file.

3. A pop up window as seen in image below should show up. Follow the prompts and leave all settings on default.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/9cf1103d-c112-46ef-8c83-b866b25796e0)


## 2 Install Open Route Service (ORS) plugin

1. Open QGIS, navigate to the "Plugins" tab and select "Manage and Install Plugins…" option from the drop-down menu.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/8bb04beb-4649-49a7-ad2a-c062cd818692)

2. The "Plugins" pop up window should appear as seen in image below.

3. In the search bar type "ORS", select the "ORS Tool" from the list of plugins, and select the install button to install the plugin.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/d0e22d26-4dfa-47a7-89a7-fab42ecea2a6)

4. You will now have to setup an account on the Open Route Service website which can be accessed by clicking the link below.

ORS website: [https://openrouteservice.org/](https://openrouteservice.org/)

ORS Sign up: [https://openrouteservice.org/dev/#/signup](https://openrouteservice.org/dev/#/signup)

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/0cdb2ccd-8a19-46ba-9afa-1406074a222f)

5. Fill in all the necessary fields to sign up and then log into your account.

6. Request a standard token and provide a name for Token.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/efe9f9ab-1f29-4c28-81ec-73c8268b0e5e)

7. Once token has been created, navigate to the Dashboard tab and click on the API key as seen in the image below. The API key should now be copied to clipboard.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/5d0e7d0d-561b-46bd-980d-d9ef7059148e)


9. In the QGIS window navigate the ORS tool and select "Provider Settings".

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/7234b8ac-99a6-4668-8867-a0f4b29efb6a)

9. The provider settings pop up window should now appear as seen in the image below.

10. Past the API key that has been copied to the clipboard into the API Key field and press "OK".

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/6cdf18f4-5908-46ef-a6c7-f36fb3d07048)

**N.B.** Additional credits can be requested on the ORS site by applying for the collaborative plan as described [here](https://openrouteservice.org/plans/). You will have to provide a brief motivation, however, if your application is in a humanitarian, academic, governmental, or non-for-profit organization, you should be eligible for the collaborative plan.

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

9. Once the installations are complete you can close command line pop-up window.

10. Open QGIS, navigate to the "Plugins" tab and select "Manage and Install Plugins…" option from the drop-down menu.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/17d610e1-c989-435c-ba10-187657d853b7)

11. In the plugin pop up window navigate to the "Install from ZIP" tab.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/34ed8ae1-d533-43af-8dc7-17645189201a)

12. From the "Install from ZIP" tab navigate back to your extracted ZIP folder and select the "gender\_indicator\_tool" compressed (zipped) folder as seen in the image bellow.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/2cc9b67e-a990-4375-953a-2131f801dfcc)

13. Once ZIP file has been selected click on "Install Plugin".

14. Once plugin has been installed navigate to the "All" tab.

15. In the search bar type "GEEST" and click the check box next to the "Gender Enabling Environments Spatial Tool (GEEST)" to install the plugin.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/120469484/93ba70f0-1eca-48a4-aaad-cc68872d01f7)

16. The plugin is now installed and you should now be able to access it in you tool bar or under the Plugin's tab as seen in the image below.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/754006a1-3fe2-4f01-9561-71bd5af2d88f)

## 4 Using the Plugin

### 4.1 SETUP TAB

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/3bd49833-ed0b-4a5e-a77d-ac4159cf3b16)

1. Create a project folder that will be used to store all tool outputs.
   
3. Set the output directory to project folder created in the previous step.
   
5. Set the country boundary layer by navigating to and selecting the **Admin 0** country boundary polygon shapefile for the country you want to analyze.

6. Select the appropriate coordinate reference system (CRS) form the QGIS CRS database.

**Appendix A**  _lists the all the CRS to be used for the SIDS countries._

5. Copy and paste the EPSG code for your specific country and paste it in the Filter bar as seen in the image below.

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/2a318f46-e78d-4f89-b6ee-cb291ad07e18)

6. Select the CRS from the list and click "OK".

7. Set your preferred out raster output resolution in meters squared.

### 4.2 INDIVIDUAL TAB

#### 4.2.1 Education

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/39326777-56ac-4070-9926-40a7f064758e)

1. Navigate to and select polygon input shapefile containing a field reporting the percentage of women who have achieved a post-secondary education.

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing the percentage of women who have achieved a post-secondary education.

4. Enter an alternate raster output file name if desired.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The aggregated output raster file will be store in the project folder specified in the "Setup" tab, under the "Individual" folder. (_Project\_ Folder/Individual/Raster\_output.tif_)

#### 4.2.2 Care Responsibilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/93de6a5b-15cb-4ca9-89a6-2bc7f4bc0537)

1. Navigate to and select polygon input shapefile containing a field reporting the percentage of time women spend on care responsibilities or household activities.

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing percentage of time women spend on care responsibilities or household activities.

4. Enter an alternate raster output file name if desired.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The aggregated output raster file will be store in the project folder specified in the "Setup" tab, under the "Individual" folder. (_Project\_ Folder/Individual/Raster\_output.tif_)

#### 4.2.3 Domestic Violence

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/b7aa52c3-a1f9-4554-9754-c9ddec97c46a)

1. Navigate to and select polygon input shapefile containing a field reporting the percentage of women who have suffered domestic violence.

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing the percentage of women who have suffered domestic violence.

4. Enter an alternate raster output file name if desired.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The aggregated output raster file will be store in the project folder specified in the "Setup" tab, under the "Individual" folder. (_Project\_ Folder/Individual/Raster\_output.tif_)

#### 4.2.4 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/652149bb-9205-4b14-9f01-cb19da7e8701)

1. Load the raster outputs generated in each of the previous factor tabs for the Individual Dimension.

_If a factor was executed in the same work session, it's file path will automatically be populated after execution._

2. If factors are missing adjust weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter an alternate aggregated raster output file name if desired.

4. Click "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of content.

7. The aggregated output raster file will be store in the project folder specified in the "Setup" tab, under the "Individual" folder. (_Project\_ Folder/Individual/Raster\_output.tif_)

### 4.3 CONTEXTUAL TAB

#### 4.3.1 Policy and Legal Protection

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/c77e07f2-2980-4294-9f70-9506c3bf7f81)

1. Navigate to and select polygon input shapefile containing a field reporting a percentage representing the level of protective policies afforded to women.
2. Click the "Set" button to extract all the fields from the polygon input layer.
3. Select the field containing the numeric value representing a percentage representing the level of protective policies afforded to women.
4. Enter an alternate raster output file name if desired.
5. Click "Execute" button to run the algorithm.
6. Status text next to the "Execute" button will appear and let you know once processing is complete.
7. The aggregated output raster file will be store in the project folder specified in the "Setup" tab, under the "Contextual" folder. (_Project\_ Folder/Contextual/Raster\_output.tif_)

#### 4.3.2 Access to Finance

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/5644492a-99c3-41c2-a8bf-d61f68827cdf)

1. Navigate to and select polygon input shapefile containing a field reporting the percentage of women who have a bank account.

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing the percentage of women who have a bank account.

4. Enter an alternate raster output file name if desired.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The aggregated output raster file will be store in the project folder specified in the "Setup" tab, under the "Contextual" folder. (_Project\_ Folder/Contextual/Raster\_output.tif_)

#### 4.3.3 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/7d78a94b-076f-438a-b5f3-14bdf44edf17)

1. Load the raster outputs generated in each of the previous factor tabs for the Contextual Dimension.

_If a factor was executed in the same work session, it's file path will automatically be populated after execution._

2. If factors are missing adjust weighting percentage accordingly and ensure it totals to 100%.

If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension.

3. Enter an alternate aggregated raster output file name if desired.

4. Click "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of content.

7. The aggregated output raster file will be store in the project folder specified in the "Setup" tab, under the "Contextual" folder. (_Project\_ Folder/Contextual/Raster\_output.tif_)

### 4.4 ACCESSIBILITY TAB

#### 4.4.1 Women's Travel Patterns

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/96b72156-45d7-4310-b959-2f17b7718e27)

1. Navigate to and select point shapefile input of facilities related to women's role as caregivers. This includes:
  - Childcare facilities
  - Primary and secondary schools
  - Markets
  - Grocery stores
  - Recreational areas

2. Select the mode of travel (Walking OR Driving).

3. Select method of measurement (Distance OR Time).

4. Specify travel distance or time increments in meters or time respectively using comma delimitation.

5. Edit the facility raster output file name for each unique type of facility.

6. Click "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The output raster file will be store in the project folder specified in the "Setup" tab, in the "WTP" folder under the "Accessibility" folder. (_Project\_ Folder/Accessibility/WTP/Raster\_output.tif_)

**Steps 1 – 8 will have to be repeated for all facility types**.

9. Once all facilities have completed the processing, Enter aggregated raster output file name.

10. Click "Aggregate" button to run the algorithm.

11. Status text next to the "Execute" button will appear and let you know once processing is complete.

12. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (_Project\_Foldser/Accessibility/Raster\_output.tif_)

#### 4.4.2 Access to Public Transport

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/c3bf07a4-3a6e-4cf1-a59b-6731b5d6cbf3)

1. Navigate to and select point shapefile input for public transport stops.

2. Select the mode of travel (Walking OR Driving).

3. Select method of measurement (Distance OR Time).

4. Specify travel distance or time increments in meters or time respectively using comma delimitation.

5. Enter an alternate raster output file name if desired.

6. Click "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder set in the "Setup" tab, under the "Accessibility" folder (_Project\_ Folder/Accessibility/Raster\_output.tif_).

#### 4.4.3 Access to Education and Training Facilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/38c5ef9e-0b82-4db7-b22a-afce1e678e65)

1. Navigate to and select point shapefile input of education and training facilities.

2. Select the mode of travel (Walking OR Driving).

3. Select method of measurement (Distance OR Time).

4. Specify travel distance or time increments in meters or time respectively using comma delimitation.

5. Enter alternate raster output file name if desired.

6. Click "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (_Project\_ Folder/Accessibility/Raster\_output.tif_).

#### 4.4.4 Access to Jobs in the RE sector

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/3138898e-1c2a-419f-ab45-8bf1e0a025e0)

1. Navigate to and select point shapefile input of jobs or job facilities.

2. Select the mode of travel (Walking OR Driving).

3. Select method of measurement (Distance OR Time).

4. Specify travel distance or time increments in meters or time respectively using comma delamination.

5. Enter alternate raster output file name if desired.

6. Click "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (_Project\_ Folder/Accessibility/Raster\_output.tif_).

#### 4.4.5 Access to Health Facilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/74cab802-4d1a-42e0-a15e-0b062e308217)

1. Navigate to and select point shapefile input of health care facilities.

2. Select the mode of travel (Walking OR Driving).

3. Select method of measurement (Distance OR Time).

4. Specify travel distance or time increments in meters or time respectively using comma delimitation.

5. Enter alternate raster output file name if desired.

6. Click "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder. (_Project\_ Folder/Accessibility/Raster\_output.tif_)

#### 4.4.6 Access to Financial Facilities

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/df5b270e-b77a-4820-af28-343088359878)

1. Navigate to and select point shapefile input of financial facilities.

2. Select the mode of travel (Walking OR Driving).

3. Select method of measurement (Distance OR Time).

4. Specify travel distance or time increments in meters or time respectively using comma delamination.

5. Enter alternate raster output file name if desired.

6. Click "Execute" button to run the algorithm.

7. Status text next to the "Execute" button will appear and let you know once processing is complete.

8. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Accessibility" folder (_Project\_ Folder/Accessibility/Raster\_output.tif_).

#### 4.4.7 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/395612a1-f2d1-4c4c-9a03-80874651ddf2)

1. Load the raster outputs generated in each of the previous factor tabs for the Accessibility Dimension.

_If a factor was executed in the same work session, the file path will automatically be populated after execution._

2. If factors are missing, adjust weighting percentage accordingly and ensure it totals to 100%.

_If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension._

3. Enter alternate aggregated raster output file name if desired.

4. Click "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of content.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (_Project\_ Folder/Accessibility/Raster\_output.tif_).

### 4.5 PLACE CHARACTERIZATION TAB

#### 4.5.1 Active Transport

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/437ac901-0f25-4750-acf4-ee3f7f460d3f)

1. Navigate to and select polyline road network shapefile.

2. Click the "Set" button to extract all the fields from the polyline input layer.

3. Select the field containing the road type categorical values.

4. Click the "Unique Values" button to extract all the unique road type values.

5. Score each of the extracted road types from 1 to 5 based on local knowledge, where 5 is a road type that is very safe for walking and cycling and 1 is a road type that is unsafe.

6. Enter alternate raster output file name if desired.

7. Click "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (_Project\_ Folder/__Place Characterization/Raster\_output.tif_).

#### 4.5.2 Availability of Public Transport

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/19f8a8bc-1868-42f5-a199-023dc6f14849)

1. Navigate to and select point shapefile input for public transport stops.

2. Set hexagon grid size. The default is 1km.

The smaller size the more computationally intensive the algorithm will be.

3. Enter alternate raster output file name if desired.

4. Click "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (_Project\_ Folder/__Place Characterization/Raster\_output.tif_).

#### 4.5.3 Safety

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/93fa284e-77ab-4f77-a15e-6886ce90623b)

1. Navigate to and select night time lights raster input.

2. Enter alternate raster output file name if desired.

3. Click "Execute" button to run the algorithm.

4. Status text next to the "Execute" button will appear and let you know once processing is complete.

5. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Place Characterization" folder (_Project\_ Folder/Place Characterization/Raster\_output.tif_).

### 4.5.4 Security

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/5eed1d4f-08fb-41d7-88c9-f8c5be3555af)

1. Navigate to and select crime rate polygon input shapefile containing a field reporting crime rate for a specific incident.

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing crime rate.

4. Enter raster output file name for the crime type.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The output raster file will be stored in the project folder specified in the "Setup" tab, in the "SEC" folder under the "Accessibility" folder (_Project\_ Folder/Place Characterization/SEC/Raster\_output.tif_).

**Steps 1 – 8 will have to be repeated for all facility types**.

8. Once all crime types have completed the processing, enter aggregated raster output file name.

9. Click "Aggregate" button to run the algorithm.

10. Status text next to the "Execute" button will appear and let you know once processing is complete.

11. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder. (_Project\_Folder//Place Characterization/Raster\_output.tif_)

#### 4.5.5 Income Level

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/5e244e96-ba82-4c63-a6ca-5b569d6c8d13)

1. Navigate to and select wealth index polygon input shapefile containing a field with the wealth index.

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing wealth index.

4. Enter alternate raster output file name if desired.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (_Project\_Folder//Place Characterization/Raster\_output.tif_).

#### 4.5.6 Electricity Access

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/a24d2cb5-f62f-411f-9774-49b41b455d7d)

1. Navigate to and select electricity access polygon input shapefile containing a field indicating percentage individuals that have access to electricity.

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing percentage individuals that have access to electricity.

4. Enter an alternate raster output file name if desired.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (_Project\_Folder//Place Characterization/Raster\_output.tif_).

OR

1. Navigate to and select night time lights raster input.

2. Enter raster output file name.

3. Click "Execute" button to run the algorithm.

4. Status text next to the "Execute" button will appear and let you know once processing is complete.

5. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (Project\_ Folder/Place Characterization/Raster\_output.tif).

**N.B. If night time lights raster data is used for the "Safe Urban Design" factor it should not be used in the "Electrical Access" factor and vice-versa**

#### 4.5.7Urbanization

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/dd3e2069-b8cc-4a63-b69d-e0ec16110662)

1. Navigate to and select GHS-SMOD raster input.

2. Enter alternate raster output file name if desired.

3. Click "Execute" button to run the algorithm.

4. Status text next to the "Execute" button will appear and let you know once processing is complete.

5. The output raster file will be stored in the project folder set in the "Setup" tab, under the "Place Characterization" folder (_Project\_ Folder/Place Characterization/Raster\_output.tif_).

#### 4.5.8 Size of Housing

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/98ade628-c27b-4103-8b19-22402d71c6b4)

1. Navigate to and select the building footprints polygon shapefile.

2. Set hexagon grid size. The default is 1 km.

The smaller size the more computationally intensive the algorithm will be.

3. Enter alternate raster output file name if desired.

4. Click "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder (_Project\_ Folder/__Place Characterization/Raster\_output.tif_).

#### 4.5.9 Digital Inclusion

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/3a31dbee-636f-48bb-bf5a-8f3aea50fed6)

1. Navigate to and select the polygon input shapefile containing a field indicating representing the percentage of houses with Internet access

2. Click the "Set" button to extract all the fields from the polygon input layer.

3. Select the field containing the numeric value representing the percentage of houses with Internet access

4. Enter alternate raster output file name if desired.

5. Click "Execute" button to run the algorithm.

6. Status text next to the "Execute" button will appear and let you know once processing is complete.

7. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (_Project\_Folder//Place Characterization/Raster\_output.tif_).

#### 4.5.10 Natural Environment and Climatic Factors

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/503e2e4f-f4d2-46be-b941-19dd81a37e34)

1. Navigate to and select polygon hazard shapefile.

2. Click the "Set" button to extract all the fields from the polyline input layer.

3. Select the field containing the descriptive risk level values.

4. Click the "Unique Values" button to extract all the unique risk level values.

5. Score each of the extracted risk levels from 1 to 5, where 5 is a lowest risk and 1 is highest risk.

6. Enter hazard type raster output file name.

7. Click "Execute" button to run the algorithm.

8. Status text next to the "Execute" button will appear and let you know once processing is complete.

9. The output raster file will be stored in the project folder specified in the "Setup" tab, under the "Place Characterization" folder. (_Project\_ Folder/Place Characterization/ENV/Raster\_output.tif_)

**Steps 1 – 9 will have to be repeated for all hazard types**.

10. Once all hazard types have been processed, enter aggregated raster output file name.

11. Click "Aggregate" button to run the algorithm.

12. Status text next to the "Execute" button will appear and let you know once processing is complete.

13. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (_Project\_Folder//Place Characterization/Raster\_output.tif_).

#### 4.5.11 Aggregate

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/86a30af0-6fe2-4711-8f2a-43ecdd854098)

1. Load the raster outputs generated in each of the previous factor tabs for the Place Characterization Dimension.

_If a factor was executed in the same work session, it's file path will automatically be populated after execution._

2. If factors are missing, adjust weighting percentage accordingly and ensure it totals to 100%.

If a factor is missing it needs to be given a weighting of 0%. All factors should have equal weighting within a dimension.

3. Enter aggregated raster output file name.

4. Click "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated layer will be loaded to the QGIS and appear in the table of content.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Contextual" folder (_Project\_ Folder/Place Characterization/Raster\_output.tif_).

### 4.6 DIMENSION AGGREGATION TAB

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/f0e52173-c037-49d3-be0f-b30b3f858ebc)

1. Load each dimensions aggregated raster outputs.

_If a dimension's factor aggregation was executed in the same work session, it's file path will automatically be populated after execution._

2. If dimensions are missing, adjust weighting percentage accordingly and ensure it totals up to 100%.

If a dimension is missing it needs to be given a weighting of 0%.

3. Enter aggregated dimensions raster output file name.

4. Click "Execute" button to run the algorithm.

5. Status text next to the "Execute" button will appear and let you know once processing is complete.

6. The aggregated dimensional layer will be loaded to the QGIS and appear in the table of content.

7. The aggregated output raster file will be stored in the project folder specified in the "Setup" tab, under the "Final\_output" folder (_Project\_ Folder/Final\_Output/Raster\_output.tif_).

### 4.7 INSIGHTS TAB

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/d6f7ba73-01f4-4791-b09b-7f1276811f10)

## 5 Troubleshooting

To be populated during the tool trial period as we identify common bugs or issues that aren't necessarily related to the back end programming of the tool.

### 5.1 Acceccibilty tab processing Permission Error

### 5.2 INTERFACE WIDGETS AND TEXT ARE DISTORTED

### 5.3 Raster outputs not dispalying correctly

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/383081b1-4b8b-41c7-8c4b-bf3fe09b5215)

Occasionally, some of the outputs that are automatically loaded to the QGIS table of contents don't display correctly. To correct this, try and removing the layer that is displayed incorrectly and add it again to QGIS.
#
## 5.4 ERROR: OUTPUT DIRECTORY NOT SET

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/9ae44237-e6f8-4bb9-ac4d-ba9081cc83b9)

If you see the following error message, please check if you're output directory has been set in the "Setup" tab.

### 5.5 ERROR: Country boundary Polygon not set

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/8c92f6df-07b3-4953-bf7b-0a57a3c10072)

If you see the following error message, please check if you're country boundary polygon layer has been set in the "Setup" tab.

### 5.6 ERROR: Co-ordinate Reference System (CRS) not set

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/fd3baffa-6b3f-4ef7-a89a-8168b57cd7be)

If you see the following error message, please check if you're CRS has been set in the "Setup" tab.

### 5.7 Steps to take if tool freezes or does not run as expected

1. Install the "Plugin Reloader" plugin.

   1.1 Navigate to and open “Manage and Install Plugins…” under the plugins tab in QGIS.

   1.2 In the search bar type “plugin reloader”.

   1.3 Select the “Plugin Reloader” plugin and click on the install button. 
   

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/da85a4b2-f16c-4fb0-a9a5-3acaa42b768f)

 1.4 Navigate to the "Plugin Reloader" configuration window under the Plugins tab.

*Plugins* → *Plugin Reloader* → *Configure*

 1.5 From the drop down list select the "gender\_indicator\_tool" plugin and press "OK".

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/3019b00e-46ac-490d-854c-5c7f61ee6a2e)

  1.6 If you encounter an unexpected error in the tool that has not…

![image](https://github.com/Pegasys-Resilience/WBGIT/assets/145646474/b3b0f393-d4ff-4d92-8ea5-d54540070ae9)

**OR**

**If the "Plugin Reloader" does not resolve the error close QGIS and restart it again, and re-run the process you were trying to execute.**

# APPENDIX A SIDS CRS

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

