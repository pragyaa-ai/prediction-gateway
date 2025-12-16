#!/usr/bin/env python3
"""
Test script for RESTful LOS endpoints
Tests the new /predict/{model_id} endpoint format
"""

import requests
import json
from datetime import datetime

# Gateway endpoint - NEW RESTful style
GATEWAY_URL = "http://localhost:8000/predict/los_fakeeh_ksa"

# Sample patient data - NO model_id needed in body!
sample_request = {
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


def test_restful_endpoint():
    """Test the new RESTful endpoint style"""
    
    print("=" * 80)
    print("🏥 Testing RESTful LOS Endpoint")
    print("=" * 80)
    print(f"\n📍 Gateway URL: {GATEWAY_URL}")
    print(f"🎯 Model: Specified in URL (los_fakeeh_ksa)")
    print(f"👤 Client ID: {sample_request.get('client_id')}")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}\n")
    
    print("💡 KEY DIFFERENCE:")
    print("   OLD: POST /v1/predict with model_id in body")
    print("   NEW: POST /predict/los_fakeeh_ksa with model in URL")
    print()
    
    try:
        # Send prediction request
        print("📤 Sending prediction request...")
        response = requests.post(
            GATEWAY_URL,
            json=sample_request,
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
            
            print("\n✅ RESTful endpoint test PASSED!")
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


def test_all_endpoint_styles():
    """Test both old and new endpoint styles"""
    print("\n" + "=" * 80)
    print(" 🔄 Testing Both Endpoint Styles")
    print("=" * 80 + "\n")
    
    # Test 1: New RESTful style
    print("1️⃣  Testing NEW RESTful style: /predict/los_fakeeh_ksa\n")
    restful_ok = test_restful_endpoint()
    
    # Test 2: Old style with model_id in body
    print("\n\n2️⃣  Testing OLD style: /v1/predict (model_id in body)\n")
    print("=" * 80)
    
    old_style_request = {
        "model_id": "los_fakeeh_ksa",  # In body for old style
        "client_id": sample_request["client_id"],
        "inputs": sample_request["inputs"]
    }
    
    try:
        response = requests.post(
            "http://localhost:8000/v1/predict",
            json=old_style_request,
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Old style endpoint also works!")
            old_ok = True
        else:
            print(f"⚠️  Old style returned status {response.status_code}")
            old_ok = False
    except Exception as e:
        print(f"❌ Old style failed: {e}")
        old_ok = False
    
    print("\n" + "=" * 80)
    print("\n📊 Test Results:")
    print(f"   RESTful style (/predict/model_id): {'✅ PASS' if restful_ok else '❌ FAIL'}")
    print(f"   Legacy style (/v1/predict):        {'✅ PASS' if old_ok else '❌ FAIL'}")
    
    if restful_ok and old_ok:
        print("\n🎉 Both endpoint styles work! Use RESTful for cleaner API.")
        return True
    elif restful_ok:
        print("\n✅ RESTful endpoint works (recommended)")
        return True
    else:
        print("\n❌ Tests failed")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print(" 🚀 ML INFERENCE GATEWAY - RESTful Endpoint Test")
    print("=" * 80 + "\n")
    
    success = test_all_endpoint_styles()
    
    if success:
        print("\n💡 Usage Examples:")
        print("\n   RESTful style (recommended):")
        print("   curl -X POST http://localhost:8000/predict/los_fakeeh_ksa \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"client_id\": \"hospital\", \"inputs\": {...}}'")
        print("\n   Legacy style (still supported):")
        print("   curl -X POST http://localhost:8000/v1/predict \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"model_id\": \"los_fakeeh_ksa\", \"inputs\": {...}}'")
        print("\n")
        exit(0)
    else:
        exit(1)
