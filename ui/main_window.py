"""
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
"""

import os
import customtkinter as ctk
from engine import __version__
from utils.ui_helpers import COLORS, ModernButton, ModernModal, SettingsModal
from ui.tabs.workflow_tab import WorkflowTab
from ui.tabs.node_dev_tab import NodeDevTab
from ui.tabs.planner_tab import PlannerTab
from ui.tabs.compiler_tab_v2 import BridgeCompilerTab
from ui.tabs.bridge_execute_tab import BridgeExecuteTab

DOC_GENERAL = f"""COMFY BRIDGE v{__version__} — GENERAL HELP

WHY COMFY BRIDGE EXISTS
-----------------------
ComfyUI workflows are large, repetitive JSON documents that quickly overwhelm AI context windows.

Node geometry, widget arrays, and metadata create massive token footprints, making AI collaboration slow, expensive, and unreliable.

Comfy Bridge solves this.

It introduces BridgeZip — a compressed, logic-preserving workflow format that significantly reduces size, eliminates UI noise, and enables precise, deterministic collaboration using a hybrid system (1 external AI agent + 2 deterministic Python components).

The application provides the tooling, extraction utilities, and hybrid system orchestration needed to safely design, modify, and execute complex ComfyUI workflows with AI.

THE HYBRID SYSTEM
-----------------
Comfy Bridge uses a hybrid architecture: 1 external AI agent (ChatGPT) for planning, plus 2 deterministic Python components for validation and execution.

1. BRIDGE PLANNER (ChatGPT - External AI Agent)
   - Analyses workflows
   - Interprets user intent
   - Designs structural solutions
   - Produces the Compiler Brief

2. BRIDGE COMPILER (Python-only - Deterministic Component)
   - Validates node classes and slot indices
   - Translates the plan into a strict Task Envelope
   - Guarantees correct BridgeZip syntax and linking
   - Performs no reasoning or execution

3. BRIDGE EXECUTE (Python-only - Deterministic Component)
   - Executes the Task Envelope using the BridgeZip engine
   - Applies all modifications
   - Outputs a clean, updated BridgeZip workflow
   - Operates in strict silent mode

This architecture ensures clarity, safety, and deterministic results.

QUICK START
-----------
1. Get Node Definitions
   - Go to Bridge Context
   - Use Live Mode (recommended) or File Mode
   - Extract definitions, compressed meta, or model index

2. Prepare Workflow
   - Convert JSON → BridgeZip (Bridge Flow)
   - Or work directly with existing BridgeZip

3. Plan the Change
   - Go to Bridge Planner
   - Request analysis or structural design
   - Receive the Compiler Brief

4. Compile the Plan
   - Go to Bridge Compiler
   - Paste the brief + workflow + definitions
   - Receive a validated Task Envelope

5. Execute the Change
   - Go to Bridge Execute
   - Paste the envelope
   - Receive updated BridgeZip

6. Re-import to ComfyUI
   - Inflate via Bridge Flow or directly inside ComfyUI
   - Test and iterate

CONFIGURATION
-------------
Before using Live API mode, configure your ComfyUI connection:
- Click the "⚙️ Settings" button in the header
- Set ComfyUI URL/Port (default: http://127.0.0.1:8188)
- Optionally set ComfyUI Image Input Folder path
- Click "Test" to verify connection
- Click "Save" to apply settings

Settings are saved to config.json in the application directory.

TAB OVERVIEW
------------
1. BRIDGE CONTEXT
   Extracts all data needed for LLM-assisted workflow editing, including:
   - Node definitions (full or compressed)
   - Installed packs
   - Model index
   - Group extraction
   - Node extraction from BridgeZip
   
   Supports Live API mode (no files required) or File mode.

2. BRIDGE FLOW
   A conversion and inspection layer for workflows.
   - JSON ↔ BridgeZip
   - Token-efficient workflow exchange
   - Essential when collaborating with AI tools

3. BRIDGE PLANNER
   High-level design and diagnosis.
   - Workflow audits
   - Structural planning
   - Topology design
   - Produces the Compiler Brief

4. BRIDGE COMPILER
   Strict translation stage.
   - Validates all definitions
   - Converts the Planner's design into an executable Task Envelope
   - Ensures correct BridgeZip syntax

5. BRIDGE EXECUTE
   Silent execution stage (Python-only).
   - Runs the Task Envelope
   - Applies changes via bridgezip_core
   - Returns updated BridgeZip workflows

RECOMMENDED WORKFLOW PIPELINE
------------------------------
1. Context → Extract definitions
2. Flow → Convert workflow to BridgeZip
3. Planner → Design and audit
4. Compiler → Produce Task Envelope
5. Execute → Apply modifications
6. ComfyUI → Test the result

FILE FORMATS
------------
1. BRIDGEZIP (WORKFLOWS)
   A compressed workflow format beginning with W:.
   
   Preserves:
   - Node logic
   - Links
   - Widgets
   - Metadata
   
   Removes:
   - Visual layout
   - Redundant UI details
   
   Ideal for AI-based planning and execution.

2. NODE DEFINITIONS
   Extracted from ComfyUI using Bridge Context.
   - Used by Planner and Compiler
   - Ensures node names, inputs, outputs, and widget schemas are correct
   - Supports both detailed JSON and compressed signature format

3. MODEL INDEX
   Organises your local model files into a lightweight structure.
   - Used for accurate model selection during planning

NOTE
----
Comfy Bridge is designed for safe, deterministic workflow editing.

It separates reasoning, validation, and execution to avoid hallucinations, reduce context load, and ensure every workflow modification remains structurally valid."""

class ComfyBridgeApp(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.title(f"Comfy Bridge v{__version__}")
        self.geometry("1100x900")
        self.configure(fg_color=COLORS['bg_main'])
        
        # Set window icon (must be before setup_ui for taskbar icon)
        icon_path = os.path.abspath(os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "assets", 
            "ComfyBridge.ico"
        ))
        if os.path.exists(icon_path):
            try:
                # Set icon for window and taskbar
                self.iconbitmap(icon_path)
                # Also try wm_iconbitmap for better Windows compatibility
                self.wm_iconbitmap(icon_path)
                # Force update to ensure icon is applied
                self.update_idletasks()
            except Exception as e:
                # Log error instead of silently failing
                from utils.logger import logger
                logger.warning(f"Could not load window icon: {e}")
        else:
            from utils.logger import logger
            logger.warning(f"Icon file not found: {icon_path}")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Build the main UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        header.pack(fill="x", pady=(15, 5), padx=20)
        
        # Main title with increased prominence
        ctk.CTkLabel(
            header, text="Comfy Bridge", font=("Segoe UI", 25, "bold"),
            text_color="white"
        ).pack(side="left")
        
        # Live indicator with accent color
        ctk.CTkLabel(
            header, text="(live)", font=("Segoe UI", 20, "normal"),
            text_color=COLORS['accent_1']
        ).pack(side="left", padx=(4, 0))
        
        self.status = ctk.CTkLabel(
            header, text="Ready", font=("Segoe UI", 12),
            text_color=COLORS['fg_sub']
        )
        self.status.pack(side="left", padx=20, pady=(8, 0))
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ModernButton(
            btn_frame, text="🎬 Demo",
            command=self.load_demo_data,
            fg_color=COLORS['accent_1'], width=70
        ).pack(side="left", padx=5)
        
        ModernButton(
            btn_frame, text="⚙️ Settings",
            command=self.show_settings,
            fg_color=COLORS['btn_surface'], width=70
        ).pack(side="left", padx=5)
        
        ModernButton(
            btn_frame, text="About",
            command=self.show_about,
            fg_color=COLORS['btn_surface'], width=70
        ).pack(side="left", padx=5)
        
        ModernButton(
            btn_frame, text="Help ?",
            command=lambda: ModernModal(self, "General Documentation", DOC_GENERAL),
            fg_color=COLORS['btn_surface'], width=70
        ).pack(side="left", padx=5)
        
        # Tab View
        self.tabview = ctk.CTkTabview(
            self, fg_color=COLORS['bg_panel'],
            segmented_button_fg_color=COLORS['bg_main'],
            segmented_button_selected_color=COLORS['bg_panel'],
            segmented_button_selected_hover_color=COLORS['bg_panel'],
            segmented_button_unselected_color=COLORS['bg_main'],
            segmented_button_unselected_hover_color=COLORS['tab_hover'],
            text_color=COLORS['fg_sub'], corner_radius=8
        )
        self.tabview.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Add tabs in order
        self.tabview.add("Bridge Context")
        self.tabview.add("Bridge Flow")
        self.tabview.add("Bridge Planner")
        self.tabview.add("Bridge Compiler")
        self.tabview.add("Bridge Execute")
        
        # Setup tabs
        self.setup_workflow_tab()
        self.setup_node_tab()
        self.setup_planner_tab()
        self.setup_compiler_tab()
        self.setup_execute_tab()
        
        # Setup keyboard shortcuts
        self.setup_keyboard_shortcuts()
    
    def set_status(self, msg, busy=False):
        """Update status bar."""
        self.status.configure(
            text=msg,
            text_color=COLORS['orange'] if busy else COLORS['fg_sub']
        )
        self.update_idletasks()
    
    def setup_workflow_tab(self):
        """Setup Bridge Flow tab."""
        tab = self.tabview.tab("Bridge Flow")
        self.workflow_tab = WorkflowTab(tab)
        self.workflow_tab.pack(fill="both", expand=True)
    
    def setup_node_tab(self):
        """Setup Bridge Context tab."""
        tab = self.tabview.tab("Bridge Context")
        self.node_tab = NodeDevTab(
            tab,
            status_callback=self.set_status,
            workflow_getter=self.get_workflow_json,
            bridgezip_getter=self.get_workflow_bridgezip
        )
        self.node_tab.pack(fill="both", expand=True)
    
    def setup_planner_tab(self):
        """Setup Bridge Planner tab."""
        tab = self.tabview.tab("Bridge Planner")
        self.planner_tab = PlannerTab(tab, workflow_getter=self.get_workflow_json, node_data_getter=self.get_node_data)
        self.planner_tab.pack(fill="both", expand=True)
    
    def setup_compiler_tab(self):
        """Setup Bridge Compiler (Python) tab."""
        tab = self.tabview.tab("Bridge Compiler")
        self.compiler_tab = BridgeCompilerTab(
            tab,
            bridgezip_getter=self.get_workflow_bridgezip,
            node_data_getter=self.get_node_data
        )
        self.compiler_tab.pack(fill="both", expand=True)
    
    def setup_execute_tab(self):
        """Setup Bridge Execute (Python) tab."""
        tab = self.tabview.tab("Bridge Execute")
        self.execute_tab = BridgeExecuteTab(
            tab,
            task_envelope_getter=self.get_task_envelope,
            workflow_getter=self.get_workflow_bridgezip
        )
        self.execute_tab.pack(fill="both", expand=True)
    
    def get_task_envelope(self):
        """Get Task Envelope JSON from Bridge Compiler tab."""
        if hasattr(self, 'compiler_tab'):
            return self.compiler_tab.get_task_envelope_json()
        return ""
    
    def show_settings(self):
        """Display Settings dialog."""
        def refresh_connection_status():
            """Refresh connection status in Bridge Context tab after settings save."""
            if hasattr(self, 'node_tab'):
                # Only refresh if in live mode
                if self.node_tab.data_source_mode.get() == "live":
                    self.node_tab.update_live_status()
        
        SettingsModal(self, on_save_callback=refresh_connection_status)
    
    def show_about(self):
        """Display About dialog with version and copyright information."""
        about_text = f"""Comfy Bridge v{__version__}

A professional tool for compressing, analyzing, and modifying ComfyUI workflows using AI agents.

This application introduces BridgeZip—a compressed, logic-preserving workflow format that significantly reduces size and enables precise collaboration with multiple LLMs.

The Hybrid System:
• Bridge Planner: High-level reasoning and design (ChatGPT)
• Bridge Compiler: Validation and translation
• Bridge Execute: Deterministic execution

For more information, see the Help documentation.

© 2025 Dominic Hawgood | Licensed under Apache 2.0"""
        
        ModernModal(self, "About Comfy Bridge", about_text)
    
    def load_demo_data(self):
        """Load demo data into all tabs."""
        import os
        from tkinter import messagebox
        
        # Get project root directory (two levels up from ui/main_window.py)
        current_file = os.path.abspath(__file__)
        ui_dir = os.path.dirname(current_file)
        project_root = os.path.dirname(ui_dir)
        demo_dir = os.path.join(project_root, "demo")
        
        # File paths
        workflow_json_path = os.path.join(demo_dir, "sample_workflow.json")
        workflow_bridgezip_path = os.path.join(demo_dir, "sample_workflow_bridgezip.txt")
        object_info_path = os.path.join(demo_dir, "sample_object_info.json")
        
        errors = []
        
        # Load workflow JSON into Bridge Flow tab
        try:
            if os.path.exists(workflow_json_path):
                with open(workflow_json_path, 'r', encoding='utf-8') as f:
                    workflow_json = f.read()
                if hasattr(self, 'workflow_tab'):
                    self.workflow_tab.wf_json.set_text(workflow_json)
            else:
                errors.append("sample_workflow.json not found")
        except Exception as e:
            errors.append(f"Error loading workflow JSON: {e}")
        
        # Load BridgeZip into Bridge Flow tab
        try:
            if os.path.exists(workflow_bridgezip_path):
                with open(workflow_bridgezip_path, 'r', encoding='utf-8') as f:
                    bridgezip_text = f.read()
                if hasattr(self, 'workflow_tab'):
                    self.workflow_tab.wf_flow.set_text(bridgezip_text)
            else:
                errors.append("sample_workflow_bridgezip.txt not found")
        except Exception as e:
            errors.append(f"Error loading BridgeZip: {e}")
        
        # Load object_info.json into Bridge Context tab
        try:
            if os.path.exists(object_info_path):
                if hasattr(self, 'node_tab'):
                    # Set to file mode
                    self.node_tab.data_source_mode.set("file")
                    # Set file path
                    self.node_tab.node_file_path = object_info_path
                    # Update status
                    self.node_tab.on_mode_change()
            else:
                errors.append("sample_object_info.json not found")
        except Exception as e:
            errors.append(f"Error loading object_info.json: {e}")
        
        # Show result
        if errors:
            messagebox.showerror(
                "Demo Load Error",
                "Some demo files could not be loaded:\n\n" + "\n".join(errors)
            )
        else:
            messagebox.showinfo(
                "Demo Loaded",
                "Demo data loaded successfully!\n\n"
                "• Workflow JSON loaded into Bridge Flow (left panel)\n"
                "• BridgeZip loaded into Bridge Flow (right panel)\n"
                "• Object info loaded into Bridge Context (file mode)\n\n"
                "You can now explore the compression and features."
            )
            # Switch to Bridge Flow tab to show the loaded data
            self.tabview.set("Bridge Flow")
    
    def get_workflow_json(self):
        """Get current workflow JSON from Workflow tab."""
        if hasattr(self, 'workflow_tab'):
            return self.workflow_tab.get_workflow_json()
        return ""
    
    def get_workflow_bridgezip(self):
        """Get current workflow BridgeZip from Workflow tab."""
        if hasattr(self, 'workflow_tab'):
            return self.workflow_tab.get_workflow_bridgezip()
        return ""
    
    def get_node_data(self):
        """Get current node data from Bridge Context tab."""
        if hasattr(self, 'node_tab'):
            return self.node_tab.get_node_data()
        return ""
    
    def setup_keyboard_shortcuts(self):
        """Set up global keyboard shortcuts."""
        self.bind_all("<Control-s>", lambda e: self._handle_save_shortcut())
        self.bind_all("<Control-c>", lambda e: self._handle_copy_shortcut())
        self.bind_all("<F1>", lambda e: ModernModal(self, "General Documentation", DOC_GENERAL))
        self.bind_all("<Control-h>", lambda e: ModernModal(self, "General Documentation", DOC_GENERAL))
    
    def _handle_save_shortcut(self):
        """Handle Ctrl+S - Save current workflow if in Bridge Flow tab."""
        if hasattr(self, 'workflow_tab'):
            # Try to save from Bridge Flow tab
            workflow_json = self.workflow_tab.get_workflow_json()
            if workflow_json and workflow_json.strip():
                # Trigger save dialog
                from tkinter import filedialog, messagebox
                file_path = filedialog.asksaveasfilename(
                    defaultextension=".json",
                    filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
                )
                if file_path:
                    try:
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(workflow_json)
                        messagebox.showinfo("Saved", f"Workflow saved to:\n{file_path}")
                    except Exception as e:
                        messagebox.showerror("Save Error", f"Failed to save:\n{e}")
    
    def _handle_copy_shortcut(self):
        """Handle Ctrl+C - Copy context if available."""
        # Check if we're in a tab with copy context functionality
        current_tab = self.tabview.get()
        if current_tab == "Bridge Planner" and hasattr(self, 'planner_tab'):
            try:
                self.planner_tab.copy_context_to_clipboard()
            except:
                pass
        elif current_tab == "Bridge Compiler" and hasattr(self, 'compiler_tab'):
            try:
                self.compiler_tab.copy_context_to_clipboard()
            except:
                pass

