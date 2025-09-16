#!/usr/bin/env python3
import os
import shutil

# Create a mapping from the generic names to more descriptive names
icon_mapping = {
    "icon_01.png": "setup_tab.png",  # This is the most common one - used for Setup Tab
    "icon_02.png": "dimension_aggregation_tab.png",  # Used for Dimension Aggregation Tab
    "icon_03.png": "insights_tab.png",  # Used for Insights Tab
    "icon_04.png": "raster_output_error.png",  # Used for raster output errors
    "icon_05.png": "country_boundary_error.png",  # Used for country boundary errors
}

# Look at the larger icons to see what they might be
print("Larger icons (likely screenshots):")
for i in range(6, 38):  # icons 6-37 are the larger ones
    filename = f"icon_{i:02d}.png"
    if os.path.exists(f"images/{filename}"):
        size = os.path.getsize(f"images/{filename}")
        print(f"{filename}: {size} bytes")

# The small icons 1-5 are likely the tab icons, let's rename them
for old_name, new_name in icon_mapping.items():
    old_path = f"images/{old_name}"
    new_path = f"images/{new_name}"

    if os.path.exists(old_path):
        shutil.copy2(old_path, new_path)
        print(f"Copied {old_name} to {new_name}")

print(f"\nSmall tab icons have been given descriptive names.")
print(f"Large screenshot icons (icon_06.png to icon_37.png) are left as is.")
print(f"You may want to rename them based on their content if needed.")
