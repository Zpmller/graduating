"""
告警服务：告警相关的业务逻辑
"""
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert, AlertType, AlertSeverity


class AlertService:
    """告警服务"""
    
    @staticmethod
    async def get_alerts(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        device_id: Optional[int] = None,
        alert_type: Optional[AlertType] = None,
        severity: Optional[AlertSeverity] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        is_acknowledged: Optional[bool] = None,
    ) -> tuple[list[Alert], int]:
        """
        获取告警列表
        
        Returns:
            (告警列表, 总数)
        """
        # 构建查询
        query = select(Alert)
        count_query = select(func.count(Alert.id))
        
        # 应用过滤条件
        conditions = []
        if device_id:
            conditions.append(Alert.device_id == device_id)
        if alert_type:
            conditions.append(Alert.type == alert_type)
        if severity:
            conditions.append(Alert.severity == severity)
        if start_date:
            conditions.append(Alert.timestamp >= start_date)
        if end_date:
            conditions.append(Alert.timestamp <= end_date)
        if is_acknowledged is not None:
            conditions.append(Alert.is_acknowledged == is_acknowledged)
        
        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))
        
        # 排序：最新的在前
        query = query.order_by(Alert.timestamp.desc())
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        # 执行查询
        result = await db.execute(query)
        alerts = result.scalars().all()
        
        count_result = await db.execute(count_query)
        total = count_result.scalar()
        
        return list(alerts), total
    
    @staticmethod
    async def get_alert_stats(
        db: AsyncSession,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        device_id: Optional[int] = None,
    ) -> dict:
        """
        获取告警统计信息
        
        Returns:
            统计字典
        """
        # 默认时间范围：最近24小时
        if end_date is None:
            end_date = datetime.utcnow()
        if start_date is None:
            start_date = end_date - timedelta(hours=24)
        
        # 构建基础查询条件
        conditions = [
            Alert.timestamp >= start_date,
            Alert.timestamp <= end_date,
        ]
        if device_id:
            conditions.append(Alert.device_id == device_id)
        
        base_query = select(Alert).where(and_(*conditions))
        
        # 总数
        total_query = select(func.count(Alert.id)).where(and_(*conditions))
        total_result = await db.execute(total_query)
        total_alerts = total_result.scalar() or 0
        
        # 按类型统计
        type_query = select(
            Alert.type,
            func.count(Alert.id).label("count")
        ).where(and_(*conditions)).group_by(Alert.type)
        type_result = await db.execute(type_query)
        by_type = {row.type.value: row.count for row in type_result}
        
        # 按严重程度统计
        severity_query = select(
            Alert.severity,
            func.count(Alert.id).label("count")
        ).where(and_(*conditions)).group_by(Alert.severity)
        severity_result = await db.execute(severity_query)
        by_severity = {row.severity.value: row.count for row in severity_result}
        
        # 未确认数量
        unack_query = select(func.count(Alert.id)).where(
            and_(*conditions, Alert.is_acknowledged == False)
        )
        unack_result = await db.execute(unack_query)
        unacknowledged_count = unack_result.scalar() or 0
        
        # 24小时趋势（按小时分组）
        trend_query = select(
            func.date_format(Alert.timestamp, "%H:00").label("hour"),
            func.count(Alert.id).label("count")
        ).where(and_(*conditions)).group_by("hour").order_by("hour")
        trend_result = await db.execute(trend_query)
        trend_24h = [{"hour": row.hour, "count": row.count} for row in trend_result]
        
        return {
            "total_alerts": total_alerts,
            "by_type": by_type,
            "by_severity": by_severity,
            "unacknowledged_count": unacknowledged_count,
            "trend_24h": trend_24h,
        }


alert_service = AlertService()
