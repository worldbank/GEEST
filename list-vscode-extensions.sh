#!/usr/bin/env bash

# Install required extensions
echo "code --user-data-dir='.vscode' \\"
echo "--profile='geest' \\"
echo "--extensions-dir='.vscode-extensions' . \\"
code --user-data-dir='.vscode' \
--profile='geest' \
--extensions-dir='.vscode-extensions' . \
--list-extensions \
--show-versions | xargs -L 1 echo code --extensions-dir=".vscode-extensions" --install-extension 

echo ""
echo "Paste the above lines into your .vscode.sh and add a back slash at the end of each install-extension line except the last."
