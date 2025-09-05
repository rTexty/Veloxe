from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Any, Optional
from datetime import datetime
import sys
import os
import json
import redis.asyncio as redis

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.config.database import get_db
from shared.models.settings import Settings
from shared.models.prompt_history import PromptHistory
from sqlalchemy import desc

# Import AI service for ping testing
try:
    from apps.bot.services.ping_ai_service import PingAIService
except ImportError:
    PingAIService = None

router = APIRouter()

async def save_prompt_to_history(db: AsyncSession, prompt_text: str, changed_by: str = "admin", description: str = None):
    """Save a prompt to history table"""
    
    # Mark all existing prompts as inactive
    existing_active = await db.execute(
        select(PromptHistory).where(PromptHistory.is_active == "active")
    )
    for prompt in existing_active.scalars():
        prompt.is_active = "inactive"
    
    # Get next version number
    version_result = await db.execute(
        select(PromptHistory)
        .order_by(desc(PromptHistory.version))
        .limit(1)
    )
    last_prompt = version_result.scalar_one_or_none()
    next_version = (last_prompt.version + 1) if last_prompt else 1
    
    # Create new history entry
    new_prompt = PromptHistory(
        prompt_text=prompt_text,
        prompt_type="system_prompt",
        version=next_version,
        description=description,
        changed_by=changed_by,
        is_active="active"
    )
    
    db.add(new_prompt)
    
    return new_prompt

async def invalidate_settings_cache(key: str, value: Any):
    try:
        redis_client = redis.from_url("redis://localhost:6379", decode_responses=True)
        # Invalidate the bot settings cache
        await redis_client.delete("bot_settings_cache")
        # Also publish to pubsub for any other listeners
        await redis_client.publish("settings_update", json.dumps({"key": key, "value": value}))
        await redis_client.close()
    except:
        pass


class SettingResponse(BaseModel):
    id: int
    key: str
    category: str
    string_value: Optional[str] = None
    integer_value: Optional[int] = None
    boolean_value: Optional[bool] = None
    json_value: Optional[Any] = None
    description: Optional[str] = None
    is_active: bool
    changed_by: Optional[str] = None
    changed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: Any
    changed_by: str = "admin"


class SettingCreate(BaseModel):
    key: str
    category: str
    value: Any
    description: Optional[str] = None
    changed_by: str = "admin"


@router.get("", response_model=List[SettingResponse])
@router.get("/", response_model=List[SettingResponse])
async def get_all_settings(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all settings, optionally filtered by category"""
    
    query = select(Settings).where(Settings.is_active == True)
    
    if category:
        query = query.where(Settings.category == category)
    
    query = query.order_by(Settings.category, Settings.key)
    
    result = await db.execute(query)
    settings = result.scalars().all()
    
    return [SettingResponse.model_validate(setting) for setting in settings]


@router.get("/categories")
async def get_setting_categories(db: AsyncSession = Depends(get_db)):
    """Get all setting categories"""
    
    result = await db.execute(
        select(Settings.category).distinct().where(Settings.is_active == True)
    )
    categories = result.scalars().all()
    
    return {"categories": categories}


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Get specific setting by key"""
    
    result = await db.execute(
        select(Settings).where(Settings.key == key, Settings.is_active == True)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    # Debug: log what we're returning
    print(f"DEBUG GET: {key} - boolean_value: {setting.boolean_value}, string_value: {setting.string_value}")
    
    return SettingResponse.model_validate(setting)


@router.put("/{key}")
async def update_setting(
    key: str,
    setting_update: SettingUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update existing setting"""
    
    result = await db.execute(
        select(Settings).where(Settings.key == key, Settings.is_active == True)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    # Debug: log received value
    print(f"DEBUG: Updating {key} with value: {setting_update.value} (type: {type(setting_update.value)})")
    
    # Clear all value fields first
    setting.string_value = None
    setting.integer_value = None
    setting.boolean_value = None
    setting.json_value = None
    
    # Set appropriate value field based on type
    # IMPORTANT: Check bool BEFORE int because bool is subclass of int in Python
    value = setting_update.value
    if isinstance(value, bool):  # Must check bool first!
        setting.boolean_value = value
        print(f"DEBUG: Set boolean_value = {value}")
    elif isinstance(value, str):
        setting.string_value = value
        print(f"DEBUG: Set string_value = {value}")
    elif isinstance(value, int):
        setting.integer_value = value
        print(f"DEBUG: Set integer_value = {value}")
    else:
        setting.json_value = value
        print(f"DEBUG: Set json_value = {value}")
    
    setting.changed_by = setting_update.changed_by
    setting.changed_at = datetime.utcnow()
    
    # If this is a system_prompt update, also save to history
    if key == "system_prompt" and isinstance(value, str):
        await save_prompt_to_history(
            db, 
            value, 
            setting_update.changed_by,
            f"Updated via admin panel"
        )
    
    await db.commit()
    await db.refresh(setting)
    
    # Debug: log final state
    print(f"DEBUG: After commit - boolean_value: {setting.boolean_value}, string_value: {setting.string_value}")
    
    # Invalidate cache globally
    await invalidate_settings_cache(key, setting_update.value)
    
    return {"message": "Setting updated successfully", "key": key}


@router.post("")
@router.post("/")
async def create_setting(
    setting_create: SettingCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create new setting"""
    
    # Check if setting already exists
    result = await db.execute(
        select(Settings).where(Settings.key == setting_create.key)
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=400, detail="Setting already exists")
    
    # Create new setting
    setting = Settings(
        key=setting_create.key,
        category=setting_create.category,
        description=setting_create.description,
        changed_by=setting_create.changed_by,
        changed_at=datetime.utcnow()
    )
    
    # Set appropriate value field
    # IMPORTANT: Check bool BEFORE int because bool is subclass of int in Python
    value = setting_create.value
    if isinstance(value, bool):  # Must check bool first!
        setting.boolean_value = value
    elif isinstance(value, str):
        setting.string_value = value
    elif isinstance(value, int):
        setting.integer_value = value
    else:
        setting.json_value = value
    
    db.add(setting)
    await db.commit()
    await db.refresh(setting)
    
    return {"message": "Setting created successfully", "id": setting.id}


@router.post("/{key}/preview")
async def preview_setting_template(
    key: str, 
    preview_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Preview template with variable substitution"""
    
    result = await db.execute(
        select(Settings).where(Settings.key == key, Settings.is_active == True)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    # Get template value
    template = None
    if setting.string_value:
        template = setting.string_value
    elif setting.json_value and isinstance(setting.json_value, str):
        template = setting.json_value
    
    if not template:
        return {"preview": "No template content found"}
    
    # Apply variable substitutions
    preview_text = template
    for var_name, var_value in preview_data.items():
        placeholder = "{" + var_name + "}"
        preview_text = preview_text.replace(placeholder, str(var_value))
    
    return {"preview": preview_text, "variables_used": list(preview_data.keys())}


class PingAITestRequest(BaseModel):
    system_prompt: str
    test_level: int = 1


@router.post("/ping_ai_test")
async def test_ping_ai_generation(request: PingAITestRequest, db: AsyncSession = Depends(get_db)):
    """Test AI ping generation with the given system prompt"""
    
    if not PingAIService:
        raise HTTPException(status_code=501, detail="AI service not available")
    
    try:
        ping_ai_service = PingAIService()
        generated_text = await ping_ai_service.test_generation(
            system_prompt=request.system_prompt,
            test_level=request.test_level
        )
        
        return {
            "generated_text": generated_text,
            "test_level": request.test_level,
            "system_prompt_length": len(request.system_prompt)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate AI ping: {str(e)}")


@router.delete("/{key}")
async def delete_setting(key: str, db: AsyncSession = Depends(get_db)):
    """Soft delete setting (mark as inactive)"""
    
    result = await db.execute(
        select(Settings).where(Settings.key == key, Settings.is_active == True)
    )
    setting = result.scalar_one_or_none()
    
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    
    setting.is_active = False
    setting.changed_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Setting deleted successfully"}