# Cascade Effect - Live Command Builder

## Overview
The Cascade effect now works exactly like the Marquee system with live command string building and direct method execution.

## How It Works

### 1. **Live Command Building**
- As soon as you add colors and adjust any parameters, the command string is built automatically
- The command display shows the direct method string in real-time
- Visual command builder shows the structure with color-coded blocks

### 2. **String Builder Behavior (Like Marquee)**
- **Add Colors**: Each color added triggers command rebuild
- **Adjust Parameters**: All sliders and controls trigger live updates:
  - Color Length (ft)
  - Padding Length (ft) 
  - Moving Speed
  - Transition Type
  - Mirror settings
  - Oscillation settings

### 3. **Execute Button**
- Sends the generated direct method string directly to the controller
- No additional processing - uses the exact command shown in the text area
- Just like Marquee system behavior

## Generated Command Format

```json
<LIGHTING.ON({
  "CH": [-1],
  "FUNCTION": "Custom", 
  "BRIGHTNESS": 100,
  "Config": {
    "colorSelections": ["360,100,100", "120,100,100"],
    "bgColor": [0, 0, 0],
    "colorLength": 48,
    "paddingLength": 24,
    "transitionType": "None",
    "movingSpeed": 100,
    "enableMirror": 0,
    "mirrorPosition": 0,
    "oscAmp": 0,
    "oscPeriod": 1
  }
})>
```

## Features

### ✅ **Live Updates**
- Command string updates instantly when any parameter changes
- Visual builder shows real-time command structure
- Status indicator shows command readiness

### ✅ **Direct Execution** 
- Execute button sends the exact command string shown
- No additional processing or transformation
- Same behavior as Marquee system

### ✅ **Color Management**
- Add multiple colors with RGB sliders
- Colors converted to H,S,V format for controller
- Timeline shows color sequence visually

### ✅ **Parameter Controls**
- All measurements converted automatically (ft to inches)
- Range validation and proper scaling
- Mirror and oscillation controls with live preview

## Usage

1. **Add Colors**: Click "Add Color" and use RGB sliders
2. **Adjust Settings**: Use sliders to fine-tune all parameters
3. **Watch Command Build**: See the direct method string update live
4. **Execute**: Click "Execute" to send the command to controller

The system now works identically to the Marquee effect with live string building and direct method execution!
