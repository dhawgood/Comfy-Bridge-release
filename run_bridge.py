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
import ctypes
from engine import __version__
from ui.main_window import ComfyBridgeApp
from utils.logger import logger

if __name__ == "__main__":
    # --- Fix: Tell Windows this is a unique app (prevents Python icon in taskbar) ---
    myappid = 'dominichawgood.comfybridge.1.2.1'
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass  # Silently fail if not Windows or if API call fails
    
    # Set appearance mode
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
    
    # Log startup
    logger.info(f"Comfy Bridge v{__version__} starting...")
    logger.info("Copyright 2025 Dominic Hawgood - Licensed under Apache 2.0")
    
    # Create and run app
    try:
        app = ComfyBridgeApp()
        logger.info("Application initialized successfully")
        app.mainloop()
    except Exception as e:
        logger.error(f"Error starting application: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")









