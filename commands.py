"""group_admin_plugin 群管理命令。

提供 /ga 命令，供管理员执行禁言、踢出等群管理操作。
管理员白名单通过插件配置中的 admin_users 字段控制。

命令用法：
  /ga mute <@用户> [秒数]       — 禁言用户（默认 600 秒）
  /ga unmute <@用户>            — 解除用户禁言
  /ga kick <@用户> [拒绝加群]    — 踢出用户
  /ga help                      — 显示帮助
"""

from __future__ import annotations

import re
from typing import Any

from src.app.plugin_system.api import adapter_api
from src.app.plugin_system.api.log_api import get_logger
from src.app.plugin_system.api.send_api import send_text
from src.app.plugin_system.api.stream_api import get_stream_info
from src.core.components.base.command import BaseCommand, cmd_route

logger = get_logger("group_admin_plugin.command")

_NAPCAT_ADAPTER_SIGNATURE = "napcat_adapter:adapter:napcat_adapter"

# 匹配框架展开后的 AT 段，格式：@<昵称:用户ID>
_AT_PATTERN = re.compile(r"^@<([^>:]*):([^>]+)>$")

_USAGE = """\
/ga 群管理命令（管理员专用）：
  mute / 禁言   @用户 [秒数]       — 禁言用户（默认 600 秒）
  unmute / 解禁 @用户              — 解除用户禁言
  kick / 踢出   @用户 [拒绝加群]    — 踢出用户
  help / 帮助                      — 显示此帮助

示例：
  /ga mute @用户 300
  /ga unmute @用户
  /ga kick @用户 true"""


# ── NapCat API 辅助函数 ────────────────────────────────────────────────────────


def _coerce_int_if_digit(value: Any) -> Any:
    """将纯数字字符串转换为 int，其他保持原样。"""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            try:
                return int(s)
            except Exception:
                return value
    return value


def _format_napcat_failure(action: str, resp: dict[str, Any]) -> str:
    """将 NapCat 响应格式化为更易懂的失败文本。"""
    _ = str(resp.get("status") or "").strip().lower()
    retcode = resp.get("retcode")
    message = str(resp.get("message") or "").strip()
    wording = str(resp.get("wording") or "").strip()
    detail = wording or message

    if not detail:
        detail = f"retcode={retcode}" if retcode is not None else "未知错误"

    lowered = detail.lower()
    if "权限" in detail or "permission" in lowered or "not admin" in lowered:
        return (
            f"{action} 失败：权限不足。\n"
            "- 需要机器人为群主/管理员\n"
            "- 目标用户权限必须低于机器人\n"
            f"- 原始信息：{detail}"
        )

    if "不存在" in detail or "not found" in lowered:
        return (
            f"{action} 失败：目标不存在或已失效。\n"
            f"- 原始信息：{detail}"
        )

    if "超时" in detail or "timeout" in lowered:
        return (
            f"{action} 失败：请求超时。\n"
            "- 请检查 napcat_adapter 是否已连接 NapCat\n"
            "- 请检查 NapCat 服务是否正常\n"
            f"- 原始信息：{detail}"
        )

    return f"{action} 失败：{detail}"


async def _call_napcat_api(
    *,
    action_name: str,
    params: dict[str, Any],
    timeout: float = 30.0,
) -> tuple[bool, str]:
    """调用 napcat_adapter API 并统一解析响应。"""
    adapter = adapter_api.get_adapter(_NAPCAT_ADAPTER_SIGNATURE)
    if adapter is None:
        return False, "napcat_adapter 未启动：请先启用并启动 napcat_adapter 插件。"

    if not hasattr(adapter, "send_napcat_api"):
        return False, "napcat_adapter 不支持 send_napcat_api：请确认 napcat_adapter 版本兼容。"

    try:
        resp = await adapter.send_napcat_api(action_name, params, timeout=timeout)  # type: ignore[attr-defined]
    except Exception as exc:
        return (
            False,
            f"调用 NapCat API 异常：{exc}\n- action={action_name}\n- params={params}",
        )

    status = str(resp.get("status") or "").strip().lower()
    retcode = resp.get("retcode")
    if status == "ok" and (retcode == 0 or retcode is None):
        return True, "ok"

    return False, _format_napcat_failure(action_name, resp)


# ── 命令类 ──────────────────────────────────────────────────────────────────


class GroupAdminCommand(BaseCommand):
    """群管理命令。

    仅管理员（在插件配置的 admin_users 白名单中）可使用。
    """

    command_name: str = "ga"
    command_description: str = "群管理命令（管理员专用）：禁言/解除禁言/踢出群成员"
    associated_platforms: list[str] = ["qq"]

    @classmethod
    def match(cls, parts: list[str]) -> int:
        """匹配命令名，支持 ga 和 管理 两种触发词。

        Args:
            parts: 命令片段列表

        Returns:
            匹配长度，不匹配返回 0
        """
        if not parts:
            return 0
        if parts[0] in ("ga", "管理"):
            return 1
        return 0

    # ── 权限检查 ──────────────────────────────────────────────────────────

    def _is_admin(self) -> bool:
        """检查当前命令发送者是否为配置中的管理员。

        Returns:
            是否在管理员白名单中
        """
        if self._message is None:
            return False

        config = getattr(self.plugin, "config", None)
        if config is None:
            return False

        admin_users = getattr(getattr(config, "admin", None), "admin_users", None)
        if not admin_users:
            return False

        user_id = f"{self._message.platform}:{self._message.sender_id}"
        return user_id in admin_users

    async def _require_admin(self) -> bool:
        """检查管理员权限，若未通过则发送提示并返回 False。

        Returns:
            是否通过权限检查
        """
        if self._is_admin():
            return True
        msg = "无权使用该命令：你不在管理员白名单中。"
        await self._reply(msg)
        return False

    # ── 工具方法 ──────────────────────────────────────────────────────────

    async def _reply(self, text: str) -> None:
        """向当前聊天流发送文本回复。

        Args:
            text: 要发送的文本内容
        """
        await send_text(text, stream_id=self.stream_id)

    async def _get_group_id(self) -> int | str | None:
        """从当前会话中获取群 ID。

        Returns:
            群 ID，非群聊时返回 None
        """
        info = await get_stream_info(self.stream_id)
        if not info:
            return None
        group_id = info.get("group_id")
        if group_id is None:
            return None
        return _coerce_int_if_digit(group_id)

    async def _parse_user(self, user_arg: str) -> str | None:
        """解析用户参数，返回 user_id。

        Args:
            user_arg: 用户参数（支持 @<昵称:ID> 或直接 user_id）

        Returns:
            用户 ID，解析失败时返回 None
        """
        at_match = _AT_PATTERN.fullmatch(user_arg)
        if at_match:
            return at_match.group(2)
        return user_arg.strip() or None

    # ── 命令处理器 ────────────────────────────────────────────────────────

    @cmd_route("help")
    async def handle_help(self) -> tuple[bool, str]:
        """显示帮助信息。"""
        if not await self._require_admin():
            return False, "no permission"
        await self._reply(_USAGE)
        return True, "ok"

    @cmd_route("帮助")
    async def handle_help_cn(self) -> tuple[bool, str]:
        """显示帮助信息（中文别名）。"""
        return await self.handle_help()

    @cmd_route()
    async def handle_root(self) -> tuple[bool, str]:
        """无子命令时显示帮助。"""
        return await self.handle_help()

    # ── mute / 禁言 ──────────────────────────────────────────────────────

    @cmd_route("mute")
    async def handle_mute(
        self,
        user: str = "",
        seconds: str = "600",
    ) -> tuple[bool, str]:
        """禁言指定用户。

        Args:
            user: @<昵称:用户ID> 或 user_id
            seconds: 禁言时长（秒），默认 600

        Returns:
            tuple[bool, str]: (是否成功, 结果详情)
        """
        if not await self._require_admin():
            return False, "no permission"

        if not user:
            await self._reply("用法：/ga mute @用户 [秒数]")
            return False, "missing user"

        user_id = await self._parse_user(user)
        if not user_id:
            return False, "invalid user"

        group_id = await self._get_group_id()
        if not group_id:
            await self._reply("禁言只能在群聊中使用。")
            return False, "not in group"

        try:
            duration = int(seconds)
            if duration <= 0:
                await self._reply("禁言时长必须为正整数（单位：秒）。")
                return False, "invalid duration"
        except ValueError:
            await self._reply("禁言时长必须为正整数（单位：秒）。")
            return False, "invalid duration"

        ok, msg = await _call_napcat_api(
            action_name="set_group_ban",
            params={
                "group_id": group_id,
                "user_id": _coerce_int_if_digit(user_id),
                "duration": duration,
            },
        )
        if ok:
            reply = f"已禁言用户 {user_id}（{duration} 秒）。"
            await self._reply(reply)
            return True, reply
        await self._reply(msg)
        return False, msg

    @cmd_route("禁言")
    async def handle_mute_cn(
        self,
        user: str = "",
        seconds: str = "600",
    ) -> tuple[bool, str]:
        """禁言指定用户（中文别名）。"""
        return await self.handle_mute(user, seconds)

    # ── unmute / 解禁 ────────────────────────────────────────────────────

    @cmd_route("unmute")
    async def handle_unmute(self, user: str = "") -> tuple[bool, str]:
        """解除用户禁言。

        Args:
            user: @<昵称:用户ID> 或 user_id

        Returns:
            tuple[bool, str]: (是否成功, 结果详情)
        """
        if not await self._require_admin():
            return False, "no permission"

        if not user:
            await self._reply("用法：/ga unmute @用户")
            return False, "missing user"

        user_id = await self._parse_user(user)
        if not user_id:
            return False, "invalid user"

        group_id = await self._get_group_id()
        if not group_id:
            await self._reply("解除禁言只能在群聊中使用。")
            return False, "not in group"

        ok, msg = await _call_napcat_api(
            action_name="set_group_ban",
            params={
                "group_id": group_id,
                "user_id": _coerce_int_if_digit(user_id),
                "duration": 0,
            },
        )
        if ok:
            reply = f"已解除用户 {user_id} 的禁言。"
            await self._reply(reply)
            return True, reply
        await self._reply(msg)
        return False, msg

    @cmd_route("解禁")
    async def handle_unmute_cn(self, user: str = "") -> tuple[bool, str]:
        """解除用户禁言（中文别名）。"""
        return await self.handle_unmute(user)

    # ── kick / 踢出 ──────────────────────────────────────────────────────

    @cmd_route("kick")
    async def handle_kick(
        self,
        user: str = "",
        reject_add_request: str = "false",
    ) -> tuple[bool, str]:
        """踢出群成员。

        Args:
            user: @<昵称:用户ID> 或 user_id
            reject_add_request: 是否拒绝再加群（true/false），默认 false

        Returns:
            tuple[bool, str]: (是否成功, 结果详情)
        """
        if not await self._require_admin():
            return False, "no permission"

        if not user:
            await self._reply("用法：/ga kick @用户 [true/false]")
            return False, "missing user"

        user_id = await self._parse_user(user)
        if not user_id:
            return False, "invalid user"

        group_id = await self._get_group_id()
        if not group_id:
            await self._reply("踢出只能在群聊中使用。")
            return False, "not in group"

        reject = reject_add_request.lower() in ("true", "1", "yes", "on")

        ok, msg = await _call_napcat_api(
            action_name="set_group_kick",
            params={
                "group_id": group_id,
                "user_id": _coerce_int_if_digit(user_id),
                "reject_add_request": reject,
            },
        )
        if ok:
            suffix = "（已拒绝再次加群）" if reject else ""
            reply = f"已踢出用户 {user_id}{suffix}。"
            await self._reply(reply)
            return True, reply
        await self._reply(msg)
        return False, msg

    @cmd_route("踢出")
    async def handle_kick_cn(
        self,
        user: str = "",
        reject_add_request: str = "false",
    ) -> tuple[bool, str]:
        """踢出群成员（中文别名）。"""
        return await self.handle_kick(user, reject_add_request)


__all__ = ["GroupAdminCommand"]
