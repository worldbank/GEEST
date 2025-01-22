## Navigation

### Accessing the Plugin

After installing the plugin, its interface should automatically appear:  
<p align="center">
  <img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/First%20page.jpg" 
    alt="Plugin Interface" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

1. **Locate the Toolbar Icon**  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Tool%20icon.jpg" alt="Toolbar Icon" style="width:5%;" title="Click to enlarge" onclick="window.open(this.src, '_blank')">  
   Find the plugin’s icon in the QGIS toolbar.

2. **Open the Plugin**  
   Click on the plugin’s toolbar icon to open its main window.

### Navigating the Plugin Window

Once the plugin window is open, press the right arrow buttons highlighted in red to navigate through the pages:

<p align="center">
  <img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/First%20page%20next.jpg" 
    alt="First Page Next" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
  <img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Second%20page%20next.jpg" 
    alt="Second Page Next" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

> - **Welcome to GEEST Page**: This is the introductory page of the plugin, providing an overview of its purpose and functionality. It serves as the starting point to familiarize users with the plugin's capabilities and its relevance to geospatial analysis.
>
> - **About Page**: This page offers detailed information about the plugin, including its contributors, development background, and licensing. It highlights the open-source nature of the tool and acknowledges the organizations or individuals involved in its creation.

### Setting Up the ORS Key

To use the GEEST plugin effectively, you need to configure the **Open Route Service (ORS)** API key. The ORS platform is used for spatial analysis workflows, and obtaining an API key is a simple and free process. Below are the steps:

---

#### **Step 1: Get Your API Key**
1. Open your browser and go to the [ORS API Key Signup Page](https://openrouteservice.org/sign-up/).
2. Register for an account or log in if you already have one.
3. Once logged in, generate an API key by following the on-screen instructions.

#### **Step 2: Paste the API Key**
> **Note**: If you already entered your ORS API key in **Step 5: Verify the Installation and Configure the Tool** under the **[Installing GEEST](https://github.com/worldbank/GEEST/blob/main/docs/userguide/install.md)** instructions, the key will automatically appear here. In this case, you can skip this step and proceed to the next one.
1. Copy the API key from the ORS website.
2. Open the **GEEST ORS Setup** window in the plugin.
3. Paste the API key into the text box provided (as shown in the screenshot below).

<p align="center">
 <img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/ORS%20setup.jpg" 
    alt="ORS key" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

#### **Step 3: Verify the Key**
1. After pasting the API key, click the **Check my key...** button.
2. If the key is valid, a green checkmark will appear, indicating the API key has been successfully set up.

---

> #### **Tips for Setting Up the ORS Key**
> - 💡 **Tip**: Ensure you paste the exact API key without any extra spaces or characters.
> - ⚠️ **Warning**: Avoid sharing your API key publicly to keep it secure.
> - 🔄 **If You Encounter Issues**: Double-check your internet connection and ensure your API key is valid.
> - **This step is crucial to unlock the full functionality of the plugin, including advanced spatial analysis workflows.**
---

### GEEST Project Selection

In this step, you need to select a project folder to begin your work. The plugin provides you with two options:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/GEEST%20project.jpg" 
    alt="Geest Project" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

**Option 1: Open an Existing Project**:  
   Select this option if you already have a project folder created previously. Choosing this will load the project along with all its associated files. Once loaded, press the right arrow button to proceed to the data input and processing interface for further analysis.
   
<p align="center">
 <img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/GEEST%20project%20open.jpg" 
    alt="Open Geest Project" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

**Option 2: Create a New Project**:  
   Choose this option to start a new project. The plugin will guide you through creating a new folder that will store the GEEST project files and working analysis results for spatial processing.
     
<p align="center">
 <img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/GEEST%20project%20new.jpg" 
    alt="New Geest Project" 
    style="width:50%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

**How to Create a New Folder**
- Click on **Create or select a project directory** (highlighted in red).
- Navigate to the desired location on your system where you want to store the project.
- Create a **new folder** and ensure it is **empty**.
- Select the newly created folder and confirm your choice.

---
> **Important Considerations**
> - ⚠️ **Warning**: Ensure the folder is **empty**. Using a folder with other files may lead to errors or accidental overwrites.
> - 💡 **Tip**: Use a descriptive name for the folder, incorporating details such as the name of the country or region you want to analyze and a timestamp. The timestamp could reflect either the time of the analysis process or the date of the input datasets. This will help you easily identify the folder for future reference and maintain better organization.
> - 🔒 **Reminder**: Ensure the folder is stored in a location with adequate storage space for analysis outputs. The contents of the selected folder will be managed by the plugin, ensuring proper organization of project-related files.

---


#### **Additional Steps After Creating the Folder**

- **Select a Layer**: Click on the three dots button to choose a layer containing your Admin0 areas (country or region boundaries). The input layer must be in either SHP or GPKG format. Once selected, use the dropdown menu to specify the column that contains the names of the areas. Ensure the column is correctly populated to avoid errors during analysis.
  
- **Set the Analysis Cell Size**:
   - Enter a value between **100m and 1000m**:
     - Smaller values (e.g., 100m) will provide more detailed results but require longer processing times.
     - Larger values (e.g., 1000m) will reduce processing time but result in coarser outputs.
    
 ---
  > - 💡 **Tip**: For larger regions or countries, it is recommended to start with a larger cell size for initial testing to ensure faster processing times. Once the initial results are satisfactory, refine the analysis by reducing the cell size to achieve greater detail. This approach will help you unlock the full potential of the tool and ensure accurate and detailed outputs.
---      

- **Coordinate System Configuration**:

   - <span style="color: red;">If your boundary layer uses a valid **projected CRS** (e.g., UTM or EPSG:3857), select the checkbox **Use Coordinate System of your boundary layer**. This ensures that spatial calculations, such as distances and areas, are accurate and aligned with your layer's CRS.</span>

---   
  > - <span style="color: red;">⚠️ **Note**: This option is automatically disabled if the map units of your boundary layer are in degrees (e.g., EPSG:4326). Spatial analysis requires projected coordinate systems with units in meters for precision.</span> 
  > - <span style="color: red;">💡 **Tip**: If your data uses geographic coordinates (latitude/longitude in degrees), reproject it to a projected CRS before proceeding with the analysis.</span>
--- 

    
### Proceed to the Processing Data Interface

Once you have completed all required inputs on the **GEEST Project Creation** screen, follow these steps to proceed:

---

#### **1. Verify the Project Folder Path**
- Ensure that the **folder path** displayed at the bottom of the interface is correct. This path indicates where the GEEST plugin will store analysis outputs and working files.
- **Example Path**:  
  `C:/Work/GEEST/Analysis/Country/01152025`

**Important Notes**:
- The folder must be **empty**, containing no other files unrelated to the analysis.
- Choose a **descriptive name** for the folder, as it will store critical project data.

---

#### **2. Click the Right Arrow Button**
- Locate the **right arrow button** at the bottom-right corner of the interface (highlighted in red in the image).
- Clicking this button confirms all settings and transitions to the **Processing Data Interface**, where you can initiate the analysis.

<p align="center">
 <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/GEEST%20project%20final.jpg"
    alt="Geest Project final" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

---

> ### Key Considerations
> - ⚠️ **Warning**: Double-check your settings and input data before clicking the arrow. Any incorrect configuration could lead to errors during the processing stage.
> - 💡 **Tip**: Ensure that the analysis cell size and boundary layer are correctly configured to avoid unexpected results.

---

### Overview of Next Steps

After pressing the right arrow, the plugin will begin processing the input boundary layer by dividing it into a grid based on the specified cell size. During this step, the project folder will automatically populate with the generated outputs, including the study area split into grids, polygons, gridded areas, bounding boxes and other relevant data.

Once this pre-processing step is completed, you will seamlessly transition to the **Processing Data Interface**, where you can proceed with the core analysis workflows:

1. The tool will generate outputs based on the inputs and configuration you’ve provided.
2. View progress bars for analysis steps.
3. Results will be saved in the selected project folder for further use.

<p align="center">
 <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/GEEST%20data%20processing%20UI.jpg"
    alt="Geest data processing" 
    style="width:30%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

This marks the completion of the project setup and transition to the core analysis workflow.














```{tableofcontents}
```
