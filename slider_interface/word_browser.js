// This array stores all dictionary words loaded from the server.
let wordList = [];

// Fetch words from the server when the page loads.
fetch("/words.json")
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
  
  // Calculate the starting index for the current page.
  const startIndex = pageIndex * wordsPerPage;
  
  // Clear all three columns before populating them again.
  column1.innerHTML = "";
  column2.innerHTML = "";
  column3.innerHTML = "";
  
   // Populate each column with words.
  for (let i = 0; i < rowsPerColumn; i++) {
    // First column.
    if (startIndex + i < wordList.length) {
      const wordItem = document.createElement("div");
      wordItem.className = "word-item";
      wordItem.textContent = wordList[startIndex + i];
      column1.appendChild(wordItem);
    }

    // Second column.
    if (startIndex + rowsPerColumn + i < wordList.length) {
      const wordItem = document.createElement("div");
      wordItem.className = "word-item";
      wordItem.textContent = wordList[startIndex + rowsPerColumn + i];
      column2.appendChild(wordItem);
    }

    // Third column.
    if (startIndex + 2 * rowsPerColumn + i < wordList.length) {
      const wordItem = document.createElement("div");
      wordItem.className = "word-item";
      wordItem.textContent = wordList[startIndex + 2 * rowsPerColumn + i];
      column3.appendChild(wordItem);
    }
  }
}

/**
 * Sets the slider position and updates the word display.
 * @param {number} x - The x-coordinate to position the slider at.
 */
function setSliderPosition(x) {
  // Ensure the position stays within valid bounds.
  const newPosition = Math.max(0, Math.min(sliderWidth - handleWidth, x));
  sliderHandle.style.left = `${newPosition}px`;
  currentPosition = newPosition;
  updateDisplay(currentPosition);
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
