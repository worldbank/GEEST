#!/usr/bin/env python

import pandas as pd
import json
import os


class SpreadsheetToJsonParser:
    def __init__(self, spreadsheet_path):
        """
        Constructor for SpreadsheetToJsonParser class.
        Takes in the path to an ODS spreadsheet file.
        """
        self.spreadsheet_path = spreadsheet_path
        self.dataframe = None
        self.result = {"dimensions": []}

    def load_spreadsheet(self):
        """
        Load the spreadsheet and preprocess it.
        """
        # Load the ODS spreadsheet
        self.dataframe = pd.read_excel(self.spreadsheet_path, engine="odf", skiprows=1)
        print(self.dataframe.columns)

        # Select only the relevant columns, including the new layer columns
        self.dataframe = self.dataframe[
            [
                "Dimension",
                "Default Dimension Analysis Weighting",
                "Factor",
                "Default Factor Dimension Weighting",
                "Indicator",
                "Default Indicator Factor Weighting",
                "ID",
                "Factor Description",
                "Default Index Score",
                "Index Score",
                "Use Default Index Score",
                "Default Multi Buffer Distances",
                "Use Multi Buffer Point",
                "Default Single Buffer Distance",
                "Use Single Buffer Point",
                "Default Pixel",
                "Use Create Grid",
                "Use OSM Downloader",
                "Use Bbox for AOI",
                "Use Rasterize Layer",
                "Use WBL Downloader",
                "Use Humdata Downloader",
                "Use Mapillary Downloader",
                "Use Other Downloader",
                "Use Add Layers Manually",
                "Use Classify Polygon into Classes",
                "Use Classify Safety Polygon into Classes",
                "Use CSV to Point Layer",
                "Use Polygon per Cell",
                "Use Polyline per Cell",
                "Use Point per Cell",
                "Use Nighttime Lights",
                "Use Environmental Hazards",
                "Use Street Lights",
                "Analysis Mode",
            ]
        ]

        # Fill NaN values in 'Dimension' and 'Factor' columns to propagate their values downwards for hierarchical grouping
        self.dataframe["Dimension"] = self.dataframe["Dimension"].ffill()
        self.dataframe["Factor"] = self.dataframe["Factor"].ffill()

    def create_id(self, name):
        """
        Helper method to create a lowercase, underscore-separated id from the name.
        """
        return name.lower().replace(" ", "_").replace("'", "_")

    def parse_to_json(self):
        """
        Parse the dataframe into the hierarchical JSON structure.
        """
        analysis_model = {}

        for _, row in self.dataframe.iterrows():
            dimension = row["Dimension"]
            factor = row["Factor"]

            # Prepare dimension data
            dimension_id = self.create_id(dimension)
            default_dimension_analysis_weighting = (
                row["Default Dimension Analysis Weighting"]
                if not pd.isna(row["Default Dimension Analysis Weighting"])
                else ""
            )
            if dimension_id not in analysis_model:
                # Hardcoded descriptions for specific dimensions
                description = ""
                if dimension_id == "contextual":
                    description = "The Contextual Dimension refers to the laws and policies that shape workplace gender discrimination, financial autonomy, and overall gender empowerment. Although this dimension may vary between countries due to differences in legal frameworks, it remains consistent within a single country, as national policies and regulations are typically applied uniformly across countries."
                elif dimension_id == "accessibility":
                    description = "The Accessibility Dimension evaluates women’s daily mobility by examining their access to essential services. Levels of enablement for work access in this dimension are determined by service areas, which represent the geographic zones that facilities like childcare, supermarkets, universities, banks, and clinics can serve based on proximity. The nearer these facilities are to where women live, the more supportive and enabling the environment becomes for their participation in the workforce."
                elif dimension_id == "place_characterization":
                    description = "The Place-Characterization Dimension refers to the social, environmental, and infrastructural attributes of geographical locations, such as walkability, safety, and vulnerability to natural hazards. Unlike the Accessibility Dimension, these factors do not involve mobility but focus on the inherent characteristics of a place that influence women’s ability to participate in the workforce."

            # If the Dimension doesn't exist yet, create it
            if dimension not in analysis_model:
                new_dimension = {
                    "id": dimension_id,
                    "name": dimension,
                    "default_analysis_weighting": default_dimension_analysis_weighting,
                    # Initialise the weighting to the default value
                    "analysis_weighting": default_dimension_analysis_weighting,
                    "description": description,
                    "factors": [],
                }
                self.result["dimensions"].append(new_dimension)
                analysis_model[dimension] = new_dimension

            # Prepare factor data
            factor_id = self.create_id(factor)
            default_factor_dimension_weighting = (
                row["Default Factor Dimension Weighting"]
                if not pd.isna(row["Default Factor Dimension Weighting"])
                else ""
            )

            # If the Factor doesn't exist in the current dimension, add it
            factor_map = {f["name"]: f for f in analysis_model[dimension]["factors"]}
            if factor not in factor_map:
                new_factor = {
                    "id": factor_id,
                    "name": factor,
                    "default_dimension_weighting": default_factor_dimension_weighting,
                    # Initialise the weighting to the default value
                    "dimension_weighting": default_factor_dimension_weighting,
                    "indicators": [],
                    "description": (
                        row["Factor Description"]
                        if not pd.isna(row["Factor Description"])
                        else ""
                    ),
                }
                analysis_model[dimension]["factors"].append(new_factor)
                factor_map[factor] = new_factor

            # Add indicator data to the current Factor, including new columns
            default_factor_weighting = (
                row["Default Indicator Factor Weighting"]
                if not pd.isna(row["Default Indicator Factor Weighting"])
                else ""
            )
            indicator_data = {
                # These are all parsed from the spreadsheet
                "indicator": row["Indicator"] if not pd.isna(row["Indicator"]) else "",
                "id": row["ID"] if not pd.isna(row["ID"]) else "",
                "description": "",
                "default_factor_weighting": default_factor_weighting,
                # Initialise the weighting to the default value
                "factor_weighting": default_factor_weighting,
                "default_index_score": (
                    row["Default Index Score"]
                    if not pd.isna(row["Default Index Score"])
                    else ""
                ),
                "index_score": (
                    row["Index Score"] if not pd.isna(row["Index Score"]) else ""
                ),
                "use_default_index_score": (
                    row["Use Default Index Score"]
                    if not pd.isna(row["Use Default Index Score"])
                    else ""
                ),
                "default_multi_buffer_distances": (
                    row["Default Multi Buffer Distances"]
                    if not pd.isna(row["Default Multi Buffer Distances"])
                    else ""
                ),
                "use_multi_buffer_point": (
                    row["Use Multi Buffer Point"]
                    if not pd.isna(row["Use Multi Buffer Point"])
                    else ""
                ),
                "default_single_buffer_distance": (
                    row["Default Single Buffer Distance"]
                    if not pd.isna(row["Default Single Buffer Distance"])
                    else ""
                ),
                "use_single_buffer_point": (
                    row["Use Single Buffer Point"]
                    if not pd.isna(row["Use Single Buffer Point"])
                    else ""
                ),
                "default_pixel": (
                    row["Default Pixel"] if not pd.isna(row["Default Pixel"]) else ""
                ),
                "use_create_grid": (
                    row["Use Create Grid"]
                    if not pd.isna(row["Use Create Grid"])
                    else ""
                ),
                "use_osm_downloader": (
                    row["Use OSM Downloader"]
                    if not pd.isna(row["Use OSM Downloader"])
                    else ""
                ),
                "use_bbox_for_aoi": (
                    row["Use Bbox for AOI"]
                    if not pd.isna(row["Use Bbox for AOI"])
                    else ""
                ),
                "use_rasterize_layer": (
                    row["Use Rasterize Layer"]
                    if not pd.isna(row["Use Rasterize Layer"])
                    else ""
                ),
                "use_wbl_downloader": (
                    row["Use WBL Downloader"]
                    if not pd.isna(row["Use WBL Downloader"])
                    else ""
                ),
                "use_humdata_downloader": (
                    row["Use Humdata Downloader"]
                    if not pd.isna(row["Use Humdata Downloader"])
                    else ""
                ),
                "use_mapilliary_downloader": (
                    row["Use Mapillary Downloader"]
                    if not pd.isna(row["Use Mapillary Downloader"])
                    else ""
                ),
                "use_other_downloader": (
                    row["Use Other Downloader"]
                    if not pd.isna(row["Use Other Downloader"])
                    else ""
                ),
                "use_add_layers_manually": (
                    row["Use Add Layers Manually"]
                    if not pd.isna(row["Use Add Layers Manually"])
                    else ""
                ),
                "use_classify_polygon_into_classes": (
                    row["Use Classify Polygon into Classes"]
                    if not pd.isna(row["Use Classify Polygon into Classes"])
                    else ""
                ),
                "use_classify_safety_polygon_into_classes": (
                    row["Use Classify Safety Polygon into Classes"]
                    if not pd.isna(row["Use Classify Safety Polygon into Classes"])
                    else ""
                ),
                "use_csv_to_point_layer": (
                    row["Use CSV to Point Layer"]
                    if not pd.isna(row["Use CSV to Point Layer"])
                    else ""
                ),
                "use_polygon_per_cell": (
                    row["Use Polygon per Cell"]
                    if not pd.isna(row["Use Polygon per Cell"])
                    else ""
                ),
                "use_polyline_per_cell": (
                    row["Use Polyline per Cell"]
                    if not pd.isna(row["Use Polyline per Cell"])
                    else ""
                ),
                "use_point_per_cell": (
                    row["Use Point per Cell"]
                    if not pd.isna(row["Use Point per Cell"])
                    else ""
                ),
                "use_nighttime_lights": (
                    row["Use Nighttime Lights"]
                    if not pd.isna(row["Use Nighttime Lights"])
                    else ""
                ),
                "use_environmental_hazards": (
                    row["Use Environmental Hazards"]
                    if not pd.isna(row["Use Environmental Hazards"])
                    else ""
                ),
                "use_street_lights": (
                    row["Use Street Lights"]
                    if not pd.isna(row["Use Street Lights"])
                    else ""
                ),
                "analysis_mode": (
                    row["Analysis Mode"] if not pd.isna(row["Analysis Mode"]) else ""
                ),  # New column
            }

            factor_map[factor]["indicators"].append(indicator_data)

    def get_json(self):
        """
        Return the parsed JSON structure.
        """
        return self.result

    def save_json_to_file(self, output_json_path="model.json"):
        """
        Save the parsed JSON structure to a file.
        """
        with open(output_json_path, "w") as json_file:
            json.dump(self.result, json_file, indent=4)
        print(f"JSON data has been saved to {output_json_path}")


if __name__ == "__main__":
    parser = SpreadsheetToJsonParser("geest/resources/geest2.ods")
    parser.load_spreadsheet()
    parser.parse_to_json()
    json_data = parser.get_json()
    parser.save_json_to_file("geest/resources/model.json")
