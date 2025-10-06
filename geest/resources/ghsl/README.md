# GHS MOD 2023 GeoParquet

This data was sourced from the
[Global Human Settlements Model Grid, 2023](https://human-settlement.emergency.copernicus.eu/download.php?ds=smod)
details of which can be found in the
[GHSL Data Package](https://human-settlement.emergency.copernicus.eu/documents/GHSL_Data_Package_2023.pdf?t=1727170839)
documentation.

The global grid will be post-processed by reclassifying all pixes of class 10
(sea) and 11 (low population) to 0 and all other pixels to 1.

The grid is then converted to a vector layer using the GDAL polygonize tool, and
then converted to a GeoParquet file. Additionally a raster mask is created with
value of 0 where population is low or zero and a value of 1 where people inhabit
the area.

Tim Sutton September 2025
