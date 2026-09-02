# update

`update` 是一个针对 Arch Linux 及 Flatpak 环境的一键系统更新工具。

---

## 📖 用法与示例

```bash
update [选项]
```

### 选项
- `-h, --help`: 显示帮助信息并退出

### 示例
```bash
update         # 直接更新系统与 Flatpak 软件包
```

---

## ⚙️ 运作原理

1. 自动检测并优先调用包管理器：
   - 若系统已安装 `yay`，执行 `yay -Syu` 协同更新官方仓库与 AUR 软件包。
   - 若未安装 `yay`，回退至 `sudo pacman -Syu`。
2. 若系统配置有 `flatpak` (如 `flathub`)，一并执行 `flatpak update`。
3. 更新成功后，将今日日期（`YYYY-MM-DD`）写入 `~/.cache/zsh/UpdateFlag.lock`，重置当天打开终端时的更新提示。
