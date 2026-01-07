"""
Bridge Compiler — Python-only Task Envelope generator.

This tab bypasses ChatGPT for compilation and instead:
- Accepts a strict JSON Compiler Brief from Bridge Planner
- Accepts the CURRENT WORKFLOW BridgeZip string
- Accepts Node Definitions (live or file)
- Validates basic structure
- Generates a Task Envelope ready for Bridge Execute

NOTE:
- This module intentionally keeps all logic local to avoid touching the BridgeZip engine.
- It imports TYPE_SHORTHAND_MAP and escape_widget_value from engine.bridgezip but does
  NOT modify any engine functions.
"""

import json
import customtkinter as ctk
import tkinter as tk

from engine.bridgezip import (
    TYPE_SHORTHAND_MAP,
    escape_widget_value,
    inflate_workflow,
    encode_properties,
)
from utils.ui_helpers import COLORS, ModernButton, ModernModal, ToolTip, center_window


DOC_COMPILER_PY = """BRIDGE COMPILER — PYTHON-ONLY

PURPOSE

This tab compiles a strict JSON Compiler Brief into a Task Envelope using Python only.
It does not call ChatGPT or any external model.

INPUTS

- Compiler Brief JSON (produced by Bridge Planner)
- Current Workflow (BridgeZip string)
- Node Definitions (JSON, matching ComfyUI object_info format)

OUTPUT

A JSON object with:
- TASK_ENVELOPE: Contains plan summary
- CURRENT_WORKFLOW: The BridgeZip workflow string (unchanged)

BEHAVIOUR

- Fails fast on invalid JSON or missing fields
- Does not guess or invent node types
- Uses BridgeZip type shorthands strictly
- Does not execute or modify workflows
"""


class ContextSettingsModal(ctk.CTkToplevel):
    """Modal to configure which data is included in context."""
    def __init__(self, parent, options, callback):
        super().__init__(parent)
        self.title("Context Settings")
        self.geometry("500x350")
        self.configure(fg_color=COLORS['bg_main'])
        self.options = options
        self.callback = callback
        self.transient(parent)  # Anchor to main window
        
        # Center modal
        center_window(self, parent, 500, 350)
        self.grab_set()
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            header, text="Context Configuration", font=("Segoe UI", 16, "bold"),
            text_color="white"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            self, text="Select data to include when copying context:", font=("Segoe UI", 12),
            text_color=COLORS['fg_sub']
        ).pack(anchor="w", padx=20, pady=(0, 10))
        
        # Options
        self.vars = {}
        self.create_option("compiler_brief", "Compiler Brief JSON", "The Compiler Brief JSON from Bridge Planner.", disabled=False)
        self.create_option("workflow", "Current Workflow (BridgeZip)", "The current workflow in BridgeZip format.", disabled=False)
        self.create_option("node_defs", "Node Definitions", "The Node Definitions JSON.", disabled=False)
        
        # Footer
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", side="bottom", pady=20, padx=20)
        
        ModernButton(
            btn_row, text="Save", command=self.save,
            fg_color=COLORS['success'], width=100
        ).pack(side="right")
        
        ModernButton(
            btn_row, text="Cancel", command=self.destroy,
            fg_color=COLORS['btn_surface'], width=100
        ).pack(side="right", padx=10)

    def create_option(self, key, label, tooltip, disabled=False, default=None):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="x", padx=20, pady=5)

        var = tk.BooleanVar(value=self.options.get(key, True))
        self.vars[key] = var
        
        chk = ctk.CTkCheckBox(
            frame, text=label, variable=var,
            font=("Segoe UI", 12, "bold" if key == "compiler_brief" else "normal"),
            state="disabled" if disabled else "normal",
            fg_color=COLORS["accent_1"], hover_color=COLORS["accent_1"],
            border_color=COLORS["fg_sub"]
        )
        chk.pack(side="left")
        
        if tooltip:
            ToolTip(chk, tooltip)
            ctk.CTkLabel(
                frame, text=tooltip, font=("Segoe UI", 10),
                text_color=COLORS['fg_sub']
            ).pack(side="left", padx=10)

    def save(self):
        new_options = {}
        for k, v in self.vars.items():
            new_options[k] = v.get()
        
        self.callback(new_options)
        self.destroy()


class BridgeCompilerTab(ctk.CTkFrame):
    """Bridge Compiler Tab - Python-only compiler."""

    def __init__(self, parent, bridgezip_getter=None, node_data_getter=None):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=0)
        self.last_context_payload = ""
        
        # Default Context Options
        self.context_options = {
            "compiler_brief": True,
            "workflow": True,
            "node_defs": True
        }
        
        # Getter functions from main window
        self.bridgezip_getter = bridgezip_getter
        self.node_data_getter = node_data_getter
        
        self._build_ui()

    # ------------------------------------------------------------------
    # UI CONSTRUCTION
    # ------------------------------------------------------------------
    
    def _update_status(self, label_widget, message, is_success=True, clear_after=3000):
        """Update status label with message and auto-clear."""
        if is_success:
            label_widget.configure(text=message, text_color=COLORS["success"])
        else:
            label_widget.configure(text=message, text_color=COLORS["orange"])
        # Cancel any pending clear
        if hasattr(label_widget, '_clear_job'):
            self.after_cancel(label_widget._clear_job)
        # Schedule auto-clear
        label_widget._clear_job = self.after(clear_after, lambda: label_widget.configure(text=""))
    
    def _build_ui(self) -> None:
        """Build the Compiler tab UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.pack(fill="x", padx=10, pady=(10, 5))

        ctk.CTkLabel(
            header,
            text="Bridge Compiler",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["accent_1"],
        ).pack(side="left", padx=10)

        ModernButton(
            header,
            text="ℹ",
            command=lambda: ModernModal(self, "Bridge Compiler Help", DOC_COMPILER_PY),
            fg_color=COLORS["info"],
            text_color="black",
            width=30,
            height=28,
        ).pack(side="right", padx=10)

        # Top control row
        controls = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_main"],
            corner_radius=8,
            border_width=1,
            border_color="#30363d",
        )
        controls.pack(fill="x", padx=10, pady=(0, 10))

        controls_inner = ctk.CTkFrame(controls, fg_color="transparent")
        controls_inner.pack(fill="x", padx=10, pady=10)

        btn_row = ctk.CTkFrame(controls_inner, fg_color="transparent")
        btn_row.pack(side="left")

        # Settings button
        self.settings_btn = ModernButton(
            btn_row,
            text="⚙",
            command=self.show_settings_modal,
            fg_color=COLORS['btn_surface'],
            width=36,
            height=36,
        )
        self.settings_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.settings_btn, "Configure Context Data")

        # Copy Context button
        self.copy_context_btn = ModernButton(
            btn_row,
            text="Copy Context",
            command=self.copy_context_to_clipboard,
            fg_color=COLORS['accent_2'],
            width=120,
            height=36,
        )
        self.copy_context_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.copy_context_btn, "Copy all inputs to clipboard")

        # Inspect button
        self.inspect_btn = ModernButton(
            btn_row,
            text="Inspect",
            command=self.show_context_modal,
            fg_color=COLORS['btn_surface'],
            width=100,
            height=36,
        )
        self.inspect_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.inspect_btn, "View formatted input data")

        self.compile_btn = ModernButton(
            btn_row,
            text="Compile (Python)",
            command=self._on_compile_clicked,
            fg_color=COLORS["accent_1"],
            width=150,
            height=36,
        )
        self.compile_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.compile_btn, "Compile JSON brief into Task Envelope using Python")

        self.clear_btn = ModernButton(
            btn_row,
            text="Clear",
            command=self._on_clear_clicked,
            fg_color=COLORS["btn_surface"],
            width=80,
            height=36,
        )
        self.clear_btn.pack(side="left")
        ToolTip(self.clear_btn, "Clear all input and output areas")
        
        # Status label for compile errors (to the right of Clear button)
        self.compile_status_label = ctk.CTkLabel(
            btn_row,
            text="",
            font=("Segoe UI", 10),
            text_color=COLORS["orange"],
        )
        self.compile_status_label.pack(side="left", padx=(10, 0))
        
        # Status label for Copy Context feedback
        self.copy_status_label = ctk.CTkLabel(
            btn_row,
            text="",
            font=("Segoe UI", 10),
            text_color=COLORS["success"],
        )
        self.copy_status_label.pack(side="left", padx=(10, 0))

        # Main content split: left (inputs) / right (output)
        content = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_main"],
            corner_radius=8,
            border_width=1,
            border_color="#30363d",
        )
        content.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Equal column weights: left 50%, right 50%
        content.grid_columnconfigure(0, weight=1)  # Left column
        content.grid_columnconfigure(1, weight=1)  # Right column (50/50 split)
        content.grid_rowconfigure(0, weight=1)

        # LEFT: Inputs - all 3 split evenly
        left_frame = ctk.CTkFrame(content, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_columnconfigure(0, weight=1)
        # All 3 inputs get equal vertical space
        left_frame.grid_rowconfigure(1, weight=1)  # Compiler Brief
        left_frame.grid_rowconfigure(3, weight=1)  # Current Workflow
        left_frame.grid_rowconfigure(5, weight=1)  # Node Definitions

        # Compiler Brief JSON
        brief_label = ctk.CTkLabel(
            left_frame,
            text="Compiler Brief JSON",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["fg_sub"],
        )
        brief_label.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self.brief_text = ctk.CTkTextbox(
            left_frame,
            fg_color=COLORS["bg_panel"],
            text_color=COLORS["fg_text"],
            corner_radius=6,
            font=("Consolas", 12),
            wrap="none",
        )
        self.brief_text.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        # Current Workflow
        wf_label_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        wf_label_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        wf_label_frame.grid_columnconfigure(0, weight=1)
        if self.bridgezip_getter:
            wf_label_frame.grid_columnconfigure(1, weight=0)  # Status label
            wf_label_frame.grid_columnconfigure(2, weight=0)  # Button
        
        wf_label = ctk.CTkLabel(
            wf_label_frame,
            text="Current Workflow (BridgeZip)",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["fg_sub"],
        )
        wf_label.grid(row=0, column=0, sticky="w")
        
        if self.bridgezip_getter:
            # Status label for workflow load
            self.wf_status_label = ctk.CTkLabel(
                wf_label_frame,
                text="",
                font=("Segoe UI", 10),
                text_color=COLORS["success"],
            )
            self.wf_status_label.grid(row=0, column=1, sticky="e", padx=(10, 10))
            
            self.load_wf_btn = ModernButton(
                wf_label_frame,
                text="Load from Bridge Flow",
                command=self._load_workflow_from_bridge_flow,
                fg_color=COLORS["accent_2"],
                width=150,
                height=24,
            )
            self.load_wf_btn.grid(row=0, column=2, sticky="e", padx=(0, 0))
            ToolTip(self.load_wf_btn, "Auto-fill workflow from Bridge Flow tab")

        self.workflow_text = ctk.CTkTextbox(
            left_frame,
            fg_color=COLORS["bg_panel"],
            text_color=COLORS["fg_text"],
            corner_radius=6,
            font=("Consolas", 12),
            wrap="none",
        )
        self.workflow_text.grid(row=3, column=0, sticky="nsew", pady=(0, 8))

        # Node Definitions
        node_label_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        node_label_frame.grid(row=4, column=0, sticky="ew", pady=(0, 4))
        node_label_frame.grid_columnconfigure(0, weight=1)
        if self.node_data_getter:
            node_label_frame.grid_columnconfigure(1, weight=0)  # Status label
            node_label_frame.grid_columnconfigure(2, weight=0)  # Button
        
        node_label = ctk.CTkLabel(
            node_label_frame,
            text="Node Definitions (JSON or object_info fragment)",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["fg_sub"],
        )
        node_label.grid(row=0, column=0, sticky="w")
        
        if self.node_data_getter:
            # Status label for node definitions load
            self.node_defs_status_label = ctk.CTkLabel(
                node_label_frame,
                text="",
                font=("Segoe UI", 10),
                text_color=COLORS["success"],
            )
            self.node_defs_status_label.grid(row=0, column=1, sticky="e", padx=(10, 10))
            
            self.load_node_defs_btn = ModernButton(
                node_label_frame,
                text="Load from Bridge Context",
                command=self._load_node_defs_from_bridge_context,
                fg_color=COLORS["accent_2"],
                width=170,
                height=24,
            )
            self.load_node_defs_btn.grid(row=0, column=2, sticky="e", padx=(0, 0))
            ToolTip(self.load_node_defs_btn, "Auto-fill node definitions from Bridge Context tab")

        self.node_defs_text = ctk.CTkTextbox(
            left_frame,
            fg_color=COLORS["bg_panel"],
            text_color=COLORS["fg_text"],
            corner_radius=6,
            font=("Consolas", 12),
            wrap="none",
        )
        self.node_defs_text.grid(row=5, column=0, sticky="nsew")

        # RIGHT: Output
        right_frame = ctk.CTkFrame(content, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        out_header = ctk.CTkFrame(right_frame, fg_color="transparent")
        out_header.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            out_header,
            text="Task Envelope (Python Output)",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["fg_sub"],
        ).pack(side="left")

        # Status label for Copy Output feedback
        self.copy_output_status_label = ctk.CTkLabel(
            out_header,
            text="",
            font=("Segoe UI", 10),
            text_color=COLORS["success"],
        )
        self.copy_output_status_label.pack(side="right", padx=(10, 5))

        self.copy_output_btn = ModernButton(
            out_header,
            text="Copy",
            command=self._copy_output,
            fg_color=COLORS["accent_1"],
            width=70,
            height=28,
        )
        self.copy_output_btn.pack(side="right", padx=(5, 0))
        ToolTip(self.copy_output_btn, "Copy Task Envelope JSON to clipboard")

        self.output_text = ctk.CTkTextbox(
            right_frame,
            fg_color=COLORS["bg_panel"],
            text_color=COLORS["fg_text"],
            corner_radius=6,
            font=("Consolas", 12),
            wrap="none",
        )
        self.output_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

    # ------------------------------------------------------------------
    # UI CALLBACKS
    # ------------------------------------------------------------------
    def _on_clear_clicked(self) -> None:
        """Clear all input and output areas."""
        self.brief_text.delete("1.0", "end")
        self.workflow_text.delete("1.0", "end")
        self.node_defs_text.delete("1.0", "end")
        self.output_text.delete("1.0", "end")

    def _copy_output(self) -> None:
        """Copy the output JSON to clipboard."""
        text = self.output_text.get("1.0", "end").strip()
        if not text:
            self._update_status(self.copy_output_status_label, "Empty", False)
            return
        self.winfo_toplevel().clipboard_clear()
        self.winfo_toplevel().clipboard_append(text)
        self._update_status(self.copy_output_status_label, "✓ Copied", True)

    def get_task_envelope_json(self) -> str:
        """Get the current Task Envelope JSON from output."""
        try:
            content = self.output_text.get("1.0", tk.END).strip()
            return content
        except:
            return ""

    def show_settings_modal(self):
        """Show context settings modal."""
        ContextSettingsModal(self, self.context_options, self.update_context_options)

    def update_context_options(self, new_options):
        """Update context options from settings modal."""
        self.context_options = new_options
        self._update_status(self.copy_status_label, "✓ Settings updated", True, clear_after=3000)

    def copy_context_to_clipboard(self):
        """Copy formatted context (inputs) to clipboard."""
        context_parts = []
        stats = {"brief": False, "workflow": False, "node_defs": False, "size": 0}

        # 1. Compiler Brief
        if self.context_options.get("compiler_brief"):
            brief_raw = self.brief_text.get("1.0", "end").strip()
            if brief_raw:
                context_parts.append(f"=== COMPILER BRIEF JSON ===\n{brief_raw}")
                stats["brief"] = True
                try:
                    brief_json = json.loads(brief_raw)
                    stats["brief_nodes"] = len(brief_json.get("nodes_to_add", []))
                    stats["brief_deletes"] = len(brief_json.get("nodes_to_delete", []))
                except:
                    pass

        # 2. Current Workflow
        if self.context_options.get("workflow"):
            workflow_str = self.workflow_text.get("1.0", "end").strip()
            if workflow_str:
                context_parts.append(f"=== CURRENT WORKFLOW (BridgeZip) ===\n{workflow_str}")
                stats["workflow"] = True
                stats["workflow_lines"] = len([l for l in workflow_str.split('\n') if l.strip()])

        # 3. Node Definitions
        if self.context_options.get("node_defs"):
            node_defs_raw = self.node_defs_text.get("1.0", "end").strip()
            if node_defs_raw:
                context_parts.append(f"=== NODE DEFINITIONS ===\n{node_defs_raw}")
                stats["node_defs"] = True
                try:
                    node_defs_json = json.loads(node_defs_raw)
                    if isinstance(node_defs_json, dict) and "node_definitions" in node_defs_json:
                        stats["node_defs_count"] = len(node_defs_json.get("node_definitions", {}))
                    elif isinstance(node_defs_json, dict):
                        stats["node_defs_count"] = len(node_defs_json)
                except:
                    pass

        if not context_parts:
            self._update_status(self.copy_status_label, "No data selected", False)
            return

        final_context = "\n\n".join(context_parts)
        self.last_context_payload = final_context
        stats["size"] = len(final_context)

        # Copy to clipboard
        self.winfo_toplevel().clipboard_clear()
        self.winfo_toplevel().clipboard_append(final_context)
        self.update()

        # Build compact stats message
        stats_parts = []
        if stats.get("brief"):
            stats_parts.append(f"Brief: {stats.get('brief_nodes', 0)}+{stats.get('brief_deletes', 0)}")
        if stats.get("workflow"):
            stats_parts.append(f"WF: {stats.get('workflow_lines', 0)} lines")
        if stats.get("node_defs"):
            stats_parts.append(f"Nodes: {stats.get('node_defs_count', 0)} types")
        stats_parts.append(f"{stats['size']} chars")
        
        stats_message = f"✓ Copied: {', '.join(stats_parts)}"
        self._update_status(self.copy_status_label, stats_message, True, clear_after=5000)

    def show_context_modal(self):
        """Show formatted context in a modal."""
        context_parts = []

        # Build formatted view
        brief_raw = self.brief_text.get("1.0", "end").strip()
        workflow_str = self.workflow_text.get("1.0", "end").strip()
        node_defs_raw = self.node_defs_text.get("1.0", "end").strip()

        if brief_raw:
            context_parts.append("=== COMPILER BRIEF JSON ===")
            context_parts.append(brief_raw)
            context_parts.append("")

        if workflow_str:
            context_parts.append("=== CURRENT WORKFLOW (BridgeZip) ===")
            context_parts.append(workflow_str)
            context_parts.append("")

        if node_defs_raw:
            context_parts.append("=== NODE DEFINITIONS ===")
            context_parts.append(node_defs_raw)

        if not context_parts:
            formatted_context = "All input fields are empty."
        else:
            formatted_context = "\n".join(context_parts)
        
        ModernModal(self.winfo_toplevel(), "Input Data Inspection", formatted_context)

    def _load_workflow_from_bridge_flow(self):
        """Load workflow BridgeZip from Bridge Flow tab."""
        if not self.bridgezip_getter:
            if hasattr(self, 'wf_status_label'):
                self._update_status(self.wf_status_label, "Not available", False)
            return
        
        try:
            bridgezip = self.bridgezip_getter()
            if not bridgezip or not bridgezip.strip():
                self._update_status(self.wf_status_label, "Empty", False)
                return
            
            # Validate it's BridgeZip format
            if not bridgezip.strip().startswith("W:"):
                self._update_status(self.wf_status_label, "Invalid format", False)
                return
            
            # Clear and fill the textbox
            self.workflow_text.delete("1.0", "end")
            self.workflow_text.insert("1.0", bridgezip.strip())
            self._update_status(self.wf_status_label, "✓ Loaded", True)
        except Exception as e:
            self._update_status(self.wf_status_label, "Error", False)

    def _load_node_defs_from_bridge_context(self):
        """Load node definitions from Bridge Context tab (JSON only)."""
        if not self.node_data_getter:
            if hasattr(self, 'node_defs_status_label'):
                self._update_status(self.node_defs_status_label, "Not available", False)
            return
        
        try:
            node_data = self.node_data_getter()
            if not node_data or not node_data.strip():
                self._update_status(self.node_defs_status_label, "Empty", False)
                return
            
            # Validate it's JSON (not packs)
            try:
                parsed = json.loads(node_data.strip())
                if not isinstance(parsed, dict):
                    raise ValueError("Not a JSON object")
            except (json.JSONDecodeError, ValueError):
                # It's not valid JSON - likely packs or other text
                self._update_status(self.node_defs_status_label, "Need JSON format", False)
                
                # Show modal with instructions and copy button
                prompt_text = "I need to extract node definitions for Bridge Compiler. What are all the node types (class names) used in this workflow? Please provide them as a comma-separated list ONLY in a single code block."
                
                instructions = f"""Bridge Compiler requires JSON node definitions, not packs.

STEPS:
1. Go to Bridge Context tab
2. Set JSON mode to 'Compiler' (radio button)
3. In Smart Filter, enter node types separated by commas
   Example: CheckpointLoaderSimple, CLIPTextEncode, EmptyLatentImage

TO GET NODE LIST:
Ask Bridge Planner the following (click "Copy Prompt" to copy):"""
                
                # Create custom modal with copy button
                modal = ctk.CTkToplevel(self.winfo_toplevel())
                modal.title("JSON Format Required")
                modal.geometry("700x600")
                modal.configure(fg_color=COLORS['bg_main'])
                modal.resizable(False, False)
                center_window(modal, self.winfo_toplevel(), 700, 600)
                modal.grab_set()
                modal.focus_set()
                
                # Header
                header = ctk.CTkFrame(modal, fg_color="transparent", height=40)
                header.pack(fill="x", pady=15, padx=20)
                ctk.CTkLabel(header, text="JSON Format Required", font=("Segoe UI", 18, "bold"), text_color="white").pack(side="left")
                
                # Instructions text
                text_area = ctk.CTkTextbox(
                    modal, font=("Segoe UI", 13), fg_color=COLORS['bg_panel'],
                    text_color=COLORS['fg_text'], wrap="word", corner_radius=8, border_width=1, border_color="#30363d"
                )
                text_area.insert("1.0", instructions)
                text_area.configure(state="disabled")
                text_area.pack(fill="both", expand=True, padx=20, pady=(0, 10))
                
                # Prompt box (selectable)
                prompt_label = ctk.CTkLabel(
                    modal, text="Prompt:", font=("Segoe UI", 12, "bold"),
                    text_color=COLORS['fg_sub']
                )
                prompt_label.pack(anchor="w", padx=20, pady=(0, 5))
                
                prompt_box = ctk.CTkTextbox(
                    modal, font=("Segoe UI", 12), fg_color=COLORS['bg_panel'],
                    text_color=COLORS['fg_text'], wrap="word", corner_radius=6, 
                    border_width=1, border_color="#30363d", height=80
                )
                prompt_box.insert("1.0", prompt_text)
                prompt_box.configure(state="normal")  # Allow selection
                prompt_box.pack(fill="x", padx=20, pady=(0, 10))
                
                # Buttons
                btn_frame = ctk.CTkFrame(modal, fg_color="transparent")
                btn_frame.pack(fill="x", padx=20, pady=(0, 20))
                
                def copy_prompt():
                    modal.winfo_toplevel().clipboard_clear()
                    modal.winfo_toplevel().clipboard_append(prompt_text)
                    self._update_status(self.node_defs_status_label, "✓ Prompt copied", True, clear_after=2000)
                
                ModernButton(
                    btn_frame, text="Copy Prompt", command=copy_prompt,
                    fg_color=COLORS['accent_1'], width=120
                ).pack(side="left", padx=(0, 10))
                
                ModernButton(
                    btn_frame, text="CLOSE", command=modal.destroy,
                    fg_color=COLORS['btn_surface'], width=100
                ).pack(side="right")
                
                return
            
            # Clear and fill the textbox
            self.node_defs_text.delete("1.0", "end")
            self.node_defs_text.insert("1.0", node_data.strip())
            self._update_status(self.node_defs_status_label, "✓ Loaded", True)
        except Exception as e:
            self._update_status(self.node_defs_status_label, "Error", False)

    def _on_compile_clicked(self) -> None:
        """Handle Compile (Python) button press."""
        self.output_text.delete("1.0", "end")

        brief_raw = self.brief_text.get("1.0", "end").strip()
        workflow_str = self.workflow_text.get("1.0", "end").strip()
        node_defs_raw = self.node_defs_text.get("1.0", "end").strip()

        if not brief_raw:
            self._update_status(self.compile_status_label, "Brief required", False)
            return
        if not workflow_str:
            self._update_status(self.compile_status_label, "Workflow required", False)
            return
        if not node_defs_raw:
            self._update_status(self.compile_status_label, "Node defs required", False)
            return

        try:
            brief = json.loads(brief_raw)
        except Exception as e:
            self._update_status(self.compile_status_label, "Invalid brief JSON", False)
            return

        try:
            node_defs_data = json.loads(node_defs_raw)
        except Exception as e:
            self._update_status(self.compile_status_label, "Invalid node defs JSON", False)
            return

        # Support both full object_info and plain definitions dict
        if isinstance(node_defs_data, dict) and "node_definitions" in node_defs_data:
            node_defs = node_defs_data.get("node_definitions", {})
        else:
            node_defs = node_defs_data if isinstance(node_defs_data, dict) else {}

        if not isinstance(node_defs, dict) or not node_defs:
            self._update_status(self.compile_status_label, "Node defs must be object", False)
            return

        ok, err = validate_compiler_brief(brief, node_defs)
        if not ok:
            self._update_status(self.compile_status_label, f"Validation: {err[:30]}...", False)
            self.output_text.insert("1.0", f"ERROR: {err}")
            return

        try:
            add_nodes_str = generate_add_nodes_str(brief, node_defs, workflow_str)
        except Exception as e:
            self._update_status(self.compile_status_label, "Generation error", False)
            self.output_text.insert("1.0", f"ERROR generating add_nodes_str: {e}")
            return

        try:
            envelope = assemble_task_envelope(brief, workflow_str, add_nodes_str)
        except Exception as e:
            self._update_status(self.compile_status_label, "Assembly error", False)
            self.output_text.insert("1.0", f"ERROR assembling Task Envelope: {e}")
            return

        pretty = json.dumps(envelope, indent=2)
        self.output_text.insert("1.0", pretty)
        self._update_status(self.compile_status_label, "✓ Compiled", True)


# ----------------------------------------------------------------------
# PURE PYTHON HELPERS (NO UI)
# ----------------------------------------------------------------------

def validate_compiler_brief(brief: dict, node_defs: dict) -> tuple[bool, str]:
    """
    Minimal structural validation for the Compiler Brief JSON.

    This aims to be strict but not overly clever. It ensures:
    - Required top-level keys exist
    - Types are correct for critical fields
    - Node types referenced exist in node_defs
    """
    if not isinstance(brief, dict):
        return False, "Compiler Brief must be a JSON object."

    required_keys = ["plan_summary", "nodes_to_add", "nodes_to_delete", "groups_to_add"]
    for key in required_keys:
        if key not in brief:
            return False, f"Missing required field: '{key}'."

    if not isinstance(brief["plan_summary"], str):
        return False, "plan_summary must be a string."

    if not isinstance(brief["nodes_to_add"], list):
        return False, "nodes_to_add must be an array."
    if not isinstance(brief["nodes_to_delete"], list):
        return False, "nodes_to_delete must be an array."
    if not isinstance(brief["groups_to_add"], list):
        return False, "groups_to_add must be an array."

    for idx, nid in enumerate(brief["nodes_to_delete"]):
        if not isinstance(nid, int):
            return False, f"nodes_to_delete[{idx}] must be an integer node id."

    # Node checks
    for i, node in enumerate(brief["nodes_to_add"]):
        if not isinstance(node, dict):
            return False, f"nodes_to_add[{i}] must be an object."
        for field in ["placeholder_id", "type", "position", "widgets"]:
            if field not in node:
                return False, f"nodes_to_add[{i}] missing required field '{field}'."

        placeholder = node["placeholder_id"]
        if not isinstance(placeholder, str) or not placeholder.startswith("NODE_"):
            return False, f"nodes_to_add[{i}].placeholder_id must be like 'NODE_1'."

        ntype = node["type"]
        if not isinstance(ntype, str):
            return False, f"nodes_to_add[{i}].type must be a string."
        if ntype not in node_defs:
            return False, f"nodes_to_add[{i}].type '{ntype}' not found in Node Definitions."

        pos = node["position"]
        if (
            not isinstance(pos, list)
            or len(pos) != 2
            or not all(isinstance(v, int) for v in pos)
        ):
            return False, f"nodes_to_add[{i}].position must be [x, y] integers."

        widgets = node["widgets"]
        if not isinstance(widgets, list):
            return False, f"nodes_to_add[{i}].widgets must be an array."

        # Inputs / outputs optional but if present must be arrays
        for key in ("inputs", "outputs"):
            if key in node and not isinstance(node[key], list):
                return False, f"nodes_to_add[{i}].{key} must be an array if present."

    # Groups
    for i, g in enumerate(brief["groups_to_add"]):
        if not isinstance(g, dict):
            return False, f"groups_to_add[{i}] must be an object."
        if "title" not in g or "bounding" not in g:
            return False, f"groups_to_add[{i}] must have 'title' and 'bounding'."
        if not isinstance(g["title"], str):
            return False, f"groups_to_add[{i}].title must be a string."
        b = g["bounding"]
        if (
            not isinstance(b, list)
            or len(b) != 4
            or not all(isinstance(v, int) for v in b)
        ):
            return False, f"groups_to_add[{i}].bounding must be [x, y, w, h] integers."

    # Optional node updates
    nodes_to_update = brief.get("nodes_to_update", [])
    if nodes_to_update is not None and not isinstance(nodes_to_update, list):
        return False, "nodes_to_update must be an array if present."

    for i, upd in enumerate(nodes_to_update):
        if not isinstance(upd, dict):
            return False, f"nodes_to_update[{i}] must be an object."
        if "target" not in upd or "widgets" not in upd:
            return (
                False,
                f"nodes_to_update[{i}] must have 'target' and 'widgets' fields.",
            )
        target = upd["target"]
        if not isinstance(target, str) or not target.startswith("EXISTING_"):
            return (
                False,
                f"nodes_to_update[{i}].target must be like 'EXISTING_6'.",
            )
        if "type" in upd and upd["type"] is not None:
            if not isinstance(upd["type"], str):
                return (
                    False,
                    f"nodes_to_update[{i}].type must be a string if present.",
                )
            if upd["type"] not in node_defs:
                return (
                    False,
                    f"nodes_to_update[{i}].type '{upd['type']}' "
                    "not found in Node Definitions.",
                )
        if not isinstance(upd["widgets"], list):
            return False, f"nodes_to_update[{i}].widgets must be an array."

    return True, ""


def _get_node_io_schema(node_defs: dict, node_type: str) -> tuple[list, list]:
    """
    Extract ordered input and output schemas for a given node type from Node Definitions.

    Returns:
        (inputs_schema, outputs_schema)
    Where:
        inputs_schema: list of (name, type_str)
        outputs_schema: list of (name, type_str)
    """
    raw = node_defs.get(node_type, {})
    inputs_schema = []
    outputs_schema = []

    input_spec = raw.get("input", {})
    for section in ("required", "optional"):
        fields = input_spec.get(section, {})
        if isinstance(fields, dict):
            for name, spec in fields.items():
                if isinstance(spec, (list, tuple)) and spec:
                    raw_type = spec[0]
                    if isinstance(raw_type, list):
                        # Combo / list input — treat as LIST for BridgeZip
                        t = "LIST"
                    else:
                        t = str(raw_type)
                    inputs_schema.append((name, t))

    outputs = raw.get("output", [])
    if isinstance(outputs, list):
        for idx, out_type in enumerate(outputs):
            if isinstance(out_type, list):
                safe_type = str(out_type[0]) if out_type else "*"
            else:
                safe_type = str(out_type)
            outputs_schema.append((f"OUT_{idx}", safe_type))

    return inputs_schema, outputs_schema


def generate_add_nodes_str(brief: dict, node_defs: dict, workflow_str: str) -> str:
    """
    Generate the BridgeZip fragment (add_nodes_str) from the Compiler Brief.

    Supports:
    - nodes_to_add: new nodes with NODE_x / LINK_x placeholders
    - nodes_to_update: overwrite existing nodes' widgets (and preserve links)
    """
    # Inflate current workflow to resolve existing nodes for updates
    inflated = inflate_workflow(workflow_str)
    wf = json.loads(inflated) if isinstance(inflated, str) else inflated
    existing_nodes = {n.get("id"): n for n in wf.get("nodes", [])}

    lines: list[str] = []
    link_counter = 1
    link_map: dict[tuple[str, str], str] = {}  # (src, dst) -> LINK_id string

    def get_link_id(src: str, dst: str) -> str:
        nonlocal link_counter
        key = (src, dst)
        if key not in link_map:
            link_map[key] = f"LINK_{link_counter}"
            link_counter += 1
        return link_map[key]

    # ----------- NEW NODES -----------
    nodes_to_add = brief.get("nodes_to_add", [])
    for node in nodes_to_add:
        placeholder = node["placeholder_id"]  # e.g. NODE_1
        node_id_token = f"N{placeholder}"  # N + NODE_1
        node_type = node["type"]
        pos = node["position"]
        size = node.get("size", [300, 100])

        x, y = int(pos[0]), int(pos[1])
        w = int(size[0]) if isinstance(size, (list, tuple)) and size else 300
        h = int(size[1]) if isinstance(size, (list, tuple)) and len(size) > 1 else 100

        inputs_schema, outputs_schema = _get_node_io_schema(node_defs, node_type)

        # Build inputs string
        inputs_map = node.get("inputs", [])
        inputs_str_parts = []
        for idx, (name, type_str) in enumerate(inputs_schema):
            # Find matching connection in brief (by input_name)
            link_token = "None"
            for conn in inputs_map:
                if conn.get("input_name") == name:
                    src = conn.get("from", {})
                    src_node = src.get("node")
                    src_slot = src.get("slot", 0)
                    if isinstance(src_slot, int):
                        # Node label can be EXISTING_10 or NODE_1
                        src_label = _normalize_node_ref(src_node)
                        dst_label = _normalize_node_ref(placeholder)
                        link_token = get_link_id(
                            f"{src_label}.{src_slot}", f"{dst_label}.{idx}"
                        )
                    break

            shorthand = TYPE_SHORTHAND_MAP.get(type_str, TYPE_SHORTHAND_MAP.get("*"))
            inputs_str_parts.append(f"{name}:{shorthand}:{link_token}")

        inputs_str = ",".join(inputs_str_parts)

        # Build outputs string
        outputs_map = node.get("outputs", [])
        outputs_str_parts = []
        for idx, (name, type_str) in enumerate(outputs_schema):
            # Collect links for this output
            link_tokens = []
            for conn in outputs_map:
                if conn.get("output_name") == name:
                    for dst in conn.get("to", []):
                        dst_node = dst.get("node")
                        dst_slot = dst.get("slot", 0)
                        if isinstance(dst_slot, int):
                            src_label = _normalize_node_ref(placeholder)
                            dst_label = _normalize_node_ref(dst_node)
                            lid = get_link_id(
                                f"{src_label}.{idx}", f"{dst_label}.{dst_slot}"
                            )
                            link_tokens.append(lid)
            shorthand = TYPE_SHORTHAND_MAP.get(type_str, TYPE_SHORTHAND_MAP.get("*"))
            links_field = ",".join(link_tokens) if link_tokens else ""
            outputs_str_parts.append(f"{name}:{shorthand}:{links_field}")

        outputs_str = ";".join(outputs_str_parts)

        # Widgets
        widget_values = node.get("widgets", [])
        widgets_str = ";".join(escape_widget_value(w) for w in widget_values)

        rest = ""
        color = node.get("color")
        if color:
            rest += f"|C:{color},"

        line = (
            f"{node_id_token}:{node_type}|{x},{y},{w},{h}"
            f"|I:{inputs_str}|O:{outputs_str}|W:{widgets_str}{rest}"
        )
        lines.append(line)

    # ----------- UPDATE EXISTING NODES -----------
    for upd in brief.get("nodes_to_update", []):
        target_ref = upd.get("target")
        widgets = upd.get("widgets", [])
        if not isinstance(target_ref, str) or not target_ref.startswith("EXISTING_"):
            continue
        try:
            real_id = int(target_ref.split("_", 1)[1])
        except Exception:
            continue

        existing = existing_nodes.get(real_id)
        if not existing:
            continue

        node_type_final = (
            upd.get("type") or existing.get("type") or existing.get("class_type", "")
        )

        pos = existing.get("pos", [0, 0])
        size = existing.get("size", [300, 100])
        x, y = int(pos[0]), int(pos[1])
        if isinstance(size, dict):
            w, h = int(size.get("0", 300)), int(size.get("1", 100))
        else:
            w = int(size[0]) if len(size) > 0 else 300
            h = int(size[1]) if len(size) > 1 else 100

        # Preserve existing input/output wiring exactly
        inputs_parts: list[str] = []
        for inp in existing.get("inputs", []):
            name = inp.get("name", "")
            t = inp.get("type", "*")
            shorthand = TYPE_SHORTHAND_MAP.get(t, TYPE_SHORTHAND_MAP.get("*"))
            link_id = inp.get("link")
            link_token = str(link_id) if link_id is not None else "None"
            inputs_parts.append(f"{name}:{shorthand}:{link_token}")
        inputs_str = ",".join(inputs_parts)

        outputs_parts: list[str] = []
        for out in existing.get("outputs", []):
            name = out.get("name", "")
            t = out.get("type", "*")
            shorthand = TYPE_SHORTHAND_MAP.get(t, TYPE_SHORTHAND_MAP.get("*"))
            links_field = ",".join(str(x) for x in (out.get("links") or []) if x is not None)
            outputs_parts.append(f"{name}:{shorthand}:{links_field}")
        outputs_str = ";".join(outputs_parts)

        widgets_str = ";".join(escape_widget_value(wv) for wv in widgets)

        rest = ""
        color = existing.get("color")
        if color:
            rest += f"|C:{color},{existing.get('bgcolor','')}"
        props = existing.get("properties")
        if props:
            rest += f"|P:{encode_properties(props)}"

        line = (
            f"N{real_id}:{node_type_final}|{x},{y},{w},{h}"
            f"|I:{inputs_str}|O:{outputs_str}|W:{widgets_str}{rest}"
        )
        lines.append(line)

    # ----------- LINK LINES (LLINK_*) FOR NEW PLACEHOLDERS -----------
    for (src_label, dst_label), token in link_map.items():
        lines.append(f"LL{token}:{src_label}->{dst_label}:*")

    return "\n".join(lines)


def _normalize_node_ref(ref: str | None) -> str:
    """
    Normalise node references from brief into BridgeZip-friendly tokens.

    - \"EXISTING_10\" -> \"10\"
    - \"NODE_1\" -> \"NODE_1\" (placeholder left for executor)
    """
    if not isinstance(ref, str):
        return "Unknown"
    if ref.startswith("EXISTING_"):
        try:
            return str(int(ref.split("_", 1)[1]))
        except Exception:
            return ref
    return ref


def assemble_task_envelope(
    brief: dict, workflow_str: str, add_nodes_str: str
) -> dict:
    """
    Assemble the final Task Envelope JSON object.

    NOTE:
    - CURRENT WORKFLOW is not embedded here; the UI presents it separately.
    - This function focuses purely on the JSON envelope.
    """
    envelope = {
        "plan_summary": brief.get("plan_summary", ""),
        "delete_node_ids": brief.get("nodes_to_delete", []),
        "add_nodes_str": add_nodes_str,
        "add_groups": [],
    }

    for g in brief.get("groups_to_add", []):
        title = g.get("title", "Untitled")
        bounding = g.get("bounding", [0, 0, 300, 100])
        color = g.get("color", "#3f789e")
        envelope["add_groups"].append(
            {
                "title": title,
                "bounding": bounding,
                "color": color,
            }
        )

    # The workflow_str itself is not placed in JSON; caller handles echo.
    return {
        "TASK_ENVELOPE": envelope,
        "CURRENT_WORKFLOW": workflow_str,
    }



