<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="Symbology" version="3.38.3-Grenoble">
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option type="QString" value="" name="name"/>
      <Option name="properties"/>
      <Option type="QString" value="collection" name="type"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling enabled="false" zoomedInResamplingMethod="nearestNeighbour" maxOversampling="2" zoomedOutResamplingMethod="nearestNeighbour"/>
    </provider>
    <rasterrenderer type="singlebandpseudocolor" alphaBand="-1" band="1" classificationMin="0" classificationMax="5" nodataColor="" opacity="1">
      <rasterTransparency/>
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <rastershader>
        <colorrampshader clip="0" classificationMode="2" labelPrecision="0" colorRampType="DISCRETE" minimumValue="0" maximumValue="5">
          <colorramp type="gradient" name="[source]">
            <Option type="Map">
              <Option type="QString" value="215,25,28,255,rgb:0.84313725490196079,0.09803921568627451,0.10980392156862745,1" name="color1"/>
              <Option type="QString" value="28,234,14,255,hsv:0.32222222222222224,0.94117647058823528,0.91764705882352937,1" name="color2"/>
              <Option type="QString" value="ccw" name="direction"/>
              <Option type="QString" value="0" name="discrete"/>
              <Option type="QString" value="gradient" name="rampType"/>
              <Option type="QString" value="rgb" name="spec"/>
              <Option type="QString" value="0.2;28,234,14,255,hsv:0.32222222222222224,0.94117647058823528,0.91764705882352937,1;rgb;ccw" name="stops"/>
            </Option>
          </colorramp>
          <item value="0" color="#d7191c" label="Excluded" alpha="255"/>
          <item value="1" color="#1cea0e" label="Included" alpha="255"/>
          <rampLegendSettings prefix="" maximumLabel="" orientation="2" direction="0" useContinuousLegend="1" minimumLabel="" suffix="">
            <numericFormat id="basic">
              <Option type="Map">
                <Option type="invalid" name="decimal_separator"/>
                <Option type="int" value="6" name="decimals"/>
                <Option type="int" value="0" name="rounding_type"/>
                <Option type="bool" value="false" name="show_plus"/>
                <Option type="bool" value="true" name="show_thousand_separator"/>
                <Option type="bool" value="false" name="show_trailing_zeros"/>
                <Option type="invalid" name="thousand_separator"/>
              </Option>
            </numericFormat>
          </rampLegendSettings>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" gamma="1" contrast="0"/>
    <huesaturation saturation="0" colorizeRed="255" grayscaleMode="0" colorizeBlue="128" colorizeGreen="128" colorizeStrength="100" colorizeOn="0" invertColors="0"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
