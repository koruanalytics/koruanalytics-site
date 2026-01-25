# KoruAnalytics Landing Page

Professional landing page for KoruAnalytics - Visual Analytics and OSINT consultancy.

## 🎯 Overview

Single-page landing showcasing visual analytics services for international organizations, with focus on EU Election Observation Missions and OSINT projects.

**Live Site**: [koruanalytics.com](https://www.koruanalytics.com)

## 📐 Design

- **Style**: Refined minimalism, premium aesthetic
- **Target**: International organizations, diplomatic missions
- **Brand Color**: Koru Blue (#1a9bba)
- **Fonts**: Playfair Display (headings) + DM Sans (body)

## 🏗️ Structure

```
koruanalytics-site/
├── index.html          # Main landing page
├── css/
│   └── styles.css      # All styles (mobile-first)
├── js/
│   └── main.js         # Vanilla JavaScript (ES6+)
├── img/                # Visual assets (7 images)
│   └── README.md       # Image specifications
└── README.md           # This file
```

## 📄 Sections

1. **Navigation** - Fixed header with smooth scroll
2. **Hero** - Value proposition + dual CTAs
3. **Services** - OSINT Projects + Data Analytics (2-col grid)
4. **Process** - 4-step methodology
5. **Work** - Portfolio metrics + dashboards
6. **About** - Company overview
7. **Contact** - Email + LinkedIn
8. **Footer** - Copyright + links

## 🎨 Color Palette

| Name | Hex | Usage |
|------|-----|-------|
| Koru Blue | `#1a9bba` | CTAs, accents, links |
| Koru Blue Dark | `#147a94` | Hover states |
| Text Primary | `#1a1a1a` | Headings, body text |
| Text Secondary | `#5a5a5a` | Subtitles, descriptions |
| Background | `#ffffff` | Main background |
| Background Alt | `#f8f9fa` | Alternating sections |

## 📱 Responsive Design

- **Mobile-first** CSS architecture
- **Breakpoints**:
  - Mobile: < 768px
  - Tablet: 768px - 1023px
  - Desktop: ≥ 1024px

## ♿ Accessibility

- ✓ WCAG AA contrast ratios (minimum 4.5:1)
- ✓ Semantic HTML5
- ✓ ARIA labels for navigation
- ✓ Focus-visible states
- ✓ Reduced motion support
- ✓ Skip link for keyboard navigation

## 🚀 Performance

- Pure CSS (no frameworks)
- `font-display: swap` for web fonts
- Lazy loading for images
- Smooth scroll behavior
- Minimal animations (CSS only)

## 📦 Required Assets

Before deploying, add these images to `/img/`:
- `logo.svg` - Main logo
- `logo-white.svg` - Footer logo
- `favicon.png` - Browser icon
- `og-image.png` - Social sharing (1200x630px)
- `map-countries.png` - Project locations map
- `dashboard-congo.png` - Dashboard screenshot
- `dashboard-ethiopia.png` - Dashboard screenshot

See `/img/README.md` for detailed specifications.

## 🌐 Deployment

Hosted on **Azure Static Web Apps**.

### Deployment Workflow
GitHub Actions automatically deploys on push to `main` branch.

Configuration: `.github/workflows/azure-static-web-apps-*.yml`

### Manual Deployment
```bash
# Commit changes
git add .
git commit -m "Update landing page"
git push origin main

# Azure automatically builds and deploys
```

## 📧 Contact

**Email**: carlospeinado@koruanalytics.com
**LinkedIn**: [linkedin.com/in/carlospeinado](https://www.linkedin.com/in/carlospeinado/)

## 📝 License

© 2025 KoruAnalytics. All rights reserved.

---

**Built with**: Pure HTML5, CSS3, Vanilla JavaScript
**Optimized for**: Speed, accessibility, and professional presentation
