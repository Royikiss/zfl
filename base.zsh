export ZFL_HOME="${0:A:h}"

source "$ZFL_HOME/core/func.zsh"

if [[ -f "$ZFL_HOME/core/usr.zsh" ]]; then
    source "$ZFL_HOME/core/usr.zsh"
fi

source "$ZFL_HOME/core/startup_tasks.zsh"

