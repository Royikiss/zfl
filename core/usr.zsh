# 在这里填写你自己的配置，这里填写的所有配置会覆盖系统已有的配置

# alias for 'list files':
alias ls='eza --icons'
alias l='eza -lgh --header --git --icons'
alias la='eza -a --icons'
alias lla='eza -algh --header --git --icons'
alias lt='eza --tree --level=2 --icons'
alias ltree='eza --tree --icons'
alias l.='eza -a --icons | grep "^\."'
alias ll.='eza -algh --header --git --icons | grep "^\."'

# alias for 'clear':
alias c='clear'

# alias for gcc/g++:
alias gcc='gcc -I.'
alias g++='g++ -I.'
alias gclean='rm -f *.o *.out *.exe main'

# alias for System & Network:
alias sysupdate='sudo pacman -Syu'  # Arch 核心包更新
alias update='yay -Syu'             # Arch 全部包更新
alias topcpu='top -o %CPU'       # 按 CPU 排序
alias dfh='df -h'                # 查看磁盘空间
alias topmem='top -o %MEM'       # 按内存排序

# rust
alias rc='rustc'

export HTTPS_PROXY=http://127.0.0.1:7897
export HTTP_PROXY=http://127.0.0.1:7897

export PATH=$PATH:~/.local/bin


[[ -s /usr/share/autojump/autojump.zsh ]] && source /usr/share/autojump/autojump.zsh
