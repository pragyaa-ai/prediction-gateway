#!/usr/bin/env python3
"""
Test script for LOS Fakeeh KSA model
Sends a sample prediction request to verify the gateway is working
"""

import requests
import json
from datetime import datetime

# Gateway endpoint
GATEWAY_URL = "http://localhost:8000/v1/predict"

# Sample patient data for LOS prediction
sample_patient = {
    "model_id": "los_fakeeh_ksa",
    "client_id": "fakeeh_hospital_test",
    "inputs": {
        "MARITAL_STATUS": "",
        "NATIONALITY": "BRITISH",
        "Column1": 0,
        "BMI": 35.841,
        "MRNO": 12345678,
        "AGE": 38,
        "AGE_GROUP": "Adult",
        "AGE_GROUP_encoded": 1,
        "ADMISSION_TYPE": "Regular Admission",
        "ADMISSION_TYPE_encoded": 2,
        "ADMISSION_LEVEL": "Delivery Room",
        "ADMISSION_LEVEL_encoded": 3,
        "ROOM_TYPE": "Ward",
        "ROOM_TYPE_encoded": 1,
        "SOURCE_OF_ADMN": "ER",
        "SOURCE_OF_ADMN_encoded": 1,
        "PRIMARY": "R10.3-Pain localised to other parts of lower abdomen",
        "PRIMARY_encoded": 5,
        "SECONDARY": "O34.2-Maternal care due to uterine scar from previous surgery",
        "SURGERY_NAME": "",
        "PAYER": "Saudi Enaya Cooperative Insurance/CLASS A+ - Suite Room",
        "PREVIOUS_IP": 0,
        "SODIUM": 0,
        "SODIUM_available": 1,
        "GLUCOSE": "",
        "BLOOD_UREA_NITROGEN": 0,
        "BLOOD_UREA_NITROGEN_available": 1,
        "C_REACTIVE_PROTEIN": 0,
        "C_REACTIVE_PROTEIN_available": 1,
        "CREATININE": 0,
        "CREATININE_available": 1,
        "WBC": "",
        "PLATELETS_COUNT": 206,
        "PLATELETS_COUNT_available": 1,
        "HEMATOGY_TESTS": "CBC",
        "CHEMISTRY_TESTS": "ORAL GLUCOSE TOLERANCE TEST (FASTING)  ;  ORAL GLUCOSE TOLERANCE TEST (FIRST HOUR)  ;  GLYCOSYLATED HEMOGLOBIN.(HBA1C)  ;  ORAL GLUCOSE TOLERANCE TEST (SECOND HOUR)",
        "IMMUNOLOGY_TESTS": "",
        "CULTURE_TESTS": "PRENATAL VAGINAL SWAB ( GROUP - B STREPTOCOCCUS -  CULTURE & SENSITIVITY )",
        "OXYGEN_SATURATION": 100,
        "TEMPERATURE": 36.9,
        "BPSYSTOLIC": 118,
        "BPDIASTOLIC": 79,
        "PULSE": 85,
        "RESPIRATION": 20,
        "RADIOLOGY_TESTS": "US- Obstetrical Targeted Obstetric Ultrasound  ;  US- Obstetrical Routine Scan",
        "TOTAL_MEDICINE_ORDERED": 0,
        "MEDICATION_TYPE": "",
        "CLINICAL_WARNING": "",
        "EXPIRED": False,
        "EXPIRED_encoded": 0,
        "LOS_GROUP": "LONG",
        "LOS_GROUP_encoded": 2,
        "IP_IN_PREVIOUS_30_DAYS": False,
        "IP_IN_PREVIOUS_30_DAYS_encoded": 0,
        "HOSPITALIZATION_PREVIOUS_YEAR": 0
    }
}


def test_los_prediction():
    """Send test prediction request to LOS model"""
    
    print("=" * 80)
    print("🏥 Testing LOS Fakeeh KSA Model")
    print("=" * 80)
    print(f"\n📍 Gateway URL: {GATEWAY_URL}")
    print(f"🔬 Model ID: {sample_patient['model_id']}")
    print(f"👤 Client ID: {sample_patient['client_id']}")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}\n")
    
    try:
        # Send prediction request
        print("📤 Sending prediction request...")
        response = requests.post(
            GATEWAY_URL,
            json=sample_patient,
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
            
            if result.get('los_category'):
                print(f"\n🏥 LOS Category: {result['los_category']}")
            
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
        print("   The Azure ML endpoint may be slow or unavailable")
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
                print(f"   • {model_id} v{config.get('version', '?')} - {status}")
            return True
        else:
            print(f"⚠️  Could not list models (status {response.status_code})")
            return False
    except:
        print("❌ Could not reach gateway")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" 🚀 ML INFERENCE GATEWAY - LOS MODEL TEST SUITE")
    print("=" * 80 + "\n")
    
    # Run tests
    health_ok = test_gateway_health()
    
    if health_ok:
        models_ok = test_list_models()
        
        if models_ok:
            prediction_ok = test_los_prediction()
            
            if prediction_ok:
                print("\n🎉 ALL TESTS PASSED!")
                print("\n💡 Next steps:")
                print("   1. View predictions in admin dashboard: http://localhost:8000/admin")
                print("   2. Check analytics tab for charts")
                print("   3. Review activity logs")
                print("\n")
                exit(0)
            else:
                print("\n❌ Prediction test failed")
                exit(1)
        else:
            print("\n⚠️  Model listing failed but gateway is running")
            exit(1)
    else:
        print("\n❌ Gateway is not running. Start it with: python main.py")
        exit(1)
