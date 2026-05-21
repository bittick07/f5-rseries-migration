#!/usr/bin/env python3
"""
edit_scf.py - F5 SCF Editor for iSeries to rSeries Migration

Reads environment variables set by Ansible:
  SCF_SOURCE      - Path to the source SCF file from iSeries
  SCF_OUTPUT      - Path to write the edited SCF file
  MGMT_IP         - Management IP to set on the rSeries tenant
  MGMT_PREFIX     - Management prefix length
  MGMT_GATEWAY    - Management gateway IP
  REMOVE_PATTERNS - Pipe-separated regex patterns for blocks to remove
"""

import os
import re
import sys


def edit_scf(input_file, output_file, mgmt_ip, mgmt_prefix, gateway,
             remove_patterns):

    print(f"[edit_scf] Reading source SCF: {input_file}")

    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    # ------------------------------------------------------------------
    # Fix Windows line endings (CRLF -> LF)
    # ------------------------------------------------------------------
    original_len = len(content)
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    if len(content) != original_len:
        print("[edit_scf] Fixed Windows line endings (CRLF -> LF)")

    lines = content.split('\n')
    output_lines = []
    skip_block = False
    brace_depth = 0
    removed_blocks = []
    current_block_name = ""
    in_mgmt_route = False

    compiled_patterns = [re.compile(p) for p in remove_patterns]

    print(f"[edit_scf] Processing {len(lines)} lines...")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ------------------------------------------------------------------
        # If we are inside a block being skipped, track brace depth
        # ------------------------------------------------------------------
        if skip_block:
            brace_depth += line.count('{') - line.count('}')
            if brace_depth <= 0:
                print(f"[edit_scf] Removed block: {current_block_name}")
                removed_blocks.append(current_block_name)
                skip_block = False
                brace_depth = 0
            i += 1
            continue

        # ------------------------------------------------------------------
        # Check if this line starts a block we want to remove
        # ------------------------------------------------------------------
        should_remove = any(p.search(stripped) for p in compiled_patterns)

        if should_remove:
            current_block_name = stripped[:80]
            if '{' in line:
                # Multi-line block - start skipping
                skip_block = True
                brace_depth = line.count('{') - line.count('}')
                if brace_depth <= 0:
                    # Single line block - already closed
                    skip_block = False
                    print(f"[edit_scf] Removed single line: {stripped[:80]}")
                    removed_blocks.append(stripped[:80])
            else:
                # Single line with no braces
                print(f"[edit_scf] Removed line: {stripped[:80]}")
                removed_blocks.append(stripped[:80])
            i += 1
            continue

        # ------------------------------------------------------------------
        # Update management IP
        # ------------------------------------------------------------------
        if re.match(r'sys management-ip\s+\S+\s*\{', stripped):
            line = f"sys management-ip {mgmt_ip}/{mgmt_prefix} {{ }}"
            print(f"[edit_scf] Updated management-ip to {mgmt_ip}/{mgmt_prefix}")

        # ------------------------------------------------------------------
        # Update management route/gateway
        # ------------------------------------------------------------------
        if re.match(r'sys management-route', stripped):
            in_mgmt_route = True

        if in_mgmt_route and re.match(r'gateway\s+', stripped):
            line = re.sub(r'gateway\s+\S+', f'gateway {gateway}', line)
            print(f"[edit_scf] Updated management gateway to {gateway}")
            in_mgmt_route = False

        output_lines.append(line)
        i += 1

    # ------------------------------------------------------------------
    # Write output file
    # ------------------------------------------------------------------
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))

    print(f"\n[edit_scf] Done. Written to: {output_file}")
    print(f"[edit_scf] Total blocks/lines removed: {len(removed_blocks)}")
    print("\n[edit_scf] Removed objects summary:")
    for block in removed_blocks:
        print(f"  - {block}")


if __name__ == "__main__":
    input_file  = os.environ.get('SCF_SOURCE')
    output_file = os.environ.get('SCF_OUTPUT')
    mgmt_ip     = os.environ.get('MGMT_IP')
    mgmt_prefix = os.environ.get('MGMT_PREFIX', '24')
    gateway     = os.environ.get('MGMT_GATEWAY')
    patterns_raw = os.environ.get('REMOVE_PATTERNS', '')

    # Validate required env vars
    missing = [v for v, k in [
        (input_file, 'SCF_SOURCE'),
        (output_file, 'SCF_OUTPUT'),
        (mgmt_ip, 'MGMT_IP'),
        (gateway, 'MGMT_GATEWAY'),
    ] if v is None]

    if missing:
        print(f"[edit_scf] ERROR: Missing environment variables: {missing}")
        sys.exit(1)

    if not os.path.exists(input_file):
        print(f"[edit_scf] ERROR: Source SCF file not found: {input_file}")
        sys.exit(1)

    remove_patterns = [p.strip() for p in patterns_raw.split('|') if p.strip()]

    edit_scf(
        input_file=input_file,
        output_file=output_file,
        mgmt_ip=mgmt_ip,
        mgmt_prefix=mgmt_prefix,
        gateway=gateway,
        remove_patterns=remove_patterns,
    )
