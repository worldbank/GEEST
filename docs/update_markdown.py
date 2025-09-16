#!/usr/bin/env python3
import re

# Read the original markdown file
with open("Gender_Enabling_Environments_Spatial_Tool_v1.md", "r") as f:
    content = f.read()

# Define the base64 patterns and their replacement image paths
replacements = [
    # The recurring small tab icons (these appear multiple times)
    {
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAABhUlEQVQokZ2S3ytDcRjGn+3M/AMu1vGjvhfaubDhFE7JjcjaStRMxN2u0FYrtCLhzjWuWBbtzI7mioh/ANmpQ4iinY38Cduc9brQqV0M8dRz9T5vz1vvx0JEMJXLv7I9WZk6OjkLvL29NwEAzzt0n6c/NTE2stnYUP9iZi3m4v7BYXBpdW29VCrVoorsdntxZXF+OuAf2gYAEBGSSjrIBJGYIFIoEpUzqiYZhsEZhsFlVE0KRaKyOU8q6SARAXouz5xuqcAEkWLxRJiIUM2xeCLMBJGcbqmg5/KMq3M0LFxdqz2DPo8cnQ3PVTsTANpbXRfPL1nh/uGxrabG9oHuXm+WCSJlVE36rs10RtUkJojU3evNWpggEgA83V7aOI4rf9cIAOVymWtu6TQAwPpT8CdZed6hA4B2c9fxW9jM8LxDt3oH+hQAiO8lQ78t7uzKYQDwefpTX+9wdRX/+o5/A/An5JYX52ZG/cNbQAWrwBfku4nU9PHp+Ugl5N6BPmVyPLBRCfkntjcTOGgznsUAAAAASUVORK5CYII=",
        "filename": "setup_tab.png",
        "alt_text": "Setup Tab",
    },
    {
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAABbklEQVQokZ1Sz0oCcRgcXbUX6CCbBb9DtIe0WqgWooskiUIUmBF09FShIGQISVS3ztGpJClay7BTEPQEFbmwRUVB4mrSI6itfB1ioYN/sIE5fTPMBzMmIoKBYumTnciZ5avrm2C5/NUHADxv1/xez/nS4vx+r6Mnb2hNhvHs4jK0ubO7V6vVutAANputup1YXwkGZg8BAESEdCYbYoJITBApHI3LOUWVdF3ndF3ncooqhaNx2binM9kQEQFascQGXFKFCSIlU6cRIkIjJlOnESaINOCSKlqxxLhuu2Pj/kGZnPF75fhaJNboTQAYGXLefuQLwsvr27DVavnGhNtXYIJIOUWVmqUZzCmqxASRJty+gokJIgHA+9OdheO4erNEAKjX61z/4JgOAOZWwlYw87xdAwD18Xm0ndjQ8LxdM/umpzIAkDpJh9sZj47lCAD4vZ7z3zqc49VO6/j3ADqa3FYitroQmDsA/mwV6GzkP7ZHEzgTeJKOAAAAAElFTkSuQmCC",
        "filename": "dimension_aggregation_tab.png",
        "alt_text": "Dimension Aggregation Tab",
    },
    {
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAABh0lEQVQokZWS3ytDcRjGn+3M/AMu1vGjvhfaufDzFE7Jzdra2koUE3G3K7RThCZLuHONK2TRzjjiSil/AbJThxBFO5vlT2DOel3olNhoTz1X7/P2vPV+bEQES9ncC9tT1PGT07NwPv/aAAA87zJCAd/B6PDgRn1d7bOVtVmL+4fHkcWV1bVCoVCNEnI6ne/L8bmJ8EDfFgCAiJBSjyJMEIkJIkWnYkpa0yXTNDnTNLm0pkvRqZhizVPqUYSIACObY+4W6Y0JIm0nkjIRoZS3E0mZCSK5W6Q3I5tjXI2rbuHySuvpDQWU2Iw8W+pMAGhvbT5/es4Id/cPbVVVjg90e4IZJoiU1nSpXJvltKZLTBCp2xPM2JggEgA83lw4OI4rlmsEgGKxyDU2dZoAYP8r+JfsPO8yAEC/vu34L2xleN5l2IN+rwoAib1U9L/FnV1FBoBQwHfw9Y7mrvdK3/ELAHl6PvkTAHl6PvkTgIqQW4rPTg4N9G8C31gFykMe9HvVsZHw+nfIPwG4fxM8na2CBwAAAABJRU5ErkJggg==",
        "filename": "insights_tab.png",
        "alt_text": "Insights Tab",
    },
    {
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAABbUlEQVQokZ2SzUoCcRTFj47aC7SQ6QP+i3AWaTVQDUSbKBKFKDAjaOmqwoEgQ0ii2rWOViVJ4ZgTtgqCnqAiB6aoKEgcTXqEspHbIgZaqGEHzur+LufCPTYigqVS+Y0dK+ri+cVluFJ57wYAnncbQf9EdmF+dq+rs6NgsTZr8eT0LLKxvbNbrVbbUEcul+tzK7G2FA5NHwAAiAgZNRdhgkhMECm6Elfymi6ZpsmZpsnlNV2KrsQVa55RcxEiAoxSmXl80gcTREqm0jIRoZ6TqbTMBJE8PunDKJUZ1+7uXL+51Uangn4lvirH6p0JAAN93qvXQlF4fHrudzodXxgZCxSZIFJe06VGaZbzmi4xQaSRsUDRxgSRAODl/trBcVytUSIA1Go1rqd3yAQAezOwmew87zYAQL97GPwLthiedxv2wOS4CgCHR4r816LFBP0T2Z93eIc/W33HvwvQUuU2E7HludDMPvCrq0BrJf8GtB8TNijEMtcAAAAASUVORK5CYII=",
        "filename": "raster_output_error.png",
        "alt_text": "Raster Output Error",
    },
    {
        "base64": "iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMAAA7EAAAOxAGVKw4bAAABcklEQVQokZWS0StDcRTHv9u1+Qc8rGvU70G7Dwy3cGt5WZa1lSgm5XFPaLcm02QJb57lCRHtjoknpfwFyG5dQhTtbpY/YZu7jgfdkraxb52n8zmdU+djISKYyeXf2aGSnjm/uAwVCh/tAMDzDj3o9x1PT01stTlb30zWYg4enZyFV9Y3NsvlcjOqxG63l9YSi7Oh8dEdAAARIZU+DTNBJCaIFInGlYyqSYZhcIZhcBlVk+T5paTZT6VPw0QE6Lk8c7mlIhNE2t1PykSEarW7n5SZIJLLLRX1XJ5xLQ7n8s2tOjgS9CvxBTlW7UwA6O3uunp9ywqPT889NlvTJzzeQJYJImVUTaq1zayMqklMEMnjDWQtTBAJAF7ur5s4jqvU2ggAlUqF6+jsNwDAWg+sFyvPO3QA0O4e+v6CTYbnHbo1MDyUBoC9A0X+a9Bkgn7f8fc7ugZKjb7jXwJEonHltwANKbeaiM1Njo9tAz9cBRqT/Au5LRM42goJ8QAAAABJRU5ErkJggg==",
        "filename": "country_boundary_error.png",
        "alt_text": "Country Boundary Error",
    },
]

# Keep track of processed base64 strings to avoid duplicates
processed_base64 = set()

# Start replacing from the smallest (most specific) to largest patterns
for replacement in replacements:
    base64_pattern = replacement["base64"]

    if base64_pattern in processed_base64:
        continue

    # Create the full pattern to match
    full_pattern = f"data:image/png;base64,{base64_pattern}"

    # Replace all instances
    content = content.replace(full_pattern, f"images/{replacement['filename']}")
    processed_base64.add(base64_pattern)

    print(f"Replaced instances of {replacement['filename']}")

# For the remaining large screenshots, let's replace them with generic numbered images
icon_counter = 6  # Start from icon_06 (the first large screenshot)

# Find remaining base64 patterns that weren't replaced above
remaining_pattern = r"data:image/png;base64,([A-Za-z0-9+/=]+)"
remaining_matches = re.finditer(remaining_pattern, content)

for match in remaining_matches:
    full_match = match.group(0)
    base64_data = match.group(1)

    if base64_data not in processed_base64:
        # Replace with generic icon name
        replacement_path = f"images/icon_{icon_counter:02d}.png"
        content = content.replace(full_match, replacement_path)
        processed_base64.add(base64_data)
        print(f"Replaced large screenshot with {replacement_path}")
        icon_counter += 1

# Save the updated markdown file
with open("Gender_Enabling_Environments_Spatial_Tool_v1_updated.md", "w") as f:
    f.write(content)

print(
    f"\nUpdated markdown file saved as 'Gender_Enabling_Environments_Spatial_Tool_v1_updated.md'"
)
print(
    f"All base64 images have been replaced with file references to images in the 'images/' folder."
)
