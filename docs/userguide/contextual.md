## Contextual

<p align="justify"> 
The Contextual Dimension refers to the laws and policies that shape workplace gender discrimination, financial autonomy, and overall gender empowerment. Although this dimension may vary between countries due to differences in legal frameworks, it remains consistent within a single country, as national policies and regulations are typically applied uniformly across countries. 
</p>

<h3>Workplace Discrimination</h3>
<hr style="height: 3px; background-color: grey; border: none;">

<p align="justify"> 
Workplace Discrimination involves laws that address gender biases and stereotypes that hinder women's career advancement, especially in male-dominated fields.
This indicator is composed by the Workplace Index score of the WBL 2024, which is then standardized on a scale from 0 to 5.
</p>

<p align="justify"> 
<strong>Step 1</strong>: Accessing the <strong>Contextual Dimension</strong>
<ul>
    <li><strong>Locate the Contextual Section:</strong>
        <ul>
            <li>Open the GEEST tool interface.</li>
            <li>In the left panel, find the section labeled "Contextual".</li>
        </ul>
    </li>
    <li><strong>Find the Workplace Discrimination Category:</strong>
        <ul>
            <li>Under the "Contextual" section, you will see "Workplace Discrimination". This category contains various inputs.</li>
        </ul>
    </li>
</ul>

<strong>Step 2</strong>: Opening the Properties
<ul>
    <li><strong>Right-Click on Workplace Discrimination:</strong>
        <ul>
            <li>Right-click on "WBL 2024 Workplace Index Score" within the Workplace Discrimination section.</li>
        </ul>
    </li>
    <li><strong>Select Show Properties:</strong>
        <ul>
            <li>A context menu will appear. Click on "Show Properties" to access the details of the input.</li>
        </ul>
    </li>
    <li><strong>Pop-Up Window:</strong>
        <ul>
            <li>A new pop-up window will appear, displaying various properties and options related to the Workplace Index Score.</li>
        </ul>
    </li>
</ul>
</p>


<p align="center">
 **IMAGE for WD**
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
