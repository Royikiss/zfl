# extract (万能解压与一键压缩终极工具)

`extract` 是 ZFL 内置的高性能命令行解压与压缩一体化工具。设计遵循极简交互哲学：**不传格式参数默认自适应解压；传入格式参数直接一键压缩**。具备压缩率统计、内容预览、源文件自动清理与静默模式。

---

## 📖 使用方法与示例

### 1. 默认解压模式 (无需任何选项)
直接传入压缩包文件名，自动识别格式并解压，内置重名碰撞防护与防解压炸弹保护：
```bash
extract project.tar.gz               # 自动解压 tar.gz
x release.zip docs.7z                # 快捷别名，同时解压 zip 与 7z
extract -p 123456 secret.zip        # 解压带密码的压缩包
```

### 2. 预览模式 (`-l` / `--list`)
无需解压，直接在终端中打印压缩包内部目录树清单：
```bash
extract -l project.tar.gz
extract -l -p 123456 secret.zip
```

### 3. 一键压缩与密码加密模式
传入格式选项（如 `--zip`, `--tar.gz`, `--7z`）触发压缩，可使用 `-p <密码>` 加密：
```bash
extract --zip my_folder/                    # 自动压缩为 my_folder.zip 并显示压缩率统计
extract --zip -p 123456 confidential/      # 加密压缩为 zip
extract --7z -p mypass -o secret assets/   # 指定输出名为 secret.7z 并加密
```

### 4. 解压后自动删除源包 (`-rm` / `--remove-source`)
解压成功后可选自动清理原始压缩包：
```bash
extract -rm temporary_log.zip
```

### 5. 静默模式 (`-q` / `--quiet`)
方便在 Shell 脚本或 Cron 后台任务中静默运行：
```bash
extract -q --zip backup_dir/
```

---

## ⚙️ 格式与选项参数对照表

| 选项参数 | 说明 |
| :--- | :--- |
| `-l` / `--list` | 预览压缩包内容清单不解压 |
| `-rm` / `--remove-source` | 解压成功后自动删除源压缩文件 |
| `-q` / `--quiet` | 静默模式，隐藏所有终端日志 |
| `-p <密码>` | 指定加密或解密密码 |
| `-o <包名>` | 指定输出压缩包名称 |
| `--zip` | 通用 zip 压缩格式 (支持加密与压缩率统计) |
| `--tar.gz` / `--tgz` | tar 打包 + gzip 压缩 |
| `--tar.bz2` / `--tbz2` | tar 打包 + bzip2 压缩 |
| `--tar.xz` / `--txz` | tar 打包 + xz 极高压缩率 |
| `--tar.zst` / `--tzst` | tar 打包 + zstd 极速高压缩率 |
| `--7z` | 7-Zip 高压缩率归档 (支持加密与统计) |
| `--rar` | RAR 归档格式 (支持加密与统计) |

---

## 💡 Zsh Tab 自动补全

在终端输入 `extract -` 或 `x -` 并按 **Tab** 键，系统自动提示参数菜单与说明：

```bash
-l         -- 仅预览压缩包内容清单不解压
-rm        -- 解压成功后自动删除源压缩包
-q         -- 静默运行模式，隐藏状态日志
-p         -- 指定压缩/解压密码
-o         -- 指定输出文件名
--zip      -- 一键压缩为 .zip 格式
--7z       -- 一键压缩为 7-Zip (.7z)
```
