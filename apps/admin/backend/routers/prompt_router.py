from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List, Dict, Optional
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.config.database import get_db
# from apps.bot.services.gpt_service import GPTService  # Temporarily disabled due to import issues
from apps.bot.services.greeting_service import GreetingService
# Import shared models directly
from shared.models.settings import Settings
from shared.models.prompt_history import PromptHistory
from sqlalchemy import select, desc

router = APIRouter()


class PromptHistoryItem(BaseModel):
    id: int
    prompt: str
    changed_at: str
    changed_by: Optional[str] = None
    is_current: bool = False


async def get_setting(db: AsyncSession, key: str, default_value=None):
    """Simple helper to get settings from database"""
    from sqlalchemy import select
    
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()
    
    if not setting:
        return default_value
    
    # Return the appropriate value based on type
    if setting.string_value is not None:
        return setting.string_value
    elif setting.integer_value is not None:
        return setting.integer_value
    elif setting.boolean_value is not None:
        return setting.boolean_value
    elif setting.json_value is not None:
        return setting.json_value
    
    return default_value


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
    await db.commit()
    
    return new_prompt


class PromptTestRequest(BaseModel):
    prompt: str
    test_message: str
    user_profile: Optional[Dict] = None
    model: str = "gpt-4"
    temperature: float = 0.8
    max_tokens: int = 800


class PromptTestResponse(BaseModel):
    response: str
    token_count: int
    blocks: List[str]
    is_crisis: bool
    processing_time: float
    error: Optional[str] = None


@router.post("/test", response_model=PromptTestResponse)
async def test_prompt(
    request: PromptTestRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test a system prompt with a sample user message"""
    
    import time
    start_time = time.time()
    
    try:
        # Direct OpenAI call for prompt testing
        from openai import AsyncOpenAI
        from shared.config.settings import settings as app_settings
        
        client = AsyncOpenAI(api_key=app_settings.openai_api_key)
        
        # Test the prompt directly
        response = await client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": request.prompt},
                {"role": "user", "content": request.test_message}
            ],
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        result_text = response.choices[0].message.content.strip()
        token_count = response.usage.total_tokens if response.usage else 0
        
        # Simple crisis detection
        crisis_keywords = ["не хочу жить", "покончить", "суицид", "убить себя", "бессмысленно"]
        is_crisis = any(keyword in request.test_message.lower() for keyword in crisis_keywords)
        
        # Split into blocks (simple implementation)
        blocks = [block.strip() for block in result_text.split('\n\n') if block.strip()]
        
        result = {
            'response': result_text,
            'token_count': token_count,
            'blocks': blocks,
            'is_crisis': is_crisis
        }
        
        processing_time = time.time() - start_time
        
        return PromptTestResponse(
            response=result.get('response', ''),
            token_count=result.get('token_count', 0),
            blocks=result.get('blocks', []),
            is_crisis=result.get('is_crisis', False),
            processing_time=round(processing_time, 2),
            error=result.get('error')
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        return PromptTestResponse(
            response="",
            token_count=0,
            blocks=[],
            is_crisis=False,
            processing_time=round(processing_time, 2),
            error=str(e)
        )


@router.get("/examples")
async def get_test_examples():
    """Get example test messages for prompt testing"""
    
    return {
        "examples": [
            {
                "category": "Тревога",
                "message": "Я постоянно беспокоюсь о работе, не могу заснуть",
                "user_profile": {
                    "name": "Анна",
                    "age": 28,
                    "emotion_tags": ["😰 тревога", "😞 усталость"],
                    "topic_tags": ["💼 работа", "😴 сон"]
                }
            },
            {
                "category": "Отношения",
                "message": "Поссорился с девушкой, не знаю как помириться",
                "user_profile": {
                    "name": "Дмитрий",
                    "age": 25,
                    "emotion_tags": ["😔 грусть", "😟 беспокойство"],
                    "topic_tags": ["❤️ отношения"]
                }
            },
            {
                "category": "Семья",
                "message": "Родители не понимают меня, постоянные конфликты дома",
                "user_profile": {
                    "name": "Мария",
                    "age": 19,
                    "emotion_tags": ["😤 раздражение", "😥 чувство вины"],
                    "topic_tags": ["👨‍👩‍👧 семья"]
                }
            },
            {
                "category": "Кризисная ситуация (ТЕСТ)",
                "message": "Мне так плохо, не хочу жить, все бессмысленно",
                "user_profile": {
                    "name": "Тестовый пользователь",
                    "age": 30,
                    "emotion_tags": ["😔 грусть", "😓 беспомощность"],
                    "topic_tags": ["🏥 здоровье"]
                }
            },
            {
                "category": "Обычная беседа",
                "message": "Привет! Как дела? Хочу поговорить",
                "user_profile": {
                    "name": "Алексей",
                    "age": 32,
                    "emotion_tags": ["😊 радость"],
                    "topic_tags": ["💬 общение"]
                }
            }
        ]
    }


@router.get("/current")
async def get_current_prompt(db: AsyncSession = Depends(get_db)):
    """Get current system prompt from settings"""
    
    current_prompt = await get_setting(
        db,
        "system_prompt",
        "Default prompt not found"
    )
    
    return {
        "prompt": current_prompt,
        "model": await get_setting(db, "gpt_model", "gpt-4"),
        "temperature": await get_setting(db, "gpt_temperature", 0.8),
        "max_tokens": await get_setting(db, "gpt_max_tokens", 800)
    }


class GreetingTestRequest(BaseModel):
    user_profile: Dict
    scenario: str = "first_time"
    time_of_day: Optional[str] = None


class GreetingTestResponse(BaseModel):
    greeting: str
    scenario: str
    processing_time: float
    fallback_used: bool
    error: Optional[str] = None


@router.post("/test-greeting", response_model=GreetingTestResponse)
async def test_greeting(
    request: GreetingTestRequest,
    db: AsyncSession = Depends(get_db)
):
    """Test greeting generation with different scenarios"""
    
    import time
    start_time = time.time()
    
    try:
        greeting_service = GreetingService()
        
        greeting = await greeting_service.generate_greeting(
            request.user_profile,
            request.scenario,
            request.time_of_day
        )
        
        processing_time = time.time() - start_time
        
        # Check if it's a fallback (simple heuristic)
        fallback_used = "😊" in greeting or "🌸" in greeting or len(greeting) < 50
        
        return GreetingTestResponse(
            greeting=greeting,
            scenario=request.scenario,
            processing_time=round(processing_time, 2),
            fallback_used=fallback_used
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        return GreetingTestResponse(
            greeting="",
            scenario=request.scenario,
            processing_time=round(processing_time, 2),
            fallback_used=True,
            error=str(e)
        )


@router.get("/greeting-scenarios")
async def get_greeting_scenarios():
    """Get available greeting scenarios for testing"""
    
    return {
        "scenarios": [
            {
                "key": "first_time",
                "name": "Первое знакомство",
                "description": "Пользователь впервые заходит в бота"
            },
            {
                "key": "return_user",
                "name": "Возвращающийся пользователь",
                "description": "Пользователь заходит после перерыва"
            },
            {
                "key": "onboarding_complete",
                "name": "Завершение анкеты", 
                "description": "Пользователь завершил заполнение анкеты"
            },
            {
                "key": "daily_return",
                "name": "Обычный заход",
                "description": "Пользователь заходит как обычно"
            }
        ],
        "times_of_day": [
            {"key": "morning", "name": "Утром", "hours": "6-12"},
            {"key": "afternoon", "name": "Днем", "hours": "12-18"},
            {"key": "evening", "name": "Вечером", "hours": "18-23"},
            {"key": "night", "name": "Ночью", "hours": "23-6"}
        ]
    }


@router.post("/generate-multiple-greetings")
async def generate_multiple_greetings(
    request: GreetingTestRequest,
    count: int = 3,
    db: AsyncSession = Depends(get_db)
):
    """Generate multiple greeting variations"""
    
    try:
        greeting_service = GreetingService()
        
        greetings = await greeting_service.generate_multiple_greetings(
            request.user_profile,
            count
        )
        
        return {
            "greetings": greetings,
            "user_profile": request.user_profile,
            "count": len(greetings)
        }
        
    except Exception as e:
        return {
            "greetings": [],
            "user_profile": request.user_profile,
            "count": 0,
            "error": str(e)
        }


@router.get("/history")
async def get_prompt_history(db: AsyncSession = Depends(get_db)):
    """Get recent prompt history (last 10 changes)"""
    
    try:
        result = await db.execute(
            select(PromptHistory)
            .where(PromptHistory.prompt_type == "system_prompt")
            .order_by(desc(PromptHistory.changed_at))
            .limit(10)
        )
        prompts = result.scalars().all()
        
        history = []
        for i, prompt in enumerate(prompts):
            history.append({
                "id": prompt.id,
                "prompt": prompt.prompt_text,
                "version": prompt.version,
                "description": prompt.description,
                "changed_at": prompt.changed_at.isoformat() if prompt.changed_at else "",
                "changed_by": prompt.changed_by or "system",
                "is_current": prompt.is_active == "active"
            })
        
        return {"history": history}
        
    except Exception as e:
        return {"history": [], "error": str(e)}


@router.post("/restore/{prompt_id}")
async def restore_prompt_from_history(
    prompt_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Restore a prompt from history"""
    
    try:
        # Get the historical prompt
        result = await db.execute(
            select(PromptHistory).where(PromptHistory.id == prompt_id)
        )
        historical_prompt = result.scalar_one_or_none()
        
        if not historical_prompt:
            raise HTTPException(status_code=404, detail="Historical prompt not found")
        
        # Update settings table with this prompt
        current_result = await db.execute(
            select(Settings)
            .where(Settings.key == "system_prompt")
            .limit(1)
        )
        current_setting = current_result.scalar_one_or_none()
        
        if current_setting:
            # Save current prompt to history before changing
            await save_prompt_to_history(
                db, 
                current_setting.string_value or "", 
                "admin (backup before restore)",
                f"Auto-backup before restoring to version {historical_prompt.version}"
            )
            
            # Update current setting
            current_setting.string_value = historical_prompt.prompt_text
            current_setting.changed_by = f"admin (restored from v{historical_prompt.version})"
            
            # Mark all existing prompts as inactive
            existing_active = await db.execute(
                select(PromptHistory).where(PromptHistory.is_active == "active")
            )
            for prompt in existing_active.scalars():
                prompt.is_active = "inactive"
            
            # Mark the restored prompt as active
            historical_prompt.is_active = "active"
            
            await db.commit()
            
            return {
                "success": True,
                "message": f"Prompt restored from version {historical_prompt.version} ({historical_prompt.changed_at.strftime('%Y-%m-%d %H:%M:%S') if historical_prompt.changed_at else 'unknown date'})",
                "prompt": historical_prompt.prompt_text,
                "version": historical_prompt.version
            }
        else:
            raise HTTPException(status_code=404, detail="Current prompt setting not found")
            
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error restoring prompt: {str(e)}")


class SavePromptRequest(BaseModel):
    prompt: str
    description: Optional[str] = None
    changed_by: str = "admin"


@router.post("/save")
async def save_new_prompt(
    request: SavePromptRequest,
    db: AsyncSession = Depends(get_db)
):
    """Save a new prompt to history and update current setting"""
    
    try:
        # Save to history
        new_prompt = await save_prompt_to_history(
            db, 
            request.prompt, 
            request.changed_by,
            request.description
        )
        
        # Update current setting
        current_result = await db.execute(
            select(Settings)
            .where(Settings.key == "system_prompt")
            .limit(1)
        )
        current_setting = current_result.scalar_one_or_none()
        
        if current_setting:
            current_setting.string_value = request.prompt
            current_setting.changed_by = request.changed_by
            current_setting.changed_at = new_prompt.changed_at
        else:
            # Create new setting if it doesn't exist
            current_setting = Settings(
                key="system_prompt",
                category="frequent",
                string_value=request.prompt,
                description="AI chatbot system prompt",
                is_active=True,
                changed_by=request.changed_by
            )
            db.add(current_setting)
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Prompt saved as version {new_prompt.version}",
            "version": new_prompt.version,
            "prompt": new_prompt.prompt_text
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error saving prompt: {str(e)}")


@router.delete("/history/{prompt_id}")
async def delete_prompt_from_history(
    prompt_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete a prompt from history (archive it)"""
    
    try:
        result = await db.execute(
            select(PromptHistory).where(PromptHistory.id == prompt_id)
        )
        prompt = result.scalar_one_or_none()
        
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")
        
        if prompt.is_active == "active":
            raise HTTPException(status_code=400, detail="Cannot delete active prompt")
        
        prompt.is_active = "archived"
        await db.commit()
        
        return {
            "success": True,
            "message": f"Prompt version {prompt.version} archived"
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error archiving prompt: {str(e)}")