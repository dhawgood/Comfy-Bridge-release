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
from utils.config import get_comfyui_url

def collect_models_hierarchical(data_source="live", file_path=None):
    """Collect models and organize them hierarchically by type -> category -> models."""
    if data_source == "live":
        from logic.filtering import _get_live_object_info
        data = _get_live_object_info()
        if not data:
            base_url = get_comfyui_url()
            return None, f"Error connecting to ComfyUI ({base_url}). Ensure it is running."
        node_defs = data.get("node_definitions", data)
    else:  # file mode
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            node_defs = data.get("node_definitions", data)
        except Exception as e:
            return None, f"Error reading file: {e}"
    
    # Organize models hierarchically
    organized = {
        "CHECKPOINTS": {},
        "LORAS": {},
        "VAES": {},
        "UNETS": {},
        "CLIPS": {}
    }
    
    for node_name, info in node_defs.items():
        if not isinstance(info, dict):
            continue
        
        inputs = info.get("input", {}).get("required", {})
        
        # Helper to categorize and add model
        def add_model(model_type, model_name):
            if not model_name or model_name == "None" or model_name.strip() == "":
                return
            # Extract category (folder prefix before first backslash)
            if '\\' in model_name:
                category = model_name.split('\\')[0]
            elif '/' in model_name:
                category = model_name.split('/')[0]
            else:
                category = "Other"
            
            if category not in organized[model_type]:
                organized[model_type][category] = []
            if model_name not in organized[model_type][category]:
                organized[model_type][category].append(model_name)
        
        # Checkpoints
        if "ckpt_name" in inputs:
            items = inputs["ckpt_name"][0]
            if isinstance(items, list):
                for item in items:
                    add_model("CHECKPOINTS", item)
        
        # LoRAs
        if "lora_name" in inputs:
            items = inputs["lora_name"][0]
            if isinstance(items, list):
                for item in items:
                    add_model("LORAS", item)
        
        # VAEs
        if "vae_name" in inputs:
            items = inputs["vae_name"][0]
            if isinstance(items, list):
                for item in items:
                    add_model("VAES", item)
        
        # UNETs
        if "unet_name" in inputs:
            items = inputs["unet_name"][0]
            if isinstance(items, list):
                for item in items:
                    add_model("UNETS", item)
        
        # CLIPs
        for key in inputs:
            if "clip_name" in key:
                items = inputs[key][0]
                if isinstance(items, list):
                    for item in items:
                        add_model("CLIPS", item)
    
    # Sort categories and models within each type
    for model_type in organized:
        # Sort categories
        organized[model_type] = dict(sorted(organized[model_type].items(), key=lambda x: x[0].lower()))
        # Sort models within each category
        for category in organized[model_type]:
            organized[model_type][category].sort(key=str.lower)
    
    return organized, None

def extract_models_logic_live():
    """Extract model lists (checkpoints, LoRAs, VAEs, etc.) from live ComfyUI."""
    from logic.filtering import _get_live_object_info
    
    data = _get_live_object_info()
    if not data:
        base_url = get_comfyui_url()
        return f"Error connecting to ComfyUI ({base_url}). Ensure it is running."
    
    node_defs = data.get("node_definitions", data)
    models = set()
    loras = set()
    vaes = set()
    unets = set()
    clips = set()

    for node_name, info in node_defs.items():
        if not isinstance(info, dict):
            continue
        
        inputs = info.get("input", {}).get("required", {})
        if "ckpt_name" in inputs:
            items = inputs["ckpt_name"][0]
            if isinstance(items, list):
                models.update(items)
        if "lora_name" in inputs:
            items = inputs["lora_name"][0]
            if isinstance(items, list):
                loras.update(items)
        if "vae_name" in inputs:
            items = inputs["vae_name"][0]
            if isinstance(items, list):
                vaes.update(items)
        if "unet_name" in inputs:
            items = inputs["unet_name"][0]
            if isinstance(items, list):
                unets.update(items)
        for key in inputs:
            if "clip_name" in key:
                items = inputs[key][0]
                if isinstance(items, list):
                    clips.update(items)

    res = "=== USER MODEL INDEX ===\n"
    res += f"\n[CHECKPOINTS ({len(models)})]\n" + "\n".join(sorted(list(models)))
    res += f"\n\n[UNETS ({len(unets)})]\n" + "\n".join(sorted(list(unets)))
    res += f"\n\n[LORAS ({len(loras)})]\n" + "\n".join(sorted(list(loras)))
    res += f"\n\n[VAES ({len(vaes)})]\n" + "\n".join(sorted(list(vaes)))
    res += f"\n\n[CLIPS ({len(clips)})]\n" + "\n".join(sorted(list(clips)))
    return res

def extract_categories_logic(file_path):
    """Extract pack categories from object_info.json."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        cats = set()
        for n in data.values():
            if not isinstance(n, dict):
                continue
            raw = n.get("category", "Unknown")
            cat_str = str(raw[0]) if isinstance(raw, list) and raw else str(raw)
            root_cat = cat_str.split('/')[0]
            # Filter out internal/system categories (__hidden__, _for_testing, etc.)
            if not root_cat.startswith('__') and not root_cat.startswith('_'):
                cats.add(root_cat)
        return "INSTALLED PACKS:\n----------------\n" + "\n".join(sorted(list(cats), key=str.lower))
    except Exception as e:
        return f"Error parsing categories: {e}"

def extract_models_logic(file_path):
    """Extract model lists (checkpoints, LoRAs, VAEs, etc.) from object_info.json."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        models = set()
        loras = set()
        vaes = set()
        unets = set()
        clips = set()

        for node_name, info in data.items():
            if not isinstance(info, dict):
                continue
            
            inputs = info.get("input", {}).get("required", {})
            if "ckpt_name" in inputs:
                items = inputs["ckpt_name"][0]
                if isinstance(items, list):
                    models.update(items)
            if "lora_name" in inputs:
                items = inputs["lora_name"][0]
                if isinstance(items, list):
                    loras.update(items)
            if "vae_name" in inputs:
                items = inputs["vae_name"][0]
                if isinstance(items, list):
                    vaes.update(items)
            if "unet_name" in inputs:
                items = inputs["unet_name"][0]
                if isinstance(items, list):
                    unets.update(items)
            for key in inputs:
                if "clip_name" in key:
                    items = inputs[key][0]
                    if isinstance(items, list):
                        clips.update(items)

        res = "=== USER MODEL INDEX ===\n"
        res += f"\n[CHECKPOINTS ({len(models)})]\n" + "\n".join(sorted(list(models)))
        res += f"\n\n[UNETS ({len(unets)})]\n" + "\n".join(sorted(list(unets)))
        res += f"\n\n[LORAS ({len(loras)})]\n" + "\n".join(sorted(list(loras)))
        res += f"\n\n[VAES ({len(vaes)})]\n" + "\n".join(sorted(list(vaes)))
        res += f"\n\n[CLIPS ({len(clips)})]\n" + "\n".join(sorted(list(clips)))
        return res
    except Exception as e:
        return f"Error extracting models: {e}"

def collect_groups_from_workflow(json_data):
    """Collect all groups from workflow JSON with metadata."""
    try:
        if not json_data or not json_data.strip():
            return None, "Error: No workflow data provided."
        
        wf = json.loads(json_data)
        groups = wf.get("groups", [])
        
        if not groups:
            return [], None
        
        groups_list = []
        for g in groups:
            title = g.get("title", "Untitled")
            group_id = g.get("id", "?")
            b = g.get("bounding", [])
            
            # Count nodes in this group
            node_count = 0
            if len(b) >= 4:
                gx, gy, gw, gh = b[0], b[1], b[2], b[3]
                for n in wf.get("nodes", []):
                    pos = n.get("pos", [0, 0])
                    nx, ny = pos[0], pos[1]
                    if gx <= nx <= (gx + gw) and gy <= ny <= (gy + gh):
                        node_count += 1
            
            groups_list.append({
                "title": title,
                "id": group_id,
                "bounding": b,
                "node_count": node_count
            })
        
        return groups_list, None
    except Exception as e:
        return None, f"Error processing workflow: {e}"

def extract_group_nodes_logic(json_data, group_names):
    """Extract nodes within one or more groups from workflow JSON."""
    try:
        if not json_data or not json_data.strip():
            return "Error: No workflow data provided."
            
        wf = json.loads(json_data)
        groups = wf.get("groups", [])
        
        if isinstance(group_names, str):
            group_names = [group_names]
        
        out_lines = []
        total_nodes = 0
        
        for group_name in group_names:
            target_group = None
            for g in groups:
                if g.get("title", "").lower() == group_name.lower():
                    target_group = g
                    break
            
            if not target_group:
                out_lines.append(f"⚠ Group '{group_name}' not found in workflow.\n")
                continue

            b = target_group.get("bounding", [])
            if len(b) < 4:
                out_lines.append(f"⚠ Group '{group_name}' has invalid bounding data.\n")
                continue
                
            gx, gy, gw, gh = b[0], b[1], b[2], b[3]
            
            found_nodes = []
            for n in wf.get("nodes", []):
                pos = n.get("pos", [0, 0])
                nx, ny = pos[0], pos[1]
                if gx <= nx <= (gx + gw) and gy <= ny <= (gy + gh):
                    found_nodes.append(n)
            
            if not found_nodes:
                out_lines.append(f"⚠ No nodes found inside group '{group_name}'.\n")
                continue
                
            found_nodes.sort(key=lambda x: int(x.get("id", 0)))
            total_nodes += len(found_nodes)
            
            # Group header
            out_lines.append("=" * 60)
            out_lines.append(f"GROUP: {target_group.get('title', 'Unknown')}")
            out_lines.append(f"ID: {target_group.get('id', 'Unknown')}")
            out_lines.append(f"Bounding Box: [{int(gx)}, {int(gy)}] → [{int(gw)}, {int(gh)}]")
            out_lines.append(f"Nodes: {len(found_nodes)}")
            out_lines.append("=" * 60)
            out_lines.append("")
            
            # Node details
            for n in found_nodes:
                node_id = n.get("id", "?")
                node_type = n.get("type", "Unknown")
                
                widgets = n.get("widgets_values", [])
                w_str_list = []
                for w in widgets:
                    val = str(w)
                    if len(val) > 50:
                        val = val[:47] + "..."
                    w_str_list.append(val)
                w_str = ", ".join(w_str_list) if w_str_list else "(no widgets)"
                
                inps = []
                for i in n.get("inputs", []):
                    inps.append(f"{i['name']}({i.get('type', '*')})")
                
                outs = []
                for o in n.get("outputs", []):
                    outs.append(f"{o['name']}({o.get('type', '*')})")
                
                out_lines.append(f"  N{node_id}: {node_type}")
                if w_str != "(no widgets)":
                    out_lines.append(f"    Widgets: {w_str}")
                if inps:
                    out_lines.append(f"    Inputs: {{ {', '.join(inps)} }}")
                if outs:
                    out_lines.append(f"    Outputs: {{ {', '.join(outs)} }}")
                out_lines.append("")
        
        if not out_lines:
            return "No groups selected or found."
        
        # Add summary at top
        summary = f"=== EXTRACTED GROUPS ({len(group_names)} group(s), {total_nodes} total nodes) ===\n\n"
        return summary + "\n".join(out_lines)
        
    except Exception as e:
        return f"Error processing group: {e}"

def extract_nodes_from_bridgezip(bridgezip_data, node_ids_str=""):
    """Extract specific nodes from BridgeZip data by ID or node type name."""
    if not bridgezip_data.startswith("W:"): 
        return "Error: Invalid BridgeZip format. Must start with 'W:'"

    raw_input = node_ids_str.strip()
    if not raw_input:
        return bridgezip_data

    try:
        # Parse input: separate numeric IDs from text names (node types)
        parts = re.split(r'[,+\s]+', raw_input)
        target_ids = []
        target_names = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            # Check if it's a number
            if part.isdigit():
                target_ids.append(int(part))
            else:
                # It's a node type name (case-insensitive)
                target_names.append(part.lower())
        
        if not target_ids and not target_names:
            return "No valid node IDs or names found in filter."
        
        lines = bridgezip_data.strip().split('\n')
        output = []
        matched_node_ids = set()  # Track which node IDs matched (for link filtering)

        for line in lines:
            if line.startswith("W:"):
                output.append(line)
            elif line.startswith("M:"):
                # Always include metadata line
                output.append(line)
            elif line.startswith("N"):
                # Parse: N{id}:{type}|...
                m = re.match(r"N(\d+):([^|]+)", line)
                if m:
                    node_id = int(m.group(1))
                    node_type = m.group(2)
                    
                    # Match by ID or by type name (case-insensitive)
                    match_by_id = node_id in target_ids
                    match_by_name = node_type.lower() in target_names
                    
                    if match_by_id or match_by_name:
                        output.append(line)
                        matched_node_ids.add(node_id)
            elif line.startswith("L"):
                # Include links if either source or target node was matched
                m = re.match(r"L\d+:(\d+)\.\d+->(\d+)\.\d+:", line)
                if m:
                    src_id = int(m.group(1))
                    tgt_id = int(m.group(2))
                    if src_id in matched_node_ids or tgt_id in matched_node_ids:
                        output.append(line)
        
        res = "\n".join(output) if len(output) > 1 else "No matching nodes found."
        return res
    except Exception as e:
        return f"Error: {e}"

