# About GEEST
<p align="justify">  
The Gender Enabling Environments Spatial Tool (GEEST), developed by the World Bank, evaluates locations based on how supportive they are of women’s employment and business opportunities. By incorporating 15 spatial factors across three dimensions—Contextual, Accessibility, and Place Characterization—GEEST offers a comprehensive analysis of how the environment impacts women's job prospects, indicating whether it is highly enabling or not enabling at all. 
</p>


<h3>Brief summary of the framework</h3>
<hr style="height: 3px; background-color: black; border: none;">
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


<table style="width: 100%; border-collapse: collapse; margin-top: 20px; border: 1px solid #ddd;">
  <thead>
    <tr>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Score range</th>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Class</th>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Interpretation</th>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Color</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">0.00 - 0.50</td>
      <td style="padding: 10px; border: 1px solid #ddd;">0</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Not enabling</td>
      <td style="background-color: #d73027; padding: 10px; border: 1px solid #ddd;">#d73027</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">0.51 - 1.50</td>
      <td style="padding: 10px; border: 1px solid #ddd;">1</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Very low enabling</td>
      <td style="background-color: #fc8d59; padding: 10px; border: 1px solid #ddd;">#fc8d59</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">1.51 - 2.50</td>
      <td style="padding: 10px; border: 1px solid #ddd;">2</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Low enabling</td>
      <td style="background-color: #fee090; padding: 10px; border: 1px solid #ddd;">#fee090</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">2.51 - 3.50</td>
      <td style="padding: 10px; border: 1px solid #ddd;">3</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Moderately enabling</td>
      <td style="background-color: #e0f3f8; padding: 10px; border: 1px solid #ddd;">#e0f3f8</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">3.51 - 4.50</td>
      <td style="padding: 10px; border: 1px solid #ddd;">4</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Enabling</td>
      <td style="background-color: #91bfdb; padding: 10px; border: 1px solid #ddd;">#91bfdb</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd;">4.51 - 5.00</td>
      <td style="padding: 10px; border: 1px solid #ddd;">5</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Highly enabling</td>
      <td style="background-color: #4575b4; padding: 10px; border: 1px solid #ddd;">#4575b4</td>
    </tr>
  </tbody>
</table>

<p style="text-align: center; font-weight: normal;">
  <em>Proposed discrete score classes to enable simpler visual interpretation of raw score outputs</em>
</p>


<h3>Confidence Level</h3>
<hr style="height: 3px; background-color: black; border: none;">
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



<h3>Insights</h3>
<hr style="height: 3px; background-color: black; border: none;">
<p align="justify"> 
The raw aggregate scores can be used in combination with information regarding the distribution of women and renewable energy sites to derive further insights. The insights tab categorizes population counts into three groups based on the lower, median, and upper quartile ranges of the data to identify areas with low, medium, and high numbers of women. These groupings are then combined with score classes to create 15 score-population classes, as listed below:
</p>



<table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
  <thead>
    <tr>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Class</th>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Description</th>
      <th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Color</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">1</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Very low enablement, low population</td>
      <td style="background-color: #b11419; padding: 10px; border: 1px solid #ddd;">#b11419</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">2</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Very low enablement, medium population</td>
      <td style="background-color: #d7191c; padding: 10px; border: 1px solid #ddd;">#d7191c</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">3</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Very low enablement, high population</td>
      <td style="background-color: #f14247; padding: 10px; border: 1px solid #ddd;">#f14247</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">4</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Low enablement, low population</td>
      <td style="background-color: #d68f47; padding: 10px; border: 1px solid #ddd;">#d68f47</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">5</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Low enablement, medium population</td>
      <td style="background-color: #fdae61; padding: 10px; border: 1px solid #ddd;">#fdae61</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">6</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Low enablement, high population</td>
      <td style="background-color: #ffc688; padding: 10px; border: 1px solid #ddd;">#ffc688</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">7</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Moderately enabling, low population</td>
      <td style="background-color: #e0e09f; padding: 10px; border: 1px solid #ddd;">#e0e09f</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">8</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Moderately enabling, medium population</td>
      <td style="background-color: #ffffb4; padding: 10px; border: 1px solid #ddd;">#ffffb4</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">9</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Moderately enabling, high population</td>
      <td style="background-color: #ffffee; padding: 10px; border: 1px solid #ddd;">#ffffee</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">10</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Enabling, low population</td>
      <td style="background-color: #93bd9b; padding: 10px; border: 1px solid #ddd;">#93bd9b</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">11</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Enabling, medium population</td>
      <td style="background-color: #bce1b8; padding: 10px; border: 1px solid #ddd;">#bce1b8</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">12</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Enabling, high population</td>
      <td style="background-color: #dbfbd5; padding: 10px; border: 1px solid #ddd;">#dbfbd5</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">13</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Highly enabling, low population</td>
      <td style="background-color: #1d5c8d; padding: 10px; border: 1px solid #ddd;">#1d5c8d</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">14</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Highly enabling, medium population</td>
      <td style="background-color: #2c7bb6; padding: 10px; border: 1px solid #ddd;">#2c7bb6</td>
    </tr>
    <tr>
      <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">15</td>
      <td style="padding: 10px; border: 1px solid #ddd;">Highly enabling, high population</td>
      <td style="background-color: #4ab8e0; padding: 10px; border: 1px solid #ddd;">#4ab8e0</td>
    </tr>
  </tbody>
</table>


