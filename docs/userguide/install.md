# Installing GEEST

Follow the steps below to install the GEEST QGIS plugin.

### Step 1: Open the Plugin Manager in QGIS

> - 1. Launch QGIS.
> - 2. Go to **Plugins** > **Manage and Install Plugins…**.

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/plugins.JPG" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/plugins.JPG" alt="QGIS Plugin Setup" width="500" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>

### Step 2: Install the Plugin

> - 1. In the **Plugin Manager** window, select the **All** tab in the Plugin Manager.
> - 2. Search for `GEEST`.
> - 3. Select the plugin and click **Install Plugin**.

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Install_page_plugin.png" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Install_page_plugin.png" alt="QGIS Plugin Installation" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>

### Step 3: Verify the Installation and Configure the Tool

> - 1. After installation, check the QGIS toolbar for the new **GEEST** icon *Show/Hide GEEST Panel*. [![GEEST Toolbar Icons](https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/icons.jpg)](https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/icons.jpg "Click to enlarge")
> - 2. If the icon is not visible, go to **Plugins** > **Manage and Install Plugins…**, then click on the **Installed** tab.
> - 3. In the list, find **Gender Enabling Environments Spatial Tool (GEEST)** and ensure the checkbox is ticked. The GEEST panel should now appear in the QGIS interface.

<p align="center">
  <a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Install_page_show.png" target="_blank">
    <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Install_page_show.png" alt="QGIS Plugin Installation" width="600" title="Click to enlarge">
  </a>
</p>

> - 4. Optionally, you can customize the plugin's behavior by navigating to:  
>   **Settings Menu** → **Options** → **GEEST Settings**. While the **default settings are recommended**, the following configurable sections are available:  
>
>       ▪︎ **Chunk size**  
>       Determines how many cells are processed at once. For example, a chunk size of `10` processes 10×10 cell blocks. Increasing this value (e.g., to `50`) can improve performance on powerful machines, but may slow down or crash QGIS on lower-spec systems.  
>
>       ▪︎ **Analysis Options – Assign 0 to cells by default**  
>       If checked, areas without data will be assigned a value of 0. If unchecked, those areas will be left as NoData. This is useful for consistent raster outputs when comparing or summing layers.  
>
>       ▪︎ **User Interface Options**  
>       ▫︎ **Show layer when clicking an item in the GEEST tree**  
>   Automatically activates the corresponding layer in QGIS when selected in the GEEST panel.  
>
>       ▫︎ **Show canvas overlay with current layer details**  
>       Enables an overlay that provides quick visual feedback about selected layers.  
>
>       ▪︎ **Advanced Options – Concurrent Tasks**  
>       Specifies how many processing threads to run simultaneously. Set this equal to the number of CPU cores for efficient performance (e.g., 4 or more on most systems).  
>
>       ▫︎ **Enable developer mode**  
>       Intended for debugging — attaches the plugin to a remote debugger. ⚠️ Not recommended unless you're actively developing the plugin.  
>
>       ▫︎ **Verbose logging mode**  
>       Enables detailed logging useful for troubleshooting and diagnostics. Requires a restart to take effect.  

<a href="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Install_page_settings.png" target="_blank">
  <img src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Install_page_settings.png" alt="GEEST Settings" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>


