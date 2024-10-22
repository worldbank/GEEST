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

<h3>Step 1: Accessing the Contextual Dimension</h3>
<ul>
    <li>
        <strong>Locate the Workplace Discrimination Section:</strong>
        <ul>
               <span>🔍 Right-Click on Workplace Discrimination.</span><br>
               <span>⚙️ Select Show Properties.</span>
        </ul>
        <img src="your_image_path_here" alt="IMAGE for WD" style="width:100%;"/>
    </li>
</ul>

<h3>Step 2: Opening the Show Properties Dialog</h3>
<ul>
    <li>
        <strong>Input the Value for <em>Value</em>:</strong>
        <ul>
            <span>  🖊️ Enter the <strong>WBL Workplace Index Score</strong> value.</span><br>
            <span>  ✔️ Press <strong>OK</strong> to confirm your input.</span><br>
        </ul>
    </li>
           <img src="your_image_path_here" alt="IMAGE for WD" style="width:100%;"/>
    </li>
</ul>

<p>📂 <strong>The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder.</strong></p>


<p align="center">
 **IMAGE for WD**
</p>

<h3>Regulatory Frameworks</h3>
<hr style="height: 3px; background-color: grey; border: none;">
<p align="justify"> 
Regulatory Frameworks pertain to laws and policies that protect women’s employment rights, such as childcare support and parental leave, influencing their workforce participation.
This indicator is composed by aggregating the Parenthood and Pay Index scores of the WBL 2024, both standardized on a scale from 0 to 5.
</p>

<h3>Step 1: Accessing the Contextual Dimension</h3>
<ul>
    <li>
        <strong>Locate the Regulatory Frameworks Section:</strong>
        <ul>
               <span>🔍 Right-Click on Regulatory Frameworks.</span><br>
               <span>⚙️ Select Show Properties.</span>
        </ul>
        <img src="your_image_path_here" alt="IMAGE for WD" style="width:100%;"/>
    </li>
</ul>

<h3>Step 2: Opening the Show Properties Dialog</h3>
<ul>
    <li>
        <strong>Input the Value for <em>Value</em>:</strong>
        <ul>
            <span>  🖊️ Enter the <strong>WBL Pay and Parenthood Index Scores</strong> value.</span><br>
            <span>  ✔️ Press <strong>OK</strong> to confirm your input.</span><br>
        </ul>
    </li>
           <img src="your_image_path_here" alt="IMAGE for WD" style="width:100%;"/>
    </li>
</ul>

<p>📂 <strong>The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder.</strong></p>


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
