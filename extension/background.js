// Background service worker for Dark Pattern Detector
// Handles API communication, server health checks, and message routing

const API_URL = "http://127.0.0.1:5000";
let serverConnected = false;
let connectionCheckInterval = null;

// ============================================================================
// Server Connection Management
// ============================================================================

async function checkServerHealth() {
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000);
        
        const response = await fetch(`${API_URL}/health`, {
            method: 'GET',
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const data = await response.json();
            serverConnected = data.status === "healthy";
            console.log(`Server health check: ${serverConnected ? "Connected" : "Disconnected"}`);
            return serverConnected;
        }
        serverConnected = false;
        return false;
    } catch (error) {
        console.log("Server not reachable:", error.message);
        serverConnected = false;
        return false;
    }
}

// Start periodic server health checks
function startHealthChecks() {
    if (connectionCheckInterval) {
        clearInterval(connectionCheckInterval);
    }
    connectionCheckInterval = setInterval(async () => {
        await checkServerHealth();
    }, 30000);
}

// Initialize health checks
startHealthChecks();

// ============================================================================
// API Communication Functions
// ============================================================================

async function detectDarkPattern(imageData, elementData) {
    if (!serverConnected) {
        console.log("Server not connected, using fallback detection");
        return getFallbackDetection(elementData);
    }
    
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 15000);
        
        const response = await fetch(`${API_URL}/detect`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                image: imageData,
                element: elementData
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (response.ok) {
            const result = await response.json();
            console.log(`Detection result: ${result.detected ? result.pattern : "None"} (${Math.round(result.confidence * 100)}%)`);
            return result;
        }
        
        return getFallbackDetection(elementData);
        
    } catch (error) {
        console.error("Detection error:", error);
        return getFallbackDetection(elementData);
    }
}

function getFallbackDetection(elementData) {
    const text = (elementData.text || elementData.innerText || "").toLowerCase();
    
    // Keyword-based fallback detection
    if (text.includes("only") && (text.includes("left") || text.includes("stock"))) {
        return {
            detected: true,
            pattern: "fake_scarcity",
            confidence: 0.85,
            text: text.substring(0, 200)
        };
    }
    if (text.includes("hurry") || text.includes("limited") || text.includes("expires")) {
        return {
            detected: true,
            pattern: "urgency_messaging",
            confidence: 0.80,
            text: text.substring(0, 200)
        };
    }
    if ((text.includes("yes") && text.includes("discount")) || (text.includes("no") && text.includes("full price"))) {
        return {
            detected: true,
            pattern: "confirmshaming",
            confidence: 0.85,
            text: text.substring(0, 200)
        };
    }
    if (text.includes("accept") && text.includes("cookie")) {
        return {
            detected: true,
            pattern: "cookie_wall",
            confidence: 0.75,
            text: text.substring(0, 200)
        };
    }
    if (text.includes("subscribe") && text.includes("auto-renew")) {
        return {
            detected: true,
            pattern: "automatic_renewal",
            confidence: 0.80,
            text: text.substring(0, 200)
        };
    }
    
    return { detected: false, pattern: null, confidence: 0.0 };
}

async function getLawInfo(patternName) {
    const lawMapping = {
        "fake_scarcity": {
            "name": "Fake Scarcity",
            "description": "False urgency messages like 'Only 2 left in stock'.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5(1)(a)"], "violation": "Artificial scarcity pressure triggers impulsive buying"},
                {"name": "CCPA", "articles": ["Section 1798.100"], "violation": "Misleading product information"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "False advertising"}
            ]
        },
        "urgency_messaging": {
            "name": "Urgency Messaging",
            "description": "Messages creating false urgency to prompt immediate action.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5(1)(a)"], "violation": "Artificial urgency pressure reduces rational decision-making"},
                {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Creates psychological pressure"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "False urgency to prompt immediate action"}
            ]
        },
        "confirmshaming": {
            "name": "Confirmshaming",
            "description": "Users are guilt-tripped for rejecting data sharing.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5"], "violation": "Emotional manipulation influences users to accept tracking"},
                {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Emotional manipulation to avoid negative messaging"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Deceptive marketing practices"}
            ]
        },
        "automatic_renewal": {
            "name": "Automatic Renewal",
            "description": "Free trial automatically converts into a paid subscription without clear disclosure.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 7"], "violation": "Lack of clear disclosure and exploitation of user inattention"},
                {"name": "CCPA", "articles": ["Section 1798.135"], "violation": "Unclear or hidden renewal conditions"},
                {"name": "FTC", "articles": ["ROSCA"], "violation": "Users unknowingly enter paid subscriptions"}
            ]
        },
        "cookie_wall": {
            "name": "Cookie Wall",
            "description": "Access to service is blocked unless users accept cookies.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 7"], "violation": "Users are coerced into consenting because refusal prevents service access"},
                {"name": "CCPA", "articles": ["Section 1798.120"], "violation": "Refusal prevents service access"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Coercive consent mechanism"}
            ]
        }
    };
    
    return lawMapping[patternName] || {
        "name": patternName.replace(/_/g, " ").toUpperCase(),
        "description": "Dark pattern detected",
        "laws": [
            {"name": "GDPR", "articles": ["Article 5"], "violation": "Unfair business practices"},
            {"name": "FTC", "articles": ["Section 5"], "violation": "Deceptive practices"}
        ]
    };
}

async function getAllPatterns() {
    return {
        "fake_scarcity": {
            "name": "Fake Scarcity",
            "description": "False urgency messages like 'Only 2 left in stock'.",
            "laws": [{"name": "GDPR", "articles": ["Article 5(1)(a)"], "violation": "Artificial scarcity pressure"}]
        },
        "urgency_messaging": {
            "name": "Urgency Messaging",
            "description": "Messages creating false urgency to prompt immediate action.",
            "laws": [{"name": "FTC", "articles": ["Section 5"], "violation": "False urgency"}]
        },
        "confirmshaming": {
            "name": "Confirmshaming",
            "description": "Users are guilt-tripped for rejecting data sharing.",
            "laws": [{"name": "GDPR", "articles": ["Article 5"], "violation": "Emotional manipulation"}]
        }
    };
}

// ============================================================================
// Message Handling
// ============================================================================

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "detect") {
        detectDarkPattern(request.imageData, request.elementData)
            .then(result => sendResponse(result))
            .catch(error => sendResponse({ error: error.message, detected: false }));
        return true;
    }
    
    if (request.action === "getLaws") {
        getLawInfo(request.patternName)
            .then(result => sendResponse(result))
            .catch(error => sendResponse({ error: error.message }));
        return true;
    }
    
    if (request.action === "getPatterns") {
        getAllPatterns()
            .then(result => sendResponse(result))
            .catch(error => sendResponse({ error: error.message }));
        return true;
    }
    
    if (request.action === "checkHealth") {
        checkServerHealth()
            .then(result => sendResponse({ connected: result }))
            .catch(error => sendResponse({ connected: false, error: error.message }));
        return true;
    }
    
    if (request.action === "highlightElement") {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, {
                    action: "highlight",
                    elementId: request.elementId,
                    patternInfo: request.patternInfo
                }).catch(err => console.log("Tab not ready:", err));
            }
        });
        sendResponse({ success: true });
        return true;
    }
    
    if (request.action === "clearHighlights") {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { action: "clearHighlights" })
                    .catch(err => console.log("Tab not ready:", err));
            }
        });
        sendResponse({ success: true });
        return true;
    }
    
    if (request.action === "getServerStatus") {
        sendResponse({ connected: serverConnected });
        return true;
    }
});

chrome.runtime.onInstalled.addListener((details) => {
    console.log("Dark Pattern Detector installed:", details.reason);
    chrome.storage.local.set({
        detectionActive: false,
        settings: {
            autoScan: true,
            highlightColor: "#ff3366",
            showBadges: true,
            scanDelay: 1000
        }
    });
    checkServerHealth();
});

chrome.runtime.onStartup.addListener(() => {
    console.log("Dark Pattern Detector starting up");
    checkServerHealth();
});

console.log("Dark Pattern Detector background service worker loaded");