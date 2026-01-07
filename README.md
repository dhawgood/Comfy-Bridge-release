<div align="center">

# Comfy Bridge

<a href="https://github.com/dhawgood/Comfy-Bridge-release/releases/latest/download/ComfyBridge_v1.2.1.zip">
  <img src="https://img.shields.io/badge/Download_For_Windows-Comfy_Bridge_v1.2.1-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Download Comfy Bridge" height="40"/>
</a>

<br><br>

> **⚠️ IMPORTANT:** Please use the blue download button above.<br>
> *The standard green "Code" button on GitHub contains raw source files and will not launch correctly.*

</div>

---

## Version 1.2.1

A professional tool for compressing, analyzing, and modifying ComfyUI workflows using AI agents. Comfy Bridge introduces Bridge Planner, a custom GPT responsible for reasoning about changes and translating creative intent into explicit, deterministic, compiler-ready plans. At its core, Bridge Planner asks a single question: given the current workflow state and the user's intent, can this be expressed as a valid, deterministic set of structural operations?

## Features

- **Hybrid System**: 1 external AI agent (ChatGPT) + 2 deterministic Python components
- **Live API Integration**: Extract node definitions, packs, and models directly from ComfyUI
- **BridgeZip Protocol**: Significantly compresses ComfyUI workflows while preserving all logic
- **Workflow Conversion**: Seamless JSON ↔ BridgeZip conversion
- **Context Management**: Intelligent extraction of workflow data for AI collaboration
- **Modern UI**: Professional Nordic/Deep Slate aesthetic with intuitive interface

## Installation

### Prerequisites

- Python 3.10-3.13 installed and in PATH
- ComfyUI installation (for Live API mode)

### Setup

1. Extract the `ComfyBridge_v1.2.1.zip` package to any folder
2. Double-click `START.bat`
3. The application will:
   - Check for Python installation
   - Create a virtual environment automatically
   - Install dependencies automatically
   - Launch the application

**Note:** Make sure Python is installed and added to PATH during installation.

### Development Setup

If you're developing or modifying the code:

1. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python run_bridge.py
   ```

## Configuration

Comfy Bridge automatically creates a `config.json` file on first run. You can configure settings via the Settings button (⚙️) in the application header:

- **ComfyUI URL/Port**: Set the ComfyUI API endpoint such as http://127.0.0.1:8000 (default: http://127.0.0.1:8188)
- **ComfyUI Image Input Folder**: Set the path to your ComfyUI input folder for image uploads

Settings are saved automatically and persist between sessions.

## Quick Start

1. **Get Node Definitions**
   - Go to Bridge Context tab
   - Use Live Mode (recommended) or File Mode
   - Extract definitions, compressed meta, or model index

2. **Prepare Workflow**
   - Export ComfyUI workflow
   - Go to Bridge Flow tab
   - Convert JSON → BridgeZip (or work with existing BridgeZip)

3. **Plan the Change**
   - Go to Bridge Planner tab
   - Request analysis or structural design
   - Receive the Compiler Brief

4. **Compile the Plan**
   - Go to Bridge Compiler tab
   - Paste the brief + workflow + definitions
   - Receive a validated Task Envelope

5. **Execute the Change**
   - Go to Bridge Execute tab
   - Paste the envelope
   - Receive updated BridgeZip

6. **Re-import to ComfyUI**
   - Inflate via Bridge Flow or directly inside ComfyUI
   - Test and iterate

## Architecture

### The Hybrid System

Comfy Bridge uses a hybrid architecture: 1 external AI agent (ChatGPT) for planning, plus 2 deterministic Python components for validation and execution.

1. **Bridge Planner** (ChatGPT - External AI Agent)
   - Analyses workflows
   - Interprets user intent
   - Designs structural solutions
   - Produces the Compiler Brief

2. **Bridge Compiler** (Python-only - Deterministic Component)
   - Validates node classes and slot indices
   - Translates the plan into a strict Task Envelope
   - Guarantees correct BridgeZip syntax and linking
   - Performs no reasoning or execution

3. **Bridge Execute** (Python-only - Deterministic Component)
   - Executes the Task Envelope using the BridgeZip engine
   - Applies all modifications
   - Outputs a clean, updated BridgeZip workflow
   - Operates in strict silent mode

### BridgeZip Format

BridgeZip is a compressed workflow format that:
- Preserves node logic, links, widgets, and metadata
- Removes visual layout and redundant UI details
- Significantly reduces token footprint
- Enables efficient AI-based workflow modification

## Project Structure

```
Comfy_Bridge/
├── run_bridge.py    # Application entry point
├── LICENSE          # Apache 2.0 License
├── README.md        # This file
├── requirements.txt # Python dependencies
├── START.bat        # Windows launcher
├── engine/          # BridgeZip compression engine
├── logic/           # Business logic (filtering, extraction)
├── ui/              # User interface components
│   ├── tabs/        # Tab implementations
│   └── modals/      # Modal dialogs
├── utils/           # Utility functions and helpers
├── scripts/         # Launch scripts
├── assets/          # Application icons
└── demo/            # Sample files for testing
```

## License

Copyright 2025 Dominic Hawgood

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

## Contributing

This is a personal project. For issues or suggestions, please contact the maintainer.

## Version History

- **1.2.1** - Professional release with hybrid system (1 AI agent + 2 Python components)
