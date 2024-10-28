## Data Collection

how data was collected...

# Data Collection for GEEST Tool

This page provides guidance on finding and collecting relevant data for the GEEST tool, using Saint Lucia as an example. The data sources, layers, and indicators shown here can serve as references when gathering data for other countries.

## Data Sources for Saint Lucia

<table style="border-collapse: collapse; width: 100%; font-size: small;">
  <tr>
    <th style="border: 1px solid black; padding: 1px; text-align: center;"><b>DIMENSION</b></th>
    <th style="border: 1px solid black; padding: 1px; text-align: center;"><b>FACTOR</b></th>
    <th style="border: 1px solid black; padding: 1px; text-align: center;"><b>LAYER</b></th>
    <th style="border: 1px solid black; padding: 1px; text-align: center;"><b>DATA SOURCE/QUERY</b></th>
  </tr>
  
  <!-- Contextual Section with Merged DIMENSION Cell -->
  <tr>
    <td rowspan="3" style="border: 1px solid black; padding: 1px; text-align: center; ">CONTEXTUAL</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Workplace Discrimination</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">WBL 2024 Workplace Index Score</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://wbl.worldbank.org/content/dam/documents/wbl/2024/snapshots/St-lucia.pdf" target="_blank">
        WBL 2024 index score: 83.8
    </a>
</td>

  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Regulatory Frameworks</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">WBL 2024 Pay+Parenthood Index Score</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://wbl.worldbank.org/content/dam/documents/wbl/2024/snapshots/St-lucia.pdf" target="_blank">
        WBL 2024 index score: Pay 100  and Parenthood 40
    </a>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Financial Inclusion</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">WBL 2024 Entrepreneurship Index Score</td>
 <td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://wbl.worldbank.org/content/dam/documents/wbl/2024/snapshots/St-lucia.pdf" target="_blank">
        WBL 2024 index score: Entrepreneurship 75
    </a>
  </tr>
  
  <!-- Accessibility Section with Merged DIMENSION Cell -->
  <tr>
    <td rowspan="9" style="border: 1px solid black; padding: 1px; text-align: center; ">ACCESSIBILITY</td>
    <td rowspan="5" style="border: 1px solid black; padding: 1px; text-align: center; ">Women's Travel Patterns</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of kindergartens/childcare</td>
 <td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://data.humdata.org/dataset/hotosm-saint-lucia-schools" target="_blank">
        Humdata
    </a>
    or
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22amenity%22=%22kindergarten%22](area.area_0);way[%22amenity%22=%22kindergarten%22](area.area_0);relation[%22amenity%22=%22kindergarten%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
</tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of primary schools</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://data.humdata.org/dataset/hotosm-saint-lucia-schools" target="_blank">
        Humdata
    </a>
   or
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22amenity%22=%22school%22](area.area_0);way[%22amenity%22=%22school%22](area.area_0);relation[%22amenity%22=%22school%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of groceries</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22shop%22=%22greengrocer%22](area.area_0);way[%22shop%22=%22greengrocer%22](area.area_0);relation[%22shop%22=%22greengrocer%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of pharmacies</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22amenity%22=%22pharmacy%22](area.area_0);way[%22amenity%22=%22pharmacy%22](area.area_0);relation[%22amenity%22=%22pharmacy%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of green spaces</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22leisure%22=%22park%22](area.area_0);node[%22boundary%22=%22national_park%22](area.area_0);way[%22leisure%22=%22park%22](area.area_0);way[%22boundary%22=%22national_park%22](area.area_0);relation[%22leisure%22=%22park%22](area.area_0);relation[%22boundary%22=%22national_park%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
</tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Access to Public Transport</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of public transportation stops, including maritime</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22public_transport%22=%22stop_position%22](area.area_0);node[%22public_transport%22=%22platform%22](area.area_0);node[%22public_transport%22=%22station%22](area.area_0);node[%22public_transport%22=%22stop_area%22](area.area_0);node[%22highway%22=%22bus_stop%22](area.area_0);node[%22highway%22=%22platform%22](area.area_0);way[%22public_transport%22=%22stop_position%22](area.area_0);way[%22public_transport%22=%22platform%22](area.area_0);way[%22public_transport%22=%22station%22](area.area_0);way[%22public_transport%22=%22stop_area%22](area.area_0);way[%22highway%22=%22bus_stop%22](area.area_0);way[%22highway%22=%22platform%22](area.area_0);relation[%22public_transport%22=%22stop_position%22](area.area_0);relation[%22public_transport%22=%22platform%22](area.area_0);relation[%22public_transport%22=%22station%22](area.area_0);relation[%22public_transport%22=%22stop_area%22](area.area_0);relation[%22highway%22=%22bus_stop%22](area.area_0);relation[%22highway%22=%22platform%22](area.area_0);node[%22amenity%22=%22ferry_terminal%22](area.area_0);way[%22amenity%22=%22ferry_terminal%22](area.area_0);relation[%22amenity%22=%22ferry_terminal%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
</tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Access to Health Facilities</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of hospitals and clinics</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://data.humdata.org/dataset/hotosm_lca_health_facilities" target="_blank">
        Humdata
    </a>
    or
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22amenity%22=%22dentist%22](area.area_0);node[%22amenity%22=%22doctors%22](area.area_0);node[%22amenity%22=%22hospital%22](area.area_0);node[%22amenity%22=%22clinic%22](area.area_0);way[%22amenity%22=%22dentist%22](area.area_0);way[%22amenity%22=%22doctors%22](area.area_0);way[%22amenity%22=%22hospital%22](area.area_0);way[%22amenity%22=%22clinic%22](area.area_0);relation[%22amenity%22=%22dentist%22](area.area_0);relation[%22amenity%22=%22doctors%22](area.area_0);relation[%22amenity%22=%22hospital%22](area.area_0);relation[%22amenity%22=%22clinic%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
</tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Access to Education and Training Facilities</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of universities and technical schools</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://data.humdata.org/dataset/hotosm-saint-lucia-schools" target="_blank">
        Humdata
    </a>
    or
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22amenity%22=%22university%22](area.area_0);way[%22amenity%22=%22university%22](area.area_0);relation[%22amenity%22=%22university%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
</tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Access to Financial Facilities</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of Banks and other financial facilities</td>
<td style="border: 1px solid black; padding: 1px; text-align: center;">
    <a href="https://overpass-turbo.eu/?Q=[out:xml][timeout:25];{{geocodeArea:Saint%20Lucia}}->.area_0;(node[%22amenity%22=%22bank%22](area.area_0);node[%22office%22=%22financial%22](area.area_0);way[%22amenity%22=%22bank%22](area.area_0);way[%22office%22=%22financial%22](area.area_0);relation[%22amenity%22=%22bank%22](area.area_0);relation[%22office%22=%22financial%22](area.area_0););(._;>;);out%20body;" target="_blank">
        OSM
    </a>
</td>
</tr>
  
  <!-- Place Characterization Section with Merged DIMENSION Cell -->
  <tr>
    <td rowspan="10" style="border: 1px solid black; padding: 1px; text-align: center; ">PLACE CHARACTERIZATION</td>
    <td rowspan="4" style="border: 1px solid black; padding: 1px; text-align: center; ">Active Transport</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of street crossings</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">OSM - Street crossing locations</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of cycle paths (OSM)</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">OSM - Cycle path locations</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Location of footpaths (OSM)</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">OSM - Footpath locations</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Block Layout (OSM)</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">OSM - Block layout data</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Safety</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Street lights/Nighttime lights</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Local data sources for street lights and nighttime light data</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">FCV</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">ACLED data (Violence Estimated Events)</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">ACLED - Query for estimated violence events</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Education</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Percentage of the labor force comprising women with university degrees</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">National labor statistics - University degree holders among women</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Digital Inclusion</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Individuals using the Internet (% of population)</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">World Bank, ITU - Internet usage data</td>
  </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Environmental Hazards</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Global Natural Hazards Data</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">ceva</td>
 </tr>
  <tr>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Water Sanitation</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">Water points (OSM), catch basins, water valves, and fire hydrants (Mapillary)</td>
    <td style="border: 1px solid black; padding: 1px; text-align: center; ">altceva</td>
  </tr>
</table>


## Potential Data Sources for Other Countries

While the above table showcases data specific to Saint Lucia, similar data can be found for other countries through the following sources:

1. **World Bank - Women, Business and the Law**: Provides indices on workplace discrimination, regulatory frameworks, and more.
2. **United Nations Development Programme (UNDP)**: Offers data on gender equality, economic empowerment, and related metrics.
3. **National Statistics Offices**: Many countries publish gender-disaggregated data that can be useful for contextual analysis.
4. **International Labour Organization (ILO)**: Sources data on labor force participation, wage gaps, and workplace regulations by country.

**Instructions for Data Collection**:
- **Query the Source**: Use the query instructions provided in the table to filter and collect specific data.
- **Check Availability for Each Country**: Not all indicators may be available for every country; adapt based on what is accessible.
- **Document Sources and Methods**: Record each source, method, and any specific details relevant to your data collection process.


