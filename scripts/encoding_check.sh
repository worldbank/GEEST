#!/usr/bin/env bash

# SPDX-FileCopyrightText: Tim Sutton
# SPDX-License-Identifier: MIT

# 🤖 Add a precommit hook that ensures that each python
# file is declared with the correct encoding
# -*- coding: utf-8 -*-

add_encoding_to_file() {
    local file="$1"
    local temp_file
    temp_file=$(mktemp)

    # Check if file starts with shebang
    if head -n 1 "$file" | grep -q "^#!"; then
        # Add encoding after shebang
        head -n 1 "$file" >"$temp_file"
        echo "# -*- coding: utf-8 -*-" >>"$temp_file"
        tail -n +2 "$file" >>"$temp_file"
    else
        # Add encoding at the beginning
        echo "# -*- coding: utf-8 -*-" >"$temp_file"
        cat "$file" >>"$temp_file"
    fi

    mv "$temp_file" "$file"
    echo "Added UTF-8 encoding declaration to $file"
}

for file in $(git diff --cached --name-only --diff-filter=ACM | grep -E "\.py$"); do
    if ! grep -q "^#.*coding[:=]\s*utf-8" "$file"; then
        echo "$file is missing UTF-8 encoding declaration"
        read -p "Do you want to add the encoding declaration to $file? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            add_encoding_to_file "$file"
        else
            echo "Skipping $file"
            exit 1
        fi
    fi
done
