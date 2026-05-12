# check_update 详细文档

本文档说明 `functions/check_update.zsh` 的设计目标、执行流程、配置项、状态文件、故障排查与运维建议。

适用范围：当前仓库 `base.zsh -> core/startup_tasks.zsh -> check_update` 启动链路。

---

## 1. 目标与设计原则

`check_update` 是一个“启动时提示 + 按需执行更新”的函数，目标是：

1) 启动不阻塞
- 前台优先读取缓存。
- 缓存缺失/过期时，后台异步刷新。

2) 后台不触发 sudo
- 后台仅做只读计数（`checkupdates` / `pacman -Qu` / `yay -Qua` / `flatpak remote-ls`）。
- 真正需要权限的更新仅在用户确认后执行（`yay -Syu` / `flatpak update`）。

3) 可控提示频率
- 支持策略化提示（避免“太吵”或“漏更新”）。

4) 可恢复
- 锁文件支持陈旧锁自愈，避免后台刷新永久卡住。

---

## 2. 入口与调用方式

- 自动入口：`core/startup_task_commands.zsh` 中的 `check_update`
- 手动调用：
  - `check_update`
  - `check_update --force`
  - `check_update --help`

参数：

- `-f, --force`
  - 忽略日常抑制条件，强制进入一次交互流程。
- `-h, --help`
  - 显示帮助。

---

## 3. 后端与职责划分

当前内置后端：

1) `aur_pacman`
- 可用性：`yay` 存在。
- 计数（只读）：
  - 官方仓：`checkupdates`（若无则 fallback `pacman -Qu`）
  - AUR：`yay -Qua`
  - 总数 = 官方仓 + AUR
- 执行更新：`yay -Syu`

2) `flathub`
- 可用性：`flatpak` 存在且 remotes 中有 `flathub`
- 计数（只读）：`flatpak remote-ls --updates --columns=application,origin`
- 执行更新：按 ref 逐个 `flatpak update -y <ref>`，并显示 `[idx/total]` 进度

---

## 4. 关键状态文件

目录：`~/.cache/zsh`

1) `UpdateFlag.lock`
- 含义：上次“成功更新”日期（YYYY-MM-DD）。
- 仅在更新成功后写入。

2) `UpdatePromptFlag.lock`
- 含义：上次“拒绝更新提示”日期。
- 仅在用户拒绝时写入。

3) `UpdateCountCache.lock`
- 含义：更新数量缓存（shell 赋值格式）。
- 字段：
  - `generated_at=<epoch>`
  - `aur_pacman=<count>`
  - `flathub=<count>`

4) `UpdateRefresh.lock/`
- 含义：后台刷新互斥锁目录。
- 含时间戳：`.timestamp`（epoch）。
- 超时后可自动回收（见环境变量）。

备注：标记文件会以只读权限保存（0400），写入前临时放开权限，写完再恢复，防止误改。

---

## 5. 交互流程（主流程）

1) 参数解析
- 识别 `--force` / `--help`。
- 其他参数报错并返回非 0。

2) 初始化状态
- 首次运行若无 `UpdateFlag.lock`，初始化为今天（保持“首次不强制更新”）。

3) 读取缓存与后端
- 探测可用后端。
- 读取 `UpdateCountCache.lock`。
- 缓存缺失或过期时，异步触发刷新（不阻塞前台）。

4) 计算是否提示
- 由 `CHECK_UPDATE_PROMPT_POLICY` 控制（详见第 6 节）。
- `--force` 始终优先。

5) 进入问答
- 输入：
  - `Enter / Y / y` => 执行更新
  - `C / c` => 查看各后端可更新数量后继续问
  - `N / n / 其他` => 拒绝更新

6) 写回状态
- 更新成功：写 `UpdateFlag.lock`，删除同日拒绝标记，异步刷新缓存。
- 用户拒绝：写 `UpdatePromptFlag.lock`。
- 更新失败：不写成功/拒绝标记，便于后续重试。

---

## 6. 环境变量（可调策略）

1) `CHECK_UPDATE_CACHE_TTL_SECONDS`
- 含义：更新数量缓存有效期（秒）。
- 默认：`1800`。
- 非法值会回退到默认值。

2) `CHECK_UPDATE_LOCK_STALE_SECONDS`
- 含义：后台刷新锁“陈旧阈值”（秒）。
- 默认：`600`。
- 若锁时间戳超过阈值，自动回收锁后重建。
- 非法值会回退到默认值。

3) `CHECK_UPDATE_PROMPT_POLICY`
- 可选值：
  - `pending_first`（默认）
    - 同天若仍有待更新包，仍会提示（减少漏更新）。
  - `once_per_day`
    - 同天最多提示一次；当日拒绝后静默。
  - `strict_daily`
    - 仅依据“上次成功更新日期”是否为今天；同天不再提示。
- 非法值会回退到 `pending_first`。

建议配置示例（可放 `core/usr.zsh`）：

```zsh
# 缓存30分钟
export CHECK_UPDATE_CACHE_TTL_SECONDS=1800

# 锁超时10分钟自动回收
export CHECK_UPDATE_LOCK_STALE_SECONDS=600

# 提示策略：同天只提示一次
export CHECK_UPDATE_PROMPT_POLICY=once_per_day
```

---

## 7. 与 startup task 执行器的协作约束

`core/startup_tasks.zsh` 已使用独立文件描述符读取任务文件（fd 3），避免占用全局 stdin。

意义：
- `check_update` 内部 `read` 会从真实终端读取。
- 不会再误读任务文件后续行（例如注释）导致“看起来像自动按了 N”。

---

## 8. 输出与退出码语义

在 startup 执行器视角：
- `0`：任务成功（包括“用户拒绝更新”这种受控分支，函数内部已处理）。
- 非 0：任务失败（例如参数错误或更新执行失败未被吞掉）。

在 `check_update` 内部问答函数语义：
- `0`：更新成功
- `2`：用户拒绝
- 其他：更新失败

主函数会把拒绝分支处理为“业务成功结束”，因此启动日志可见 `exit=0`。

---

## 9. 故障排查

1) 现象：启动不再刷新数量
- 排查：`~/.cache/zsh/UpdateRefresh.lock` 是否残留。
- 处理：
  - 正常应被自动回收（超时机制）。
  - 手动兜底：`rm -rf ~/.cache/zsh/UpdateRefresh.lock`

2) 现象：总是提示更新
- 检查：
  - 当前策略是否 `pending_first`
  - `UpdateCountCache.lock` 中计数是否持续 > 0
- 可改策略：`once_per_day` 或 `strict_daily`

3) 现象：后台提示 sudo 密码
- 当前实现不应出现。
- 若出现，通常是外部脚本/其他任务触发，不是 `check_update` 后台计数路径。

4) 现象：帮助信息/策略不生效
- 确认已加载最新函数文件（重新开 shell 或重新 source `base.zsh`）。

---

## 10. 运维建议

1) 变更前先打 checkpoint commit
- 启动链路改动影响面大，建议始终先做空提交锚点。

2) 把“检测”和“更新”分离到底
- 检测阶段禁止 sudo。
- 只在用户确认更新时请求权限。

3) 优先保留可观测性
- 保留缓存年龄、锁状态、后端可用性等提示，便于现场诊断。

4) 新增后端时遵循约定
- 每个后端提供 3 个函数：
  - `_check_update_backend_available_<name>`
  - `_check_update_backend_count_<name>`
  - `_check_update_backend_update_<name>`

---

## 11. 未来可选增强

1) 增加 `quiet/info/debug` 日志级别
2) 将后端注册进一步插件化（从硬编码数组解耦）
3) 增加最小 smoke test（zsh -n + 关键函数 dry-run）
4) 引入 per-backend 缓存时间戳，展示更细粒度新鲜度

---

## 12. 相关文件

- `functions/check_update.zsh`
- `core/startup_tasks.zsh`
- `core/startup_task_commands.zsh`
- `PROJECT_ARCHITECTURE.md`
