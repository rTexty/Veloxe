from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.config.database import get_db
from shared.models.analytics import Event
from shared.models.user import User
from shared.models.subscription import Subscription

router = APIRouter()


@router.get("/")
async def get_analytics_overview(db: AsyncSession = Depends(get_db)):
    """Get overview analytics for the dashboard"""
    
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar()
    
    # Active subscriptions
    active_subs_result = await db.execute(
        select(func.count(Subscription.id)).where(Subscription.is_active == True)
    )
    active_subscriptions = active_subs_result.scalar()
    
    # Messages today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    messages_today_result = await db.execute(
        select(func.count(Event.id))
        .where(and_(
            Event.created_at >= today_start,
            Event.event_type == 'message_sent'
        ))
    )
    messages_today = messages_today_result.scalar()
    
    # Messages this week
    week_start = today_start - timedelta(days=7)
    messages_week_result = await db.execute(
        select(func.count(Event.id))
        .where(and_(
            Event.created_at >= week_start,
            Event.event_type == 'message_sent'
        ))
    )
    messages_this_week = messages_week_result.scalar()
    
    # Messages this month
    month_start = today_start - timedelta(days=30)
    messages_month_result = await db.execute(
        select(func.count(Event.id))
        .where(and_(
            Event.created_at >= month_start,
            Event.event_type == 'message_sent'
        ))
    )
    messages_this_month = messages_month_result.scalar()
    
    # Revenue this month (placeholder)
    revenue_this_month = active_subscriptions * 99  # Assuming 99 rubles per subscription
    
    # New users today
    new_users_today_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    new_users_today = new_users_today_result.scalar()
    
    # New users this week
    new_users_week_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )
    new_users_this_week = new_users_week_result.scalar()
    
    # Crisis interventions
    crisis_result = await db.execute(
        select(func.count(Event.id))
        .where(Event.event_type == 'crisis_triggered')
    )
    crisis_interventions = crisis_result.scalar()
    
    # Memory anchors created
    memory_result = await db.execute(
        select(func.count(Event.id))
        .where(Event.event_type == 'memory_anchor_created')
    )
    memory_anchors_created = memory_result.scalar()
    
    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "messages_today": messages_today,
        "messages_this_week": messages_this_week,
        "messages_this_month": messages_this_month,
        "revenue_this_month": revenue_this_month,
        "new_users_today": new_users_today,
        "new_users_this_week": new_users_this_week,
        "crisis_interventions": crisis_interventions,
        "memory_anchors_created": memory_anchors_created
    }


class EventStatsResponse(BaseModel):
    event_type: str
    count: int
    percentage: float


class DailyStatsResponse(BaseModel):
    date: str
    new_users: int
    active_users: int
    messages_sent: int
    subscriptions: int


class ConversionStatsResponse(BaseModel):
    paywall_shown: int
    payment_attempts: int
    payment_success: int
    conversion_rate: float


@router.get("/events", response_model=List[EventStatsResponse])
async def get_event_stats(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get event statistics for the last N days"""
    
    since = datetime.utcnow() - timedelta(days=days)
    
    result = await db.execute(
        select(Event.event_type, func.count(Event.id).label('count'))
        .where(Event.created_at >= since)
        .group_by(Event.event_type)
        .order_by(desc('count'))
    )
    
    events_data = result.all()
    total_events = sum(count for _, count in events_data)
    
    stats = []
    for event_type, count in events_data:
        percentage = (count / total_events * 100) if total_events > 0 else 0
        stats.append(EventStatsResponse(
            event_type=event_type,
            count=count,
            percentage=round(percentage, 2)
        ))
    
    return stats


@router.get("/daily", response_model=List[DailyStatsResponse])
async def get_daily_stats(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get daily statistics"""
    
    stats = []
    
    for i in range(days):
        date = datetime.utcnow() - timedelta(days=i)
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # New users
        new_users_result = await db.execute(
            select(func.count(User.id))
            .where(and_(User.created_at >= day_start, User.created_at < day_end))
        )
        new_users = new_users_result.scalar()
        
        # Active users
        active_users_result = await db.execute(
            select(func.count(func.distinct(Event.user_id)))
            .where(and_(Event.created_at >= day_start, Event.created_at < day_end))
        )
        active_users = active_users_result.scalar()
        
        # Messages sent
        messages_result = await db.execute(
            select(func.count(Event.id))
            .where(and_(
                Event.created_at >= day_start,
                Event.created_at < day_end,
                Event.event_type == 'message_out'
            ))
        )
        messages_sent = messages_result.scalar()
        
        # New subscriptions
        subscriptions_result = await db.execute(
            select(func.count(Subscription.id))
            .where(and_(
                Subscription.created_at >= day_start,
                Subscription.created_at < day_end,
                Subscription.is_active == True
            ))
        )
        subscriptions = subscriptions_result.scalar()
        
        stats.append(DailyStatsResponse(
            date=day_start.strftime('%Y-%m-%d'),
            new_users=new_users,
            active_users=active_users,
            messages_sent=messages_sent,
            subscriptions=subscriptions
        ))
    
    return list(reversed(stats))  # Most recent first


@router.get("/conversion", response_model=ConversionStatsResponse)
async def get_conversion_stats(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get conversion funnel statistics"""
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Paywall shown events
    paywall_result = await db.execute(
        select(func.count(Event.id))
        .where(and_(
            Event.created_at >= since,
            Event.event_type == 'paywall_shown'
        ))
    )
    paywall_shown = paywall_result.scalar()
    
    # Payment attempts (not implemented yet, using placeholder)
    payment_attempts = 0
    
    # Successful payments
    payment_success_result = await db.execute(
        select(func.count(Event.id))
        .where(and_(
            Event.created_at >= since,
            Event.event_type == 'payment_ok'
        ))
    )
    payment_success = payment_success_result.scalar()
    
    # Calculate conversion rate
    conversion_rate = (payment_success / paywall_shown * 100) if paywall_shown > 0 else 0
    
    return ConversionStatsResponse(
        paywall_shown=paywall_shown,
        payment_attempts=payment_attempts,
        payment_success=payment_success,
        conversion_rate=round(conversion_rate, 2)
    )


@router.get("/crisis")
async def get_crisis_stats(
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get crisis intervention statistics"""
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Crisis triggered events
    crisis_triggered_result = await db.execute(
        select(func.count(Event.id))
        .where(and_(
            Event.created_at >= since,
            Event.event_type == 'crisis_triggered'
        ))
    )
    crisis_triggered = crisis_triggered_result.scalar()
    
    # Crisis resolved events
    crisis_resolved_result = await db.execute(
        select(func.count(Event.id))
        .where(and_(
            Event.created_at >= since,
            Event.event_type == 'crisis_resolved'
        ))
    )
    crisis_resolved = crisis_resolved_result.scalar()
    
    # Currently in crisis
    current_crisis_result = await db.execute(
        select(func.count(User.id)).where(User.is_in_crisis == True)
    )
    current_crisis = current_crisis_result.scalar()
    
    return {
        "crisis_triggered": crisis_triggered,
        "crisis_resolved": crisis_resolved,
        "currently_in_crisis": current_crisis,
        "resolution_rate": round((crisis_resolved / crisis_triggered * 100) if crisis_triggered > 0 else 0, 2)
    }


@router.get("/top-emotions")
async def get_top_emotions(db: AsyncSession = Depends(get_db)):
    """Get most common user emotions"""
    
    result = await db.execute(
        select(User.emotion_tags).where(User.emotion_tags.isnot(None))
    )
    
    emotion_counts = {}
    for (emotion_tags,) in result:
        if emotion_tags:
            for emotion in emotion_tags:
                # Extract emotion name (remove emoji)
                emotion_name = emotion.split(' ', 1)[1] if ' ' in emotion else emotion
                emotion_counts[emotion_name] = emotion_counts.get(emotion_name, 0) + 1
    
    # Sort by frequency and take top 10
    top_emotions = sorted(emotion_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "emotions": [{"name": name, "count": count} for name, count in top_emotions]
    }


@router.get("/top-topics")
async def get_top_topics(db: AsyncSession = Depends(get_db)):
    """Get most common user topics"""
    
    result = await db.execute(
        select(User.topic_tags).where(User.topic_tags.isnot(None))
    )
    
    topic_counts = {}
    for (topic_tags,) in result:
        if topic_tags:
            for topic in topic_tags:
                # Extract topic name (remove emoji)
                topic_name = topic.split(' ', 1)[1] if ' ' in topic else topic
                topic_counts[topic_name] = topic_counts.get(topic_name, 0) + 1
    
    # Sort by frequency and take top 10
    top_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "topics": [{"name": name, "count": count} for name, count in top_topics]
    }