## Install the tool

## Install QGIS

1. The link below will take you to the QGIS website where you will be able to download the QGIS installation file. Note that it is possible to use older versions of QGIS, e.g. Version 3.32 - Lima.

QGIS website: [https://www.qgis.org/en/site/](https://www.qgis.org/en/site/)

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/installQGIS.jpg" alt="Install QGIS">
</p>


2. Once the installation file is downloaded run the installation file.

3. A pop-up window as seen in the image below should show up. Follow the prompts and leave all settings on default.

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/qgis-setup.jpg" alt="QGIS Setup">
</p>


## Install Open Route Service (ORS) plugin

1. Open QGIS, navigate to the "Plugins" tab and select the "Manage and Install Plugins…" option from the drop-down menu.

<p align="center">
  <img src="https://github.com/worldbank/GEEST/raw/main/docs/pictures/installORS.jpg" alt="install ORS">
</p>

2. The "Plugins" pop-up window should appear as seen in the image below.

3. In the search bar type "ORS", select the "ORS Tool" from the list of plugins, and select the install button to install the plugin.

![image](https://github.com/worldbank/GEEST/assets/120469484/6274c002-9b56-4374-8fd4-9278d2246afb)

4. You will now have to set up an account on the Open Route Service website which can be accessed by clicking the link below.

ORS website: [https://openrouteservice.org/](https://openrouteservice.org/)

ORS Sign up: [https://openrouteservice.org/dev/#/signup](https://openrouteservice.org/dev/#/signup)

![image](https://github.com/worldbank/GEEST/assets/120469484/79728902-e5ba-49c1-a262-32cd9df628a6)

5. Fill in all the necessary fields to sign up and then log into your account.

6. Request a standard token and provide a name for the Token.

![image](https://github.com/worldbank/GEEST/assets/120469484/72eb8f24-84b5-42e9-8da7-e19bf96d410a)

7. Once the token has been created, navigate to the Dashboard tab and click on the API key as seen in the image below. The API key should now be copied to the clipboard.

![image](https://github.com/worldbank/GEEST/assets/120469484/26564e04-4520-4022-9930-4b791df8e63f)

8. In the QGIS window navigate the ORS tool and select "Provider Settings".

![image](https://github.com/worldbank/GEEST/assets/120469484/45a45354-8478-45df-b212-c477a99b2c9a)

9. The provider settings pop-up window should now appear as seen in the image below.

10. Past the API key that has been copied to the clipboard into the API Key field and press "OK".

![image](https://github.com/worldbank/GEEST/assets/120469484/b255a792-4d46-42ef-a0ff-79edb1e2fd19)

**N.B.** Additional credits can be requested on the ORS site by applying for the collaborative plan as described [here](https://openrouteservice.org/plans/). You will have to provide a brief motivation, however, if your application is in a humanitarian, academic, governmental, or not-for-profit organization, you should be eligible for the collaborative plan.

This email address can also be used for further assistance:

support@openrouteservice.heigit.org

## Installing Plugin on local device

1. Click on the green "Code" button and select the "Download ZIP" option.

![image](https://github.com/worldbank/GEEST/assets/120469484/af517d0b-8b32-43b6-a664-0bb250a1d620)

2. Once the download has been completed extract the contents of the ZIP file.

3. Navigate to your extracted ZIP folder and copy the _requirements.txt_ file.

![image](https://github.com/worldbank/GEEST/assets/120469484/6adea1a2-e63c-4067-9052-346811697828)

4. Navigate to the QGIS program folder and paste the _requirements.txt_ file into it. The file path would be similar to this: _C:\Program Files\QGIS 3.32.0_ as seen in the image under **step 5**.

5. Run the _OSGeo4W_ batch file.

![image](https://github.com/worldbank/GEEST/assets/120469484/9a8376bb-dc50-41fa-a3fd-f3e0757a3850)

6. A command line pop-up window will appear as seen in the image below.

7. Type the following into it and press Enter.
```pip install -r requirements.txt```

![image](https://github.com/worldbank/GEEST/assets/120469484/ed373467-0f80-4b75-8931-9c9e2d03d013)

8. All the Python libraries that the Plugin is dependent on will now be installed. This can take a few minutes to install.

9. Once the installations are complete you can close the command line pop-up window.

10. Open QGIS, navigate to the "Plugins" tab and select the "Manage and Install Plugins…" option from the drop-down menu.

![image](https://github.com/worldbank/GEEST/assets/120469484/39e233a5-15de-4471-9560-028cd8cde839)

11. In the plugin pop-up window navigate to the "Install from ZIP" tab.

![image](https://github.com/worldbank/GEEST/assets/120469484/9ed559bc-5672-4631-a33d-714710440819)

12. From the "Install from ZIP" tab navigate back to your extracted ZIP folder and select the "gender\_indicator\_tool" compressed (zipped) folder as seen in the image below.

![image](https://github.com/worldbank/GEEST/assets/120469484/f2e81343-1bb4-4dc1-b593-38c26726f767)

13. Once the ZIP file has been selected click on "Install Plugin".

14. Once the plugin has been installed navigate to the "All" tab.

15. In the search bar type "GEEST" and click the check box next to the "Gender Enabling Environments Spatial Tool (GEEST)" to install the plugin.

![image](https://github.com/worldbank/GEEST/assets/120469484/aac4db6e-3585-40dc-9e73-d0eb3a8bc247)

16. The plugin is now installed and you should now be able to access it in your toolbar or under the Plugin's tab as seen in the image below.

![image](https://github.com/worldbank/GEEST/assets/120469484/eceaf443-ff8b-4be0-9282-a1236a03bb86)