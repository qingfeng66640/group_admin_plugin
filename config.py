"""group_admin_plugin 配置模型。"""

from __future__ import annotations

from src.core.components.base.config import BaseConfig, Field, SectionBase, config_section


class GroupAdminConfig(BaseConfig):
    """群管理插件配置。"""

    config_name: str = "group_admin_plugin"

    @config_section("plugin")
    class PluginSection(SectionBase):
        """插件基本设置。"""

        enabled: bool = Field(default=True, description="是否启用插件")
        config_version: str = Field(default="1.0.0", description="配置文件版本")

    @config_section("admin")
    class AdminSection(SectionBase):
        """管理员白名单。"""

        admin_users: list[str] = Field(
            default=[],
            description="管理员用户列表，格式：platform:user_id，如 qq:12345678",
        )

    plugin: PluginSection = Field(default_factory=PluginSection)
    admin: AdminSection = Field(default_factory=AdminSection)


__all__ = ["GroupAdminConfig"]
