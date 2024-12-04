# Installing GEEST

Follow the steps below to install the GEEST QGIS plugin using the custom repository.

### Step 1: Open the Plugin Manager in QGIS

1. Launch QGIS.
2. Go to **Plugins** > **Manage and Install Plugins…**.

<a href="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/plugins.JPG" target="_blank">
  <img src="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/plugins.JPG" alt="QGIS Plugin Setup" width="500" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>


### Step 2: Add a New Plugin Repository

1. In the **Plugin Manager** window, select the **Settings** tab.
2. Ensure the **Show also Experimental Plugins** option is checked.
3. Under **Plugin Repositories**, click on **Add…**.

<a href="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/plugins%20settings.jpg" target="_blank">
  <img src="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/plugins%20settings.jpg" alt="QGIS Plugin Settings" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>


### Step 3: Enter Repository Details

In the **Repository Details** window:

- **Name**: Enter `GEEST` (or any other name you prefer).
- **URL**: Paste the following URL:  
  `https://raw.githubusercontent.com/worldbank/GEEST/refs/heads/main/docs/repository/plugins.xml`
- Ensure the **Enabled** checkbox is checked.
- Click **OK** to save.

<a href="https://github.com/worldbank/GEEST/raw/main/docs/images/new%20images/repository.jpg" target="_blank">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/images/new%20images/repository.jpg" alt="QGIS Repository Settings" width="400" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>





### Step 4: Install the Plugin

1. Return to the **All** tab in the Plugin Manager.
2. Search for `GEEST` (or the plugin name).
3. Select the plugin and click **Install Experimental Plugin**.

<a href="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/install.jpg" target="_blank">
  <img src="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/install.jpg" alt="QGIS Plugin Installation" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>



### Step 5: Verify the Installation and Configure the Tool

1. After installation, check the QGIS toolbar for the new **GEEST** icons. You should see options like **GEEST Settings** and **GEEST Debug Mode** (as shown in the image below).

   [![GEEST Toolbar Icons](https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/icons.jpg)](https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/icons.jpg "Click to enlarge")

2. In the **GEEST Settings** window, locate the **API Key for the Open Route Service** field. Enter your ORS API key here to enable access to routing services.

> **Note:** To obtain an ORS API key, visit the [OpenRouteService website](https://openrouteservice.org/). This API key is essential for enabling routing services within the GEEST tool.


3. **Optional**: Adjust other settings as needed, such as **Concurrent Tasks**, **Enable Editing**, and **Verbose Logging Mode**, to enhance performance and debugging.


<a href="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/geest%20settings.jpg" target="_blank">
  <img src="https://github.com/elbeejay/draft-docs/raw/main/docs/images/new%20images/geest%20settings.jpg" alt="GEEST Settings" width="600" style="display: block; margin-left: auto; margin-right: auto;" title="Click to enlarge">
</a>


