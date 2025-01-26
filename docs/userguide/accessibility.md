## Accessibility

<p align="justify"> 
The Accessibility Dimension evaluates women’s daily mobility by examining their access to essential services. Levels of enablement for work access in this dimension are determined by service areas, which represent the geographic zones that facilities like childcare, supermarkets, universities, banks, and clinics can serve based on proximity. The nearer these facilities are to where women live, the more supportive and enabling the environment becomes for their participation in the workforce. For more information on data input used from open sources, please refer to the <a href="https://worldbank.github.io/GEEST/docs/userguide/datacollection.html" target="_blank">Data Collection section</a>.
</p>

### General Overview
---
This tool evaluates how easily women can access essential services and amenities, considering their caregiving roles and daily travel needs. It uses geospatial area analysis with Openrouteservices (ORS) and OpenStreetMap (OSM) data to measure accessibility for several factors, including:

- **Women’s Travel Patterns:** Access to everyday services like pharmacies, markets, supermarkets, childcare centers, schools and parks.
- **Access to Public Transport:** Proximity to bus stops, train stations, and other transport facilities.
- **Health Facilities:** Availability of clinics, hospitals, and other healthcare services.
- **Education and Training Facilities:** Distance to colleges, universities and other training centers.
- **Financial Facilities:** Access to banks and financial support institutions.

The process generates zones around these amenities, showing how far women can travel on foot or by car within increasing distances or times. Each zone is assigned a score from 5 (most accessible) to 0 (not accessible), reflecting decreasing accessibility as distance or travel time increases.

### Input Accessibility factors
---
#### Women’s Travel Patterns (WTP)
<p align="justify"> 
<strong>Women’s Travel Patterns (WTP)</strong> refer to the unique travel behaviors of women, often involving multiple stops for household or caregiving tasks, making proximity to essential services like markets, supermarkets, childcare centers, primary schools, pharmacies, and green spaces crucial. This factor is composed by 5 subfactors which provide additional granularity: kindergartens/childcare | primary schools | groceries | pharmacies | green spaces. which is then standardized on a scale from 0 to 5.

---    
For **Women’s Travel Patterns**, the tool focuses on essential services such as markets, supermarkets, childcare centers, primary schools, pharmacies, and parks. Walking is often the default travel mode and the following thresholds are loaded by default based on evidence based on literature:

- **0 to 400 meters:** Score = 5 (high accessibility)
- **401 to 800 meters:** Score = 4
- **801 to 1200 meters:** Score = 3
- **1201 to 1500 meters:** Score = 2
- **1501 to 2000 meters:** Score = 1
- **Over 2000 meters:** Score = 0 (no accessibility)

---

💡 **Tip**: If evidence from the local context suggests alternative thresholds and increments are more appropriate, the user can alter these increments. If the selected travel mode is driving, the equivalent measurement increments should be in minutes and informed by the local context (for example, if evidence suggests the maximum time that women spend driving is 30 minutes, the increments could be 6, 12, 18, 24, 30).

---

**Locate Women's Travel Patterns Section**

> - 🖱️🖱️ **Double-click** on the **Women's Travel Patterns section** to open the pop-up.
> - 📝 In the *Input* field, you can select layers already loaded in the QGIS Layer Panel from the dropdown menu or manually enter the file path for the shapefiles (**point features**) corresponding to the indicators by clicking the three-dot button.
> - 🔧 **Optional**: Change the travel mode from walking to driving and the measurements from meters to minutes and amend the default thresholds if local context suggests more appropriate increments.
> - ⚖️ **Assign Weights**: Assign appropriate weights to reflect the relative importance of each factor in the analysis. Ensure these values are consistent with your project objectives, accurately represent the significance of each factor and add up to 1 for a balanced evaluation.
> - 🚫 **Exclude Unused Factors**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
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
<strong>Access to Public Transport</strong> focuses on the availability and proximity of public transportation stops, which is crucial for women, especially those who rely on buses, trains, or trams to access jobs, education, and essential services.

---



