#!/usr/bin/env python3
"""
Callback script for git-filter-repo to remove hardcoded SECRET_KEY.
Usage: git filter-repo --blob-callback /path/to/this/script
"""

import sys

# Read the blob data
blob = sys.stdin.buffer.read()

# Define the old secret to replace
OLD_SECRET = b"django-insecure-$sndye)!a@mj0pz6@=z78-+@b^x7^$@amxmnf%s2z8fq=_+7@3"
NEW_SECRET = b"your-secret-key-here-generate-a-new-one"

# Replace if found
if OLD_SECRET in blob:
    blob = blob.replace(OLD_SECRET, NEW_SECRET)

# Write the modified blob back
sys.stdout.buffer.write(blob)
