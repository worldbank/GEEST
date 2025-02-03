# Installing GEEST

Follow the steps below to install the GEEST QGIS plugin using the custom repository.

### Step 1: Open the Plugin Manager in QGIS

> - 1. Launch QGIS.
> - 2. Go to **Plugins** > **Manage and Install Plugins…**.

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/plugins.JPG" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/plugins.JPG" alt="QGIS Plugin Setup" width="500" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>

### Step 2: Add a New Plugin Repository

> - 1. In the **Plugin Manager** window, select the **Settings** tab.
> - 2. Ensure the **Show also Experimental Plugins** option is checked.
> - 3. Under **Plugin Repositories**, click on **Add…**.

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/plugins%20settings.jpg" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/plugins%20settings.jpg" alt="QGIS Plugin Settings" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>


### Step 3: Enter Repository Details

> - In the **Repository Details** window:
>   - **Name**: Enter `GEEST` (or any other name you prefer).
>   - **URL**: Paste the following URL:  
>   - <span style="color: red;">`https://raw.githubusercontent.com/worldbank/GEEST/refs/heads/main/docs/repository/plugins.xml`</span>
>   - Ensure the **Enabled** checkbox is checked.
>   - Click **OK** to save.

<a href="https://github.com/worldbank/GEEST/raw/main/docs/images/new%20images/repository.jpg" target="_blank">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/images/new%20images/repository.jpg" alt="QGIS Repository Settings" width="400" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>


### Step 4: Install the Plugin

> - 1. Return to the **All** tab in the Plugin Manager.
> - 2. Search for `GEEST` (or the plugin name).
> - 3. Select the plugin and click **Install Plugin**.

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/install.jpg" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/install.jpg" alt="QGIS Plugin Installation" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>

### Step 5: Verify the Installation and Configure the Tool

> - 1. After installation, check the QGIS toolbar for the new **GEEST** icon *Show/Hide GEEST Panel*. [![GEEST Toolbar Icons](https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/icons.jpg)](https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/icons.jpg "Click to enlarge")
> - 2. In the **GEEST Settings** window, locate the **API Key for the Open Route Service** field. Enter your ORS API key here to enable access to routing services.
>   - **Note:** To obtain an ORS API key, visit the [OpenRouteService website](https://openrouteservice.org/). This API key is essential for enabling routing services within the GEEST tool.
> - 3. **Optional**: **The default settings are recommended** but you can adjust other settings as needed, such as **Study Area Preparation Options**, **Analysis
Options** and **User Interface Options**, to enhance performance and debugging:
>   - *Chunk Size*: Specifies how the study area is divided into smaller sections (chunks) for processing. For example, a chunk size of 10 means the area will be processed in chunks of 10x10 cells. Larger chunk sizes can speed up processing but require more memory, while smaller chunks are slower but less memory-intensive.
>   - *Assign 0 to cells by default*: When enabled, cells without data are assigned a value of 0 during analysis. If unchecked, such cells are treated as "no data," meaning they are excluded from calculations. This option ensures clarity in areas where no data is present.
>   - *Show layer when clicking an item in the Geest tree*: Automatically displays the associated layer in the map view when an item is selected in the Geest tree. This feature improves usability by providing visual feedback for selected layers.
>   - *Advanced Options*:
>     - *Concurrent Tasks*: Controls the number of threads (tasks) that can run simultaneously during analysis. A value of 1 means tasks are executed sequentially (one at a time). Higher values (e.g., matching the number of CPU cores) can speed up processing but may require a more powerful machine.
>     - *Enable Developer Mode*: Intended for developers to debug the plugin using a remote debugger. **Important Note**: Should only be enabled if a remote debugger is set up. Enabling this without proper setup can block QGIS startup. When active, it creates a debug log tab for tracking issues.
>     - *Verbose Logging Mode*: Adds detailed log messages during processing, which are helpful for diagnosing issues. This option is useful when troubleshooting but can slow down performance due to the extra logging.


<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/geest%20settings.jpg" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/geest%20settings.jpg" alt="GEEST Settings" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>


