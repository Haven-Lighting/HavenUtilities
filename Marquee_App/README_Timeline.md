# Audio Timeline Feature

## Overview
The Audio Timeline replaces the old playlist functionality with a Final Cut Pro-style timeline interface for MP3 audio files with synchronized lighting action blocks.

## Features

### Audio File Support
- Load MP3, WAV, FLAC, and M4A audio files
- High-resolution waveform visualization
- Real-time audio playback with visual cursor

### Timeline Controls
- **Play/Pause**: Space bar or ▶ button
- **Stop**: ⏸ button  
- **Go to Start**: ⏮ button or Home key
- **Seek**: Click anywhere on the timeline or use ←/→ arrow keys

### Zoom Functionality
- **Zoom In**: + button, Plus key, or mouse wheel up
- **Zoom Out**: - button, Minus key, or mouse wheel down
- **Zoom to Fit**: "Fit" button or F key
- **Zoom Range**: 10 to 1000 pixels per second
- **Smart Time Markers**: Automatically adjusts time marker intervals based on zoom level

### Action Timeline System
- **Dual Timeline**: Audio waveform above, action blocks below
- **Action Toolbar**: 20 pre-defined actions (1-20) in colorful buttons
- **Drag & Drop**: Drag actions from toolbar to timeline
- **Default Duration**: 10 seconds (adjustable by resizing)
- **Visual Blocks**: Color-coded blocks showing action ID and duration
- **Resize Handles**: Drag left/right edges to adjust duration
- **Move Blocks**: Click and drag entire blocks to reposition
- **Selection**: Click blocks to select (golden outline)

### Action Management
- **Execute Actions**: ▶ Execute Actions button runs all actions sync'd with audio
- **Delete**: Delete button or Delete key removes selected action
- **Clear All**: Removes all action blocks with confirmation
- **Copy/Paste**: C/V keys to duplicate actions at playback position
- **Minimum Duration**: 0.1 seconds minimum for all actions
- **Timeline Boundaries**: Actions constrained to audio duration

### Visual Features
- High-resolution waveform display in green
- Red playback cursor with smooth 50ms updates (synced across both timelines)
- Auto-scrolling to keep cursor visible
- Time markers with appropriate intervals
- Real-time position display (current/total time)
- Color-coded action blocks (20 unique colors)
- Resize handles on action blocks
- Selection highlighting

### Keyboard Shortcuts
- **Space**: Play/Pause
- **+/=**: Zoom In
- **-**: Zoom Out
- **F**: Zoom to Fit
- **Home**: Go to Start
- **←**: Seek backward 1 second
- **→**: Seek forward 1 second
- **Delete**: Delete selected action
- **C**: Copy selected action
- **V**: Paste action at playback position

### Mouse Controls
- **Audio Timeline**: Click to seek, drag to scrub, wheel to zoom
- **Action Timeline**: Click blocks to select, drag to move, drag edges to resize
- **Toolbar**: Click and drag actions to timeline
- **Synchronized Scrolling**: Both timelines scroll together

## Technical Details
- Uses pygame for audio playback
- Uses librosa for audio analysis and waveform generation
- 44.1kHz audio sampling for high quality
- Preserves direct method communication system for lighting control
- Maintains compatibility with existing effects system
- Action execution uses JSON command format for lighting controller

## Usage Instructions
1. Click "Open Audio Timeline" button
2. Click "Browse" to select an audio file
3. Use zoom controls to get the desired view precision
4. Drag actions from the toolbar to the action timeline
5. Resize action blocks by dragging their edges
6. Move actions by clicking and dragging the blocks
7. Use playback controls or keyboard shortcuts to control audio
8. Click "▶ Execute Actions" to run lighting sequence synchronized with audio
9. The cursor will automatically follow playback in real-time on both timelines

## Action Execution
When "Execute Actions" is clicked:
1. All actions are sorted by start time
2. Audio playback begins
3. Each action is scheduled to execute at its precise timing
4. Commands are sent to the lighting controller using the direct method format
5. Actions execute for their specified duration

The timeline provides professional-level precision for audio synchronization with lighting effects, making it perfect for creating complex light shows synchronized to music.
