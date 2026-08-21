#? name: link_skills
#? description: Selectively symlink skills from ~/.agents/skills/ into .agents/skills/ of current project (Alias for mskill)
#? author: Royi
#? version: 1.1.0
#? deps: python3
#? usage: link_skills [options] [skill_name/group_name...]
#? example: link_skills startup

_link_skills() {
    _mskill "$@"
}

link_skills() {
    mskill "$@"
}
