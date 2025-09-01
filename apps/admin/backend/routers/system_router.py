from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from datetime import datetime
import psutil
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))

from shared.config.settings import settings

router = APIRouter()


class SystemStatsResponse(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    uptime_hours: float


class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str
    api_version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """System health check"""
    
    # Basic health check - in production you'd check database connectivity
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        database="postgresql://connected",
        api_version="1.0.0"
    )


@router.get("/stats", response_model=SystemStatsResponse)
async def get_system_stats():
    """Get system resource statistics"""
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Memory usage
    memory = psutil.virtual_memory()
    memory_used_mb = memory.used / (1024 * 1024)
    memory_total_mb = memory.total / (1024 * 1024)
    
    # Disk usage
    disk = psutil.disk_usage('/')
    disk_used_gb = disk.used / (1024 * 1024 * 1024)
    disk_total_gb = disk.total / (1024 * 1024 * 1024)
    
    # System uptime
    boot_time = psutil.boot_time()
    uptime_hours = (datetime.utcnow().timestamp() - boot_time) / 3600
    
    return SystemStatsResponse(
        cpu_percent=round(cpu_percent, 2),
        memory_percent=round(memory.percent, 2),
        memory_used_mb=round(memory_used_mb, 2),
        memory_total_mb=round(memory_total_mb, 2),
        disk_percent=round(disk.percent, 2),
        disk_used_gb=round(disk_used_gb, 2),
        disk_total_gb=round(disk_total_gb, 2),
        uptime_hours=round(uptime_hours, 2)
    )


@router.get("/logs")
async def get_recent_logs():
    """Get recent system logs (placeholder)"""
    
    # In production, this would read actual log files
    return {
        "logs": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "message": "System running normally",
                "service": "admin-api"
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=5)).isoformat(),
                "level": "INFO", 
                "message": "User authentication successful",
                "service": "admin-api"
            }
        ]
    }


from datetime import timedelta