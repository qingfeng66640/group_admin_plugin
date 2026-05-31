"""group_admin_plugin 插件注册入口。

遵循 napcat_extension 的模式，将 @register_plugin 放在独立的 plugin.py 中，
避免 __init__.py 作为包导入时与 manifest.json entry_point 加载产生冲突。
"""

from __future__ import annotations

from src.core.components import BasePlugin, register_plugin

from .commands import GroupAdminCommand
from .config import GroupAdminConfig


@register_plugin
class GroupAdminPlugin(BasePlugin):
    """群管理插件：通过 /ga 命令禁言/踢出。"""

    plugin_name: str = "group_admin_plugin"
    plugin_description: str = "群管理插件：通过 /ga 命令禁言/踢出（基于 NapCat API）"
    plugin_version: str = "1.0.0"

    configs: list[type] = [GroupAdminConfig]
    dependent_components: list[str] = ["napcat_adapter:adapter:napcat_adapter"]

    def get_components(self) -> list[type]:
        """返回本插件提供的组件类。"""
        return [GroupAdminCommand]


__all__ = ["GroupAdminPlugin"]
