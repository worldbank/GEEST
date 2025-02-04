# Project Background
  
<h2 id="introduction">Introduction</h2>
    
<p align="justify">  
  With support from the <a href="https://www.worldbank.org/en/topic/climatechange/brief/canada-world-bank-clean-energy-and-forests-climate-facility">Canada Clean Energy and Forest Climate Facility (CCEFCFy)</a>, the <a href="https://worldbank.github.io/GOST">Geospatial Operational Support Team (GOST, DECSC)</a> launched the project "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector" in <a href="#footnote1" id="ref1">SIDS<sup>1</sup></a>. The project aims to propose a novel methodology and generate a geospatial open-source tool for mapping the enabling environments for women in a country that can inform new energy projects to support the advancement of women's economic empowerment in <a href="#footnote1" id="ref1">SIDS<sup>1</sup></a> while contributing to closing gender gaps in employment in the RE sector.
</p>


<h2 id="project-scope">Project Scope</h2>

### 1. Novel Analytical Framework

---

<p align="justify">  
An extensive literature review, focusing on the barriers women face in securing jobs, particularly within SIDS, was conducted. This comprehensive review resulted in the formulation of a Multicriteria Evaluation (MCE) framework comprising 15 key factors, both spatial and non-spatial, that affect women’s job opportunities. These factors are categorized into three dimensions: <strong>Contextual</strong>, <strong>Accessibility</strong>, and <strong>Place Characterization</strong>. The latter two dimensions concentrate on geographical factors.

For a comprehensive understanding of the Analytical Framework and the associated methodology employed to evaluate women’s spatial access to employment opportunities, please refer to the Methodology Report available at the following link: <a href="https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099121123091527675/p1792120dc820d04409928040a279022b42" target="_blank">Methodology Report</a>
</p>

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/framework.jpg" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/framework.jpg" alt="Analytical Framework" width="700" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view the Analytical Framework">
</a>


### 2. Gender Enabling Environments Tool (GEEST)

---

<p align="justify"> 
Based on the Methodological Framework, the GEEST, an open-source plugin in QGIS, was developed for the automatic computation of the factors and dimensions. The GEEST characterizes communities based on women’s prospects to secure jobs or establish their own businesses within the RE sector. It aims to assist decision-makers in selecting optimal locations for RE projects, ensuring the maximum positive impact on communities and addressing gender disparities. Additionally, it provides insights for building the necessary infrastructure around RE projects to create enabling environments that enhance women’s participation in the RE sector in SIDS.

The GEEST generates raw score outputs for 15 factors outlined in the Analytical Framework. Each of the 15 factors, dimensions, and overall aggregate scores are assessed on a scale ranging from 0 to 5.
</p>

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/3%20countries%20maps.png" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/3%20countries%20maps.png" alt="Examples" width="700" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view map">
</a>


### 3. Study Case: Saint Lucia

---

<p align="justify"> 
  The GEEST was tested in Saint Lucia to assess its functionality. The selection of this country was strategic, considering its varied geographic region, size, population densities, and data availability. Testing the GEEST across such a broad range of conditions ensured that its usefulness, applicability, and functionality in different contexts could be accurately tested. The findings and insights derived from the GEEST implementation are documented in the Implementation Report, accessible through the following link: 
  <a href="https://worldbankgroup-my.sharepoint.com/:w:/r/personal/civanescu_worldbank_org/Documents/Desktop/Work/Gender/TORs/Task%203/St%20Lucia%20-%20GEEST/Implementation%20Report/Implementation%20Report%20Saint%20Lucia.docx?d=wd12a9d054d5747f49788597e3fdc4ff8&csf=1&web=1&e=q6UcU0" target="_blank">Implementation Report St. Lucia</a>
</p>


**GEEST Results in Saint Lucia**

            a. Contextual Dimension
<p align="justify"> 
The Contextual Dimension (CD) factors were evaluated using the World Bank's Women, Business, and the Law study, a reputable non-governmental resource that assigns country-level scores ranging from 0 to 100 based on the presence of relevant laws and regulations. Scores for factors in this dimension were standardized on a scale of 0 to 5, with 5 representing the most favorable environment for that specific factor.  
</p>
<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Contextual_new.png" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Contextual_new.png" alt="Contextual Image" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view map">
</a>


            b. Accessibility Dimension
<p align="justify"> 
The factors in the Accessibility Dimension were assessed using service areas through network analyses around key facilities, which defined varying levels of access. As anticipated, the highest levels of access to each factor are concentrated in urban centers. Women's Travel Patterns, which relate to essential services needed by women to fulfill their caregiving and household responsibilities, is the factor in this dimension with the fewest highly enabling areas. The latter underscores the need for environments that are better planned with the unique needs and responsibilities of women in mind. This includes ensuring that essential services, such as childcare, pharmacies, and grocery stores, are easily accessible to support women in their roles as caregivers and members of the workforce.
</p>
<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Acc.jpg" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Acc.jpg" alt="Accessibility Image" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view map">
</a>



            c. Place Characterization Dimension
<p align="justify"> 
The Place-Characterization Dimension encompasses seven factors, each evaluated through distinct analytical methods. Notably, the analyses of factors such as Active Transport, Education, and Water and Sanitation reveal some areas where these elements fail to be even moderately supportive of women's access to employment.
</p>
<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/PD.jpg" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/PD.jpg" alt="Accessibility Image" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view map">
</a>


<p align="justify"> 
The overall enablement scores for Saint Lucia reveal that, although some areas in the northwest and south exhibit a somewhat supportive environment, the country largely lacks regions that are highly conducive to facilitating women’s access to employment opportunities. Notably, the area around the solar plant in Vieux Fort provides a moderately enabling environment for women's job access, but it still falls short of achieving the highest level of enablement.
</p>
<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/WEE%20score%20solar.png" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/WEE%20score%20solar.png" alt="WEE Score Solar" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view map">
</a>



<p align="justify"> 
When the enablement scores are combined with data on the distribution of women of working age, specifically those aged 35 to 39, across low, medium, and high population densities, it was observed that the most enabling areas on the island corresponded with regions of high female population. However, a few areas with very high population density were identified as having significantly low enablement scores. For example, the area surrounding the solar plant in Vieux Fort is characterized by a high female population density but is classified as only moderately enabling. 
</p>

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/3D%20Score%20map.png" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/3D%20Score%20map.png" alt="3D Score Map" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view map">
</a>

> <p align="justify"><strong>Note</strong>: For detailed information and guidance on the data collected and utilized, please refer to the <a href="https://worldbank.github.io/GEEST/docs/userguide/datacollection.html">Data Collection</a> section.</p>


### 4. Gender Spatial Data Gap Assessment

---

<p align="justify"> 
This undertaking involved the identification and compilation of essential open-source geospatial information layers that are crucial for assessing women’s development, employment, and business prospects within the Renewable Energy (RE) sector. A thorough research was conducted for 38 data layers within each country, organized into 11 thematic categories. The table below presents the 38 layers identified during the desk research, grouped into 11 categories, as outlined below:
</p>

<table style="border-collapse: collapse; width: 100%; font-size: small;">
  <tr>
    <th style="border: 1px solid black; padding: 2px;">🌍 Category</th>
    <th style="border: 1px solid black; padding: 2px;">📊 Data Layers</th>
  </tr>
  <tr>
    <td rowspan="3" style="border: 1px solid black; padding: 2px;">📌 Reference Data</td>
    <td style="border: 1px solid black; padding: 2px;">Administrative boundaries</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location and outline of cities/villages</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location and outline of cities/villages</td>
  </tr>
  <tr>
    <td rowspan="2" style="border: 1px solid black; padding: 2px;">👥 Demographics and Population</td>
    <td style="border: 1px solid black; padding: 2px;">Population Density</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Age</td>
  </tr>
  <tr>
    <td rowspan="5" style="border: 1px solid black; padding: 2px;">⚡ Renewable Energy</td>
    <td style="border: 1px solid black; padding: 2px;">Existing RE: Solar Plants, Wind Onshore and Offshore</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Potential RE Project Sites: Solar</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Potential RE Project Sites: Wind Onshore</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Potential RE Project Sites: Wind Offshore</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Potential RE Project Sites: Geothermal</td>
  </tr>
  <tr>
    <td rowspan="3" style="border: 1px solid black; padding: 2px;">⚖️ Law/Policy</td>
    <td style="border: 1px solid black; padding: 2px;">Workplace Discrimination</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Regulatory Frameworks</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Financial Inclusion</td>
  </tr>
  <tr>
    <td rowspan="8" style="border: 1px solid black; padding: 2px;">🏥 Amenities</td>
    <td style="border: 1px solid black; padding: 2px;">Location of Hospitals and Clinics</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location of Grocery Stores</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location of Green Spaces</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location of Kindergartens/Childcare</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location of Pharmacies</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location of Schools</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location of Universities</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Location of Banks and other financial facilities</td>
  </tr>
  <tr>
    <td rowspan="6" style="border: 1px solid black; padding: 2px;">🚶‍♂️ Transportation and Active Transport</td>
    <td style="border: 1px solid black; padding: 2px;">Public Transportation Stops</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Ports</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Street crossings</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Cyclepaths</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Blocklayout</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Footpaths</td>
  </tr>
  <tr>
    <td rowspan="3" style="border: 1px solid black; padding: 2px;">🔦 Safety</td>
    <td style="border: 1px solid black; padding: 2px;">Measure of Visible Light at Nighttime</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Street lights for safe areas at night</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">FCV data</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">🌐 Digital Inclusion</td>
    <td style="border: 1px solid black; padding: 2px;">Access to internet</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">🎓 Education</td>
    <td style="border: 1px solid black; padding: 2px;">Percentage of women with post-secondary education</td>
  </tr>
  <tr>
    <td rowspan="5" style="border: 1px solid black; padding: 2px;">🌪️ Climate Hazards</td>
    <td style="border: 1px solid black; padding: 2px;">Fires</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Coastal or Inland Flood Risk</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Cyclones</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Landslides</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">Drought</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 2px;">🚰 Water Sanitation</td>
    <td style="border: 1px solid black; padding: 2px;">Water points, catch basins, water valves and fire hydrants</td>
  </tr>
</table>
<br>
<p align="justify"> 
  This effort resulted in a Data Gap Analysis Report for each of the 31 SIDS included in the project. The report for each country provides a comprehensive overview of the findings derived from an extensive data gap analysis, specifically centered on women in SIDS and their access (or lack thereof) to employment opportunities within the RE sector. This endeavor entailed thorough desk-based research, necessitating a detailed exploration of both spatial and non-spatial data sources that are publicly available. The focus was on identifying critical open sources, evaluating the resolution and quality of the data, and specifying any pertinent gaps or missing information in each country. The reports are available here: 
  <a href="https://datacatalog.worldbank.org/search/collections/genderspatial" target="_blank">Data Catalog</a>.
  The following figure summarizes the data availability concerning the datasets examined for each country:
</p>


<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/data%20availability%20per%20country.JPG" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/data%20availability%20per%20country.JPG" alt="Data Availability per Country" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to view data availability">
</a>


### 5.	Geospatial Databases

---

<p align="justify"> 
  In parallel with the Gender Data Gap Assessment, a comprehensive geospatial database was compiled for each of the 31 Small Island Developing States (SIDS) targeted in the project. The repository containing the geospatial databases can be found in the following link: 
  <a href="https://datacatalog.worldbank.org/search/collections/genderspatial" target="_blank">Data Catalog</a>.
</p>

    
  <small><a href="#ref1" id="footnote1"><sup>1</sup> **Eligible SIDS:**
Antigua and Barbuda, Belize, Cabo Verde, Comoros, Dominica, Dominican Republic, Federated States of Micronesia, Fiji, Grenada, Guinea-Bissau, Guyana, Haiti, Jamaica, Kiribati, Maldives, Marshall Islands, Mauritius, Nauru, Niue, Palau, Papua New Guinea, Samoa, São Tomé and Príncipe, Solomon Islands, St. Lucia, St. Vincent and Grenadines, Suriname, Timor-Leste, Tonga, Tuvalu, Vanuatu.</a></small>
</p>


