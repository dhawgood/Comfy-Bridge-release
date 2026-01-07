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
import os
import sys
import subprocess
import threading
import json
from utils.ui_helpers import COLORS, ModernButton, ModernModal, center_window, ToolTip
from engine.bridgezip import compress_workflow
from logic.filtering import fetch_live_node_meta, fetch_live_categories

DOC_PLANNER = """BRIDGE PLANNER — CHATGPT CUSTOM GPT

PURPOSE

This tab provides the high-level reasoning layer for workflow design, diagnosis, and structural planning.

It is the conceptual and analytical engine in the hybrid system (1 external AI agent + 2 deterministic Python components).

ROLE IN HYBRID SYSTEM

Bridge Planner (ChatGPT - External AI Agent): Audits workflows, interprets intent, and designs the structural solution.

Bridge Compiler: Converts the Planner's design into a strict Task Envelope (Python-only).

Bridge Execute: Applies the envelope and returns the updated BridgeZip workflow (Python-only).

WHAT THE PLANNER DOES

- Analyses workflows (BridgeZip or JSON)
- Identifies structural issues, bottlenecks, or missing components
- Designs full topological solutions and modification strategies
- Produces the Compiler Brief, containing:
  - Structural instructions
  - Node classes to add or modify
  - Link logic
  - Creative configuration
  - Required node definitions
  - Layout guidance
- Ensures all referenced nodes actually exist in the user's library
- Outputs a Compiler Brief in JSON

HOW TO USE THIS TAB

1. Provide a Workflow

You may paste either:

- Standard ComfyUI JSON 
- BridgeZip (recommended for token efficiency)

Do not paste object_info.json — that file is too large and is handled separately via the extraction tools.

2. Request Analysis, Planning, Design, or Creative assistance 

Ask for broad or specific design tasks, for example:

- "Analyse this workflow and identify problems."
- "Plan how to extend this graph with additional processing."
- "Show the best way to restructure this section."
- "Design a clean approach for integrating a new feature."

The Planner will interpret the intent and produce a clear, structured plan.  

3. Receive the Compiler Brief

The Planner returns:

- Topological plan
- Node classes to add
- Link structure
- Widget/model guidance if needed
- Required node definitions
- Layout positioning strategy

This brief is designed specifically for Bridge Compiler.

4. Forward the Brief to Bridge Compiler

Paste the Planner's output into the Bridge Compiler tab.

The Compiler will validate everything and generate the executable Task Envelope.

TYPICAL WORKFLOW

1. Planner → Strategy, design, and analysis
2. Compiler → Conversion into Task Envelope
3. Execute → Apply modifications and output BridgeZip
4. ComfyUI → Test and iterate

REQUIREMENTS

- ChatGPT account (free or paid)
- Workflow input (JSON or BridgeZip)
- Node Definitions only when the Planner requests them

NOTE

This tab performs thinking, diagnosis, and design.

It does not compile or execute changes—those responsibilities belong to the Compiler and Execute tabs.

- - - - - 

A SUGGESTED STARTING PROMPT:

You are analysing a live ComfyUI workflow.

First, analyse the current workflow and explain what it is doing:

- what it generates

- how the main stages relate to each other

- where creative control and key decisions live

Then, propose a single constrained plan to change the visual outcome

while preserving the rest of the workflow.

Structure the response using the following sections:

WORKFLOW ANALYSIS
=================

Current behavior
- Summarise how the workflow currently behaves.

Key constraints
- Identify what must remain unchanged.

PROPOSED CONSTRAINED CHANGE
===========================

Goal
- State the intended visual change.

Single bounded area
- Identify the specific area of the workflow affected.

Why this is safe
- Explain why the change preserves stability and structure.

Be analytical and deliberate.

Do not output executable or node-level instructions.

Return the full response inside a single code block."""

class ContextSettingsModal(ctk.CTkToplevel):
    """Modal to configure which data is included in context."""
    def __init__(self, parent, options, callback):
        super().__init__(parent)
        self.title("Context Settings")
        self.geometry("500x400")
        self.configure(fg_color=COLORS['bg_main'])
        self.options = options
        self.callback = callback
        self.transient(parent)  # Anchor to main window
        
        # Center modal
        center_window(self, parent, 500, 400)
        self.grab_set()
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            header, text="Context Configuration", font=("Segoe UI", 16, "bold"),
            text_color="white"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            self, text="Select data to include in context:", font=("Segoe UI", 12),
            text_color=COLORS['fg_sub']
        ).pack(anchor="w", padx=20, pady=(0, 10))
        
        # Options
        self.vars = {}
        self.create_option("bridgezip", "Workflow (BridgeZip)", "Recommended. The actual workflow structure.", disabled=False)
        self.create_option("node_defs", "Active Node Definitions", "Highly Recommended. Prevents syntax errors for custom nodes.")
        self.create_option("packs", "Installed Packs List", "Optional. Helps ChatGPT know what libraries are available.")
        self.create_option("models", "Full Model Library", "Optional (Heavy). List all checkpoints/LoRAs.")
        
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

        var = tk.BooleanVar(value=self.options.get(key, False))
        self.vars[key] = var
        
        chk = ctk.CTkCheckBox(
            frame, text=label, variable=var,
            font=("Segoe UI", 12, "bold" if key == "bridgezip" else "normal"),
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

class PlannerTab(ctk.CTkFrame):
    """Bridge Planner Tab - Embedded ChatGPT Custom GPT."""
    
    def __init__(self, parent, workflow_getter=None, node_data_getter=None):
        super().__init__(parent, fg_color=COLORS['bg_panel'], corner_radius=0)
        self.workflow_getter = workflow_getter
        self.node_data_getter = node_data_getter
        self.last_context_payload = ""
        
        # Default Context Options
        self.context_options = {
            "bridgezip": True,
            "node_defs": True,
            "packs": False,
            "models": False
        }
        
        self.webview_hwnd = None
        self.browser_process = None
        self.setup_ui()
        self.initialize_context()
    
    def setup_ui(self):
        """Build the planner tab UI."""
        # Header with help button
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.pack(fill="x", padx=10, pady=(10, 5))
        
        ctk.CTkLabel(
            header, text="Bridge Planner", font=("Segoe UI", 18, "bold"),
            text_color=COLORS['accent_1']
        ).pack(side="left", padx=10)
        
        ModernButton(
            header, text="ℹ", command=lambda: ModernModal(self, "Bridge Planner Help", DOC_PLANNER),
            fg_color=COLORS['info'], text_color="black", width=30, height=28
        ).pack(side="right", padx=10)
        
        # Button container (matching Bridge Execute layout)
        context_container = ctk.CTkFrame(self, fg_color=COLORS['bg_main'], corner_radius=8, border_width=1, border_color="#30363d")
        context_container.pack(fill="x", padx=10, pady=(0, 10))
        
        context_frame = ctk.CTkFrame(context_container, fg_color="transparent")
        context_frame.pack(fill="x", padx=10, pady=10)
        
        btn_row = ctk.CTkFrame(context_frame, fg_color="transparent")
        btn_row.pack(side="left")
        
        # Settings button
        self.settings_btn = ModernButton(
            btn_row, text="⚙", command=self.show_settings_modal,
            fg_color=COLORS['btn_surface'], width=36, height=36
        )
        self.settings_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.settings_btn, "Configure Context Data")

        # Copy Context button
        self.copy_context_btn = ModernButton(
            btn_row, text="Copy Context", command=self.copy_context_to_clipboard,
            fg_color=COLORS['accent_2'], width=120, height=36
        )
        self.copy_context_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.copy_context_btn, "Copy context to clipboard (paste into ChatGPT)")
        
        # Inspect button
        self.inspect_btn = ModernButton(
            btn_row, text="Inspect", command=self.show_context_modal,
            fg_color=COLORS['btn_surface'], width=100, height=36
        )
        self.inspect_btn.pack(side="left", padx=(0, 5))
        ToolTip(self.inspect_btn, "View raw context payload")
        
        self.webview_frame = ctk.CTkFrame(self, fg_color=COLORS['bg_main'], corner_radius=8, border_width=1, border_color="#30363d")
        self.webview_frame.pack(fill="both", expand=True, padx=10)
        self.webview_frame.bind("<Configure>", self.on_planner_resize)
        
        # Clean up any existing browser script
        try:
            if os.path.exists("bridge_browser_internal_planner.py"):
                os.remove("bridge_browser_internal_planner.py")
        except:
            pass
        
        # Launch webview after a short delay
        self.after(500, self.launch_webview)
    
    def launch_webview(self):
        """Launch the webview process."""
        script_content = """
import webview
import sys
import threading
import time

def inject_text_selection(window):
    \"\"\"Inject JavaScript to enable text selection and add copy function.\"\"\"
    time.sleep(1.5)  # Wait for page to load
    
    enable_selection_js = '''
    (function() {
        const style = document.createElement('style');
        style.textContent = `
            * {
                -webkit-user-select: text !important;
                -moz-user-select: text !important;
                -ms-user-select: text !important;
                user-select: text !important;
            }
        `;
        document.head.appendChild(style);
        
        console.log('Text selection enabled');
    })();
    '''
    
    try:
        window.evaluate_js(enable_selection_js)
    except Exception:
        pass  # Silently fail - text selection is optional

def on_closed(): 
    sys.exit(0)

if __name__ == "__main__":
    wv = webview.create_window("Bridge Planner", "https://chatgpt.com/g/g-69403492523c8191a3ef8444acb66351-comfy-bridger-planner", width=800, height=600, resizable=True)
    wv.events.closed += on_closed
    
    # Inject text selection after window loads
    threading.Thread(target=lambda: inject_text_selection(wv), daemon=True).start()
    
    webview.start()
"""
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bridge_browser_internal_planner.py")
        script_path = os.path.abspath(script_path)
        
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
        except Exception as e:
            ctk.CTkLabel(
                self.webview_frame,
                text=f"Error creating browser script:\n{e}",
                text_color="red"
            ).pack(expand=True)
            return

        try:
            startupinfo = None
            if sys.platform == 'win32':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            self.browser_process = subprocess.Popen(
                [sys.executable, script_path],
                startupinfo=startupinfo
            )
            self.after(1000, self.embed_window)
        except Exception as e:
            ctk.CTkLabel(
                self.webview_frame,
                text=f"Error launching process:\n{e}",
                text_color="red"
            ).pack(expand=True)
    
    def embed_window(self):
        """Embed the webview window into the frame."""
        if sys.platform == "win32":
            try:
                from ctypes import windll
                target_title = "Bridge Planner"
                hwnd = windll.user32.FindWindowW(None, target_title)
                if hwnd:
                    self.webview_hwnd = hwnd
                    parent_hwnd = self.webview_frame.winfo_id()
                    windll.user32.SetParent(hwnd, parent_hwnd)
                    style = windll.user32.GetWindowLongW(hwnd, -16)
                    style = style & ~0x00C00000
                    style = style & ~0x00040000
                    windll.user32.SetWindowLongW(hwnd, -16, style | 0x80000000)
                    self.force_resize_webview()
                else:
                    self.after(500, self.embed_window)
            except Exception:
                pass  # Silently handle embedding failures
    
    def on_planner_resize(self, event):
        """Handle resize events."""
        if hasattr(self, 'webview_hwnd') and self.webview_hwnd:
            self.force_resize_webview(event.width, event.height)
    
    def force_resize_webview(self, w=None, h=None):
        """Force resize the embedded webview."""
        if sys.platform == "win32":
            from ctypes import windll
            if w is None:
                w = self.webview_frame.winfo_width()
            if h is None:
                h = self.webview_frame.winfo_height()
            if self.webview_hwnd:
                windll.user32.SetWindowPos(self.webview_hwnd, 0, 0, 0, w, h, 0x0004 | 0x0040)
    
    def initialize_context(self):
        """Initialize the tab."""
        pass

    def show_settings_modal(self):
        ContextSettingsModal(self, self.context_options, self.update_context_options)

    def update_context_options(self, new_options):
        self.context_options = new_options
        messagebox.showinfo("Settings Updated", "Context settings updated. Use 'Copy Context' to apply.")

    def copy_context_to_clipboard(self):
        """Copy context to clipboard instead of sending to API."""
        if not self.workflow_getter:
            messagebox.showwarning("No Workflow", "Workflow getter not linked.")
            return

        self.copy_context_btn.configure(state="disabled", text="...")
        threading.Thread(target=self._copy_context_async, daemon=True).start()

    def _copy_context_async(self):
        """Build context and copy to clipboard."""
        try:
            workflow_json = self.workflow_getter()
            if not workflow_json or not workflow_json.strip():
                self.after(0, lambda: self._finish_context_copy(False, "No workflow found in 'Bridge Flow' tab."))
                return

            context_parts = []
            stats = {"nodes": 0, "defs": "Disabled", "packs": "Disabled", "size": 0}

            # 1. BRIDGEZIP (Required)
            try:
                bridgezip = compress_workflow(workflow_json)
                if bridgezip.startswith("Error"):
                    context_parts.append(f"=== CURRENT WORKFLOW (JSON) ===\n{workflow_json}")
                else:
                    context_parts.append(f"=== CURRENT WORKFLOW (BridgeZip) ===\n{bridgezip}")
                    stats["nodes"] = len([l for l in bridgezip.split('\n') if l.startswith('N')])
            except:
                context_parts.append(f"=== CURRENT WORKFLOW (JSON) ===\n{workflow_json}")

            # 2. NODE DEFS (Optional)
            if self.context_options.get("node_defs"):
                try:
                    wf_data = json.loads(workflow_json)
                    used_node_types = {n.get("type", "Unknown") for n in wf_data.get("nodes", [])}
                    node_list_str = ",".join(list(used_node_types))
                    
                    if node_list_str:
                        live_defs = fetch_live_node_meta(node_list_str)
                        if not live_defs.startswith("Error"):
                            context_parts.append(f"=== ACTIVE NODE DEFINITIONS ===\n{live_defs}")
                            stats["defs"] = len(live_defs.split('\n\n'))
                        elif self.node_data_getter:
                             manual = self.node_data_getter()
                             if manual: context_parts.append(f"=== NODE DEFINITIONS (Manual) ===\n{manual}")
                except: pass
            else:
                stats["defs"] = "Disabled"

            # 3. PACKS (Optional)
            if self.context_options.get("packs"):
                try:
                    packs_str = fetch_live_categories()
                    if not packs_str.startswith("Error"):
                        context_parts.append(packs_str)
                        stats["packs"] = len(packs_str.split('\n')) - 2
                except: pass
            else:
                stats["packs"] = "Disabled"

            # 4. MODELS (Optional - Not impl yet, placeholder)
            if self.context_options.get("models"):
                # Could implement extract_models_logic live here
                pass

            final_context = "\n\n".join(context_parts)
            self.last_context_payload = final_context
            stats["size"] = len(final_context)
            
            # Copy to clipboard
            self.winfo_toplevel().clipboard_clear()
            self.winfo_toplevel().clipboard_append(final_context)
            self.winfo_toplevel().update()
            
            summary = (
                f"Context copied to clipboard!\n"
                f"- Workflow Nodes: {stats['nodes']}\n"
                f"- Live Defs: {stats['defs']}\n"
                f"- Packs: {stats['packs']}\n"
                f"- Size: {stats['size']} chars\n"
                f"\nPaste into ChatGPT above."
            )
            
            self.after(0, lambda: self._finish_context_copy(True, summary))

        except Exception as e:
            self.after(0, lambda: self._finish_context_copy(False, f"Error: {e}"))

    def _finish_context_copy(self, success, msg):
        self.copy_context_btn.configure(state="normal", text="Copy Context")
        if success:
            messagebox.showinfo("Context Copied", msg)
        else:
            messagebox.showerror("Error", msg)

    def show_context_modal(self):
        if not self.last_context_payload:
            messagebox.showinfo("Empty", "No context copied yet. Use 'Copy Context' first.")
            return
        ModernModal(self, "Current Context Payload", self.last_context_payload)

