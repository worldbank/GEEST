#!/usr/bin/env python


def parse_to_json(self):
    """
    Parse the dataframe into the hierarchical JSON structure.
    """
    dimension_map = {}

    for _, row in self.dataframe.iterrows():
        dimension = row["Dimension"]
        factor = row["Factor"]

        # Prepare dimension data
        dimension_id = self.create_id(dimension)
        dimension_required = (
            row["Dimension Required"] if not pd.isna(row["Dimension Required"]) else ""
        )
        default_dimension_analysis_weighting = (
            row["Default Dimension Analysis Weighting"]
            if not pd.isna(row["Default Dimension Analysis Weighting"])
            else ""
        )

        # If the Dimension doesn't exist yet, create it
        if dimension_id not in dimension_map:
            # Hardcoded descriptions for specific dimensions
            description = ""
            if dimension_id == "contextual":
                description = "The Contextual Dimension refers to the laws and policies that shape workplace gender discrimination, financial autonomy, and overall gender empowerment. Although this dimension may vary between countries due to differences in legal frameworks, it remains consistent within a single country, as national policies and regulations are typically applied uniformly across countries."
            elif dimension_id == "accessibility":
                description = "The Accessibility Dimension evaluates women’s daily mobility by examining their access to essential services. Levels of enablement for work access in this dimension are determined by service areas, which represent the geographic zones that facilities like childcare, supermarkets, universities, banks, and clinics can serve based on proximity. The nearer these facilities are to where women live, the more supportive and enabling the environment becomes for their participation in the workforce."
            elif dimension_id == "place_characterization":
                description = "The Place-Characterization Dimension refers to the social, environmental, and infrastructural attributes of geographical locations, such as walkability, safety, and vulnerability to natural hazards. Unlike the Accessibility Dimension, these factors do not involve mobility but focus on the inherent characteristics of a place that influence women’s ability to participate in the workforce."

            # Create a new dimension entry
            new_dimension = {
                "id": dimension_id,
                "name": dimension,
                "required": dimension_required,
                "default_analysis_weighting": default_dimension_analysis_weighting,
                "description": description,
                "factors": [],
            }
            # Add the new dimension to the result and the dimension_map
            self.result["dimensions"].append(new_dimension)
            dimension_map[dimension_id] = new_dimension

        # Prepare factor data
        factor_id = self.create_id(factor)
        factor_required = (
            row["Factor Required"] if not pd.isna(row["Factor Required"]) else ""
        )
        default_factor_dimension_weighting = (
            row["Default Factor Dimension Weighting"]
            if not pd.isna(row["Default Factor Dimension Weighting"])
            else ""
        )

        # If the Factor doesn't exist in the current dimension, add it
        factor_map = {f["name"]: f for f in dimension_map[dimension_id]["factors"]}
        if factor not in factor_map:
            new_factor = {
                "id": factor_id,
                "name": factor,
                "required": factor_required,
                "default_dimension_weighting": default_factor_dimension_weighting,
                "layers": [],
            }
            dimension_map[dimension_id]["factors"].append(new_factor)
            factor_map[factor] = new_factor

        # Add layer data to the current Factor, including new columns
        layer_data = {
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
                row["Use Create Grid"] if not pd.isna(row["Use Create Grid"]) else ""
            ),
            "Use OSM Downloader": (
                row["Use OSM Downloader"]
                if not pd.isna(row["Use OSM Downloader"])
                else ""
            ),
            "Use Bbox for AOI": (
                row["Use Bbox for AOI"] if not pd.isna(row["Use Bbox for AOI"]) else ""
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
            "Use Nighttime Lights": (
                row["Use Nighttime Lights"]
                if not pd.isna(row["Use Nighttime Lights"])
                else ""
            ),
            "Use Environmental Hazards": (
                row["Use Environmental Hazards"]
                if not pd.isna(row["Use Environmental Hazards"])
                else ""
            ),
            "Analysis Mode": (
                row["Analysis Mode"] if not pd.isna(row["Analysis Mode"]) else ""
            ),  # New column
            "Layer Required": (
                row["Layer Required"] if not pd.isna(row["Layer Required"]) else ""
            ),  # New column
        }

        factor_map[factor]["layers"].append(layer_data)
