# Image Assets for KoruAnalytics Landing Page

This directory contains all visual assets for the website.

## Current Images

✅ **Added** (5 images):
- `logo.png` - Navigation logo (50.9 KB)
- `logo-white.png` - Footer logo (31.5 KB)
- `map-countries.png` - World map (675 KB)
- `dashboard-congo.png` - Dashboard screenshot (3.5 MB)
- `dashboard-ethiopia.png` - Dashboard screenshot (814 KB)

❌ **Missing** (3 images):
- `favicon.png` - Browser tab icon (32x32px recommended)
- `og-image.png` - Social media preview (1200x630px required)
- `globe-visualization.svg` - Hero section visual (optional)

*Note: Currently using logo.png as temporary fallback for favicon and og-image*

## Required Images

### Navigation & Branding
| Filename | Type | Dimensions | Usage |
|----------|------|------------|-------|
| `logo.svg` | SVG | - | Main navigation logo |
| `logo-white.svg` | SVG | - | Footer logo (white version) |
| `favicon.png` | PNG | 32x32px | Browser favicon |
| `apple-touch-icon.png` | PNG | 180x180px | iOS home screen icon |

### Social Media
| Filename | Type | Dimensions | Usage |
|----------|------|------------|-------|
| `og-image.png` | PNG/JPG | 1200x630px | Open Graph / Twitter Card |

### Hero Section
| Filename | Type | Dimensions | Usage |
|----------|------|------------|-------|
| `globe-visualization.svg` | SVG | - | Hero section visual (optional) |

### Work Section
| Filename | Type | Dimensions | Usage |
|----------|------|------------|-------|
| `map-countries.png` | PNG/JPG | ~1200px wide | World map showing project countries |
| `dashboard-congo.png` | PNG/JPG | ~600px wide | Electoral dashboard screenshot (Congo) |
| `dashboard-ethiopia.png` | PNG/JPG | ~600px wide | Electoral dashboard screenshot (Ethiopia) |

## Image Specifications

### Optimization
- Compress all images using tools like TinyPNG or ImageOptim
- Target file sizes: < 200KB for photos, < 50KB for graphics
- Use WebP format with PNG/JPG fallback when possible

### Naming Convention
- Use lowercase with hyphens (kebab-case)
- Be descriptive: `dashboard-congo.png` not `img1.png`
- Use semantic names that describe content

### Accessibility
- All images have proper `alt` attributes in HTML
- Decorative images should have `alt=""`
- Informative images need descriptive alt text

## Color Palette Reference

For creating graphics that match the brand:
- **Primary**: #1a9bba (Koru Blue)
- **Primary Dark**: #147a94 (Hover states)
- **Text**: #1a1a1a
- **Background**: #ffffff
- **Background Alt**: #f8f9fa

## How to Create Missing Images

### 1. favicon.png (Browser Tab Icon)
**Dimensions**: 32x32px (or 16x16px)
**Quick Method**:
```bash
# Using ImageMagick (if installed)
magick logo.png -resize 32x32 favicon.png

# Or use online tool: https://favicon.io/favicon-converter/
```

### 2. og-image.png (Social Media Preview)
**Dimensions**: 1200x630px
**Template**:
- Background: White or light blue gradient
- Logo: Centered or top-left
- Text: "KoruAnalytics | Visual Analytics Solutions"
- Keep important content in center 1200x600px (safe zone)

**Quick Method**:
- Use Canva: https://www.canva.com/ (free)
- Template: "Facebook Post" (1200x630)
- Add logo + tagline
- Export as PNG

### 3. globe-visualization.svg (Optional)
**Alternative**: Use Font Awesome or similar icon library
- Globe icon with data points
- Export as SVG
- Or use a simple abstract data visualization graphic

## Image Optimization

⚠️ **Large Files Detected**:
- `dashboard-congo.png` - **3.5 MB** (needs optimization!)
- `dashboard-ethiopia.png` - **814 KB** (could be smaller)

**Optimize with**:
```bash
# TinyPNG (online): https://tinypng.com/
# Target: < 200KB per dashboard image

# Or use ImageMagick:
magick dashboard-congo.png -quality 85 -resize 1200x dashboard-congo-optimized.png
```

## Tips for Screenshots

### Dashboard Screenshots
- Use actual project dashboards (anonymized if needed)
- Show data visualizations clearly
- Include enough context but avoid text-heavy areas
- Maintain 16:10 or similar aspect ratio
- Minimum 1200px wide for retina displays
- **Optimize to < 200KB** for fast loading

### Map
- Show highlighted countries where projects were conducted
- Use subtle colors aligned with brand (blues/grays)
- Ensure country labels are readable
- SVG preferred for crisp scaling
