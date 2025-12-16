#!/bin/bash
# Quick test commands for ML Inference Gateway

echo "🚀 ML Inference Gateway - Quick Test Commands"
echo "=============================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 1. Health Check
echo -e "${BLUE}1. Testing Gateway Health...${NC}"
curl -s http://localhost:8000/health | jq '.'
echo ""

# 2. List Models
echo -e "${BLUE}2. Listing Available Models...${NC}"
curl -s http://localhost:8000/models | jq '.'
echo ""

# 3. Test LOS Prediction
echo -e "${BLUE}3. Testing LOS Fakeeh KSA Model...${NC}"
curl -s -X POST http://localhost:8000/v1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": "los_fakeeh_ksa",
    "client_id": "fakeeh_hospital",
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
      "EXPIRED": false,
      "EXPIRED_encoded": 0,
      "LOS_GROUP": "LONG",
      "LOS_GROUP_encoded": 2,
      "IP_IN_PREVIOUS_30_DAYS": false,
      "IP_IN_PREVIOUS_30_DAYS_encoded": 0,
      "HOSPITALIZATION_PREVIOUS_YEAR": 0
    }
  }' | jq '.'
echo ""

echo -e "${GREEN}✅ All tests complete!${NC}"
echo ""
echo "📊 View results in admin dashboard: http://localhost:8000/admin"
echo "📧 Login credentials: krishna@pragyaa.ai / changeme123"
