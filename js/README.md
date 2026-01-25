# JavaScript Documentation

## Overview

The site uses **minimal vanilla JavaScript** (ES6+) with no dependencies or frameworks.

**File**: `main.js` (79 lines total, ~45 lines of code)

## Features Implemented

### 1. Mobile Navigation Toggle
- Opens/closes hamburger menu on mobile
- Updates `aria-expanded` attribute for accessibility
- Toggles body class to prevent scroll when menu is open

### 2. Auto-Close Menu on Link Click
- Closes mobile menu when navigation link is clicked
- Improves UX on mobile devices

### 3. Smooth Scroll for Anchor Links
- Smooth scrolling to sections when clicking nav links
- Accounts for fixed navbar height
- Polyfill for older browsers (CSS `scroll-behavior: smooth` as fallback)

### 4. Navbar Scroll Effect
- Adds background blur when scrolling past 50px
- Uses `passive: true` for better scroll performance
- CSS class `.nav--scrolled` triggers backdrop-filter

### 5. Dynamic Year in Footer
- Automatically updates copyright year
- No need to manually update every year

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ features used:
  - Arrow functions
  - `const`/`let`
  - Template literals
  - Optional chaining (`?.`)
  - `forEach()` and `querySelectorAll()`

## Performance Optimizations

1. **IIFE Wrapper** - Avoids polluting global scope
2. **DOM Caching** - Elements queried once and cached
3. **Passive Listeners** - Scroll listener marked as passive
4. **Null Checks** - Checks element existence before adding listeners
5. **Event Delegation** - Could be improved but not needed for this small site

## File Size

- **Unminified**: ~2.1 KB
- **Estimated minified**: ~1.2 KB
- **Gzipped**: ~0.6 KB

Very lightweight! Total JS impact is negligible.

## Alternatives Considered

### What We DON'T Need

- ❌ **jQuery** - Modern vanilla JS is sufficient
- ❌ **Alpine.js/Vue** - Overkill for simple interactions
- ❌ **Intersection Observer** - CSS animations are enough
- ❌ **Lazy Loading Library** - Native `loading="lazy"` works
- ❌ **Animation Library** - CSS transitions are smoother

### CSS-Only Alternatives

Most features could be done CSS-only:
- Smooth scroll: `scroll-behavior: smooth` ✅ Already used
- Navbar scroll: Could use `position: sticky` with custom scroll trigger (complex)
- Mobile menu: CSS checkbox hack (less accessible)

We chose **minimal JS** for better UX and accessibility.

## Maintenance

### To Modify Scroll Threshold
Change `50` in line 62:
```javascript
if (currentScroll > 50) {  // Change this value
```

### To Add New Features
Add inside the IIFE before the closing `})();`:
```javascript
/**
 * New Feature Name
 */
// Your code here
```

### To Debug
Add console logging:
```javascript
console.log('Nav scrolled:', currentScroll);
```

## Testing Checklist

- [ ] Mobile menu opens/closes
- [ ] Menu closes when clicking links
- [ ] Smooth scroll works on all anchor links
- [ ] Navbar background appears after scrolling
- [ ] Footer year displays current year
- [ ] No console errors
- [ ] Works on mobile devices
- [ ] Works on tablets
- [ ] Works on desktop

## Production Recommendations

### Optional: Minification
```bash
# Using terser (if installed)
npx terser main.js -o main.min.js -c -m

# Then update index.html
<script src="js/main.min.js"></script>
```

### Optional: Add to Build Process
If you add a build step later, consider:
- Minification
- Source maps
- Bundle with other assets
- Cache busting (e.g., `main.js?v=1.0.0`)

## Notes

- **No dependencies** - Can be deployed anywhere
- **Modern syntax** - May need transpiling for IE11 (not recommended in 2025)
- **Accessibility-first** - Proper ARIA attributes and keyboard support
- **Performance-conscious** - Minimal impact on page load
- **Maintainable** - Clear comments and structure

Total JavaScript footprint: **~2 KB** (excellent!)
