from pydantic import BaseModel


class DashboardStatsRes(BaseModel):
    """首页统计数据响应"""
    total_users: int = 0  # 总用户数
    total_products: int = 0  # 总商品数
    total_designs: int = 0  # 总设计作品数
    total_orders: int = 0  # 总订单数
    today_users: int = 0  # 今日新增用户数
    today_orders: int = 0  # 今日订单数
    today_revenue: float = 0.0  # 今日收入
    pending_designs: int = 0  # 待审核设计作品数

