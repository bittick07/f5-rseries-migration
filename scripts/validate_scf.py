#!/usr/bin/env python3
"""
validate_scf.py - Basic pre-flight validation of an edited SCF file

Checks for:
  - File exists and is not empty
  - No Windows line endings remaining
  - No unmatched braces
  - No known problematic iSeries-specific keywords still present
  - No lines exceeding 4096 characters (BIG-IP parser limit)

Environment variables:
  SCF_FILE - Path to the SCF file to validate
"""

import os
import re
import sys


KNOWN_PROBLEMS = [
    (r'turboflex',          "TurboFlex config (iSeries only)"),
    (r'epsec',              "APM EPSEC package (APM not provisioned)"),
    (r'data-publisher',     "Data publisher (APM remnant)"),
    (r'\bnet trunk\b',      "net trunk (should be at F5OS layer)"),
    (r'\bnet stp\b',        "net stp (should be at F5OS layer)"),
    (r'\bnet fdb\b',        "net fdb tunnel (iSeries hardware specific)"),
    (r'cm device ',         "cm device object (iSeries hardware specific)"),
    (r'dtca|dtos|dtdi',     "Device trust cert/key (old HA pair)"),
    (r'lacp enabled',       "LACP enabled (not supported on rSeries tenant)"),
    (r'platform-id\s+C',    "iSeries platform ID (C-series hardware reference)"),
]


def validate_scf(scf_file):
    errors = []
    warnings = []

    # ------------------------------------------------------------------
    # File exists and not empty
    # ------------------------------------------------------------------
    if not os.path.exists(scf_file):
        print(f"[validate] ERROR: File not found: {scf_file}")
        sys.exit(1)

    file_size = os.path.getsize(scf_file)
    if file_size == 0:
        errors.append("File is empty")
    else:
        print(f"[validate] File size: {file_size} bytes")

    with open(scf_file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    lines = content.split('\n')
    print(f"[validate] Total lines: {len(lines)}")

    # ------------------------------------------------------------------
    # Windows line endings
    # ------------------------------------------------------------------
    if '\r' in content:
        errors.append("Windows line endings (CRLF) still present - run dos2unix or edit_scf.py")

    # ------------------------------------------------------------------
    # Line length check (BIG-IP parser limit is 4096 chars)
    # ------------------------------------------------------------------
    long_lines = [(i+1, len(l)) for i, l in enumerate(lines) if len(l) > 4096]
    for lineno, length in long_lines:
        errors.append(f"Line {lineno} exceeds 4096 characters ({length} chars)")

    # ------------------------------------------------------------------
    # Brace matching
    # ------------------------------------------------------------------
    open_braces = content.count('{')
    close_braces = content.count('}')
    if open_braces != close_braces:
        errors.append(
            f"Unmatched braces: {open_braces} opening vs {close_braces} closing. "
            f"Check for incomplete block deletions."
        )
    else:
        print(f"[validate] Braces balanced: {open_braces} open / {close_braces} close")

    # ------------------------------------------------------------------
    # Known problematic keywords
    # ------------------------------------------------------------------
    for pattern, description in KNOWN_PROBLEMS:
        matches = [(i+1, l.strip()) for i, l in enumerate(lines)
                   if re.search(pattern, l, re.IGNORECASE)]
        if matches:
            for lineno, line_content in matches:
                warnings.append(
                    f"Line {lineno}: Possible issue - {description}\n"
                    f"           Content: {line_content[:100]}"
                )

    # ------------------------------------------------------------------
    # Print results
    # ------------------------------------------------------------------
    print("\n" + "="*60)
    print("SCF VALIDATION RESULTS")
    print("="*60)

    if warnings:
        print(f"\n⚠  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  {w}")

    if errors:
        print(f"\n✗  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")
        print("\n[validate] Validation FAILED - fix errors before loading SCF")
        sys.exit(1)
    else:
        print("\n✓  No errors found.")
        if warnings:
            print("   Review warnings above before proceeding.")
        print("\n[validate] Validation PASSED")


if __name__ == "__main__":
    scf_file = os.environ.get('SCF_FILE')
    if not scf_file:
        print("[validate] ERROR: SCF_FILE environment variable not set")
        sys.exit(1)

    validate_scf(scf_file)
