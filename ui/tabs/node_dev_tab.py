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
from tkinter import filedialog, messagebox
import threading
import os
from utils.ui_helpers import COLORS, ModernButton, ModernModal, TextEditorPanel
from utils.config import get_comfyui_url
from logic.filtering import fetch_live_node_meta, compress_nodes_v4_logic, fetch_live_categories, _get_live_object_info
from logic.extraction import extract_categories_logic, extract_models_logic, extract_models_logic_live, extract_group_nodes_logic, extract_nodes_from_bridgezip

DOC_NODES = """BRIDGE CONTEXT — NODE EXTRACTION

PURPOSE

This tab extracts all data needed for LLM-assisted workflow editing in the hybrid system (1 external AI agent + 2 deterministic Python components).

It provides node definitions, model indexes, pack lists, and workflow components that Bridge Planner, Bridge Compiler, and Bridge Execute require to generate valid, accurate workflows for your specific ComfyUI installation.

ROLE IN HYBRID SYSTEM

Bridge Context supplies essential data to all three components:

- Bridge Planner: Needs node definitions to design valid solutions
- Bridge Compiler: Requires node definitions to validate and compile Task Envelopes
- Bridge Execute: Uses node definitions when processing workflow modifications

Without accurate node definitions, the agents cannot generate workflows that work with your installed custom nodes.

DATA SOURCE MODES
-----------------
LIVE MODE (Recommended):
- Connects directly to your running ComfyUI instance via API
- No file downloads needed
- Always up-to-date with your current installation
- Select "Live (ComfyUI API)" radio button

FILE MODE:
- Requires manual download of object_info.json
- Useful when ComfyUI is not running
- Select "File (object_info.json)" radio button
- Click "Load File" to select your object_info.json

GETTING object_info.json (File Mode Only)
------------------------------------------
If using File mode, you need to download object_info.json from ComfyUI:

>> COMFYUI WEB (Browser):
1. Ensure ComfyUI is running
2. Navigate to: http://127.0.0.1:8188/object_info
   (Replace IP/Port if your ComfyUI uses different settings)
3. Right-click on the page → "Save Page As..."
4. Save as "object_info.json"

>> COMFYUI DESKTOP (Electron):
1. Open ComfyUI Desktop application
2. Go to Settings → About → System Info
3. Note the port number (e.g. 8188)
4. Open an external browser (Chrome/Edge)
5. Navigate to: http://127.0.0.1:8188/object_info
   (Use the port from step 3)
6. Right-click on the page → "Save Page As..."
7. Save as "object_info.json"

EXTRACTION ACTIONS
-------------------
1. EXTRACT JSON
   - Full node metadata in JSON format
   - Use for initial AI setup or detailed node inspection
   - Smart Filter: Leave empty for all nodes, or enter: NodeA, NodeB

2. COMPRESSED META
   - Compressed signature format (@NodeName +input -output)
   - Token-efficient for AI context
   - Recommended for Bridge Planner and Bridge Compiler
   - Smart Filter: Leave empty for all nodes, or enter: NodeA, NodeB

3. EXTRACT PACKS
   - Lists all installed node packs/categories
   - Alphabetically sorted, excludes internal categories
   - Useful for understanding your installation

4. EXTRACT MODELS
   - Hierarchical selection UI (Type → Category → Models)
   - Select specific model types and categories
   - Prevents AI from inventing fake model names
   - Essential for accurate model selection in workflows

5. EXTRACT GROUPS
   - Extracts groups from a workflow JSON file
   - Shows group names with node counts
   - Select multiple groups for extraction

6. EXTRACT NODES
   - Extracts specific nodes from a BridgeZip file
   - Filter by node ID (numeric) or node type name
   - Smart Filter: Leave empty for all nodes, or enter: 1, 2, NodeA

7. COMPRESS ALL
   - Compresses ALL nodes to signature format
   - Use for complete node library export
   - Warning: This processes many nodes (may take time)

SMART FILTER USAGE
------------------
- Leave empty = Extract all nodes
- Enter node names: NodeA, NodeB, NodeC
- Supports spaces, commas, or + as separators
- Case-insensitive matching
- For EXTRACT NODES: Can filter by numeric IDs (1, 2, 3) or node type names

TYPICAL WORKFLOW

1. Extract node definitions (COMPRESSED META recommended)
2. Extract model index if needed
3. Convert workflow to BridgeZip (Bridge Flow)
4. Plan modifications (Bridge Planner)
5. Compile plan (Bridge Compiler)
6. Execute changes (Bridge Execute)
7. Test workflow in ComfyUI

WHEN TO USE EACH FEATURE
-------------------------
- EXTRACT JSON: Initial AI setup, need full node details
- COMPRESSED META: Regular AI context for Bridge Planner and Bridge Compiler (token-efficient)
- EXTRACT PACKS: Understanding available libraries
- EXTRACT MODELS: Preventing AI from inventing model names during planning
- EXTRACT GROUPS: Working with specific workflow groups
- EXTRACT NODES: Extracting specific nodes from a workflow
- COMPRESS ALL: Complete node library for AI training"""

NODE_FIELD_SCHEMA = [
    "class_name", "display_name", "category", "python_module", "output_node",
    "input", "input_order", "output", "output_name", "output_is_list",
    "widgets", "widgets_values", "properties", "rect",
    "cnr_id", "ver", "custom_data", "extension_data",
    "description", "help", "tags", "color", "flags"
]

class NodeDevTab(ctk.CTkFrame):
    """Bridge Context Tab - Node extraction and filtering."""
    
    def __init__(self, parent, status_callback=None, workflow_getter=None, bridgezip_getter=None):
        super().__init__(parent, fg_color=COLORS['bg_panel'], corner_radius=0)
        self.status_callback = status_callback
        self.workflow_getter = workflow_getter  # Function to get workflow JSON
        self.bridgezip_getter = bridgezip_getter  # Function to get BridgeZip
        self.node_file_path = None
        self.field_vars = {}
        self.data_source_mode = tk.StringVar(value="live")  # "live" or "file"
        # JSON export mode for EXTRACT JSON: "planner" (LLM blocks) or "compiler" (strict dict)
        self.json_mode = tk.StringVar(value="planner")
        # Shared workflow storage for EXTRACT GROUPS and EXTRACT NODES
        self.shared_workflow = {
            "json": None,
            "bridgezip": None,
            "filename": None
        }
        self.setup_ui()
    
    def setup_ui(self):
        """Build the node developer UI."""
        ctrl_container = ctk.CTkFrame(self, fg_color="transparent")
        ctrl_container.pack(fill="x", pady=5, padx=5)
        
        # Row 1: Data Source Selector
        row1 = ctk.CTkFrame(ctrl_container, fg_color=COLORS['bg_main'], corner_radius=8, border_width=1, border_color="#30363d")
        row1.pack(fill="x", pady=(0, 10), padx=0, ipady=8)
        
        # Left side: Radio buttons
        radio_frame = ctk.CTkFrame(row1, fg_color="transparent")
        radio_frame.pack(side="left", padx=15, pady=5)
        
        ctk.CTkLabel(
            radio_frame, text="Data Source:", font=("Segoe UI", 12, "bold"),
            text_color=COLORS['fg_text']
        ).pack(side="left", padx=(0, 15))
        
        # Live Radio Button
        live_radio = ctk.CTkRadioButton(
            radio_frame, text="Live (ComfyUI API)", variable=self.data_source_mode,
            value="live", font=("Segoe UI", 11), command=self.on_mode_change,
            fg_color=COLORS['accent_1'], hover_color=COLORS['accent_1'],
            text_color=COLORS['fg_text']
        )
        live_radio.pack(side="left", padx=(0, 20))
        
        # File Radio Button
        file_radio = ctk.CTkRadioButton(
            radio_frame, text="File (object_info.json)", variable=self.data_source_mode,
            value="file", font=("Segoe UI", 11), command=self.on_mode_change,
            fg_color=COLORS['accent_1'], hover_color=COLORS['accent_1'],
            text_color=COLORS['fg_text']
        )
        file_radio.pack(side="left", padx=(0, 20))
        
        # Status indicator frame
        status_frame = ctk.CTkFrame(row1, fg_color="transparent")
        status_frame.pack(side="left", fill="x", expand=True, padx=15)
        
        self.status_indicator = ctk.CTkLabel(
            status_frame, text="", font=("Segoe UI", 10),
            text_color=COLORS['fg_sub']
        )
        self.status_indicator.pack(side="left")
        
        # File load button (only visible in file mode)
        self.file_load_btn = ModernButton(
            status_frame, text="📂 Load File", command=self.load_node_file,
            fg_color=COLORS['btn_surface'], width=120, height=28
        )
        self.file_load_btn.pack(side="left", padx=(10, 0))
        
        # Help button
        ModernButton(
            row1, text="ℹ", command=lambda: ModernModal(self, "Bridge Context Help", DOC_NODES),
            fg_color=COLORS['info'], text_color="black", width=30, height=28
        ).pack(side="right", padx=15)
        
        # Initialize status
        self.on_mode_change()
        
        # Row 2: Filter Input
        row2 = ctk.CTkFrame(ctrl_container, fg_color=COLORS['bg_main'], corner_radius=6, border_width=1, border_color="#30363d")
        row2.pack(fill="x", pady=(0, 10), ipady=3)
        
        ctk.CTkLabel(
            row2, text="Smart Filter:", font=("Segoe UI", 12, "bold"),
            text_color="#ccc"
        ).pack(side="left", padx=(10, 3))
        
        self.filter_entry = ctk.CTkEntry(
            row2,
            placeholder_text="Enter node names: NodeA, NodeB (empty = all nodes)",
            font=("Segoe UI", 12),
            corner_radius=6, border_width=1, border_color="#30363d"
        )
        self.filter_entry.pack(side="left", fill="x", expand=True, padx=(3, 3))

        # JSON mode toggle (Planner / Compiler) - packed first (rightmost)
        json_mode_frame = ctk.CTkFrame(row2, fg_color="transparent")
        json_mode_frame.pack(side="right", padx=(3, 2), pady=2)

        planner_radio = ctk.CTkRadioButton(
            json_mode_frame,
            text="Planner",
            variable=self.json_mode,
            value="planner",
            font=("Segoe UI", 9),
            fg_color=COLORS["accent_1"],
            hover_color=COLORS["accent_1"],
        )
        planner_radio.pack(side="left", padx=(0, 0))

        compiler_radio = ctk.CTkRadioButton(
            json_mode_frame,
            text="Compiler",
            variable=self.json_mode,
            value="compiler",
            font=("Segoe UI", 9),
            fg_color=COLORS["accent_1"],
            hover_color=COLORS["accent_1"],
        )
        compiler_radio.pack(side="left")

        # EXTRACT JSON - packed second (left of radio buttons)
        ModernButton(
            row2, text="EXTRACT JSON", command=lambda: (self.update_smart_filter_placeholder("extract_json"), self.start_extract_json()),
            fg_color=COLORS['success'], width=130, height=28
        ).pack(side="right", padx=(3, 3), pady=2)

        # COMPRESSED META - packed third (left of EXTRACT JSON)
        ModernButton(
            row2, text="COMPRESSED META", command=lambda: (self.update_smart_filter_placeholder("compress_meta"), self.start_compress_meta()),
            fg_color=COLORS['btn_surface'], hover_color=COLORS['btn_hover'],
            border_width=1, border_color=COLORS['accent_1'], width=140, height=28
        ).pack(side="right", padx=(3, 3), pady=2)
        
        # Field Checklist Panel
        self.create_field_checklist(ctrl_container)
        
        # Row 3: Action Buttons
        row3 = ctk.CTkFrame(ctrl_container, fg_color="transparent")
        row3.pack(fill="x", pady=(5, 5))
        row3.grid_columnconfigure(0, weight=1)
        row3.grid_columnconfigure(1, weight=1)
        row3.grid_columnconfigure(2, weight=1)
        row3.grid_columnconfigure(3, weight=1)
        row3.grid_columnconfigure(4, weight=1)

        ModernButton(
            row3, text="EXTRACT PACKS", command=self.start_extract,
            fg_color=COLORS['btn_surface'], hover_color=COLORS['btn_hover'],
            border_width=1, border_color=COLORS['orange']
        ).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        
        ModernButton(
            row3, text="EXTRACT MODELS", command=self.start_extract_models,
            fg_color=COLORS['btn_surface'], hover_color=COLORS['btn_hover'],
            border_width=1, border_color=COLORS['purple']
        ).grid(row=0, column=1, sticky="ew", padx=5)
        
        ModernButton(
            row3, text="EXTRACT GROUPS", command=self.start_extract_groups,
            fg_color=COLORS['btn_surface'], hover_color=COLORS['btn_hover'],
            border_width=1, border_color=COLORS['accent_2']
        ).grid(row=0, column=2, sticky="ew", padx=5)
        
        ModernButton(
            row3, text="EXTRACT NODES", command=lambda: (self.update_smart_filter_placeholder("extract_nodes"), self.extract_nodes()),
            fg_color=COLORS['btn_surface'], hover_color=COLORS['btn_hover'],
            border_width=1, border_color=COLORS['accent_1']
        ).grid(row=0, column=3, sticky="ew", padx=5)
        
        ModernButton(
            row3, text="COMPRESS ALL", command=self.start_compress_all,
            fg_color=COLORS['accent_1']
        ).grid(row=0, column=4, sticky="ew", padx=(5, 0))
        
        self.node_out = TextEditorPanel(
            self, "", [("Text Files", "*.txt")]
        )
        self.node_out.pack(fill="both", expand=True, pady=(10, 0))
        
        # Compression stats frame (initially hidden)
        self.stats_frame = ctk.CTkFrame(self.node_out, fg_color="transparent", height=24)
        self.stats_label = ctk.CTkLabel(
            self.stats_frame, text="", 
            font=("Segoe UI", 9), 
            text_color=COLORS['fg_sub']
        )
        self.stats_label.pack(side="left", padx=10)
        
        # Mark as read-only and apply binding
        self.node_out._readonly = True
        self.node_out._prevent_editing = self._prevent_output_editing
        self.node_out.text_area.bind("<Key>", self._prevent_output_editing)
    
    def create_field_checklist(self, parent):
        """Create the field selection checklist."""
        check_frame = ctk.CTkFrame(parent, fg_color=COLORS['bg_main'], corner_radius=6, border_width=1, border_color="#30363d")
        check_frame.pack(fill="x", pady=(0, 10), padx=0)
        
        head = ctk.CTkFrame(check_frame, fg_color="transparent")
        head.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            head, text="Field Selection Checklist", font=("Segoe UI", 11, "bold"),
            text_color=COLORS['fg_sub']
        ).pack(side="left")
        
        def toggle_all(state):
            for k, v in self.field_vars.items():
                v.set(state)
        
        btn_box = ctk.CTkFrame(head, fg_color="transparent")
        btn_box.pack(side="right")
        
        ctk.CTkButton(
            btn_box, text="All", width=40, height=20, font=("Segoe UI", 10),
            command=lambda: toggle_all(True), fg_color=COLORS['btn_surface']
        ).pack(side="left", padx=2)
        
        ctk.CTkButton(
            btn_box, text="None", width=40, height=20, font=("Segoe UI", 10),
            command=lambda: toggle_all(False), fg_color=COLORS['btn_surface']
        ).pack(side="left", padx=2)

        grid_frame = ctk.CTkFrame(check_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        cols = 4
        for i, field in enumerate(NODE_FIELD_SCHEMA):
            var = tk.BooleanVar(value=True)
            self.field_vars[field] = var
            chk = ctk.CTkCheckBox(
                grid_frame, text=field, variable=var, font=("Consolas", 11),
                checkbox_height=16, checkbox_width=16, border_width=1,
                fg_color=COLORS["accent_1"], hover_color=COLORS["accent_1"],
                border_color=COLORS["fg_sub"]
            )
            chk.grid(row=i//cols, column=i%cols, sticky="w", padx=5, pady=2)
            grid_frame.grid_columnconfigure(i%cols, weight=1)
    
    def update_smart_filter_placeholder(self, context):
        """Update Smart Filter placeholder text based on context."""
        placeholders = {
            "extract_json": "Filter nodes for JSON extraction: KSampler, CLIPTextEncode (empty = all nodes)",
            "compress_meta": "Filter nodes for compression: KSampler, CLIPTextEncode (empty = all nodes)",
            "extract_nodes": "Filter by node ID or name: 1, 2, EmptyLatentImage (empty = all nodes)",
            "default": "Enter node names: NodeA, NodeB (empty = all nodes)"
        }
        placeholder = placeholders.get(context, placeholders["default"])
        self.filter_entry.configure(placeholder_text=placeholder)
    
    def on_mode_change(self):
        """Handle data source mode change."""
        mode = self.data_source_mode.get()
        
        if mode == "live":
            self.file_load_btn.pack_forget()
            self.update_live_status()
        else:  # file mode
            self.file_load_btn.pack(side="left", padx=(10, 0))
            self.update_file_status()
    
    def update_live_status(self):
        """Update status indicator for live mode."""
        # Test connection
        base_url = get_comfyui_url()
        try:
            import urllib.request
            req = urllib.request.Request(f"{base_url}/object_info", method="HEAD")
            with urllib.request.urlopen(req, timeout=2) as response:
                if response.status == 200:
                    self.status_indicator.configure(
                        text="● Connected to ComfyUI",
                        text_color=COLORS['success']
                    )
                    return
        except:
            pass
        
        self.status_indicator.configure(
            text=f"● ComfyUI not detected ({base_url})",
            text_color=COLORS['red']
        )
    
    def update_file_status(self):
        """Update status indicator for file mode."""
        if self.node_file_path:
            filename = os.path.basename(self.node_file_path)
            self.status_indicator.configure(
                text=f"● Loaded: {filename}",
                text_color=COLORS['success']
            )
        else:
            self.status_indicator.configure(
                text="● No file loaded",
                text_color=COLORS['fg_sub']
            )
    
    def load_node_file(self):
        """Load object_info.json file."""
        path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if path:
            self.node_file_path = path
            self.update_file_status()
    
    def set_status(self, msg, busy=False):
        """Update status via callback."""
        if self.status_callback:
            self.status_callback(msg, busy)
    
    def _format_size(self, size_bytes):
        """Format bytes to KB/MB with 1 decimal place."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
    
    def finish(self, res, stats_info=None):
        """Finish async operation and update UI.
        
        Args:
            res: Result text to display
            stats_info: Optional dict with stat type and data:
                - 'type': 'compression', 'packs', 'groups', 'nodes', 'json', 'models'
                - Additional keys depend on type
        """
        def update_ui():
            self.node_out.set_text(res)
            self.set_status("✅ Done")
            
            # Show stats if provided
            if stats_info and 'type' in stats_info:
                stats_type = stats_info['type']
                stats_text = ""
                
                if stats_type == 'compression':
                    original_size = stats_info.get('original_size', 0)
                    compressed_size = len(res.encode('utf-8'))
                    compression_pct = ((original_size - compressed_size) / original_size) * 100 if original_size > 0 else 0
                    node_count = len([l for l in res.split('\n') if l.startswith('@')])
                    stats_text = f"📊 {compression_pct:.1f}% compression | {self._format_size(original_size)} → {self._format_size(compressed_size)} | {node_count} nodes"
                
                elif stats_type == 'packs':
                    # Count pack lines (skip header lines)
                    pack_lines = [l for l in res.split('\n') if l.strip() and not l.startswith('INSTALLED') and not l.startswith('---')]
                    pack_count = len(pack_lines)
                    stats_text = f"📦 {pack_count} packs extracted"
                
                elif stats_type == 'groups':
                    # Parse summary from output (format: "=== EXTRACTED GROUPS (X group(s), Y total nodes) ===")
                    import re
                    match = re.search(r'EXTRACTED GROUPS \((\d+) group\(s\), (\d+) total nodes\)', res)
                    if match:
                        group_count = match.group(1)
                        node_count = match.group(2)
                        stats_text = f"📁 {group_count} groups, {node_count} nodes"
                    else:
                        # Fallback: count group headers
                        group_count = len([l for l in res.split('\n') if l.startswith('GROUP:')])
                        node_count = len([l for l in res.split('\n') if l.startswith('  N')])
                        if group_count > 0:
                            stats_text = f"📁 {group_count} groups, {node_count} nodes"
                
                elif stats_type == 'nodes':
                    # Count nodes in BridgeZip (lines starting with 'N')
                    node_count = len([l for l in res.split('\n') if l.startswith('N') and ':' in l])
                    stats_text = f"🔍 {node_count} nodes extracted"
                
                elif stats_type == 'json':
                    # Count JSON node objects (rough estimate: count lines with "class_name" or count top-level objects)
                    import json
                    try:
                        data = json.loads(res)
                        if isinstance(data, dict):
                            node_count = len(data) if 'node_definitions' not in data else len(data.get('node_definitions', {}))
                        else:
                            node_count = len(data) if isinstance(data, list) else 0
                        stats_text = f"📄 {node_count} nodes extracted"
                    except:
                        # Fallback: count lines with common node fields
                        node_count = len([l for l in res.split('\n') if '"class_name"' in l or '"display_name"' in l])
                        stats_text = f"📄 {node_count} nodes extracted"
                
                elif stats_type == 'models':
                    # Parse model counts from output format
                    import re
                    checkpoints = len(re.findall(r'\[CHECKPOINTS \((\d+)\)\]', res))
                    loras = len(re.findall(r'\[LORAS \((\d+)\)\]', res))
                    vaes = len(re.findall(r'\[VAES \((\d+)\)\]', res))
                    unets = len(re.findall(r'\[UNETS \((\d+)\)\]', res))
                    clips = len(re.findall(r'\[CLIPS \((\d+)\)\]', res))
                    # Extract actual counts from the format
                    ckpt_match = re.search(r'\[CHECKPOINTS \((\d+)\)\]', res)
                    lora_match = re.search(r'\[LORAS \((\d+)\)\]', res)
                    vae_match = re.search(r'\[VAES \((\d+)\)\]', res)
                    unet_match = re.search(r'\[UNETS \((\d+)\)\]', res)
                    clip_match = re.search(r'\[CLIPS \((\d+)\)\]', res)
                    parts = []
                    if ckpt_match:
                        parts.append(f"{ckpt_match.group(1)} checkpoints")
                    if lora_match:
                        parts.append(f"{lora_match.group(1)} LoRAs")
                    if vae_match:
                        parts.append(f"{vae_match.group(1)} VAEs")
                    if unet_match:
                        parts.append(f"{unet_match.group(1)} UNETs")
                    if clip_match:
                        parts.append(f"{clip_match.group(1)} CLIPs")
                    if parts:
                        stats_text = f"🎨 {', '.join(parts)}"
                    else:
                        stats_text = f"🎨 Models extracted"
                
                if stats_text:
                    self.stats_label.configure(text=stats_text)
                    self.stats_frame.pack(side="bottom", fill="x", pady=2)
                else:
                    self.stats_frame.pack_forget()
            else:
                # Hide stats for operations without stats
                self.stats_frame.pack_forget()
        self.after(0, update_ui)
    
    def start_extract(self):
        """Extract categories/packs."""
        mode = self.data_source_mode.get()
        
        if mode == "live":
            self.set_status("⏳ Extracting Packs (live)...", True)
            threading.Thread(
                target=lambda: self.finish(fetch_live_categories(), stats_info={'type': 'packs'}),
                daemon=True
            ).start()
        else:  # file mode
            if not self.node_file_path:
                return messagebox.showwarning("Error", "Load object_info.json first")
            self.set_status("⏳ Extracting Packs...", True)
            threading.Thread(
                target=lambda: self.finish(extract_categories_logic(self.node_file_path), stats_info={'type': 'packs'}),
                daemon=True
            ).start()
    
    def start_extract_models(self):
        """Extract models - embeds selection panel in output area."""
        mode = self.data_source_mode.get()
        
        def embed_panel(models_data, error):
            if error:
                self.finish(error)
                return
            
            from ui.modals.model_selection import ModelSelectionPanel
            panel = ModelSelectionPanel(
                self.node_out, models_data, 
                lambda output: self.finish(output, stats_info={'type': 'models'})
            )
            self.node_out.embed_widget(panel)
        
        if mode == "live":
            self.set_status("⏳ Loading Models (live)...", True)
            threading.Thread(
                target=lambda: self._collect_and_embed_panel("live", None, embed_panel),
                daemon=True
            ).start()
        else:  # file mode
            if not self.node_file_path:
                return messagebox.showwarning("Error", "Load object_info.json first")
            self.set_status("⏳ Loading Models...", True)
            threading.Thread(
                target=lambda: self._collect_and_embed_panel("file", self.node_file_path, embed_panel),
                daemon=True
            ).start()
    
    def _collect_and_embed_panel(self, mode, file_path, callback):
        """Collect models and embed panel in main thread."""
        from logic.extraction import collect_models_hierarchical
        models_data, error = collect_models_hierarchical(mode, file_path)
        self.after(0, lambda: callback(models_data, error))
    
    def start_extract_json(self):
        """Extract full JSON node metadata."""
        query = self.filter_entry.get().strip()
        
        selected = [k for k, v in self.field_vars.items() if v.get()]
        if not selected:
            return messagebox.showwarning("Selection Empty", "Select at least one field from the checklist.")
        
        mode = self.data_source_mode.get()
        json_mode = self.json_mode.get()

        if mode == "live":
            if not query:
                self.set_status("⏳ Fetching all nodes (live)...", True)
            else:
                self.set_status(f"⏳ Fetching '{query}' (live)...", True)

            if json_mode == "planner":
                worker = lambda: self.finish(
                    fetch_live_node_meta(query, selected),
                    stats_info={"type": "json"},
                )
            else:
                worker = lambda: self.finish(
                    fetch_live_node_meta_compiler(query, selected),
                    stats_info={"type": "json"},
                )

            threading.Thread(target=worker, daemon=True).start()
        else:  # file mode
            if not self.node_file_path:
                return messagebox.showwarning("Error", "Load object_info.json first")
            if not query:
                self.set_status("⏳ Extracting all nodes from file...", True)
            else:
                self.set_status(f"⏳ Extracting '{query}' from file...", True)

            if json_mode == "planner":
                worker = lambda: self.finish(
                    self._extract_json_from_file(query, selected),
                    stats_info={"type": "json"},
                )
            else:
                worker = lambda: self.finish(
                    self._extract_json_from_file_compiler(query, selected),
                    stats_info={"type": "json"},
                )

            threading.Thread(target=worker, daemon=True).start()
    
    def start_compress_meta(self):
        """Compress nodes to signature format."""
        query = self.filter_entry.get().strip()
        
        mode = self.data_source_mode.get()
        
        if mode == "live":
            # Live compression - need to get data and compress it
            if not query:
                self.set_status("⏳ Compressing all nodes (live)...", True)
            else:
                self.set_status(f"⏳ Compressing '{query}' (live)...", True)
            threading.Thread(
                target=lambda: self._compress_live_with_stats(query),
                daemon=True
            ).start()
        else:  # file mode
            if not self.node_file_path:
                return messagebox.showwarning("Error", "Load object_info.json first")
            if not query:
                if not messagebox.askyesno("Confirm", "This will process ALL nodes.\nProceed?"):
                    return
                self.set_status("⏳ Compressing ALL nodes...", True)
            else:
                self.set_status(f"⏳ Compressing '{query}'...", True)
            # Get original file size for stats
            try:
                original_size = os.path.getsize(self.node_file_path)
            except:
                original_size = 0
            threading.Thread(
                target=lambda: self.finish(
                    compress_nodes_v4_logic(self.node_file_path, query),
                    stats_info={'type': 'compression', 'original_size': original_size} if original_size > 0 else None
                ),
                daemon=True
            ).start()
    
    def _compress_live_nodes(self, search_query=""):
        """Compress nodes from live ComfyUI source.
        
        Returns:
            tuple: (result_text, original_size_bytes) or (error_message, None)
        """
        import json
        from logic.filtering import _get_live_object_info
        from engine.bridgezip import TYPE_SHORTHAND_MAP
        
        data = _get_live_object_info()
        if not data:
            base_url = get_comfyui_url()
            return (f"Error connecting to ComfyUI ({base_url}). Ensure it is running.", None)
        
        # Estimate original size from JSON data
        original_size = len(json.dumps(data, ensure_ascii=False).encode('utf-8'))
        
        node_defs = data.get("node_definitions", data)
        
        # Parse search terms
        search_query = search_query.strip() if search_query else ""
        search_terms = [t.strip().lower() for t in search_query.split(',')] if search_query else []
        
        result = []
        
        for node_name, node_info in node_defs.items():
            if not isinstance(node_info, dict):
                continue
            
            # Filter by search terms if provided
            if search_terms:
                cat_raw = node_info.get("category", "")
                cat_str = str(cat_raw[0]) if isinstance(cat_raw, list) and cat_raw else str(cat_raw)
                if not (any(q in node_name.lower() for q in search_terms) or any(q in cat_str.lower() for q in search_terms)):
                    continue
            
            parts = [f"@{node_name}"]
            
            def process_inputs(inputs_dict, prefix):
                for name, spec in inputs_dict.items():
                    if isinstance(spec, (list, tuple)) and len(spec) > 0:
                        raw_type = spec[0]
                        if isinstance(raw_type, list):
                            parts.append(f"%{name}:COMBO")
                            continue
                        if raw_type in ["INT", "FLOAT", "STRING", "BOOLEAN"]:
                            parts.append(f"%{name}:{raw_type}")
                            continue
                        if raw_type in TYPE_SHORTHAND_MAP:
                            shorthand = TYPE_SHORTHAND_MAP.get(raw_type, '*')
                            parts.append(f"{prefix}{name}:{shorthand}")
                            continue
                        parts.append(f"{prefix}{name}:*")
            
            if "required" in node_info.get("input", {}): 
                process_inputs(node_info["input"]["required"], '+')
            if "optional" in node_info.get("input", {}): 
                process_inputs(node_info["input"]["optional"], '?')
            
            if "output" in node_info:
                outputs = node_info["output"]
                if isinstance(outputs, list):
                    for out_type in outputs:
                        if isinstance(out_type, list): 
                            safe_type = str(out_type[0]) if out_type else "*"
                        else: 
                            safe_type = str(out_type)
                        parts.append(f"-{TYPE_SHORTHAND_MAP.get(safe_type, '*')}")
            
            result.append(" ".join(parts))
        
        result_text = "\n".join(result) if result else "No nodes found."
        return (result_text, original_size)
    
    def _compress_live_with_stats(self, search_query=""):
        """Compress live nodes and finish with stats."""
        result, original_size = self._compress_live_nodes(search_query)
        if original_size is None:
            # Error case
            self.finish(result)
        else:
            self.finish(result, stats_info={'type': 'compression', 'original_size': original_size})
    
    def start_compress_all(self):
        """Compress all nodes."""
        mode = self.data_source_mode.get()
        
        if mode == "live":
            if not messagebox.askyesno("Confirm", "This will process ALL nodes from live ComfyUI.\nProceed?"):
                return
            self.set_status("⏳ Compressing ALL (live)...", True)
            threading.Thread(
                target=lambda: self._compress_live_with_stats(""),
                daemon=True
            ).start()
        else:  # file mode
            if not self.node_file_path:
                return messagebox.showwarning("Error", "Load object_info.json first")
            if not messagebox.askyesno("Confirm", "This will process many nodes.\nProceed?"):
                return
            self.set_status("⏳ Compressing ALL...", True)
            # Get original file size for stats
            try:
                original_size = os.path.getsize(self.node_file_path)
            except:
                original_size = 0
            threading.Thread(
                target=lambda: self.finish(
                    compress_nodes_v4_logic(self.node_file_path, ""),
                    stats_info={'type': 'compression', 'original_size': original_size} if original_size > 0 else None
                ),
                daemon=True
            ).start()
    
    def start_extract_groups(self):
        """Extract groups from workflow - opens file selection panel."""
        from ui.modals.workflow_file_selection import WorkflowFileSelectionPanel
        
        def on_workflow_loaded(workflow_json, bridgezip):
            """Handle workflow loaded from file selection panel."""
            if not workflow_json:
                # User cancelled
                return
            
            def embed_panel(groups_data, error):
                if error:
                    self.finish(error)
                    return
                
                from ui.modals.group_selection import GroupSelectionPanel
                
                def generate_output(selected_groups):
                    """Generate output from selected groups."""
                    if isinstance(selected_groups, list):
                        # Selected groups from panel
                        self.set_status(f"⏳ Extracting {len(selected_groups)} group(s)...", True)
                        threading.Thread(
                            target=lambda: self.finish(extract_group_nodes_logic(workflow_json, selected_groups), stats_info={'type': 'groups'}),
                            daemon=True
                        ).start()
                    else:
                        # Empty string from cancel
                        self.finish("")
                
                panel = GroupSelectionPanel(
                    self.node_out, groups_data, generate_output
                )
                self.node_out.embed_widget(panel)
            
            self.set_status("⏳ Loading groups...", True)
            threading.Thread(
                target=lambda: self._collect_groups_and_embed(workflow_json, embed_panel),
                daemon=True
            ).start()
        
        # Embed file selection panel
        panel = WorkflowFileSelectionPanel(
            self.node_out, "json", self.shared_workflow, on_workflow_loaded
        )
        self.node_out.embed_widget(panel)
    
    def _collect_groups_and_embed(self, workflow_json, callback):
        """Collect groups from workflow and embed panel in main thread."""
        from logic.extraction import collect_groups_from_workflow
        groups_data, error = collect_groups_from_workflow(workflow_json)
        self.after(0, lambda: callback(groups_data, error))
    
    def extract_nodes(self):
        """Extract nodes from BridgeZip - opens file selection panel."""
        from ui.modals.workflow_file_selection import WorkflowFileSelectionPanel
        
        def on_workflow_loaded(workflow_json, bridgezip):
            """Handle BridgeZip loaded from file selection panel."""
            if not bridgezip:
                # User cancelled
                return
            
            # Display BridgeZip in output
            self.node_out.set_text(bridgezip)
            
            # Check if Smart Filter has input
            raw_input = self.filter_entry.get().strip()
            if not raw_input:
                self.set_status("✅ BridgeZip loaded (ready for node extraction)")
                # Show stats for full BridgeZip
                self.finish(bridgezip, stats_info={'type': 'nodes'})
                return
            
            # Extract nodes based on Smart Filter
            result = extract_nodes_from_bridgezip(bridgezip, raw_input)
            self.set_status("✅ Nodes Extracted")
            # Show stats
            self.finish(result, stats_info={'type': 'nodes'})
        
        # Embed file selection panel
        panel = WorkflowFileSelectionPanel(
            self.node_out, "bridgezip", self.shared_workflow, on_workflow_loaded
        )
        self.node_out.embed_widget(panel)
    
    def _extract_json_from_file(self, search_query, allowed_fields):
        """Extract JSON metadata from file."""
        import json
        import re
        
        try:
            with open(self.node_file_path, 'r', encoding='utf-8') as f:
                node_defs = json.load(f)
            
            # Parse search terms (empty = all nodes)
            search_query = search_query.strip() if search_query else ""
            search_terms = [t for t in re.split(r'[,+\s]+', search_query) if t] if search_query else []
            
            # Filter nodes
            if search_terms:
                found_nodes = {}
                for term in search_terms:
                    term_lower = term.lower()
                    for name, info in node_defs.items():
                        if not isinstance(info, dict):
                            continue
                        if (term_lower in name.lower() or 
                            term_lower in str(info.get("category", "")).lower()):
                            found_nodes[name] = info
                nodes_to_process = found_nodes
            else:
                nodes_to_process = {k: v for k, v in node_defs.items() if isinstance(v, dict)}
            
            if not nodes_to_process:
                return f"No nodes found matching: {', '.join(search_terms)}" if search_terms else "No nodes found in file."
            
            # Process each node
            results = []
            for name, node in nodes_to_process.items():
                # Synthesize widgets_values
                w_values = []
                if "input" in node:
                    req = node["input"].get("required", {}).items()
                    opt = node["input"].get("optional", {}).items()
                    for input_name, config in list(req) + list(opt):
                        if isinstance(config, list) and len(config) > 0:
                            raw_type = config[0]
                            opts = config[1] if len(config) > 1 and isinstance(config[1], dict) else {}
                            if isinstance(raw_type, list):
                                def_val = opts.get("default", raw_type[0] if raw_type else "")
                                w_values.append(def_val)
                            elif raw_type in ["INT", "FLOAT", "STRING", "BOOLEAN"]:
                                def_val = opts.get("default", 0 if raw_type == "INT" else 0.0 if raw_type == "FLOAT" else "" if raw_type == "STRING" else False)
                                w_values.append(def_val)
                
                node_copy = node.copy()
                node_copy["widgets_values"] = w_values
                if "class_name" not in node_copy:
                    node_copy["class_name"] = name
                
                # Filter fields
                if allowed_fields and len(allowed_fields) > 0:
                    filtered_node = {k: v for k, v in node_copy.items() if k in allowed_fields}
                    results.append(json.dumps(filtered_node, indent=2))
                else:
                    results.append(json.dumps(node_copy, indent=2))
            
            return "\n\n".join(results)
        except Exception as e:
            return f"Error extracting from file: {e}"

    def _extract_json_from_file_compiler(self, search_query, allowed_fields):
        """Extract JSON metadata from file in strict dict format for Compiler."""
        import json
        import re
        try:
            with open(self.node_file_path, 'r', encoding='utf-8') as f:
                node_defs = json.load(f)

            # Parse search terms (empty = all nodes)
            search_query = search_query.strip() if search_query else ""
            search_terms = [t for t in re.split(r'[,+\s]+', search_query) if t] if search_query else []

            # Filter nodes
            if search_terms:
                found_nodes = {}
                for term in search_terms:
                    term_lower = term.lower()
                    for name, info in node_defs.items():
                        if not isinstance(info, dict):
                            continue
                        if (
                            term_lower in name.lower()
                            or term_lower in str(info.get("category", "")).lower()
                        ):
                            found_nodes[name] = info
                nodes_to_process = found_nodes
            else:
                nodes_to_process = {
                    k: v for k, v in node_defs.items() if isinstance(v, dict)
                }

            if not nodes_to_process:
                return (
                    f"No nodes found matching: {', '.join(search_terms)}"
                    if search_terms
                    else "No nodes found in file."
                )

            result = {}
            for name, node in nodes_to_process.items():
                # Synthesize widgets_values (same as _extract_json_from_file)
                w_values = []
                if "input" in node:
                    req = node["input"].get("required", {}).items()
                    opt = node["input"].get("optional", {}).items()
                    for input_name, config in list(req) + list(opt):
                        if isinstance(config, list) and len(config) > 0:
                            raw_type = config[0]
                            opts = (
                                config[1]
                                if len(config) > 1 and isinstance(config[1], dict)
                                else {}
                            )
                            if isinstance(raw_type, list):
                                def_val = opts.get(
                                    "default", raw_type[0] if raw_type else ""
                                )
                                w_values.append(def_val)
                            elif raw_type in ["INT", "FLOAT", "STRING", "BOOLEAN"]:
                                def_val = opts.get(
                                    "default",
                                    0
                                    if raw_type == "INT"
                                    else 0.0
                                    if raw_type == "FLOAT"
                                    else ""
                                    if raw_type == "STRING"
                                    else False,
                                )
                                w_values.append(def_val)

                node_copy = node.copy()
                node_copy["widgets_values"] = w_values
                if "class_name" not in node_copy:
                    node_copy["class_name"] = name

                if allowed_fields and len(allowed_fields) > 0:
                    node_copy = {
                        k: v for k, v in node_copy.items() if k in allowed_fields
                    }

                result[name] = node_copy

            return json.dumps(result, indent=2)
        except Exception as e:
            return f"Error extracting from file (compiler mode): {e}"
    
    def _prevent_output_editing(self, event):
        """Block editing in definition output but allow navigation and copy."""
        # Allow Ctrl+C, Ctrl+A, Ctrl+V (for paste button), and navigation keys
        if (event.state & 4):  # Ctrl key
            if event.keysym.lower() in ['c', 'a', 'v']:
                return None
        # Allow navigation keys
        if event.keysym in ['Up', 'Down', 'Left', 'Right', 'Home', 'End', 'Page_Up', 'Page_Down']:
            return None
        # Block all other typing
        return "break"
    
    def get_node_data(self):
        """Get current node output data."""
        return self.node_out.get_text()


def fetch_live_node_meta_compiler(search_query, allowed_fields=None):
    """Fetch node metadata from live ComfyUI as a single dict for Compiler."""
    import json
    import re

    data = _get_live_object_info()
    if not data:
        base_url = get_comfyui_url()
        return f"Error connecting to ComfyUI ({base_url}). Ensure it is running."

    node_defs = data.get("node_definitions", data)

    search_query = search_query.strip() if search_query else ""
    search_terms = (
        [t for t in re.split(r"[,+\s]+", search_query) if t]
        if search_query
        else []
    )

    if not search_terms:
        unique_nodes = node_defs
    else:
        found_nodes = []
        for term in search_terms:
            term_lower = term.lower()
            term_matches = []
            if term in node_defs:
                term_matches.append((term, node_defs[term]))
            else:
                for k, v in node_defs.items():
                    if k.lower() == term_lower:
                        term_matches.append((k, v))
                        break
                if not term_matches:
                    for k, v in node_defs.items():
                        if term_lower in k.lower():
                            term_matches.append((k, v))
            found_nodes.extend(term_matches)

        if not found_nodes:
            return f"No nodes found matching: {', '.join(search_terms)}"

        unique_nodes = {}
        for name, info in found_nodes:
            unique_nodes[name] = info

    result = {}
    for name, raw_def in unique_nodes.items():
        if not isinstance(raw_def, dict):
            continue
        node = raw_def.copy()

        w_values = []
        if "input" in node:
            req = node["input"].get("required", {}).items()
            opt = node["input"].get("optional", {}).items()
            for input_name, config in list(req) + list(opt):
                if isinstance(config, list) and len(config) > 0:
                    raw_type = config[0]
                    opts = (
                        config[1]
                        if len(config) > 1 and isinstance(config[1], dict)
                        else {}
                    )
                    if isinstance(raw_type, list):
                        def_val = opts.get(
                            "default", raw_type[0] if raw_type else ""
                        )
                        w_values.append(def_val)
                    elif raw_type in ["INT", "FLOAT", "STRING", "BOOLEAN"]:
                        def_val = opts.get(
                            "default",
                            0
                            if raw_type == "INT"
                            else 0.0
                            if raw_type == "FLOAT"
                            else ""
                            if raw_type == "STRING"
                            else False,
                        )
                        w_values.append(def_val)

        node["widgets_values"] = w_values
        if "rect" not in node:
            node["rect"] = {"w": 300, "h": 100}
        if "ver" not in node:
            node["ver"] = "0.0.0 (Live)"
        if "cnr_id" not in node:
            node["cnr_id"] = "unknown_pack"
        if "properties" not in node:
            node["properties"] = {"Node name for S&R": name}
        if "class_name" not in node:
            node["class_name"] = name

        if allowed_fields and len(allowed_fields) > 0:
            node = {k: v for k, v in node.items() if k in allowed_fields}

        result[name] = node

    return json.dumps(result, indent=2)

