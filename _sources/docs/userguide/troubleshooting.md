## Troubleshooting

### ACCESSIBILTY TABS PERMISSIONS ERROR

![image](https://github.com/worldbank/GEEST/assets/120469484/63edfc18-8294-478c-bcc5-1a4f28c07711)

This error occurs when some of the shapefiles produced in the temp folder of the working directory are trying to be overwritten or deleted but can't because it's still being stored in QGIS's memory. This can occurs even when the layer is removed from the QGIS table of contents.

**This error may also occur when the tool runs correctly so first check if the desired output file was produced in the working directory.**

If the file is not produced you can try the following:
- Delete the *temp* folder in the working directory
- If you cannot delete the *temp* folder you will have to close QGIS and open it again, complete the setup tab, go back to the tab where the error occurred and re-run the tab again.

### QGIS PLUGIN/INTERFACE WIDGETS AND TEXT ARE DISTORTED AND SCALED INCORRECTLY
![image](https://github.com/worldbank/GEEST/assets/120469484/e195416b-ee86-4998-9ca5-a4784f7c724e)

This is a problem linked to display settings caused by the connection of multiple monitors and/or varying display scales and resolutions, rather than a QGIS or plugin-related issue. This is backed by a Microsoft support post, linked [here](https://support.microsoft.com/en-gb/topic/windows-scaling-issues-for-high-dpi-devices-508483cd-7c59-0d08-12b0-960b99aa347d), highlighting the issues that may be experienced when using a high-DPI device, such as a 4k monitor. Additionally, in the scaling display setting, Microsoft indicates that entering a custom scaling size between 100% - 500% is not recommended as "...it can cause text and apps to become unreadable."

![image](https://github.com/worldbank/GEEST/assets/120469484/248fde5c-dd1a-41d0-94ad-2ace20a74f95)

Possible solutions to this are:
- Adjust the scale for all monitors to 100%.
- Ensure that the display resolution is the same for both monitors. i.e. If the smallest monitor is set to 1920 x 1080 set the 4k monitor to this display resolution as well.

### RASTER OUTPUTS NOT BEING LOADED AND DISPLAYING CORRECTLY

![image](https://github.com/worldbank/GEEST/assets/120469484/10de6c72-f8f6-47b8-adb3-930f5c625f66)

Occasionally, some of the outputs automatically loaded to the QGIS table of contents do not display correctly. To correct this, try removing the layer that is displayed incorrectly and add it again to QGIS.

### ERROR: OUTPUT DIRECTORY NOT SET

![image](https://github.com/worldbank/GEEST/assets/120469484/b2f2959e-85c4-4e89-8493-dac2b9a20f07)

If you see the following error message, please check if your output directory has been set in the "Setup" tab.

### ERROR: COUNTRY BOUNDARY POLYGON NOT SET

![image](https://github.com/worldbank/GEEST/assets/120469484/75882e9d-a9af-43fc-9f68-0293c75b49b3)

If you see the following error message, please check if you're country boundary polygon layer has been set in the "Setup" tab.

### ERROR: CO-ORDINATE REFERENCE SYSTEM (CRS) NOT SET

![image](https://github.com/worldbank/GEEST/assets/120469484/120c0cf9-e526-4d8b-adff-de3a9d2f7fb8)

If you see the following error message, please check if you're CRS has been set in the "Setup" tab.

### ALTERNATIVE WAY TO REFRESH THE PLUGIN IF IT FREEZES OR DOES NOT RUN AS EXPECTED

1. Install the "Plugin Reloader" plugin.

   1.1 Navigate to and open “Manage and Install Plugins…” under the plugins tab in QGIS.

   1.2 In the search bar type “plugin reloader”.

   1.3 Select the “Plugin Reloader” plugin and click on the install button.


![image](https://github.com/worldbank/GEEST/assets/120469484/801db189-92ca-4755-a79f-8898b2e43a2f)

 1.4 Navigate to the "Plugin Reloader" configuration window under the Plugins tab.

*Plugins* → *Plugin Reloader* → *Configure*

 1.5 From the drop-down list select the "gender\_indicator\_tool" plugin and press "OK".

![image](https://github.com/worldbank/GEEST/assets/120469484/3dc21c04-2ebe-4b33-92bc-1020746ee9e3)

  1.6 If you encounter an unexpected error in the tool that has not been mentioned in any of the previous troubleshooting sections you can try runing the "plugin reload" tool

![image](https://github.com/worldbank/GEEST/assets/120469484/80e1ae57-8608-4392-8df2-46e5b5d4789e)

**OR**

**If the "Plugin Reloader" does not resolve the error close QGIS, restart it again, and re-run the process you were trying to execute.**