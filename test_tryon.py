"""
Virtual Try-On Diagnostic Tool
Tests if all dependencies are installed correctly
"""

print("="*50)
print("VIRTUAL TRY-ON DIAGNOSTIC TOOL")
print("="*50)
print()

errors = []
warnings = []

# Test 1: PIL/Pillow
print("[1/3] Testing PIL (Pillow)...")
try:
    from PIL import Image
    print("     ✓ PIL installed")
except ImportError as e:
    errors.append("PIL not installed")
    print(f"     ✗ Error: {e}")
    print("     Fix: pip install pillow")

# Test 2: Gradio Client
print("[2/3] Testing Gradio Client...")
try:
    from gradio_client import Client
    print("     ✓ Gradio Client installed")
except ImportError as e:
    errors.append("Gradio Client not installed")
    print(f"     ✗ Error: {e}")
    print("     Fix: pip install gradio-client")

# Test 3: Requests
print("[3/3] Testing Requests...")
try:
    import requests
    print("     ✓ Requests installed")
except ImportError as e:
    errors.append("Requests not installed")
    print(f"     ✗ Error: {e}")
    print("     Fix: pip install requests")

print()
print("="*50)

if errors:
    print("ERRORS FOUND:")
    for error in errors:
        print(f"  ✗ {error}")
    print()
    print("FIX COMMAND:")
    print("  pip install pillow gradio-client requests")
else:
    print("✓ ALL DEPENDENCIES INSTALLED CORRECTLY!")
    print()
    print("Testing Gradio connection (this may take a moment)...")
    try:
        from gradio_client import Client
        client = Client("yisol/IDM-VTON")
        print("✓ Successfully connected to IDM-VTON model!")
        print()
        print("READY TO USE!")
        print("Your virtual try-on should work now.")
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        print()
        print("This might be normal if:")
        print("  - Model is loading (wait 30 seconds)")
        print("  - No internet connection")
        print("  - Hugging Face Spaces is down")

print("="*50)