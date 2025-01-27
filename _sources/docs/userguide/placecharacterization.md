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

> - 2️⃣ Using **Classified Safety data** as input; select the layer and the classification field to be used for processing:
<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Safety_classes.jpg" 
    alt="Safety classes" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 3️⃣ Using **Nighttime Lights data** as input; VIIRS Nighttime Lights raster may be used as proxy data for streetlight locations:
<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Safety_NTL.jpg" 
    alt="Safety NTL" 
    style="width:55%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - 4️⃣ Using **Street lights data** as input; select point locations representing street lights:
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
> - 1️⃣ Using **Point features data** as input; select point locations representing data related to fragility, conflict and violence events; a buffer is needed to estimate the spatial impact of these events, the default radius is 5000m but If the impact radius of an event is known, it should be used instead:

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

