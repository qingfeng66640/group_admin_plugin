# Group Admin Plugin — 群管理插件

基于 NapCat API 的群管理命令插件，支持禁言、解除禁言、踢出群成员等操作。

## 适用平台

- QQ（通过 NapCat）

## 安装

### 方法一：从插件市场安装（推荐）

```bash
mpdt market install group_admin_plugin
```

### 方法二：手动安装

将插件文件夹放入 Neo-MoFox 的 `plugins/` 目录下，并安装依赖：

```bash
cd plugins/group_admin_plugin
mpdt depend install
```

## 配置

配置文件位于 `config/plugins/group_admin_plugin/config.toml`：

```toml
[plugin]
enabled = true
config_version = "1.0.0"

[admin]
admin_users = ["qq:12345678", "qq:87654321"]
```

### 配置项说明

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `plugin.enabled` | bool | `true` | 是否启用插件 |
| `plugin.config_version` | string | `"1.0.0"` | 配置文件版本 |
| `admin.admin_users` | string[] | `[]` | 管理员白名单，格式：`platform:user_id` |

> ⚠️ **权限说明**：`admin_users` 用于指定有权限使用群管理命令的管理员。列表中每一项的格式为 `平台:用户ID`，例如 `qq:12345678`。不在白名单中的用户无法执行任何管理操作。

## 使用方式

### 触发命令

- `/ga <子命令> [参数]`
- `/管理 <子命令> [参数]`

两种触发词效果相同。

### 命令列表

| 命令 | 中文别名 | 功能 | 参数 |
|------|---------|------|------|
| `mute` | `禁言` | 禁言用户 | `@用户 [秒数]` |
| `unmute` | `解禁` | 解除禁言 | `@用户` |
| `kick` | `踢出` | 踢出群成员 | `@用户 [true/false]` |
| `help` | `帮助` | 显示帮助信息 | 无 |

> 参数中 `@用户` 支持 NapCat 的 AT 格式 `@<昵称:用户ID>` 或直接输入用户 ID。

### 详细用法

#### 禁言用户

```
/ga mute @用户 300
/ga 禁言 @用户
```

- `秒数` 可选，默认为 600 秒（10 分钟）
- 禁言时长必须为正整数

#### 解除禁言

```
/ga unmute @用户
/ga 解禁 @用户
```

#### 踢出群成员

```
/ga kick @用户
/ga kick @用户 true
/ga 踢出 @用户 false
```

- 第三个参数可选，`true` 表示拒绝该用户再次加群，默认为 `false`

#### 查看帮助

```
/ga help
/ga 帮助
/管理 帮助
```

## 使用示例

```
# 禁言用户 5 分钟
/ga mute @小明 300

# 解除用户禁言
/ga unmute @小明

# 踢出用户并不允许再加群
/ga kick @捣蛋鬼 true

# 查看帮助
/ga help
```

## 错误处理

| 场景 | 提示内容 |
|------|---------|
| 非管理员使用 | "无权使用该命令：你不在管理员白名单中。" |
| 非群聊中使用群管理命令 | "禁言/解除禁言/踢出只能在群聊中使用。" |
| 缺少必要参数 | "用法：/ga mute @用户 [秒数]" |
| NapCat API 权限不足 | "xxx 失败：权限不足。需要机器人为群主/管理员" |
| NapCat 未启动 | "napcat_adapter 未启动：请先启用并启动 napcat_adapter 插件。" |

## 依赖

- `napcat_adapter:adapter:napcat_adapter` — NapCat 适配器，提供 OneBot API 调用能力
- Neo-MoFox Core >= 1.0.0

## 开发

```bash
# 运行测试
pytest test/plugins/group_admin_plugin/ -v

# 检查代码
ruff check plugins/group_admin_plugin/
```

## 许可

GPL-3.0
