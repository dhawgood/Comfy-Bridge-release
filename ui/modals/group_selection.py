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
from utils.ui_helpers import COLORS, ModernButton

class GroupSelectionPanel(ctk.CTkFrame):
    """Embedded panel for selecting which groups to extract."""
    
    def __init__(self, parent, groups_data, callback):
        super().__init__(parent, fg_color=COLORS['bg_main'], corner_radius=0)
        self.groups_data = groups_data
        self.callback = callback
        self.selection_vars = {}  # Store checkbox variables
        
        self.setup_ui()
    
    def setup_ui(self):
        """Build the panel UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkLabel(
            header, text="Select Groups to Extract", 
            font=("Segoe UI", 18, "bold"), text_color=COLORS['fg_text']
        ).pack(side="left")
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        
        ModernButton(
            btn_frame, text="Select All", command=self.select_all,
            fg_color=COLORS['btn_surface'], width=80, height=28
        ).pack(side="left", padx=5)
        
        ModernButton(
            btn_frame, text="Select None", command=self.select_none,
            fg_color=COLORS['btn_surface'], width=80, height=28
        ).pack(side="left", padx=5)
        
        # Scrollable frame for groups list
        scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color=COLORS['bg_panel'], corner_radius=8
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Build groups list
        self.build_list(scroll_frame)
        
        # Footer buttons
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=(0, 20))
        
        ModernButton(
            footer, text="Cancel", command=self.cancel,
            fg_color=COLORS['btn_surface'], width=100
        ).pack(side="left")
        
        self.generate_btn = ModernButton(
            footer, text="Generate Output", command=self.generate_output,
            fg_color=COLORS['accent_1'], width=150
        )
        self.generate_btn.pack(side="right")
        self.update_generate_button()
    
    def build_list(self, parent):
        """Build the groups list with checkboxes."""
        if not self.groups_data:
            ctk.CTkLabel(
                parent, text="No groups found in workflow.",
                font=("Segoe UI", 12), text_color=COLORS['fg_sub']
            ).pack(pady=20)
            return
        
        for group in self.groups_data:
            group_name = group.get("title", "Untitled")
            node_count = group.get("node_count", 0)
            group_id = group.get("id", "?")
            
            # Group frame
            group_frame = ctk.CTkFrame(parent, fg_color="transparent")
            group_frame.pack(fill="x", padx=10, pady=5)
            
            # Checkbox
            group_var = tk.BooleanVar(value=True)
            self.selection_vars[group_name] = group_var
            
            group_check = ctk.CTkCheckBox(
                group_frame, 
                text=f"{group_name} ({node_count} nodes) [ID: {group_id}]",
                variable=group_var, font=("Segoe UI", 12),
                command=self.update_generate_button
            )
            group_check.pack(side="left")
    
    def select_all(self):
        """Select all groups."""
        for var in self.selection_vars.values():
            if isinstance(var, tk.BooleanVar):
                var.set(True)
        self.update_generate_button()
    
    def select_none(self):
        """Deselect all groups."""
        for var in self.selection_vars.values():
            if isinstance(var, tk.BooleanVar):
                var.set(False)
        self.update_generate_button()
    
    def update_generate_button(self):
        """Enable/disable generate button based on selection."""
        has_selection = any(
            var.get() for var in self.selection_vars.values()
            if isinstance(var, tk.BooleanVar)
        )
        self.generate_btn.configure(state="normal" if has_selection else "disabled")
    
    def cancel(self):
        """Cancel selection and clear the panel."""
        self.destroy()
        self.callback("")
    
    def generate_output(self):
        """Generate output from selected groups."""
        selected_groups = [
            group.get("title") for group in self.groups_data
            if self.selection_vars.get(group.get("title"), tk.BooleanVar(value=False)).get()
        ]
        
        if not selected_groups:
            return
        
        # Destroy this panel first, then generate output
        self.destroy()
        # The callback will handle generating the output with selected group names
        self.callback(selected_groups)



