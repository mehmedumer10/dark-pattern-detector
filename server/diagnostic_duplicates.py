"""
Duplicate Detection Diagnostic Script
Analyzes your detection results to identify and report duplicates
"""

import json
import hashlib
from collections import defaultdict
from typing import List, Dict, Tuple

def extract_signature(detection: Dict) -> str:
    """Extract unique signature from a detection"""
    pattern = detection.get('pattern', '')
    text = detection.get('text', '')[:50]  # First 50 chars
    confidence = str(round(detection.get('confidence', 0), 2))
    
    sig = f"{pattern}|{text}|{confidence}"
    return hashlib.md5(sig.encode()).hexdigest()

def find_duplicate_groups(detections: List[Dict]) -> Dict[str, List[int]]:
    """Group detections by signature to find duplicates"""
    groups = defaultdict(list)
    
    for idx, detection in enumerate(detections):
        sig = extract_signature(detection)
        groups[sig].append(idx)
    
    return groups

def analyze_detections(detections: List[Dict]) -> Dict:
    """Analyze detections for duplicates and provide report"""
    
    groups = find_duplicate_groups(detections)
    
    # Find duplicate groups (more than 1 detection with same signature)
    duplicates = {sig: indices for sig, indices in groups.items() if len(indices) > 1}
    
    total_detections = len(detections)
    unique_detections = len(groups)
    duplicate_count = total_detections - unique_detections
    
    # Calculate statistics
    stats = {
        'total_detections': total_detections,
        'unique_detections': unique_detections,
        'duplicate_count': duplicate_count,
        'duplicate_percentage': round((duplicate_count / total_detections * 100), 1) if total_detections > 0 else 0,
        'num_duplicate_groups': len(duplicates),
        'duplicates': {}
    }
    
    # Detailed duplicate information
    for sig, indices in sorted(duplicates.items(), key=lambda x: len(x[1]), reverse=True):
        pattern = detections[indices[0]].get('pattern', 'unknown')
        text = detections[indices[0]].get('text', '')[:100]
        confidence = detections[indices[0]].get('confidence', 0)
        
        stats['duplicates'][sig] = {
            'pattern': pattern,
            'text': text,
            'confidence': confidence,
            'count': len(indices),
            'detection_indices': indices
        }
    
    return stats

def print_report(stats: Dict):
    """Print diagnostic report"""
    print("\n" + "="*70)
    print("DUPLICATE DETECTION DIAGNOSTIC REPORT")
    print("="*70)
    
    print(f"\n📊 SUMMARY:")
    print(f"  Total Detections:     {stats['total_detections']}")
    print(f"  Unique Detections:    {stats['unique_detections']}")
    print(f"  Duplicate Count:      {stats['duplicate_count']}")
    print(f"  Duplicate Rate:       {stats['duplicate_percentage']}%")
    print(f"  Duplicate Groups:     {stats['num_duplicate_groups']}")
    
    if stats['duplicate_count'] == 0:
        print(f"\n✅ No duplicates detected!")
        return
    
    print(f"\n⚠️  DUPLICATE GROUPS FOUND:")
    print("-" * 70)
    
    for idx, (sig, info) in enumerate(stats['duplicates'].items(), 1):
        print(f"\nGroup {idx}: {info['pattern'].upper()} ({info['count']} occurrences)")
        print(f"  Confidence: {info['confidence']}")
        print(f"  Text Sample: {info['text'][:80]}...")
        print(f"  Detection Indices: {info['detection_indices']}")
    
    print("\n" + "="*70)
    print(f"RECOMMENDATION: Remove {stats['duplicate_count']} duplicate detections")
    print("="*70 + "\n")

def remove_duplicates(detections: List[Dict]) -> Tuple[List[Dict], List[int]]:
    """Remove duplicate detections, keeping only first occurrence"""
    groups = find_duplicate_groups(detections)
    
    # Keep only first index of each group
    kept_indices = []
    for sig, indices in groups.items():
        kept_indices.append(min(indices))
    
    kept_indices.sort()
    
    # Filter detections
    cleaned = [detections[i] for i in kept_indices]
    removed_indices = [i for i in range(len(detections)) if i not in kept_indices]
    
    return cleaned, removed_indices

# Example usage
if __name__ == "__main__":
    # Example detections (replace with your actual data)
    example_detections = [
        {
            'pattern': 'automatic_renewal',
            'text': 'Skip to Main content Keyboard shortcuts',
            'confidence': 0.90
        },
        {
            'pattern': 'automatic_renewal',
            'text': 'Skip to Main content Keyboard shortcuts',
            'confidence': 0.90  # DUPLICATE
        },
        {
            'pattern': 'urgency_messaging',
            'text': 'Today\'s Deals Gift Cards',
            'confidence': 0.85
        },
        {
            'pattern': 'urgency_messaging',
            'text': 'Today\'s Deals Gift Cards',
            'confidence': 0.85  # DUPLICATE
        },
        {
            'pattern': 'urgency_messaging',
            'text': 'Today\'s Deals Gift Cards',
            'confidence': 0.85  # DUPLICATE
        }
    ]
    
    # Analyze
    stats = analyze_detections(example_detections)
    print_report(stats)
    
    # Remove duplicates
    cleaned, removed = remove_duplicates(example_detections)
    print(f"\nCleaned Results:")
    print(f"  Before: {len(example_detections)} detections")
    print(f"  After:  {len(cleaned)} detections")
    print(f"  Removed: {removed}")
    
    print(f"\nUse this script with your actual detection data to:")
    print("  1. Identify duplicate detections")
    print("  2. See which detections are duplicates")
    print("  3. Remove duplicates from your results")
