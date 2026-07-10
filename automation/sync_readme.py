#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 描述: README.md 项目结构树自动同步与检测工具

import os
import re

# 获取项目根目录 (相对于 scripts/automation)
script_dir = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(script_dir)

# 预设的顶层项及其展示顺序
TOP_LEVEL_ITEMS = [
    'base.zsh',
    'core/',
    'functions/',
    'custom_functions/',
    'python/',
    'docs/',
    'automation/'
]

# 静态 fallback 描述字典
FALLBACK_DESCS = {
    'core/': '核心调度与公共模块',
    'functions/': '模块化业务函数目录 (文件名与函数名 1:1 映射)',
    'custom_functions/': '用户本地私有函数目录 (已被 gitignore 忽略)',
    'python/': '跨语言脚本辅助',
    'docs/': '技术设计、机制说明及排障避坑文档',
    'automation/': 'AI 编程自动化检测与同步脚本',
    'base.zsh': '框架总入口（导出 ZFL_HOME 并加载核心模块）',
}

def extract_zsh_desc(filepath):
    """提取 Zsh 函数文件中的元数据描述"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                match = re.search(r'#\?\s*描述:\s*(.*)', line)
                if match:
                    return match.group(1).strip()
    except Exception:
        pass
    return None

def extract_py_desc(filepath):
    """提取 Python 脚本文件首部注释中的描述"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for _ in range(10):
                line = f.readline()
                if not line:
                    break
                match = re.search(r'#\s*(?:描述|description):\s*(.*)', line, re.IGNORECASE)
                if match:
                    return match.group(1).strip()
    except Exception:
        pass
    return None

def parse_existing_readme(readme_content):
    """从现有的 README.md 的结构树中解析并保留已存在的描述信息"""
    match = re.search(r'## 📂 项目结构\s*\n\s*```bash\s*\n(.*?)\n\s*```', readme_content, re.DOTALL)
    if not match:
        return {}
    
    block_content = match.group(1)
    lines = block_content.splitlines()
    
    existing_descs = {}
    active_dirs = {0: ""} # level -> 当前嵌套路径
    
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        
        # 提取注释
        comment = ""
        if '#' in line:
            parts = line.split('#', 1)
            line_part = parts[0]
            comment = parts[1].strip()
        else:
            line_part = line
            
        prefix_chars = ' │├└─'
        name = line_part.strip(prefix_chars).strip()
        if not name:
            continue
            
        level = len(line_part) - len(line_part.lstrip(prefix_chars))
        level = level // 4
        
        if level == 0:
            continue
            
        parent = active_dirs.get(level - 1, "")
        is_dir = name.endswith('/')
        clean_name = name.rstrip('/')
        
        rel_path = os.path.join(parent, clean_name) if parent else clean_name
        
        if is_dir:
            active_dirs[level] = rel_path
            if comment:
                existing_descs[rel_path + '/'] = comment
        else:
            if comment:
                existing_descs[rel_path] = comment
                
    return existing_descs

def parse_readme_doc_list(readme_content):
    """从 README.md 尾部的命令与文档列表中，获取 docs/ 下文档的描述"""
    pattern = re.compile(r'-\s*(?:[^\w\s\[]+)?\s*\[([^\]]+)\]\(([^)]+)\)\s*-\s*(.*)')
    doc_descs = {}
    for line in readme_content.splitlines():
        match = pattern.search(line)
        if match:
            url = match.group(2).strip()
            desc = match.group(3).strip()
            if 'docs/' in url:
                filename = url.split('/')[-1]
                doc_descs[f"docs/{filename}"] = desc
    return doc_descs

def get_dir_files(dir_path):
    """列出目录下符合条件的文件"""
    full_path = os.path.join(workspace_root, dir_path)
    if not os.path.exists(full_path) or not os.path.isdir(full_path):
        return []
        
    files = []
    for f in os.listdir(full_path):
        if not os.path.isfile(os.path.join(full_path, f)):
            continue
            
        # 根据目录类型过滤文件
        if dir_path == 'core':
            if f.endswith('.zsh') or f.endswith('.zsh.example'):
                files.append(f)
        elif dir_path == 'functions':
            if f.endswith('.zsh'):
                files.append(f)
        elif dir_path == 'python':
            if f.endswith('.py'):
                files.append(f)
        elif dir_path == 'docs':
            if f.endswith('.md'):
                files.append(f)
        elif dir_path == 'automation':
            if f.endswith('.py') or f.endswith('.sh'):
                files.append(f)
                
    return sorted(files)

def get_description(rel_path, existing_descs, doc_list_descs):
    """多级 fallback 获取文件描述"""
    abs_path = os.path.join(workspace_root, rel_path.rstrip('/'))
    
    desc = None
    # 1. 尝试从文件本身提取
    if os.path.isfile(abs_path):
        if rel_path.endswith('.zsh'):
            desc = extract_zsh_desc(abs_path)
        elif rel_path.endswith('.py'):
            desc = extract_py_desc(abs_path)
            
    # 2. 尝试从 README 核心命令文档列表中提取 (针对 docs/*.md)
    if not desc and rel_path.startswith('docs/'):
        desc = doc_list_descs.get(rel_path)
        
    # 3. 尝试从历史 README 的目录树中提取
    if not desc:
        desc = existing_descs.get(rel_path)
        
    # 4. 尝试从静态备用字典中提取
    if not desc:
        desc = FALLBACK_DESCS.get(rel_path)
        
    return desc

def generate_tree_lines():
    """生成目录树基础行 (tree_part, rel_path)"""
    tree_lines = []
    tree_lines.append(("zsh/", "zsh/"))
    
    for i, item in enumerate(TOP_LEVEL_ITEMS):
        is_last_top = (i == len(TOP_LEVEL_ITEMS) - 1)
        top_prefix = "└── " if is_last_top else "├── "
        child_indent = "    " if is_last_top else "│   "
        
        if item.endswith('/'):
            dir_name = item.rstrip('/')
            tree_lines.append((f"{top_prefix}{dir_name}/", item))
            
            children = get_dir_files(dir_name)
            for j, child in enumerate(children):
                is_last_child = (j == len(children) - 1)
                child_prefix = "└── " if is_last_child else "├── "
                
                rel_path = os.path.join(dir_name, child)
                tree_lines.append((f"{child_indent}{child_prefix}{child}", rel_path))
        else:
            tree_lines.append((f"{top_prefix}{item}", item))
            
    return tree_lines

def sync():
    readme_path = os.path.join(workspace_root, 'README.md')
    if not os.path.exists(readme_path):
        print(f"Error: README.md not found at {readme_path}")
        return False
        
    with open(readme_path, 'r', encoding='utf-8') as f:
        readme_content = f.read()
        
    # 解析现有描述信息
    existing_descs = parse_existing_readme(readme_content)
    doc_list_descs = parse_readme_doc_list(readme_content)
    
    # 生成新目录树结构
    tree_lines = generate_tree_lines()
    
    # 寻找最大树路径宽度以对齐注释
    max_len = 0
    for tree_part, rel_path in tree_lines:
        if rel_path == 'zsh/':
            continue
        max_len = max(max_len, len(tree_part))
        
    target_col = max(34, max_len + 2)
    
    new_tree_lines = []
    for tree_part, rel_path in tree_lines:
        if rel_path == 'zsh/':
            new_tree_lines.append(tree_part)
            continue
            
        desc = get_description(rel_path, existing_descs, doc_list_descs)
        if desc:
            padding = " " * (target_col - len(tree_part))
            new_tree_lines.append(f"{tree_part}{padding}# {desc}")
        else:
            new_tree_lines.append(tree_part)
            
    new_tree_block = "\n".join(new_tree_lines)
    
    # 替换 README.md 中的内容
    pattern = re.compile(r'(## 📂 项目结构\s*\n\s*```bash\s*\n).*?(\n\s*```)', re.DOTALL)
    
    if not pattern.search(readme_content):
        print("Error: Could not find ## 📂 项目结构 and ```bash block in README.md")
        return False
        
    updated_content = pattern.sub(rf'\g<1>{new_tree_block}\g<2>', readme_content)
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
        
    print("README.md project structure tree has been successfully synchronized.")
    return True

if __name__ == '__main__':
    sync()
