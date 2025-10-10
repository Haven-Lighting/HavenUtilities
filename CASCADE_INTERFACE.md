# Cascade Lighting Effect Interface

## Overview

The Cascade effect has been added to the Effects Tester with a complete interface similar to Marquee but with specific controls for the Cascade lighting pattern.

## Features

### Color Management
- **Add Colors**: Click "Add Color" to start building your cascade
- **Color Timeline**: Visual representation of selected colors
- **Remove Colors**: Click on any color in the timeline to remove it
- **Multiple Colors**: Use the "+" button to add additional colors

### Control Sliders

#### Basic Controls
1. **Color Length (ft)**: 
   - Range: 0.25 - 100 feet
   - Controls the physical length of each color segment
   - Converted to inches for the direct method (feet × 12)

2. **Padding Length (ft)**:
   - Range: 0.25 - 100 feet  
   - Controls the background/spacing size between colors
   - Converted to inches for the direct method (feet × 12)

3. **Moving Speed**:
   - Range: 0 - 200
   - Controls how fast the cascade pattern moves
   - Direct value passed to the controller

4. **Transition Type**:
   - Dropdown with options: None, Placeholder1, Placeholder2
   - Future expansion for transition effects

#### Advanced Options
5. **Enable Mirror**:
   - Checkbox to enable/disable mirror functionality
   - Shows/hides mirror position control

6. **Mirror Position (ft)**:
   - Range: -200 to 200 feet
   - Controls where the mirror effect is positioned
   - Converted to inches for the direct method

7. **Osc Amplitude**:
   - Range: 0.0 - 1.0 (increments of 0.1)
   - Controls oscillation amplitude
   - Converted to 0-10 range for direct method

8. **Osc Period**:
   - Range: 0 - 10
   - Controls oscillation period timing

## Direct Method Output

The interface generates a complete direct method string in this format:

```
<LIGHTING.ON({"CH":[-1],"FUNCTION":"Custom","BRIGHTNESS":100,"Config":{"colorSelections":["0,100,100"],"bgColor":[0,0,0],"colorLength":48,"paddingLength":24,"transitionType":"None","movingSpeed":100,"enableMirror":0,"mirrorPosition":0,"oscAmp":0,"oscPeriod":1}})
```

### Config Object Details:
- **colorSelections**: Array of colors in "H,S,V" format (Hue 0-360, Saturation 0-100, Value 0-100)
- **bgColor**: Background color [R,G,B] - currently fixed to black [0,0,0]
- **colorLength**: Length in inches (feet × 12)
- **paddingLength**: Padding in inches (feet × 12)
- **transitionType**: String value from dropdown
- **movingSpeed**: Direct integer value (0-200)
- **enableMirror**: 1 or 0 (boolean)
- **mirrorPosition**: Position in inches (feet × 12)
- **oscAmp**: Amplitude scaled to 0-10 range (0.0-1.0 × 10)
- **oscPeriod**: Direct integer value (0-10)

## Usage Instructions

1. **Open Effects Tester** from the main application
2. **Select Cascade Tab** in the notebook interface
3. **Add Colors**:
   - Click "Add Color"
   - Adjust RGB sliders to select color
   - Click "Add Color" to confirm
   - Repeat for multiple colors
4. **Adjust Parameters** using the control sliders
5. **Execute**: Click "Execute" to send to controller (requires connection)
6. **Copy Command**: Click "Update Direct Method String" then click the command text to copy to clipboard

## Color Conversion

Colors are automatically converted from RGB (0-255) to HSV format:
- **Hue**: 0-360 degrees
- **Saturation**: 0-100%
- **Value**: 0-100%

## Real-time Updates

The direct method string updates automatically when any parameter changes, allowing you to see the exact command that will be sent to the controller.

## Integration

The Cascade interface integrates seamlessly with the existing Effects Tester and maintains the same connection and logging functionality as the Marquee and Color Selector tabs.
