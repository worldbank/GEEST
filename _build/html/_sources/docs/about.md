# About GEEST

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
