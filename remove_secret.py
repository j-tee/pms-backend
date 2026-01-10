#!/usr/bin/env python3
"""
Git filter script to remove hardcoded SECRET_KEY from repository history.
This script replaces the hardcoded Django secret with a placeholder.
"""

import re
import sys

# The insecure key to find and replace
OLD_SECRET = r"django-insecure-\$sndye\)!a@mj0pz6@=z78-\+@b\^x7\^\$@amxmnf%s2z8fq=_\+7@3"
NEW_SECRET = "your-secret-key-here-generate-a-new-one"

def replace_secret(filename):
    """Replace hardcoded SECRET_KEY in the given file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Only process if it contains the old secret
        if 'django-insecure-$sndye)!a@mj0pz6@=z78-+@b^x7^$@amxmnf%s2z8fq=_+7@3' in content:
            # Replace the hardcoded secret
            new_content = content.replace(
                "'django-insecure-$sndye)!a@mj0pz6@=z78-+@b^x7^$@amxmnf%s2z8fq=_+7@3'",
                f"'{NEW_SECRET}'"
            )
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return True
        return False
    except Exception as e:
        print(f"Error processing {filename}: {e}", file=sys.stderr)
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        for filename in sys.argv[1:]:
            if replace_secret(filename):
                print(f"Replaced secret in: {filename}")
