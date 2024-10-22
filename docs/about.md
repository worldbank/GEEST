# About GEEST
<p align="justify">  
The Gender Enabling Environments Spatial Tool (GEEST), developed by the World Bank, evaluates locations based on how supportive they are of women’s employment and business opportunities. By incorporating 15 spatial factors across three dimensions—Contextual, Accessibility, and Place Characterization—GEEST offers a comprehensive analysis of how the environment impacts women's job prospects, indicating whether it is highly enabling or not enabling at all. 
</p>


**Brief summary of the framework** 
<p align="justify">  
The framework identifies 15 factors that are considered key to women’s ability to access employment opportunities. These factors are evaluated individually to create a single raster output layer for each factor with scores ranging from 0 to 5. 
Factor layers are aggregated into 3 dimensions (Contextual, Accessibility and Place Characterization) using a multicriteria evaluation as described in the methodology document. Dimensions are also represented by a single raster layer with scores ranging from 0 to 5. Finally, dimensions can be further combined to produce a final aggregate output of scores ranging from 0 to 5. 
</p>

The table below outlines the dimensions, factors, and recommended indicators for computing the GEEST, derived from the Methodological Framework:

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/ReadMe/factors.jpg" alt="picture">
</p>

<p align="justify"> 
The interpretation of these scores is thoroughly detailed in the <a href="https://documents.worldbank.org/en/publication/documents-reports/documentdetail/099121123091527675/p1792120dc820d04409928040a279022b42">Methodology Report</a>.
</p>

Higher scores signify a more conducive environment for women to access job opportunities. Conversely, scores of 0 indicate a lack of supportive conditions for women to access employment opportunities. To enhance comprehension, the methodology further categorizes these scores into distinct 'classes,' offering a simplified approach to their interpretation, as shown in the following table:


<table style="width: 100%; border-collapse: collapse;">
  <thead>
    <tr>
      <th style="padding: 10px;">Score range</th>
      <th style="padding: 10px;">Class</th>
      <th style="padding: 10px;">Interpretation</th>
      <th style="padding: 10px;">Color</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px;">0.00 - 0.50</td>
      <td style="padding: 10px;">0</td>
      <td style="padding: 10px;">Not enabling</td>
      <td style="background-color: #d73027; padding: 10px;">#d73027</td>
    </tr>
    <tr>
      <td style="padding: 10px;">0.51 - 1.50</td>
      <td style="padding: 10px;">1</td>
      <td style="padding: 10px;">Very low enabling</td>
      <td style="background-color: #fc8d59; padding: 10px;">#fc8d59</td>
    </tr>
    <tr>
      <td style="padding: 10px;">1.51 - 2.50</td>
      <td style="padding: 10px;">2</td>
      <td style="padding: 10px;">Low enabling</td>
      <td style="background-color: #fee090; padding: 10px;">#fee090</td>
    </tr>
    <tr>
      <td style="padding: 10px;">2.51 - 3.50</td>
      <td style="padding: 10px;">3</td>
      <td style="padding: 10px;">Moderately enabling</td>
      <td style="background-color: #e0f3f8; padding: 10px;">#e0f3f8</td>
    </tr>
    <tr>
      <td style="padding: 10px;">3.51 - 4.50</td>
      <td style="padding: 10px;">4</td>
      <td style="padding: 10px;">Enabling</td>
      <td style="background-color: #91bfdb; padding: 10px;">#91bfdb</td>
    </tr>
    <tr>
      <td style="padding: 10px;">4.51 - 5.00</td>
      <td style="padding: 10px;">5</td>
      <td style="padding: 10px;">Highly enabling</td>
      <td style="background-color: #4575b4; padding: 10px;">#4575b4</td>
    </tr>
  </tbody>
</table>
<p style="text-align: center; font-weight: normal;">
  <em>Proposed discrete score classes to enable simpler visual interpretation of raw score outputs</em>
</p>


**Confidence Level** 
<p align="justify">  
An overall confidence level is assigned to the final aggregate output based on the percentage of factors included in the aggregation. The level of confidence in the overall result can be interpreted as follows: 
</p>
<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
  <thead>
    <tr>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Confidence Range</th>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Description</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">0-24%</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Very low confidence</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">25-49%</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Low confidence</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">50-74%</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Medium confidence</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">75-89%</td>
      <td style="padding: 10px; border: 1px solid #ddd;">High confidence</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">90-100%</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Very high confidence</td>
    </tr>
  </tbody>
</table>



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

