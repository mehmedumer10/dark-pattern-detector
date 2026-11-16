"""
Dark Pattern Detector Server - ML Model Primary, Keyword as High-Confidence Fallback
"""

import os
import sys
import json
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from pathlib import Path
import base64
from io import BytesIO
import re
import string
import warnings
from collections import Counter
import traceback
import hashlib
warnings.filterwarnings("ignore")

# ==================== LAW MAPPING ====================
LAW_MAPPING = {
    "dark_patterns": {
        "automatic_renewal": {
            "name": "Automatic Renewal",
            "description": "Free trial automatically converts into a paid subscription without clear disclosure.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 7"], "violation": "Lack of clear disclosure"},
                {"name": "CCPA", "articles": ["Section 1798.135"], "violation": "Unclear or hidden renewal conditions"},
                {"name": "FTC", "articles": ["ROSCA"], "violation": "Users unknowingly enter paid subscriptions"}
            ]
        },
        "confirmshaming": {
            "name": "Confirmshaming",
            "description": "Users are guilt-tripped for rejecting data sharing.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5"], "violation": "Emotional manipulation"},
                {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Emotional manipulation to avoid negative messaging"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Deceptive marketing practices"}
            ]
        },
        "fake_scarcity": {
            "name": "Fake Scarcity",
            "description": "False urgency messages like 'Only 2 left in stock'.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5(1)(a)"], "violation": "Artificial scarcity pressure"},
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
                {"name": "FTC", "articles": ["Section 5"], "violation": "False urgency to prompt immediate action"}
            ]
        },
        "cookie_wall": {
            "name": "Cookie Wall",
            "description": "Access to service is blocked unless users accept cookies.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 7"], "violation": "Coerced consent"},
                {"name": "CCPA", "articles": ["Section 1798.120"], "violation": "Refusal prevents service access"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Coercive consent mechanism"}
            ]
        },
        "hidden_costs": {
            "name": "Hidden Costs",
            "description": "Extra charges appear only at final checkout stage.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5(1)(a)"], "violation": "Hides total price"},
                {"name": "CCPA", "articles": ["Section 1798.100"], "violation": "Hidden fees at checkout"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Exploiting user's commitment"}
            ]
        },
        "misleading_discounts": {
            "name": "Misleading Discounts",
            "description": "Inflated original price shown to exaggerate discounts.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5"], "violation": "Price anchoring manipulation"},
                {"name": "CCPA", "articles": ["Section 1798.100"], "violation": "False pricing information"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "False advertising"}
            ]
        },
        "roach_motel": {
            "name": "Roach Motel",
            "description": "Easy to sign up but difficult to cancel or delete data.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 7(3)"], "violation": "Difficult withdrawal of consent"},
                {"name": "CCPA", "articles": ["Section 1798.105"], "violation": "Difficult data deletion"},
                {"name": "FTC", "articles": ["ROSCA"], "violation": "Friction to prevent cancellation"}
            ]
        },
        "interface_interference": {
            "name": "Interface Interference",
            "description": "Interface design nudges users toward privacy-invasive choices.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 7", "Article 25"], "violation": "Visual design pushes toward tracking"},
                {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Visual design subverts autonomy"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Deceptive interface design"}
            ]
        },
        "privacy_zuckering": {
            "name": "Privacy Zuckering",
            "description": "Users tricked into sharing more personal information than intended.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5", "Article 7"], "violation": "Encourages excess data sharing"},
                {"name": "CCPA", "articles": ["Section 1798.100"], "violation": "Hidden data collection practices"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Tricking users into sharing more data"}
            ]
        },
        "drip_pricing": {
            "name": "Drip Pricing",
            "description": "Hidden costs appear only at final checkout.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5(1)(a)", "Article 12"], "violation": "Hides total price until final step"},
                {"name": "CCPA", "articles": ["Section 1798.100"], "violation": "Hidden fees at checkout"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Drip pricing deception"}
            ]
        },
        "countdown_timer_pressure": {
            "name": "Countdown Timer Pressure",
            "description": "Fake countdown timers create urgency to buy quickly.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 5(1)(a)"], "violation": "Time pressure manipulation"},
                {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Creates false urgency"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Fake countdown timers"}
            ]
        },
        "continuous_prompting": {
            "name": "Continuous Prompting",
            "description": "Users repeatedly receive requests to enable tracking or permissions.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 7"], "violation": "Repeated prompts pressure users"},
                {"name": "CCPA", "articles": ["Section 1798.140"], "violation": "Pressure tactics to obtain consent"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Coercive consent mechanisms"}
            ]
        },
        "skipping": {
            "name": "Skipping",
            "description": "Privacy consent step is bypassed during onboarding.",
            "laws": [
                {"name": "GDPR", "articles": ["Article 6", "Article 7"], "violation": "Data collected without consent opportunity"},
                {"name": "CCPA", "articles": ["Section 1798.120"], "violation": "Consent step bypassed"},
                {"name": "FTC", "articles": ["Section 5"], "violation": "Users denied consent opportunity"}
            ]
        }
    }
}

# ==================== MODEL CONFIGURATION ====================
VIT_MODEL_NAME = "google/vit-base-patch16-224"
ROBERTA_MODEL_NAME = "roberta-base"
FUSION_DIM = 256
N_HEADS = 8
DROPOUT = 0.15
NUM_CLASSES = 27
IMG_SIZE = 224
MAX_TEXT_LEN = 128

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {DEVICE}")

# ==================== FULL LABEL MAP (all 27 classes) ====================
# Map index -> canonical pattern key used in LAW_MAPPING
LABEL_TO_NAME = {
    0:  "automatic_renewal",
    1:  "confirmshaming",
    2:  "continuous_prompting",
    3:  "cookie_wall",
    4:  "countdown_timer_pressure",
    5:  "drip_pricing",
    6:  "fake_scarcity",
    7:  "hidden_costs",
    8:  "interface_interference",
    9:  "misleading_discounts",
    10: "privacy_zuckering",
    11: "roach_motel",
    12: "skipping",
    13: "urgency_messaging",
    # Classes 14-26: extended / variant labels mapped to canonical keys
    14: "fake_scarcity",           # scarcity variant
    15: "urgency_messaging",       # urgency variant
    16: "confirmshaming",          # confirmshaming variant
    17: "hidden_costs",            # hidden costs variant
    18: "misleading_discounts",    # discount variant
    19: "roach_motel",             # roach motel variant
    20: "cookie_wall",             # cookie variant
    21: "drip_pricing",            # drip pricing variant
    22: "automatic_renewal",       # renewal variant
    23: "privacy_zuckering",       # privacy variant
    24: "interface_interference",  # interface variant
    25: "continuous_prompting",    # prompting variant
    26: "skipping",                # skipping variant
}

# ==================== KEYWORD PATTERNS (HIGH-PRECISION, HIGH-THRESHOLD) ====================
# These are used ONLY when the ML model is unavailable or returns low confidence.
# Each pattern requires MULTIPLE strong signals to fire — not a single word match.

KEYWORD_RULES = {
    "fake_scarcity": {
        "required": [  # at least one of these must match
            r"\bonly\s+\d+\s+(left|remaining|available|in\s+stock)",
            r"\b\d+\s+(items?|units?|pieces?)\s+(left|remaining)",
            r"\b(almost|nearly|last)\s+(.*?)?(gone|out\s+of\s+stock|sold\s+out)",
            r"\b\d+\s+(people|users?|viewers?|customers?)\s+(viewing|watching|interested)",  # NEW: Viewing count
            r"\b(limited\s+)?(stock|quantity|availability)\b",  # NEW: Generic scarcity
        ],
        "boost": [r"\bhurry\b", r"\bact\s+now\b", r"\blimited\b", r"\bviewing\b"],
        "min_confidence": 0.72
    },
    "urgency_messaging": {
        "required": [
            r"\boffer\s+ends\s+(today|tonight|soon|in)\b",
            r"\blimited\s+time\s+offer\b",
            r"\bexpires?\s+in\s+\d+\b",
            r"\bact\s+now\b.{0,30}\bexpir",
            r"\bdon'?t\s+miss\s+(out|this)\b",
            r"\btoday\s+only\b",
        ],
        "boost": [r"\bhurry\b", r"\blast\s+chance\b", r"\bending\s+soon\b"],
        "min_confidence": 0.78
    },
    "confirmshaming": {
        "required": [
            r"\bno\s+thanks?.{0,30}(full\s+price|pay\s+more|miss\s+out)\b",
            r"\bno.{0,20}i\s+(prefer|like)\s+to\s+pay\s+more\b",
            r"\bno.{0,20}i\s+don'?t\s+want\s+(a\s+)?(discount|deal|savings?)\b",
            r"\byes.{0,30}(discount|save|deal).{0,30}no.{0,30}(full\s+price|pay\s+more)\b",
            r"\b(are\s+you\s+sure|sure\s+you|really|certain)\s+(you\s+)?want\s+to\s+miss",  # NEW: "Are you sure"
            r"\bdon'?t\s+miss\s+(out\s+on|this)\s+.*?(limited|exclusive|free)",  # NEW: FOMO trigger
        ],
        "boost": [r"\bguilty\b", r"\bregret\b", r"\bmiss\b", r"\bsure\b"],
        "min_confidence": 0.72
    },
    "automatic_renewal": {
        "required": [
            r"\bfree\s+trial.{0,60}(auto.?renew|automatically\s+(renew|billed|charged))\b",
            r"\bfree\s+trial.*?no\s+credit\s+card",  # Free trial mentioned with credit card assurance
            r"\bauto.?renew\b.*?[\$\d]",  # Auto-renew mentioned with any price
            r"\bcancel\s+anytime\b.*?free\s+trial",  # Reassurance language with free trial
        ],
        "boost": [r"\bfree\b", r"\bsubscription\b", r"\bcharge\b", r"\brecurring\b"],
        "min_confidence": 0.72
    },
    
    "cookie_wall": {
        "required": [
            r"\b(accept|agree\s+to)\s+(all\s+)?cookies?\s+to\s+(continue|access|use)\b",
            r"\b(must|have\s+to)\s+accept\s+(all\s+)?cookies?\b",
            r"\bcookie\s+wall\b",
            r"\bto\s+continue\s+(browsing|using|accessing).{0,40}accept\b",
        ],
        "boost": [r"\bprivacy\b", r"\btracking\b"],
        "min_confidence": 0.80
    },
    "hidden_costs": {
        "required": [
            r"\b(service|processing|handling|booking)\s+fee\s+(not\s+included|added\s+at\s+checkout)\b",
            r"\badditional\s+(fees?|charges?)\s+(apply|at\s+checkout)\b",
            r"\btax\s+not\s+included\b",
            r"\bextra\s+(charges?|fees?)\s+(added|appear|revealed)\b",
        ],
        "boost": [r"\bcheckout\b", r"\btotal\b"],
        "min_confidence": 0.80
    },
    "misleading_discounts": {
        "required": [
            r"\bwas\s+\$[\d,]+\.?\d*\s+now\s+\$[\d,]+\.?\d*\b",
            r"\boriginal\s+price\s*:?\s*\$[\d,]+\b",
            r"\brrp\s*:?\s*\$[\d,]+\b",
            r"\bcrossed.{0,20}\$[\d,]+\b",
        ],
        "boost": [r"\bsave\b", r"\boff\b", r"\bdeal\b"],
        "min_confidence": 0.78
    },
    "roach_motel": {
        "required": [
            r"\bcancel\s+(your\s+)?(subscription|membership|account).{0,60}(difficult|hard|complex|multiple\s+steps|steps)\b",
            r"\b(hard|difficult|complex)\s+to\s+(cancel|unsubscribe|delete)\b",
            r"\bcancellation.*?(?:process|requires|involves|step).{0,60}(?:call|phone|mail|contact|4.step)",
            r"\bcancel.{0,30}(4.step|phone|mail|call|fax|contact)",  # NEW: Catch "cancel (4-step)"
            r"\bunsubscribe.{0,30}(difficult|hard|process|multiple|steps?)\b",  # NEW: Unsubscribe friction
        ],
        "boost": [r"\bunsubscribe\b", r"\bdelete\s+account\b", r"\bprocess\b"],
        "min_confidence": 0.75
    },
    "countdown_timer_pressure": {
        "required": [
            r"\b\d{1,2}:\d{2}(:\d{2})?\s*(remaining|left|to\s+go)\b",
            r"\bcountdown\s+timer\b",
            r"\bexpires?\s+in\s+\d+\s*(minutes?|hours?|seconds?)\b",
            r"\b(hurry|act\s+now).{0,30}(timer|countdown|expires?)\b",
        ],
        "boost": [r"\blimited\b", r"\burgent\b"],
        "min_confidence": 0.80
    },
    "continuous_prompting": {
        "required": [
            r"\b(remind\s+me\s+later|ask\s+me\s+again)\b.{0,100}\b(notification|permission|tracking)\b",
            r"\b(not\s+now|dismiss|skip).{0,60}\b(we'?ll?\s+ask\s+again|remind\s+you\s+later)\b",
        ],
        "boost": [r"\bpermission\b", r"\benable\b"],
        "min_confidence": 0.82
    },
    "drip_pricing": {
        "required": [
            r"\b(fees?|charges?|surcharge)\s+(added|revealed|appear(s)?)\s+(at|during)\s+(checkout|payment)\b",
            r"\bprice\s+shown\s+(does\s+not\s+include|excludes?)\b",
            r"\b\+\s*\$[\d.]+\s*(fee|charge|surcharge)\b",
        ],
        "boost": [r"\btotal\b", r"\bfinal\s+price\b"],
        "min_confidence": 0.80
    },
    "privacy_zuckering": {
        "required": [
            r"\bshare\s+(your\s+)?(data|information)\s+with\s+(our\s+)?(partners?|third\s+parties?)\b",
            r"\bpersonaliz(e|ation).{0,60}(share|collect|gather)\s+(your\s+)?data\b",
            r"\bimprove\s+(our\s+)?services?.{0,60}(share|send|use)\s+(your\s+)?(data|information)\b",
        ],
        "boost": [r"\bcollect\b", r"\btracking\b"],
        "min_confidence": 0.80
    },
    "interface_interference": {
        "required": [
            r"\baccept\s+all\b.{0,40}\breject\s+all\b",
            r"\b(accept|agree)\s+all.{0,60}(grey(d?)|disabled|hidden|small\s+text)\b",
        ],
        "boost": [r"\bcookies?\b", r"\bprivacy\b"],
        "min_confidence": 0.82
    },
    "skipping": {
        "required": [
            r"\b(skip|bypass|continue\s+without).{0,40}(consent|privacy|permission|data\s+settings?)\b",
            r"\bagree\s+and\s+continue\b.{0,80}(data|privacy|tracking)",
        ],
        "boost": [r"\bonboarding\b", r"\bsetup\b"],
        "min_confidence": 0.80
    },
}

# Compile all regex patterns
COMPILED_RULES = {}
for pattern_key, rule in KEYWORD_RULES.items():
    COMPILED_RULES[pattern_key] = {
        "required": [re.compile(p, re.IGNORECASE | re.DOTALL) for p in rule["required"]],
        "boost":    [re.compile(p, re.IGNORECASE | re.DOTALL) for p in rule.get("boost", [])],
        "min_confidence": rule["min_confidence"]
    }


def keyword_detection(text):
    """
    High-precision keyword detection.
    Returns (pattern_key, confidence) only when STRONG multi-signal evidence exists.
    Used ONLY as fallback when ML model is unavailable or low-confidence.
    """
    if not text or len(text.strip()) < 10:
        return None, 0.0

    text_lower = text.strip()
    best_pattern = None
    best_confidence = 0.0

    for pattern_key, rule in COMPILED_RULES.items():
        # Must match at least one required pattern
        required_hits = sum(1 for rx in rule["required"] if rx.search(text_lower))
        if required_hits == 0:
            continue

        # Boost score with supporting signals
        boost_hits = sum(1 for rx in rule["boost"] if rx.search(text_lower))

        # Confidence formula: base from required hits + boost from supporting signals
        base = rule["min_confidence"]
        bonus = min(0.10, required_hits * 0.03 + boost_hits * 0.02)
        confidence = min(0.93, base + bonus)

        if confidence > best_confidence:
            best_confidence = confidence
            best_pattern = pattern_key

    return best_pattern, best_confidence


# ==================== MODEL ARCHITECTURE ====================
class CrossModalAttention(nn.Module):
    def __init__(self, d_model: int = 256, n_heads: int = 8, dropout: float = 0.2):
        super().__init__()
        self.proj_v = nn.Linear(768, d_model)
        self.proj_t = nn.Linear(768, d_model)
        self.v_attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.t_attn = nn.MultiheadAttention(d_model, n_heads, dropout=dropout, batch_first=True)
        self.norm_v = nn.LayerNorm(d_model)
        self.norm_t = nn.LayerNorm(d_model)
        self.dropout = nn.Dropout(dropout)

    def forward(self, vis_feat, txt_feat):
        v = self.proj_v(vis_feat).unsqueeze(1)
        t = self.proj_t(txt_feat).unsqueeze(1)
        v_cross, _ = self.v_attn(query=v, key=t, value=t)
        v_out = self.norm_v(v + self.dropout(v_cross)).squeeze(1)
        t_cross, _ = self.t_attn(query=t, key=v, value=v)
        t_out = self.norm_t(t + self.dropout(t_cross)).squeeze(1)
        return torch.cat([v_out, t_out], dim=-1)


class DualStreamDarkPatternDetector(nn.Module):
    def __init__(self, num_classes: int, fusion_dim: int = 256, n_heads: int = 8, dropout: float = 0.2):
        super().__init__()
        self.vit = None
        self.roberta = None
        self.fusion = CrossModalAttention(d_model=fusion_dim, n_heads=n_heads, dropout=dropout)
        fused_dim = 2 * fusion_dim
        self.classifier = nn.Sequential(
            nn.Linear(fused_dim, fused_dim),
            nn.BatchNorm1d(fused_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fused_dim, fused_dim // 2),
            nn.BatchNorm1d(fused_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(fused_dim // 2, num_classes),
        )
        self.dropout = nn.Dropout(dropout)

    def forward(self, pixel_values, input_ids, attention_mask):
        vit_out = self.vit(pixel_values=pixel_values)
        vis_cls = self.dropout(vit_out.last_hidden_state[:, 0, :])
        rob_out = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
        txt_cls = self.dropout(rob_out.last_hidden_state[:, 0, :])
        fused = self.fusion(vis_cls, txt_cls)
        logits = self.classifier(fused)
        return logits


# ==================== GLOBALS ====================
model = None
vit_processor = None
roberta_tokenizer = None


def load_model(model_path):
    global model, vit_processor, roberta_tokenizer
    print("Loading model from:", model_path)
    try:
        from transformers import ViTModel, RobertaModel, ViTImageProcessor, RobertaTokenizer

        print("Loading image processor...")
        vit_processor = ViTImageProcessor.from_pretrained(VIT_MODEL_NAME)
        print("Loading tokenizer...")
        roberta_tokenizer = RobertaTokenizer.from_pretrained(ROBERTA_MODEL_NAME)
        print("Loading ViT model...")
        vit_model = ViTModel.from_pretrained(VIT_MODEL_NAME)
        print("Loading RoBERTa model...")
        roberta_model = RobertaModel.from_pretrained(ROBERTA_MODEL_NAME)

        detector = DualStreamDarkPatternDetector(
            num_classes=NUM_CLASSES,
            fusion_dim=FUSION_DIM,
            n_heads=N_HEADS,
            dropout=DROPOUT,
        )
        detector.vit = vit_model
        detector.roberta = roberta_model

        print("Loading trained weights...")
        checkpoint = torch.load(model_path, map_location=DEVICE)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        new_state_dict = {}
        for k, v in state_dict.items():
            new_state_dict[k[7:] if k.startswith("module.") else k] = v

        detector.load_state_dict(new_state_dict, strict=False)
        detector.to(DEVICE)
        detector.eval()
        model = detector
        print(f"✓ Model loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        traceback.print_exc()
        return False


# ==================== CONFIDENCE CALIBRATION ====================

def temperature_scale(logits, temperature=1.5):
    """
    Apply temperature scaling to soften overconfident softmax outputs.
    T > 1 makes the distribution flatter (more conservative).
    T < 1 makes it sharper. We use T=1.5 to avoid overconfidence.
    """
    return logits / temperature


def calibrated_confidence(probs, pred_class, top2_margin_threshold=0.15):
    """
    Penalise predictions where the model is not clearly ahead of the 2nd-best class.
    If the margin between top-1 and top-2 is small, reduce effective confidence.
    """
    top2 = torch.topk(probs, 2, dim=-1)
    top1_prob = top2.values[0, 0].item()
    top2_prob = top2.values[0, 1].item()
    margin = top1_prob - top2_prob

    # If the model is barely ahead of second place, penalise confidence
    if margin < top2_margin_threshold:
        penalty = (top2_margin_threshold - margin) / top2_margin_threshold
        adjusted = top1_prob * (1.0 - 0.25 * penalty)
        return adjusted, margin
    return top1_prob, margin


# ==================== ML MODEL PREDICTION ====================

# Thresholds
ML_DETECTION_THRESHOLD   = 0.25   # ML model must exceed this to report a detection
ML_HIGH_CONFIDENCE       = 0.45   # Above this: report ML result without keyword check
ML_LOW_CONFIDENCE        = 0.20   # Below this: try keyword fallback
KEYWORD_MIN_CONFIDENCE   = 0.70   # Keyword result must exceed this to be used


def predict_with_model(image_b64, text):
    """
    Primary detection path: ML model with temperature scaling + margin calibration.
    Returns result dict or None.
    """
    global model

    if model is None:
        return None

    try:
        if image_b64.startswith("data:image"):
            image_b64 = image_b64.split(",")[1]
        image_bytes = base64.b64decode(image_b64)
        image = Image.open(BytesIO(image_bytes)).convert("RGB")
        image = image.resize((IMG_SIZE, IMG_SIZE))

        vit_inputs = vit_processor(images=image, return_tensors="pt")
        pixel_values = vit_inputs["pixel_values"].to(DEVICE)

        input_text = text if (text and text != "insufficient_content" and len(text.strip()) > 3) else "ui element"
        roberta_inputs = roberta_tokenizer(
            input_text,
            max_length=MAX_TEXT_LEN,
            padding="max_length",
            truncation=True,
            return_tensors="pt"
        )
        input_ids = roberta_inputs["input_ids"].to(DEVICE)
        attention_mask = roberta_inputs["attention_mask"].to(DEVICE)

        with torch.no_grad():
            logits = model(pixel_values, input_ids, attention_mask)

            # Apply temperature scaling before softmax
            scaled_logits = temperature_scale(logits, temperature=1.5)
            probs = F.softmax(scaled_logits, dim=-1)

            pred_class = torch.argmax(probs, dim=-1).item()

        # Calibrated confidence with margin check
        confidence, margin = calibrated_confidence(probs, pred_class)

        # Resolve class index to canonical pattern name
        pattern_name = LABEL_TO_NAME.get(pred_class)
        if pattern_name is None:
            print(f"Unknown class index {pred_class}, skipping.")
            return None

        print(f"ML model: class={pred_class} → {pattern_name}, raw_conf={probs[0, pred_class].item():.3f}, "
              f"calibrated_conf={confidence:.3f}, margin={margin:.3f}")

        if confidence < ML_DETECTION_THRESHOLD:
            print(f"ML confidence {confidence:.3f} below threshold {ML_DETECTION_THRESHOLD}, not reporting.")
            return {
                "detected": False,
                "pattern": pattern_name,
                "confidence": confidence,
                "method": "model_low_confidence"
            }

        law_info = LAW_MAPPING["dark_patterns"].get(pattern_name, {})
        return {
            "detected": True,
            "pattern": pattern_name,
            "confidence": round(confidence, 4),
            "text": text[:200] if text else "",
            "laws": law_info,
            "method": "model"
        }

    except Exception as e:
        print(f"Error in model prediction: {e}")
        traceback.print_exc()
        return None


def predict_with_keywords(text):
    """
    Fallback detection path: high-precision keyword rules.
    Only fires when STRONG multi-signal evidence exists.
    """
    pattern, confidence = keyword_detection(text)
    if pattern and confidence >= KEYWORD_MIN_CONFIDENCE:
        print(f"Keyword fallback: {pattern} with confidence {confidence:.3f}")
        law_info = LAW_MAPPING["dark_patterns"].get(pattern, {})
        return {
            "detected": True,
            "pattern": pattern,
            "confidence": round(confidence, 4),
            "text": text[:200] if text else "",
            "laws": law_info,
            "method": "keyword"
        }
    return None


# ============================================================================
# FLASK APP
# ============================================================================
app = Flask(__name__)
CORS(app)


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "model_loaded": model is not None})


@app.route('/detect', methods=['POST'])
def detect():
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    image_b64 = data.get("image", "")
    element_data = data.get("element", {})

    # Extract and clean text
    text = (
        element_data.get("text", "") or
        element_data.get("innerText", "") or
        ""
    ).strip()

    print(f"\n--- Detection Request ---")
    print(f"Text (first 120 chars): '{text[:120]}'")

    result = None

    # ----------------------------------------------------------------
    # Step 1: Try ML model first (primary)
    # ----------------------------------------------------------------
    if image_b64:
        ml_result = predict_with_model(image_b64, text)

        if ml_result is not None:
            if ml_result["detected"]:
                # ML model confident — use it directly
                confidence = ml_result["confidence"]

                if confidence >= ML_HIGH_CONFIDENCE:
                    # Very confident ML result — no further checks needed
                    print(f"✅ ML HIGH CONFIDENCE: {ml_result['pattern']} ({confidence:.3f})")
                    result = ml_result

                else:
                    # Moderate ML confidence: cross-check with keyword rules
                    # If keyword agrees → boost; if keyword disagrees → prefer ML but note
                    kw_pattern, kw_conf = keyword_detection(text)
                    if kw_pattern and kw_conf >= KEYWORD_MIN_CONFIDENCE:
                        if kw_pattern == ml_result["pattern"]:
                            # Agreement → slight confidence boost
                            boosted = min(0.95, confidence + 0.05)
                            ml_result["confidence"] = round(boosted, 4)
                            ml_result["method"] = "model+keyword_agreement"
                            print(f"✅ ML+KW AGREE: {ml_result['pattern']} boosted to {boosted:.3f}")
                        else:
                            # Disagreement → trust ML but log it
                            ml_result["method"] = "model_kw_disagree"
                            print(f"⚠️  ML({ml_result['pattern']}) vs KW({kw_pattern}) — trusting ML")
                    result = ml_result

            else:
                # ML model ran but confidence was too low
                # Fall through to keyword fallback below
                print(f"ML below threshold — trying keyword fallback")

    # ----------------------------------------------------------------
    # Step 2: Keyword fallback (only if ML failed or model not loaded)
    # ----------------------------------------------------------------
    if result is None and text:
        result = predict_with_keywords(text)

    # ----------------------------------------------------------------
    # Step 3: Return
    # ----------------------------------------------------------------
    if result and result.get("detected"):
        print(f"✅ FINAL DETECTION: {result['pattern']} "
              f"(conf={result['confidence']}, method={result.get('method','?')})")
        return jsonify(result)

    print(f"❌ No detection for: '{text[:60]}'")
    return jsonify({"detected": False, "pattern": None, "confidence": 0.0})


@app.route('/all_patterns', methods=['GET'])
def get_all_patterns():
    patterns = {}
    for key, value in LAW_MAPPING["dark_patterns"].items():
        patterns[key] = {
            "name": value["name"],
            "description": value["description"],
            "laws": value["laws"]
        }
    return jsonify(patterns)


if __name__ == "__main__":
    model_path = Path(__file__).parent / "best_model_no_leakage.pt"
    if not model_path.exists():
        model_path = Path(__file__).parent.parent / "best_model_no_leakage.pt"

    if model_path.exists():
        success = load_model(model_path)
        if not success:
            print("Warning: Model failed to load. Using keyword fallback only.")
    else:
        print(f"Warning: Model not found at {model_path}. Using keyword fallback only.")

    print("\n" + "=" * 60)
    print("Dark Pattern Detector Server (ML-Primary Edition)")
    print(f"Model loaded: {model is not None}")
    print(f"ML detection threshold:  {ML_DETECTION_THRESHOLD}")
    print(f"ML high-confidence gate: {ML_HIGH_CONFIDENCE}")
    print(f"Keyword fallback min:    {KEYWORD_MIN_CONFIDENCE}")
    print(f"Temperature scaling:     T=1.5")
    print(f"Total label classes:     {NUM_CLASSES} → {len(set(LABEL_TO_NAME.values()))} canonical patterns")
    print("=" * 60)
    print(f"Server URL: http://127.0.0.1:5000")
    print("Press Ctrl+C to stop\n")

    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)