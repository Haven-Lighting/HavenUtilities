# Action Block Snapping Feature

## Overview
Added intelligent snap-to-snap functionality for action blocks in the audio timeline, similar to professional video editing software.

## Snap Functionality

### **Snap Points**
- **Action Block Edges**: Start and end points of all other action blocks
- **Timeline Boundaries**: Beginning (0:00) and end of audio file
- **Bi-directional**: Works for both start and end edges of blocks

### **Snap Behavior**
- **Moving Blocks**: Snaps to the nearest edge (start or end) of other blocks
- **Resizing Left**: Snaps the start edge to other block edges
- **Resizing Right**: Snaps the end edge to other block edges
- **Intelligent Selection**: Chooses the closest snap point within threshold

### **Adaptive Snap Distance**
- **Zoom Responsive**: Larger snap distance at low zoom, smaller at high zoom
- **Pixel Range**: 10-40 pixels depending on zoom level
- **Consistent Feel**: Maintains same visual snap distance regardless of zoom

### **Visual Feedback**
- **Golden Snap Lines**: Dashed yellow lines show action block snap points
- **Red Boundary Lines**: Solid red lines show timeline boundary snaps
- **Edge Indicators**: White dots highlight the edges of the block being dragged
- **Smart Labels**: Show which action you're snapping to (at sufficient zoom)

### **User Controls**
- **Snap Toggle**: Checkbox in zoom controls to enable/disable snapping
- **Keyboard Shortcut**: Press 'S' to toggle snapping on/off
- **Default State**: Snapping is enabled by default

### **Audio Feedback**
- **Log Messages**: Shows which action or boundary you snapped to
- **Rate Limited**: Prevents spam by logging once per second max

## Usage Examples

### **Creating Sequential Actions**
1. Drop Action 1 on timeline (0-10 seconds)
2. Drop Action 2 near the end of Action 1
3. Action 2 automatically snaps to start at 10 seconds (butt-to-butt)

### **Precise Alignment**
1. Resize Action 3 by dragging its start edge
2. As you approach Action 2's end, golden snap line appears
3. Release to snap perfectly to Action 2's end time

### **Timeline Boundaries**
1. Drag any action near the beginning or end of the audio
2. Red snap lines appear at 0:00 and audio end time
3. Actions snap perfectly to timeline boundaries

## Technical Details
- **Snap Threshold**: Calculated as `max(10, min(40, 20 * (100 / zoom_level))) / zoom_level`
- **Priority System**: Closest snap point wins if multiple points are within threshold
- **Conflict Resolution**: For moving blocks, compares start vs end snap distances
- **Performance**: Snap calculations only during drag operations

## Keyboard Shortcuts
- **S**: Toggle snapping on/off
- **Drag + S**: Hold S while dragging to temporarily disable snapping (if normally enabled)

This creates a professional, intuitive timeline editing experience where action blocks naturally align and connect seamlessly!
