from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment
from nonebot.plugin import on_command, PluginMetadata
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.adapters import Message
from nonebot import require, get_driver
from nonebot import logger
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .config import load_config, get_config, Connection
from nonebot_plugin_htmlrender import text_to_pic


# 确保 apscheduler 插件已加载
require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler

__plugin_meta__ = PluginMetadata(
    name="定时任务插件",
    description="每 30 秒在控制台输出运行状态",
    usage="自动运行，无需手动触发",
    type="application",
    homepage="",
    supported_adapters=None,
)


# ============ 全局变量 ============
# 全局客户端（长连接）
_client: httpx.AsyncClient = None


# ============ 错误追踪 ============
@dataclass
class ErrorTracker:
    """错误追踪器"""
    error_type: str = ""      # 当前错误类型
    error_reason: str = ""    # 错误原因
    count: int = 0            # 连续出现次数
    reported: bool = False    # 是否已上报

# 全局错误追踪表 {name: ErrorTracker}
_error_trackers: Dict[str, ErrorTracker] = {}


# ============ 生命周期管理 ============
driver = get_driver()

@driver.on_startup
async def init_client():
    """Bot 启动时初始化连接池"""
    global _client
    
    # 先加载配置
    config = load_config("connections.toml")
    settings = config.settings
    
    # 使用配置中的 timeout 初始化客户端
    _client = httpx.AsyncClient(timeout=settings.timeout)
    logger.info(f"连接池初始化完成 (timeout={settings.timeout}s)")

    logger.info(f"已加载 {len(config.connections)} 个连接:")
    for conn in config.connections:
        logger.info(f"  - {conn.name}: {conn.url}")
    
    # 手动注册定时任务，使用配置中的 interval
    scheduler.add_job(
        timer_task,
        "interval",
        seconds=settings.interval,
        id="check_login_status",
        replace_existing=True
    )
    logger.info(f"定时任务已注册 (interval={settings.interval}s, threshold={settings.error_threshold}次)")


@driver.on_shutdown
async def close_client():
    """Bot 关闭时释放连接池"""
    global _client
    if _client:
        await _client.aclose()
        _client = None


# ============ 核心函数 ============
async def get_client() -> httpx.AsyncClient:
    """获取/初始化客户端"""
    global _client
    if _client is None:
        config = get_config()
        _client = httpx.AsyncClient(timeout=config.settings.timeout)
    return _client


async def fetch_single(conn: Connection) -> Dict[str, Any]:
    """
    请求单个地址

    Args:
        conn: 连接配置对象
    """
    client = await get_client()
    try:
        response = await client.get(
            url=f"{conn.url}/get_status",
            headers={"Authorization": f"Bearer {conn.token}"}
        )
        # 尝试解析 JSON，失败则返回空字典
        try:
            data = response.json()
        except Exception:
            data = {}
        
        return {
            "name": conn.name,
            "url": conn.url,
            "status_code": response.status_code,
            "data": data,
            "success": True,
        }
    except Exception as e:
        return {
            "name": conn.name,
            "url": conn.url,
            "error": str(e),
            "success": False,
        }


async def fetch_all() -> List[Dict[str, Any]]:
    """并发请求所有连接"""
    config = get_config()
    tasks = [fetch_single(conn) for conn in config.connections]
    return await asyncio.gather(*tasks)


def get_error_info(data: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    """
    解析错误信息
    
    Returns:
        (error_type, error_reason) 或 (None, None) 表示正常
    """
    # 连接失败
    if not data["success"]:
        return ("offline", data.get("error", "连接失败"))
    
    # HTTP 错误
    if data["status_code"] != 200:
        return ("http_error", f"HTTP {data['status_code']}")
    
    # 业务错误
    resp = data.get("data", {})
    status = resp.get("status")
    retcode = resp.get("retcode")
    
    if status != "ok" or retcode != 0:
        return ("bot_error", f"status={status}, retcode={retcode}")
    
    # 正常
    return (None, None)


async def check_changes(results: List[Dict[str, Any]]) -> None:
    """
    检查连接状态变化，连续6次相同错误才上报
    
    Args:
        results: fetch_all 返回的结果列表
    """
    to_report = []  # 需要上报的错误
    config = get_config()
    error_threshold = config.settings.error_threshold

    for data in results:
        name = data["name"]
        url = data["url"]
        
        # 初始化追踪器
        if name not in _error_trackers:
            _error_trackers[name] = ErrorTracker()
        
        tracker = _error_trackers[name]
        
        # 判断当前状态
        error_type, error_reason = get_error_info(data)
        
        if error_type is None:
            # 正常状态，重置追踪器
            if tracker.count > 0:
                logger.info(f"✅ [{name}] 恢复正常")
            tracker.error_type = ""
            tracker.error_reason = ""
            tracker.count = 0
            tracker.reported = False
        else:
            # 有错误
            if tracker.error_type == error_type:
                # 相同错误，累加计数
                tracker.count += 1
            else:
                # 不同错误，重置计数
                tracker.error_type = error_type
                tracker.error_reason = error_reason
                tracker.count = 1
                tracker.reported = False
            
            logger.warning(f"⚠️ [{name}] {error_type} - 连续第 {tracker.count} 次 - {error_reason}")
            
            # 达到阈值且未上报
            if tracker.count >= error_threshold and not tracker.reported:
                tracker.reported = True
                to_report.append({
                    "name": name,
                    "url": url,
                    "error_type": error_type,
                    "error_reason": error_reason,
                    "count": tracker.count
                })

    # 触发上报
    if to_report:
        for error in to_report:
            logger.error(f"🔴 [{error['name']}] 触发上报！连续 {error['count']} 次 {error['error_type']}")
        await send_error_report(to_report)


async def send_error_report(errors: List[Dict[str, Any]]):
    """
    发送错误上报给管理员
    
    Args:
        errors: 需要上报的错误列表
    """
    from nonebot import get_bot
    
    config = get_config()
    group_id = config.settings.group
    
    if not group_id:
        logger.warning("未配置上报群号，跳过上报")
        return
    
    try:
        bot = get_bot()
    except Exception as e:
        logger.error(f"获取 Bot 实例失败: {e}")
        return
    
    for error in errors:
        msg = f"⚠️ 连接异常警报\n"
        msg += f"名称: {error['name']}\n"
        msg += f"地址: {error['url']}\n"
        msg += f"类型: {error['error_type']}\n"
        msg += f"原因: {error['error_reason']}\n"
        msg += f"连续: {error['count']} 次"
        
        try:
            await bot.send_group_msg(group_id=group_id, message=msg)
        except Exception as e:
            logger.error(f"发送上报消息失败: {e}")


def get_all_errors() -> List[Dict[str, Any]]:
    """
    获取当前所有异常状态（供手动查询使用）
    """
    errors = []
    for name, tracker in _error_trackers.items():
        if tracker.count > 0:
            errors.append({
                "name": name,
                "type": tracker.error_type,
                "reason": tracker.error_reason,
                "count": tracker.count,
                "reported": tracker.reported
            })
    return errors


# ============ 定时函数 ============
async def timer_task():
    """定时任务：根据配置的 interval 执行"""
    results = await fetch_all()
    await check_changes(results)


# ============ 消息函数 ============
status = on_command(
    cmd = "nc状态",
    aliases={"nc status"},
    permission=SUPERUSER,
    priority=10,
    block=True
)

@status.handle()
async def handle_nc_status(event: MessageEvent, arg: Message = CommandArg()):
    results = await fetch_all()
    await check_changes(results)
    
    # 获取当前所有异常
    user_data = get_all_errors()

    if not user_data:
        await status.finish("未发现异常状态，所有连接正常")
    
    msg_end = ""
    for data in user_data:
        name = data['name']
        error_type = data['type']
        reason = data['reason']
        count = data['count']
        reported = "是" if data['reported'] else "否"
        msg_message = f"实例名称: {name}\n错误类型: {error_type}\n目前状态: {reason}\n连续次数: {count}\n已上报: {reported}\n\n"
        msg_end += msg_message
    
    pic = await text_to_pic(text=msg_end.strip(), width=300)
    await status.finish(MessageSegment.image(pic))
