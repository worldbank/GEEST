<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis styleCategories="Symbology" version="3.44.1-Solothurn">
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option name="name" value="" type="QString"/>
      <Option name="properties"/>
      <Option name="type" value="collection" type="QString"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling zoomedInResamplingMethod="nearestNeighbour" maxOversampling="2" zoomedOutResamplingMethod="nearestNeighbour" enabled="false"/>
    </provider>
    <rasterrenderer opacity="1" nodataColor="" alphaBand="-1" type="singlebandpseudocolor" classificationMin="0" classificationMax="5" band="1">
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
        <colorrampshader classificationMode="2" labelPrecision="0" maximumValue="5" clip="0" minimumValue="0" colorRampType="DISCRETE">
          <colorramp name="[source]" type="gradient">
            <Option type="Map">
              <Option name="color1" value="215,25,28,255,rgb:0.8431373,0.0980392,0.1098039,1" type="QString"/>
              <Option name="color2" value="44,123,182,255,rgb:0.172549,0.4823529,0.7137255,1" type="QString"/>
              <Option name="direction" value="ccw" type="QString"/>
              <Option name="discrete" value="0" type="QString"/>
              <Option name="rampType" value="gradient" type="QString"/>
              <Option name="spec" value="rgb" type="QString"/>
              <Option name="stops" value="0.2;215,25,28,255,rgb:0.8431373,0.0980392,0.1098039,1;rgb;ccw:0.4;253,174,97,255,rgb:0.9921569,0.6823529,0.3803922,1;rgb;ccw:0.6;255,255,191,255,rgb:1,1,0.7490196,1;rgb;ccw:0.8;188,225,184,255,rgb:0.7372549,0.8823529,0.7215686,1;rgb;ccw" type="QString"/>
            </Option>
          </colorramp>
          <item value="1" color="#d7191c" label="0 - 1 Very Low Enablement" alpha="255"/>
          <item value="2" color="#fdae61" label="1 - 2 Low Enablement" alpha="255"/>
          <item value="3" color="#ffffbf" label="2 - 3 Moderately Enabling" alpha="255"/>
          <item value="4" color="#bce1b8" label="3 - 4 Enabling" alpha="255"/>
          <item value="5" color="#2c7bb6" label="4 - 5 Highly Enabling" alpha="255"/>
          <rampLegendSettings prefix="" minimumLabel="" useContinuousLegend="1" maximumLabel="" direction="0" orientation="2" suffix="">
            <numericFormat id="basic">
              <Option type="Map">
                <Option name="decimal_separator" type="invalid"/>
                <Option name="decimals" value="6" type="int"/>
                <Option name="rounding_type" value="0" type="int"/>
                <Option name="show_plus" value="false" type="bool"/>
                <Option name="show_thousand_separator" value="true" type="bool"/>
                <Option name="show_trailing_zeros" value="false" type="bool"/>
                <Option name="thousand_separator" type="invalid"/>
              </Option>
            </numericFormat>
          </rampLegendSettings>
        </colorrampshader>
      </rastershader>
    </rasterrenderer>
    <brightnesscontrast brightness="0" contrast="0" gamma="1"/>
    <huesaturation colorizeOn="0" invertColors="0" saturation="0" colorizeGreen="128" colorizeStrength="100" colorizeBlue="128" grayscaleMode="0" colorizeRed="255"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
