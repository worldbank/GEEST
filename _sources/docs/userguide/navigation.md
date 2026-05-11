## Navigation

The GeoE3 plugin interface is intuitive and easy to navigate. In this section, the streamlined workflow ensures an efficient transition from setup to core spatial analysis. For detailed instructions on each step, refer to the sections below.

### Accessing the Plugin

---
After installing the plugin, its interface should automatically appear:
<p align="center">
  <img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Welcome_GeoE3.jpg"
    alt="Plugin Interface"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

> 1. **Locate the Toolbar Icon**  <img src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Tool%20icon.jpg" alt="Toolbar Icon" style="width:5%;" title="Click to enlarge" onclick="window.open(this.src, '_blank')">
> Find the plugin’s icon in the QGIS toolbar.
>
> 2. **Open the Plugin**
> Click on the plugin’s toolbar icon to open its main window.

### Project Setup

---
Once the plugin window is open, press the right arrow buttons highlighted in red to navigate through the pages:

<p align="center">
  <img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Welcome_GeoE3_navigation.jpg"
    alt="First Page Next"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

- **Welcome to GeoE3 Page**: This is the introductory page of the plugin, providing an overview of its purpose and functionality. It serves as the starting point to familiarize users with the plugin's capabilities and its relevance to geospatial analysis.

- **About Page**: This page offers detailed information about the plugin, including its contributors, development background, and licensing. It highlights the open-source nature of the tool and acknowledges the organizations or individuals involved in its creation.

#### GeoE3 Project Selection

In this step, you need to select a project folder to begin your work. The plugin provides you with two options:

<p align="center">
<img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Project_Selection.jpg"
    alt="GeoE3 Project"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

Option 1: **Open an Existing Project**:
   Select this option if you already have a project folder created previously. Choosing this will load the project along with all its associated files. Once loaded, press the right arrow button to proceed to the data input and processing interface for further analysis.

Option 2: **Create a New Project**:
   Choose this option to start a new project. The plugin will guide you through creating a new folder that will store the GeoE3 project files and working analysis results for spatial processing.

<p align="center">
 <img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Project_Selection_2.jpg"
    alt="New GeoE3 Project"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
   <img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Project_Selection_3.jpg"
    alt="New GeoE3 Project"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

---
 Important Considerations

- ⚠️ **Warning**: Ensure the folder is **empty**. Using a folder with other files may lead to errors or accidental overwrites.
- 💡 **Tip**: Use a descriptive name for the folder, incorporating details such as the name of the country or region you want to analyze and a timestamp. The timestamp could reflect either the time of the analysis process or the date of the input datasets. This will help you easily identify the folder for future reference and maintain better organization.
- 🔒 **Reminder**: Ensure the folder is stored in a location with adequate storage space for analysis outputs. The contents of the selected folder will be managed by the plugin, ensuring proper organization of project-related files.

---

##### Additional Steps After Creating the Folder

> - **Select a Layer**:
>   - Click on the three dots button to choose a layer containing your Admin0 areas (country or region boundaries). The input layer must be in either SHP or GPKG format. Once selected, use the dropdown menu to specify the column that contains the names of the areas. Ensure the column is correctly populated to avoid errors during analysis.
>
> - **Set the Analysis Cell Size**:
>   - Enter a value between **100m and 1000m**:
>     - Smaller values (e.g., 100m) will provide **more detailed results but require longer processing times**.
>     - Larger values (e.g., 1000m) will **reduce processing time but result in coarser outputs**.
>
> - **Coordinate System Configuration**:If your boundary layer uses a valid **projected CRS** (e.g., UTM or EPSG:3857), select the checkbox **Use Coordinate System of your boundary layer**. This ensures that spatial calculations, such as distances and areas, are accurate and aligned with your layer's CRS.

---
- ⚠️ **Note**: This option is automatically disabled if the map units of your boundary layer are in degrees (e.g., EPSG:4326). Spatial analysis requires projected coordinate systems with units in meters for precision.
- 💡 **Tip**: If your data uses geographic coordinates (latitude/longitude in degrees), reproject it to a projected CRS before proceeding with the analysis.
---

### Pre-Processing

> - Locate the **right arrow button** at the bottom-right corner of the interface (highlighted in red in the image).
> - Clicking this button confirms all selected settings and initiates the first step of the processing workflow — splitting the study area into grids. After the area is successfully split into grids, the interface transitions to the **Processing Data Interface**, where you can initiate the main analysis.
<p align="center">
 <img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/StudyArea_Creation.jpg"
    alt="New GeoE3 Project"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">  
</p>
> - Now the process of splitting the area into grids has started, and a progress bar is displayed in the interface. Once completed, a report titled **Study Area Report** will open automatically. This report, along with all grid-splitting outputs, is saved in the project directory under the `/study_area` folder. This report summarizes the processing time and provides an explanation of each generated output, including: study area bounding boxes, polygons, grid cells and processing chunks.

<p align="center">
 <img src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/StudyArea_report.jpg"
    alt="GeoE3 Project final"
    style="width:55%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

> - **Download or select the road network**: To conduct the analysis for the Accessibility dimension, a road network is required. The process uses geospatial area analysis based on road network data to evaluate accessibility. If you have a key to use the ORS service, you can input it here. Alternatively, you can provide this data in two ways: either upload an existing road network or download it directly from OpenStreetMap (OSM) by clicking the **Download from Open Street Map** button. Once the download is complete, proceed by clicking the arrow in the bottom-right corner to continue.

<p align="center">
 <img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/RoadNetwork.jpg"
    alt="New GeoE3 Project"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
<img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/RoadNetwork2.jpg"
    alt="New GeoE3 Project"
    style="width:45%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
  
</p>

### Processing Data Interface

---
The data processing interface serves as the central hub for managing, configuring, and processing inputs across multiple dimensions and factors within the project. This interface is designed to streamline workflows and provide users with a clear overview of the processing status. Below is a guide to understanding the key components of this interface:

<p align="center">
 <img src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Nav_understand.jpg"
    alt="GeoE3 data processing"
    style="width:65%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

**🖥️ Key Elements of the Interface**

<table border="1" style="border-collapse: collapse; width: 100%; text-align: left;">
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;"><strong>1. The Three Dimensions</strong></td>
    <td style="border: 1px solid black;">The interface organizes the analysis into three primary dimensions: <strong>Contextual</strong>, <strong>Accessibility</strong>, and <strong>Place Characterization</strong>.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;"><strong>2. Fifteen Factors</strong></td>
    <td style="border: 1px solid black;">Each dimension consists of factors representing the main themes of analysis.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;"><strong>3. Fourteen Subfactors</strong></td>
    <td style="border: 1px solid black;">Certain factors include subfactors for additional granularity.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td rowspan="6" style="border: 1px solid black;"><strong>4. Processing Status Widgets</strong></td>
    <td style="border: 1px solid black;">- <strong>4a Configured, not run</strong>: Inputs are set up but processing has not started.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;">- <strong>4b Required and not configured</strong>: Essential inputs are missing and need configuration.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;">- <strong>4c Completed successfully</strong>: Processing finished without errors.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;">- <strong>4d Workflow failed</strong>: The process encountered an error and requires troubleshooting.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;">- <strong>4e Not configured (optional)</strong>: Inputs are optional and not configured.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;">- <strong>4f Excluded from analysis</strong>: Intentionally excluded factors or subfactors.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td rowspan="2" style="border: 1px solid black;"><strong>5. Run All/Run Incomplete</strong></td>
    <td style="border: 1px solid black;">- <strong>Run All</strong>: Executes all workflows, regardless of configuration or status.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;">- <strong>Run Incomplete</strong>: Focuses only on workflows that are incomplete.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;"><strong>6. Project Setup Pages</strong></td>
    <td style="border: 1px solid black;">The <strong>Project</strong> button opens setup pages to configure the project folder and analysis parameters.</td>
  </tr>
  <tr style="border: 1px solid black;">
    <td style="border: 1px solid black;"><strong>7. Help</strong></td>
    <td style="border: 1px solid black;">Clicking the <strong>Help</strong> button redirects to the tool’s GitHub page for detailed documentation and support resources.</td>
  </tr>
</table>

<br>

**🗂️ Key Considerations**

| Consideration               | Details                                                                                  |
|-----------------------------|------------------------------------------------------------------------------------------|
| 📁 **Organize Your Folder** | Ensure your project folder is empty before starting to avoid accidental overwrites.       |
| 🕒 **Start with Large Cells**| Begin with larger cell sizes for initial testing and refine later for greater detail.     |
| 🖥️ **Monitor Progress**    | Use status widgets to track progress and troubleshoot errors promptly.                   |
| 📖 **Use Help Resources**   | Refer to the Help section or GitHub documentation for additional support.                |

By keeping these considerations in mind, you can ensure a smooth and efficient workflow while minimizing errors and maximizing the utility of the GeoE3 plugin.
