// Popup script for Dark Pattern Detector
let detectionActive = false;
let serverConnected = false;

// DOM Elements
const detectionSwitch = document.getElementById("detectionSwitch");
const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");
const statsSection = document.getElementById("statsSection");
const actionsSection = document.getElementById("actionsSection");
const detectionCount = document.getElementById("detectionCount");
const scanStatus = document.getElementById("scanStatus");
const clearHighlightsBtn = document.getElementById("clearHighlightsBtn");
const rescanBtn = document.getElementById("rescanBtn");
const showLawsBtn = document.getElementById("showLawsBtn");
const generateReportBtn = document.getElementById("generateReportBtn");
const serverStatusText = document.getElementById("serverStatusText");

// Get current tab
async function getCurrentTab() {
    return new Promise((resolve) => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            resolve(tabs[0]);
        });
    });
}

// Send message to content script
async function sendMessageToContentScript(action, data = {}) {
    try {
        const tab = await getCurrentTab();
        if (!tab || !tab.id) return null;
        
        const response = await chrome.tabs.sendMessage(tab.id, { action, ...data });
        return response;
    } catch (error) {
        console.log(`Error sending ${action}:`, error.message);
        return null;
    }
}

// Check server connection
async function checkServerConnection() {
    try {
        const response = await chrome.runtime.sendMessage({ action: "checkHealth" });
        serverConnected = response && response.connected;
        
        if (serverConnected) {
            serverStatusText.textContent = "Connected";
            serverStatusText.style.color = "#06d6a0";
        } else {
            serverStatusText.textContent = "Not Connected";
            serverStatusText.style.color = "#ff3366";
        }
        
        return serverConnected;
    } catch (error) {
        serverStatusText.textContent = "Error";
        serverStatusText.style.color = "#ff3366";
        serverConnected = false;
        return false;
    }
}

// Get detection count
async function getDetectionCount() {
    try {
        const response = await sendMessageToContentScript("getDetectionCount");
        return response ? response.count : 0;
    } catch (error) {
        return 0;
    }
}

// Update stats
async function updateStats() {
    if (!detectionActive) return;
    
    const count = await getDetectionCount();
    detectionCount.textContent = count;
    
    if (count > 0) {
        detectionCount.style.color = "#ff3366";
        scanStatus.textContent = `${count} pattern${count !== 1 ? 's' : ''} found`;
        scanStatus.style.color = "#ffd966";
    } else {
        detectionCount.style.color = "#06d6a0";
        scanStatus.textContent = "Scanning";
        scanStatus.style.color = "#aaa";
    }
}

// Start detection
async function startDetection() {
    try {
        const response = await sendMessageToContentScript("startDetection");
        
        if (response && response.success) {
            detectionActive = true;
            scanStatus.textContent = "Active";
            scanStatus.style.color = "#06d6a0";
            
            statsSection.style.display = "flex";
            actionsSection.style.display = "flex";
            
            startStatsUpdate();
            showNotification("Dark pattern detection enabled", "success");
            return true;
        }
        return false;
    } catch (error) {
        console.error("Error starting detection:", error);
        showNotification("Failed to start detection. Make sure you're on a web page.", "error");
        return false;
    }
}

// Stop detection
async function stopDetection() {
    try {
        const response = await sendMessageToContentScript("stopDetection");
        
        if (response && response.success) {
            detectionActive = false;
            scanStatus.textContent = "Stopped";
            scanStatus.style.color = "#888";
            detectionCount.textContent = "0";
            
            statsSection.style.display = "none";
            actionsSection.style.display = "none";
            
            stopStatsUpdate();
            showNotification("Dark pattern detection disabled", "info");
            return true;
        }
        return false;
    } catch (error) {
        console.error("Error stopping detection:", error);
        return false;
    }
}

// Clear highlights
async function clearHighlights() {
    try {
        const response = await sendMessageToContentScript("clearHighlights");
        if (response && response.success) {
            detectionCount.textContent = "0";
            showNotification("Highlights cleared", "info");
        }
    } catch (error) {
        console.error("Error clearing highlights:", error);
    }
}

// Rescan page
async function rescanPage() {
    try {
        showNotification("Rescanning page...", "info");
        
        if (detectionActive) {
            await stopDetection();
            setTimeout(async () => {
                await startDetection();
            }, 500);
        } else {
            await startDetection();
            detectionSwitch.checked = true;
        }
    } catch (error) {
        console.error("Error rescanning:", error);
        showNotification("Error rescanning page", "error");
    }
}

// Generate PDF report
async function generatePDFReport() {
    try {
        console.log("Generate PDF report clicked");
        
        const reportBtn = document.getElementById("generateReportBtn");
        const originalText = reportBtn.textContent;
        reportBtn.textContent = "⏳ Generating...";
        reportBtn.disabled = true;
        
        const tab = await getCurrentTab();
        
        // Check if content script is loaded
        const pingResponse = await sendMessageToContentScript("ping");
        if (!pingResponse || !pingResponse.success) {
            showNotification("Please refresh the page and try again.", "error");
            reportBtn.textContent = originalText;
            reportBtn.disabled = false;
            return;
        }
        
        // Get all detected patterns
        const patternsResponse = await sendMessageToContentScript("getAllDetectedPatterns");
        
        if (!patternsResponse || !patternsResponse.patterns || patternsResponse.patterns.length === 0) {
            showNotification("No dark patterns detected on this page to generate report.", "info");
            reportBtn.textContent = originalText;
            reportBtn.disabled = false;
            return;
        }
        
        showNotification(`Generating report for ${patternsResponse.patterns.length} patterns...`, "info");
        
        // Generate report
        const reportResult = await sendMessageToContentScript("generatePDFReport", {
            patterns: patternsResponse.patterns,
            pageUrl: tab.url,
            pageTitle: tab.title
        });
        
        if (reportResult && reportResult.success) {
            showNotification("Report generated! A new window will open.", "success");
        } else {
            showNotification("Failed to generate report: " + (reportResult?.error || "Unknown error"), "error");
        }
        
        reportBtn.textContent = originalText;
        reportBtn.disabled = false;
        
    } catch (error) {
        console.error("Error generating report:", error);
        showNotification("Error generating report: " + error.message, "error");
        
        const reportBtn = document.getElementById("generateReportBtn");
        if (reportBtn) {
            reportBtn.textContent = "📄 Generate PDF Report";
            reportBtn.disabled = false;
        }
    }
}

// Show law mappings modal
async function showLawMappings() {
    try {
        showNotification("Loading law mappings...", "info");
        
        const patterns = await chrome.runtime.sendMessage({ action: "getPatterns" });
        
        if (!patterns || Object.keys(patterns).length === 0) {
            showNotification("Could not load law mappings", "error");
            return;
        }
        
        const modal = document.createElement("div");
        modal.className = "law-modal-overlay";
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.9);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 100000;
        `;
        
        let patternsHtml = "";
        for (const [key, pattern] of Object.entries(patterns)) {
            if (pattern && pattern.laws && pattern.laws.length > 0) {
                patternsHtml += `
                    <div style="margin-bottom: 20px; padding: 16px; background: #1a1a2e; border-radius: 12px; border-left: 3px solid #ff3366;">
                        <h4 style="color: #ffd966; margin: 0 0 8px 0;">${pattern.name || key.replace(/_/g, " ").toUpperCase()}</h4>
                        <p style="margin: 0 0 12px 0; font-size: 12px; color: #aaa;">${pattern.description || "Deceptive design pattern"}</p>
                        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                            ${pattern.laws.map(law => `
                                <span style="background: #ff3366; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold;">${law.name}</span>
                            `).join("")}
                        </div>
                    </div>
                `;
            }
        }
        
        modal.innerHTML = `
            <div style="background: #0f0f1a; border-radius: 20px; max-width: 600px; width: 90%; max-height: 80vh; overflow-y: auto; border: 2px solid #ff3366;">
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 20px; border-bottom: 1px solid #2a2a3e;">
                    <h3 style="margin: 0; color: #ff3366;">📜 Dark Pattern Law Mappings</h3>
                    <button id="closeLawModal" style="background: none; border: none; color: white; font-size: 24px; cursor: pointer;">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <div style="background: #1a1a2e; padding: 12px; border-radius: 8px; margin-bottom: 20px;">
                        <p style="margin: 0; font-size: 12px; color: #aaa;">Based on GDPR, CCPA/CPRA, and FTC regulations. Each dark pattern violates specific consumer protection laws.</p>
                    </div>
                    ${patternsHtml}
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeBtn = modal.querySelector("#closeLawModal");
        closeBtn.addEventListener("click", () => modal.remove());
        modal.addEventListener("click", (e) => {
            if (e.target === modal) modal.remove();
        });
        
    } catch (error) {
        console.error("Error showing law mappings:", error);
        showNotification("Error loading law mappings", "error");
    }
}

// Show notification
function showNotification(message, type = "info") {
    let notification = document.querySelector(".popup-notification");
    
    if (!notification) {
        notification = document.createElement("div");
        notification.className = "popup-notification";
        notification.style.cssText = `
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            padding: 10px;
            border-radius: 8px;
            font-size: 12px;
            text-align: center;
            z-index: 1000;
            animation: slideUp 0.3s ease;
        `;
        document.querySelector(".popup-container").appendChild(notification);
    }
    
    notification.textContent = message;
    notification.style.background = type === "success" ? "rgba(6, 214, 160, 0.9)" : 
                                    type === "error" ? "rgba(255, 51, 102, 0.9)" : 
                                    "rgba(255, 209, 102, 0.9)";
    notification.style.color = type === "info" ? "#0f0f1a" : "white";
    notification.style.display = "block";
    
    setTimeout(() => {
        notification.style.display = "none";
    }, 3000);
}

// Stats update timer
let statsUpdateInterval = null;

function startStatsUpdate() {
    if (statsUpdateInterval) clearInterval(statsUpdateInterval);
    statsUpdateInterval = setInterval(updateStats, 2000);
    updateStats();
}

function stopStatsUpdate() {
    if (statsUpdateInterval) {
        clearInterval(statsUpdateInterval);
        statsUpdateInterval = null;
    }
}

// Update status badge
function updateStatusBadge(connected) {
    if (connected) {
        statusBadge.className = "status-badge connected";
        statusText.textContent = "Ready";
    } else {
        statusBadge.className = "status-badge disconnected";
        statusText.textContent = "Server Offline";
    }
}

// Load saved state
async function loadSavedState() {
    return new Promise((resolve) => {
        chrome.storage.local.get(["detectionActive"], (result) => {
            detectionActive = result.detectionActive || false;
            detectionSwitch.checked = detectionActive;
            resolve(detectionActive);
        });
    });
}

// Save state
async function saveState() {
    chrome.storage.local.set({ detectionActive: detectionActive });
}

// Initialize
async function init() {
    const connected = await checkServerConnection();
    updateStatusBadge(connected);
    
    const wasActive = await loadSavedState();
    
    if (wasActive) {
        const response = await sendMessageToContentScript("ping");
        
        if (response && response.success) {
            startDetection();
        } else {
            detectionActive = false;
            detectionSwitch.checked = false;
            showNotification("Please reload the page to enable detection", "info");
        }
    } else {
        statsSection.style.display = "none";
        actionsSection.style.display = "none";
    }
    
    // Event listeners
    detectionSwitch.addEventListener("change", async (e) => {
        const isEnabled = e.target.checked;
        
        if (isEnabled) {
            const success = await startDetection();
            if (!success) {
                detectionSwitch.checked = false;
                return;
            }
        } else {
            await stopDetection();
        }
        
        detectionActive = isEnabled;
        await saveState();
    });
    
    if (clearHighlightsBtn) {
        clearHighlightsBtn.addEventListener("click", clearHighlights);
    }
    
    if (rescanBtn) {
        rescanBtn.addEventListener("click", rescanPage);
    }
    
    if (showLawsBtn) {
        showLawsBtn.addEventListener("click", showLawMappings);
    }
    
    if (generateReportBtn) {
        generateReportBtn.addEventListener("click", generatePDFReport);
    }
    
    setInterval(async () => {
        const connected = await checkServerConnection();
        updateStatusBadge(connected);
        
        if (!connected && detectionActive) {
            showNotification("Server disconnected. Detection may not work.", "error");
        }
    }, 10000);
    
    console.log("Dark Pattern Detector popup initialized");
}

init();