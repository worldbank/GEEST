## Contextual

<p align="justify">
The Contextual Dimension refers to the laws and policies that shape workplace gender discrimination, financial autonomy, and overall gender empowerment. Although this dimension may vary between countries due to differences in legal frameworks, it remains consistent within a single country, as national policies and regulations are typically applied uniformly across countries.  For more information on data input used from open sources, please refer to the
    <a href="https://worldbank.github.io/GEOE3/docs/userguide/datacollection.html" target="_blank">Data Collection section</a>.
</p>

### Input Contextual factors

### > - If the analysis is generic, GeoE3 utilizes the EPLEX score of a country.
---
<p align="justify">EPLEX is a summary measure of Employment Protection Legislation (EPL) stringency, created by the International Labour Organization (ILO) that measures how strongly a country's laws protect workers against dismissal at the initiative of an employer.
<p align="center">
<img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Contextual_dm.jpg"
    alt="Contextual Weights"
    style="width:75%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>
<p align="center">
<img width="369" height="189" alt="image" src="https://github.com/user-attachments/assets/23240df3-f294-4310-9259-c47a8eebd849" />
</p>

### > - If the analysis is tailored for Women's Enabling Environments, GeoE3 utilizes data from the WBL database, as follows:
---
<p align="justify">
<strong>Workplace Discrimination</strong> involves laws that address gender biases and stereotypes that hinder women's career advancement, especially in male-dominated fields and it is btained from the Workplace Index score of the WBL.
</p>
<p align="justify">
<strong>Regulatory Frameworks</strong> pertain to laws and policies that protect women’s employment rights, such as childcare support and parental leave, influencing their workforce participation.This indicator is composed by the Workplace Index score of the WBL database.
</p>
<p align="justify">
<strong>Finacial Inclusion</strong> involves laws concerning women’s access to financial resources like loans and credit, which is crucial for starting businesses and investing in economic opportunities. This indicator is composed by the Workplace Index score of the WBL 2024.
</p>
The conversion of the WBL scores to the corresponding GeoWEAF classess is represented below.
<p align="center">
<img width="420" height="209" alt="image" src="https://github.com/user-attachments/assets/d6b223bf-25dc-4e86-bb60-77c93762782c" />
</p>


---
**Additional Steps Before Processing**:

> - 🖱️🖱️ **Double-click** on the **Contextual section** to open the pop-up.
> - ⚖️ **Assign Weights**: Ensure the **weights** are correctly assigned, as they determine the relative importance of each factor in the analysis. Carefully review these values to ensure they are aligned with your project's objectives and reflect the significance of each factor accurately.
> - 🚫 **Exclude Unused Factors**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - 🔄 **Readjust Weights**: After excluding any factors, make sure to **Balance Weights** of the remaining factors. This step ensures the weight distribution remains balanced and totals correctly, preserving the integrity of the analysis, then click **OK** to proceed.

### Process Contextual factors

---
After entering the values for the factors and adjusting their weights to achieve balance, you can initiate the process workflow:

> - 🖱️**Right-click on Contextual**.
> - ▶️**Select Run Item Workflow** from the context menu.

<p align="center">
<img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Contextual_dm2.jpg"
    alt="Contextual Run"
    style="width:55%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets.

### Visualizing the Outputs

---
<p align="justify">
After completing the process, the outputs are automatically added to the Layer Panel in QGIS as a group layer. This group layer has the <i>Mutually Exclusive Group</i> feature activated, which ensures that only one layer within the group can be visible at a time. When this feature is enabled, turning on the visibility of one layer automatically turns off the visibility of the others within the same group, making it easier to compare results without overlapping visualizations.

The outputs consist of the Workplace Discrimination, Regulatory Frameworks, and Financial Inclusion factors, as well as the aggregation of these three factors into the final Contextual output. All scores are assessed on a scale from 0 to 5, categorized as follows: **≤ 0.5 (Not Enabling) | 0.5–1.5 (Very Low Enablement) | 1.5–2.5 (Low Enablement) | 2.5–3.5 (Moderately Enabling) | 3.5–4.5 (Enabling) | 4.5–5.0 (Highly Enabling)**.
</p>

<p align="center">
<img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Contextual_dm1.jpg"
    alt="Contextual Final Output"
    style="width:75%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

<p align="justify">
The outputs are stored under the Contextual folder within the project folder created during the setup phase as raster files. These files can be shared and further utilized for various purposes, such as visualization in QGIS or other GIS software, integration into reports, overlaying with other spatial datasets, or performing advanced geospatial analyses, such as identifying priority areas or conducting trend analysis based on the scores.

If the results do not immediately appear in the Layer Panel after processing the Contextual Dimension, you can resolve this by either adding them manually from the folder path or by right-clicking on the Contextual Dimension and selecting **Add to map** from the context menu. There is also an option to directly open the working folder from within the interface:
</p>

<p align="center">
<img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/Contextual_dm3.jpg"
    alt="Contextual Add to map"
    style="width:55%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

> 💡 **Tip**: If the input values need to be changed for any reason (e.g., incorrect initial input), you can clear the results and reprocess them as follows:
>
> - 🖱️ **Right-click** on the factor/dimension and select **Clear Item**.
> - 🖱️ **Right-click again** on the same cleared factor/dimension, and while holding the **SHIFT** key on your keyboard, select **Run Item Workflow**.
> This process ensures that the tool reassesses the input values and outputs the corrected scores.

<p align="center">
<img
    src="https://raw.githubusercontent.com/worldbank/GEOE3/main/docs/images/new%20images/CD%20clear%20and%20rerun.jpg"
    alt="Contextual Clear and rerun"
    style="width:75%;"
    title="Click to enlarge"
    onclick="window.open(this.src, '_blank')">
</p>

### Key Considerations

---

- **Input Accuracy**: Ensure all input values are carefully entered and correspond to the correct indices (e.g., Workplace Discrimination, Regulatory Frameworks, Financial Inclusion). Incorrect data will impact the outputs and subsequent analysis.

- **Weight Adjustment**: Assign weights thoughtfully to reflect the importance of each factor in the overall analysis. After making changes, always balance the weights to ensure they sum up correctly.
