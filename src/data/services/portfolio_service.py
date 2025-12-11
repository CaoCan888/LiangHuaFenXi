# -*- coding: utf-8 -*-
"""
持仓与自选股管理服务
"""

from datetime import datetime, date
from typing import List, Optional, Dict
from contextlib import contextmanager
import logging

from src.data.storage.db_manager import get_db_manager
from src.data.models import Watchlist, Position, TradeRecord

logger = logging.getLogger(__name__)


@contextmanager
def get_session():
    """获取数据库会话的上下文管理器"""
    db = get_db_manager()
    session = db.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class PortfolioService:
    """持仓与自选股管理服务"""
    
    # ===== 自选股管理 =====
    
    def add_to_watchlist(
        self, 
        stock_code: str, 
        stock_name: str = "",
        group_name: str = "默认",
        notes: str = "",
        current_price: float = 0
    ) -> bool:
        """添加自选股"""
        try:
            with get_session() as session:
                # 检查是否已存在
                existing = session.query(Watchlist).filter(
                    Watchlist.stock_code == stock_code
                ).first()
                
                if existing:
                    logger.info(f"自选股已存在: {stock_code}")
                    return True
                
                item = Watchlist(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    group_name=group_name,
                    notes=notes,
                    added_price=current_price if current_price > 0 else None
                )
                session.add(item)
                session.commit()
                logger.info(f"添加自选股: {stock_code} {stock_name}")
                return True
        except Exception as e:
            logger.error(f"添加自选股失败: {e}")
            return False
    
    def remove_from_watchlist(self, stock_code: str) -> bool:
        """删除自选股"""
        try:
            with get_session() as session:
                session.query(Watchlist).filter(
                    Watchlist.stock_code == stock_code
                ).delete()
                session.commit()
                return True
        except Exception as e:
            logger.error(f"删除自选股失败: {e}")
            return False
    
    def get_watchlist(self, group_name: str = None) -> List[Dict]:
        """获取自选股列表"""
        try:
            with get_session() as session:
                query = session.query(Watchlist)
                if group_name:
                    query = query.filter(Watchlist.group_name == group_name)
                query = query.order_by(Watchlist.sort_order, Watchlist.added_at.desc())
                
                result = []
                for item in query.all():
                    result.append({
                        'code': item.stock_code,
                        'name': item.stock_name,
                        'group': item.group_name,
                        'notes': item.notes,
                        'added_price': item.added_price,
                        'added_at': item.added_at
                    })
                return result
        except Exception as e:
            logger.error(f"获取自选股失败: {e}")
            return []
    
    def get_watchlist_groups(self) -> List[str]:
        """获取所有自选股分组"""
        try:
            with get_session() as session:
                groups = session.query(Watchlist.group_name).distinct().all()
                return [g[0] for g in groups if g[0]]
        except Exception as e:
            logger.error(f"获取分组失败: {e}")
            return ["默认"]
    
    # ===== 持仓管理 =====
    
    def add_position(
        self,
        stock_code: str,
        stock_name: str,
        shares: int,
        avg_cost: float,
        buy_date: date = None,
        strategy_tag: str = "",
        notes: str = ""
    ) -> bool:
        """添加/更新持仓"""
        try:
            with get_session() as session:
                # 检查是否已有持仓
                pos = session.query(Position).filter(
                    Position.stock_code == stock_code,
                    Position.is_active == True
                ).first()
                
                if pos:
                    # 更新持仓 (加仓逻辑)
                    total_shares = pos.shares + shares
                    total_cost = pos.total_cost + (shares * avg_cost)
                    pos.shares = total_shares
                    pos.total_cost = total_cost
                    pos.avg_cost = total_cost / total_shares if total_shares > 0 else 0
                    pos.last_trade_date = buy_date or date.today()
                    pos.updated_at = datetime.now()
                else:
                    # 新建持仓
                    pos = Position(
                        stock_code=stock_code,
                        stock_name=stock_name,
                        shares=shares,
                        avg_cost=avg_cost,
                        total_cost=shares * avg_cost,
                        buy_date=buy_date or date.today(),
                        last_trade_date=buy_date or date.today(),
                        strategy_tag=strategy_tag,
                        notes=notes,
                        is_active=True
                    )
                    session.add(pos)
                
                session.commit()
                logger.info(f"更新持仓: {stock_code} {shares}股 @ {avg_cost}")
                return True
        except Exception as e:
            logger.error(f"添加持仓失败: {e}")
            return False
    
    def sell_position(
        self,
        stock_code: str,
        shares: int,
        sell_price: float,
        sell_date: date = None,
        reason: str = ""
    ) -> Optional[Dict]:
        """卖出持仓 (减仓/清仓)"""
        try:
            with get_session() as session:
                pos = session.query(Position).filter(
                    Position.stock_code == stock_code,
                    Position.is_active == True
                ).first()
                
                if not pos:
                    logger.warning(f"未找到持仓: {stock_code}")
                    return None
                
                if shares > pos.shares:
                    shares = pos.shares  # 最多卖出全部
                
                # 计算盈亏
                cost_per_share = pos.avg_cost
                profit = (sell_price - cost_per_share) * shares
                profit_pct = (sell_price / cost_per_share - 1) * 100 if cost_per_share > 0 else 0
                
                # 更新持仓
                pos.shares -= shares
                pos.total_cost = pos.shares * pos.avg_cost
                pos.last_trade_date = sell_date or date.today()
                
                if pos.shares <= 0:
                    pos.is_active = False
                
                # 记录交易
                trade = TradeRecord(
                    stock_code=stock_code,
                    stock_name=pos.stock_name,
                    trade_type='SELL',
                    trade_date=sell_date or date.today(),
                    trade_time=datetime.now(),
                    price=sell_price,
                    shares=shares,
                    amount=sell_price * shares,
                    profit=profit,
                    profit_pct=profit_pct,
                    reason=reason
                )
                session.add(trade)
                session.commit()
                
                result = {
                    'code': stock_code,
                    'shares_sold': shares,
                    'sell_price': sell_price,
                    'cost_price': cost_per_share,
                    'profit': profit,
                    'profit_pct': profit_pct,
                    'remaining_shares': pos.shares
                }
                logger.info(f"卖出: {stock_code} {shares}股 @ {sell_price}, 盈亏 {profit:.2f} ({profit_pct:.2f}%)")
                return result
        except Exception as e:
            logger.error(f"卖出失败: {e}")
            return None
    
    def get_positions(self, active_only: bool = True) -> List[Dict]:
        """获取持仓列表"""
        try:
            with get_session() as session:
                query = session.query(Position)
                if active_only:
                    query = query.filter(Position.is_active == True)
                
                result = []
                for pos in query.all():
                    result.append({
                        'code': pos.stock_code,
                        'name': pos.stock_name,
                        'shares': pos.shares,
                        'avg_cost': pos.avg_cost,
                        'total_cost': pos.total_cost,
                        'buy_date': pos.buy_date,
                        'strategy': pos.strategy_tag,
                        'notes': pos.notes
                    })
                return result
        except Exception as e:
            logger.error(f"获取持仓失败: {e}")
            return []
    
    def get_position(self, stock_code: str) -> Optional[Dict]:
        """获取单只股票的持仓信息"""
        try:
            with get_session() as session:
                pos = session.query(Position).filter(
                    Position.stock_code == stock_code,
                    Position.is_active == True
                ).first()
                
                if not pos:
                    return None
                
                return {
                    'code': pos.stock_code,
                    'name': pos.stock_name,
                    'shares': pos.shares,
                    'avg_cost': pos.avg_cost,
                    'total_cost': pos.total_cost,
                    'buy_date': pos.buy_date,
                    'strategy': pos.strategy_tag
                }
        except Exception as e:
            logger.error(f"获取持仓信息失败: {e}")
            return None
    
    def calculate_pnl(self, stock_code: str, current_price: float) -> Optional[Dict]:
        """计算持仓盈亏"""
        pos = self.get_position(stock_code)
        if not pos:
            return None
        
        market_value = pos['shares'] * current_price
        profit = market_value - pos['total_cost']
        profit_pct = (current_price / pos['avg_cost'] - 1) * 100 if pos['avg_cost'] > 0 else 0
        
        return {
            'code': stock_code,
            'name': pos['name'],
            'shares': pos['shares'],
            'avg_cost': pos['avg_cost'],
            'current_price': current_price,
            'market_value': market_value,
            'total_cost': pos['total_cost'],
            'profit': profit,
            'profit_pct': profit_pct
        }


# 全局实例
portfolio_service = PortfolioService()
