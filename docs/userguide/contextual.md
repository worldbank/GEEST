## Contextual

<p align="justify"> 
The Contextual Dimension refers to the laws and policies that shape workplace gender discrimination, financial autonomy, and overall gender empowerment. Although this dimension may vary between countries due to differences in legal frameworks, it remains consistent within a single country, as national policies and regulations are typically applied uniformly across countries.  For more information on data input used from open sources, please refer to the 
    <a href="https://worldbank.github.io/GEEST/docs/userguide/datacollection.html" target="_blank">Data Collection section</a>.
</p>

### Input Contextual factors
---
<p align="justify"> 
<strong>Workplace Discrimination</strong> involves laws that address gender biases and stereotypes that hinder women's career advancement, especially in male-dominated fields.
This indicator is composed by the Workplace Index score of the WBL 2024, which is then standardized on a scale from 0 to 5.
</p>

**Locate the Workplace Discrimination Section**

> - 🖱️🖱️ **Double-click** on the **Workplace Discrimination section** to open the pop-up.
> - 📝 In the *Input* field, enter the value from the **WBL2024 Workplace Index Score** and click **OK** to proceed.

     
<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/WD.jpg" 
    alt="Workplace Discrimination" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

---
<p align="justify"> 
<strong>Regulatory Frameworks</strong> pertain to laws and policies that protect women’s employment rights, such as childcare support and parental leave, influencing their workforce participation. 
This indicator is composed by the Workplace Index score of the WBL 2024, which is then standardized on a scale from 0 to 5.
</p>

**Locate the Regulatory Frameworks Section**

> - 🖱️🖱️ **Double-click** on the **Regulatory Frameworks section** to open the pop-up.
> - 📝 In the *Input* field, enter the **average** value of the **WBL2024 Pay Score and Parenthood Index Score**, then click **OK** to proceed.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/RF.jpg" 
    alt="Regulatory Frameworks" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

---
<p align="justify"> 
<strong>Finacial Inclusion</strong> involves laws concerning women’s access to financial resources like loans and credit, which is crucial for starting businesses and investing in economic opportunities. 
This indicator is composed by the Workplace Index score of the WBL 2024, which is then standardized on a scale from 0 to 5.
</p>

**Locate the Financial Inclusion Section**

> - 🖱️🖱️ **Double-click** on the **Financial Inclusion section** to open the pop-up.
> - 📝 In the *Input* field, enter the value from the **WBL2024 Entrepreneurship Index Score**, then click **OK** to proceed.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/FI.jpg" 
    alt="Finacial Inclusion" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

---
**Additional Steps Before Processing**: 

> - 🖱️🖱️ **Double-click** on the **Contextual section** to open the pop-up.
> - ⚖️ **Assign Weights**: Ensure the **weights** are correctly assigned, as they determine the relative importance of each factor in the analysis. Carefully review these values to ensure they are aligned with your project's objectives and reflect the significance of each factor accurately.
> - 🚫 **Exclude Unused Factors**: If a specific factor is not intended to be included in the process, uncheck the **Use** button associated with it.
> - 🔄 **Readjust Weights**: After excluding any factors, make sure to **Balance Weights** of the remaining factors. This step ensures the weight distribution remains balanced and totals correctly, preserving the integrity of the analysis, then click **OK** to proceed.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/Contextual_Weights.jpg" 
    alt="Contextual Weights" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

### Process Contextual factors
---
After entering the values for the factors and adjusting their weights to achieve balance, you can initiate the process workflow:

> - 🖱️**Right-click on Contextual**.  
> - ▶️**Select Run Item Workflow** from the context menu.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/CD_Run_item.jpg" 
    alt="Contextual Run" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The successful completion of the process is indicated by the green checkmark widgets, as highlighted in red in the image below:


<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/CD_run_success.jpg" 
    alt="Contextual Run Success" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

### Visualizing the Outputs 
---
After completing the process, the outputs are automatically added to the Layer Panel in QGIS as a group layer. This group layer has the *Mutually Exclusive Group* feature activated, which ensures that only one layer within the group can be visible at a time. When this feature is enabled, turning on the visibility of one layer automatically turns off the visibility of the others within the same group, making it easier to compare results without overlapping visualizations.

The outputs consist of the Workplace Discrimination, Regulatory Frameworks, and Financial Inclusion factors, as well as the aggregation of these three factors into the final Contextual output. All scores are assessed on a scale from 0 to 5, categorized as follows: ≤ 0.5 (Not Enabling) | 0.5–1.5 (Very Low Enablement) | 1.5–2.5 (Low Enablement) | 2.5–3.5 (Moderately Enabling) | 3.5–4.5 (Enabling) | 4.5–5.0 (Highly Enabling).

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/CD_final.jpg" 
    alt="Contextual Final Output" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

The outputs are stored under the Contextual folder within the project folder created during the setup phase as raster files. These files can be shared and further utilized for various purposes, such as visualization in QGIS or other GIS software, integration into reports, overlaying with other spatial datasets, or performing advanced geospatial analyses, such as identifying priority areas or conducting trend analysis based on the scores.

If the results do not immediately appear in the Layer Panel after processing the Contextual Dimension, you can resolve this by either adding them manually from the folder path or by right-clicking on the Contextual Dimension and selecting **Add to map** from the context menu:

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/CD_add2map.jpg" 
    alt="Contextual Add to map" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>


> 💡 **Tip**: If the input values need to be changed for any reason (e.g., incorrect initial input), you can clear the results and reprocess them as follows:
> - 🖱️ **Right-click** on the factor/dimension and select **Clear Item**.  
> - 🖱️ **Right-click again** on the same cleared factor/dimension, and while holding the **SHIFT** key on your keyboard, select **Run Item Workflow**.
> This process ensures that the tool reassesses the input values and outputs the corrected scores.

<p align="center">
<img 
    src="https://raw.githubusercontent.com/worldbank/GEEST/main/docs/images/new%20images/CD%20clear%20and%20rerun.jpg" 
    alt="Contextual Clear and rerun" 
    style="width:75%;" 
    title="Click to enlarge" 
    onclick="window.open(this.src, '_blank')">
</p>

### Key Considerations
---
- **Input Accuracy**: Ensure all input values are carefully entered and correspond to the correct indices (e.g., Workplace Discrimination, Regulatory Frameworks, Financial Inclusion). Incorrect data will impact the outputs and subsequent analysis.

- **Weight Adjustment**: Assign weights thoughtfully to reflect the importance of each factor in the overall analysis. After making changes, always balance the weights to ensure they sum up correctly.



