# Case Distribution Map - Marker Issues Analysis

**Date:** 2026-01-20
**Status:** Markers not appearing on map
**Dashboard Type:** Dengue Disease Surveillance Dashboard

---

## SUMMARY OF APPROACHES TRIED

### Approach 1: Expose Map State Globally (Commit: b51051f)
**Date:** Jan 20, 2026 12:01
**What was done:**
- Exposed `window.mapState` object globally
- Made map instance accessible outside the IIFE scope
- Allowed PDF download function to access markers

**Result:** ❌ PARTIAL - Fixed access to map, but markers still didn't appear in PDF

---

### Approach 2: Add Progress Modal & Improve Rendering (Commit: 3da9a85)
**Date:** Jan 20, 2026 12:26
**What was done:**
- Added progress modal during PDF generation
- Implemented SVG style inlining (recursive)
- Added 1-second delay before capturing map
- Called `map.invalidateSize()` and `markers.bringToFront()`

**Result:** ❌ PARTIAL - Improved rendering process, but markers still missing

---

### Approach 3: Process Custom Panes (Commit: 5ec1668, ca248ea)
**Date:** Jan 20, 2026 12:37
**What was done:**
- **ROOT CAUSE IDENTIFIED:** Markers rendered in custom `casePane` (zIndex 650)
- PDF code only processed default `leaflet-overlay-pane`
- **FIX:** Added explicit processing of custom panes:
  - `casePane` (where red circle markers live)
  - `meteoHexPane` (where meteorology hexagons live)
- Copy pane positioning and CSS styles
- Deep clone SVG elements from custom panes

**Code added (lines 9499-9510):**
```javascript
// CRITICAL FIX: Process custom panes where markers are actually rendered
const customPaneSelectors = [
  { className: 'casePane', description: 'case markers' },
  { className: 'meteoHexPane', description: 'meteorology hexagons' }
];

customPaneSelectors.forEach(({ className }) => {
  const originalCustomPane = originalMapContainer.querySelector(`.${className}`);
  const clonedCustomPane = clonedMapContainer.querySelector(`.${className}`);
  processPaneSvgs(originalCustomPane, clonedCustomPane);
});
```

**Result:** ✅ SHOULD WORK - This was the definitive fix for PDF downloads

---

## CURRENT SITUATION

Based on git commits, **all known fixes are implemented**. If markers still don't appear:

### Two Scenarios:

#### A. Markers Not Appearing ON SCREEN (Live Dashboard)
**Possible causes:**
1. CSV file doesn't have latitude/longitude columns
2. Lat/lng columns have wrong names (not detected)
3. Coordinates are invalid (non-numeric, out of range)
4. Timeline filtering is active and no cases match selected date
5. Map not initialized (section not opened)

#### B. Markers Not Appearing IN PDF (But visible on screen)
**Possible causes:**
1. Custom pane not being found by selector
2. SVG elements not being cloned correctly
3. html2canvas not capturing the pane layer
4. Markers outside the visible viewport during capture

---

## DIAGNOSTIC CHECKLIST

### Step 1: Verify Data Has Coordinates
**Action:** Open browser DevTools Console and run:
```javascript
console.log(window.dengueState?.processedRows?.filter(r => r._coords).length);
```
**Expected:** Should show number > 0 (number of rows with valid coordinates)
**If 0:** CSV file is missing lat/lng columns or columns not detected

---

### Step 2: Check Map Initialization
**Action:** In console, run:
```javascript
console.log(window.mapState?.map ? 'Map initialized' : 'Map NOT initialized');
```
**Expected:** "Map initialized"
**If NOT:** Open "4. Case distribution map" section to initialize map

---

### Step 3: Check Markers Were Added
**Action:** In console, run:
```javascript
console.log(window.mapState?.markers?.getLayers().length);
```
**Expected:** Should match the number from Step 1
**If 0:** Markers not being added to map (code issue)

---

### Step 4: Check Custom Pane Exists
**Action:** In console, run:
```javascript
const pane = document.querySelector('.casePane');
console.log(pane ? 'casePane found' : 'casePane NOT found');
if (pane) {
  console.log('SVG elements in casePane:', pane.querySelectorAll('svg').length);
  console.log('Circle elements:', pane.querySelectorAll('circle').length);
}
```
**Expected:**
- "casePane found"
- SVG elements > 0
- Circle elements > 0

---

### Step 5: Check Timeline Filtering
**Action:** Look at the map section controls:
- Is "Show all cases" checkbox CHECKED? (should be for testing)
- Is "7-days delay" checkbox UNCHECKED? (should be for testing)

**Action:** In console, run:
```javascript
console.log({
  timelineActive: window.mapState?.timelineActive,
  showAllCases: window.mapState?.showAllCases,
  selectedDate: window.mapState?.selectedDate
});
```
**Expected for full marker view:**
- `timelineActive: false` OR `showAllCases: true`

---

## ALTERNATIVE SOLUTIONS

### Alternative 1: Force Markers to Default Pane ⭐ RECOMMENDED
**Complexity:** LOW
**Risk:** LOW
**Effectiveness:** HIGH

**Change marker creation to use default pane instead of custom pane**

**File:** `index.html`
**Line:** 8531-8538
**Change:**
```javascript
// BEFORE:
const marker = L.circleMarker([r._lat, r._lng], {
  radius: 4,
  color: '#dc2626',
  fillColor: '#dc2626',
  fillOpacity: 0.8,
  weight: 1,
  pane: 'casePane'  // ← REMOVE THIS LINE
});

// AFTER:
const marker = L.circleMarker([r._lat, r._lng], {
  radius: 4,
  color: '#dc2626',
  fillColor: '#dc2626',
  fillOpacity: 0.8,
  weight: 1
  // No pane specified = uses default overlay pane (already processed in PDF)
});
```

**Why this works:**
- Default overlay pane is ALREADY being processed in PDF code (line 9495-9497)
- No need for custom pane processing
- Simpler architecture

**Trade-off:**
- Markers may appear behind/in front of district boundaries (zIndex less controlled)
- But functionally equivalent for most use cases

---

### Alternative 2: Use Marker Clustering
**Complexity:** MEDIUM
**Risk:** MEDIUM
**Effectiveness:** MEDIUM
**Additional dependency:** `leaflet.markercluster.js`

**Replace individual circle markers with marker clusters**

**Pros:**
- Better performance with many markers
- Automatic grouping of nearby markers
- Built-in MarkerCluster library has better PDF compatibility

**Cons:**
- Need to add external library
- Changes visual appearance significantly
- Clusters may not expand in static PDF

**Not recommended** unless you have 1000+ markers and performance issues

---

### Alternative 3: Canvas-Based Markers Instead of SVG
**Complexity:** HIGH
**Risk:** HIGH
**Effectiveness:** MEDIUM
**Requires:** Custom Canvas overlay layer

**Replace Leaflet SVG markers with Canvas rendering**

**Pros:**
- Canvas captures reliably in html2canvas
- Better performance for many markers

**Cons:**
- Lose interactivity (tooltips, popups)
- Must implement custom rendering code
- Significant refactoring required

**Not recommended** unless SVG approach completely fails

---

### Alternative 4: Add Explicit Marker Debug Rendering
**Complexity:** LOW
**Risk:** LOW
**Effectiveness:** HIGH (for diagnosis)

**Add visible debugging to see what's happening**

Add this code before PDF capture (line 9395):

```javascript
// Debug: Log marker information
if (window.mapState?.markers) {
  const markerCount = window.mapState.markers.getLayers().length;
  console.log(`[PDF] Found ${markerCount} markers in featureGroup`);

  // Debug: Highlight casePane with border
  const casePane = document.querySelector('.casePane');
  if (casePane) {
    console.log(`[PDF] casePane found, SVG count: ${casePane.querySelectorAll('svg').length}`);
    casePane.style.border = '3px solid blue'; // Visual debug
  } else {
    console.warn('[PDF] casePane NOT FOUND');
  }
}
```

**Why this helps:**
- Console logs show exactly what's being found
- Blue border on casePane shows if it exists visually
- Confirms whether issue is in capture or rendering

---

### Alternative 5: Screenshot Map Separately Using Leaflet.EasyPrint
**Complexity:** MEDIUM
**Risk:** LOW
**Effectiveness:** HIGH
**Requires:** `leaflet-easyprint` plugin

**Use specialized Leaflet screenshot plugin instead of html2canvas**

**Install:**
```html
<script src="https://unpkg.com/leaflet-easyprint@2.1.9/dist/bundle.js"></script>
```

**Replace html2canvas map capture with:**
```javascript
// Instead of cloning and using html2canvas...
const printControl = L.easyPrint({
  hidden: true,
  exportOnly: true,
  sizeModes: ['A4Portrait']
});
map.addControl(printControl);

// Capture map as image
printControl.printMap('CurrentSize', 'map-export');
```

**Pros:**
- Designed specifically for Leaflet maps
- Handles all panes automatically
- Better SVG compatibility

**Cons:**
- Must integrate with existing jsPDF workflow
- Another external dependency
- May require refactoring download function

---

### Alternative 6: Server-Side Rendering
**Complexity:** VERY HIGH
**Risk:** HIGH
**Effectiveness:** VERY HIGH
**Requires:** Node.js backend, Puppeteer

**Move PDF generation to server using headless browser**

**Not recommended** for this single-HTML-file dashboard

---

## RECOMMENDED ACTION PLAN

### Plan A: Quick Fix (5 minutes) ⭐
**Try Alternative 1** - Remove custom pane assignment

1. Edit `index.html` line 8537
2. Remove `pane: 'casePane'` from marker options
3. Save and test
4. If works → commit and done

---

### Plan B: Debug First (15 minutes)
**Use Alternative 4** - Add debug logging

1. Run diagnostic checklist (Steps 1-5 above)
2. Add debug logging code
3. Download PDF and check console
4. Identify exact point of failure
5. Apply targeted fix based on findings

---

### Plan C: Alternative Technology (1 hour)
**Use Alternative 5** - Leaflet.EasyPrint plugin

1. Add plugin to HTML
2. Replace map capture logic
3. Integrate with jsPDF
4. Test thoroughly

---

## NEXT STEPS

**Please choose one of the following:**

1. **Run diagnostics** - I'll add logging code and help you debug
2. **Try Alternative 1** - I'll remove the custom pane assignment (quickest)
3. **Try Alternative 5** - I'll integrate Leaflet.EasyPrint plugin (most robust)
4. **Share diagnostic info** - Run the checklist commands and share the console output

**My recommendation:** Try **Alternative 1** first (remove custom pane). It's a 1-line change that should fix both the live view and PDF if the issue is pane-related.

---

## FILES REFERENCE

- **Main file:** `/home/user/comm_dss_dashboard/index.html` (336.8 KB)
- **Map initialization:** Lines 8405-8427
- **Marker creation:** Lines 8530-8554
- **PDF download:** Lines 9260-9607
- **Custom pane processing:** Lines 9499-9510

---

**Document version:** 1.0
**Last updated:** 2026-01-20
**Status:** Awaiting user decision on which approach to try
