function prepend_path_dir --argument-names dir
    if not test -d "$dir"
        return
    end

    set -l new_path "$dir"
    for entry in $PATH
        if test -n "$entry"; and test "$entry" != "$dir"
            set new_path $new_path "$entry"
        end
    end

    set -gx PATH $new_path
end

set -l clean_path
for entry in $PATH
    if test "$entry" != "$HOME/.local/share/omarchy/bin"
        set clean_path $clean_path "$entry"
    end
end
set -gx PATH $clean_path

for dir in "$HOME/.local/share/mise/shims" "$HOME/shims"
    prepend_path_dir "$dir"
end
prepend_path_dir "$HOME/.local/bin"
functions -e prepend_path_dir
