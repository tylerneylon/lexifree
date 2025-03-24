// Load wordList from server
let wordList = [];

// Fetch words from the server
fetch('/words.json')
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        wordList = data;
        initializeInterface();
    })
    .catch(error => {
        console.error('Error loading words:', error);
    });
    
// Initialize variables
const sliderHandle = document.getElementById('sliderHandle');
const displayArea = document.getElementById('displayArea');
const column1 = document.getElementById('column1');
const column2 = document.getElementById('column2');
const column3 = document.getElementById('column3');

const sliderContainer = document.querySelector('.slider-container');
const sliderWidth = sliderContainer.offsetWidth;
const handleWidth = sliderHandle.offsetWidth;

// Calculate rows based on display area height
function calculateRows() {
    const displayHeight = displayArea.offsetHeight;
    const wordItemHeight = 24; // Approximate height of each word item (font-size + padding)
    return Math.floor(displayHeight / wordItemHeight);
}

let rowsPerColumn = calculateRows();
let wordsPerPage = rowsPerColumn * 3;

// Update display on window resize
window.addEventListener('resize', () => {
    rowsPerColumn = calculateRows();
    wordsPerPage = rowsPerColumn * 3;
    updateDisplay(currentPosition);
});

// Initialize slider position
let isDragging = false;
let startX = 0;
let currentPosition = 0;

// Update displayed words based on slider position with pagination
function updateDisplay(position) {
    // Calculate which page to show (0 to 1 position)
    const normalizedPosition = position / (sliderWidth - handleWidth);
    const wordsPerPage = rowsPerColumn * 3;
    const totalPages = Math.ceil(wordList.length / wordsPerPage);
    
    // Find the closest page to the current position
    let pageIndex = Math.floor(normalizedPosition * totalPages);
    if (pageIndex >= totalPages) pageIndex = totalPages - 1;
    
    // Calculate the start index for this page
    const startIndex = pageIndex * wordsPerPage;
    
    // Clear columns
    column1.innerHTML = '';
    column2.innerHTML = '';
    column3.innerHTML = '';
    
    // Fill columns
    for (let i = 0; i < rowsPerColumn; i++) {
        if (startIndex + i < wordList.length) {
            const wordItem = document.createElement('div');
            wordItem.className = 'word-item';
            wordItem.textContent = wordList[startIndex + i];
            column1.appendChild(wordItem);
        }
        
        if (startIndex + rowsPerColumn + i < wordList.length) {
            const wordItem = document.createElement('div');
            wordItem.className = 'word-item';
            wordItem.textContent = wordList[startIndex + rowsPerColumn + i];
            column2.appendChild(wordItem);
        }
        
        if (startIndex + 2 * rowsPerColumn + i < wordList.length) {
            const wordItem = document.createElement('div');
            wordItem.className = 'word-item';
            wordItem.textContent = wordList[startIndex + 2 * rowsPerColumn + i];
            column3.appendChild(wordItem);
        }
    }
}

// Set initial slider position and display
function setSliderPosition(x) {
    const newPosition = Math.max(0, Math.min(sliderWidth - handleWidth, x));
    sliderHandle.style.left = `${newPosition}px`;
    currentPosition = newPosition;
    updateDisplay(currentPosition);
}

// Mouse and touch event handlers for dragging
sliderHandle.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX - sliderHandle.getBoundingClientRect().left;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    e.preventDefault();
});

function onMouseMove(e) {
    if (isDragging) {
        const containerRect = sliderContainer.getBoundingClientRect();
        const newX = e.clientX - containerRect.left - startX;
        setSliderPosition(newX);
    }
}

function onMouseUp() {
    isDragging = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
}

// Touch support for mobile devices
sliderHandle.addEventListener('touchstart', (e) => {
    isDragging = true;
    startX = e.touches[0].clientX - sliderHandle.getBoundingClientRect().left;
    document.addEventListener('touchmove', onTouchMove, { passive: false });
    document.addEventListener('touchend', onTouchEnd);
    e.preventDefault();
});

function onTouchMove(e) {
    if (isDragging) {
        const containerRect = sliderContainer.getBoundingClientRect();
        const newX = e.touches[0].clientX - containerRect.left - startX;
        setSliderPosition(newX);
        e.preventDefault();
    }
}

function onTouchEnd() {
    isDragging = false;
    document.removeEventListener('touchmove', onTouchMove);
    document.removeEventListener('touchend', onTouchEnd);
}

// Allow clicking on the slider container to jump to that position
sliderContainer.addEventListener('mousedown', (e) => {
    if (e.target !== sliderHandle) {
        const containerRect = sliderContainer.getBoundingClientRect();
        const clickX = e.clientX - containerRect.left - handleWidth / 2;
        setSliderPosition(clickX);
        isDragging = true;
        startX = handleWidth / 2;
        document.addEventListener('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }
});

// Initialize the interface after words are loaded
function initializeInterface() {
    // Initialize the display
    setSliderPosition(0);
    
    // Handle window resize
    window.addEventListener('resize', () => {
        const containerWidth = sliderContainer.offsetWidth;
        const ratio = currentPosition / (sliderWidth - handleWidth);
        sliderWidth = containerWidth;
        setSliderPosition(ratio * (sliderWidth - handleWidth));
    });
}