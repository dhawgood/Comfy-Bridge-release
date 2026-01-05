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

import tkinter as tk
import customtkinter as ctk
import os

# Colors from main app
COLORS = {
    # --- Backgrounds ("Ink Soup" / Deep Slate) ---
    "bg_main":    "#0f172a",      # A very deep blue-black (Slate 900). richer than standard gray.
    "bg_panel":   "#1e293b",      # A lighter slate for panels (Slate 800).
    
    # --- Typography (Mist & Bone) ---
    "fg_text":    "#f1f5f9",      # Crisp, cool white.
    "fg_sub":     "#94a3b8",      # Muted slate text for secondary info.
    
    # --- The "Oasis" Accents ---
    "accent_1":   "#14b8a6",      # Primary Action: Teal/Turquoise (From the 'Oasis' swatch).
    "accent_2":   "#64748b",      # Secondary Action: Muted Slate Blue.
    "success":    "#10b981",      # Success: Soft Sage Green (Natural, not digital).
    "purple":     "#818cf8",      # AI/Special: Dusty Iris.

    # --- Semantics (Earthy tones from Image 2) ---
    "orange":     "#d97706",      # Muted Amber
    "red":        "#be123c",      # Brick/Rose (Not bright red)
    "info":       "#0ea5e9",      # Sky Blue

    # --- Interactive (Slate Tones) ---
    "btn_surface": "#334155",     # Button background (Slate 700)
    "btn_hover":   "#475569",     # Hover state (Slate 600)
    "tab_hover":   "#1e293b",     # Tab hover

    # --- Tooltips ---
    "tooltip_bg": "#334155",      
    "tooltip_fg": "#f8fafc"       
}

def center_window(window, parent, width=None, height=None):
    """
    Center a window relative to its parent window.
    
    Args:
        window: The window to center (CTkToplevel or Tk)
        parent: The parent window
        width: Window width (if None, uses current geometry)
        height: Window height (if None, uses current geometry)
    """
    window.update_idletasks()
    
    # Get window dimensions
    if width is None or height is None:
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()
    
    # Get parent position and size
    parent.update_idletasks()
    parent_x = parent.winfo_x()
    parent_y = parent.winfo_y()
    parent_width = parent.winfo_width()
    parent_height = parent.winfo_height()
    
    # Calculate centered position
    x = parent_x + (parent_width // 2) - (width // 2)
    y = parent_y + (parent_height // 2) - (height // 2)
    
    # Ensure window stays on screen
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    x = max(0, min(x, screen_width - width))
    y = max(0, min(y, screen_height - height))
    
    window.geometry(f"{width}x{height}+{x}+{y}")

class ToolTip:
    """Tooltip widget for buttons and other UI elements."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self.show_tip)
        widget.bind("<Leave>", self.hide_tip)
    
    def show_tip(self, event=None):
        if self.tip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x = x + self.widget.winfo_rootx() + 25
        y = y + self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tk.Label(
            tw, text=self.text, justify=tk.LEFT,
            background=COLORS['tooltip_bg'], foreground=COLORS['tooltip_fg'],
            relief=tk.SOLID, borderwidth=1, font=("Segoe UI", 9)
        ).pack(ipadx=4, ipady=2)
    
    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class ModernButton(ctk.CTkButton):
    """Styled button component."""
    def __init__(self, master, **kwargs):
        kwargs.setdefault("corner_radius", 6)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("border_color", "#30363d")
        kwargs.setdefault("font", ("Segoe UI", 11, "bold"))
        kwargs.setdefault("height", 32)
        super().__init__(master, **kwargs)

class ModernModal(ctk.CTkToplevel):
    """Modal dialog for displaying documentation or information."""
    def __init__(self, parent, title, text):
        super().__init__(parent)
        self.title(title)
        self.geometry("700x550")
        self.configure(fg_color=COLORS['bg_main'])
        self.resizable(False, False)
        center_window(self, parent, 700, 550)
        self.grab_set()
        self.focus_set()
        
        header = ctk.CTkFrame(self, fg_color="transparent", height=40)
        header.pack(fill="x", pady=15, padx=20)
        ctk.CTkLabel(header, text=title, font=("Segoe UI", 18, "bold"), text_color="white").pack(side="left")
        
        text_area = ctk.CTkTextbox(
            self, font=("Segoe UI", 13), fg_color=COLORS['bg_panel'],
            text_color=COLORS['fg_text'], wrap="word", corner_radius=8, border_width=1, border_color="#30363d"
        )
        text_area.insert("1.0", text)
        text_area.configure(state="disabled")
        text_area.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        ModernButton(self, text="CLOSE", command=self.destroy, fg_color=COLORS['btn_surface'], width=100).pack(pady=(0, 20))

class SettingsModal(ctk.CTkToplevel):
    """Settings modal for configuring ComfyUI connection and paths."""
    def __init__(self, parent, on_save_callback=None):
        super().__init__(parent)
        self.title("Settings")
        self.configure(fg_color=COLORS['bg_main'])
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        width, height = 600, 500
        self.geometry(f"{width}x{height}")
        center_window(self, parent, width, height)
        
        # Import here to avoid circular imports
        from utils.config import get_comfyui_url, set_comfyui_url, get_comfyui_input_folder, set_comfyui_input_folder
        
        self.get_comfyui_url = get_comfyui_url
        self.set_comfyui_url = set_comfyui_url
        self.get_comfyui_input_folder = get_comfyui_input_folder
        self.set_comfyui_input_folder = set_comfyui_input_folder
        
        # Store callback to call after saving
        self.on_save_callback = on_save_callback
        
        # Store original values for cancel
        self.original_url = get_comfyui_url()
        self.original_input_folder = get_comfyui_input_folder()
        
        self.setup_ui()
    
    def setup_ui(self):
        """Build the settings UI."""
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(
            header, text="Settings", font=("Segoe UI", 20, "bold"),
            text_color=COLORS['fg_text']
        ).pack(anchor="w")
        
        # Main content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=10)
        
        # ComfyUI Connection Section
        conn_frame = ctk.CTkFrame(content, fg_color=COLORS['bg_panel'], corner_radius=6, border_width=1, border_color="#30363d")
        conn_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            conn_frame, text="ComfyUI Connection", font=("Segoe UI", 14, "bold"),
            text_color=COLORS['fg_text']
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        url_row = ctk.CTkFrame(conn_frame, fg_color="transparent")
        url_row.pack(fill="x", padx=15, pady=(0, 10))
        
        ctk.CTkLabel(
            url_row, text="URL:", font=("Segoe UI", 11),
            text_color=COLORS['fg_sub'], width=60
        ).pack(side="left", padx=(0, 10))
        
        self.url_entry = ctk.CTkEntry(
            url_row, font=("Segoe UI", 11),
            fg_color=COLORS['bg_main'], text_color=COLORS['fg_text'],
            border_width=1, border_color="#30363d", corner_radius=6
        )
        self.url_entry.insert(0, self.original_url)
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        test_btn = ModernButton(
            url_row, text="Test", command=self.test_connection,
            fg_color=COLORS['accent_1'], width=80
        )
        test_btn.pack(side="left", padx=(0, 5))
        
        reset_btn = ModernButton(
            url_row, text="Reset", command=self.reset_to_default,
            fg_color=COLORS['btn_surface'], width=70
        )
        reset_btn.pack(side="left")
        
        self.connection_status = ctk.CTkLabel(
            conn_frame, text="● Not tested", font=("Segoe UI", 10),
            text_color=COLORS['fg_sub']
        )
        self.connection_status.pack(anchor="w", padx=15, pady=(0, 15))
        
        # ComfyUI Input Folder Section
        folder_frame = ctk.CTkFrame(content, fg_color=COLORS['bg_panel'], corner_radius=6, border_width=1, border_color="#30363d")
        folder_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(
            folder_frame, text="ComfyUI Image Input Folder", font=("Segoe UI", 14, "bold"),
            text_color=COLORS['fg_text']
        ).pack(anchor="w", padx=15, pady=(15, 10))
        
        folder_row = ctk.CTkFrame(folder_frame, fg_color="transparent")
        folder_row.pack(fill="x", padx=15, pady=(0, 10))
        
        self.folder_entry = ctk.CTkEntry(
            folder_row, font=("Segoe UI", 11),
            fg_color=COLORS['bg_main'], text_color=COLORS['fg_text'],
            border_width=1, border_color="#30363d", corner_radius=6,
            state="readonly"
        )
        if self.original_input_folder:
            self.folder_entry.insert(0, self.original_input_folder)
        self.folder_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        browse_btn = ModernButton(
            folder_row, text="Browse", command=self.browse_folder,
            fg_color=COLORS['btn_surface'], width=80
        )
        browse_btn.pack(side="left")
        
        self.folder_status = ctk.CTkLabel(
            folder_frame, text="", font=("Segoe UI", 10),
            text_color=COLORS['fg_sub']
        )
        self.folder_status.pack(anchor="w", padx=15, pady=(0, 15))
        self.update_folder_status()
        
        # Footer buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        cancel_btn = ModernButton(
            btn_frame, text="Cancel", command=self.cancel,
            fg_color=COLORS['btn_surface'], width=100
        )
        cancel_btn.pack(side="right", padx=(10, 0))
        
        save_btn = ModernButton(
            btn_frame, text="Save", command=self.save_settings,
            fg_color=COLORS['accent_1'], width=100
        )
        save_btn.pack(side="right")
    
    def test_connection(self):
        """Test ComfyUI connection."""
        url = self.url_entry.get().strip()
        if not url:
            self.connection_status.configure(
                text="● Error: URL cannot be empty",
                text_color=COLORS['red']
            )
            return
        
        self.connection_status.configure(
            text="● Testing...",
            text_color=COLORS['orange']
        )
        self.update()
        
        try:
            import urllib.request
            import urllib.error
            import socket
            test_url = url.rstrip('/') + '/object_info'
            req = urllib.request.Request(test_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=3) as response:
                if response.status == 200:
                    self.connection_status.configure(
                        text="● Connected successfully",
                        text_color=COLORS['success']
                    )
                else:
                    self.connection_status.configure(
                        text=f"● Error: HTTP {response.status}",
                        text_color=COLORS['red']
                    )
        except urllib.error.URLError as e:
            # Parse common connection errors for user-friendly messages
            error_str = str(e).lower()
            if '10061' in error_str or 'connection refused' in error_str:
                message = "● ComfyUI is not running on this port"
            elif '10060' in error_str or 'timed out' in error_str:
                message = "● Connection timeout - check if ComfyUI is running"
            elif '11001' in error_str or 'getaddrinfo failed' in error_str:
                message = "● Invalid hostname or address"
            elif '10049' in error_str or 'cannot assign' in error_str:
                message = "● Address already in use"
            else:
                # Extract the meaningful part of the error
                if hasattr(e, 'reason'):
                    reason = str(e.reason)
                    if len(reason) > 60:
                        reason = reason[:57] + "..."
                    message = f"● Connection failed: {reason}"
                else:
                    message = "● Connection failed - check URL and ComfyUI status"
            
            self.connection_status.configure(
                text=message,
                text_color=COLORS['red']
            )
        except socket.timeout:
            self.connection_status.configure(
                text="● Connection timeout - ComfyUI may not be running",
                text_color=COLORS['red']
            )
        except Exception as e:
            # Fallback for any other errors
            error_msg = str(e)
            if len(error_msg) > 70:
                error_msg = error_msg[:67] + "..."
            self.connection_status.configure(
                text=f"● Error: {error_msg}",
                text_color=COLORS['red']
            )
    
    def reset_to_default(self):
        """Reset URL to default value."""
        default_url = "http://127.0.0.1:8188"
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, default_url)
        self.connection_status.configure(
            text="● Reset to default",
            text_color=COLORS['fg_sub']
        )
    
    def browse_folder(self):
        """Browse for ComfyUI input folder."""
        from tkinter import filedialog
        folder = filedialog.askdirectory(title="Select ComfyUI Input Folder")
        if folder:
            self.folder_entry.configure(state="normal")
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            self.folder_entry.configure(state="readonly")
            self.set_comfyui_input_folder(folder)
            self.update_folder_status()
    
    def update_folder_status(self):
        """Update folder validation status."""
        folder = self.folder_entry.get().strip()
        if not folder:
            self.folder_status.configure(text="● No folder selected", text_color=COLORS['fg_sub'])
        elif os.path.exists(folder) and os.path.isdir(folder):
            self.folder_status.configure(text="✓ Valid folder", text_color=COLORS['success'])
        else:
            self.folder_status.configure(text="✗ Folder does not exist", text_color=COLORS['red'])
    
    def save_settings(self):
        """Save settings to config."""
        url = self.url_entry.get().strip()
        if not url:
            from tkinter import messagebox
            messagebox.showerror("Error", "ComfyUI URL cannot be empty.")
            return
        
        # Save URL
        self.set_comfyui_url(url)
        
        # Folder is already saved when browsed, but ensure it's in config
        folder = self.folder_entry.get().strip()
        if folder:
            self.set_comfyui_input_folder(folder)
        
        from tkinter import messagebox
        messagebox.showinfo("Settings Saved", "Settings have been saved successfully.")
        
        # Call callback if provided to refresh UI
        if self.on_save_callback:
            self.on_save_callback()
        
        self.destroy()
    
    def cancel(self):
        """Cancel and close without saving."""
        self.destroy()

class TextEditorPanel(ctk.CTkFrame):
    """Text editor panel with file operations."""
    def __init__(self, parent, label_text, file_type_def):
        super().__init__(parent, fg_color=COLORS['bg_panel'], corner_radius=0, border_width=1, border_color="#30363d")
        self.file_type_def = file_type_def
        
        header = ctk.CTkFrame(self, fg_color="transparent", height=28)
        header.pack(fill="x", pady=(0, 5))
        if label_text:
            ctk.CTkLabel(header, text=label_text, font=("Segoe UI", 11, "bold"), text_color=COLORS['fg_sub']).pack(side="left", padx=10)
        
        btn_frame = ctk.CTkFrame(header, fg_color="transparent")
        btn_frame.pack(side="right")
        self.mk_btn(btn_frame, "🗑️", self.clear_text, "#c0392b", "Clear Text")
        self.mk_btn(btn_frame, "📂", self.load_file, COLORS['btn_surface'], "Load File")
        self.mk_btn(btn_frame, "💾", self.save_file, COLORS['btn_surface'], "Save File")
        self.mk_btn(btn_frame, "📋", self.paste_text, COLORS['btn_surface'], "Paste Clipboard")
        self.mk_btn(btn_frame, "📑", self.copy_text, COLORS['btn_surface'], "Copy to Clipboard")
        
        self.text_area = ctk.CTkTextbox(
            self, font=("Consolas", 12), undo=True,
            fg_color=COLORS['bg_main'], text_color=COLORS['fg_text'], corner_radius=6, border_width=1, border_color="#30363d"
        )
        self.text_area.pack(fill="both", expand=True, padx=0, pady=0)
        self.embedded_widget = None  # Track embedded widget
    
    def mk_btn(self, parent, txt, cmd, color, tip_text):
        btn = ctk.CTkButton(
            parent, text=txt, command=cmd, fg_color=color,
            hover_color=COLORS['btn_hover'], width=34, height=30,
            font=("Segoe UI", 15), corner_radius=6, border_width=1, border_color="#30363d"
        )
        btn.pack(side="left", padx=2)
        ToolTip(btn, tip_text)
    
    def get_text(self):
        return self.text_area.get("1.0", "end").strip()
    
    def set_text(self, text):
        """Set text in the text area, removing any embedded widget."""
        if self.embedded_widget:
            self.embedded_widget.destroy()
            self.embedded_widget = None
            self.text_area.pack(fill="both", expand=True, padx=0, pady=0)
        self.text_area.configure(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.insert("1.0", text)
        # Re-apply read-only if needed (for definition output)
        if hasattr(self, '_readonly') and self._readonly:
            self.text_area.bind("<Key>", self._prevent_editing)
    
    def embed_widget(self, widget):
        """Embed a widget in place of the text area."""
        if self.embedded_widget:
            self.embedded_widget.destroy()
        self.text_area.pack_forget()
        self.embedded_widget = widget
        widget.pack(fill="both", expand=True, padx=0, pady=0)
    
    def clear_text(self):
        self.text_area.delete("1.0", "end")
    
    def paste_text(self):
        try:
            self.text_area.insert("insert", self.clipboard_get())
        except:
            pass
    
    def copy_text(self):
        try:
            self.clipboard_clear()
            self.clipboard_append(self.get_text())
            self.update()
        except:
            pass
    
    def load_file(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(filetypes=self.file_type_def)
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self.set_text(f.read())
    
    def save_file(self):
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=self.file_type_def[0][1][1:],
            filetypes=self.file_type_def
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self.get_text())

