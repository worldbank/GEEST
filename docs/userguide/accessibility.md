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

Travel mode: The user can select walking or driving as a travel mode, and it is recommended that the same travel mode should be selected for all accessibility factors. The default travel mode is walking due to its inclusive nature.

Measurement: The default measurement for travel is distance in meters, which is most appropriate for walking. These <a href="#footnote1" id="ref1">thresholds<sup>1</sup></a> are based on evidence from the literature at the factor level and are designed to provide consistency across analyses. If driving is selected as a travel mode, time in minutes is a more appropriate measurement.

---

💡 **Tip**: If evidence from the local context suggests alternative thresholds and increments are more appropriate, the user can alter these increments. If the selected travel mode is driving, the equivalent measurement increments should be in minutes and informed by the local context (for example, if evidence suggests the maximum time that women spend driving is 30 minutes, the increments could be 6, 12, 18, 24, 30).

---

Output: The process generates zones around these amenities, showing how far women can travel on foot or by car within increasing distances or times. Each zone is assigned a score from 5 (high accessibility) to 0 (no accessibility), reflecting decreasing accessibility as distance or travel time increases.

### Input Accessibility factors
---
#### Women’s Travel Patterns (WTP)
<p align="justify"> 
<strong>Women’s Travel Patterns (WTP)</strong> refer to the unique travel behaviors of women, often involving multiple stops for household or caregiving tasks, making proximity to essential services like markets, supermarkets, childcare centers, primary schools, pharmacies and green spaces crucial. This factor is composed by 5 subfactors which provide additional granularity: kindergartens/childcare | primary schools | groceries | pharmacies | green spaces. These are standardized on a scale from 0 to 5.

---    
For **Women’s Travel Patterns**, the tool emphasizes essential services and walking is typically set as the default travel mode, with the following thresholds preloaded based on evidence from the literature:

- **0 to 400 meters:** Score = 5 (high accessibility)
- **401 to 800 meters:** Score = 4
- **801 to 1200 meters:** Score = 3
- **1201 to 1500 meters:** Score = 2
- **1501 to 2000 meters:** Score = 1
- **Over 2000 meters:** Score = 0 (no accessibility)



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

Walking is typically set as the default travel mode, with the following thresholds preloaded based on evidence from the literature:

- **0 to 250 meters:** Score = 5 (high accessibility)
- **251 to 500 meters:** Score = 4
- **501 to 750 meters:** Score = 3
- **751 to 1000 meters:** Score = 2
- **1001 to 1250 meters:** Score = 1
- **Over 1250 meters:** Score = 0 (no accessibility)








<small><a href="#ref1" id="footnote1"><sup>1</sup> Thresholds

| **Factor**                                | **Distance**               | **Score** |
|-------------------------------------------|----------------------------|-----------|
| <small>**Women's Travel Patterns**</small>               | <small>0 to 400 meters</small>            | <small>5</small>         |
|                                           | <small>401 to 800 meters</small>          | <small>4</small>         |
|                                           | <small>801 to 1200 meters</small>         | <small>3</small>         |
|                                           | <small>1201 to 1500 meters</small>        | <small>2</small>         |
|                                           | <small>1501 to 2000 meters</small>        | <small>1</small>         |
|                                           | <small>Over 2000 meters</small>           | <small>0</small>         |
| <small>**Access to Public Transport**</small>            | <small>0 to 250 meters</small>            | <small>5</small>         |
|                                           | <small>251 to 500 meters</small>          | <small>4</small>         |
|                                           | <small>501 to 750 meters</small>          | <small>3</small>         |
|                                           | <small>751 to 1,000 meters</small>        | <small>2</small>         |
|                                           | <small>1,001 to 1,250 meters</small>      | <small>1</small>         |
|                                           | <small>Over 1,250 meters</small>          | <small>0</small>         |
| <small>**Access to Health Facilities**</small>           | <small>0 to 2,000 meters</small>          | <small>5</small>         |
|                                           | <small>2,001 to 4,000 meters</small>      | <small>4</small>         |
|                                           | <small>4,001 to 6,000 meters</small>      | <small>3</small>         |
|                                           | <small>6,001 to 8,000 meters</small>      | <small>2</small>         |
|                                           | <small>8,001 to 10,000 meters</small>     | <small>1</small>         |
|                                           | <small>Over 10,000 meters</small>         | <small>0</small>         |
| <small>**Access to Education and Training Facilities**</small> | <small>0 to 2,000 meters</small>          | <small>5</small>         |
|                                           | <small>2,001 to 4,000 meters</small>      | <small>4</small>         |
|                                           | <small>4,001 to 6,000 meters</small>      | <small>3</small>         |
|                                           | <small>6,001 to 8,000 meters</small>      | <small>2</small>         |
|                                           | <small>8,001 to 10,000 meters</small>     | <small>1</small>         |
|                                           | <small>Over 10,000 meters</small>         | <small>0</small>         |
| <small>**Access to Financial Facilities**</small>        | <small>0 to 400 meters</small>            | <small>5</small>         |
|                                           | <small>401 to 800 meters</small>          | <small>4</small>         |
|                                           | <small>801 to 1,200 meters</small>        | <small>3</small>         |
|                                           | <small>1,201 to 2,000 meters</small>      | <small>2</small>         |
|                                           | <small>2,001 to 3,000 meters</small>      | <small>1</small>         |
|                                           | <small>Over 3,000 meters</small>          | <small>0</small>         |




| **Factor**                                | **Distance**               | **Score** |
|-------------------------------------------|----------------------------|-----------|
| **Women's Travel Patterns**               | 0 to 400 meters            | 5         |
|                                           | 401 to 800 meters          | 4         |
|                                           | 801 to 1200 meters         | 3         |
|                                           | 1201 to 1500 meters        | 2         |
|                                           | 1501 to 2000 meters        | 1         |
|                                           | Over 2000 meters           | 0         |
| **Access to Public Transport**            | 0 to 250 meters            | 5         |
|                                           | 251 to 500 meters          | 4         |
|                                           | 501 to 750 meters          | 3         |
|                                           | 751 to 1,000 meters        | 2         |
|                                           | 1,001 to 1,250 meters      | 1         |
|                                           | Over 1,250 meters          | 0         |
| **Access to Health Facilities**           | 0 to 2,000 meters          | 5         |
|                                           | 2,001 to 4,000 meters      | 4         |
|                                           | 4,001 to 6,000 meters      | 3         |
|                                           | 6,001 to 8,000 meters      | 2         |
|                                           | 8,001 to 10,000 meters     | 1         |
|                                           | Over 10,000 meters         | 0         |
| **Access to Education and Training Facilities** | 0 to 2,000 meters          | 5         |
|                                           | 2,001 to 4,000 meters      | 4         |
|                                           | 4,001 to 6,000 meters      | 3         |
|                                           | 6,001 to 8,000 meters      | 2         |
|                                           | 8,001 to 10,000 meters     | 1         |
|                                           | Over 10,000 meters         | 0         |
| **Access to Financial Facilities**        | 0 to 400 meters            | 5         |
|                                           | 401 to 800 meters          | 4         |
|                                           | 801 to 1,200 meters        | 3         |
|                                           | 1,201 to 2,000 meters      | 2         |
|                                           | 2,001 to 3,000 meters      | 1         |
|                                           | Over 3,000 meters          | 0         |

</a></small>  
