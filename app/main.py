from fastapi import FastAPI, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from app.core.config import settings
from app.api.endpoints import auth, users, chat, subscription
from app.services.stripe import StripeService
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="FastAPI MongoDB Auth")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS_LIST,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(auth.router, prefix="/auth")
app.include_router(users.router, prefix="/users")
app.include_router(chat.router, prefix="/chat")
app.include_router(subscription.router, prefix="/subscription")


@app.get("/")
async def root():
    return {"message": "Hello World"}

# Direct webhook endpoint for Stripe (since Stripe calls /webhook)
@app.post("/webhook")
async def stripe_webhook_direct(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature")
):
    """Direct webhook endpoint for Stripe events"""
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe signature")
    
    try:
        # Get raw body
        body = await request.body()
        
        # Get Stripe service
        stripe_service = StripeService(app.mongodb)
        
        # Process webhook
        result = await stripe_service.handle_webhook(body, stripe_signature)
        return JSONResponse(content=result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.on_event("startup")
async def startup_db_client():
    app.mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
    app.mongodb = app.mongodb_client[settings.DATABASE_NAME]

@app.on_event("shutdown")
async def shutdown_db_client():
    app.mongodb_client.close()