// Add this function to capture more context from elements
function getEnhancedElementData(element) {
    const rect = element.getBoundingClientRect();
    
    // Get computed styles
    const styles = window.getComputedStyle(element);
    
    return {
        tagName: element.tagName,
        text: element.innerText || element.textContent || "",
        innerText: element.innerText || "",
        placeholder: element.placeholder || "",
        value: element.value || "",
        type: element.type || "",
        ariaLabel: element.getAttribute("aria-label") || "",
        className: element.className || "",
        id: element.id || "",
        href: element.href || "",
        role: element.getAttribute("role") || "",
        // Add visual properties
        backgroundColor: styles.backgroundColor,
        color: styles.color,
        fontWeight: styles.fontWeight,
        fontSize: styles.fontSize,
        // Position
        position: {
            x: rect.x,
            y: rect.y,
            width: rect.width,
            height: rect.height
        },
        // Check if element is clickable
        isClickable: element.onclick !== null || 
                     element.getAttribute("onclick") !== null ||
                     element.tagName === "BUTTON" ||
                     element.tagName === "A" ||
                     element.getAttribute("role") === "button"
    };
}

// Update the detectElement function
async function detectElement(element, elementId) {
    try {
        const elementData = getEnhancedElementData(element);
        const imageData = await captureElementImage(element);
        
        if (!imageData) return null;
        
        // Send to background script with timeout
        const result = await Promise.race([
            chrome.runtime.sendMessage({
                action: "detect",
                imageData: imageData,
                elementData: elementData
            }),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error("Detection timeout")), 10000)
            )
        ]);
        
        return result;
    } catch (error) {
        console.error("Detection error:", error);
        return null;
    }
}

// Add visual indicator while scanning
function showScanningIndicator() {
    const indicator = document.createElement("div");
    indicator.id = "dp-scanning-indicator";
    indicator.innerHTML = `
        <div style="
            position: fixed;
            top: 10px;
            right: 10px;
            background: #e94560;
            color: white;
            padding: 8px 16px;
            border-radius: 8px;
            z-index: 100000;
            font-family: monospace;
            font-size: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        ">
            🔍 Scanning for dark patterns...
        </div>
    `;
    document.body.appendChild(indicator);
    
    setTimeout(() => {
        if (indicator) indicator.remove();
    }, 3000);
}