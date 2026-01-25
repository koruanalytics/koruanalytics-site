#!/usr/bin/env python3
"""
Create og-image.png (1200x630) for social media sharing
Includes logo and company tagline
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Paths
script_dir = os.path.dirname(os.path.abspath(__file__))
img_dir = os.path.join(script_dir, 'img')
logo_path = os.path.join(img_dir, 'logo.png')
og_image_path = os.path.join(img_dir, 'og-image.png')

# Design settings (matching brand colors from wireframe)
WIDTH = 1200
HEIGHT = 630
BG_COLOR = '#ffffff'  # White background
PRIMARY_COLOR = '#1a9bba'  # Koru Blue
TEXT_COLOR = '#1a1a1a'  # Dark text

print("Creating og-image.png for social sharing...")
print(f"Dimensions: {WIDTH}x{HEIGHT}px")

try:
    # Create new image with white background
    og_image = Image.new('RGB', (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(og_image)

    # Open and resize logo
    with Image.open(logo_path) as logo:
        # Resize logo to fit nicely (max 400px wide)
        logo_width = 400
        aspect_ratio = logo.height / logo.width
        logo_height = int(logo_width * aspect_ratio)
        logo_resized = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)

        # Convert logo to RGBA if needed
        if logo_resized.mode != 'RGBA':
            logo_resized = logo_resized.convert('RGBA')

        # Position logo (center-left)
        logo_x = 100
        logo_y = (HEIGHT - logo_height) // 2

        # Paste logo (handle transparency)
        og_image.paste(logo_resized, (logo_x, logo_y), logo_resized)

    # Add text using default font (since custom fonts may not be available)
    # Title: "KoruAnalytics"
    title = "KoruAnalytics"
    subtitle = "Visual Analytics Solutions"
    tagline = "Insights through Visual Analytics"

    # Position text to the right of logo
    text_x = logo_x + logo_width + 80
    text_y_start = (HEIGHT // 2) - 60

    # Draw title (we'll use the draw.text with default font)
    # Note: Without custom fonts, this will use PIL's default font
    draw.text((text_x, text_y_start), title, fill=TEXT_COLOR)
    draw.text((text_x, text_y_start + 40), tagline, fill=PRIMARY_COLOR)
    draw.text((text_x, text_y_start + 80), "OSINT Projects | Data Analytics", fill=TEXT_COLOR)

    # Add subtle border
    border_width = 3
    draw.rectangle(
        [(border_width, border_width), (WIDTH - border_width, HEIGHT - border_width)],
        outline=PRIMARY_COLOR,
        width=border_width
    )

    # Save
    og_image.save(og_image_path, 'PNG', optimize=True, quality=95)

    # Get file size
    size = os.path.getsize(og_image_path)
    print(f"Success! Created og-image.png ({size:,} bytes)")
    print(f"Location: {og_image_path}")

except FileNotFoundError:
    print(f"Error: Could not find {logo_path}")
except Exception as e:
    print(f"Error: {e}")
