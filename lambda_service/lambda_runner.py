import os
import asyncio
from fastapi import FastAPI, HTTPException, Request, Header
from lambda_service.payment_processor_handler import lambda_handler as payment_handler
from lambda_service.ticket_generator_handler import lambda_handler as generator_handler

app = FastAPI(title="AWS Lambda Simulator Runner", version="1.0")

# Secret key matching settings.LAMBDA_API_KEY
LAMBDA_API_KEY = os.getenv("LAMBDA_API_KEY", "super-secret-api-key")

def verify_api_key(x_api_key: str = Header(None)):
    if not x_api_key or x_api_key != LAMBDA_API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid or missing X-API-KEY")

@app.post("/payment")
async def invoke_payment(payload: Request, x_api_key: str = Header(None)):
    """
    Simulates calling payment Lambda.
    """
    verify_api_key(x_api_key)
    
    # Simulación de Latencia Real (1.5 seconds controlled latency)
    await asyncio.sleep(1.5)
    
    try:
        event = await payload.json()
        if not isinstance(event, dict):
            event = {}
    except Exception:
        event = {}
        
    result = payment_handler(event, None)
    
    if result["statusCode"] != 200:
        raise HTTPException(status_code=result["statusCode"], detail=result["body"])
    
    return result["body"]

@app.post("/generate_ticket")
async def invoke_generator(payload: Request, x_api_key: str = Header(None)):
    """
    Simulates calling ticket generator Lambda.
    """
    verify_api_key(x_api_key)
    
    try:
        event = await payload.json()
        if not isinstance(event, dict):
            event = {}
    except Exception:
        event = {}
        
    result = generator_handler(event, None)
    
    if result["statusCode"] != 200:
        raise HTTPException(status_code=result["statusCode"], detail=result["body"])
    
    return result["body"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
