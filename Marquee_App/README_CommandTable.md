# Command Table Feature

## Overview
The Command Table feature allows you to export all virtual channel color blocks from the audio timeline as a CSV file containing lighting commands with precise timing and color information.

## How to Use

1. **Open Audio Timeline**: Click "Open Audio Timeline" from the main interface
2. **Load Audio File**: Browse and select an MP3/WAV audio file
3. **Add Color Blocks**: 
   - Drag colors from the Color Command Palette to the virtual channel timelines (vc1-vc8)
   - Resize and position blocks as needed
   - Use snapping to align blocks precisely

4. **Save Command Table**: 
   - Click "Save Command Table" button in the timeline window, or
   - Use the menu: Channels → Save Command Table

## Command Table Format

The exported CSV file contains the following columns:

- **Channel**: Virtual channel identifier (vc1, vc2, etc.)
- **Start_Time**: When the command starts (in seconds)
- **R**: Red component (0-100 scale)
- **G**: Green component (0-100 scale) 
- **B**: Blue component (0-100 scale)
- **Duration_ms**: Duration of the command in milliseconds
- **Color_Hex**: Original hex color code for reference

## Example Output

```csv
Command Table
Channel,Start_Time,R,G,B,Duration_ms,Color_Hex
vc1,0.000,100.0,0.0,0.0,100,#FF0000
vc2,0.100,0.0,100.0,0.0,200,#00FF00
vc1,0.200,0.0,0.0,100.0,150,#0000FF
```

## Features

- **Automatic Color Conversion**: Hex colors are automatically converted to RGB values (0-100 scale)
- **Precise Timing**: Start times and durations are calculated from timeline positions
- **Sorted Output**: Commands are sorted by start time for sequential execution
- **Multi-Channel Support**: Supports all 8 virtual channels (vc1-vc8)
- **Duration Calculation**: Automatically calculates duration in milliseconds from block length

## Use Cases

- **Lighting Sequence Programming**: Generate precise lighting commands for shows
- **Timeline Export**: Export complex timeline data for external systems
- **Command Verification**: Review and verify lighting sequences before execution
- **System Integration**: Import commands into other lighting control systems

## Notes

- RGB values use 0-100 scale (not 0-255) to match the effects system format
- Duration is automatically converted from seconds to milliseconds
- Empty channels are not included in the export
- Commands are automatically sorted by start time regardless of channel order
