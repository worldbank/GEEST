## Place Characterization

<p align="justify"> 
The Place Characterization Dimension refers to the social, environmental, and infrastructural attributes of geographical locations, such as walkability, safety, and vulnerability to natural hazards. Unlike the Accessibility Dimension, these factors do not involve mobility but focus on the inherent characteristics of a place that influence women’s ability to participate in the workforce. For more information on data input used from open sources, please refer to the <a href="https://worldbank.github.io/GEEST/docs/userguide/datacollection.html" target="_blank">Data Collection section</a>.
</p>

### General Overview

Place Characterization factors refer to the following indicators:

- **Active Transport:** identifies areas based on their ability to support safe and efficient active transport for women, such as walking, cycling, and other non-motorized modes of travel, by analyzing features like street crossings, block lengths, footpaths, and cycle paths.
- **Safety:** defines areas perceived as safe based on specific data or, alternatively, on how brightly lit they are, assuming that brightly lit areas are safer than those with no lights.
- **Fragility, conflict and violence (FCV):** assigns scores to by analyzing overlap with ACLED data with buffers representing various types of events.
- **Education:** computes a raster containing a standardized measure of the percentage of women who have attained higher education in the country/region of interest.
- **Digital Inclusion:** assesses the availability and accessibility of digital infrastructure.
- **Environmental Hazards:** characterizes areas based on their vulnerability to natural disasters.
- **Water sanitation:** assesses the availability and accessibility of clean water and sanitation facilities.

The default <a href="#footnote1" id="ref1">thresholds<sup>1</sup></a> are listed in the footnote.

For certain factors, **multiple data input options** are available depending on the data's format and availability.

### Input Place Characterization factors
---
#### Active Transport

<p align="justify"> 
<strong>Active Transport</strong> refers to the presence of walkable environments and cycling infrastructure, as women often rely on walking or cycling for their daily commutes and errands. This factor is composed by 4 subfactors which provide additional granularity: street crossings | cycly paths | footpaths | block layout.

**Locate Active Transport Section**

> - 🖱️🖱️ **Double-click** on the **Active Transport section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**point features for street crossings, lines for cycle paths and footpaths and polygons for block layout**) corresponding to the indicators by clicking the three-dot button.
> - ⚖️ **Assign Weights**: Assign appropriate weights to reflect the relative importance of each factor in the analysis. Ensure these values are consistent with your project objectives, accurately represent the significance of each factor and add up to 1 for a balanced evaluation.
> - 🚫 **Exclude Unused Factors (optional)**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - 🔄 **Readjust Weights**: After excluding any factors, make sure to **Balance Weights** of the remaining factors. This step ensures the weight distribution remains balanced and totals correctly, preserving the integrity of the analysis.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.


<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ActiveTr.jpg" 
    alt="Active Transport input" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

**Process Active Transport factors**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Active Transport**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ActiveRun.jpg" 
    alt="Active transport run" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

---
#### Safety

<p align="justify"> 
<strong>Safety</strong> addresses the perceived security of public spaces, evaluated through the availability of adequate lighting, which affects women’s ability to move freely, seek employment, and access essential services.
</p>

**Locate Safety Section**

> - 🖱️🖱️ **Double-click** on the **Safety section** to open the pop-up.
> - 📂 **Flexible Data Input Options**: Multiple data input options are available depending on the data's availability, format, or geographic coverage. Select one of the following options:
> - 1️⃣ Using **Perceived Safety data** index score as input:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Safety_index.jpg" 
    alt="Safety index score" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 2️⃣ Using **Classified Safety data** as input; select the layer already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**polygon features**) corresponding to the safety data by clicking the three-dot button and the classification field; this layer will be used for processing:
<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Safety_classes.jpg" 
    alt="Safety classes" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 3️⃣ Using **Nighttime Lights data** as input; VIIRS Nighttime Lights raster may be used as proxy data for streetlight locations; select the layer already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the (**raster data**) corresponding to the streetlights data by clicking the three-dot button; this layer will be used for processing:
<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Safety_NTL.jpg" 
    alt="Safety NTL" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 4️⃣ Using **Street lights data** as input; select the layer already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**point locations**) representing street lights by clicking the three-dot button; this layer will be used for processing:
<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Safety_street.jpg" 
    alt="Safety street lights" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 🚫 **Exclude Unused Factors (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

**Process Safety factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Safety**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Safety_run.jpg" 
    alt="Safety run" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

---
#### FCV

<p align="justify"> 
<strong>Fragility, conflict and violence (FCV)</strong> considers the frequency of events related to political unrest, conflict, and violence in a region, which can increase women’s vulnerability and limit their access to employment and essential services.
</p>

**Locate FCV Section**

> - 🖱️🖱️ **Double-click** on the **FCV section** to open the pop-up.
> - 📂 **Flexible Data Input Options**: Multiple data input options are available depending on the data's availability, format, or geographic coverage. Select one of the following options:
> - 1️⃣ Using **Point features data** as input; select point locations representing data related to fragility, conflict and violence events; a buffer is needed to estimate the spatial impact of these events, the default radius is 5000m but if the impact radius of an event is known, it should be used instead:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/FCV1.jpg" 
    alt="FCV points" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 2️⃣ Using **ACLED data** as input; select ACLED data in CSV format representing fragility, conflict, and violence events; a buffer is required to estimate the spatial impact of these events, with a default radius of 5000m; if the specific impact radius of an event is known, it should be applied instead; a pop-up will appear to validate the CSV format.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/FCV2.jpg" 
    alt="FCV csv data" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 🚫 **Exclude Unused Factor (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

**Process FCV factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **FCV**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/FCVrun.jpg" 
    alt="FCV run" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

---
#### Education

<p align="justify"> 
<strong>Education</strong> refers to the proportion of women in a region who have attained higher education, particularly in the specific field of analysis, serving as an indicator of societal attitudes towards women working in that sector.
</p>

**Locate Education Section**

> - 🖱️🖱️ **Double-click** on the **Education section** to open the pop-up.
> - 📂 **Flexible Data Input Options**: Multiple data input options are available depending on the data's availability, format, or geographic coverage. Select one of the following options:
> - 1️⃣ Using **Index score** at the national or regional level, based on the proportion of women who have attained higher education as input: 

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Edu_index.jpg" 
    alt="Education index score" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 2️⃣ Using **Classify Polygon Into Classes data** as input; select the layer already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**polygon features**) corresponding to the education data by clicking the three-dot button then, select the classification field to be used for processing:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Edu_class.jpg" 
    alt="Education classified polygons data" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 🚫 **Exclude Unused Factor (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

**Process Education factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Education**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Edu_run.jpg" 
    alt="Education run" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

---
#### Digital Inclusion

<p align="justify"> 
<strong>Digital Inclusion</strong> assesses the presence of digital infrastructure in a specific location, which is essential for women to pursue job opportunities, access training and education opportunities, and use financial services.
</p>

**Locate Digital Inclusion Section**

> - 🖱️🖱️ **Double-click** on the **Digital Inclusion section** to open the pop-up.
> - 📂 **Flexible Data Input Options**: Multiple data input options are available depending on the data's availability, format, or geographic coverage. Select one of the following options:
> - 1️⃣ Using **Index score** at the national or regional level, based on the proportion of available digital infrastructure as input: 

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/DIG_index.jpg" 
    alt="Digital Inclusion index score" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 2️⃣ Using **Classify Polygon Into Classes data** as input; select the layer already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**polygon features**) corresponding to the digital inclusion data by clicking the three-dot button then, select the classification field to be used for processing:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/DIG_class.jpg" 
    alt="Digital Inclusion classified polygons data" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 🚫 **Exclude Unused Factor (optional)**: If this factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

**Process Digital Inclusion factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Digital Inclusion**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/DIG_run.jpg" 
    alt="Digital Inclusion run" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

---
#### Environmental Hazards

<p align="justify"> 
<strong>Environmental Hazards</strong> relate to the impact of environmental risks, such as floods, droughts, landslides, fires and extreme weather events, which can disrupt job stability, particularly for women in vulnerable sectors.
</p>

<p align="justify">
This factor is composed, by default, of five subfactors representing different types of hazards: fires, floods, landslides, tropical cyclones and droughts. These subfactors are aggregated into a single factor, referred to as Environmental Hazards, based on the selected weights assigned to each subfactor.

If data for one or more hazard types is not available, these subfactors can be excluded from the processing. In such cases, the tool will automatically adjust the weights of the remaining subfactors to ensure accurate aggregation.

The thresholds for defining hazard levels are based on a predefined scoring list (**provided in the footnote**). The input data relies on globally available open data sources and is reclassified for use within the tool. However, if more precise and localized data is available, users are encouraged to incorporate it into the processing. In doing so, users should align the data with the thresholds provided to maintain consistency and reliability.
</p>

**Locate Environmental Hazards Section**

> - 🖱️🖱️ **Double-click** on the **Environmental Hazards section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the **raster features** corresponding to the indicators by clicking the three-dot button.
> - ⚖️ **Assign Weights**: Assign appropriate weights to reflect the relative importance of each factor in the analysis. Ensure these values are consistent with your project objectives, accurately represent the significance of each factor and add up to 1 for a balanced evaluation.
> - 🚫 **Exclude Unused Factors (optional)**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - 🔄 **Readjust Weights**: After excluding any factors, make sure to **Balance Weights** of the remaining factors. This step ensures the weight distribution remains balanced and totals correctly, preserving the integrity of the analysis.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ENV_select.jpg" 
    alt="Environmental Hazards data input" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

**Process Environmental Hazards factors**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Environmental Hazards**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ENV_run.jpg" 
    alt="Environmental Hazards run" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

---
#### Water sanitation

<p align="justify"> 
<strong>Water sanitation</strong> concerns the availability of clean water and sanitation facilities, affecting women’s time allocation and capacity to engage in employment.
</p>

**Locate Water sanitation Section**

> - 🖱️🖱️ **Double-click** on the **Water sanitation section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**point features**) corresponding to the water and sanitation facilities by clicking the three-dot button; a buffer is needed to estimate the spatial impact of these facilities, the default radius is set to 1000 meters; however, this value can be adjusted based on the user's considerations.
> - 🚫 **Exclude Unused Factor (optional)**: If this specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - ✅ **Finalize**: Once all settings are configured, click OK to confirm and proceed to the next step.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Water_select.jpg" 
    alt="Water sanitation input" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

**Process Water sanitation factor**

Back in the Data Processing Interface:

> - 🖱️ **Right-click** on **Water sanitation**.  
> - ▶️ **Select "Run Item Workflow"** from the context menu to initiate the process.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Water_run.jpg" 
    alt="Water run" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

---
**Additional Steps Before Processing**: 

> - 🖱️🖱️ **Double-click** on the **Place Characterization section** to open the pop-up.
> - ⚖️ **Assign Weights**: Ensure the **weights** are correctly assigned, as they determine the relative importance of each factor in the analysis. Carefully review these values to ensure they are aligned with your project's objectives and reflect the significance of each factor accurately.
> - 🚫 **Exclude Unused Factors (optional)**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - 🔄 **Readjust Weights**: After excluding any factors, make sure to **Balance Weights** of the remaining factors. This step ensures the weight distribution remains balanced and totals correctly, preserving the integrity of the analysis, then click **OK** to proceed.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/PC_weights.jpg" 
    alt="Place Characterization Weights" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

### Process Place Characterization factors
---
After configuring the factors and adjusting their weights to achieve balance, you can initiate the process workflow:

> - 🖱️**Right-click on Place Characterization**.  
> - ▶️**Select Run Item Workflow** from the context menu.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/PC_run.jpg" 
    alt="Place Characterization Run" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The process should be successfully completed and indicated by a green checkmark widget.

### Visualizing the Outputs 
---
After completing the process, the outputs are automatically added to the Layer Panel in QGIS as a group layer. This group layer has the *Mutually Exclusive Group* feature activated, which ensures that only one layer within the group can be visible at a time. When this feature is enabled, turning on the visibility of one layer automatically turns off the visibility of the others within the same group, making it easier to compare results without overlapping visualizations.

The outputs consist of all factors and subfactors, as well as the aggregation of these into the final Place Characterization output. All scores are assessed on a scale from 0 to 5, categorized as follows: ≤ 0.5 (Not Enabling) | 0.5–1.5 (Very Low Enablement) | 1.5–2.5 (Low Enablement) | 2.5–3.5 (Moderately Enabling) | 3.5–4.5 (Enabling) | 4.5–5.0 (Highly Enabling).

<span style="color: red;">[Not working - Need to be amended]</span>

The outputs are stored under the Place Characterization folder within the project folder created during the setup phase as raster files. These files can be shared and further utilized for various purposes, such as visualization in QGIS or other GIS software, integration into reports, overlaying with other spatial datasets, or performing advanced geospatial analyses, such as identifying priority areas or conducting trend analysis based on the scores.

If the results do not immediately appear in the Layer Panel after processing the Place Characterization Dimension, you can resolve this by either adding them manually from the folder path or by right-clicking on the Place Characterization Dimension and selecting **Add to map** from the context menu:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/PC_add.jpg" 
    alt="Place Characterization Add to map" 
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
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/PC_rerun.jpg" 
    alt="Place Characterization Clear and rerun" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

### Key Considerations
---
- **Input Accuracy**: Ensure all input datasets are carefully entered/selected and correspond to the correct factors and/or subfactors. Incorrect data will impact the outputs and subsequent analysis.

- **Weight Adjustment**: Assign weights thoughtfully to reflect the importance of each factor in the overall analysis. After making changes, always balance the weights to ensure they sum up correctly.
  
<small>
    <a id="footnote1" href="#ref1">1</a>: <span style="color: #505050;"><strong>Default thresholds</strong> </span>
 <br>
 <span style="color: #505050;">
 <strong>Active transport</strong> factor is calculated based on four factors averaged across the raster cells:
    <br>
    <em>Street Crossings scores</em>: (score 0 = none, score 3 = 1 crossing, score 5 = 2+ crossings)<br>
    <em>Cycle Paths scores</em>: (score 0 = none, score 3 = 1 cycle path, score 5 = 2+ paths)<br>
    <em>Footpaths scores</em>: (score 0 = none, score 3 = 1 path, score 5 = 2+ paths)<br>
    <em>Block Sizes scores</em>: (score 0 = none, score 1 = >1 km, score 2 = 751m-1 km, score 3 = 501m-750m, score 4 = 251m-500m, score 5 = <250m)<br>
    <br>
    <strong>Safety</strong> is calculated by generating 20-meter buffers around streetlights. Raster cells where 80-100% of their area intersects with these buffers are assigned a <em>score of 5</em>. Cells with 60-79% intersection receive a <em>score of 4</em>, 40-59% a <em>score of 3</em>, 20-39% a <em>score of 2</em>, and 1-19% a <em>score of 1</em>. Cells with no overlap are <em>scored as 0</em>. <strong>Note:</strong> Use nighttime light data only if streetlight data is unavailable.
    <br><br>
    <strong>FCV</strong> is structured by assigning scores to raster cells based on their overlap with buffers representing different types of events. Using point locations of FCV (Fragility, Conflict, and Violence) events, create circular buffers with a radius of 5 km to estimate the spatial impact. If a specific event's impact radius is known, it should be applied instead. Raster cells intersecting with these buffers are scored as follows:
    <ul>
        <li>Rasters overlapping with buffers for battles and explosions: <em>score 0</em></li>
        <li>Rasters overlapping with buffers for explosions and remote violence: <em>score 1</em></li>
        <li>Rasters overlapping with buffers for violence against civilians: <em>score 2</em></li>
        <li>Rasters overlapping with buffers for protests and riots: <em>score 4</em></li>
        <li>Areas with no overlap with any event: <em>score 5</em></li>
    </ul>
    <br>
    <strong>Education</strong> reclassifies the input data to a standardized scale from 0 to 5 using a linear scaling process. In this scale, a <em>score of 5</em> represents areas where all women have a university degree, while a <em>score of 0</em> represents areas where no women have a university degree.
    <br><br>
    <strong>Digital Inclusion</strong> reclassifies input data to a standardized scale of 0 to 5 using a linear scaling process, where <em>5</em> represents areas where 100% of households have internet access, and <em>0</em> represents areas where no households have internet access.
    <br><br>
    <strong>Environmental Hazards</strong> reclassifies input data to a standardized scale of 0 to 5 using a linear scaling process, where <em>5</em> represents areas with no environmental hazards and <em>0</em> represents areas with the highest level of hazard.
<br><br>
<em>Number of Fires per km²</em> is classified into GEEST classes as follows: 0 or No Data: <em>class 5</em> | 0 to 1: <em>class 4</em> | 1 to 2: <em>class 3</em> | 2 to 5: <em>class 2</em> | 5 to 8: <em>class 1</em> | Greater than 8: <em>class 0</em>
<br>
<em>Floods data</em> is classified into GEEST classes as follows: No Data or 0: <em>class 5</em> | Less than 180 cm: <em>class 4</em> | 180–360 cm: <em>class 3</em> | 360–540 cm: <em>class 2</em> | 540–720 cm: <em>class 1</em> | 720–900 cm: <em>class 0</em>
<br>
<em>Landslide data</em> is classified into GEEST classes as follows: No Data or 0: <em>class 5</em> | Slight (1): <em>class 4</em> | Low Moderate1 (2): <em>class 3</em> | Moderate (3): <em>class 2</em> | High-Moderate2 (4): <em>class 1</em> | Severe (5): <em>class 0</em>
<br>
<em>Tropical Cyclone frequency per 100 years</em> is classified into GEEST classes as follows: No Data or 0: <em>class 5</em> | Less than 25 events: <em>class 4</em> | 25–50 events: <em>class 3</em> | 50–75 events: <em>class 2</em> | 75–100 events: <em>class 1</em> | More than 100 events: <em>class 0</em>
<br>     
<em>Drought data</em> is classified into GEEST classes as follows: No Data or 0: <em>class 5</em> | 0–1: <em>class 4</em> | 1–2: <em>class 3</em> | 2–3: <em>class 2</em> | 3–4: <em>class 1</em> | 4–5: <em>class 0</em>
    <br><br>
    <strong>Water Sanitation</strong> is assessed based on the presence of water and sanitation facilities within a raster cell, applying a default 1000m buffer. The scoring is as follows:
    <ul>
        <li>Raster cell with no water points: <em>score 0</em></li>
        <li>Raster cell with 1 water point: <em>score 3</em></li>
        <li>Raster cell with 2 or more water points: <em>score 5</em></li>
    </ul>
     </span>
</small>
