"""
Bridge Execute — Python-only Task Envelope executor.

This tab executes Task Envelopes using Python only, replacing ChatGPT dependency.
It applies modifications to BridgeZip workflows deterministically.

NOTE:
- This module uses apply_modifications from engine.bridgezip
- It does NOT modify any engine functions
"""

import json
import customtkinter as ctk
import tkinter as tk

from engine.bridgezip import apply_modifications
from utils.ui_helpers import COLORS, ModernButton, ModernModal, ToolTip, center_window


DOC_EXECUTE_PY = """BRIDGE EXECUTE — PYTHON-ONLY

PURPOSE

This tab executes Task Envelopes using Python only.
It does not call ChatGPT or any external model.

INPUTS

- Task Envelope JSON (produced by Bridge Compiler)
- Current Workflow (BridgeZip string)

OUTPUT

- Updated BridgeZip workflow:
  - Nodes added/deleted as specified
  - Connections repaired
  - Groups merged into metadata
  - IDs resolved and updated

BEHAVIOUR

- Fails fast on invalid JSON or BridgeZip format
- Applies modifications deterministically
- Repairs all connections automatically
- Resolves NODE_X/LINK_X placeholders to real IDs
- Operates in silent mode: no explanations, just results
"""


class BridgeExecuteTab(ctk.CTkFrame):
    """Bridge Execute Tab - Python-only executor."""

    def __init__(self, parent, task_envelope_getter=None, workflow_getter=None):
        super().__init__(parent, fg_color=COLORS["bg_panel"], corner_radius=0)
        
        # Getter functions from main window
        self.task_envelope_getter = task_envelope_getter
        self.workflow_getter = workflow_getter
        
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
        """Build the Execute tab UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            header,
            text="Bridge Execute",
            font=("Segoe UI", 18, "bold"),
            text_color=COLORS["accent_1"],
        ).pack(side="left", padx=10)
        
        ModernButton(
            header,
            text="ℹ",
            command=lambda: ModernModal(self, "Bridge Execute Help", DOC_EXECUTE_PY),
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
        
        # Execute button
        self.execute_btn = ModernButton(
            btn_row,
            text="Execute (Python)",
            command=self._on_execute_clicked,
            fg_color=COLORS["accent_1"],
            width=150,
            height=36,
        )
        self.execute_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.execute_btn, "Execute Task Envelope using Python")

        # Copy Output button
        self.copy_output_btn = ModernButton(
            btn_row,
            text="Copy Output",
            command=self._copy_output,
            fg_color=COLORS["accent_2"],
            width=120,
            height=36,
        )
        self.copy_output_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.copy_output_btn, "Copy resulting BridgeZip to clipboard")

        # Inspect button
        self.inspect_btn = ModernButton(
            btn_row,
            text="Inspect",
            command=self._show_output_modal,
            fg_color=COLORS["btn_surface"],
            width=100,
            height=36,
        )
        self.inspect_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.inspect_btn, "View output in modal")

        # Clear button
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
        
        # Status label for execute feedback (to the right of Clear button)
        self.execute_status_label = ctk.CTkLabel(
            btn_row,
            text="",
            font=("Segoe UI", 10),
            text_color=COLORS["orange"],
        )
        self.execute_status_label.pack(side="left", padx=(10, 0))

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

        # LEFT: Inputs - split evenly vertically
        left_frame = ctk.CTkFrame(content, fg_color="transparent")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_frame.grid_columnconfigure(0, weight=1)
        # Both inputs get equal vertical space
        left_frame.grid_rowconfigure(1, weight=1)  # Task Envelope
        left_frame.grid_rowconfigure(3, weight=1)  # Current Workflow

        # Task Envelope JSON
        envelope_label_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        envelope_label_frame.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        envelope_label_frame.grid_columnconfigure(0, weight=1)
        if self.task_envelope_getter:
            envelope_label_frame.grid_columnconfigure(1, weight=0)  # Status label
            envelope_label_frame.grid_columnconfigure(2, weight=0)  # Button
        
        envelope_label = ctk.CTkLabel(
            envelope_label_frame,
            text="Task Envelope JSON",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["fg_sub"],
        )
        envelope_label.grid(row=0, column=0, sticky="w")
        
        if self.task_envelope_getter:
            # Status label for envelope load
            self.envelope_status_label = ctk.CTkLabel(
                envelope_label_frame,
                text="",
                font=("Segoe UI", 10),
                text_color=COLORS["success"],
            )
            self.envelope_status_label.grid(row=0, column=1, sticky="e", padx=(10, 10))
            
            self.load_envelope_btn = ModernButton(
                envelope_label_frame,
                text="Load from Bridge Compiler",
                command=self._load_envelope_from_compiler,
                fg_color=COLORS["accent_2"],
                width=170,
                height=24,
            )
            self.load_envelope_btn.grid(row=0, column=2, sticky="e", padx=(0, 0))
            ToolTip(self.load_envelope_btn, "Auto-fill Task Envelope from Bridge Compiler tab")

        self.envelope_text = ctk.CTkTextbox(
            left_frame,
            fg_color=COLORS["bg_panel"],
            text_color=COLORS["fg_text"],
            corner_radius=6,
            font=("Consolas", 12),
            wrap="none",
        )
        self.envelope_text.grid(row=1, column=0, sticky="nsew", pady=(0, 8))

        # Current Workflow
        wf_label_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        wf_label_frame.grid(row=2, column=0, sticky="ew", pady=(0, 4))
        wf_label_frame.grid_columnconfigure(0, weight=1)
        if self.workflow_getter:
            wf_label_frame.grid_columnconfigure(1, weight=0)  # Status label
            wf_label_frame.grid_columnconfigure(2, weight=0)  # Button
        
        wf_label = ctk.CTkLabel(
            wf_label_frame,
            text="Current Workflow (BridgeZip)",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["fg_sub"],
        )
        wf_label.grid(row=0, column=0, sticky="w")
        
        if self.workflow_getter:
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
        self.workflow_text.grid(row=3, column=0, sticky="nsew")

        # RIGHT: Output
        right_frame = ctk.CTkFrame(content, fg_color="transparent")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)

        out_header = ctk.CTkFrame(right_frame, fg_color="transparent")
        out_header.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            out_header,
            text="Resulting BridgeZip",
            font=("Segoe UI", 12, "bold"),
            text_color=COLORS["fg_sub"],
        ).pack(side="left")

        self.output_text = ctk.CTkTextbox(
            right_frame,
            fg_color=COLORS["bg_panel"],
            text_color=COLORS["fg_text"],
            corner_radius=6,
            font=("Consolas", 12),
            wrap="none",
            state="disabled",
        )
        self.output_text.grid(row=1, column=0, sticky="nsew", pady=(4, 0))

    # ------------------------------------------------------------------
    # UI CALLBACKS
    # ------------------------------------------------------------------
    def _on_clear_clicked(self) -> None:
        """Clear all input and output areas."""
        self.envelope_text.delete("1.0", "end")
        self.workflow_text.delete("1.0", "end")
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.configure(state="disabled")

    def _copy_output(self) -> None:
        """Copy the output BridgeZip to clipboard."""
        text = self.output_text.get("1.0", "end").strip()
        if not text:
            if hasattr(self, 'execute_status_label'):
                self._update_status(self.execute_status_label, "Empty", False)
            return
        self.winfo_toplevel().clipboard_clear()
        self.winfo_toplevel().clipboard_append(text)
        if hasattr(self, 'execute_status_label'):
            self._update_status(self.execute_status_label, "✓ Copied", True)

    def _show_output_modal(self) -> None:
        """Show output in modal for inspection."""
        text = self.output_text.get("1.0", "end").strip()
        if not text:
            text = "No output to inspect."
        ModernModal(self.winfo_toplevel(), "Execute Output", text)

    def _load_envelope_from_compiler(self) -> None:
        """Load Task Envelope from Bridge Compiler tab."""
        if not self.task_envelope_getter:
            if hasattr(self, 'envelope_status_label'):
                self._update_status(self.envelope_status_label, "Not available", False)
            return
        envelope = self.task_envelope_getter()
        if envelope:
            self.envelope_text.delete("1.0", "end")
            self.envelope_text.insert("1.0", envelope)
            if hasattr(self, 'envelope_status_label'):
                self._update_status(self.envelope_status_label, "✓ Loaded", True)
        else:
            if hasattr(self, 'envelope_status_label'):
                self._update_status(self.envelope_status_label, "Empty", False)

    def _load_workflow_from_bridge_flow(self) -> None:
        """Load workflow from Bridge Flow tab."""
        if not self.workflow_getter:
            if hasattr(self, 'wf_status_label'):
                self._update_status(self.wf_status_label, "Not available", False)
            return
        workflow = self.workflow_getter()
        if workflow:
            self.workflow_text.delete("1.0", "end")
            self.workflow_text.insert("1.0", workflow)
            if hasattr(self, 'wf_status_label'):
                self._update_status(self.wf_status_label, "✓ Loaded", True)
        else:
            if hasattr(self, 'wf_status_label'):
                self._update_status(self.wf_status_label, "Empty", False)

    # ------------------------------------------------------------------
    # EXECUTION LOGIC
    # ------------------------------------------------------------------
    def _on_execute_clicked(self) -> None:
        """Execute Task Envelope."""
        envelope_raw = self.envelope_text.get("1.0", "end").strip()
        workflow_str = self.workflow_text.get("1.0", "end").strip()

        if not envelope_raw:
            self._update_status(self.execute_status_label, "Envelope required", False)
            return
        if not workflow_str:
            self._update_status(self.execute_status_label, "Workflow required", False)
            return

        # Parse Task Envelope JSON
        try:
            # Handle case where envelope might include "TASK_ENVELOPE" wrapper
            envelope_data = json.loads(envelope_raw)
            if "TASK_ENVELOPE" in envelope_data:
                envelope = envelope_data["TASK_ENVELOPE"]
            else:
                envelope = envelope_data
        except Exception as e:
            self._update_status(self.execute_status_label, "Invalid envelope JSON", False)
            return

        # Extract fields
        delete_node_ids = envelope.get("delete_node_ids", [])
        add_nodes_str = envelope.get("add_nodes_str", "")
        add_groups = envelope.get("add_groups", [])

        # Validate delete_node_ids is a list of integers
        if not isinstance(delete_node_ids, list):
            self._update_status(self.execute_status_label, "delete_node_ids must be array", False)
            return
        delete_node_ids = [int(x) for x in delete_node_ids if isinstance(x, (int, str)) and str(x).isdigit()]

        # Execute modifications
        try:
            result = apply_modifications(workflow_str, add_nodes_str, delete_node_ids)
            
            if isinstance(result, str) and result.startswith("Error"):
                self._update_status(self.execute_status_label, "Execution error", False)
                return

            # Handle groups: merge into workflow metadata
            if add_groups:
                # Inflate result to add groups, then recompress
                from engine.bridgezip import inflate_workflow, compress_workflow
                inflated = inflate_workflow(result)
                if isinstance(inflated, str) and not inflated.startswith("Error"):
                    try:
                        wf = json.loads(inflated)
                        existing_groups = wf.get("groups", [])
                        # Merge new groups (avoid duplicates by title)
                        existing_titles = {g.get("title") for g in existing_groups}
                        for new_group in add_groups:
                            if new_group.get("title") not in existing_titles:
                                existing_groups.append(new_group)
                        wf["groups"] = existing_groups
                        result = compress_workflow(wf)
                    except Exception:
                        pass  # If group merge fails, use result as-is

            # Display result
            self.output_text.configure(state="normal")
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", result)
            self.output_text.configure(state="disabled")
            
            self._update_status(self.execute_status_label, "✓ Executed", True)

        except Exception as e:
            self._update_status(self.execute_status_label, "Execution error", False)

