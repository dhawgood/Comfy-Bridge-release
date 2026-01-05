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

import json
import re
import time
import urllib.request
from engine.bridgezip import TYPE_SHORTHAND_MAP
from utils.config import get_comfyui_url

# Global Cache for Live Node Data
_OBJECT_INFO_CACHE = None
_LAST_CACHE_TIME = 0
_CACHE_DURATION = 60  # seconds

def _get_live_object_info():
    """Fetch object_info from ComfyUI or return cached version."""
    global _OBJECT_INFO_CACHE, _LAST_CACHE_TIME
    base_url = get_comfyui_url()
    url = f"{base_url}/object_info"
    current_time = time.time()

    if _OBJECT_INFO_CACHE is None or (current_time - _LAST_CACHE_TIME > _CACHE_DURATION):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    return None
                _OBJECT_INFO_CACHE = json.loads(response.read().decode('utf-8'))
                _LAST_CACHE_TIME = current_time
        except:
            return None
    return _OBJECT_INFO_CACHE

def fetch_live_categories():
    """
    Fetch list of installed packs (categories) from live ComfyUI.
    Returns a formatted string of unique root categories.
    """
    data = _get_live_object_info()
    if not data:
        return "Error: Could not connect to ComfyUI."
    
    node_defs = data.get("node_definitions", data)
    cats = set()
    
    for n in node_defs.values():
        if not isinstance(n, dict): continue
        raw = n.get("category", "Unknown")
        cat_str = str(raw[0]) if isinstance(raw, list) and raw else str(raw)
        # Get root category (before the first slash)
        root_cat = cat_str.split('/')[0]
        # Filter out internal/system categories (__hidden__, _for_testing, etc.)
        if not root_cat.startswith('__') and not root_cat.startswith('_'):
            cats.add(root_cat)
        
    return "INSTALLED PACKS:\n----------------\n" + "\n".join(sorted(list(cats), key=str.lower))

def fetch_live_node_meta(search_query, allowed_fields=None):
    """
    Fetches node metadata from live ComfyUI.
    """
    data = _get_live_object_info()
    if not data:
        base_url = get_comfyui_url()
        return f"Error connecting to ComfyUI ({base_url}). Ensure it is running."

    node_defs = data.get("node_definitions", data)
    
    # 2. Parse Search Terms (empty query = all nodes)
    search_query = search_query.strip() if search_query else ""
    search_terms = [t for t in re.split(r'[,+\s]+', search_query) if t] if search_query else []
    
    # 3. Get nodes (all or filtered)
    if not search_terms:
        # Empty filter = return all nodes
        unique_nodes = node_defs
    else:
        # Filter by search terms
        found_nodes = []
        
        for term in search_terms:
            term_lower = term.lower()
            term_matches = []
            
            # Priority 1: Exact Match
            if term in node_defs:
                term_matches.append((term, node_defs[term]))
            else:
                # Priority 2: Case-insensitive Match
                for k, v in node_defs.items():
                    if k.lower() == term_lower:
                        term_matches.append((k, v))
                        break 
                
                # Priority 3: Substring Match (only if no exact match found)
                if not term_matches:
                    for k, v in node_defs.items():
                        if term_lower in k.lower():
                            term_matches.append((k, v))
            
            found_nodes.extend(term_matches)

        if not found_nodes:
            return f"No nodes found matching: {', '.join(search_terms)}"

        # Deduplicate based on node name
        unique_nodes = {}
        for name, data in found_nodes:
            unique_nodes[name] = data
    
    # 4. Synthesize & Filter
    results = []
    for name, raw_def in unique_nodes.items():
        # Copy to avoid modifying cache
        node = raw_def.copy()
        
        # -- SYNTHESIZE WIDGETS_VALUES --
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

        # Inject Defaults
        node["widgets_values"] = w_values
        if "rect" not in node: node["rect"] = {"w": 300, "h": 100}
        if "ver" not in node: node["ver"] = "0.0.0 (Live)"
        if "cnr_id" not in node: node["cnr_id"] = "unknown_pack"
        if "properties" not in node: node["properties"] = {"Node name for S&R": name}
        if "class_name" not in node: node["class_name"] = name

        # -- FILTER FIELDS --
        if allowed_fields and len(allowed_fields) > 0:
            filtered_node = {k: v for k, v in node.items() if k in allowed_fields}
            results.append(json.dumps(filtered_node, indent=2))
        else:
            results.append(json.dumps(node, indent=2))

    return "\n\n".join(results)

def compress_nodes_v4_logic(file_path, search_query=""):
    """Compress node definitions into signature format."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            nodes_data = json.load(f)
        result = []
        terms = [t.strip().lower() for t in search_query.split(',')] if search_query else []
        
        for node_name, node_info in nodes_data.items():
            if not isinstance(node_info, dict):
                continue

            if terms:
                cat_raw = node_info.get("category", "")
                cat_str = str(cat_raw[0]) if isinstance(cat_raw, list) and cat_raw else str(cat_raw)
                if not (any(q in node_name.lower() for q in terms) or any(q in cat_str.lower() for q in terms)):
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
        return "\n".join(result) if result else "No nodes found."
    except Exception as e:
        return f"Error: {e}"
