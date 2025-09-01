from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.config.database import get_db
from shared.models.user import User
from shared.models.subscription import Subscription
from shared.models.analytics import Event

router = APIRouter()


class UserResponse(BaseModel):
    id: int
    telegram_id: str
    name: Optional[str]
    age: Optional[int]
    gender: Optional[str]
    city: Optional[str]
    timezone: Optional[str]
    terms_accepted: bool
    is_active: bool
    is_in_crisis: bool
    created_at: datetime
    
    # Subscription info
    subscription_active: bool = False
    subscription_plan: Optional[str] = None
    subscription_ends_at: Optional[datetime] = None
    daily_messages_used: int = 0
    daily_messages_limit: int = 5

    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    total_users: int
    active_users_today: int
    active_users_week: int
    subscribers: int
    crisis_users: int
    new_users_today: int


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(db: AsyncSession = Depends(get_db)):
    """Get user statistics"""
    
    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    # Total users
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar()
    
    # New users today
    new_today_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today)
    )
    new_users_today = new_today_result.scalar()
    
    # Active users (users with events today)
    active_today_result = await db.execute(
        select(func.count(func.distinct(Event.user_id)))
        .where(Event.created_at >= today)
    )
    active_users_today = active_today_result.scalar()
    
    # Active users this week
    active_week_result = await db.execute(
        select(func.count(func.distinct(Event.user_id)))
        .where(Event.created_at >= week_ago)
    )
    active_users_week = active_week_result.scalar()
    
    # Subscribers (active subscriptions)
    subscribers_result = await db.execute(
        select(func.count(Subscription.id))
        .where(
            and_(
                Subscription.is_active == True,
                Subscription.ends_at > now
            )
        )
    )
    subscribers = subscribers_result.scalar()
    
    # Crisis users
    crisis_result = await db.execute(
        select(func.count(User.id)).where(User.is_in_crisis == True)
    )
    crisis_users = crisis_result.scalar()
    
    return UserStatsResponse(
        total_users=total_users,
        active_users_today=active_users_today,
        active_users_week=active_users_week,
        subscribers=subscribers,
        crisis_users=crisis_users,
        new_users_today=new_users_today
    )


@router.get("/", response_model=List[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Get paginated list of users"""
    
    # Get users first, then we'll get their latest subscription separately
    query = select(User)
    
    if active_only:
        query = query.where(User.is_active == True)
    
    if search:
        query = query.where(
            func.or_(
                User.name.ilike(f"%{search}%"),
                User.telegram_id.ilike(f"%{search}%"),
                User.city.ilike(f"%{search}%")
            )
        )
    
    query = query.order_by(desc(User.created_at))
    query = query.offset((page - 1) * size).limit(size)
    
    result = await db.execute(query)
    user_list = result.scalars().all()
    
    users = []
    for user in user_list:
        user_response = UserResponse.model_validate(user)
        
        # Get latest subscription for this user (matching bot logic)
        subscription_result = await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user.id)
            .order_by(desc(Subscription.created_at))
        )
        subscription = subscription_result.scalar_one_or_none()
        
        if subscription:
            user_response.subscription_active = subscription.is_active and subscription.ends_at > datetime.utcnow()
            user_response.subscription_plan = subscription.plan_name
            user_response.subscription_ends_at = subscription.ends_at
            user_response.daily_messages_used = subscription.daily_messages_used
            user_response.daily_messages_limit = subscription.daily_messages_limit
        
        users.append(user_response)
    
    return users


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Get specific user details"""
    
    # Get latest subscription (active or inactive) to match bot logic
    result = await db.execute(
        select(User, Subscription)
        .outerjoin(Subscription, Subscription.user_id == User.id)
        .where(User.id == user_id)
        .order_by(desc(Subscription.created_at))
        .limit(1)
    )
    
    user_data = result.first()
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user, subscription = user_data
    user_response = UserResponse.model_validate(user)
    
    if subscription:
        user_response.subscription_active = subscription.is_active and subscription.ends_at > datetime.utcnow()
        user_response.subscription_plan = subscription.plan_name
        user_response.subscription_ends_at = subscription.ends_at
        user_response.daily_messages_used = subscription.daily_messages_used
        user_response.daily_messages_limit = subscription.daily_messages_limit
    
    return user_response


@router.put("/{user_id}/crisis")
async def toggle_crisis_mode(user_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle user crisis mode"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_in_crisis = not user.is_in_crisis
    if not user.is_in_crisis:
        user.crisis_freeze_until = None
    
    await db.commit()
    
    return {
        "message": f"Crisis mode {'enabled' if user.is_in_crisis else 'disabled'}",
        "crisis_mode": user.is_in_crisis
    }


@router.put("/{user_id}/activate")
async def toggle_user_active(user_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle user active status"""
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = not user.is_active
    
    await db.commit()
    
    return {
        "message": f"User {'activated' if user.is_active else 'deactivated'}",
        "is_active": user.is_active
    }


@router.patch("/{user_id}/subscription")
async def toggle_user_subscription(user_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle user subscription status"""
    
    result = await db.execute(
        select(User, Subscription).outerjoin(
            Subscription,
            and_(
                Subscription.user_id == User.id,
                Subscription.is_active == True
            )
        ).where(User.id == user_id)
    )
    
    user_data = result.first()
    
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user, subscription = user_data
    
    if subscription:
        # Deactivate existing subscription
        subscription.is_active = False
        message = "Subscription deactivated"
        active = False
    else:
        # Create or activate subscription
        existing_sub = await db.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        existing = existing_sub.scalar_one_or_none()
        
        if existing:
            existing.is_active = True
            from datetime import timedelta
            existing.ends_at = datetime.utcnow() + timedelta(days=30)
        else:
            new_subscription = Subscription(
                user_id=user_id,
                plan_name="Premium",
                is_active=True,
                ends_at=datetime.utcnow() + timedelta(days=30),
                daily_messages_limit=50
            )
            db.add(new_subscription)
        
        message = "Subscription activated"
        active = True
    
    await db.commit()
    
    return {
        "message": message,
        "subscription_active": active
    }