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
        self.result = {"dimensions": []}  # Correct capitalization to match the usage

    def load_spreadsheet(self):
        """
        Load the spreadsheet and preprocess it.
        """
        # Load the ODS spreadsheet
        self.dataframe = pd.read_excel(self.spreadsheet_path, engine="odf", skiprows=1)
        print(self.dataframe.columns)

        # Select only the relevant columns
        self.dataframe = self.dataframe[
            [
                "Dimension",
                "Factor",
                "Layer",
                "ID",
                "Text",
                "Default Index Score",
                "Index Score",
                "Use Default Index Score",
                "Default Multi Buffer Distances",
                "Use Multi Buffer Point",
                "Default Single Buffer Distance",
                "Use Single Buffer Point",
                "Default pixel",
                "Use Create Grid",
                "Use OSM Downloader",
                "Use Bbox for AOI",
                "Use Rasterize Layer",
                "Use WBL Downloader",
                "Use Humdata Downloader",
                "Use Mapillary Downloader",
                "Use Other Downloader",
                "Use Add Layers Manually",
                "Use Classify Poly into Classes",
                "Use CSV to Point Layer",
                "Use Poly per Cell",
                "Use Polyline per Cell",
                "Use Point per Cell",
            ]
        ]

        # Fill NaN values in 'Dimension' and 'Factor' columns to propagate their values downwards for hierarchical grouping
        self.dataframe["Dimension"] = self.dataframe["Dimension"].ffill()
        self.dataframe["Factor"] = self.dataframe["Factor"].ffill()

    def parse_to_json(self):
        """
        Parse the dataframe into the hierarchical JSON structure.
        """
        dimension_map = {}

        for _, row in self.dataframe.iterrows():
            dimension = row["Dimension"]
            factor = row["Factor"]
            layer_data = {
                # These are initially blank for the user to make choices
                "Analysis Mode": "",
                "Points Per Cell Layer": "",
                "Lines Per Cell Layer": "",
                "Polygons Per Cell Layer": "",
                # These are all parsed from the spreadsheet
                "Layer": row["Layer"] if not pd.isna(row["Layer"]) else "",
                "ID": row["ID"] if not pd.isna(row["ID"]) else "",
                "Text": row["Text"] if not pd.isna(row["Text"]) else "",
                "Default Index Score": (
                    row["Default Index Score"]
                    if not pd.isna(row["Default Index Score"])
                    else ""
                ),
                "Index Score": (
                    row["Index Score"] if not pd.isna(row["Index Score"]) else ""
                ),
                "Use Default Index Score": (
                    row["Use Default Index Score"]
                    if not pd.isna(row["Use Default Index Score"])
                    else ""
                ),
                "Default Multi Buffer Distances": (
                    row["Default Multi Buffer Distances"]
                    if not pd.isna(row["Default Multi Buffer Distances"])
                    else ""
                ),
                "Use Multi Buffer Point": (
                    row["Use Multi Buffer Point"]
                    if not pd.isna(row["Use Multi Buffer Point"])
                    else ""
                ),
                "Default Single Buffer Distance": (
                    row["Default Single Buffer Distance"]
                    if not pd.isna(row["Default Single Buffer Distance"])
                    else ""
                ),
                "Use Single Buffer Point": (
                    row["Use Single Buffer Point"]
                    if not pd.isna(row["Use Single Buffer Point"])
                    else ""
                ),
                "Default pixel": (
                    row["Default pixel"] if not pd.isna(row["Default pixel"]) else ""
                ),
                "Use Create Grid": (
                    row["Use Create Grid"]
                    if not pd.isna(row["Use Create Grid"])
                    else ""
                ),
                "Use OSM Downloader": (
                    row["Use OSM Downloader"]
                    if not pd.isna(row["Use OSM Downloader"])
                    else ""
                ),
                "Use Bbox for AOI": (
                    row["Use Bbox for AOI"]
                    if not pd.isna(row["Use Bbox for AOI"])
                    else ""
                ),
                "Use Rasterize Layer": (
                    row["Use Rasterize Layer"]
                    if not pd.isna(row["Use Rasterize Layer"])
                    else ""
                ),
                "Use WBL Downloader": (
                    row["Use WBL Downloader"]
                    if not pd.isna(row["Use WBL Downloader"])
                    else ""
                ),
                "Use Humdata Downloader": (
                    row["Use Humdata Downloader"]
                    if not pd.isna(row["Use Humdata Downloader"])
                    else ""
                ),
                "Use Mapillary Downloader": (
                    row["Use Mapillary Downloader"]
                    if not pd.isna(row["Use Mapillary Downloader"])
                    else ""
                ),
                "Use Other Downloader": (
                    row["Use Other Downloader"]
                    if not pd.isna(row["Use Other Downloader"])
                    else ""
                ),
                "Use Add Layers Manually": (
                    row["Use Add Layers Manually"]
                    if not pd.isna(row["Use Add Layers Manually"])
                    else ""
                ),
                "Use Classify Poly into Classes": (
                    row["Use Classify Poly into Classes"]
                    if not pd.isna(row["Use Classify Poly into Classes"])
                    else ""
                ),
                "Use CSV to Point Layer": (
                    row["Use CSV to Point Layer"]
                    if not pd.isna(row["Use CSV to Point Layer"])
                    else ""
                ),
                "Use Poly per Cell": (
                    row["Use Poly per Cell"]
                    if not pd.isna(row["Use Poly per Cell"])
                    else ""
                ),
                "Use Polyline per Cell": (
                    row["Use Polyline per Cell"]
                    if not pd.isna(row["Use Polyline per Cell"])
                    else ""
                ),
                "Use Point per Cell": (
                    row["Use Point per Cell"]
                    if not pd.isna(row["Use Point per Cell"])
                    else ""
                ),
            }

            # If the Dimension doesn't exist yet, create it
            if dimension not in dimension_map:
                new_dimension = {"name": dimension, "factors": []}
                self.result["dimensions"].append(new_dimension)
                dimension_map[dimension] = new_dimension

            # If the Factor doesn't exist in the current dimension, add it
            factor_map = {f["name"]: f for f in dimension_map[dimension]["factors"]}
            if factor not in factor_map:
                new_factor = {"name": factor, "layers": []}
                dimension_map[dimension]["factors"].append(new_factor)  # Correct variable name
                factor_map[factor] = new_factor

            # Add layer data to the current Factor
            factor_map[factor]["layers"].append(layer_data)

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
