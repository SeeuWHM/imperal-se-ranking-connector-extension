#!/usr/bin/env python3
"""Post-build fixup: SDK 5.7-5.9's ext.secret().to_manifest_dict() emits
'scope' and 'env_fallback' keys that the M3 manifest validator's
SecretDecl model rejects (extra="forbid") -- a real upstream SDK bug,
reproducible on every extension that declares secrets (verified against
matomo-analytics-extension too). Run this after every `imperal build .`
until the SDK fixes the emitter/validator mismatch.
"""
import json
import sys

path = "imperal.json"
with open(path) as f:
    d = json.load(f)

changed = False
for s in d.get("secrets", []) or []:
    for bad_key in ("scope", "env_fallback"):
        if s.pop(bad_key, None) is not None:
            changed = True

if changed:
    with open(path, "w") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print("stripped incompatible secrets.*.scope/env_fallback fields from imperal.json")
else:
    print("no incompatible fields found — nothing to strip")
