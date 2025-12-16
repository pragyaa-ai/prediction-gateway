#!/usr/bin/env python3
"""
Test script for ML Inference Gateway
"""
import requests
import json
import time
from typing import Dict, Any

GATEWAY_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{GATEWAY_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200


def test_list_models():
    """Test model listing"""
    print("📋 Testing model listing...")
    response = requests.get(f"{GATEWAY_URL}/models")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}\n")
    return response.status_code == 200


def test_prediction(model_id: str, inputs: Dict[str, Any], client_id: str = "test_client"):
    """Test prediction endpoint"""
    print(f"🤖 Testing prediction for model: {model_id}...")
    
    payload = {
        "model_id": model_id,
        "inputs": inputs,
        "client_id": client_id
    }
    
    start = time.time()
    response = requests.post(
        f"{GATEWAY_URL}/v1/predict",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    elapsed = (time.time() - start) * 1000
    
    print(f"Status: {response.status_code}")
    print(f"Client latency: {elapsed:.0f}ms")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print(f"✅ Prediction successful!")
    else:
        print(f"❌ Error: {response.text}")
    
    print()
    return response.status_code == 200


def test_invalid_model():
    """Test with invalid model ID"""
    print("🚫 Testing invalid model ID...")
    response = requests.post(
        f"{GATEWAY_URL}/v1/predict",
        json={
            "model_id": "non_existent_model",
            "inputs": {"test": 123},
            "client_id": "test"
        }
    )
    print(f"Status: {response.status_code} (expected 400)")
    print(f"Response: {response.json()}\n")
    return response.status_code == 400


def main():
    """Run all tests"""
    print("=" * 60)
    print("🚀 ML Inference Gateway - Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health()))
    
    # Test 2: List models
    results.append(("List Models", test_list_models()))
    
    # Test 3: Credit risk prediction
    credit_inputs = {
        "age": 42,
        "income": 70000,
        "credit_score": 680
    }
    results.append((
        "Credit Risk Prediction",
        test_prediction("credit_risk_v2", credit_inputs)
    ))
    
    # Test 4: Invalid model (should fail gracefully)
    results.append(("Invalid Model (Expected Fail)", test_invalid_model()))
    
    # Test 5: Fraud detection (if configured)
    fraud_inputs = {
        "transaction_amount": 1500.00,
        "merchant_id": "MERCH_12345",
        "user_age": 35,
        "transaction_hour": 14
    }
    # Uncomment if fraud_detection_v1 is configured
    # results.append((
    #     "Fraud Detection",
    #     test_prediction("fraud_detection_v1", fraud_inputs)
    # ))
    
    # Summary
    print("=" * 60)
    print("📊 Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print()
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    print(f"Total: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 All tests passed!")
    else:
        print("⚠️  Some tests failed")


if __name__ == "__main__":
    main()
