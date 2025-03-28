// This array stores all dictionary words loaded from the server.
let wordList = [];

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

    // XXX
    wordList.length = 1000;

    initializeInterface();
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
let rowsPerColumn = calculateRows();
let wordsPerPage = rowsPerColumn * 3;

/**
 * Calculates how many rows of words can fit in each column.
 * @returns {number} The number of rows that fit in each column.
 */
function calculateRows() {
  const displayHeight = displayArea.offsetHeight;
  const wordItemHeight = 26;  // Approximate height of each word item in pixels.
  return Math.floor(displayHeight / wordItemHeight);
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
 */
function updateVisiblePages(newVisiblePageIndex) {
  // Skip if nothing changed.
  if (newVisiblePageIndex === currentVisiblePageIndex) {
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
  updateVisiblePages(currentVisiblePageIndex);
}

/**
 * Updates the displayed words based on the slider position.
 * @param {number} position - The current slider position in pixels.
 */
function updateDisplay(position) {
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
    
    const totalPages = Math.ceil(wordList.length / wordsPerPage);
    
    // Calculate normalized position (0 to 1).
    const normalizedPosition = pageIndex / (totalPages === 1 ? 1 : totalPages - 1);
    
    // Convert to slider position.
    const newPosition = normalizedPosition * (sliderWidth - handleWidth);
    
    // Update slider without triggering display update to avoid feedback loop.
    setSliderPosition(newPosition, false);
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
 * Handles the end of a mouse drag operation.
 */
function onMouseUp() {
  isDragging = false;
  document.removeEventListener("mousemove", onMouseMove);
  document.removeEventListener("mouseup", onMouseUp);
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
  
  // Initialize with -1 to indicate no words start with this letter.
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
  
  // Create dividers for letter transitions.
  for (let i = 1; i < alphabet.length; i++) {
    const currentLetter = alphabet[i];
    const prevLetter = alphabet[i-1];
    
    // Skip if we don't have words that start with the current letter.
    if (letterIndices[currentLetter] === -1) continue;
    
    // Calculate position based on word distribution.
    const letterPosition = letterIndices[currentLetter] / wordList.length;
    const position = letterPosition * availableWidth + handleWidth / 2;
    
    const divider = document.createElement("div");
    divider.className = "letter-divider";
    divider.style.left = `${position}px`;
    divider.title = `${prevLetter}-${currentLetter} transition`;
    
    letterDividersContainer.appendChild(divider);
  }
}

/**
 * Sets up the interface after words are loaded.
 */
function initializeInterface() {
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
  rowsPerColumn = calculateRows();
  wordsPerPage = rowsPerColumn * 3;
  
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
