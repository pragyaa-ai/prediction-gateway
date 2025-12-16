#!/usr/bin/env python3
"""
Pre-flight check - Verify all files are syntactically correct
"""
import sys
from pathlib import Path

print("🔍 ML Gateway - Pre-flight Check")
print("=" * 50)

errors = []

# Check Python files
python_files = [
    "main.py",
    "models/schemas.py",
    "models/registry.py",
    "adapters/base.py",
    "adapters/mappers.py",
    "services/opensearch.py",
    "config/settings.py",
]

print("\n📝 Checking Python files...")
for file in python_files:
    path = Path(file)
    if path.exists():
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} - NOT FOUND")
        errors.append(f"Missing: {file}")

# Check config files
config_files = [
    "config/models.yaml",
    ".env",
    "requirements.txt",
]

print("\n⚙️  Checking config files...")
for file in config_files:
    path = Path(file)
    if path.exists():
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} - NOT FOUND")
        errors.append(f"Missing: {file}")

# Check templates
template_files = [
    "templates/admin.html",
]

print("\n🎨 Checking templates...")
for file in template_files:
    path = Path(file)
    if path.exists():
        print(f"  ✅ {file}")
    else:
        print(f"  ❌ {file} - NOT FOUND")
        errors.append(f"Missing: {file}")

# Check documentation
docs = [
    "README.md",
    "PROJECT_SUMMARY.md",
    "QUICK_REFERENCE.md",
    "ADMIN_UI_GUIDE.md",
]

print("\n📚 Checking documentation...")
for file in docs:
    path = Path(file)
    if path.exists():
        print(f"  ✅ {file}")
    else:
        print(f"  ⚠️  {file} - NOT FOUND (optional)")

# Python syntax check
print("\n🐍 Checking Python syntax...")
try:
    import py_compile
    for file in python_files:
        if Path(file).exists():
            try:
                py_compile.compile(file, doraise=True)
                print(f"  ✅ {file} - syntax OK")
            except py_compile.PyCompileError as e:
                print(f"  ❌ {file} - SYNTAX ERROR")
                errors.append(f"Syntax error in {file}: {e}")
except ImportError:
    print("  ⚠️  py_compile not available, skipping syntax check")

# Summary
print("\n" + "=" * 50)
if errors:
    print("❌ Pre-flight check FAILED")
    print("\nErrors found:")
    for error in errors:
        print(f"  - {error}")
    sys.exit(1)
else:
    print("✅ Pre-flight check PASSED")
    print("\nNext steps:")
    print("  1. Install dependencies: pip install -r requirements.txt")
    print("  2. Start gateway: ./start.sh")
    print("  3. Open admin UI: http://localhost:8000/admin")
    sys.exit(0)
