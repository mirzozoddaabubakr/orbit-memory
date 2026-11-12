"""Shared transcript masking rules, also consumed by the extension's offline queue."""
import json
import re
from pathlib import Path

rules = []
for name, pattern, *flags in json.loads((Path(__file__).parent/"extension"/"secret-patterns.json").read_text()):
    options = "".join(flags)
    rules.append((name,re.compile(pattern,(re.I if "i" in options else 0)|(re.M if "m" in options else 0))))

def mask(text):
    for name,pattern in rules:
        def replace(match):
            prefix = match.group(1) if pattern.groups else ""
            return prefix + "<redacted:" + name.replace(" ","-") + ">"
        text = pattern.sub(replace,text)
    return text

def safe_object(value):
    if isinstance(value,str):
        return mask(value)
    if isinstance(value,list):
        return [safe_object(item) for item in value]
    if isinstance(value,dict):
        return {k:safe_object(v) for k,v in value.items()}
    return value
