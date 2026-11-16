import requests
import json
import base64
from PIL import Image
import io

# Test the XAI endpoint
def test_xai_endpoint():
    # Create a test image
    img = Image.new('RGB', (224, 224), color='white')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    
    # Test element data
    element_data = {
        "text": "Hurry! Only 2 left in stock! Buy now before it's gone! Limited time offer!",
        "innerText": "Hurry! Only 2 left in stock! Buy now before it's gone!",
        "tagName": "BUTTON",
        "className": "buy-now urgent"
    }
    
    # Make POST request
    response = requests.post(
        'http://127.0.0.1:5000/detect_with_xai',
        json={
            'image': f'data:image/png;base64,{img_base64}',
            'element': element_data
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print("=" * 70)
        print("XAI DETECTION RESULT")
        print("=" * 70)
        
        # Print detection result
        detection = result.get('detection_result', {})
        print(f"\n🔍 Pattern Detected: {detection.get('pattern', 'None')}")
        print(f"📊 Confidence: {detection.get('confidence', 0):.2%}")
        print(f"📝 Detected Text: {detection.get('text', 'N/A')}")
        
        # Print XAI explanation
        xai = result.get('explainable_ai', {})
        print(f"\n💡 EXPLANATION:")
        print(f"   {xai.get('explanation', 'N/A')}")
        
        print(f"\n📋 DETECTION EVIDENCE:")
        evidence = xai.get('detection_evidence', {})
        text_analysis = evidence.get('text_analysis', {})
        print(f"   Triggered Keywords: {', '.join(text_analysis.get('detected_keywords', []))}")
        print(f"   Reasoning: {text_analysis.get('reasoning', 'N/A')}")
        
        print(f"\n⚖️ LEGAL ANALYSIS:")
        legal = xai.get('legal_analysis', {})
        print(f"   Regulatory Risk: {legal.get('regulatory_risk', 'N/A')}")
        for law in legal.get('violated_laws', []):
            print(f"\n   📜 {law.get('name', 'Unknown')}:")
            print(f"      Articles: {', '.join(law.get('articles', []))}")
            print(f"      Violation: {law.get('violation', 'N/A')}")
            print(f"      Explanation: {law.get('explanation', 'N/A')[:150]}...")
        
        print(f"\n🔧 REMEDIATION SUGGESTIONS:")
        print(f"   {xai.get('remediation_suggestions', 'N/A')}")
        
        print(f"\n✅ RECOMMENDATIONS:")
        for rec in result.get('recommendations', {}).get('immediate_actions', []):
            print(f"   • {rec}")
        
    else:
        print(f"Error: {response.status_code}")
        print(response.text)

# Test the example endpoint
def test_example():
    response = requests.get('http://127.0.0.1:5000/xai_example')
    if response.status_code == 200:
        result = response.json()
        print("\n" + "=" * 70)
        print("XAI EXAMPLE OUTPUT")
        print("=" * 70)
        xai = result.get('explainable_ai_analysis', {})
        print(f"\nPattern: {xai.get('pattern_detected', 'N/A')}")
        print(f"Confidence: {xai.get('confidence_score', 0):.2%}")
        print(f"\nExplanation: {xai.get('explanation', 'N/A')[:300]}...")
    else:
        print(f"Error: {response.status_code}")

# Test health endpoint
def test_health():
    response = requests.get('http://127.0.0.1:5000/health')
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Server Status: {result.get('status', 'Unknown')}")
        print(f"Model Loaded: {result.get('model_loaded', False)}")
    else:
        print(f"❌ Server not responding")

if __name__ == "__main__":
    print("Testing Dark Pattern Detector with XAI...")
    print("\n1. Checking server health...")
    test_health()
    
    print("\n2. Testing XAI example...")
    test_example()
    
    print("\n3. Testing detection with XAI...")
    test_xai_endpoint()