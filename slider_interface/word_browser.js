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
  const wordItemHeight = 24;  // Approximate height of each word item in pixels.
  return Math.floor(displayHeight / wordItemHeight);
}

/**
 * Creates a page of words with three columns.
 * @param {number} pageIndex - The index of the page to create.
 * @returns {HTMLElement} - The created page container.
 */
function createPage(pageIndex) {
  const pageContainer = document.createElement("div");
  pageContainer.className = "page-container";
  
  // Calculate the starting index for this page.
  const startIndex = pageIndex * wordsPerPage;
  
  // Create three columns for the page.
  const pageCols = [0, 1, 2].map(() => {
    const col = document.createElement("div");
    col.className = "word-column";
    return col;
  });
  
  // Populate each column with words.
  for (let i = 0; i < rowsPerColumn; i++) {
    // Add words to each of the three columns.
    for (let colIndex = 0; colIndex < 3; colIndex++) {
      const wordIndex = startIndex + colIndex * rowsPerColumn + i;
      
      if (wordIndex < wordList.length) {
        const wordItem = document.createElement("div");
        wordItem.className = "word-item";
        wordItem.textContent = wordList[wordIndex];
        pageCols[colIndex].appendChild(wordItem);
      }
    }
  }
  
  // Add all columns to the page container.
  pageCols.forEach(col => pageContainer.appendChild(col));
  
  return pageContainer;
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
  
  // Clear the display area.
  displayArea.innerHTML = "";
  
  // Determine which pages to show.
  const pagesToCreate = [];
  
  // Add previous page if not on first page.
  if (pageIndex > 0) {
    pagesToCreate.push(pageIndex - 1);
  }
  
  // Always add current page.
  pagesToCreate.push(pageIndex);
  
  // Add next page if not on last page.
  if (pageIndex < totalPages - 1) {
    pagesToCreate.push(pageIndex + 1);
  }
  
  // Create and add pages to the display area.
  pagesToCreate.forEach(index => {
    const page = createPage(index);
    // Store the page index as a data attribute.
    page.dataset.pageIndex = index;
    displayArea.appendChild(page);
  });
  
  // Scroll to current page (middle page, or first if only 2 pages).
  const scrollIndex = pageIndex > 0 ? 1 : 0;
  const scrollTarget = displayArea.children[scrollIndex];
  
  // Scroll without smooth behavior for initial position.
  scrollTarget.scrollIntoView({ behavior: 'auto', block: 'start' });
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
 * Sync slider position with the currently visible page.
 */
function syncSliderWithScroll() {
  // Calculate the middle point of the display area.
  const middleY = displayArea.scrollTop + displayArea.offsetHeight / 2;
  let visiblePage = null;
  
  // Find which page contains the middle point.
  for (let i = 0; i < displayArea.children.length; i++) {
    const page = displayArea.children[i];
    const pageTop = page.offsetTop;
    const pageBottom = pageTop + page.offsetHeight;
    
    // Check if this page contains the middle point.
    if (middleY >= pageTop && middleY < pageBottom) {
      visiblePage = page;
      break;
    }
  }
  
  // Default to first page if no page is found at the middle.
  if (!visiblePage && displayArea.children.length > 0) {
    visiblePage = displayArea.children[0];
  }
  
  if (visiblePage) {
    // Get the page index from the data attribute.
    const pageIndex = parseInt(visiblePage.dataset.pageIndex, 10);
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
  updateDisplay(currentPosition);
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
