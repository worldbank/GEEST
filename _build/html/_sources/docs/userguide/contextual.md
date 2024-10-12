### Contextual

#### Workplace Discrimination

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/WD.jpg" alt="picture">
</p>

1.	Navigate to the WBL (Women, Business and the Law) report and input the WBL index score representing the value from 0 to 100. This value represents data at the national level and must be standardized on a scale ranging from 0 to 5. This indicator is composed by the Workplace Index score of the WBL. The data is already formatted on a scale from 1 to 100.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder. (Project_Folder/Contextual/WD.tif). The user can rename the output file to preferred filename.


#### Regulatory Frameworks

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/RF.jpg" alt="picture">
</p>

1.	Navigate to the WBL (Women, Business and the Law) report and input the WBL Pay and Parenthood index scores, values ranging from 0 to 100. This value represents data at the national level and must be standardized on a scale ranging from 0 to 5. This indicator is composed by aggregating the Parenthood and Pay Index scores of the WBL. The data is already formatted on a scale from 1 to 100.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder (Project_Folder/Contextual/RF.tif). The user can rename the output file to preferred filename.

#### Financial Inclusion

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/FI.jpg" alt="picture">
</p>

1.	Navigate to the WBL (Women, Business and the Law) report and input the WBL Entrepreneurship index score, value ranging from 0 to 100. This value represents data at the national level and must be standardized on a scale ranging from 0 to 5. The data is already formatted on a scale from 1 to 100. It comes from the Entrepreneurship rating of the WBL Index.

2.	Click the “Execute” button to run the algorithm.

3.	Status text next to the “Execute” button will appear and let you know once processing is complete.

4.	The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder (Project_Folder/Contextual/FIN.tif). The user can rename the output file to preferred filename.

#### Aggregate

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