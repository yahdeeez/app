from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
import os
import logging
import jwt
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
import hashlib
from bson import ObjectId
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
SECRET_KEY = "your-secret-key-change-in-production"

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, parent_id: str):
        await websocket.accept()
        self.active_connections[parent_id] = websocket

    def disconnect(self, parent_id: str):
        if parent_id in self.active_connections:
            del self.active_connections[parent_id]

    async def send_personal_message(self, message: dict, parent_id: str):
        if parent_id in self.active_connections:
            await self.active_connections[parent_id].send_text(json.dumps(message))

manager = ConnectionManager()

# Models
class Parent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    password_hash: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Teen(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    parent_id: str
    device_id: str
    phone_number: Optional[str] = None
    age: Optional[int] = None
    screen_time_limits: Dict[str, int] = Field(default_factory=dict)  # day: minutes
    bedtime_schedule: Dict[str, str] = Field(default_factory=dict)  # day: time
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Location(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teen_id: str
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    address: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Geofence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teen_id: str
    name: str
    latitude: float
    longitude: float
    radius: float  # in meters
    type: str = "safe"  # safe, restricted
    notify_on_enter: bool = True
    notify_on_exit: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AppUsage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teen_id: str
    app_name: str
    package_name: str
    usage_time: int  # in minutes
    date: str  # YYYY-MM-DD
    last_used: datetime = Field(default_factory=datetime.utcnow)

class AppControl(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teen_id: str
    package_name: str
    is_blocked: bool = False
    time_limit: Optional[int] = None  # minutes per day
    created_at: datetime = Field(default_factory=datetime.utcnow)

class WebHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    teen_id: str
    url: str
    title: str
    visit_count: int = 1
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Alert(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str
    teen_id: str
    type: str  # geofence, screen_time, app_blocked, etc.
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Input Models
class ParentCreate(BaseModel):
    email: str
    password: str
    name: str

class ParentLogin(BaseModel):
    email: str
    password: str

class TeenCreate(BaseModel):
    name: str
    device_id: str
    phone_number: Optional[str] = None
    age: Optional[int] = None

class LocationCreate(BaseModel):
    teen_id: str
    latitude: float
    longitude: float
    accuracy: Optional[float] = None
    address: Optional[str] = None

class GeofenceCreate(BaseModel):
    teen_id: str
    name: str
    latitude: float
    longitude: float
    radius: float
    type: str = "safe"
    notify_on_enter: bool = True
    notify_on_exit: bool = True

class AppUsageCreate(BaseModel):
    teen_id: str
    app_name: str
    package_name: str
    usage_time: int
    date: str

class AppControlCreate(BaseModel):
    teen_id: str
    package_name: str
    is_blocked: bool = False
    time_limit: Optional[int] = None

class WebHistoryCreate(BaseModel):
    teen_id: str
    url: str
    title: str

# Utility functions
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def create_token(parent_id: str) -> str:
    payload = {
        "parent_id": parent_id,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

async def get_current_parent(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["parent_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Parent Authentication Endpoints
@api_router.post("/auth/register")
async def register_parent(parent_data: ParentCreate):
    # Check if email already exists
    existing_parent = await db.parents.find_one({"email": parent_data.email})
    if existing_parent:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new parent
    parent = Parent(
        email=parent_data.email,
        password_hash=hash_password(parent_data.password),
        name=parent_data.name
    )
    
    await db.parents.insert_one(parent.dict())
    token = create_token(parent.id)
    
    return {
        "token": token,
        "parent": {
            "id": parent.id,
            "email": parent.email,
            "name": parent.name
        }
    }

@api_router.post("/auth/login")
async def login_parent(login_data: ParentLogin):
    parent = await db.parents.find_one({"email": login_data.email})
    if not parent or not verify_password(login_data.password, parent["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = create_token(parent["id"])
    return {
        "token": token,
        "parent": {
            "id": parent["id"],
            "email": parent["email"],
            "name": parent["name"]
        }
    }

# Teen Management Endpoints
@api_router.post("/teens", response_model=Teen)
async def create_teen(teen_data: TeenCreate, parent_id: str = Depends(get_current_parent)):
    teen = Teen(
        name=teen_data.name,
        parent_id=parent_id,
        device_id=teen_data.device_id,
        phone_number=teen_data.phone_number,
        age=teen_data.age
    )
    
    await db.teens.insert_one(teen.dict())
    return teen

@api_router.get("/teens", response_model=List[Teen])
async def get_teens(parent_id: str = Depends(get_current_parent)):
    teens = await db.teens.find({"parent_id": parent_id}).to_list(100)
    return [Teen(**teen) for teen in teens]

@api_router.get("/teens/{teen_id}", response_model=Teen)
async def get_teen(teen_id: str, parent_id: str = Depends(get_current_parent)):
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    return Teen(**teen)

# Location Tracking Endpoints
@api_router.post("/locations")
async def create_location(location_data: LocationCreate):
    # Verify teen exists
    teen = await db.teens.find_one({"id": location_data.teen_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    location = Location(**location_data.dict())
    await db.locations.insert_one(location.dict())
    
    # Check geofences
    geofences = await db.geofences.find({"teen_id": location_data.teen_id}).to_list(100)
    for geofence_data in geofences:
        geofence = Geofence(**geofence_data)
        # Simple distance calculation (you might want to use a proper geospatial library)
        distance = ((location.latitude - geofence.latitude) ** 2 + 
                   (location.longitude - geofence.longitude) ** 2) ** 0.5 * 111000  # rough meters
        
        if distance <= geofence.radius:
            # Create alert
            alert = Alert(
                parent_id=teen["parent_id"],
                teen_id=location_data.teen_id,
                type="geofence_enter",
                message=f"{teen['name']} entered {geofence.name}"
            )
            await db.alerts.insert_one(alert.dict())
            
            # Send real-time notification
            await manager.send_personal_message(
                {
                    "type": "geofence_alert",
                    "teen_name": teen["name"],
                    "geofence_name": geofence.name,
                    "action": "entered"
                },
                teen["parent_id"]
            )
    
    return {"status": "success", "location_id": location.id}

@api_router.get("/teens/{teen_id}/locations")
async def get_teen_locations(teen_id: str, limit: int = 100, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    locations = await db.locations.find({"teen_id": teen_id}).sort("timestamp", -1).limit(limit).to_list(limit)
    return [Location(**loc) for loc in locations]

@api_router.get("/teens/{teen_id}/current-location")
async def get_current_location(teen_id: str, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    location = await db.locations.find_one({"teen_id": teen_id}, sort=[("timestamp", -1)])
    if not location:
        raise HTTPException(status_code=404, detail="No location data found")
    
    return Location(**location)

# Geofencing Endpoints
@api_router.post("/geofences", response_model=Geofence)
async def create_geofence(geofence_data: GeofenceCreate, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": geofence_data.teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    geofence = Geofence(**geofence_data.dict())
    await db.geofences.insert_one(geofence.dict())
    return geofence

@api_router.get("/teens/{teen_id}/geofences")
async def get_teen_geofences(teen_id: str, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    geofences = await db.geofences.find({"teen_id": teen_id}).to_list(100)
    return [Geofence(**geofence) for geofence in geofences]

# App Usage Endpoints
@api_router.post("/app-usage")
async def create_app_usage(usage_data: AppUsageCreate):
    # Verify teen exists
    teen = await db.teens.find_one({"id": usage_data.teen_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    # Check if app usage for this date already exists
    existing_usage = await db.app_usage.find_one({
        "teen_id": usage_data.teen_id,
        "package_name": usage_data.package_name,
        "date": usage_data.date
    })
    
    if existing_usage:
        # Update existing usage
        await db.app_usage.update_one(
            {"id": existing_usage["id"]},
            {"$set": {"usage_time": usage_data.usage_time, "last_used": datetime.utcnow()}}
        )
        return {"status": "updated", "usage_id": existing_usage["id"]}
    else:
        # Create new usage record
        usage = AppUsage(**usage_data.dict())
        await db.app_usage.insert_one(usage.dict())
        return {"status": "created", "usage_id": usage.id}

@api_router.get("/teens/{teen_id}/app-usage")
async def get_teen_app_usage(teen_id: str, date: Optional[str] = None, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    query = {"teen_id": teen_id}
    if date:
        query["date"] = date
    
    usage_data = await db.app_usage.find(query).to_list(1000)
    return [AppUsage(**usage) for usage in usage_data]

# App Control Endpoints
@api_router.post("/app-controls", response_model=AppControl)
async def create_app_control(control_data: AppControlCreate, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": control_data.teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    # Check if control already exists
    existing_control = await db.app_controls.find_one({
        "teen_id": control_data.teen_id,
        "package_name": control_data.package_name
    })
    
    if existing_control:
        # Update existing control
        await db.app_controls.update_one(
            {"id": existing_control["id"]},
            {"$set": control_data.dict(exclude_unset=True)}
        )
        updated_control = await db.app_controls.find_one({"id": existing_control["id"]})
        return AppControl(**updated_control)
    else:
        # Create new control
        control = AppControl(**control_data.dict())
        await db.app_controls.insert_one(control.dict())
        return control

@api_router.get("/teens/{teen_id}/app-controls")
async def get_teen_app_controls(teen_id: str, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    controls = await db.app_controls.find({"teen_id": teen_id}).to_list(1000)
    return [AppControl(**control) for control in controls]

# Web History Endpoints
@api_router.post("/web-history")
async def create_web_history(history_data: WebHistoryCreate):
    # Verify teen exists
    teen = await db.teens.find_one({"id": history_data.teen_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    # Check if URL already exists for today
    existing_history = await db.web_history.find_one({
        "teen_id": history_data.teen_id,
        "url": history_data.url
    })
    
    if existing_history:
        # Update visit count
        await db.web_history.update_one(
            {"id": existing_history["id"]},
            {"$inc": {"visit_count": 1}, "$set": {"timestamp": datetime.utcnow()}}
        )
        return {"status": "updated", "history_id": existing_history["id"]}
    else:
        # Create new history record
        history = WebHistory(**history_data.dict())
        await db.web_history.insert_one(history.dict())
        return {"status": "created", "history_id": history.id}

@api_router.get("/teens/{teen_id}/web-history")
async def get_teen_web_history(teen_id: str, limit: int = 100, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    history = await db.web_history.find({"teen_id": teen_id}).sort("timestamp", -1).limit(limit).to_list(limit)
    return [WebHistory(**hist) for hist in history]

# Alerts Endpoints
@api_router.get("/alerts")
async def get_alerts(parent_id: str = Depends(get_current_parent), unread_only: bool = False):
    query = {"parent_id": parent_id}
    if unread_only:
        query["is_read"] = False
    
    alerts = await db.alerts.find(query).sort("created_at", -1).to_list(100)
    return [Alert(**alert) for alert in alerts]

@api_router.put("/alerts/{alert_id}/read")
async def mark_alert_read(alert_id: str, parent_id: str = Depends(get_current_parent)):
    result = await db.alerts.update_one(
        {"id": alert_id, "parent_id": parent_id},
        {"$set": {"is_read": True}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success"}

# Dashboard Analytics
@api_router.get("/dashboard/{teen_id}")
async def get_dashboard_data(teen_id: str, parent_id: str = Depends(get_current_parent)):
    # Verify teen belongs to parent
    teen = await db.teens.find_one({"id": teen_id, "parent_id": parent_id})
    if not teen:
        raise HTTPException(status_code=404, detail="Teen not found")
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Get today's app usage
    app_usage = await db.app_usage.find({"teen_id": teen_id, "date": today}).to_list(1000)
    total_screen_time = sum(usage["usage_time"] for usage in app_usage)
    
    # Get recent locations
    recent_locations = await db.locations.find({"teen_id": teen_id}).sort("timestamp", -1).limit(10).to_list(10)
    
    # Get recent web history
    recent_web_history = await db.web_history.find({"teen_id": teen_id}).sort("timestamp", -1).limit(20).to_list(20)
    
    # Get active geofences
    geofences = await db.geofences.find({"teen_id": teen_id}).to_list(100)
    
    # Get unread alerts
    unread_alerts = await db.alerts.find({"parent_id": parent_id, "teen_id": teen_id, "is_read": False}).to_list(100)
    
    return {
        "teen": Teen(**teen),
        "screen_time_today": total_screen_time,
        "app_usage_today": [AppUsage(**usage) for usage in app_usage],
        "recent_locations": [Location(**loc) for loc in recent_locations],
        "recent_web_history": [WebHistory(**hist) for hist in recent_web_history],
        "geofences": [Geofence(**geofence) for geofence in geofences],
        "unread_alerts": [Alert(**alert) for alert in unread_alerts]
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws/{parent_id}")
async def websocket_endpoint(websocket: WebSocket, parent_id: str):
    await manager.connect(websocket, parent_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(parent_id)

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()