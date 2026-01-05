"""
Copyright 2025 Dominic Hawgood
STRICT BRIDGEZIP IMPLEMENTATION (v1.0.0) - UNIFIED MODERN PARSER
- Matches LLM Executor Logic exactly
- Uses efficient map() and regex parsing
- Enforces ComfyUI Version 0.4 (The Critical Fix)
"""

import json
import re
import urllib.parse

# ================================================================
# [1] TYPE MAPPING (STRICT v1.0.0)
# ================================================================
TYPE_SHORTHAND_MAP = {
    "MODEL": "M", "IMAGE": "G", "CONDITIONING": "C", "LATENT": "A",
    "VAE": "V", "CLIP": "P", "STRING": "S", "INT": "I", "FLOAT": "F",
    "BOOLEAN": "B", "MASK": "K", "CONTROL_NET": "T", "LIST": "L",
    "CLIP_VISION": "CV", "CLIP_VISION_OUTPUT": "CO", "VOXEL": "VX", "MESH": "MS",
    "*": "*"
}
REVERSE_TYPE_MAP = {v: k for k, v in TYPE_SHORTHAND_MAP.items()}

# ================================================================
# [2] HELPER UTILITIES
# ================================================================
def escape_widget_value(value):
    if value is True: return "True"
    if value is False: return "False"
    return str(value).replace("%", "%25").replace(";", "%3B").replace("\n", "%0A").replace("\r", "").replace("|", "%7C")

def unescape_widget_value(value):
    s = value.replace("%7C", "|").replace("%3B", ";").replace("%0A", "\n").replace("%25", "%")
    if s == "True": return True
    if s == "False": return False
    if s.isdigit(): return int(s)
    try: return float(s)
    except: return s

def encode_properties(props):
    try: return urllib.parse.quote(json.dumps(props, separators=(',', ':')))
    except: return ""

def decode_properties(prop_str):
    try: return json.loads(urllib.parse.unquote(prop_str))
    except: return {}

# ================================================================
# [3] PARSING HELPERS (The "Modern" Logic)
# ================================================================
def parse_node_line(line):
    # Robust Regex allowing empty fields (*)
    m = re.match(r"N(\d+):([^|]*)\|([^|]*)\|I:([^|]*)\|O:([^|]*)\|W:([^|]*)(.*)", line)
    if not m: return None
    nid, ntype, geo, instr, outstr, widstr, rest = m.groups()
    nid = int(nid)
    
    # Geometry Safety (Handles List/Dict mismatch)
    g = [int(x) for x in geo.split(',') if x.strip().lstrip('-').isdigit()]
    if len(g) >= 4: x, y, w, h = g[0], g[1], g[2], g[3]
    else: x, y, w, h = 0, 0, 300, 100
    
    node = {
        "id": nid, "type": ntype, "pos": [x, y], 
        "size": [w, h], # Force List Format
        "flags": {}, "order": nid, "mode": 0, 
        "properties": {"Node name for S&R": ntype}, "widgets_values": []
    }

    if rest:
        tags = rest.split('|')
        for tag in tags:
            if tag.startswith("C:"): 
                c = tag[2:].split(',')
                node["color"], node["bgcolor"] = c[0], (c[1] if len(c)>1 else "")
            elif tag.startswith("P:"): node["properties"] = decode_properties(tag[2:])
    
    if widstr: 
        parts = widstr.split(';')
        node["widgets_values"] = [unescape_widget_value(w) for w in parts]
    
    node["inputs"] = []
    if instr:
        for idx, i_str in enumerate(instr.split(',')):
            if not i_str: continue
            p = i_str.split(':')
            link_id = None
            if len(p) > 2 and p[2] and p[2] != 'None' and p[2].isdigit():
                link_id = int(p[2])
            node["inputs"].append({"name": p[0], "type": REVERSE_TYPE_MAP.get(p[1], p[1]), "link": link_id})

    node["outputs"] = []
    if outstr:
        for idx, o_str in enumerate(outstr.split(';')):
            if not o_str: continue
            p = o_str.split(':')
            links = []
            if len(p) > 2 and p[2]:
                links = [int(x) for x in p[2].split(',') if x.isdigit()]
            node["outputs"].append({"name": p[0], "type": REVERSE_TYPE_MAP.get(p[1], p[1]), "links": links, "slot_index": idx})
            
    return node

def parse_link_line(line):
    m = re.match(r"L(\d+)\s*:\s*(\d+)\.(\d+)\s*->\s*(\d+)\.(\d+)\s*:\s*(.+)", line)
    if m:
        lid, oid, oslot, tid, tslot = map(int, m.groups()[:5])
        return [lid, oid, oslot, tid, tslot, REVERSE_TYPE_MAP.get(m.group(6), m.group(6))]
    return None

# ================================================================
# [4] COMPRESSION
# ================================================================
def compress_workflow(data):
    try:
        if isinstance(data, str): wf = json.loads(data)
        else: wf = data

        head = f"W:{wf.get('id','none')}|r:{wf.get('revision',0)}|ln:{wf.get('last_node_id',0)}|ll:{wf.get('last_link_id',0)}|v:1.0.0"
        nodes = ["NODES:"]
        for n in wf.get("nodes", []):
            inps = []
            for i in n.get("inputs", []):
                t = i.get('type', "*")
                inps.append(f"{i['name']}:{TYPE_SHORTHAND_MAP.get(t, t)}:{i.get('link', 'None')}")

            outs = []
            for o in n.get("outputs", []):
                t = o.get('type', "*")
                links = [str(x) for x in (o.get('links') or []) if x is not None]
                outs.append(f"{o['name']}:{TYPE_SHORTHAND_MAP.get(t, t)}:{','.join(links)}")

            wids = ";".join([escape_widget_value(w) for w in n.get("widgets_values", [])])
            
            pos = n.get('pos', [0,0])
            sz = n.get('size', [300, 100])
            if isinstance(sz, dict): w, h = int(sz.get("0", 300)), int(sz.get("1", 100))
            else: w, h = int(sz[0]), int(sz[1])
            
            rest = ""
            if n.get("color"): rest += f"|C:{n['color']},{n.get('bgcolor','')}"
            if n.get("properties"): rest += f"|P:{encode_properties(n['properties'])}"
            
            nodes.append(f'N{n["id"]}:{n["type"]}|{int(pos[0])},{int(pos[1])},{w},{h}|I:{",".join(inps)}|O:{";".join(outs)}|W:{wids}{rest}')
        
        links = ["LINKS:"]
        for l in wf.get("links", []):
            links.append(f"L{l[0]}:{l[1]}.{l[2]}->{l[3]}.{l[4]}:{TYPE_SHORTHAND_MAP.get(l[5], l[5])}")
        
        meta = {"groups": wf.get("groups", []), "config": wf.get("config", {}), "extra": wf.get("extra", {})}
        return "\n".join([head] + nodes + links + ["M:" + json.dumps(meta, separators=(',', ':'))])
    except Exception as e: return f"Error: {e}"

# ================================================================
# [5] INFLATION (Modern Two-Pass Logic)
# ================================================================
def inflate_workflow(data):
    try:
        lines = [x.strip() for x in data.strip().split('\n') if x.strip()]
        if not lines: return "Error: Empty data"

        wf = {"nodes":[], "links":[], "groups":[], "config":{}, "extra":{}}

        # Header Check (Required for IDs, but safe fallbacks)
        if lines[0].startswith("W:"):
            header_line = lines.pop(0)
            try:
                h_parts = {p.split(':')[0]: p.split(':', 1)[1] for p in header_line.split('|')}
                wf.update({
                    "id": h_parts.get("W"), "revision": int(h_parts.get("r",0)), 
                    "last_node_id": int(h_parts.get("ln",0)), "last_link_id": int(h_parts.get("ll",0)), 
                    # [CRITICAL FIX] Restore standard ComfyUI version
                    "version": 0.4
                })
            except: 
                wf["version"] = 0.4
        else:
            wf["version"] = 0.4
        
        # Link Maps for Reconstruction
        node_inputs_fix = {} 
        node_outputs_fix = {} 
        
        # Section Parsing
        sect = None
        for line in lines:
            if line == "NODES:": sect = "nodes"; continue
            elif line == "LINKS:": sect = "links"; continue
            elif line.startswith("M:"):
                try: wf.update(json.loads(line[2:]))
                except: pass
                continue
            
            if sect == "nodes" and line.startswith('N'):
                # Pass 1: Parse Nodes (without links mostly)
                n = parse_node_line(line)
                if n: wf["nodes"].append(n)
            
            elif sect == "links" and line.startswith('L'):
                # Pass 2: Parse Links and build maps
                l = parse_link_line(line)
                if l: 
                    wf["links"].append(l)
                    # Map: [lid, oid, oslot, tid, tslot, type]
                    lid, oid, oslot, tid, tslot = l[0], l[1], l[2], l[3], l[4]
                    
                    if tid not in node_inputs_fix: node_inputs_fix[tid] = {}
                    node_inputs_fix[tid][tslot] = lid
                    
                    if oid not in node_outputs_fix: node_outputs_fix[oid] = {}
                    if oslot not in node_outputs_fix[oid]: node_outputs_fix[oid][oslot] = []
                    node_outputs_fix[oid][oslot].append(lid)

        # Pass 3: Re-attach Links to Nodes using the Maps
        for node in wf["nodes"]:
            nid = node['id']
            
            # Fix Inputs
            for idx, inp in enumerate(node.get("inputs", [])):
                if nid in node_inputs_fix and idx in node_inputs_fix[nid]:
                    inp['link'] = node_inputs_fix[nid][idx]
            
            # Fix Outputs
            for idx, out in enumerate(node.get("outputs", [])):
                if nid in node_outputs_fix and idx in node_outputs_fix[nid]:
                    out['links'] = node_outputs_fix[nid][idx]

        return json.dumps(wf, indent=2)
    except Exception as e: return f"Error: {e}"

# ================================================================
# [6] FRAGMENT PARSING (For Task Envelope add_nodes_str)
# ================================================================
def inflate_fragment(text):
    """Parse BridgeZip fragment (nodes + links) without full workflow structure."""
    nodes, links = [], []
    for line in text.strip().split('\n'):
        line = line.strip()
        if line.startswith("N"): 
            n = parse_node_line(line)
            if n: nodes.append(n)
        elif line.startswith("L"): 
            l = parse_link_line(line)
            if l: links.append(l)
    return {"nodes": nodes, "links": links}

# ================================================================
# [7] CONNECTION REPAIR (Synchronize Links, Inputs, Outputs)
# ================================================================
def repair_connections(wf):
    """Ensures Link Objects, Node Inputs, and Node Outputs are synchronized."""
    link_map = {l[0]: l for l in wf['links']}
    target_map = {f"{l[3]}:{l[4]}": l[0] for l in wf['links']}
    node_map = {n['id']: n for n in wf['nodes']}

    # Repair Inputs
    for node in wf['nodes']:
        nid = node['id']
        for idx, inp in enumerate(node.get("inputs", [])):
            key = f"{nid}:{idx}"
            if key in target_map: inp['link'] = target_map[key]
            elif inp.get('link') is not None and inp['link'] not in link_map: inp['link'] = None

    # Repair Outputs
    for node in wf['nodes']:
        for out in node.get('outputs', []): out['links'] = []

    for l in wf['links']:
        link_id, src_id, src_slot = l[0], l[1], l[2]
        if src_id in node_map:
            n = node_map[src_id]
            if 'outputs' in n and len(n['outputs']) > src_slot:
                if n['outputs'][src_slot].get('links') is None: n['outputs'][src_slot]['links'] = []
                n['outputs'][src_slot]['links'].append(link_id)

# ================================================================
# [8] TASK ENVELOPE EXECUTION (Apply Modifications)
# ================================================================
def apply_modifications(workflow_str, add_nodes_str="", delete_node_ids=None):
    """
    Apply Task Envelope modifications to a BridgeZip workflow.
    
    Args:
        workflow_str: Current workflow in BridgeZip format
        add_nodes_str: BridgeZip fragment with nodes/links to add (may contain NODE_X/LINK_X placeholders)
        delete_node_ids: List of node IDs to delete
    
    Returns:
        Updated BridgeZip string or error message
    """
    if delete_node_ids is None: delete_node_ids = []
    
    # 1. Inflate current workflow
    inflated = inflate_workflow(workflow_str)
    if isinstance(inflated, str) and inflated.startswith("Error"):
        return inflated
    
    try:
        wf = json.loads(inflated) if isinstance(inflated, str) else inflated
    except Exception as e:
        return f"Error: Failed to parse workflow JSON: {e}"
    
    if "error" in wf:
        return f"Error: {wf['error']}"
    
    # 2. Delete nodes and their links
    if delete_node_ids:
        wf['nodes'] = [n for n in wf['nodes'] if n['id'] not in delete_node_ids]
        wf['links'] = [l for l in wf['links'] if l[1] not in delete_node_ids and l[3] not in delete_node_ids]

    # 3. Add nodes from fragment (with ID resolution for NODE_X/LINK_X placeholders)
    if add_nodes_str:
        existing_node_ids = {n['id'] for n in wf['nodes']}
        existing_link_ids = {l[0] for l in wf['links']}
        next_node_id = max(existing_node_ids, default=0) + 1
        next_link_id = max(existing_link_ids, default=0) + 1
        
        id_map = {}
        def resolve_id(token, is_link=False):
            nonlocal next_node_id, next_link_id
            if token not in id_map:
                if is_link: id_map[token] = next_link_id; next_link_id += 1
                else: id_map[token] = next_node_id; next_node_id += 1
            return id_map[token]

        def replace_match(match):
            prefix = match.group(1); suffix = match.group(2)
            token = prefix + suffix
            return str(resolve_id(token, is_link=(prefix == 'LINK')))

        # Replace NODE_X and LINK_X placeholders with real IDs
        fixed_str = re.sub(r'(NODE|LINK)_(\d+)', replace_match, add_nodes_str)
        
        # FIX: Normalize multiple L prefixes to single L (handles LL500 -> L500)
        fixed_str = re.sub(r'^L+([0-9]+)', r'L\1', fixed_str, flags=re.MULTILINE)
        
        fragment = inflate_fragment(fixed_str)
        
        # Merge fragment nodes and links into workflow
        for n in fragment['nodes']:
            if n['id'] in existing_node_ids: wf['nodes'] = [x for x in wf['nodes'] if x['id'] != n['id']]
            wf['nodes'].append(n)
        for l in fragment['links']:
            if l[0] in existing_link_ids: wf['links'] = [x for x in wf['links'] if x[0] != l[0]]
            wf['links'].append(l)

    # 4. Repair connections and update IDs
    repair_connections(wf)
    wf['last_node_id'] = max((n['id'] for n in wf['nodes']), default=0)
    wf['last_link_id'] = max((l[0] for l in wf['links']), default=0)
    
    # 5. Compress back to BridgeZip
    return compress_workflow(wf)