#!/usr/bin/env python3
"""
Test script for No-Show Fakeeh KSA model
Sends a sample prediction request to verify the AWS SageMaker endpoint is working
"""

import requests
import json
from datetime import datetime

# Gateway endpoint
GATEWAY_URL = "http://localhost:8000/v1/predict"

# Sample appointment data for no-show prediction
# All 21 features in the exact order required by the SageMaker model
sample_appointment = {
    "model_id": "no_show_fakeeh_ksa",
    "client_id": "fakeeh_hospital_test",
    "inputs": {
        "PROVIDER_NAME": "Dr. Ahmed Al-Rashid",
        "DEPARTMENT": "Cardiology",
        "ALLOCATION_DATE_TIME": "2025-12-20 10:00:00",
        "ALLOCATION_DAY": "Friday",
        "MRNO": "MR123456",
        "TOKEN_NO": "T001",
        "GIVEN_BY": "Reception",
        "FOLLOW_NEW": "Follow-up",
        "AGE": 45,
        "REMARKS": "Routine checkup",
        "APPT_ALLOCATION_ID": "APPT001",
        "FACILITY_NAME": "Fakeeh Hospital - Riyadh",
        "GENDER": "Male",
        "VISIT_METHOD": "In-person",
        "GIVEN_ON": "2025-12-18 14:30:00",
        "DOCTORS_NATIONALITY": "Saudi",
        "APPT_BOOKING_CHANNEL": "Mobile App",
        "CITY": "Riyadh",
        "VISIT_TYPE": "Consultation",
        "CONTRACT_NAME": "Saudi Insurance Company",
        "PAYMENT_STATUS": "Paid"
    }
}


def test_noshow_prediction():
    """Send test prediction request to No-Show model"""
    
    print("=" * 80)
    print("📅 Testing No-Show Prediction Model - Fakeeh KSA")
    print("=" * 80)
    print(f"\n📍 Gateway URL: {GATEWAY_URL}")
    print(f"🔬 Model ID: {sample_appointment['model_id']}")
    print(f"👤 Client ID: {sample_appointment['client_id']}")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}\n")
    
    print("📋 Appointment Details:")
    print(f"   Patient MRN: {sample_appointment['inputs']['MRNO']}")
    print(f"   Doctor: {sample_appointment['inputs']['PROVIDER_NAME']}")
    print(f"   Department: {sample_appointment['inputs']['DEPARTMENT']}")
    print(f"   Appointment: {sample_appointment['inputs']['ALLOCATION_DATE_TIME']}")
    print(f"   Patient Age: {sample_appointment['inputs']['AGE']}")
    print(f"   Booking Channel: {sample_appointment['inputs']['APPT_BOOKING_CHANNEL']}\n")
    
    try:
        # Send prediction request
        print("📤 Sending prediction request...")
        response = requests.post(
            GATEWAY_URL,
            json=sample_appointment,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        # Check response status
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n✅ SUCCESS! Prediction received:\n")
            print("-" * 80)
            print(json.dumps(result, indent=2))
            print("-" * 80)
            
            print(f"\n🎯 Prediction: {result.get('prediction', 'N/A')}")
            print(f"📊 Confidence Score: {result.get('score', 'N/A')}")
            print(f"⚡ Latency: {result.get('latency_ms', 'N/A')} ms")
            print(f"🆔 Request ID: {result.get('request_id', 'N/A')}")
            
            if result.get('no_show_probability'):
                print(f"\n🚫 No-Show Probability: {result['no_show_probability']}")
            
            print("\n✅ Test PASSED!")
            return True
            
        else:
            print(f"\n❌ ERROR: Received status code {response.status_code}")
            print("\nResponse:")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to gateway")
        print("   Make sure the gateway is running:")
        print("   python main.py")
        return False
        
    except requests.exceptions.Timeout:
        print("\n❌ ERROR: Request timed out")
        print("   The AWS SageMaker endpoint may be slow or unavailable")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {str(e)}")
        return False
    
    finally:
        print("\n" + "=" * 80)


def test_gateway_health():
    """Check if gateway is healthy"""
    print("\n🏥 Checking gateway health...")
    
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Gateway status: {health.get('status', 'unknown')}")
            print(f"   Models loaded: {health.get('models_loaded', 0)}")
            return True
        else:
            print(f"⚠️  Gateway returned status {response.status_code}")
            return False
    except:
        print("❌ Gateway is not running")
        return False


def test_list_models():
    """List available models"""
    print("\n📋 Listing available models...")
    
    try:
        response = requests.get("http://localhost:8000/models", timeout=5)
        if response.status_code == 200:
            models = response.json()
            print(f"\n✅ Found {len(models.get('models', []))} model(s):")
            for model_id, config in models.get('models', {}).items():
                status = "🟢 Enabled" if config.get('enabled') else "🔴 Disabled"
                provider = config.get('provider', 'unknown')
                print(f"   • {model_id} ({provider}) v{config.get('version', '?')} - {status}")
            return True
        else:
            print(f"⚠️  Could not list models (status {response.status_code})")
            return False
    except:
        print("❌ Could not reach gateway")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" 🚀 ML INFERENCE GATEWAY - NO-SHOW MODEL TEST SUITE")
    print("=" * 80 + "\n")
    
    # Run tests
    health_ok = test_gateway_health()
    
    if health_ok:
        models_ok = test_list_models()
        
        if models_ok:
            prediction_ok = test_noshow_prediction()
            
            if prediction_ok:
                print("\n🎉 ALL TESTS PASSED!")
                print("\n💡 Next steps:")
                print("   1. View predictions in admin dashboard: http://localhost:8000/admin")
                print("   2. Check analytics tab for charts")
                print("   3. Review activity logs")
                print("   4. Test with different appointment scenarios")
                print("\n")
                exit(0)
            else:
                print("\n❌ Prediction test failed")
                print("\n💡 Troubleshooting:")
                print("   1. Check AWS credentials: aws configure")
                print("   2. Verify SageMaker endpoint is InService")
                print("   3. Check IAM permissions for SageMaker invoke")
                print("\n")
                exit(1)
        else:
            print("\n⚠️  Model listing failed but gateway is running")
            exit(1)
    else:
        print("\n❌ Gateway is not running. Start it with: python main.py")
        exit(1)
