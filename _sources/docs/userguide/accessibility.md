## Accessibility

<p align="justify"> 
The Accessibility Dimension evaluates women’s daily mobility by examining their access to essential services. Levels of enablement for work access in this dimension are determined by service areas, which represent the geographic zones that facilities like childcare, supermarkets, universities, banks, and clinics can serve based on proximity. The nearer these facilities are to where women live, the more supportive and enabling the environment becomes for their participation in the workforce. For more information on data input used from open sources, please refer to the <a href="https://worldbank.github.io/GEEST/docs/userguide/datacollection.html" target="_blank">Data Collection section</a>.
</p>

### General Overview
---
This tool evaluates how easily women can access essential services and amenities, considering their caregiving roles and daily travel needs. It uses geospatial area analysis with Openrouteservices (ORS) and OpenStreetMap (OSM) data to measure accessibility for several factors, including:

- **Women’s Travel Patterns:** Access to everyday services like pharmacies, markets, supermarkets, childcare centers, schools and parks.
- **Access to Public Transport:** Proximity to bus stops, train stations and other transport facilities.
- **Health Facilities:** Availability of clinics, hospitals and other healthcare services.
- **Education and Training Facilities:** Distance to colleges, universities and other training centers.
- **Financial Facilities:** Access to banks and financial support institutions.

**Travel mode**: The user can select walking or driving as a travel mode, and it is recommended that the same travel mode should be selected for all accessibility factors. The default travel mode is walking due to its inclusive nature.

**Measurement**: The default measurement for travel is distance in meters, which is most appropriate for walking. These thresholds are based on evidence from the literature at the factor level and are designed to provide consistency across analyses. If driving is selected as a travel mode, time in minutes is a more appropriate measurement.

---

💡 **Tip**: If evidence from the local context suggests alternative thresholds and increments are more appropriate, the user can alter these increments. If the selected travel mode is driving, the equivalent measurement increments should be in minutes and informed by the local context (for example, if evidence suggests the maximum time that women spend driving is 30 minutes, the increments could be 6, 12, 18, 24, 30).

---

**Output**: The process generates zones around these amenities, showing how far women can travel on foot or by car within increasing distances or times. Each zone is assigned a score from 5 (high accessibility) to 0 (no accessibility), reflecting decreasing accessibility as distance or travel time increases.

### Input Accessibility factors
---
#### Women’s Travel Patterns (WTP)
<p align="justify"> 
<strong>Women’s Travel Patterns (WTP)</strong> refer to the unique travel behaviors of women, often involving multiple stops for household or caregiving tasks, making proximity to essential services like markets, supermarkets, childcare centers, primary schools, pharmacies and green spaces crucial. This factor is composed by 5 subfactors which provide additional granularity: kindergartens/childcare | primary schools | groceries | pharmacies | green spaces.

**Locate Women's Travel Patterns Section**

> - 🖱️🖱️ **Double-click** on the **Women's Travel Patterns section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**point features**) corresponding to the indicators by clicking the three-dot button.
> - 🔧 **Travel mode (optional)**: Change the travel mode from walking to driving and the measurements from meters to minutes and amend the default thresholds if local context suggests more appropriate increments.
> - ⚖️ **Assign Weights**: Assign appropriate weights to reflect the relative importance of each factor in the analysis. Ensure these values are consistent with your project objectives, accurately represent the significance of each factor and add up to 1 for a balanced evaluation.
> - 🚫 **Exclude Unused Factors (optional)**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - 🔄 **Readjust Weights**: After excluding any factors, make sure to **Balance Weights** of the remaining factors. This step ensures the weight distribution remains balanced and totals correctly, preserving the integrity of the analysis.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/WTP%20input.jpg" 
    alt="WTP input" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

<strong>Default</strong> Women's Travel Patterns thresholds:

<table style="width:auto; border:1px solid black; border-collapse:collapse; margin-left:0; font-size:12px;">
  <tr style="border:1px solid black;">
    <th style="border:1px solid black; width:250px;">Distance to Facilities (meters)</th>
    <th style="border:1px solid black; width:80px; text-align:center;">Score</th>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">0 - 400</td>
    <td style="border:1px solid black; text-align:center;">5</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">401 - 800</td>
    <td style="border:1px solid black; text-align:center;">4</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">801 - 1,200</td>
    <td style="border:1px solid black; text-align:center;">3</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">1,201 - 1,500</td>
    <td style="border:1px solid black; text-align:center;">2</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">1,501 - 2,000</td>
    <td style="border:1px solid black; text-align:center;">1</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">Over 2,000</td>
    <td style="border:1px solid black; text-align:center;">0</td>
  </tr>
</table>

<br>

**Process Women's Travel Patterns factors**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Women's Travel Patterns**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.  


<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/WTP%20run.jpg" 
    alt="WTP run" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/WTP%20success.jpg" 
    alt="WTP success" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

---
#### Access to Public Transport

<p align="justify"> 
<strong>Access to Public Transport</strong> focuses on the availability and proximity of public transportation stops, which is crucial for women, especially those who rely on buses, trains, or trams to access jobs, education, and essential services.
</p>

**Locate Access to Public Transport Section**

> - 🖱️🖱️ **Double-click** on the **Access to Public Transport section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefile (**point features**) corresponding to the **Location of public transportation stops, including maritime** by clicking the three-dot button.
> - 🔧 **Travel mode (optional)**: Change the travel mode from walking to driving and the measurements from meters to minutes and amend the default thresholds if local context suggests more appropriate increments.
> - 🚫 **Exclude Factor (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/APT.jpg" 
    alt="APT input" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

<strong>Default</strong> Access to Public Transport thresholds:

<table style="width:auto; border:1px solid black; border-collapse:collapse; margin-left:0; font-size:12px;">
  <tr style="border:1px solid black;">
    <th style="border:1px solid black; width:250px;">Distance to Public Transport stops (meters)</th>
    <th style="border:1px solid black; width:80px; text-align:center;">Score</th>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">0 - 250</td>
    <td style="border:1px solid black; text-align:center;">5</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">251 - 500</td>
    <td style="border:1px solid black; text-align:center;">4</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">501 - 750</td>
    <td style="border:1px solid black; text-align:center;">3</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">751 - 1,000</td>
    <td style="border:1px solid black; text-align:center;">2</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">1,001 - 1,250</td>
    <td style="border:1px solid black; text-align:center;">1</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">Over 1,250</td>
    <td style="border:1px solid black; text-align:center;">0</td>
  </tr>
</table>

<br>

**Process Access to Public Transport factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Access to Public Transport**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/APT%20run.jpg" 
    alt="APT run" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The process should be successfully completed and indicated by a green checkmark widget.


---
#### Access to Health Facilities 

<p align="justify"> 
<strong>Access to Health Facilities</strong> evaluates how easily women can reach healthcare services in terms of distance, impacting their well-being and ability to participate in the workforce.
</p>

**Locate Access to Health Facilities Section**

> - 🖱️🖱️ **Double-click** on the **Access to Health Facilities section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefile (**point features**) corresponding to the **Location of hospitals and clinics** by clicking the three-dot button.
> - 🔧 **Travel mode (optional)**: Change the travel mode from walking to driving and the measurements from meters to minutes and amend the default thresholds if local context suggests more appropriate increments.
> - 🚫 **Exclude Factor (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.


<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/AHF.jpg" 
    alt="AHF input" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

<strong>Default</strong> Access to Health Facilities thresholds:

<table style="width:auto; border:1px solid black; border-collapse:collapse; margin-left:0; font-size:12px;">
  <tr style="border:1px solid black;">
    <th style="border:1px solid black; width:250px;">Distance to Health Facilities (meters)</th>
    <th style="border:1px solid black; width:80px; text-align:center;">Score</th>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">0 - 2,000</td>
    <td style="border:1px solid black; text-align:center;">5</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">2,001 - 4,000</td>
    <td style="border:1px solid black; text-align:center;">4</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">4,001 - 6,000</td>
    <td style="border:1px solid black; text-align:center;">3</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">6,001 - 8,000</td>
    <td style="border:1px solid black; text-align:center;">2</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">8,001 - 10,000</td>
    <td style="border:1px solid black; text-align:center;">1</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">Over 10,000</td>
    <td style="border:1px solid black; text-align:center;">0</td>
  </tr>
</table>

<br>

**Process Access to Health Facilities factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Access to Health Facilities**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

The process should be successfully completed and indicated by a green checkmark widget.

---
#### Access to Education and Training Facilities 

<p align="justify"> 
<strong>Access to Education and Training Facilities</strong> assesses the proximity to higher education institutions and training centers, influencing women’s ability to gain necessary qualifications.
</p>

**Locate Access to Education and Training Facilities Section**

> - 🖱️🖱️ **Double-click** on the **Access to Education and Training Facilities section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefile (**point features**) corresponding to the **Location of universities and technical schools** by clicking the three-dot button.
> - 🔧 **Travel mode (optional)**: Change the travel mode from walking to driving and the measurements from meters to minutes and amend the default thresholds if local context suggests more appropriate increments.
> - 🚫 **Exclude Factor (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/AET.jpg" 
    alt="AET input" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

<strong>Default</strong> Access to Education and Training Facilities thresholds:

<table style="width:auto; border:1px solid black; border-collapse:collapse; margin-left:0; font-size:12px;">
  <tr style="border:1px solid black;">
    <th style="border:1px solid black; width:250px;">Distance to Facilities (meters)</th>
    <th style="border:1px solid black; width:80px; text-align:center;">Score</th>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">0 - 2,000</td>
    <td style="border:1px solid black; text-align:center;">5</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">2,001 - 4,000</td>
    <td style="border:1px solid black; text-align:center;">4</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">4,001 - 6,000</td>
    <td style="border:1px solid black; text-align:center;">3</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">6,001 - 8,000</td>
    <td style="border:1px solid black; text-align:center;">2</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">8,001 - 10,000</td>
    <td style="border:1px solid black; text-align:center;">1</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">Over 10,000</td>
    <td style="border:1px solid black; text-align:center;">0</td>
  </tr>
</table>

<br>

**Process Access to Education and Training Facilities factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Access to Education and Training Facilities**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

The process should be successfully completed and indicated by a green checkmark widget.

---
#### Access to Financial Facilities 

<p align="justify"> 
<strong>Access to Financial Facilities</strong> focuses on the proximity of banks and financial institutions, which is essential for women’s economic empowerment and ability to access credit.
</p>

**Locate Access to Financial Facilities Section**

> - 🖱️🖱️ **Double-click** on the **Access to Financial Facilities section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefile (**point features**) corresponding to the **Location of banks and other financial facilities** by clicking the three-dot button.
> - 🔧 **Travel mode (optional)**: Change the travel mode from walking to driving and the measurements from meters to minutes and amend the default thresholds if local context suggests more appropriate increments.
> - 🚫 **Exclude Factor (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/AFF.jpg" 
    alt="AFF input" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

<strong>Default</strong> Access to Financial Facilities thresholds:

<table style="width:auto; border:1px solid black; border-collapse:collapse; margin-left:0; font-size:12px;">
  <tr style="border:1px solid black;">
    <th style="border:1px solid black; width:250px;">Distance to Financial Facilities (meters)</th>
    <th style="border:1px solid black; width:80px; text-align:center;">Score</th>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">0 - 400</td>
    <td style="border:1px solid black; text-align:center;">5</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">401 - 800</td>
    <td style="border:1px solid black; text-align:center;">4</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">801 - 1,200</td>
    <td style="border:1px solid black; text-align:center;">3</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">1,201 - 2,000</td>
    <td style="border:1px solid black; text-align:center;">2</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">2,001 - 3,000</td>
    <td style="border:1px solid black; text-align:center;">1</td>
  </tr>
  <tr style="border:1px solid black;">
    <td style="border:1px solid black;">Over 3,000</td>
    <td style="border:1px solid black; text-align:center;">0</td>
  </tr>
</table>

<br>

**Process Access to Financial Facilities factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Access to Financial Facilities**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

The process should be successfully completed and indicated by a green checkmark widget.

---
**Additional Steps Before Processing**: 

> - 🖱️🖱️ **Double-click** on the **Accessibility section** to open the pop-up.
> - ⚖️ **Assign Weights**: Ensure the **weights** are correctly assigned, as they determine the relative importance of each factor in the analysis. Carefully review these values to ensure they are aligned with your project's objectives and reflect the significance of each factor accurately.
> - 🚫 **Exclude Unused Factors (optional)**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - 🔄 **Readjust Weights**: After excluding any factors, make sure to **Balance Weights** of the remaining factors. This step ensures the weight distribution remains balanced and totals correctly, preserving the integrity of the analysis, then click **OK** to proceed.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ACC%20weights.jpg" 
    alt="Accessibility Weights" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>


### Process Accessibility factors
---
After configuring the factors and adjusting their weights to achieve balance, you can initiate the process workflow:

> - 🖱️**Right-click on Accessibility**.  
> - ▶️**Select Run Item Workflow** from the context menu.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ACC%20run.jpg" 
    alt="Accessibility Run" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The process should be successfully completed and indicated by a green checkmark widget.

### Visualizing the Outputs 
---
After completing the process, the outputs are automatically added to the Layer Panel in QGIS as a group layer. This group layer has the *Mutually Exclusive Group* feature activated, which ensures that only one layer within the group can be visible at a time. When this feature is enabled, turning on the visibility of one layer automatically turns off the visibility of the others within the same group, making it easier to compare results without overlapping visualizations.

The outputs consist of all factors and subfactors, as well as the aggregation of these into the final Accessibility output. All scores are assessed on a scale from 0 to 5, categorized as follows: ≤ 0.5 (Not Enabling) | 0.5–1.5 (Very Low Enablement) | 1.5–2.5 (Low Enablement) | 2.5–3.5 (Moderately Enabling) | 3.5–4.5 (Enabling) | 4.5–5.0 (Highly Enabling).

The outputs are stored under the Accessibility folder within the project folder created during the setup phase as raster files. These files can be shared and further utilized for various purposes, such as visualization in QGIS or other GIS software, integration into reports, overlaying with other spatial datasets, or performing advanced geospatial analyses, such as identifying priority areas or conducting trend analysis based on the scores.

If the results do not immediately appear in the Layer Panel after processing the Accessibility Dimension, you can resolve this by either adding them manually from the folder path or by right-clicking on the Accessibility Dimension and selecting **Add to map** from the context menu:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ACC%20add.jpg" 
    alt="Accessibility Add to map" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> 💡 **Tip**: If the input needs to be changed for any reason (e.g., incorrect initial input), you can clear the results and reprocess them as follows:
> - 🖱️ **Right-click** on the factor/dimension and select **Clear Item**.  
> - 🖱️ **Right-click again** on the same cleared factor/dimension, and while holding the **SHIFT** key on your keyboard, select **Run Item Workflow**.
> This process ensures that the tool reassesses the input datasets and outputs the corrected scores.


<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ACC%20rerun.jpg" 
    alt="Accessibility Clear and rerun" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

### Key Considerations
---
- **Input Accuracy**: Ensure all input datasets are carefully entered/selected and correspond to the correct factors and/or subfactors. Incorrect data will impact the outputs and subsequent analysis.

- **Weight Adjustment**: Assign weights thoughtfully to reflect the importance of each factor in the overall analysis. After making changes, always balance the weights to ensure they sum up correctly.
