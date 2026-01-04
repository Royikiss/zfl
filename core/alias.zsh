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
alias gcc_run='gcc -I. main.cpp -o main && ./main'
alias g++_run='g++ -I. main.cpp -o main && ./main'
alias gclean='rm -f *.o *.out *.exe main'

# alias for System & Network:
alias sysupdate='sudo pacman -Syu'  # Arch 核心包更新
alias update='yay -Syu'             # Arch 全部包更新
alias topcpu='top -o %CPU'       # 按 CPU 排序
alias dfh='df -h'                # 查看磁盘空间
alias topmem='top -o %MEM'       # 按内存排序
