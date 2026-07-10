#!/usr/bin/env python3
import os
import sys
import re

# 全局白名单变量，不会触发变量泄漏警告
GLOBAL_WHITELIST = {
    # Zsh 内建特殊变量
    "path", "fpath", "cdpath", "manpath", "commands", "aliases", "functions",
    "REPLY", "reply", "MATCH", "match", "MBEGIN", "mbegin", "MEND", "mend",
    "CURRENT", "words", "context", "pipestatus", "status", "signals",
    "IFS", "PATH", "HOME", "USER", "PWD", "OLDPWD", "SHLVL", "RANDOM", "SECONDS",
    "COLUMNS", "LINES", "UID", "GID", "PID", "CPUTYPE", "MACHTYPE", "OSTYPE",
    # ZFL 框架自定义全局变量
    "ZFL_HOME", "COLORS", 
    # check_update.zsh 相关的全局配置/状态变量
    "CHECK_UPDATE_CACHE_TTL_SECONDS", "CHECK_UPDATE_PROMPT_POLICY",
    "CHECK_UPDATE_APT_CMD", "CHECK_UPDATE_PACMAN_CMD", "CHECK_UPDATE_YAY_CMD",
    "CHECK_UPDATE_FLATPAK_CMD", "CHECK_UPDATE_AUR_CMD",
}

def strip_heredocs(code):
    """
    清除 Zsh 代码中的 heredocs 内容 (<<EOF ... EOF)，防止其内部的文本和变量定义干扰语法分析。
    """
    # 匹配 heredoc 开始，形如 <<EOF 或 <<'EOF' 或 <<-EOF
    pattern = re.compile(r'<<-?\s*([\'"]?)([a-zA-Z0-9_-]+)\1')
    
    pos = 0
    while True:
        match = pattern.search(code, pos)
        if not match:
            break
        
        delim = match.group(2)
        start_idx = match.start()
        
        # 寻找当前重定向所在行的行尾
        eol = code.find('\n', start_idx)
        if eol == -1:
            pos = start_idx + 2
            continue
        
        # 匹配闭合标识符所在的独立行。如果是 <<-，该行可能包含前导空格/制表符。
        close_pattern = re.compile(r'\n[ \t]*' + re.escape(delim) + r'(?:\n|$)')
        close_match = close_pattern.search(code, eol)
        if not close_match:
            pos = eol + 1
            continue
            
        # 清除 heredoc 的主体内容，只保留闭合行标识符
        code = code[:eol+1] + code[close_match.start():]
        pos = eol + 1
        
    return code

def preprocess_code(content):
    """
    预处理 Zsh 脚本代码：
    1. 提取元数据注释（以 #? 开头）
    2. 移除 heredocs 多行文本
    3. 移除单引号和双引号中的字符串内容（保留结构）
    4. 移除普通注释
    5. 移除大括号变量扩展，防止干扰代码块 {} 大括号配对
    6. 移除子 shell 表达式
    """
    # 提取以 #? 开头的行
    metadata_lines = []
    for line in content.splitlines():
        trimmed = line.strip()
        if trimmed.startswith("#?"):
            metadata_lines.append(trimmed)
        elif trimmed and not trimmed.startswith("#"):
            # 遇到第一个非注释且非空行，停止提取元数据
            break

    # 剥离 heredocs
    code = strip_heredocs(content)

    # 1. 移除双引号字符串 (考虑转义符)
    code = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '""', code)
    # 2. 移除单引号字符串
    code = re.sub(r"'[^']*'", "''", code)
    # 3. 移除大括号变量扩展 ${var}，循环剥离嵌套大括号
    while True:
        next_code = re.sub(r'\$\{[^}]+\}', '$_VAR_', code)
        if next_code == code:
            break
        code = next_code
    # 4. 移除普通注释（排除 #?）
    code = re.sub(r'(?<!#)#(?!\?).*', '', code)
    # 5. 移除子 shell $(...)，处理一层嵌套
    code = re.sub(r'\$\((?:[^)]|\([^)]*\))*\)', '()', code)

    return code, metadata_lines

def extract_functions(preprocessed_content):
    """
    从预处理的代码中提取所有函数定义及其边界
    """
    funcs = []
    pattern = re.compile(r'(?:function\s+)?([a-zA-Z0-9_][a-zA-Z0-9_-]*)\s*(?:\(\s*\))?\s*\{')
    for match in pattern.finditer(preprocessed_content):
        name = match.group(1)
        start_idx = match.start()
        
        brace_start = preprocessed_content.find('{', start_idx)
        if brace_start == -1:
            continue
        
        brace_count = 1
        i = brace_start + 1
        while i < len(preprocessed_content) and brace_count > 0:
            char = preprocessed_content[i]
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
            i += 1
        
        if brace_count == 0:
            body = preprocessed_content[brace_start:i]
            funcs.append({
                'name': name,
                'body': body,
                'start': start_idx,
                'end': i
            })
    return funcs

def get_local_declarations(body_content):
    """
    解析函数体，提取所有 local/typeset/integer/float/readonly 声明的变量
    """
    declared = set()
    pattern = re.compile(r'\b(?:local|typeset|integer|float|readonly|declare)\s+([^;\n]+)')
    for match in pattern.finditer(body_content):
        args_str = match.group(1)
        words = args_str.split()
        for word in words:
            if word.startswith('-'):
                continue
            name = word.split('=', 1)[0]
            name = name.split('[', 1)[0]
            name = re.sub(r'[^a-zA-Z0-9_]', '', name)
            if name:
                declared.add(name)
    return declared

def find_assigned_variables(body_content):
    """
    解析函数体，提取所有发生赋值或写入行为的变量名
    """
    assigned = set()
    
    # 1. 匹配变量赋值: var=, var+=
    # 排除 typeset/local 声明行的赋值，以及命令行选项如 --columns=
    simple_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)(?:\[[^\]]*\])?\+?=')
    for match in simple_pattern.finditer(body_content):
        start = match.start()
        # 过滤命令行选项（如果前导字符是减号 -，如 --columns=）
        if start > 0 and body_content[start - 1] == '-':
            continue
        sol = body_content.rfind('\n', 0, start) + 1
        line_prefix = body_content[sol:start]
        if re.search(r'\b(local|typeset|integer|float|readonly|declare)\b', line_prefix):
            continue
        assigned.add(match.group(1))

    # 2. 匹配 for 循环迭代变量: for var in ...
    for_pattern = re.compile(r'\bfor\s+([a-zA-Z_][a-zA-Z0-9_]*)\b')
    for match in for_pattern.finditer(body_content):
        assigned.add(match.group(1))
    
    # 3. 匹配 read 输入写入变量: read var1 var2
    # 限制 read 关键字前必须为语句起始（如行首，分号后，或 then/else/do 之后），防止匹配数组内 read 字符串
    read_pattern = re.compile(r'(?:^|;|&&|\|\||\||\b(?:then|else|do))\s*\bread\s+([^-;\n][^;\n]*)')
    for match in read_pattern.finditer(body_content):
        vars_str = match.group(1)
        for word in vars_str.split():
            # 遇到管道、重定向、命令连接符停止
            if word in ('>', '<', '>>', '|', ';', '&&', '||') or '<' in word or '>' in word:
                break
            if word.startswith('-'):
                continue
            # 必须是合法的变量名格式才计入，排除数字等
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', word):
                continue
            assigned.add(word)

    # 4. 匹配算术运算赋值: (( x++ )), (( x = val ))
    math_pattern = re.compile(r'\(\(\s*(?:\+\+|--)?\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:\+\+|--|=|\+=|-=|\*=)')
    for match in math_pattern.finditer(body_content):
        assigned.add(match.group(1))

    return assigned

def check_fd3_leak(content):
    """
    检测代码中是否存在后台任务或进程 fork 且未重定向/关闭 FD 3
    """
    leaks = []
    # 匹配 Zsh 中的后台任务运行 &（排除 &&, >&, &>, 以及输入重定向 <& ）以及 coproc
    bg_pattern = re.compile(r'(?<!&)(?<!>)(?<!<)\&(?!&)(?!>)')
    coproc_pattern = re.compile(r'\bcoproc\b')

    lines = content.splitlines()
    for idx, line in enumerate(lines, 1):
        has_bg = bg_pattern.search(line) or coproc_pattern.search(line)
        if has_bg:
            # 检查这行是否包含关闭描述符 3 的指令 "3<&-" 或 "3>&-"
            if "3<&-" not in line and "3>&-" not in line:
                leaks.append((idx, line.strip()))
    return leaks

def check_hardcoded_colors(raw_content):
    """
    检测代码中是否直接硬编码了 ANSI 颜色转移字符，推荐使用 load_color
    """
    hardcoded = []
    # 匹配 \e[ 或 \033[ 格式的硬编码色彩
    color_pattern = re.compile(r'\\033\[[0-9;]*m|\\e\[[0-9;]*m|\\x1b\[[0-9;]*m')
    lines = raw_content.splitlines()
    for idx, line in enumerate(lines, 1):
        # 排除以 # 开头的行
        if line.strip().startswith("#"):
            continue
        if color_pattern.search(line):
            hardcoded.append((idx, line.strip()))
    return hardcoded

def lint_file(file_path):
    """
    执行单文件 Lint 校验，返回错误和警告列表
    """
    errors = []
    warnings = []

    if not os.path.exists(file_path):
        errors.append(f"文件不存在: {file_path}")
        return errors, warnings

    file_name = os.path.basename(file_path)
    func_expected_name = os.path.splitext(file_name)[0]

    # 特殊文件排除：有些辅助脚本不需要满足 Zsh 函数 1:1 规范，例如 core 下的脚本
    is_core_file = "core/" in file_path or "base.zsh" in file_path

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_content = f.read()
    except Exception as e:
        errors.append(f"无法读取文件 {file_path}: {e}")
        return errors, warnings

    # 1. 检测文档配套
    if not is_core_file:
        zfl_home = os.path.dirname(os.path.dirname(os.path.abspath(file_path)))
        doc_path = os.path.join(zfl_home, "docs", f"{func_expected_name}.md")
        if not os.path.exists(doc_path):
            warnings.append(f"【文档缺失】未在 docs/ 目录下找到配套说明文档 docs/{func_expected_name}.md")

    # 2. 检测硬编码颜色字符
    hardcoded_colors = check_hardcoded_colors(raw_content)
    for line_num, line_txt in hardcoded_colors:
        # 排除 core/colors.zsh 自身的定义文件
        if "colors.zsh" not in file_name:
            warnings.append(f"【硬编码色彩】第 {line_num} 行检测到硬编码 ANSI 颜色字符。推荐使用 'load_color' 进行变量渲染。\n  └─ {line_txt}")

    # 预处理代码
    preprocessed_code, metadata = preprocess_code(raw_content)

    # 3. 提取并校验函数定义
    funcs = extract_functions(preprocessed_code)
    if not is_core_file:
        if not funcs:
            errors.append(f"【映射失败】文件内未检测到任何有效的 Zsh 函数定义。文件名应与函数名保持 1:1 映射。")
        else:
            func_names = [f['name'] for f in funcs]
            if func_expected_name not in func_names:
                errors.append(f"【映射失败】未在脚本中找到与文件名同名的主入口函数 '{func_expected_name}()'。")

    # 3.5 校验全局辅助函数的作用域与命名规范
    if not is_core_file:
        for func in funcs:
            func_name = func['name']
            # 判断是否为嵌套定义
            is_func_nested = False
            for other in funcs:
                if other == func:
                    continue
                if other['start'] < func['start'] and func['end'] < other['end']:
                    is_func_nested = True
                    break
            
            # 如果是全局（最外层）函数，且既不是主函数，也不是以 _主函数名 为前缀的合法辅助/补全函数
            if not is_func_nested:
                normalized_expected = func_expected_name.replace('-', '_')
                if func_name != func_expected_name and not func_name.startswith(f"_{func_expected_name}") and not func_name.startswith(f"_{normalized_expected}"):
                    warnings.append(f"【全局函数污染】在文件最外层检测到非规范命名的辅助函数 '{func_name}()'。\n  建议：将其嵌套在主函数 '{func_expected_name}()' 内部定义，或者重命名为 '_{func_expected_name}_xxx' 并在函数退出前使用 'unfunction' 清理。")


    # 4. 逐个函数分析变量泄漏
    for func in funcs:
        func_name = func['name']
        body = func['body']
        
        local_vars = get_local_declarations(body)
        assigned_vars = find_assigned_variables(body)
        
        # 寻找未在 local 声明且不在全局白名单中的变量
        leaks = []
        for var in assigned_vars:
            # 排除以 _ 字符开头的部分系统临时内部变量，以及动态作用域的 func_meta_* 返回变量
            if var.startswith('_') and len(var) > 1:
                continue
            if var.startswith('func_meta_'):
                continue
            if var not in local_vars and var not in GLOBAL_WHITELIST:
                leaks.append(var)
        
        if leaks:
            warnings.append(f"【变量泄漏】函数 '{func_name}()' 中以下变量未声明为 'local'，存在污染用户 Shell 全局变量的风险：\n  └─ 泄漏变量: {', '.join(sorted(leaks))}")

    # 5. 检测后台进程的 FD 3 泄露隐患
    fd3_leaks = check_fd3_leak(preprocessed_code)
    for line_num, line_txt in fd3_leaks:
        warnings.append(f"【FD 3 泄漏风险】第 {line_num} 行检测到后台任务，可能导致文件描述符 3 泄露到子进程从而锁死父 Shell。\n  建议：在命令尾部加上 '3<&-' 以安全关闭它。\n  └─ 存在隐患命令: {line_txt}")

    return errors, warnings

def main():
    if len(sys.argv) < 2:
        print("Usage: zfl_lint.py <file1.zsh> <file2.zsh> ...")
        sys.exit(1)

    exit_code = 0
    files_to_check = sys.argv[1:]

    # 终端 ANSI 色彩配置
    RED = "\033[1;31m"
    GREEN = "\033[1;32m"
    YELLOW = "\033[1;33m"
    CYAN = "\033[1;36m"
    RESET = "\033[0m"

    for file_path in files_to_check:
        print(f"{CYAN}正在校验: {file_path}{RESET}")
        errors, warnings = lint_file(file_path)

        if not errors and not warnings:
            print(f"  {GREEN}[✓] 完美通过！未检测到任何代码规范问题。{RESET}")
        else:
            for err in errors:
                print(f"  {RED}[✗] 错误: {err}{RESET}")
                exit_code = 1
            for warn in warnings:
                print(f"  {YELLOW}[!] 警告: {warn}{RESET}")
                # 将警告也视作规范不通过（让 exit_code = 1，利于 CI 流程）
                exit_code = 1

        print()

    sys.exit(exit_code)

if __name__ == "__main__":
    main()
