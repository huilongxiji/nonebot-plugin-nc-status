import tomllib
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel

# 关键：获取当前文件所在目录
PLUGIN_DIR = Path(__file__).parent

class Connection(BaseModel):
    name: str
    host: str
    port: int
    token: str
    
    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

class Settings(BaseModel):
    interval: int = 30          # 轮询间隔（秒）
    timeout: int = 10           # 请求超时（秒）
    group: Optional[int] = None  # 上报群号
    retry_count: int = 3        # 重试次数
    error_threshold: int = 6    # 连续错误阈值（达到后上报）

class Config(BaseModel):
    settings: Settings
    connections: List[Connection]

_config: Config = None

# 默认配置文件模板
DEFAULT_CONFIG = """# NC Status 连接池配置文件
# 自动生成于首次启动

[settings]
interval = 30           # 轮询间隔（秒）
timeout = 10            # 请求超时（秒）
group = 123456789       # 上报群号（请修改为实际群号）
error_threshold = 6     # 连续错误阈值（达到后上报）
retry_count = 3         # 重试次数（暂未使用）

# 连接配置示例（请根据实际情况修改）
# 每个 [[connections]] 块代表一个连接

[[connections]]
name = "示例Bot"        # 连接名称（用于识别）
host = "127.0.0.1"      # 主机地址
port = 8080             # 端口号
token = "your_token"    # 访问令牌

# 可以添加更多连接
# [[connections]]
# name = "备用Bot"
# host = "127.0.0.1"
# port = 8081
# token = "another_token"
"""

def create_default_config(path: Path) -> None:
    """创建默认配置文件"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(DEFAULT_CONFIG)

def load_config(config_path: str = "connections.toml") -> Config:
    """加载配置文件，不存在则创建默认配置"""
    global _config
    
    # 使用插件目录作为基准路径
    path = PLUGIN_DIR / config_path
    
    # 配置文件不存在则创建默认配置
    if not path.exists():
        create_default_config(path)
        # 提示用户修改配置
        raise FileNotFoundError(
            f"配置文件不存在，已自动创建默认配置: {path}\n"
            f"请修改配置文件后重新启动！"
        )
    
    with open(path, "rb") as f:
        data = tomllib.load(f)
    
    _config = Config(
        settings=Settings(**data.get("settings", {})),
        connections=[Connection(**conn) for conn in data.get("connections", [])]
    )
    return _config

def get_config() -> Config:
    if _config is None:
        raise RuntimeError("配置未加载")
    return _config