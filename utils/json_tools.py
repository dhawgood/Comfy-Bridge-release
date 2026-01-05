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

def beautify_json(data):
    """Format JSON with indentation."""
    try:
        return json.dumps(json.loads(data), indent=2)
    except Exception as e:
        return f"Error: {e}"

def minify_json(data):
    """Minify JSON by removing whitespace."""
    try:
        return json.dumps(json.loads(data), separators=(',', ':'))
    except Exception as e:
        return f"Error: {e}"









