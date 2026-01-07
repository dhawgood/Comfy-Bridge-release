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

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from utils.ui_helpers import COLORS, ModernButton, ModernModal, TextEditorPanel
from utils.json_tools import beautify_json, minify_json
from engine.bridgezip import compress_workflow, inflate_workflow

DOC_WORKFLOW = """BRIDGE FLOW — WORKFLOW COMPRESSION

PURPOSE

This tab provides conversion and inspection tools for workflows. It converts between standard ComfyUI JSON and BridgeZip format, enabling compression and inflation of workflows so they can be exchanged across the Comfy-Bridge system. 

ROLE IN HYBRID SYSTEM

Bridge Flow serves as the conversion layer:

- Before Planning: Convert JSON → BridgeZip for token-efficient analysis
- After Execution: Convert BridgeZip → JSON for importing back into ComfyUI
- Throughout the workflow: Inspect, validate, and format workflow data

WHAT IS BRIDGEZIP?

BridgeZip is a token-efficient format for sharing ComfyUI workflows with AI.

Standard ComfyUI JSON files contain massive amounts of redundant data:
- Node positions and sizes (UI layout)
- Repeated widget values
- Coordinate information
- Metadata that doesn't affect workflow logic

BridgeZip strips away this bloat while preserving:
- Node types and connections
- Widget values
- Link relationships
- Properties and metadata

Result: Significant reduction in token usage, enabling AI collaboration on complex workflows.

CRITICAL WARNINGS

1. UNMUTE NODES: Before saving in ComfyUI, ensure NO nodes are Muted or Bypassed.
   Muted nodes export with 'internal flags' that become permanent when compressed,
   potentially breaking the logic when you Inflate it later.

2. STANDARD SAVE ONLY: Do not use "Save (API Format)".
   This tool requires the standard JSON containing layout/widget data to function correctly.

HOW TO USE

1. COMPRESS (JSON → BridgeZip):
   - Paste your standard ComfyUI JSON on the LEFT panel
   - Click "COMPRESS (JSON ➔ BridgeZip)"
   - Copy/ Save the BridgeZip text from the RIGHT panel
   - Use this in Bridge Planner, Bridge Context, Bridge Compiler, or Bridge Execute (much smaller, token-efficient)

2. INFLATE (BridgeZip → JSON):
   - Paste the BridgeZip text from Bridge Execute (or any source) into the RIGHT panel
   - Click "INFLATE (BridgeZip ➔ JSON)"
   - Save the JSON from the LEFT panel
   - Load it into ComfyUI

3. JSON TOOLS:
   - "Beautify": Formats JSON with indentation so humans can read it
   - "Minify": Removes all whitespace to make JSON as small as possible for storage

TYPICAL WORKFLOW

1. Connect to ComfyUI and export workflow 
2. Convert workflow to BridgeZip (this tab)
3. Plan modifications in Bridge Planner
4. Extract node definitions in Bridge Context for Bridge Planner
5. Compile plan in Bridge Compiler
6. Execute changes in Bridge Execute
7. Inflate result back to JSON (this tab)
8. Test workflow in ComfyUI

COMMON ISSUES

- "Error: Invalid JSON": Check that your JSON is valid. Use "Beautify" to format and inspect.
- "Error: Missing required fields": Ensure you're using standard ComfyUI JSON, not API format.
- BridgeZip won't inflate: Verify the BridgeZip text is complete and wasn't truncated."""

class WorkflowTab(ctk.CTkFrame):
    """Bridge Flow Tab - JSON/BridgeZip conversion."""
    
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS['bg_panel'], corner_radius=0)
        self.setup_ui()
    
    def setup_ui(self):
        """Build the workflow tools UI."""
        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", pady=5)
        
        # Row 1: Main action buttons (centered)
        btn_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 5))
        
        ModernButton(
            btn_row, text="COMPRESS (JSON ➔ BridgeZip)", command=self.do_compress,
            fg_color=COLORS['accent_1']
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        ModernButton(
            btn_row, text="INFLATE (BridgeZip ➔ JSON)", command=self.do_inflate,
            fg_color=COLORS['success']
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Row 2: Info button (separate line)
        info_row = ctk.CTkFrame(ctrl, fg_color="transparent")
        info_row.pack(fill="x")
        
        ModernButton(
            info_row, text="ℹ", command=lambda: ModernModal(self, "Bridge Flow Help", DOC_WORKFLOW),
            fg_color=COLORS['info'], text_color="black", width=30, height=28
        ).pack(side="right")
        
        # Fixed 50/50 split - no dragging
        split_container = ctk.CTkFrame(self, fg_color="transparent")
        split_container.pack(fill="both", expand=True, pady=10)
        
        self.wf_json = TextEditorPanel(split_container, "Standard JSON", [("JSON Files", "*.json")])
        self.wf_json.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        self.wf_flow = TextEditorPanel(split_container, "BridgeZip Format", [("Text Files", "*.txt")])
        self.wf_flow.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # Compression stats frame (initially hidden)
        self.stats_frame = ctk.CTkFrame(self.wf_flow, fg_color="transparent", height=24)
        self.stats_label = ctk.CTkLabel(
            self.stats_frame, text="", 
            font=("Segoe UI", 9), 
            text_color=COLORS['fg_sub']
        )
        self.stats_label.pack(side="left", padx=10)
        # Don't pack stats_frame initially - it will be shown after compression
        
        tools = ctk.CTkFrame(self.wf_json, fg_color="transparent", height=30)
        tools.pack(side="bottom", fill="x", pady=2)
        
        ModernButton(
            tools, text="Beautify",
            command=lambda: self.wf_json.set_text(beautify_json(self.wf_json.get_text())),
            fg_color=COLORS['btn_surface'], height=24, width=60
        ).pack(side="left", padx=2)
        
        ModernButton(
            tools, text="Minify",
            command=lambda: self.wf_json.set_text(minify_json(self.wf_json.get_text())),
            fg_color=COLORS['btn_surface'], height=24, width=60
        ).pack(side="left", padx=2)
    
    def _format_size(self, size_bytes):
        """Format bytes to KB/MB with 1 decimal place."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def do_compress(self):
        """Compress JSON to BridgeZip."""
        r = compress_workflow(self.wf_json.get_text())
        if r.startswith("Error"):
            messagebox.showerror("Error", r)
            # Hide stats on error
            self.stats_frame.pack_forget()
        else:
            self.wf_flow.set_text(r)
            # Calculate and display compression stats
            original_text = self.wf_json.get_text()
            original_size = len(original_text.encode('utf-8'))
            compressed_size = len(r.encode('utf-8'))
            compression_pct = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0
            node_count = len([l for l in r.split('\n') if l.startswith('N')])
            
            # Format stats (Option A - Single Line Compact)
            stats_text = f"📊 {compression_pct:.1f}% compression | {self._format_size(original_size)} → {self._format_size(compressed_size)} | {node_count} nodes"
            self.stats_label.configure(text=stats_text)
            self.stats_frame.pack(side="bottom", fill="x", pady=2)
    
    def do_inflate(self):
        """Inflate BridgeZip to JSON."""
        r = inflate_workflow(self.wf_flow.get_text())
        if r.startswith("Error"):
            messagebox.showerror("Error", r)
        else:
            self.wf_json.set_text(r)
    
    def get_workflow_json(self):
        """Get current workflow JSON text."""
        return self.wf_json.get_text()
    
    def get_workflow_bridgezip(self):
        """Get current workflow BridgeZip text."""
        return self.wf_flow.get_text()

