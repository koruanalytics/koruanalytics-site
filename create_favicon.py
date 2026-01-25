#!/usr/bin/env python3
"""
Create favicon.png from logo.png
Resizes to 32x32 pixels for optimal browser display
"""

from PIL import Image
import os

# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
img_dir = os.path.join(script_dir, 'img')
logo_path = os.path.join(img_dir, 'logo.png')
favicon_path = os.path.join(img_dir, 'favicon.png')

print("Creating favicon.png from logo.png...")
print(f"Input: {logo_path}")
print(f"Output: {favicon_path}")

try:
    # Open the logo
    with Image.open(logo_path) as img:
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')

        # Resize to 32x32 with high-quality antialiasing
        favicon = img.resize((32, 32), Image.Resampling.LANCZOS)

        # Save as PNG
        favicon.save(favicon_path, 'PNG', optimize=True)

        # Get file size
        size = os.path.getsize(favicon_path)
        print(f"✅ Success! Created favicon.png ({size:,} bytes)")
        print(f"   Dimensions: 32x32 pixels")

except FileNotFoundError:
    print(f"❌ Error: Could not find {logo_path}")
    print("   Make sure logo.png exists in the img/ directory")
except Exception as e:
    print(f"❌ Error: {e}")
