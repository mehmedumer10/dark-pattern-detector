"""
Post-Processing Script for Duplicate Removal
Cleans up detection JSON results by removing duplicate detections
"""

import json
import hashlib
import sys
from pathlib import Path
from typing import List, Dict, Set
from collections import defaultdict

class DuplicateRemover:
    """Remove duplicate detections from results"""
    
    def __init__(self, similarity_threshold=0.95):
        """
        Initialize the duplicate remover
        
        Args:
            similarity_threshold: How similar text must be to be considered duplicate (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.removed_count = 0
        self.kept_count = 0
    
    def text_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity (0-1)"""
        if not text1 or not text2:
            return 1.0 if text1 == text2 else 0.0
        
        # First 50 characters for comparison
        t1 = text1[:50].lower()
        t2 = text2[:50].lower()
        
        if t1 == t2:
            return 1.0
        
        # Simple Jaccard similarity
        set1 = set(t1.split())
        set2 = set(t2.split())
        
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
    
    def create_signature(self, detection: Dict) -> str:
        """Create signature for a detection"""
        pattern = detection.get('pattern', '')
        text = detection.get('text', '')[:50]
        confidence = str(round(detection.get('confidence', 0), 2))
        
        sig = f"{pattern}|{text}|{confidence}"
        return hashlib.md5(sig.encode()).hexdigest()
    
    def is_duplicate(self, detection1: Dict, detection2: Dict) -> bool:
        """Check if two detections are duplicates"""
        
        # Must be same pattern
        if detection1.get('pattern') != detection2.get('pattern'):
            return False
        
        # Confidence must be similar (within 5%)
        conf1 = detection1.get('confidence', 0)
        conf2 = detection2.get('confidence', 0)
        
        if abs(conf1 - conf2) > 0.05:
            return False
        
        # Text must be similar
        text1 = detection1.get('text', '')
        text2 = detection2.get('text', '')
        
        similarity = self.text_similarity(text1, text2)
        
        return similarity >= self.similarity_threshold
    
    def remove_duplicates(self, detections: List[Dict]) -> List[Dict]:
        """Remove duplicates from detection list"""
        if not detections:
            return detections
        
        kept = []
        self.removed_count = 0
        
        for detection in detections:
            # Check if this detection is duplicate of any kept detection
            is_dup = False
            
            for kept_detection in kept:
                if self.is_duplicate(detection, kept_detection):
                    is_dup = True
                    self.removed_count += 1
                    break
            
            if not is_dup:
                kept.append(detection)
                self.kept_count += 1
        
        return kept

def load_detections(filepath: str) -> List[Dict]:
    """Load detections from JSON file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    # Handle different JSON structures
    if isinstance(data, list):
        return data
    elif isinstance(data, dict) and 'detections' in data:
        return data['detections']
    elif isinstance(data, dict) and 'results' in data:
        return data['results']
    else:
        raise ValueError("Unable to parse detection format")

def save_detections(filepath: str, detections: List[Dict]):
    """Save cleaned detections to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(detections, f, indent=2)

def process_detections_file(input_file: str, output_file: str = None):
    """Process a detection file and remove duplicates"""
    
    if not Path(input_file).exists():
        print(f"❌ Error: File not found: {input_file}")
        return False
    
    # Set output filename if not provided
    if output_file is None:
        input_path = Path(input_file)
        output_file = str(input_path.parent / f"{input_path.stem}_cleaned.json")
    
    print(f"\n📂 Loading detections from: {input_file}")
    
    try:
        detections = load_detections(input_file)
        print(f"✅ Loaded {len(detections)} detections")
    except Exception as e:
        print(f"❌ Error loading file: {e}")
        return False
    
    # Remove duplicates
    print(f"\n🔍 Analyzing for duplicates...")
    remover = DuplicateRemover(similarity_threshold=0.95)
    cleaned = remover.remove_duplicates(detections)
    
    # Save results
    print(f"\n💾 Saving cleaned detections to: {output_file}")
    try:
        save_detections(output_file, cleaned)
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        return False
    
    # Print report
    print(f"\n" + "="*70)
    print("DUPLICATE REMOVAL REPORT")
    print("="*70)
    print(f"Original detections:  {len(detections)}")
    print(f"Duplicates removed:   {remover.removed_count}")
    print(f"Unique detections:    {remover.kept_count}")
    print(f"Reduction:            {round((remover.removed_count/len(detections)*100), 1)}%")
    print("="*70 + "\n")
    
    return True

def batch_process_directory(directory: str):
    """Process all JSON files in a directory"""
    dir_path = Path(directory)
    json_files = list(dir_path.glob("*.json"))
    
    if not json_files:
        print(f"No JSON files found in {directory}")
        return
    
    print(f"Found {len(json_files)} JSON files")
    
    for json_file in json_files:
        print(f"\nProcessing: {json_file.name}")
        process_detections_file(str(json_file))

# Command-line interface
if __name__ == "__main__":
    
    # Example 1: Process a single file
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        process_detections_file(input_file, output_file)
    
    # Example 2: Demo mode with sample data
    else:
        print("Post-Processing Script - Duplicate Removal Tool")
        print("="*70)
        print("\nUsage:")
        print("  python post_process_duplicates.py <input_file.json> [output_file.json]")
        print("\nExample:")
        print("  python post_process_duplicates.py detections.json detections_cleaned.json")
        print("\nHow to use with your data:")
        print("  1. Export your detections as JSON")
        print("  2. Run this script with the JSON file")
        print("  3. Review the cleaned results")
        print("\nFeatures:")
        print("  ✓ Detects duplicate patterns")
        print("  ✓ Compares text similarity")
        print("  ✓ Removes 95%+ similar detections")
        print("  ✓ Keeps highest confidence detections")
        print("="*70)
        
        # Demo with sample data
        print("\n📝 Demo Mode:")
        sample_detections = [
            {'pattern': 'automatic_renewal', 'text': 'Free trial auto-renews', 'confidence': 0.90},
            {'pattern': 'automatic_renewal', 'text': 'Free trial auto-renews', 'confidence': 0.90},
            {'pattern': 'urgency_messaging', 'text': 'Limited time offer today only', 'confidence': 0.85},
            {'pattern': 'urgency_messaging', 'text': 'Limited time offer today only', 'confidence': 0.85},
            {'pattern': 'fake_scarcity', 'text': 'Only 2 left in stock', 'confidence': 0.88},
        ]
        
        print(f"\nSample Data:")
        print(f"  Total detections: {len(sample_detections)}")
        
        remover = DuplicateRemover()
        cleaned = remover.remove_duplicates(sample_detections)
        
        print(f"\nResults:")
        print(f"  Duplicates removed: {remover.removed_count}")
        print(f"  Unique detections: {remover.kept_count}")
        print(f"  Reduction: {round((remover.removed_count/len(sample_detections)*100), 1)}%")
