// Content script for Dark Pattern Detector - Simplified working version
let detectionActive = false;
let highlightedElements = new Map();
let isScanning = false;

// Elements to scan
const SCAN_ELEMENTS = [
    "button", "a", "div", "span", "p", "label", 
    "[class*='offer']", "[class*='deal']", "[class*='scarcity']",
    "[class*='urgency']", "[class*='timer']", "[class*='discount']"
];

// Law mapping
const LAW_MAPPING_DATA = {
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
            {"name": "GDPR", "articles": ["Article 5(1)(a)"], "violation": "Artificial urgency pressure"},
            {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Creates psychological pressure"},
            {"name": "FTC", "articles": ["Section 5"], "violation": "False urgency"}
        ]
    },
    "confirmshaming": {
        "name": "Confirmshaming",
        "description": "Users are guilt-tripped for rejecting data sharing.",
        "laws": [
            {"name": "GDPR", "articles": ["Article 5"], "violation": "Emotional manipulation"},
            {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Emotional manipulation"},
            {"name": "FTC", "articles": ["Section 5"], "violation": "Deceptive marketing"}
        ]
    },
    "automatic_renewal": {
        "name": "Automatic Renewal",
        "description": "Free trial automatically converts to paid subscription.",
        "laws": [
            {"name": "GDPR", "articles": ["Article 7"], "violation": "Lack of clear disclosure"},
            {"name": "CCPA", "articles": ["Section 1798.135"], "violation": "Unclear renewal conditions"},
            {"name": "FTC", "articles": ["ROSCA"], "violation": "Users unknowingly enter subscriptions"}
        ]
    },
    "cookie_wall": {
        "name": "Cookie Wall",
        "description": "Access blocked unless users accept cookies.",
        "laws": [
            {"name": "GDPR", "articles": ["Article 7"], "violation": "Coerced consent"},
            {"name": "CCPA", "articles": ["Section 1798.120"], "violation": "Refusal prevents service access"},
            {"name": "FTC", "articles": ["Section 5"], "violation": "Coercive consent mechanism"}
        ]
    }
};

function getLawMapping(pattern) {
    return LAW_MAPPING_DATA[pattern] || {
        "name": pattern.replace(/_/g, " ").toUpperCase(),
        "description": "Dark pattern detected",
        "laws": [
            {"name": "GDPR", "articles": ["Article 5"], "violation": "Unfair business practices"},
            {"name": "FTC", "articles": ["Section 5"], "violation": "Deceptive practices"}
        ]
    };
}

// Get element data
function getElementData(element) {
    const rect = element.getBoundingClientRect();
    let text = (element.innerText || element.textContent || "").trim();
    
    if (rect.width === 0 || rect.height === 0) return null;
    if (text.length < 3) return null;
    
    // If element text is small, try to get parent context for better pattern matching
    if (text.length < 100) {
        const parent = element.closest('[class*="offer"], [class*="deal"], [class*="sale"], [class*="price"], [class*="cart"]');
        if (parent && parent !== element) {
            const parentText = (parent.innerText || parent.textContent || "").trim();
            if (parentText.length > text.length && parentText.length < 500) {
                text = parentText;  // Use parent context if it's more complete
            }
        }
    }
    
    return {
        tagName: element.tagName,
        text: text.substring(0, 500),
        innerText: text.substring(0, 500),
        className: element.className || "",
        id: element.id || ""
    };
}

// Capture element image
async function captureElementImage(element) {
    try {
        const rect = element.getBoundingClientRect();
        if (rect.width < 10 || rect.height < 10) return null;
        
        const canvas = document.createElement('canvas');
        canvas.width = Math.min(rect.width, 150);
        canvas.height = Math.min(rect.height, 150);
        const ctx = canvas.getContext('2d');
        
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        const text = (element.innerText || element.textContent || "").trim();
        if (text) {
            ctx.fillStyle = '#000000';
            ctx.font = '12px Arial';
            ctx.textAlign = 'center';
            ctx.fillText(text.substring(0, 50), canvas.width / 2, canvas.height / 2);
        }
        
        return canvas.toDataURL("image/jpeg", 0.5);
    } catch (error) {
        return null;
    }
}

// Detect element
async function detectElement(element) {
    try {
        const elementData = getElementData(element);
        if (!elementData) return null;
        
        const imageData = await captureElementImage(element);
        
        const result = await new Promise((resolve) => {
            const timeout = setTimeout(() => resolve(null), 8000);
            
            chrome.runtime.sendMessage({
                action: "detect",
                imageData: imageData || "",
                elementData: elementData
            }, (response) => {
                clearTimeout(timeout);
                if (chrome.runtime.lastError) {
                    resolve(null);
                } else {
                    resolve(response);
                }
            });
        });
        
        return result;
    } catch (error) {
        return null;
    }
}

// Highlight element
function highlightElement(element, detectionResult) {
    if (!detectionResult || !detectionResult.detected) return;
    
    const elementId = `dp_${Date.now()}_${Math.random()}`;
    const pattern = detectionResult.pattern;
    
    console.log(`🎯 HIGHLIGHTING: ${pattern} (${Math.round(detectionResult.confidence * 100)}%)`);
    
    // Remove existing highlight from this element
    if (element.hasAttribute('data-dark-pattern')) {
        removeHighlightFromElement(element);
    }
    
    // Store original styles
    const originalOutline = element.style.outline;
    const originalBg = element.style.backgroundColor;
    
    // Apply highlight
    element.style.outline = "3px solid #ff3366";
    element.style.outlineOffset = "2px";
    element.style.backgroundColor = "rgba(255, 51, 102, 0.1)";
    element.style.cursor = "pointer";
    element.style.position = "relative";
    element.style.zIndex = "10000";
    
    element.setAttribute("data-dark-pattern", pattern);
    element.setAttribute("data-dark-pattern-confidence", detectionResult.confidence);
    element.setAttribute("data-original-outline", originalOutline);
    element.setAttribute("data-original-bg", originalBg);
    
    // Store in map
    highlightedElements.set(element, {
        patternInfo: detectionResult,
        originalOutline: originalOutline,
        originalBg: originalBg
    });
    
    // Add click handler
    const clickHandler = (e) => {
        e.stopPropagation();
        showDetails(element, detectionResult);
    };
    element.removeEventListener('click', clickHandler);
    element.addEventListener('click', clickHandler);
    element.setAttribute('data-click-handler', 'true');
    
    // Add badge
    addBadge(element, detectionResult);
}

function removeHighlightFromElement(element) {
    const originalOutline = element.getAttribute('data-original-outline') || '';
    const originalBg = element.getAttribute('data-original-bg') || '';
    
    element.style.outline = originalOutline;
    element.style.backgroundColor = originalBg;
    element.style.cursor = '';
    
    element.removeAttribute('data-dark-pattern');
    element.removeAttribute('data-dark-pattern-confidence');
    element.removeAttribute('data-original-outline');
    element.removeAttribute('data-original-bg');
    
    // Remove badge
    const badge = element.querySelector('.dark-pattern-badge');
    if (badge) badge.remove();
}

function addBadge(element, detectionResult) {
    if (element.querySelector('.dark-pattern-badge')) return;
    
    const badge = document.createElement("div");
    badge.className = "dark-pattern-badge";
    badge.style.cssText = `
        position: absolute !important;
        top: -24px !important;
        right: 0 !important;
        background: #ff3366 !important;
        color: white !important;
        font-size: 10px !important;
        font-family: monospace !important;
        font-weight: bold !important;
        padding: 2px 8px !important;
        border-radius: 12px !important;
        z-index: 10001 !important;
        white-space: nowrap !important;
        pointer-events: none !important;
    `;
    badge.textContent = `⚠️ ${detectionResult.pattern.replace(/_/g, ' ').toUpperCase()}`;
    element.appendChild(badge);
}

function showDetails(element, detectionResult) {
    const pattern = detectionResult.pattern;
    const confidence = Math.round(detectionResult.confidence * 100);
    const lawMapping = getLawMapping(pattern);
    
    const modal = document.createElement("div");
    modal.style.cssText = `
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100% !important;
        height: 100% !important;
        background: rgba(0,0,0,0.9) !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        z-index: 100000 !important;
    `;
    
    modal.innerHTML = `
        <div style="background: #1a1a2e; border-radius: 16px; max-width: 500px; width: 90%; border: 2px solid #ff3366;">
            <div style="padding: 20px; border-bottom: 1px solid #333;">
                <h3 style="color: #ff3366; margin: 0;">⚠️ Dark Pattern Detected</h3>
            </div>
            <div style="padding: 20px;">
                <h4 style="color: #ffd966; margin: 0 0 10px 0;">${lawMapping.name}</h4>
                <p style="color: #ccc; font-size: 14px;">${lawMapping.description}</p>
                
                <div style="margin: 15px 0;">
                    <div style="background: #333; height: 8px; border-radius: 4px;">
                        <div style="background: #ff3366; width: ${confidence}%; height: 100%; border-radius: 4px;"></div>
                    </div>
                    <p style="color: #ffd966; margin: 5px 0 0 0;">Confidence: ${confidence}%</p>
                </div>
                
                <div style="background: #0f0f1a; padding: 15px; border-radius: 8px; margin: 15px 0;">
                    <strong style="color: #ffd966;">📜 Violated Laws:</strong>
                    <ul style="margin: 10px 0 0 20px; color: #ccc;">
                        ${lawMapping.laws.map(law => `<li><strong>${law.name}</strong>: ${law.violation}</li>`).join('')}
                    </ul>
                </div>
                
                <div style="background: rgba(255,51,102,0.1); padding: 15px; border-radius: 8px;">
                    <strong style="color: #ff6699;">⚠️ Why This Matters:</strong>
                    <p style="color: #ccc; margin: 5px 0 0 0;">This deceptive design pattern manipulates user behavior and may violate consumer protection laws.</p>
                </div>
            </div>
            <div style="padding: 15px 20px; border-top: 1px solid #333; text-align: right;">
                <button id="closeModalBtn" style="background: #ff3366; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer;">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.getElementById('closeModalBtn').addEventListener('click', () => modal.remove());
    modal.addEventListener('click', (e) => { if (e.target === modal) modal.remove(); });
}

// Scan page
async function scanPage() {
    if (!detectionActive || isScanning) return;
    
    isScanning = true;
    console.log("🔍 Scanning for dark patterns...");
    
    // Get all potential elements
    const allElements = document.querySelectorAll('*');
    const candidates = [];
    
    for (const el of allElements) {
        const text = (el.innerText || el.textContent || "").trim();
        const rect = el.getBoundingClientRect();
        
        // Check if element has meaningful text and is visible
        if (text.length > 5 && text.length < 200 && rect.width > 0 && rect.height > 0) {
            // Check for dark pattern keywords
            const lowerText = text.toLowerCase();
            const darkKeywords = ['only', 'left', 'stock', 'hurry', 'limited', 'expires', 'timer', 
                                  'countdown', 'discount', 'free trial', 'auto-renew', 'cookie', 
                                  'accept', 'reject', 'subscribe', 'unsubscribe'];
            
            if (darkKeywords.some(kw => lowerText.includes(kw))) {
                candidates.push(el);
            }
        }
    }
    
    console.log(`Found ${candidates.length} candidate elements`);
    
    let detected = 0;
    for (let i = 0; i < candidates.length; i++) {
        const element = candidates[i];
        const result = await detectElement(element);
        
        if (result && result.detected) {
            highlightElement(element, result);
            detected++;
            console.log(`✅ Detected ${result.pattern} on element ${i}`);
        }
        
        // Small delay
        await new Promise(r => setTimeout(r, 50));
    }
    
    console.log(`✅ Scan complete! Detected ${detected} dark patterns`);
    isScanning = false;
    
    // Update popup if needed
    chrome.runtime.sendMessage({ action: "updateCount", count: detected });
}

// Start/Stop
function startDetection() {
    console.log("Starting detection...");
    detectionActive = true;
    scanPage();
}

function stopDetection() {
    console.log("Stopping detection...");
    detectionActive = false;
    isScanning = false;
    
    // Clear all highlights
    highlightedElements.forEach((_, element) => {
        removeHighlightFromElement(element);
    });
    highlightedElements.clear();
}

// ============================================================================
// PDF REPORT GENERATION (added from old version)
// ============================================================================

function getDetailedSuggestionForPattern(patternType) {
    const suggestions = {
        'fake_scarcity': 'Remove artificial scarcity messages. Display actual stock levels honestly. Use factual statements like "In stock" or "Available" instead of misleading urgency.',
        'urgency_messaging': 'Replace countdown timers with clear deadlines if they are real. For fake timers, remove them entirely. Be transparent about offer durations.',
        'confirmshaming': 'Use neutral language for both options. Replace "No thanks, I like paying more" with "No, thank you" or similar neutral alternatives.',
        'automatic_renewal': 'Implement clear opt-in for subscriptions. Send reminders before renewal. Make cancellation process simple and accessible in one click.',
        'hidden_costs': 'Display all costs upfront, including taxes and fees. Use clear pricing with no surprise charges at checkout.',
        'cookie_wall': 'Provide genuine choice for cookie consent. Don\'t block access for rejecting. Make "Reject all" as prominent as "Accept all".',
        'interface_interference': 'Design neutral interfaces where no option is visually emphasized over others. Use consistent styling for all choices.',
        'privacy_zuckering': 'Be transparent about data collection. Get explicit consent before sharing data. Don\'t hide data sharing in complex settings.',
        'roach_motel': 'Make cancellation as easy as signup. Provide one-click unsubscribe. Allow data deletion without friction.',
        'misleading_discounts': 'Show actual savings based on real prices. Don\'t inflate original prices. Be honest about discount percentages.',
        'continuous_prompting': 'Limit prompts to reasonable frequency. Respect user decisions. Don\'t repeatedly ask after rejection.',
        'drip_pricing': 'Show total price upfront including all fees. Don\'t add charges at final step. Be transparent about all costs.',
        'skipping': 'Ensure consent is obtained before data collection. Don\'t bypass privacy steps. Make all options visible and accessible.',
        'countdown_timer_pressure': 'Remove fake timers. If there is a real deadline, display it clearly without pressure tactics.'
    };
    return suggestions[patternType] || 'Review the design element to ensure it follows ethical design principles. Avoid manipulative patterns that deceive users.';
}

function generateHTMLReport(detectedPatterns, pageUrl, pageTitle) {
    const now = new Date();
    const totalPatterns = detectedPatterns.length;
    const uniquePatterns = [...new Set(detectedPatterns.map(p => p.pattern))];

    // Count pattern distribution
    const patternCount = {};
    detectedPatterns.forEach(p => {
        patternCount[p.pattern] = (patternCount[p.pattern] || 0) + 1;
    });

    // Generate patterns table with law explanations
    let patternsTableHtml = '';
    detectedPatterns.forEach((pattern, index) => {
        const suggestion = getDetailedSuggestionForPattern(pattern.pattern);
        const confidence = Math.round(pattern.confidence * 100);
        const patternName = pattern.pattern.replace(/_/g, ' ').toUpperCase();

        // Get law info - support both array of laws directly and object with .laws property
        const lawsArray = Array.isArray(pattern.laws) ? pattern.laws : (pattern.laws && pattern.laws.laws ? pattern.laws.laws : []);

        let lawExplanationsHtml = '';
        if (lawsArray.length > 0) {
            lawExplanationsHtml = lawsArray.map(law => {
                const articlesList = law.articles ? law.articles.map(article => `
                    <div style="margin-bottom: 12px;">
                        <strong style="color: #ff6699;">${article}</strong>
                    </div>
                `).join('') : '<div>Multiple provisions violated</div>';

                return `
                    <div style="margin-bottom: 16px; padding: 12px; background: #0f0f1a; border-radius: 8px; border-left: 3px solid #ff3366;">
                        <strong style="color: #ffd966;">${law.name}</strong>
                        <div style="margin-top: 8px;">
                            ${articlesList}
                        </div>
                        <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid #2a2a3e;">
                            <em style="font-size: 11px; color: #888;">${law.violation || "This pattern manipulates user behavior."}</em>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            lawExplanationsHtml = '<div style="color: #888; padding: 12px;">No specific law mapping available</div>';
        }

        patternsTableHtml += `
            <tr style="border-bottom: 1px solid #ddd;">
                <td style="padding: 12px; vertical-align: top;">${index + 1}</td>
                <td style="padding: 12px; vertical-align: top;">
                    <strong style="color: #ff3366;">${patternName}</strong>
                </td>
                <td style="padding: 12px; vertical-align: top;">
                    <div style="background: #f0f0f0; border-radius: 10px; height: 20px; width: 100%; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #ff3366, #ff6699); width: ${confidence}%; height: 100%; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px;">
                            ${confidence}%
                        </div>
                    </div>
                </td>
                <td style="padding: 12px; vertical-align: top; font-size: 11px; color: #666;">
                    "${pattern.text ? pattern.text.substring(0, 100) + '...' : 'No text detected'}"
                </td>
                <td style="padding: 12px; vertical-align: top; min-width: 300px;">
                    ${lawExplanationsHtml}
                </td>
                <td style="padding: 12px; vertical-align: top; font-size: 11px; color: #444;">
                    ${suggestion}
                </td>
            </tr>
        `;
    });

    // Generate distribution HTML
    let distributionHtml = '';
    for (const [pattern, count] of Object.entries(patternCount)) {
        const percentage = ((count / totalPatterns) * 100).toFixed(1);
        distributionHtml += `
            <div style="margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                    <span style="font-size: 12px;">${pattern.replace(/_/g, ' ').toUpperCase()}</span>
                    <span style="font-size: 12px; color: #ff3366;">${count} (${percentage}%)</span>
                </div>
                <div style="background: #e0e0e0; border-radius: 10px; height: 8px; overflow: hidden;">
                    <div style="background: #ff3366; width: ${percentage}%; height: 100%;"></div>
                </div>
            </div>
        `;
    }

    return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Dark Pattern Detection Report with Legal Analysis</title>
            <style>
                @media print {
                    body { print-color-adjust: exact; -webkit-print-color-adjust: exact; }
                    .no-print { display: none; }
                }
                * { margin: 0; padding: 0; box-sizing: border-box; }
                body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif; background: #f5f5f5; padding: 40px 20px; line-height: 1.6; }
                .report-container { max-width: 1400px; margin: 0 auto; background: white; border-radius: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); overflow: hidden; }
                .header { background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); color: white; padding: 40px; border-bottom: 4px solid #ff3366; }
                .header h1 { font-size: 28px; margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
                .header .meta { color: #aaa; font-size: 12px; margin-top: 20px; padding-top: 20px; border-top: 1px solid #2a2a3e; }
                .summary { padding: 30px 40px; background: #fafafa; border-bottom: 1px solid #e0e0e0; }
                .summary h2 { color: #ff3366; font-size: 20px; margin-bottom: 20px; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }
                .stat-card { background: white; padding: 20px; border-radius: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #e0e0e0; }
                .stat-value { font-size: 36px; font-weight: bold; color: #ff3366; margin-bottom: 8px; }
                .stat-label { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 1px; }
                .distribution { background: white; padding: 20px; border-radius: 12px; border: 1px solid #e0e0e0; margin-bottom: 20px; }
                .distribution h3 { color: #333; font-size: 16px; margin-bottom: 15px; }
                .legal-note { background: #e8f0fe; border-left: 4px solid #ff3366; padding: 15px; border-radius: 8px; font-size: 12px; }
                .patterns-section { padding: 30px 40px; }
                .patterns-section h2 { color: #ff3366; font-size: 20px; margin-bottom: 20px; }
                table { width: 100%; border-collapse: collapse; font-size: 11px; }
                th { background: #1a1a2e; color: white; padding: 12px; text-align: left; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
                td { padding: 12px; border-bottom: 1px solid #e0e0e0; vertical-align: top; }
                .footer { background: #1a1a2e; color: #888; padding: 20px 40px; text-align: center; font-size: 10px; border-top: 1px solid #2a2a3e; }
                .warning-box { background: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; border-radius: 8px; }
                .no-print { text-align: center; padding: 20px; background: white; margin-top: 20px; border-radius: 8px; }
                .no-print button { background: #ff3366; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-size: 14px; cursor: pointer; margin: 0 10px; font-weight: bold; }
                .no-print button:hover { background: #cc0044; }
            </style>
        </head>
        <body>
            <div class="report-container">
                <div class="header">
                    <h1><span>⚖️</span> Dark Pattern Detection Report with Legal Analysis</h1>
                    <p style="color: #aaa; margin-top: 10px;">Comprehensive analysis of deceptive design patterns with detailed legal explanations</p>
                    <div class="meta">
                        <div>📄 Page: ${pageTitle || 'Unknown'}</div>
                        <div>🔗 URL: ${pageUrl || 'Unknown'}</div>
                        <div>📅 Generated: ${now.toLocaleString()}</div>
                        <div>🤖 Tool: Dark Pattern Detector v2.0 - Legal Compliance Edition</div>
                    </div>
                </div>

                <div class="summary">
                    <h2>📊 Executive Summary</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">${totalPatterns}</div>
                            <div class="stat-label">Total Dark Patterns</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${uniquePatterns.length}</div>
                            <div class="stat-label">Unique Pattern Types</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${detectedPatterns.filter(p => p.confidence > 0.8).length}</div>
                            <div class="stat-label">High Confidence (&gt;80%)</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${detectedPatterns.filter(p => p.confidence > 0.9).length}</div>
                            <div class="stat-label">Critical Issues (&gt;90%)</div>
                        </div>
                    </div>

                    <div class="distribution">
                        <h3>📈 Pattern Distribution</h3>
                        ${distributionHtml}
                    </div>

                    <div class="legal-note">
                        <strong>⚖️ Legal Compliance Note:</strong> The dark patterns identified in this report may violate consumer protection laws including:
                        <ul style="margin: 10px 0 0 20px;">
                            <li><strong>GDPR (EU)</strong> - Articles 5, 7, 12, 25 - Transparency, Fairness, and Consent requirements</li>
                            <li><strong>CCPA/CPRA (California)</strong> - Sections 1798.100, 1798.105, 1798.120, 1798.135, 1798.140 - Consumer privacy rights</li>
                            <li><strong>FTC Act (US)</strong> - Section 5 - Prohibition of unfair or deceptive practices</li>
                            <li><strong>ROSCA</strong> - Online shopping and subscription transparency requirements</li>
                        </ul>
                    </div>

                    <div class="warning-box">
                        <strong>⚠️ Important Note:</strong> Dark patterns are deceptive design techniques that trick users into making decisions they wouldn't otherwise make.
                        These patterns violate consumer protection laws and can result in regulatory penalties, lawsuits, and damage to brand reputation.
                    </div>
                </div>

                <div class="patterns-section">
                    <h2>🔍 Detailed Analysis with Legal Explanations</h2>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Pattern Type</th>
                                <th>Confidence</th>
                                <th>Detected Text</th>
                                <th>Legal Analysis &amp; Violations</th>
                                <th>Remediation Suggestion</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${patternsTableHtml}
                        </tbody>
                    </table>
                </div>

                <div class="footer">
                    <p>This report was generated automatically by the Dark Pattern Detector browser extension.</p>
                    <p style="margin-top: 10px;">For more information about dark patterns and legal compliance, consult with legal counsel.</p>
                    <p style="margin-top: 10px;">© ${now.getFullYear()} Dark Pattern Detector - Promoting Ethical Design &amp; Legal Compliance</p>
                </div>
            </div>

            <div class="no-print">
                <button onclick="window.print()">📄 Save as PDF / Print</button>
                <button onclick="window.close()">❌ Close Window</button>
            </div>

            <script>
                setTimeout(function() {
                    if (confirm('Click OK to save this report as PDF. The browser print dialog will open - choose "Save as PDF" as the destination.')) {
                        window.print();
                    }
                }, 500);
            </script>
        </body>
        </html>
    `;
}

async function generatePDFReport(patterns, pageUrl, pageTitle) {
    try {
        console.log("Content script: Generating PDF report with legal analysis...");
        console.log("Patterns count:", patterns ? patterns.length : 0);

        if (!patterns || patterns.length === 0) {
            throw new Error("No patterns to report");
        }

        const htmlContent = generateHTMLReport(patterns, pageUrl, pageTitle);

        const reportWindow = window.open('', '_blank', 'width=1200,height=800,toolbar=yes,menubar=yes,scrollbars=yes');

        if (!reportWindow) {
            throw new Error("Popup blocked. Please allow popups for this site.");
        }

        reportWindow.document.write(htmlContent);
        reportWindow.document.close();

        console.log("Report window opened successfully");
        return "report_generated";

    } catch (error) {
        console.error("Error generating PDF report:", error);
        throw error;
    }
}

// ============================================================================
// END PDF REPORT GENERATION
// ============================================================================

// Message handler
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    console.log("Content received:", request.action);
    
    if (request.action === "startDetection") {
        startDetection();
        sendResponse({ success: true });
    } else if (request.action === "stopDetection") {
        stopDetection();
        sendResponse({ success: true });
    } else if (request.action === "clearHighlights") {
        highlightedElements.forEach((_, element) => {
            removeHighlightFromElement(element);
        });
        highlightedElements.clear();
        sendResponse({ success: true });
    } else if (request.action === "ping") {
        sendResponse({ success: true });
    } else if (request.action === "getDetectionCount") {
        sendResponse({ count: highlightedElements.size });
    } else if (request.action === "getAllDetectedPatterns") {
        const patterns = Array.from(highlightedElements.values()).map(v => ({
            pattern: v.patternInfo.pattern,
            confidence: v.patternInfo.confidence,
            text: v.patternInfo.text,
            laws: getLawMapping(v.patternInfo.pattern).laws
        }));
        sendResponse({ patterns: patterns });
    } else if (request.action === "generatePDFReport") {
        console.log("Generating PDF report from content script...");
        generatePDFReport(request.patterns, request.pageUrl, request.pageTitle)
            .then(fileName => {
                console.log("Report generation successful");
                sendResponse({ success: true, fileName: fileName });
            })
            .catch(error => {
                console.error("Report generation failed:", error);
                sendResponse({ success: false, error: error.message });
            });
        return true;
    } else {
        sendResponse({ success: false });
    }
    return true;
});

console.log("Dark Pattern Detector content script loaded!");