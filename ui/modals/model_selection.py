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

class ModelSelectionPanel(ctk.CTkFrame):
    """Embedded panel for selecting which models to include in the output."""
    
    def __init__(self, parent, models_data, callback):
        super().__init__(parent, fg_color=COLORS['bg_main'], corner_radius=0)
        self.models_data = models_data
        self.callback = callback
        self.selection_vars = {}  # Store checkbox variables
        
        self.setup_ui()
    
    def setup_ui(self):
        """Build the panel UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent", height=50)
        header.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkLabel(
            header, text="Select Models to Extract", 
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
        
        # Scrollable frame for tree
        scroll_frame = ctk.CTkScrollableFrame(
            self, fg_color=COLORS['bg_panel'], corner_radius=8
        )
        scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Build tree structure
        self.build_tree(scroll_frame)
        
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
    
    def cancel(self):
        """Cancel selection and clear the panel."""
        # Destroy this panel first
        self.destroy()
        # Clear the output area (restore text area)
        self.callback("")
    
    def build_tree(self, parent):
        """Build the checkbox tree structure."""
        for model_type in ["CHECKPOINTS", "LORAS", "VAES", "UNETS", "CLIPS"]:
            if model_type not in self.models_data or not self.models_data[model_type]:
                continue
            
            # Type-level checkbox
            type_frame = ctk.CTkFrame(parent, fg_color="transparent")
            type_frame.pack(fill="x", padx=10, pady=5)
            
            type_var = tk.BooleanVar(value=True)
            self.selection_vars[f"type_{model_type}"] = type_var
            
            type_check = ctk.CTkCheckBox(
                type_frame, text=f"{model_type} ({self._count_models(model_type)})",
                variable=type_var, font=("Segoe UI", 14, "bold"),
                command=lambda mt=model_type, tv=type_var: self.on_type_toggle(mt, tv)
            )
            type_check.pack(side="left")
            
            # Expand/collapse button
            expand_state = {"expanded": True}
            expand_btn = ctk.CTkButton(
                type_frame, text="▼", width=30, height=24,
                fg_color=COLORS['btn_surface']
            )
            expand_btn.pack(side="left", padx=5)
            expand_btn.configure(
                command=lambda mt=model_type, es=expand_state, eb=expand_btn: self.toggle_expand(mt, es, eb)
            )
            
            # Category container (initially visible)
            category_container = ctk.CTkFrame(parent, fg_color="transparent")
            category_container.pack(fill="x", padx=30, pady=2)
            self.selection_vars[f"container_{model_type}"] = category_container
            self.selection_vars[f"expand_state_{model_type}"] = expand_state
            
            # Categories
            for category, models in self.models_data[model_type].items():
                cat_frame = ctk.CTkFrame(category_container, fg_color="transparent")
                cat_frame.pack(fill="x", padx=10, pady=2)
                
                # Category checkbox
                cat_var = tk.BooleanVar(value=True)
                self.selection_vars[f"cat_{model_type}_{category}"] = cat_var
                
                cat_check = ctk.CTkCheckBox(
                    cat_frame, text=f"{category} ({len(models)})",
                    variable=cat_var, font=("Segoe UI", 12),
                    command=lambda mt=model_type, cat=category, cv=cat_var: self.on_category_toggle(mt, cat, cv)
                )
                cat_check.pack(side="left")
                
                # Model list container
                model_container = ctk.CTkFrame(category_container, fg_color="transparent")
                model_container.pack(fill="x", padx=30, pady=2)
                
                # Individual model checkboxes
                for model in models:
                    model_var = tk.BooleanVar(value=True)
                    self.selection_vars[f"model_{model_type}_{category}_{model}"] = model_var
                    
                    model_check = ctk.CTkCheckBox(
                        model_container, text=model,
                        variable=model_var, font=("Consolas", 10),
                        command=lambda mt=model_type, cat=category, cv=cat_var, mv=model_var: self.on_model_toggle(mt, cat, cv, mv)
                    )
                    model_check.pack(anchor="w", padx=20, pady=1)
    
    def _count_models(self, model_type):
        """Count total models in a type."""
        count = 0
        if model_type in self.models_data:
            for category in self.models_data[model_type].values():
                count += len(category)
        return count
    
    def toggle_expand(self, model_type, expand_state, expand_btn):
        """Toggle expand/collapse of category container."""
        container = self.selection_vars.get(f"container_{model_type}")
        if container:
            if expand_state["expanded"]:
                container.pack_forget()
                expand_state["expanded"] = False
                expand_btn.configure(text="▶")
            else:
                container.pack(fill="x", padx=30, pady=2)
                expand_state["expanded"] = True
                expand_btn.configure(text="▼")
    
    def on_type_toggle(self, model_type, type_var):
        """Handle type-level checkbox toggle."""
        state = type_var.get()
        # Update all categories and models under this type
        for key in list(self.selection_vars.keys()):
            if key.startswith(f"cat_{model_type}_") or key.startswith(f"model_{model_type}_"):
                self.selection_vars[key].set(state)
        self.update_generate_button()
    
    def on_category_toggle(self, model_type, category, cat_var):
        """Handle category-level checkbox toggle."""
        state = cat_var.get()
        # Update all models under this category
        for key in list(self.selection_vars.keys()):
            if key.startswith(f"model_{model_type}_{category}_"):
                self.selection_vars[key].set(state)
        
        # Update type checkbox based on category states
        self._update_type_checkbox(model_type)
        self.update_generate_button()
    
    def on_model_toggle(self, model_type, category, cat_var, model_var):
        """Handle model-level checkbox toggle."""
        # Update category checkbox based on model states
        all_checked = all(
            self.selection_vars.get(f"model_{model_type}_{category}_{m}", tk.BooleanVar(value=False)).get()
            for m in self.models_data[model_type][category]
        )
        cat_var.set(all_checked)
        
        # Update type checkbox
        self._update_type_checkbox(model_type)
        self.update_generate_button()
    
    def _update_type_checkbox(self, model_type):
        """Update type checkbox based on all category/model states."""
        type_var = self.selection_vars.get(f"type_{model_type}")
        if not type_var:
            return
        
        all_checked = all(
            self.selection_vars.get(f"cat_{model_type}_{cat}", tk.BooleanVar(value=False)).get()
            for cat in self.models_data[model_type].keys()
        )
        type_var.set(all_checked)
    
    def select_all(self):
        """Select all models."""
        for var in self.selection_vars.values():
            if isinstance(var, tk.BooleanVar):
                var.set(True)
        self.update_generate_button()
    
    def select_none(self):
        """Deselect all models."""
        for var in self.selection_vars.values():
            if isinstance(var, tk.BooleanVar):
                var.set(False)
        self.update_generate_button()
    
    def update_generate_button(self):
        """Enable/disable generate button based on selection."""
        has_selection = any(
            var.get() for var in self.selection_vars.values()
            if isinstance(var, tk.BooleanVar) and var.get()
        )
        self.generate_btn.configure(state="normal" if has_selection else "disabled")
    
    def generate_output(self):
        """Generate output from selected models."""
        output_lines = ["=== USER MODEL INDEX ===\n"]
        
        for model_type in ["CHECKPOINTS", "LORAS", "VAES", "UNETS", "CLIPS"]:
            if model_type not in self.models_data:
                continue
            
            selected_models = []
            for category, models in self.models_data[model_type].items():
                category_models = []
                for model in models:
                    var_key = f"model_{model_type}_{category}_{model}"
                    if self.selection_vars.get(var_key, tk.BooleanVar(value=False)).get():
                        category_models.append(model)
                
                if category_models:
                    selected_models.append((category, category_models))
            
            if not selected_models:
                continue
            
            # Count total selected
            total_count = sum(len(models) for _, models in selected_models)
            output_lines.append(f"[{model_type} ({total_count})]")
            
            # Add categories and models
            for category, models in selected_models:
                output_lines.append(f"  {category}:")
                for model in models:
                    output_lines.append(f"    - {model}")
            output_lines.append("")
        
        output = "\n".join(output_lines)
        # Destroy this panel first, then set the output
        self.destroy()
        self.callback(output)

