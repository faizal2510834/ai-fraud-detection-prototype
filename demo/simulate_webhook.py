import requests
import json
import uuid
import sys
import time

def simulate_webhook(reason: str, evidence_score: float):
    url = "http://localhost:8001/api/v1/dispute-webhook"
    
    payload = {
        "dispute_id": f"dp_{uuid.uuid4().hex[:12]}",
        "order_id": "ORD-12345",
        "user_id": "usr_789",
        "reason": reason,
        "evidence_score": evidence_score
    }
    
    print(f"Simulating webhook trigger to {url}...")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        
        result = response.json()
        print("\n[✓] Webhook Response Received:")
        print(json.dumps(result, indent=2))
        
        ce_analysis = result.get("ce_analysis", {})
        if result.get("action_taken") == "user_blocked":
            print(f"\n🚨 AUTO-BLOCK TRIGGERED! Confidence Score: {ce_analysis.get('confidence_score')}%")
        else:
            print(f"\n⚠️ Flagged for Review. Confidence Score: {ce_analysis.get('confidence_score')}%")
            
    except requests.exceptions.RequestException as e:
        print(f"\n[✗] Webhook Simulation Failed: {e}")

if __name__ == "__main__":
    print("--- CE 3.0 Fraud Webhook Simulation ---")
    
    # 1. Simulate an Empty Box fraud attempt (High evidence score)
    print("\nScenario 1: High Evidence + Empty Box (Should Auto-Block)")
    simulate_webhook(reason="empty_box", evidence_score=0.85)
    
    time.sleep(2)
    
    # 2. Simulate a normal defective item dispute (Should Flag for Review)
    print("\nScenario 2: High Evidence + Defective Item (Should Flag for Review)")
    simulate_webhook(reason="item_defective", evidence_score=0.90)
