## Contextual

<p align="justify"> 
The Contextual Dimension refers to the laws and policies that shape workplace gender discrimination, financial autonomy, and overall gender empowerment. Although this dimension may vary between countries due to differences in legal frameworks, it remains consistent within a single country, as national policies and regulations are typically applied uniformly across countries. 
</p>

<h3>Workplace Discrimination</h3>
<hr style="height: 3px; background-color: grey; border: none;">

<p align="justify"> 
Workplace Discrimination involves laws that address gender biases and stereotypes that hinder women's career advancement, especially in male-dominated fields.
This indicator is composed by the Workplace Index score of the WBL 2024, which is then standardized on a scale from 0 to 5.
</p>

<h3>Step 1: Accessing the Contextual Dimension</h3>
<ul>
    <li>
        <strong>Locate the Workplace Discrimination Section:</strong>
        <ul>
               <span>🔍 Right-Click on Workplace Discrimination.</span><br>
               <span>⚙️ Select Show Properties.</span>
        </ul>
        <img src="your_image_path_here" alt="IMAGE for WD" style="width:100%;"/>
    </li>
</ul>

<h3>Step 2: Opening the Show Properties Dialog</h3>
<ul>
    <li>
        <strong>Input the Value for <em>Value</em>:</strong>
        <ul>
            <span>  🖊️ Enter the <strong>WBL Workplace Index Score</strong> value.</span><br>
            <span>  ✔️ Press <strong>OK</strong> to confirm your input.</span><br>
        </ul>
    </li>
           <img src="your_image_path_here" alt="IMAGE for WD" style="width:100%;"/>
    </li>
</ul>

<p>📂 <strong>The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder.</strong></p>


<p align="center">
 **IMAGE for WD**
</p>

<h3>Regulatory Frameworks</h3>
<hr style="height: 3px; background-color: grey; border: none;">
<p align="justify"> 
Regulatory Frameworks pertain to laws and policies that protect women’s employment rights, such as childcare support and parental leave, influencing their workforce participation.
This indicator is composed by aggregating the Parenthood and Pay Index scores of the WBL 2024, both standardized on a scale from 0 to 5.
</p>

<h3>Step 1: Accessing the Contextual Dimension</h3>
<ul>
    <li>
        <strong>Locate the Regulatory Frameworks Section:</strong>
        <ul>
               <span>🔍 Right-Click on Regulatory Frameworks.</span><br>
               <span>⚙️ Select Show Properties.</span>
        </ul>
        <img src="your_image_path_here" alt="IMAGE for RF" style="width:100%;"/>
    </li>
</ul>

<h3>Step 2: Opening the Show Properties Dialog</h3>
<ul>
    <li>
        <strong>Input the Value for <em>Value</em>:</strong>
        <ul>
            <span>  🖊️ Enter the <strong>WBL Pay and Parenthood Index Scores</strong> value.</span><br>
            <span>  ✔️ Press <strong>OK</strong> to confirm your input.</span><br>
        </ul>
    </li>
           <img src="your_image_path_here" alt="IMAGE for RF" style="width:100%;"/>
    </li>
</ul>

<p>📂 <strong>The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder.</strong></p>


<p align="center">
 **IMAGE for RF**
</p>

<h3>Financial Inclusion</h3>
<hr style="height: 3px; background-color: grey; border: none;">
<p align="justify"> 
Financial Inclusion involves laws concerning women’s access to financial resources like loans and credit, which is crucial for starting businesses and investing in economic opportunities.
This indicator comes from the Entrepeneurship rating of the 2024 WBL Index and is standardized on a scale ranging from 0 to 5.
</p>

<h3>Step 1: Accessing the Contextual Dimension</h3>
<ul>
    <li>
        <strong>Locate the Financial Inclusion Section:</strong>
        <ul>
               <span>🔍 Right-Click on Financial Inclusion.</span><br>
               <span>⚙️ Select Show Properties.</span>
        </ul>
        <img src="your_image_path_here" alt="IMAGE for FI" style="width:100%;"/>
    </li>
</ul>

<h3>Step 2: Opening the Show Properties Dialog</h3>
<ul>
    <li>
        <strong>Input the Value for <em>Value</em>:</strong>
        <ul>
            <span>  🖊️ Enter the <strong>WBL Entrepeneurship Index Score</strong> value.</span><br>
            <span>  ✔️ Press <strong>OK</strong> to confirm your input.</span><br>
        </ul>
    </li>
           <img src="your_image_path_here" alt="IMAGE for FI" style="width:100%;"/>
    </li>
</ul>

<p>📂 <strong>The output raster file will be stored in the project folder specified in the “Setup” tab, under the “Contextual” folder.</strong></p>

<p align="center">
 **IMAGE for FI**
</p>


<h3>Aggregate</h3>
<hr style="height: 3px; background-color: grey; border: none;">

<h3>Step 1: Weights Set-Up</h3>
<ul>
    <li>
        <strong>Locate the Contextual Dimension Section:</strong>
        <ul>
               <span>🔍 Right-Click on Contextual Dimension.</span><br>
               <span>⚙️ Select Edit Attributes.</span>
        </ul>
        <img src="your_image_path_here" alt="IMAGE for Weights" style="width:100%;"/>
    </li>
</ul>

<h3>Step 2: Opening the Edit Attributes Dialog</h3>
<ul>
    <li>
        <strong>Ensure the <em>Weights</em> values are filled in:</strong>
        <ul>
            <span>  🖊️ Ensure that all Weight fields are filled with valid numerical entries.</span><br>
            <span>  ✔️ Press <strong>OK</strong> to confirm your input.</span><br>
            <p>
</ul>
        
<p align="justify"> 
    <span style="color: orange; font-size: 50px;">⚠️</span>
    <strong>If equal weights are not suitable for the specific context of the analysis, the user can adjust the weights as necessary, ensuring that all weights still sum to 100!</strong> The default weights are <strong>34%</strong> for <strong>Workplace Discrimination</strong>, <strong>33%</strong> for <strong>Regulatory Frameworks</strong>, and <strong>33%</strong> for <strong>Financial Inclusion</strong>. If a factor was not calculated—perhaps due to missing data or because it was deemed unimportant—that factor should be assigned a weight of <strong>0%</strong>. Subsequently, the remaining factor weights must be adjusted to ensure they collectively add up to <strong>100%</strong>.
</p>



<img src="your_image_path_here" alt="IMAGE for Weights" style="width:100%;"/>

<h3>Step 3: Aggegate</h3>
<ul>
     <li>
            it will be amended after UIX is finished...
    </li>
</ul>
