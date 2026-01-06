#!/usr/bin/env python3
"""
Test script for Delay Prediction Model - Fakeeh Dubai
"""

import requests
import json
import time

def test_delay_model():
    """Test the delay prediction model"""
    
    # Gateway URL
    gateway_url = "http://localhost:8000"
    model_id = "delay_fakeeh_dubai"
    
    # Sample input data based on the raw event format
    test_input = {
        "inputs": {
            "HOSPITAL_NAME": "Fakeeh University Hospital",
            "PROVIDER_NAME": "Mohamed Lotfy Ahmed",
            "DEPARTMENT": "GENERAL PEDIATRICS",
            "ALLOCATION_DATE_TIME": "2/13/2025",
            "ALLOCATION_DAY": "THURSDAY",
            "MRNO": "10155995",
            "TOKEN_NO": "7W",
            "GIVEN_BY": "Hesham Aboelsheour",
            "FOLLOW_NEW": "N",
            "AGE": "2y",
            "APPT_ALLOCATION_ID": "1237535",
            "FACILITY_NAME": "Fakeeh University Hospital",
            "GENDER": "Male",
            "VISIT_METHOD": "PHYSICAL",
            "GIVEN_ON": "2/13/2025 1:53 PM",
            "APPT_BOOKING_CHANNEL": "WALK-IN",
            "CITY": "DUBAI",
            "VISIT_TYPE": "CREDIT",
            "CONTRACT_NAME": "MEDNET  TPA036/Metlife 501 or 261",
            "PAYMENT_STATUS": ""
        }
    }
    
    print("🏥 Testing Delay Prediction Model - Fakeeh Dubai")
    print("=" * 60)
    print(f"📍 Gateway URL: {gateway_url}/predict/{model_id}")
    print(f"🔬 Model ID: {model_id}")
    print()
    
    try:
        # Make prediction request
        start_time = time.time()
        response = requests.post(
            f"{gateway_url}/predict/{model_id}",
            json=test_input,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        latency_ms = int((time.time() - start_time) * 1000)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Prediction completed")
            print(f"🎯 Prediction: {result.get('prediction', 'N/A')}")
            print(f"📊 Score: {result.get('score', 'N/A')}")
            print(f"⏱️  Latency: {latency_ms}ms")
            print()
            print("📋 Full Response:")
            print(json.dumps(result, indent=2))
        else:
            print(f"❌ FAILED! Status Code: {response.status_code}")
            print(f"📄 Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ REQUEST ERROR: {str(e)}")
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {str(e)}")

if __name__ == "__main__":
    test_delay_model()
