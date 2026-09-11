from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image
from PIL.ExifTags import TAGS
from google import genai
import io
import uuid
import random
import time
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Fraud Detection API Prototype - V2 Premium")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Gemini Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY")) if os.environ.get("GEMINI_API_KEY") else None

sessions = {}
ORDERS_DB = {}

PRODUCTS = [
    {
        "id": "prod_1",
        "name": "Sony Alpha a7 IV Camera",
        "price": 2499.99,
        "image": "https://images.unsplash.com/photo-1516035069371-29a1b244cc32?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
        "category": "Electronics"
    },
    {
        "id": "prod_2",
        "name": "Nike Air Zoom Pegasus",
        "price": 129.99,
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
        "category": "Apparel"
    },
    {
        "id": "prod_3",
        "name": "Apple MacBook Pro 16",
        "price": 2499.00,
        "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
        "category": "Electronics"
    },
    {
        "id": "prod_4",
        "name": "Bose QuietComfort Headphones",
        "price": 329.00,
        "image": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
        "category": "Accessories"
    },
    {
        "id": "prod_5",
        "name": "YETI Rambler Tumbler",
        "price": 35.00,
        "image": "https://images.unsplash.com/photo-1622287162716-f311baa1a2b8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
        "category": "Accessories"
    },
    {
        "id": "prod_6",
        "name": "The North Face Nuptse Jacket",
        "price": 280.00,
        "image": "https://images.unsplash.com/photo-1559551409-dadc959f76b8?ixlib=rb-4.0.3&auto=format&fit=crop&w=500&q=80",
        "category": "Apparel"
    },
    {
        "id": "prod_7",
        "name": "Acer Wireless Transparent Mouse",
        "price": 25.00,
        "image": "/acer_mouse.jpg",
        "category": "Accessories"
    }
]

def generate_code():
    return "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=4))

class OrderRequest(BaseModel):
    product_id: str

@app.get("/api/v1/products")
async def get_products():
    return PRODUCTS

@app.post("/api/v1/orders")
async def create_order(request: OrderRequest):
    product = next((p for p in PRODUCTS if p["id"] == request.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
        
    order_id = f"ORD-{random.randint(10000, 99999)}"
    ORDERS_DB[order_id] = {
        "product_id": product["id"],
        "product_name": product["name"],
        "price": product["price"],
        "image": product["image"],
        "status": "delivered",
        "order_date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    return {"status": "success", "order_id": order_id}

@app.get("/api/v1/orders")
async def get_orders():
    # Return orders sorted by newest first (dict order is insertion order in py3.7+, but reverse it)
    return [{"order_id": k, **v} for k, v in reversed(ORDERS_DB.items())]

@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: str):
    if order_id not in ORDERS_DB:
        raise HTTPException(status_code=404, detail="Order not found")
    return {"order_id": order_id, **ORDERS_DB[order_id]}

@app.post("/api/v1/analyze-layer1")
async def analyze_layer1(
    file: UploadFile = File(...), 
    order_id: str = Form(...),
    reason: str = Form(default="Not Specified"),
    comments: str = Form(default="")
):
    if order_id not in ORDERS_DB:
        raise HTTPException(status_code=404, detail="Order not found")
        
    order = ORDERS_DB[order_id]
    product_name = order["product_name"]
    contents = await file.read()
    
    try:
        image = Image.open(io.BytesIO(contents))
        
        # 1. Visual Verification using Gemini
        if not client:
             raise Exception("Missing GEMINI_API_KEY environment variable.")
             
        prompt = f'''
        You are a strict fraud detection AI for a premium retail platform. I am verifying an online return for the product: '{product_name}'.
        
        Analyze this image and answer the following:
        1. Is the product '{product_name}' (or something closely resembling it from the same category) clearly visible in the image?
        
        If true, respond EXACTLY and ONLY with the word "APPROVED".
        If false, respond with a short explanation of what is missing or incorrect, starting with "REJECTED: ". Be very strict.
        '''
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[
                prompt,
                image
            ]
        )
        
        result_text = response.text.strip()
        if not result_text.startswith("APPROVED"):
            raise HTTPException(status_code=403, detail=f"Visual Verification Failed. {result_text}")
            
        # 2. EXIF Match Check (Hardware tags)
        has_hardware_tags = False
        exif_data = image.getexif()
        
        if exif_data:
            # Check 0th IFD for Make (271), Model (272)
            has_hardware_tags = any(tag in exif_data for tag in [271, 272])
            
            # Check Exif IFD for FNumber (33437), ExposureTime (33434), ISOSpeedRatings (34855), FocalLength (37386)
            if not has_hardware_tags:
                exif_ifd = exif_data.get_ifd(0x8769)
                if exif_ifd:
                    has_hardware_tags = any(tag in exif_ifd for tag in [33434, 33437, 34855, 37386])
                    
        if has_hardware_tags:
            ORDERS_DB[order_id]["status"] = "Returned"
            return {"status": "approved", "message": "Refund processed."}
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis Error: {str(e)}")
    
    # Missing EXIF -> trap
    session_id = str(uuid.uuid4())
    code = generate_code()
    sessions[session_id] = {
        "code": code,
        "expires_at": time.time() + 60,
        "order_id": order_id,
        "reason": reason
    }
    
    return {
        "status": "challenge_required",
        "session_id": session_id,
        "code": code,
        "timeout": 60
    }

@app.get("/api/v1/refresh-session/{session_id}")
async def refresh_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    new_code = generate_code()
    sessions[session_id]["code"] = new_code
    sessions[session_id]["expires_at"] = time.time() + 60
    
    return {
        "status": "refreshed",
        "code": new_code,
        "timeout": 60
    }

@app.post("/api/v1/analyze-layer2")
async def analyze_layer2(
    file: UploadFile = File(...),
    session_id: str = Form(...)
):
    if session_id not in sessions:
        raise HTTPException(status_code=403, detail="Invalid session")
        
    session = sessions[session_id]
    order = ORDERS_DB[session["order_id"]]
    product_name = order["product_name"]
    expected_code = session["code"]
    
    # Process 1: Time Check
    if time.time() > session["expires_at"]:
        raise HTTPException(status_code=403, detail="Session expired. Please refresh.")
        
    # Process 2: EXIF Match Check
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
        exif = image.getexif()
        
        has_mock_signature = False
        if exif:
            for tag_id in exif:
                data = exif.get(tag_id)
                if isinstance(data, bytes):
                    try:
                        data = data.decode('utf-8')
                    except UnicodeDecodeError:
                        pass
                if "Mock_Native_Camera" in str(data):
                    has_mock_signature = True
                    break
                    
        if not has_mock_signature:
            raise HTTPException(status_code=403, detail="Suspicious metadata. Bypass attempt detected.")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image format")
        
    # Process 3: Visual Verification using Gemini
    try:
        if not client:
             raise Exception("Missing GEMINI_API_KEY environment variable. Unable to process visual verification.")
             
        prompt = f'''
        You are a strict fraud detection AI for a premium retail platform. I am verifying an online return for the product: '{product_name}'.
        The user was asked to write the code '{expected_code}' on a piece of paper and photograph it physically next to the item.
        
        Analyze this image and answer the following:
        1. Is the product '{product_name}' (or something closely resembling it from the same category) visible in the image?
        2. Is there a handwritten note or text clearly showing the code '{expected_code}'?
        
        If BOTH are true, respond EXACTLY and ONLY with the word "APPROVED".
        If EITHER is false, respond with a short explanation of what is missing or incorrect, starting with "REJECTED: ". Be very strict.
        '''
        
        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=[
                prompt,
                image
            ]
        )
        
        result_text = response.text.strip()
        if not result_text.startswith("APPROVED"):
            raise HTTPException(status_code=403, detail=f"Visual Verification Failed. {result_text}")
            
        ORDERS_DB[session["order_id"]]["status"] = "Returned"
        return {"status": "approved", "message": f"Proof of life visually verified for '{product_name}'. Refund processed."}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Vision Error: {str(e)}")

class WebhookPayload(BaseModel):
    dispute_id: str
    order_id: str
    user_id: str
    reason: str
    evidence_score: float

def ce_3_0_matching_logic(evidence_score: float, reason: str) -> dict:
    """
    Mock Confidence Engine (CE) 3.0 Matching Logic.
    Calculates a fraud confidence score based on the evidence and reason.
    Returns whether to auto-block the user.
    """
    base_confidence = evidence_score * 100
    
    # Heuristics based on reason
    if reason.lower() in ["empty_box", "wrong_item"]:
        base_confidence += 15.0
    elif reason.lower() == "item_defective":
        base_confidence -= 10.0
        
    confidence_score = min(max(base_confidence, 0.0), 100.0)
    
    # CE 3.0 Threshold: Auto-block if confidence score > 85%
    auto_block = confidence_score >= 85.0
    
    return {
        "confidence_score": round(confidence_score, 2),
        "auto_block": auto_block,
        "ce_version": "3.0"
    }

@app.post("/api/v1/dispute-webhook")
async def dispute_webhook(payload: WebhookPayload):
    """
    Webhook endpoint to receive dispute events from payment processors.
    Utilizes CE 3.0 matching logic to determine if a user should be auto-blocked.
    """
    ce_result = ce_3_0_matching_logic(payload.evidence_score, payload.reason)
    
    response = {
        "status": "received",
        "dispute_id": payload.dispute_id,
        "action_taken": "user_blocked" if ce_result["auto_block"] else "flagged_for_review",
        "ce_analysis": ce_result
    }
    
    return response

app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
