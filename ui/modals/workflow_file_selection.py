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
from utils.ui_helpers import COLORS, ModernButton
import json
import os

class WorkflowFileSelectionPanel(ctk.CTkFrame):
    """Embedded panel for selecting workflow JSON or BridgeZip files."""
    
    def __init__(self, parent, mode, shared_data, callback):
        """
        Args:
            parent: Parent widget
            mode: "json" for EXTRACT GROUPS, "bridgezip" for EXTRACT NODES
            shared_data: Dict with keys: json, bridgezip, filename (from NodeDevTab)
            callback: Function to call with (workflow_json, bridgezip_string) when ready
        """
        super().__init__(parent, fg_color=COLORS['bg_main'], corner_radius=0)
        self.mode = mode  # "json" or "bridgezip"
        self.shared_data = shared_data  # Reference to shared storage dict
        self.callback = callback
        self.selected_file = None
        self.input_mode = tk.StringVar(value="file")  # "file" or "paste"
        
        self.setup_ui()
        self.check_existing_data()
    
    def setup_ui(self):
        """Build the panel UI."""
        # Header with title and primary action buttons
        header = ctk.CTkFrame(self, fg_color="transparent", height=60)
        header.pack(fill="x", pady=(15, 10), padx=20)
        
        # Left side: Title
        title_text = "Select Workflow JSON File" if self.mode == "json" else "Select BridgeZip File"
        ctk.CTkLabel(
            header, text=title_text, 
            font=("Segoe UI", 18, "bold"), text_color=COLORS['fg_text']
        ).pack(side="left")
        
        # Right side: Primary action buttons (prominent and always visible)
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        self.generate_btn = ModernButton(
            btn_frame, text="▶ Load & Convert", command=self.load_and_convert,
            fg_color=COLORS['success'], width=160, height=36
        )
        self.generate_btn.pack(side="left")
        self.generate_btn.configure(state="disabled")
        
        # Main content area
        content = ctk.CTkFrame(self, fg_color=COLORS['bg_panel'], corner_radius=8)
        content.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Mode selector (File or Paste) - moved to top for visibility
        self.mode_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.mode_frame.pack(fill="x", padx=15, pady=(10, 8))
        
        ctk.CTkLabel(
            self.mode_frame, text="Input Method:",
            font=("Segoe UI", 12, "bold"), text_color=COLORS['fg_text']
        ).pack(side="left", padx=(0, 15))
        
        ctk.CTkRadioButton(
            self.mode_frame, text="📂 From File", variable=self.input_mode,
            value="file", font=("Segoe UI", 11), command=self.on_mode_change,
            fg_color=COLORS['accent_1'], hover_color=COLORS['accent_1'],
            text_color=COLORS['fg_text']
        ).pack(side="left", padx=(0, 20))
        
        ctk.CTkRadioButton(
            self.mode_frame, text="📋 From Paste", variable=self.input_mode,
            value="paste", font=("Segoe UI", 11), command=self.on_mode_change,
            fg_color=COLORS['accent_2'], hover_color=COLORS['accent_2'],
            text_color=COLORS['fg_text']
        ).pack(side="left")
        
        # File selection section (shows selected filename) - shown when mode is "file"
        self.file_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=15, pady=(0, 8))
        
        ModernButton(
            self.file_frame, text="📂 Select File", command=self.select_file,
            fg_color=COLORS['accent_1'], width=140, height=32
        ).pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(
            self.file_frame, text="Selected File:",
            font=("Segoe UI", 12, "bold"), text_color=COLORS['fg_text']
        ).pack(side="left", padx=(0, 10))
        
        self.file_label = ctk.CTkLabel(
            self.file_frame, text="No file selected",
            font=("Segoe UI", 11), text_color=COLORS['fg_sub']
        )
        self.file_label.pack(side="left", fill="x", expand=True)
        
        # Paste text area section - shown when mode is "paste"
        self.paste_frame = ctk.CTkFrame(content, fg_color="transparent")
        # Don't pack initially, will be shown/hidden based on mode
        
        paste_label_text = "Paste Workflow JSON:" if self.mode == "json" else "Paste BridgeZip:"
        ctk.CTkLabel(
            self.paste_frame, text=paste_label_text,
            font=("Segoe UI", 12, "bold"), text_color=COLORS['fg_text']
        ).pack(anchor="w", padx=(0, 0), pady=(0, 5))
        
        self.paste_text_area = ctk.CTkTextbox(
            self.paste_frame, font=("Consolas", 11), fg_color=COLORS['bg_main'],
            text_color=COLORS['fg_text'], wrap="none", corner_radius=8, height=160
        )
        self.paste_text_area.pack(fill="both", expand=True, pady=(0, 8))
        
        # Bind text change to update button state
        self.paste_text_area.bind("<KeyRelease>", lambda e: self.update_button_state())
        self.paste_text_area.bind("<Button-1>", lambda e: self.update_button_state())
        
        # Initially hide paste frame (file mode is default)
        self.paste_frame.pack_forget()
        
        # Instructions - moved below input sections
        instructions = ctk.CTkFrame(content, fg_color="transparent")
        instructions.pack(fill="x", padx=15, pady=(0, 8))
        
        if self.mode == "json":
            instruction_text = (
                "The workflow will be automatically converted to BridgeZip for use with EXTRACT NODES."
            )
        else:
            instruction_text = (
                "The BridgeZip will be automatically converted to JSON for use with EXTRACT GROUPS."
            )
        
        ctk.CTkLabel(
            instructions, text=instruction_text,
            font=("Segoe UI", 10), text_color=COLORS['fg_sub'],
            justify="left", wraplength=600
        ).pack(anchor="w")
        
        # Existing data section (if available)
        self.existing_frame = ctk.CTkFrame(content, fg_color="transparent")
        self.existing_frame.pack(fill="x", padx=15, pady=(0, 8))
        
        # Status message
        self.status_label = ctk.CTkLabel(
            content, text="",
            font=("Segoe UI", 10), text_color=COLORS['fg_sub']
        )
        self.status_label.pack(padx=15, pady=(0, 10), anchor="w")
        
        # Footer - only Cancel button (secondary action)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 20))
        
        ModernButton(
            footer, text="Cancel", command=self.cancel,
            fg_color=COLORS['btn_surface'], width=100, height=32
        ).pack(side="left")
    
    def check_existing_data(self):
        """Check if shared data exists and offer to reuse."""
        if self.mode == "json" and self.shared_data.get("json"):
            # JSON mode: check if JSON already exists
            filename = self.shared_data.get("filename", "workflow")
            self.show_existing_option(f"Workflow JSON already loaded: {filename}")
        elif self.mode == "bridgezip" and self.shared_data.get("bridgezip"):
            # BridgeZip mode: check if BridgeZip already exists
            filename = self.shared_data.get("filename", "workflow")
            self.show_existing_option(f"BridgeZip already loaded: {filename}")
    
    def show_existing_option(self, message):
        """Show option to use existing data."""
        existing_info = ctk.CTkFrame(self.existing_frame, fg_color=COLORS['success'], corner_radius=6)
        existing_info.pack(fill="x", padx=0, pady=5)
        
        inner = ctk.CTkFrame(existing_info, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)
        
        ctk.CTkLabel(
            inner, text=message,
            font=("Segoe UI", 11), text_color="white"
        ).pack(side="left")
        
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ModernButton(
            btn_frame, text="Use Existing", command=self.use_existing,
            fg_color="white", text_color=COLORS['success'], width=100, height=28
        ).pack(side="left", padx=(10, 5))
        
        ModernButton(
            btn_frame, text="Load New", command=self.clear_existing_option,
            fg_color=COLORS['btn_surface'], width=100, height=28
        ).pack(side="left")
    
    def clear_existing_option(self):
        """Clear the existing option frame."""
        for widget in self.existing_frame.winfo_children():
            widget.destroy()
    
    def use_existing(self):
        """Use existing shared data."""
        if self.mode == "json":
            workflow_json = self.shared_data.get("json")
            bridgezip = self.shared_data.get("bridgezip")
            if workflow_json:
                self.destroy()
                self.callback(workflow_json, bridgezip)
                return
        else:  # bridgezip
            workflow_json = self.shared_data.get("json")
            bridgezip = self.shared_data.get("bridgezip")
            if bridgezip:
                self.destroy()
                self.callback(workflow_json, bridgezip)
                return
        
        messagebox.showwarning("Error", "Existing data not found.")
    
    def select_file(self):
        """Open file picker."""
        if self.mode == "json":
            filetypes = [("Workflow JSON", "*.json"), ("All Files", "*.*")]
            title = "Select Workflow JSON File"
        else:  # bridgezip
            filetypes = [("BridgeZip", "*.txt"), ("Text Files", "*.txt"), ("All Files", "*.*")]
            title = "Select BridgeZip File"
        
        path = filedialog.askopenfilename(
            title=title,
            filetypes=filetypes
        )
        
        if path:
            self.selected_file = path
            filename = os.path.basename(path)
            self.file_label.configure(text=filename, text_color=COLORS['fg_text'])
            self.update_button_state()
            self.status_label.configure(text="")
    
    def load_and_convert(self):
        """Load file or paste text and convert."""
        if self.input_mode.get() == "paste":
            # Process pasted text
            pasted_text = self.paste_text_area.get("1.0", "end-1c").strip()
            if not pasted_text:
                messagebox.showwarning("Empty", "Please paste some text first.")
                return
            self.process_pasted_text(pasted_text)
            return
        
        # Process file (existing logic)
        if not self.selected_file:
            messagebox.showwarning("No File", "Please select a file first.")
            return
        
        self.status_label.configure(
            text="⏳ Loading file...",
            text_color=COLORS['accent_2']
        )
        self.update()
        
        try:
            if self.mode == "json":
                # Load JSON and convert to BridgeZip
                with open(self.selected_file, 'r', encoding='utf-8') as f:
                    workflow_json = f.read()
                
                # Validate JSON
                try:
                    data = json.loads(workflow_json)
                    if "nodes" not in data:
                        raise ValueError("Not a valid workflow JSON (missing 'nodes' key)")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON: {e}")
                
                # Convert to BridgeZip
                from engine.bridgezip import compress_workflow
                self.status_label.configure(text="⏳ Converting to BridgeZip...")
                self.update()
                
                bridgezip = compress_workflow(workflow_json)
                if bridgezip.startswith("Error"):
                    raise ValueError(bridgezip)
                
                # Store in shared data
                self.shared_data["json"] = workflow_json
                self.shared_data["bridgezip"] = bridgezip
                self.shared_data["filename"] = os.path.basename(self.selected_file)
                
                self.status_label.configure(
                    text="✅ Workflow loaded and converted to BridgeZip (ready for EXTRACT NODES)",
                    text_color=COLORS['success']
                )
                
                # Destroy panel and call callback
                self.after(300, lambda: self.finish(workflow_json, bridgezip))
                
            else:  # bridgezip
                # Load BridgeZip and convert to JSON
                with open(self.selected_file, 'r', encoding='utf-8') as f:
                    bridgezip = f.read().strip()
                
                # Validate BridgeZip
                if not bridgezip.startswith("W:"):
                    raise ValueError("Not a valid BridgeZip file (must start with 'W:')")
                
                # Convert to JSON
                from engine.bridgezip import inflate_workflow
                self.status_label.configure(text="⏳ Converting to JSON...")
                self.update()
                
                workflow_json = inflate_workflow(bridgezip)
                if workflow_json.startswith("Error"):
                    raise ValueError(workflow_json)
                
                # Store in shared data
                self.shared_data["json"] = workflow_json
                self.shared_data["bridgezip"] = bridgezip
                self.shared_data["filename"] = os.path.basename(self.selected_file)
                
                self.status_label.configure(
                    text="✅ BridgeZip loaded and converted to JSON (ready for EXTRACT GROUPS)",
                    text_color=COLORS['success']
                )
                
                # Destroy panel and call callback
                self.after(300, lambda: self.finish(workflow_json, bridgezip))
                
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Error: {str(e)}",
                text_color=COLORS['red']
            )
            messagebox.showerror("Error", f"Failed to load file:\n{str(e)}")
    
    def finish(self, workflow_json, bridgezip):
        """Finish loading and call callback."""
        self.destroy()
        self.callback(workflow_json, bridgezip)
    
    def cancel(self):
        """Cancel and close panel."""
        self.destroy()
        self.callback(None, None)
    
    def on_mode_change(self):
        """Handle mode change between file and paste."""
        if self.input_mode.get() == "file":
            # Show file frame, hide paste frame
            self.file_frame.pack(fill="x", padx=15, pady=(0, 8), after=self.mode_frame)
            self.paste_frame.pack_forget()
            self.selected_file = None
            self.file_label.configure(text="No file selected")
        else:
            # Show paste frame, hide file frame
            self.paste_frame.pack(fill="x", padx=15, pady=(0, 8), after=self.mode_frame)
            self.file_frame.pack_forget()
            self.selected_file = None
            self.paste_text_area.focus_set()
        
        # Update button state
        self.update_button_state()
    
    def update_button_state(self):
        """Update Load & Convert button state based on current mode and input."""
        if self.input_mode.get() == "file":
            # Enable if file is selected
            self.generate_btn.configure(state="normal" if self.selected_file else "disabled")
        else:
            # Enable if paste area has text
            text = self.paste_text_area.get("1.0", "end-1c").strip()
            self.generate_btn.configure(state="normal" if text else "disabled")
    
    def process_pasted_text(self, pasted_text):
        """Process pasted text (same logic as file loading)."""
        if not pasted_text or not pasted_text.strip():
            messagebox.showwarning("Empty", "Please paste some text.")
            return
        
        self.status_label.configure(
            text="⏳ Processing pasted text...",
            text_color=COLORS['accent_2']
        )
        self.update()
        
        try:
            if self.mode == "json":
                # Validate and process JSON
                workflow_json = pasted_text.strip()
                try:
                    data = json.loads(workflow_json)
                    if "nodes" not in data:
                        raise ValueError("Not a valid workflow JSON (missing 'nodes' key)")
                except json.JSONDecodeError as e:
                    raise ValueError(f"Invalid JSON: {e}")
                
                # Convert to BridgeZip
                from engine.bridgezip import compress_workflow
                self.status_label.configure(text="⏳ Converting to BridgeZip...")
                self.update()
                
                bridgezip = compress_workflow(workflow_json)
                if bridgezip.startswith("Error"):
                    raise ValueError(bridgezip)
                
                # Store in shared data
                self.shared_data["json"] = workflow_json
                self.shared_data["bridgezip"] = bridgezip
                self.shared_data["filename"] = "Pasted JSON"
                
                self.status_label.configure(
                    text="✅ Workflow loaded and converted to BridgeZip (ready for EXTRACT NODES)",
                    text_color=COLORS['success']
                )
                
                # Destroy panel and call callback
                self.after(300, lambda: self.finish(workflow_json, bridgezip))
                
            else:  # bridgezip
                # Validate and process BridgeZip
                bridgezip = pasted_text.strip()
                if not bridgezip.startswith("W:"):
                    raise ValueError("Not a valid BridgeZip (must start with 'W:')")
                
                # Convert to JSON
                from engine.bridgezip import inflate_workflow
                self.status_label.configure(text="⏳ Converting to JSON...")
                self.update()
                
                workflow_json = inflate_workflow(bridgezip)
                if workflow_json.startswith("Error"):
                    raise ValueError(workflow_json)
                
                # Store in shared data
                self.shared_data["json"] = workflow_json
                self.shared_data["bridgezip"] = bridgezip
                self.shared_data["filename"] = "Pasted BridgeZip"
                
                self.status_label.configure(
                    text="✅ BridgeZip loaded and converted to JSON (ready for EXTRACT GROUPS)",
                    text_color=COLORS['success']
                )
                
                # Destroy panel and call callback
                self.after(300, lambda: self.finish(workflow_json, bridgezip))
                
        except Exception as e:
            self.status_label.configure(
                text=f"❌ Error: {str(e)}",
                text_color=COLORS['red']
            )
            messagebox.showerror("Error", f"Failed to process pasted text:\n{str(e)}")



