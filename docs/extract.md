# extract (万能解压与一键压缩工具)

`extract` 是 ZFL 内置的高性能命令行解压与压缩一体化工具。默认支持根据文件后缀自适应解压并内置“防解压炸弹”保护；新增一键压缩模式，支持使用参数（如 `--zip`, `--tar.gz`, `--7z` 等）代替后缀指定压缩格式，并配备带中文/英文说明提示的 Zsh Tab 自动补全。

---

## 📖 使用方法与示例

```bash
# 1. 解压模式 (默认行为)
extract <压缩包1> [压缩包2 ...]
x <压缩包1> [压缩包2 ...]

# 2. 一键压缩模式 (-c 或 --compress)
extract -c [--格式参数] [-o 输出文件名] <目标1> [目标2 ...]
```

### 解压示例
```bash
extract project.tar.gz               # 解压 tar.gz
x release.zip docs.7z                # 同时解压 zip 与 7z
```

### 一键压缩示例
```bash
extract -c --zip my_folder/          # 将 my_folder/ 打包压缩为 my_folder.zip
extract -c --tar.gz file1 dir2/     # 默认以首项命名压缩为 file1.tar.gz
extract -c --7z -o backup assets/   # 指定输出名为 backup.7z
```

---

## ⚙️ 格式参数与对应文件后缀

| 参数选项 | 对应的后缀格式 | 说明 |
| :--- | :--- | :--- |
| `--zip` | `.zip` | 通用 zip 压缩格式 (默认) |
| `--tar.gz` / `--tgz` | `.tar.gz` / `.tgz` | tar 打包 + gzip 压缩 |
| `--tar.bz2` / `--tbz2` | `.tar.bz2` / `.tbz2` | tar 打包 + bzip2 压缩 |
| `--tar.xz` / `--txz` | `.tar.xz` / `.txz` | tar 打包 + xz 高压缩率 |
| `--tar.zst` / `--tzst` | `.tar.zst` / `.tzst` | tar 打包 + zstd 极速压缩 |
| `--tar` | `.tar` | 未压缩的打包归档 |
| `--7z` | `.7z` | 7-Zip 高压缩率归档 |
| `--rar` | `.rar` | RAR 归档格式 |

---

## 💡 Zsh Tab 自动补全提示

在终端中输入 `extract -` 或 `x -` 并按 **Tab** 键，系统会自动弹出一键压缩参数选择菜单，并在右侧清晰标注各个参数的功能与提示说明：

```bash
--tar.gz   -- 压缩为 .tar.gz
--zip      -- 压缩为 .zip
--7z       -- 压缩为 .7z
-c         -- 切换为一键压缩模式
-o         -- 指定输出文件名
```
