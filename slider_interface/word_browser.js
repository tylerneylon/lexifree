// This array stores all dictionary words loaded from the server.
let wordList = [];
let fontLoaded = false;
let wordsLoaded = false;

// This function initializes the interface once all resources are loaded.
function checkAllLoaded() {
  if (fontLoaded && wordsLoaded) {
    initializeInterface();
  }
}

// This sets up a font loading observer to track when all fonts are ready.
// Carefully ensure that DM Serif Text is fully loaded before proceeding.
Promise.all([
  document.fonts.ready,
  document.fonts.load('16px "DM Serif Text"')
]).then(() => {
  // Add a small delay to ensure fonts are fully processed by the browser.
  setTimeout(() => {
    fontLoaded = true;
    checkAllLoaded();
  }, 100);
});

// Fetch words from the server when the page loads.
fetch("/46k_words.json")
  .then((response) => {
    if (!response.ok) {
      throw new Error("Network response was not ok");
    }
    return response.json();
  })
  .then((data) => {
    wordList = data;
    wordsLoaded = true;
    checkAllLoaded();
  })
  .catch((error) => {
    console.error("Error loading words:", error);
  });

// DOM elements used throughout the interface.
const sliderHandle = document.getElementById("sliderHandle");
const displayArea = document.getElementById("displayArea");
const column1 = document.getElementById("column1");
const column2 = document.getElementById("column2");
const column3 = document.getElementById("column3");
const sliderContainer = document.querySelector(".slider-container");

// Measurements for slider behavior and word display.
let sliderWidth = sliderContainer.offsetWidth;
const handleWidth = sliderHandle.offsetWidth;

// Variables tracking the current state of the interface.
let isDragging = false;
let startX = 0;
let currentPosition = 0;
let rowsPerColumn = 0;
let wordsPerPage = 0;

// Store measurements once we determine them.
let measuredWordItemHeight = null;
let verticalPadding = 0;

// Store which letters can fit in the scroll bar without overlapping tick marks.
let lettersFitArray = [];

// This variable holds references to active letter overlays.
let activeLetterOverlays = [];

/**
 * Determines the current browser type.
 * @returns {string} The current browser: 'chrome', 'firefox', 'safari', or 'other'.
 */
function getBrowser() {
  const ua = navigator.userAgent;
  
  // Check for Firefox.
  if (ua.includes('Firefox') || ua.includes('FxiOS')) {
    return 'firefox';
  }
  
  // Check for Safari (must check before Chrome since Safari also includes 'Safari').
  if ((ua.includes('Safari') && !ua.includes('Chrome')) || 
      (ua.includes('AppleWebKit') && ua.includes('Mobile'))) {
    return 'safari';
  }
  
  // Check for Chrome and Chromium-based browsers that aren't Edge/Opera/Brave.
  const isChromium = ua.includes('Chrome') || ua.includes('CriOS');
  const isEdge = ua.includes('Edg');
  const isOpera = ua.includes('OPR');
  const isBrave = navigator.brave !== undefined;
  
  if (isChromium && !isEdge && !isOpera && !isBrave) {
    return 'chrome';
  }
  
  // Default for any other browser.
  return 'other';
}

/**
 * Measures the actual height of a word item in the DOM.
 * @returns {number} The measured height of a word item in pixels.
 */
function measureWordItemHeight() {
  // If we've already measured, return the cached value.
  if (measuredWordItemHeight !== null) {
    return measuredWordItemHeight;
  }
  
  // Create a temporary container.
  const tempContainer = document.createElement("div");
  tempContainer.style.visibility = "hidden";
  tempContainer.style.position = "absolute";
  document.body.appendChild(tempContainer);
  
  // Create a temporary word column.
  const tempColumn = document.createElement("div");
  tempColumn.className = "word-column";
  tempContainer.appendChild(tempColumn);
  
  // Create a single word item to measure.
  const wordItem = document.createElement("div");
  wordItem.className = "word-item";
  wordItem.textContent = wordList[0] || "Sample";
  tempColumn.appendChild(wordItem);
  
  // Measure the height.
  measuredWordItemHeight = wordItem.offsetHeight;
  
  // Clean up.
  document.body.removeChild(tempContainer);
  
  return measuredWordItemHeight;
}

/**
 * Calculates how many rows of words can fit in each column.
 * @returns {number} The number of rows that fit in each column.
 */
function calculateRows() {
  const displayHeight = displayArea.offsetHeight;
  const wordItemHeight = measureWordItemHeight();
  const columnPadding = 20; // 10px padding top + 10px padding bottom
  
  // Calculate available height for words after accounting for padding
  const availableHeight = displayHeight - columnPadding;
  
  return Math.floor(availableHeight / wordItemHeight);
}

/**
 * Creates an empty page container that serves as a placeholder.
 * @param {number} pageIndex - The index of the page to create.
 * @returns {HTMLElement} - The created empty page container.
 */
function createEmptyPage(pageIndex) {
  const pageContainer = document.createElement("div");
  pageContainer.className = "page-container";
  pageContainer.dataset.pageIndex = pageIndex;
  
  // Set height to ensure proper scrolling dimensions.
  pageContainer.style.height = "350px";
  
  return pageContainer;
}

/**
 * Populates a page with content including columns and words.
 * @param {HTMLElement} pageContainer - The page container to populate.
 * @param {number} pageIndex - The index of the page to populate.
 */
function populatePage(pageContainer, pageIndex) {
  // Skip if already populated.
  if (pageContainer.children.length > 0) {
    return;
  }
  
  // Calculate the starting index for this page.
  const startIndex = pageIndex * wordsPerPage;
  
  // Create three columns for the page.
  for (let colIndex = 0; colIndex < 3; colIndex++) {
    const col = document.createElement("div");
    col.className = "word-column";
    
    // Apply equal padding to top and bottom for vertical centering.
    col.style.paddingTop = `${verticalPadding}px`;
    col.style.paddingBottom = `${verticalPadding}px`;
    
    // Populate column with words.
    for (let i = 0; i < rowsPerColumn; i++) {
      const wordIndex = startIndex + colIndex * rowsPerColumn + i;
      
      if (wordIndex < wordList.length) {
        const wordItem = document.createElement("div");
        wordItem.className = "word-item";
        wordItem.textContent = wordList[wordIndex];
        col.appendChild(wordItem);
      }
    }
    
    pageContainer.appendChild(col);
  }
}

/**
 * Clears the content of a page by removing all its children.
 * @param {HTMLElement} pageContainer - The page container to clear.
 */
function clearPage(pageContainer) {
  // Use replaceChildren() to remove all children (more modern approach).
  pageContainer.replaceChildren();
}

// Track the currently visible page index.
let currentVisiblePageIndex = 0;

/**
 * Updates which pages are populated based on the current visible page.
 * @param {number} newVisiblePageIndex - The new visible page index.
 * @param {boolean} [force=false] - Whether to force update even if the index hasn't changed.
 */
function updateVisiblePages(newVisiblePageIndex, force = false) {
  // Skip if nothing changed and not forcing update.
  if (newVisiblePageIndex === currentVisiblePageIndex && !force) {
    return;
  }
  
  const totalPages = Math.ceil(wordList.length / wordsPerPage);
  
  // Only check the 5 pages surrounding the new visible page.
  for (let i = newVisiblePageIndex - 2; i <= newVisiblePageIndex + 2; i++) {
    // Skip invalid page indices.
    if (i < 0 || i >= totalPages) {
      continue;
    }
    
    // Access the page directly by index.
    const page = displayArea.children[i];
    if (!page) continue;
    
    // Determine if this page should be populated.
    const shouldBePopulated = Math.abs(i - newVisiblePageIndex) <= 1;
    
    if (shouldBePopulated && page.children.length === 0) {
      // Populate page if it's the visible page or a direct neighbor.
      populatePage(page, i);
    } else if (!shouldBePopulated && page.children.length > 0) {
      // Clear page if it's outside the visible range.
      clearPage(page);
    }
  }
  
  // Update the current visible page index.
  currentVisiblePageIndex = newVisiblePageIndex;
}

/**
 * Creates all empty page placeholders and populates only the initial visible pages.
 */
function loadAllPages() {
  // Clear the display area.
  while (displayArea.firstChild) {
    displayArea.removeChild(displayArea.firstChild);
  }
  
  const totalPages = Math.ceil(wordList.length / wordsPerPage);
  
  // Create and add all empty page placeholders to the display area.
  for (let i = 0; i < totalPages; i++) {
    const page = createEmptyPage(i);
    displayArea.appendChild(page);
  }
  
  // Initialize the visible page index.
  currentVisiblePageIndex = 0;
  
  // Populate only the first page and possibly the second page.
  // Force update even though the index hasn't changed.
  updateVisiblePages(currentVisiblePageIndex, true);
}

/**
 * Shows or hides letter overlays based on the current page index.
 * @param {number} pageIndex - The index of the currently visible page.
 */
function updateLetterOverlays(pageIndex) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  
  // Get the first word on the current page.
  const startWordIndex = pageIndex * wordsPerPage;
  if (startWordIndex >= wordList.length) return;
  
  const currentWord = wordList[startWordIndex];
  const currentLetter = currentWord.charAt(0).toUpperCase();
  
  // Convert letter to index.
  const currentIndex = alphabet.indexOf(currentLetter);
  if (currentIndex === -1) return;
  
  // Clear any existing overlays.
  for (const overlay of activeLetterOverlays) {
    sliderContainer.removeChild(overlay);
  }
  activeLetterOverlays = [];
  
  // Create overlays for current letter and neighbors.
  const lettersToShow = [];
  if (currentIndex > 0) {
    lettersToShow.push({letter: alphabet[currentIndex - 1], index: currentIndex - 1});
  }
  lettersToShow.push({letter: currentLetter, index: currentIndex});
  if (currentIndex < alphabet.length - 1) {
    lettersToShow.push({letter: alphabet[currentIndex + 1], index: currentIndex + 1});
  }
  
  // Create and position each letter overlay.
  for (const item of lettersToShow) {
    // Check if this letter can fit.
    if (!lettersFitArray[item.index]) {
      continue;
    }
    
    // Get the divider positions for this letter's section.
    // We need the divider positions in the pixel space of the slider.
    const leftDividerIndex = item.index;
    const rightDividerIndex = item.index + 1;
    
    // Find the first occurrence indices for calculating divider positions.
    const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const letterIndices = {};
    
    // Initialize letter indices.
    for (let i = 0; i < alphabet.length; i++) {
      letterIndices[alphabet[i]] = -1;
    }
    
    // Find the first occurrence of each letter.
    for (let i = 0; i < wordList.length; i++) {
      const firstChar = wordList[i].charAt(0).toUpperCase();
      if (alphabet.includes(firstChar) && letterIndices[firstChar] === -1) {
        letterIndices[firstChar] = i;
      }
    }
    
    // Calculate divider positions.
    const availableWidth = sliderWidth - handleWidth;
    const leftPosition = leftDividerIndex === 0 ? 0 : 
                         (letterIndices[alphabet[leftDividerIndex]] / wordList.length * availableWidth);
    const rightPosition = rightDividerIndex >= alphabet.length ? availableWidth : 
                          (letterIndices[alphabet[rightDividerIndex]] / wordList.length * availableWidth);
    
    // Position the letter in the middle between dividers.
    const position = (leftPosition + rightPosition) / 2;
    
    // Create the overlay element.
    const overlay = document.createElement('div');
    overlay.className = 'slider-letter-overlay';
    overlay.textContent = item.letter;
    overlay.style.top = '50%';
    overlay.style.left = `${position + handleWidth / 2}px`;
    overlay.style.transform = 'translate(-50%, -50%)';
    
    // The current letter is fully opaque, neighbors are semi-transparent.
    overlay.style.opacity = item.letter === currentLetter ? '1' : '0.6';
    
    sliderContainer.appendChild(overlay);
    activeLetterOverlays.push(overlay);
  }
}

/**
 * Updates the displayed words based on the slider position.
 * @param {number} position - The current slider position in pixels.
 */
function updateDisplay(position) {
  // Ensure scroll snapping is enabled when using the slider.
  displayArea.style.scrollSnapType = "y mandatory";
  
  // Clear any pending timer for disabling snap.
  if (scrollSnapTimer) {
    clearTimeout(scrollSnapTimer);
    scrollSnapTimer = null;
  }
  
  // Normalize the position to a value between 0 and 1.
  const normalizedPosition = position / (sliderWidth - handleWidth);
  const totalPages = Math.ceil(wordList.length / wordsPerPage);
  
  // Find the page index that corresponds to the current position.
  let pageIndex = Math.floor(normalizedPosition * totalPages);
  if (pageIndex >= totalPages) pageIndex = totalPages - 1;
  
  // Update which pages are populated based on the new visible page.
  updateVisiblePages(pageIndex);
  
  // Get the target page directly by index.
  const targetPage = displayArea.children[pageIndex];
  
  if (targetPage) {
    // Scroll to the target page without smooth behavior.
    targetPage.scrollIntoView({ behavior: 'auto', block: 'start' });
  }
  
  // Update letter overlays if dragging.
  if (isDragging) {
    updateLetterOverlays(pageIndex);
  }
}

/**
 * Sets the slider position and updates the word display.
 * @param {number} x - The x-coordinate to position the slider at.
 * @param {boolean} [updateWords=true] - Whether to update the word display.
 */
function setSliderPosition(x, updateWords = true) {
  // Ensure the position stays within valid bounds.
  const newPosition = Math.max(0, Math.min(sliderWidth - handleWidth, x));
  sliderHandle.style.left = `${newPosition}px`;
  currentPosition = newPosition;
  
  if (updateWords) {
    updateDisplay(currentPosition);
  }
}

/**
 * Sync slider position with the currently visible page and update page content.
 */
function syncSliderWithScroll() {
  if (displayArea.children.length === 0) return;
  
  // Get the height of a page.
  const pageHeight = displayArea.children[0].offsetHeight;
  
  // Calculate which page is in the middle of the display area.
  const pageIndex = Math.floor((displayArea.scrollTop + (displayArea.offsetHeight / 2)) / pageHeight);
  // Make sure we have a valid page index.
  if (pageIndex >= 0 && pageIndex < displayArea.children.length) {
    // Update which pages are populated based on the new visible page.
    updateVisiblePages(pageIndex);
    
    // Only update slider position if the user is not currently dragging it.
    // This prevents the scroll tab from jumping during drag operations.
    if (!isDragging) {
      const totalPages = Math.ceil(wordList.length / wordsPerPage);
      
      // Calculate normalized position (0 to 1).
      const normalizedPosition = pageIndex / (totalPages === 1 ? 1 : totalPages - 1);
      
      // Convert to slider position.
      const newPosition = normalizedPosition * (sliderWidth - handleWidth);
      
      // Update slider without triggering display update to avoid feedback loop.
      setSliderPosition(newPosition, false);
    }
  }
}

/**
 * Handles mouse movement during drag operations.
 * @param {MouseEvent} e - The mouse event object.
 */
function onMouseMove(e) {
  if (isDragging) {
    const containerRect = sliderContainer.getBoundingClientRect();
    const newX = e.clientX - containerRect.left - startX;
    setSliderPosition(newX);
  }
}

/**
 * Clears all active letter overlays.
 */
function clearLetterOverlays() {
  // Remove all letter overlays from the DOM.
  for (const overlay of activeLetterOverlays) {
    sliderContainer.removeChild(overlay);
  }
  activeLetterOverlays = [];
}

/**
 * Handles the end of a mouse drag operation.
 */
function onMouseUp() {
  isDragging = false;
  document.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseup", onMouseUp);
  
  // Clear letter overlays when dragging ends.
  clearLetterOverlays();
}

/**
 * Handles touch movement for mobile devices.
 * @param {TouchEvent} e - The touch event object.
 */
function onTouchMove(e) {
  if (isDragging) {
    const containerRect = sliderContainer.getBoundingClientRect();
    const newX = e.touches[0].clientX - containerRect.left - startX;
    setSliderPosition(newX);
    e.preventDefault();
  }
}

/**
 * Handles the end of a touch operation.
 */
function onTouchEnd() {
  isDragging = false;
  document.removeEventListener("touchmove", onTouchMove);
  document.removeEventListener("touchend", onTouchEnd);
  
  // Clear letter overlays when touch interaction ends.
  clearLetterOverlays();
}

/**
 * Calculates whether letters can fit between their corresponding dividers.
 * @param {Array} dividerPositions - Array with positions of each letter divider.
 * @returns {Array} - Boolean array indicating which letters fit.
 */
function calculateLetterFit(dividerPositions) {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  let lettersFit = new Array(26);
  
  // Get a reference to a letter marker to measure letter widths.
  const letterMarkerStyle = window.getComputedStyle(document.querySelector('.letter-marker'));
  const letterFont = `${letterMarkerStyle.fontWeight} ${letterMarkerStyle.fontSize} ${letterMarkerStyle.fontFamily}`;
  
  // Create a temporary canvas to measure text width.
  const canvas = document.createElement('canvas');
  const context = canvas.getContext('2d');
  context.font = letterFont;
  
  // For each letter, check if it fits in its section.
  for (let i = 0; i < alphabet.length; i++) {
    const letter = alphabet[i];
    
    // Measure letter width plus padding (2px on each side).
    const letterWidth = context.measureText(letter).width + 4;
    
    // Calculate the available space between dividers.
    const availableSpace = dividerPositions[i+1] - dividerPositions[i];
    
    // Letter fits if its width is less than available space.
    lettersFit[i] = (letterWidth < availableSpace);
  }
  
  return lettersFit;
}

/**
 * Creates dividers for each letter transition using the word distribution.
 */
function createLetterDividers() {
  // Bail out if the word list is empty.
  if (wordList.length === 0) return;
  
  const letterDividersContainer = document.getElementById("letterDividers");
  letterDividersContainer.innerHTML = '';
  
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
  const containerWidth = sliderContainer.offsetWidth;
  const availableWidth = containerWidth - handleWidth;
  
  // Find the indices where each letter starts in the word list.
  const letterIndices = {};
  
  // Initialize all letter indices
  for (let i = 0; i < alphabet.length; i++) {
    letterIndices[alphabet[i]] = -1;
  }
  
  // Find the first occurrence of each letter.
  for (let i = 0; i < wordList.length; i++) {
    const firstChar = wordList[i].charAt(0).toUpperCase();
    if (alphabet.includes(firstChar) && letterIndices[firstChar] === -1) {
      letterIndices[firstChar] = i;
    }
  }
  
  // Create array of divider positions
  const dividerPositions = new Array(27); // 26 letters plus the end position
  dividerPositions[0] = 0; // Start position (for 'A')
  
  // Calculate divider positions for letters B through Z
  for (let i = 1; i < alphabet.length; i++) {
    const currentLetter = alphabet[i];
    
    // Calculate position based on word distribution
    const letterPosition = letterIndices[currentLetter] / wordList.length;
    dividerPositions[i] = letterPosition * availableWidth;
    
    // Create divider element
    const divider = document.createElement("div");
    divider.className = "letter-divider";
    divider.style.left = `${dividerPositions[i] + handleWidth / 2}px`; // Add half handle width for visual positioning
    divider.title = `${alphabet[i-1]}-${currentLetter} transition`;
    
    letterDividersContainer.appendChild(divider);
  }
  
  // Add the end position
  dividerPositions[26] = availableWidth;
  
  // Calculate which letters will fit between their dividers
  lettersFitArray = calculateLetterFit(dividerPositions);
}

/**
 * Calculates the vertical padding for centering content.
 */
function calculateVerticalPadding() {
  const displayHeight = displayArea.offsetHeight;
  const wordItemHeight = measureWordItemHeight();
  const contentHeight = rowsPerColumn * wordItemHeight;
  const totalPadding = Math.max(0, displayHeight - contentHeight);
  return Math.floor(totalPadding / 2);
}

// Timer for re-enabling scroll snap after wheel events.
let scrollSnapTimer = null;

/**
 * Breifly suspend scroll snapping.
 */
function disableScrollSnap() {
  displayArea.style.scrollSnapType = "none";
  
  // Clear any existing timer.
  if (scrollSnapTimer) {
    clearTimeout(scrollSnapTimer);
  }
  
  // Set a timer to re-enable scroll snap after scrolling stops.
  scrollSnapTimer = setTimeout(() => {
    displayArea.style.scrollSnapType = "y mandatory";
    scrollSnapTimer = null;
  }, 120); // Wait 120ms after scrolling stops.
}

/**
 * Sets up the interface after words are loaded.
 */
function initializeInterface() {
  // Calculate rows and words per page based on measured item height.
  rowsPerColumn = calculateRows();
  wordsPerPage = rowsPerColumn * 3;
  
  // Calculate vertical padding for centering.
  verticalPadding = calculateVerticalPadding();
  
  // Create letter dividers.
  createLetterDividers();
  
  // Load all pages at once.
  loadAllPages();
  
  // Initialize the display with the slider at position 0.
  setSliderPosition(0);
  
  // Add scroll event listener to sync slider position.
  displayArea.addEventListener("scroll", () => {
    // Use requestAnimationFrame to optimize performance.
    requestAnimationFrame(syncSliderWithScroll);
  });
  
  // Add wheel event listener to temporarily disable scroll snapping.
  displayArea.addEventListener("wheel", (e) => {

    // Only apply special mouse wheel behavior on Chrome.
    // This is because the default mouse wheel behavior on Chrome is
    // weird when css-based snapping is used.
    const browser = getBrowser();
    if (browser !== 'chrome') return;

    // Detect if this is a trackpad or a mouse wheel.
    let isTrackpad = (e.wheelDeltaY === -3 * e.deltaY);
    if (!isTrackpad) disableScrollSnap();
  });
  
  // Handle window resize events to maintain proper slider proportions.
  window.addEventListener("resize", () => {
    const containerWidth = sliderContainer.offsetWidth;
    const ratio = currentPosition / (sliderWidth - handleWidth);
    sliderWidth = containerWidth;
    setSliderPosition(ratio * (sliderWidth - handleWidth));
    
    // Re-create letter dividers when window is resized.
    createLetterDividers();
  });
}

// Update the display upon window resizes.
window.addEventListener("resize", () => {
  // Recalculate rows and words per page.
  rowsPerColumn = calculateRows();
  wordsPerPage = rowsPerColumn * 3;
  
  // Recalculate vertical padding for centering.
  verticalPadding = calculateVerticalPadding();
  
  // Remember the current visible page index.
  const currentPage = currentVisiblePageIndex;
  
  // Reload all pages with new dimensions.
  loadAllPages();
  
  // Update scroll position based on current slider.
  updateDisplay(currentPosition);
  
  // Update letter dividers.
  createLetterDividers();
});

// Set up mouse event listeners for the slider handle.
sliderHandle.addEventListener("mousedown", (e) => {
  isDragging = true;
  startX = e.clientX - sliderHandle.getBoundingClientRect().left;
  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
  e.preventDefault();
});

// Set up touch event listeners for mobile devices.
sliderHandle.addEventListener("touchstart", (e) => {
  isDragging = true;
  startX = e.touches[0].clientX - sliderHandle.getBoundingClientRect().left;
  document.addEventListener("touchmove", onTouchMove, { passive: false });
  document.addEventListener("touchend", onTouchEnd);
  e.preventDefault();
});

// Allow clicking on the slider container to jump to that position.
sliderContainer.addEventListener("mousedown", (e) => {
  if (e.target !== sliderHandle) {
    const containerRect = sliderContainer.getBoundingClientRect();
    const clickX = e.clientX - containerRect.left - handleWidth / 2;
    setSliderPosition(clickX);
    isDragging = true;
    startX = handleWidth / 2;
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }
});
