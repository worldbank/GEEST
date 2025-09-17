import os
import unittest

from osgeo import ogr, osr


class TestOGRGPKGCreation(unittest.TestCase):

    def create_gpkg_layer(self):
        gpkg_path: str = "example.gpkg"
        layer_name: str = "points_layer"
        try:
            # Validate input parameters
            if not gpkg_path.endswith(".gpkg"):
                raise ValueError("GeoPackage path must have a .gpkg extension")
            if not layer_name:
                raise ValueError("Layer name cannot be empty")

            # Check if the file already exists
            if os.path.exists(gpkg_path):
                print(
                    f"Warning: '{gpkg_path}' already exists. Adding layer to existing GeoPackage."
                )

            # Open or create the GeoPackage
            driver = ogr.GetDriverByName("GPKG")
            if driver is None:
                raise RuntimeError("GPKG driver is not available")

            datasource = driver.CreateDataSource(gpkg_path)
            if datasource is None:
                raise RuntimeError(f"Failed to create GeoPackage: {gpkg_path}")

            # Define spatial reference (WGS 84)
            spatial_ref = osr.SpatialReference()
            if spatial_ref.ImportFromEPSG(4326) != 0:
                raise RuntimeError("Failed to set spatial reference to EPSG:4326")

            # Create layer
            layer = datasource.CreateLayer(layer_name, spatial_ref, ogr.wkbPoint)
            if layer is None:
                raise RuntimeError(f"Failed to create layer: {layer_name}")

            # Define a field
            field_defn = ogr.FieldDefn("name", ogr.OFTString)
            field_defn.SetWidth(50)
            if layer.CreateField(field_defn) != 0:
                raise RuntimeError("Failed to create field 'name'")

            print(f"Layer '{layer_name}' successfully created in '{gpkg_path}'")

        except (ValueError, RuntimeError) as e:
            print(f"Error: {e}")

        finally:
            # Cleanup
            datasource = None
            driver = None
