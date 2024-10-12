# Project Background

## Empowering Women in the Renewable Energy Sector

With support from the [Canada Clean Energy and Forest Climate Facility (CCEFCFy)](https://www.worldbank.org/en/topic/climatechange/brief/canada-world-bank-clean-energy-and-forests-climate-facility), the [Geospatial Operational Support Team (GOST, DECSC)](https://worldbank.github.io/GOST) launched the project "Geospatial Assessment of Women Employment and Business Opportunities in the Renewable Energy Sector." The project aims to propose a novel methodology and generate a geospatial open-source tool for mapping the enabling environments for women in a country that can inform new energy projects to support the advancement of women's economic empowerment in SIDS while contributing to closing gender gaps in employment in the RE sector.

![image](docs/images/img01.png)

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/ReadMe/New/WEE_15classes_raster.png" height = 800 alt="WEE pop 35-39">
</p>

Countries included in the project:

<font size="2">

| AFRICA | LATIN AMERICA AND CARIBBEAN | EAST ASIA AND PACIFIC | SOUTH ASIA |
| --- | --- | --- | --- |
| Cabo Verde | Antigua and Barbuda | Federated States of Micronesia | Maldives |
| Comoros | Belize | Fiji  | |
| Guinea-Bissau | Dominica | Kiribati | |
| Mauritius | Dominican Republic | Marshall Islands | |
| São Tomé and Príncipe | Grenada | Nauru | |  
| | Guyana | Niue | |  
| | Haiti | Palau | |  
| | Jamaica | Papua New Guinea | |  
| | St. Lucia | Samoa | |  
| | St. Vincent and Grenadines | Solomon Islands | |
| | Suriname | Timor-Leste | |  
| | | Tonga | |  
| | | Tuvalu | |  
| | | Vanuatu | |
  
</font>

**Project Components**

The project is divided into six main components:

  1. [Gender Spatial Data Gap Assessment](gender-spatial-data-gap-assessment)
  2. [Geospatial Databases](geospatial-databases)
  3. [Novel Analytical Framework](novel-analytical-framework)
  4. [Gender Enabling Environments Tool (GEEST)](gender-enabling-environments-tool-geest)
  5. [Implementation](implementation)
  6. [GEEST Main Limitations](geest-main-limitations)

(gender-spatial-data-gap-assessment)=

## 1. Gender Spatial Data Gap Assessment

This undertaking involved the identification and compilation of essential open-source geospatial information layers that are crucial for assessing women's development, employment, and business prospects within the Renewable Energy (RE) sector. A thorough research was conducted for 59 data layers within each country, organized into 12 thematic categories. The table below presents the 59 layers identified during the desk research,  grouped into 12 categories, as outlined below

<br>

This effort resulted in a Data Gap Analysis Report for each of the 31 SIDS included in the project. The report for each country provides a comprehensive overview of the findings derived from an extensive data gap analysis, specifically centered on women in SIDS and their access (or lack thereof) to employment opportunities within the RE sector. This endeavor entailed thorough desk-based research, necessitating a detailed exploration of both spatial and non-spatial data sources that are publicly available. The focus was on identifying critical open sources, evaluating the resolution and quality of the data, and specifying any pertinent gaps or missing information in each country. The reports are available here: <https://datacatalog.worldbank.org/search/collections/genderspatial>

<font size="2">

| **Reference Data** |
| --- |
| Administrative boundaries |
| Location and outline of cities/villages |
| Coordinate reference system |  
| **Demographics and Population** |
| Population Density |  
| Level of Education |  
| Age |   
| Workplace Discrimination |
| Regulatory Frameworks |  
| Financial Inclusion |
| **Renewable Energy** |
| Existing RE: Solar Plants |
| Potential RE Project Sites: Solar |
| Potential RE Project Sites: Wind |
| Potential RE Project Sites: Wind Offshore |
| **Energy Access** |
| Measure of Visible Light at Nighttime |
| **Education** |
| Location of Universities |  
| Location of Technical Schools |  
| Percentage of Women who have achieved a post-secondary education | 
| **Jobs and Finance** |
| Financial Facilities |
| Labor in Industry Sector, Gender-Disaggregated | 
| **Digital Inclusion** |
| Access to Broadband Rates |  
| Digital Literacy Rates |  
| **Transportation** |
| Public Transportation Networks |  
| Public Transportation Stops |  
| Ports |
| Airports |
| Mobility Dataset |
| Commuting Zones |
| **Safety** |
| Prevalence of Domestic Violence |
| Trust in the Police |  
| Street lights for safe areas at night |  
| **Amenities** |
| Location of Hospitals |  
| Location of Grocery Stores |  
| Location of Green Spaces |  
| Location of Daycares/Elementary Schools | 
| Location of Pharmacies |  
| **Climate/Earth (5 datasets, four in GDB)** |
| Fires |  
| Coastal or Inland Flood Risk |  
| Cyclones |
| Landslides |
| Drought |
| **Law/Policy/Government** |
| Missing Data from SDGs |

</font>

The following figure summarizes the data availability concerning the 59 datasets examined for each country:

:::{figure-md} markdown-fig
<img src="docs/images/img03.png" height = 800 alt="Proportion of data availability for the 59 datasets, by country">

Proportion of data availability for the 59 datasets, by country
:::

(geospatial-databases)=

## 2. Geospatial Databases

In parallel with the Gender Data Gap Assessment, a comprehensive geospatial database was compiled for each of the 31 Small Island Developing States (SIDS) Targeted in the project.  The repository containing the geospatial databases can be found in the following link: <https://datacatalog.worldbank.org/search/collections/genderspatial>

Examples of data layers present in the GDB for selected countries:

![image](docs/images/img04.png)

![image](docs/images/img05.jpg)

![image](docs/images/img06.jpg)


## 3. Novel Analytical Framework

An extensive literature review, focusing on the barriers women face in securing jobs, particularly within SIDS, was conducted. This comprehensive review resulted in the formulation of a Multicriteria Evaluation (MCE) framework comprising 15 key factors, both spatial and non-spatial, that affect women’s job opportunities, categorized into three dimensions: Contextual, Accessibility, and Place Characterization. The latter two dimensions concentrate on geographical factors. For a comprehensive understanding of the Analytical Framework and the associated methodology employed to evaluate women's spatial access to employment opportunities, please refer to the Methodology Report available at the following link: <https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099121123091527675/p1792120dc820d04409928040a279022b42>

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/ReadMe/anal.jpg" alt="picture">
</p>

(gender-enabling-environments-tool-geest)=

## 4. Gender Enabling Environments Tool (GEEST)

Based on the Methodological Framework, the GEEST, an open-source plugin in QGIS, was developed for the automatic computation of the factors and dimensions. The GEEST characterizes communities based on women's prospects to secure jobs or establish their own businesses within the RE sector. It aims to assist decision-makers in selecting optimal locations for RE projects, ensuring the maximum positive impact on communities and addressing gender disparities. Additionally, it provides insights for building the necessary infrastructure around RE projects to create enabling environments that enhance women's participation in the RE sector in SIDS.

The table below outlines the dimensions, factors, and recommended indicators for computing the GEEST, derived from the Methodological Framework:


<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/ReadMe/factors.jpg" alt="picture">
</p>

Dimensions, Factors and indicators included in the Analytical Framework
:::

The GEEST generates raw score outputs for 15 factors outlined in the Analytical Framework. Each of the 15 factors, dimensions, and overall aggregate scores are assessed on a scale ranging from 0 to 5.

The interpretation of these scores is thoroughly detailed in the Methodology Report: <https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099121123091527675/p1792120dc820d04409928040a279022b42>.

Higher scores signify a more conducive environment for women to access job opportunities. Conversely, scores of 0 indicate a lack of supportive conditions for women to access employment opportunities. To enhance comprehension, the methodology further categorizes these scores into distinct 'classes,' offering a simplified approach to their interpretation, as shown in the following table:

```{list-table} Proposed discrete score classes to enable simpler visual interpretation of raw score outputs and enable intersection with other layers of information (reproduced from the Methodology Report).
:header-rows: 1
:name: Class Scores Table

* - Score range
  - Class
  - Interpretation
* - 0.00-0.50
  - 0
  - Not enabling
* - 0.51-1.50
  - 1
  - Very low enabling
* - 1.51-2.50
  - 2
  - Low enabling
* - 2.51-3.50
   - 3
   - Moderately enabling
* - 3.51-4.50
   - 4
   - Enabling
* - 4.51-5.00
   - 5
   - Highly enabling
```

To access the User Manual for GEEST and the necessary installation files for QGIS, please visit the [User Guide](docs/user_guide.md) or the [GitHub repository](https://github.com/worldbank/GEEST).

(implementation)=
## 5. Implementation

The GEEST was tested Saint Lucia to assess its functionality. The selection of this country was strategic, considering its varied geographic region, size, population densities, and data availability. Testing the GEEST across such a broad range of conditions ensured that its usefulness, applicability, and functionality in different contexts could be accurately tested. The findings and insights derived from the GEEST implementation are documented in the Implementation Report, accessible through the following link: [insert link].