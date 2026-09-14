#!/usr/bin/env python3
"""
CrystalPilot Build Script
Assembles the split source files back into a single distributable .py file.

Usage:
    python3 build.py                    # builds xds-gui.py
    python3 build.py --output NAME.py   # builds to a specific filename
    python3 build.py --verify ORIG.py   # builds and compares against original

The output is a single self-contained Python file identical in behavior
to the monolithic version. Users run it with: python3 xds-gui.py
"""

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(SCRIPT_DIR, 'src')

# Source files in assembly order.
# Each entry: (filename, extra_blank_before)
# extra_blank_before: whether to insert a blank line before this section
# (to match the original file's formatting exactly)
SOURCE_FILES = [
    ('config.py',    False),
    ('project.py',   True),    # extra blank line before (original line 162)
    ('parsers.py',   True),    # extra blank line before (original line 245)
    ('jobs.py',      False),   # job reservations and process lifecycle
    ('runner.py',    False),
    ('helpers.py',   False),
    ('figures.py',   False),   # publication figures (matplotlib PNGs from a shell table)
    ('batch.py',     False),   # batch processing: discovery, strategy, queue, merge
    ('assets.py',    False),   # static image assets (logo, background)
    ('ahkl2mtz.py',  False),   # gemmi-based XDS→MTZ conversion (intensity-only)
    ('handler.py',   False),
    ('editor.py',    False),   # XDSINPEditor
    ('imaging.py',   False),   # ImageHeaderReader
    ('generator.py', False),   # XDSINPGenerator + _xscale_apply_params
    # frontend.html is embedded via get_frontend_html() — handled specially
    # main.py goes last
    ('main.py',      False),
]

FRONTEND_FILE = 'frontend.html'


def read_file(path):
    """Read a file and return its content."""
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def escape_html_for_python(html):
    """
    Escape an HTML string for embedding inside a Python '''...''' literal.
    
    The HTML file contains actual UTF-8 characters and single-level backslashes.
    When embedded in a Python triple-quoted string:
    - Backslashes need to be doubled (so Python un-escapes them back)
    - Unicode characters can stay as UTF-8 (Python handles this fine in ''')
    - No triple-quote sequences should exist in the HTML (verified during extraction)
    """
    # The only transformation needed: \ -> \\
    # This ensures Python's string parser un-escapes them back to single backslashes
    # which is what the browser needs to receive.
    escaped = html.replace('\\', '\\\\')
    return escaped


def build_frontend_function(html_content):
    """Build the get_frontend_html() function with embedded HTML."""
    escaped = escape_html_for_python(html_content)
    return "def get_frontend_html():\n    \"\"\"Return embedded frontend HTML\"\"\"\n    return '''" + escaped + "'''\n"


def assemble(output_path=None, verify_against=None):
    """Assemble all source files into a single .py file."""
    
    if output_path is None:
        output_path = os.path.join(SCRIPT_DIR, 'xds-gui.py')
    
    parts = []
    
    for filename, extra_blank in SOURCE_FILES:
        filepath = os.path.join(SRC_DIR, filename)
        if not os.path.exists(filepath):
            print(f"ERROR: Missing source file: {filepath}")
            sys.exit(1)
        
        content = read_file(filepath)
        
        if extra_blank:
            parts.append('\n')
        
        # Insert frontend function before main.py
        if filename == 'main.py':
            html_path = os.path.join(SRC_DIR, FRONTEND_FILE)
            if not os.path.exists(html_path):
                print(f"ERROR: Missing frontend file: {html_path}")
                sys.exit(1)
            html_content = read_file(html_path)
            frontend_func = build_frontend_function(html_content)
            parts.append(frontend_func)
            parts.append('\n\n')
        
        parts.append(content)
        print(f"  Assembled: {filename} ({len(content):,} bytes)")
    
    result = ''.join(parts)
    
    # Ensure file ends with a newline
    if not result.endswith('\n'):
        result += '\n'
    
    # --- Post-build integrity checks ---
    checks_passed = True
    
    if 'STATIC_ASSETS' not in result:
        print("\nERROR: STATIC_ASSETS not found in assembled file!")
        print("       assets.py content may not have been included.")
        checks_passed = False
    
    if '_LOGO_B64' not in result:
        print("\nERROR: _LOGO_B64 not found in assembled file!")
        checks_passed = False
    
    if '_DIFFRACTION_BG_B64' not in result:
        print("\nERROR: _DIFFRACTION_BG_B64 not found in assembled file!")
        checks_passed = False
    
    if 'get_frontend_html' not in result:
        print("\nERROR: get_frontend_html not found in assembled file!")
        checks_passed = False
    
    if not checks_passed:
        print("\nBuild FAILED integrity checks. Output not written.")
        sys.exit(1)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    
    line_count = result.count('\n')
    print(f"\nBuilt: {output_path}")
    print(f"Lines: {line_count}")
    print(f"Size:  {len(result):,} bytes")
    print("Integrity: OK")
    
    # Verify if requested
    if verify_against and not verify(output_path, verify_against):
        raise SystemExit(1)
    
    return output_path


def verify(built_path, original_path):
    """
    Verify the built file produces identical behavior to the original.
    
    We can't compare byte-for-byte because the HTML escaping may differ
    in representation while producing the same runtime result. Instead we:
    1. Check both files parse as valid Python (AST)
    2. Compare complete ASTs, including function bodies, constants and embedded HTML
    """
    import ast
    
    print(f"\n{'='*60}")
    print("VERIFICATION")
    print(f"{'='*60}")
    
    built_src = read_file(built_path)
    orig_src = read_file(original_path)
    
    # 1. AST validity
    print("\n1. AST compilation...")
    try:
        built_tree = ast.parse(built_src)
        print("   Built file:    OK")
    except SyntaxError as e:
        print(f"   Built file:    FAILED - {e}")
        return False
    
    try:
        orig_tree = ast.parse(orig_src)
        print("   Original file: OK")
    except SyntaxError as e:
        print(f"   Original file: FAILED - {e}")
        return False
    
    # Comparing ASTs checks bodies and values too, while allowing harmless
    # source formatting and equivalent string-literal escaping to differ.
    if ast.dump(built_tree, include_attributes=False) != ast.dump(orig_tree, include_attributes=False):
        print("VERIFICATION FAILED: Python ASTs differ (including embedded HTML)")
        return False
    print("VERIFICATION PASSED: complete Python ASTs match")
    return True


def main():
    parser = argparse.ArgumentParser(description='Build CrystalPilot single-file distribution')
    parser.add_argument('--output', '-o', default=None,
                        help='Output filename (default: xds-gui.py)')
    parser.add_argument('--verify', '-v', default=None,
                        help='Verify against original .py file')
    args = parser.parse_args()
    
    assemble(output_path=args.output, verify_against=args.verify)


if __name__ == '__main__':
    main()
