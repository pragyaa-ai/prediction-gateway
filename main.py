from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, status, File, UploadFile, Query
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import io
import csv

from models.schemas import PredictionRequest, InferenceResponse
from models.registry import registry
from adapters.base import get_adapter
from services.opensearch import opensearch_client
from services.activity_log import activity_logger
from services.api_keys import api_key_manager
from services.email_service import email_service
from config.settings import settings
from auth.users import authenticate_user, create_access_token, verify_token, SUPER_ADMIN_USERS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="ML Inference Gateway",
    description="Unified gateway for multi-model ML inference with Azure integration",
    version="1.0.0"
)

# Templates for admin UI
templates = Jinja2Templates(directory="templates")

# OAuth2 for admin authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/admin/login", auto_error=False)

# Initialize service instances
activity_logger_instance = activity_logger
api_key_manager_instance = api_key_manager
email_service_instance = email_service
opensearch_instance = opensearch_client


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    """Dependency to get current authenticated user"""
    if not token:
        return None
    user = verify_token(token)
    return user


# ========== ADMIN AUTHENTICATION ==========

@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Admin login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/admin/login")
async def admin_login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Admin login endpoint"""
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        # Log failed login attempt
        activity_logger.log_activity(
            user_email=form_data.username,
            user_name="Unknown",
            action="login",
            details={"reason": "invalid_credentials"},
            status="failed"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log successful login
    activity_logger.log_activity(
        user_email=user["email"],
        user_name=user["name"],
        action="login",
        details={},
        status="success"
    )
    
    access_token = create_access_token(data={"sub": user["email"]})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }


# ========== INFERENCE API ==========

@app.post("/predict/{model_id}", response_model=InferenceResponse)
@app.post("/v1/predict/{model_id}", response_model=InferenceResponse)
async def predict_by_path(
    model_id: str,
    request: Request,
    background_tasks: BackgroundTasks
) -> InferenceResponse:
    """
    Model-specific inference endpoint (RESTful style)
    
    Usage: POST /predict/los_fakeeh_ksa
           POST /v1/predict/credit_risk_v2
    
    Request body only needs 'inputs' (client_id is optional):
    {
        "inputs": { ... }
    }
    
    Or with optional client_id:
    {
        "client_id": "custom_client",
        "inputs": { ... }
    }
    """
    # Build PredictionRequest with model_id from path
    from models.schemas import PredictionRequest
    
    request_body = await request.json()
    print(f"DEBUG: request_body type: {type(request_body)}")
    print(f"DEBUG: request_body: {request_body}")
    
    prediction_request = PredictionRequest(
        model_id=model_id,
        inputs=request_body.get("inputs", {}),
        client_id=request_body.get("client_id")  # None defaults to "on_prem_deployment"
    )
    
    # Call the main prediction logic
    return await predict(prediction_request, background_tasks)


@app.post("/v1/predict", response_model=InferenceResponse)
async def predict(
    request: PredictionRequest,
    background_tasks: BackgroundTasks
) -> InferenceResponse:
    """
    Main inference endpoint (legacy - supports model_id in body)
    
    1. Validates request
    2. Routes to correct model
    3. Returns standardized response
    4. Logs asynchronously to OpenSearch
    """
    print(f"DEBUG PREDICT: request type: {type(request)}")
    print(f"DEBUG PREDICT: request.inputs type: {type(request.inputs)}")
    print(f"DEBUG PREDICT: request.inputs: {request.inputs}")
    
    # Convert to canonical format
    inference_request = request.to_inference_request()
    
    print(f"DEBUG PREDICT: inference_request.inputs type: {type(inference_request.inputs)}")
    print(f"DEBUG PREDICT: inference_request.inputs: {inference_request.inputs}")
    
    # Get model configuration
    model_config = registry.get_model(inference_request.model_id)
    if not model_config:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{inference_request.model_id}' not found in registry"
        )
    
    # Check if model is enabled
    if not model_config.enabled:
        raise HTTPException(
            status_code=400,
            detail=f"Model '{inference_request.model_id}' is disabled"
        )
    
    # Get appropriate adapter
    try:
        adapter = get_adapter(model_config.provider)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # Execute prediction
    try:
        response = await adapter.predict(inference_request, model_config)
        
        # Log successful prediction asynchronously
        background_tasks.add_task(
            opensearch_client.log_prediction,
            inference_request,
            response,
            model_config,
            status="success"
        )
        
        return response
        
    except TimeoutError as e:
        # Log timeout
        background_tasks.add_task(
            _log_failed_prediction,
            inference_request,
            model_config,
            "timeout",
            str(e)
        )
        raise HTTPException(status_code=504, detail=f"Gateway timeout: {str(e)}")
    
    except Exception as e:
        # Log error
        background_tasks.add_task(
            _log_failed_prediction,
            inference_request,
            model_config,
            "error",
            str(e)
        )
        raise HTTPException(status_code=502, detail=f"Model error: {str(e)}")


async def _log_failed_prediction(request, config, status, error_msg):
    """Helper to log failed predictions"""
    from models.schemas import InferenceResponse
    
    # Create a dummy response for logging
    dummy_response = InferenceResponse(
        request_id=request.request_id,
        model_id=request.model_id,
        prediction=None,
        score=None,
        probability=None,
        latency_ms=0,
    )
    
    await opensearch_client.log_prediction(
        request,
        dummy_response,
        config,
        status=status,
        error_message=error_msg
    )


# ========== HEALTH & STATUS ==========

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Gateway health check"""
    opensearch_healthy = opensearch_client.is_healthy()
    
    return {
        "status": "healthy" if opensearch_healthy else "degraded",
        "gateway": "ok",
        "opensearch": "ok" if opensearch_healthy else "unavailable",
        "models_loaded": len(registry.list_models())
    }


@app.get("/models")
async def list_models() -> Dict[str, Any]:
    """List all registered models"""
    models = registry.list_models()
    
    return {
        "count": len(models),
        "models": {
            model_id: {
                "provider": config.provider,
                "version": config.version,
                "enabled": config.enabled,
                "timeout_ms": config.timeout_ms
            }
            for model_id, config in models.items()
        }
    }


@app.post("/admin/reload-config")
async def reload_config(current_user = Depends(get_current_user)) -> Dict[str, str]:
    """Reload model configuration from YAML (requires authentication)"""
    try:
        registry.reload()
        
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="reload_config",
            details={},
            status="success"
        )
        
        return {"status": "success", "message": "Configuration reloaded"}
    except Exception as e:
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="reload_config",
            details={"error": str(e)},
            status="failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/toggle-model/{model_id}")
async def toggle_model(model_id: str, current_user = Depends(get_current_user)) -> Dict[str, Any]:
    """Enable or disable a model (requires authentication)"""
    try:
        result = registry.toggle_model(model_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
        
        status = "enabled" if result else "disabled"
        
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="toggle_model",
            details={"model_id": model_id, "new_status": status},
            status="success"
        )
        
        return {
            "status": "success",
            "model_id": model_id,
            "enabled": result,
            "message": f"Model '{model_id}' {status}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== ADMIN UI ==========

@app.get("/admin")
async def admin_redirect():
    """Redirect /admin to /admin/dashboard"""
    return RedirectResponse(url="/admin/dashboard")


@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(request: Request, user = Depends(get_current_user)):
    """Admin dashboard UI (requires authentication)"""
    # For initial load, allow access (JS will handle redirect)
    # In production, enforce authentication here
    
    models = registry.list_models()
    # Convert ModelConfig objects to dicts for JSON serialization
    models_dict = {
        model_id: {
            "provider": config.provider,
            "version": config.version,
            "enabled": config.enabled,
            "timeout_ms": config.timeout_ms,
            "endpoint_url": config.endpoint_url
        }
        for model_id, config in models.items()
    }
    opensearch_healthy = opensearch_client.is_healthy()
    recent_predictions = opensearch_client.search_recent_predictions(limit=50)
    model_stats = opensearch_client.get_model_stats()
    
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "models": models_dict,
            "opensearch_healthy": opensearch_healthy,
            "recent_predictions": recent_predictions,
            "model_stats": model_stats,
            "opensearch_host": f"{settings.opensearch_host}:{settings.opensearch_port}"
        }
    )


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@app.get("/admin/analytics/timeline")
async def get_analytics_timeline(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: dict = Depends(get_current_user)
):
    """Get prediction volume timeline for the last N hours"""
    try:
        timeline_data = await opensearch_client.get_prediction_volume_timeline(hours=hours)
        return {
            "status": "success",
            "hours": hours,
            "data": timeline_data
        }
    except Exception as e:
        logger.error(f"Error fetching timeline: {e}")
        return {"status": "error", "message": str(e), "data": []}


@app.get("/admin/analytics/error-rates")
async def get_error_rates(current_user: dict = Depends(get_current_user)):
    """Get error rates by model"""
    try:
        error_rates = await opensearch_client.get_error_rate_by_model()
        return {
            "status": "success",
            "data": error_rates
        }
    except Exception as e:
        logger.error(f"Error fetching error rates: {e}")
        return {"status": "error", "message": str(e), "data": []}


@app.get("/admin/analytics/export")
async def export_analytics(
    format: str = Query(default="csv", regex="^(csv|json|excel)$"),
    model_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Export analytics data in CSV, JSON, or Excel format"""
    try:
        # Search predictions with filters
        predictions = await opensearch_client.search_predictions(
            model_id=model_id,
            from_date=from_date,
            to_date=to_date,
            limit=10000
        )
        
        if not predictions:
            raise HTTPException(status_code=404, detail="No data found for export")
        
        # Log activity
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="export_analytics",
            details={"format": format, "model_id": model_id, "count": len(predictions)},
            status="success"
        )
        
        if format == "json":
            return JSONResponse(content=predictions)
        
        elif format == "csv":
            output = io.StringIO()
            if predictions:
                writer = csv.DictWriter(output, fieldnames=predictions[0].keys())
                writer.writeheader()
                writer.writerows(predictions)
            
            return StreamingResponse(
                iter([output.getvalue()]),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename=analytics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
            )
        
        elif format == "excel":
            try:
                import pandas as pd
                df = pd.DataFrame(predictions)
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Analytics', index=False)
                output.seek(0)
                
                return StreamingResponse(
                    output,
                    media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    headers={"Content-Disposition": f"attachment; filename=analytics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"}
                )
            except ImportError:
                raise HTTPException(status_code=500, detail="Excel export requires pandas and openpyxl")
        
    except Exception as e:
        logger.error(f"Error exporting analytics: {e}")
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="export_analytics",
            details={"format": format, "error": str(e)},
            status="failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ACTIVITY LOGS ENDPOINTS
# ============================================================================

@app.get("/admin/activity-logs")
async def get_activity_logs(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get recent activity logs"""
    try:
        activities = activity_logger.get_recent_activities(limit=limit)
        return {
            "status": "success",
            "count": len(activities),
            "data": activities
        }
    except Exception as e:
        logger.error(f"Error fetching activity logs: {e}")
        return {"status": "error", "message": str(e), "data": []}


@app.get("/admin/activity-logs/user/{email}")
async def get_user_activity_logs(
    email: str,
    limit: int = Query(default=50, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get activity logs for a specific user"""
    try:
        activities = activity_logger.get_activities_by_user(email=email, limit=limit)
        return {
            "status": "success",
            "email": email,
            "count": len(activities),
            "data": activities
        }
    except Exception as e:
        logger.error(f"Error fetching user activity logs: {e}")
        return {"status": "error", "message": str(e), "data": []}


@app.get("/admin/activity-logs/action/{action}")
async def get_action_activity_logs(
    action: str,
    limit: int = Query(default=50, ge=1, le=500),
    current_user: dict = Depends(get_current_user)
):
    """Get activity logs for a specific action type"""
    try:
        activities = activity_logger.get_activities_by_action(action=action, limit=limit)
        return {
            "status": "success",
            "action": action,
            "count": len(activities),
            "data": activities
        }
    except Exception as e:
        logger.error(f"Error fetching action activity logs: {e}")
        return {"status": "error", "message": str(e), "data": []}


# ============================================================================
# API KEY MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/admin/api-keys")
async def create_api_key(
    client_name: str,
    client_email: str,
    permissions: Optional[List[str]] = None,
    current_user: dict = Depends(get_current_user)
):
    """Generate a new API key for a client"""
    try:
        key_data = await api_key_manager.generate_key(
            client_name=client_name,
            client_email=client_email,
            created_by=current_user["email"],
            permissions=permissions or ["predict"]
        )
        
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="create_api_key",
            details={"client_name": client_name, "client_email": client_email},
            status="success"
        )
        
        return {
            "status": "success",
            "message": "API key created successfully. Save it now - it won't be shown again!",
            "data": key_data
        }
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="create_api_key",
            details={"error": str(e)},
            status="failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/api-keys")
async def list_api_keys(current_user: dict = Depends(get_current_user)):
    """List all API keys (without showing the actual key values)"""
    try:
        keys = await api_key_manager.list_keys()
        return {
            "status": "success",
            "count": len(keys),
            "data": keys
        }
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        return {"status": "error", "message": str(e), "data": []}


@app.delete("/admin/api-keys/{key_hash}")
async def revoke_api_key(
    key_hash: str,
    current_user: dict = Depends(get_current_user)
):
    """Revoke an API key"""
    try:
        success = await api_key_manager.revoke_key(key_hash)
        
        if success:
            activity_logger.log_activity(
                user_email=current_user["email"],
                user_name=current_user["name"],
                action="revoke_api_key",
                details={"key_hash": key_hash},
                status="success"
            )
            return {"status": "success", "message": "API key revoked successfully"}
        else:
            raise HTTPException(status_code=404, detail="API key not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking API key: {e}")
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="revoke_api_key",
            details={"error": str(e)},
            status="failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/api-keys/{key_hash}/stats")
async def get_api_key_stats(
    key_hash: str,
    current_user: dict = Depends(get_current_user)
):
    """Get usage statistics for a specific API key"""
    try:
        stats = await api_key_manager.get_key_stats(key_hash)
        if stats:
            return {"status": "success", "data": stats}
        else:
            raise HTTPException(status_code=404, detail="API key not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching API key stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ADVANCED SEARCH ENDPOINT
# ============================================================================

@app.get("/admin/search")
async def search_predictions(
    model_id: Optional[str] = None,
    client_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """Advanced search for predictions with multiple filters"""
    try:
        results = await opensearch_client.search_predictions(
            model_id=model_id,
            client_id=client_id,
            status=status,
            from_date=from_date,
            to_date=to_date,
            limit=limit
        )
        
        return {
            "status": "success",
            "filters": {
                "model_id": model_id,
                "client_id": client_id,
                "status": status,
                "from_date": from_date,
                "to_date": to_date
            },
            "count": len(results),
            "data": results
        }
    except Exception as e:
        logger.error(f"Error searching predictions: {e}")
        return {"status": "error", "message": str(e), "data": []}


# ============================================================================
# MODEL TESTING ENDPOINT
# ============================================================================

@app.post("/admin/test-model")
async def test_model(
    model_id: str,
    test_input: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Test a model with custom input from the admin dashboard"""
    try:
        # Get model config
        config = registry.get_model(model_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
        
        if not config.enabled:
            raise HTTPException(status_code=400, detail=f"Model '{model_id}' is disabled")
        
        # Get adapter and make prediction
        adapter = get_adapter(config)
        start_time = datetime.utcnow()
        result = await adapter.predict(test_input)
        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        # Log activity
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="test_model",
            details={"model_id": model_id, "latency_ms": latency_ms},
            status="success"
        )
        
        return {
            "status": "success",
            "model_id": model_id,
            "latency_ms": round(latency_ms, 2),
            "input": test_input,
            "output": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing model: {e}")
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="test_model",
            details={"model_id": model_id, "error": str(e)},
            status="failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BATCH PREDICTIONS ENDPOINTS
# ============================================================================

@app.post("/admin/batch-upload")
async def batch_upload_predictions(
    file: UploadFile = File(...),
    model_id: str = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload a CSV file for batch predictions"""
    try:
        # Validate model
        config = registry.get_model(model_id)
        if not config:
            raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
        
        if not config.enabled:
            raise HTTPException(status_code=400, detail=f"Model '{model_id}' is disabled")
        
        # Read CSV file
        contents = await file.read()
        csv_reader = csv.DictReader(io.StringIO(contents.decode('utf-8')))
        rows = list(csv_reader)
        
        if not rows:
            raise HTTPException(status_code=400, detail="CSV file is empty")
        
        # Process predictions
        adapter = get_adapter(config)
        results = []
        
        for idx, row in enumerate(rows):
            try:
                prediction = await adapter.predict(row)
                results.append({
                    "row": idx + 1,
                    "status": "success",
                    "input": row,
                    "output": prediction
                })
            except Exception as e:
                results.append({
                    "row": idx + 1,
                    "status": "error",
                    "input": row,
                    "error": str(e)
                })
        
        # Log activity
        success_count = sum(1 for r in results if r["status"] == "success")
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="batch_upload",
            details={
                "model_id": model_id,
                "total_rows": len(rows),
                "success_count": success_count,
                "error_count": len(rows) - success_count
            },
            status="success"
        )
        
        return {
            "status": "success",
            "model_id": model_id,
            "total_rows": len(rows),
            "success_count": success_count,
            "error_count": len(rows) - success_count,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing batch upload: {e}")
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="batch_upload",
            details={"error": str(e)},
            status="failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EMAIL CONFIGURATION ENDPOINTS
# ============================================================================

@app.post("/admin/email/test")
async def test_email(
    to_email: str,
    current_user: dict = Depends(get_current_user)
):
    """Send a test email to verify SMTP configuration"""
    try:
        await email_service.send_email(
            to_emails=[to_email],
            subject="Test Email from ML Inference Gateway",
            body=f"This is a test email sent by {current_user['name']} ({current_user['email']}) at {datetime.utcnow().isoformat()}"
        )
        
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="test_email",
            details={"to_email": to_email},
            status="success"
        )
        
        return {
            "status": "success",
            "message": f"Test email sent to {to_email}"
        }
    except Exception as e:
        logger.error(f"Error sending test email: {e}")
        activity_logger.log_activity(
            user_email=current_user["email"],
            user_name=current_user["name"],
            action="test_email",
            details={"error": str(e)},
            status="failed"
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/email/config")
async def get_email_config(current_user: dict = Depends(get_current_user)):
    """Get current email configuration (without password)"""
    return {
        "status": "success",
        "config": {
            "smtp_host": settings.smtp_host,
            "smtp_port": settings.smtp_port,
            "smtp_user": settings.smtp_user,
            "from_email": settings.from_email,
            "is_configured": bool(settings.smtp_host and settings.smtp_user and settings.smtp_password)
        }
    }


@app.get("/")
async def root():
    """Root endpoint"""
    # Get list of enabled models for quick reference
    enabled_models = [
        model_id for model_id, config in registry.list_models().items()
        if config.enabled
    ]
    
    return {
        "service": "ML Inference Gateway",
        "version": "1.0.0",
        "endpoints": {
            "inference_legacy": "/v1/predict (with model_id in body)",
            "inference_restful": "/predict/{model_id} or /v1/predict/{model_id}",
            "health": "/health",
            "models": "/models",
            "admin": "/admin"
        },
        "enabled_models": enabled_models,
        "examples": {
            "los_prediction": "POST /predict/los_fakeeh_ksa",
            "credit_risk": "POST /predict/credit_risk_v2"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.gateway_host,
        port=settings.gateway_port,
        reload=True
    )
