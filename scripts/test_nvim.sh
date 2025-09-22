#!/usr/bin/env bash
echo "Testing Neovim functionality..."

# Test basic startup
echo "1. Testing basic startup..."
if vim --headless +"lua print('Basic startup: OK')" +qa 2>/dev/null; then
    echo "✓ Basic startup works"
else
    echo "✗ Basic startup failed"
fi

# Test plugin loading
echo "2. Testing plugin loading..."
if vim --headless +"lua require('lazy').check()" +qa 2>/dev/null; then
    echo "✓ Plugins load successfully"
else
    echo "✗ Plugin loading failed"
fi

# Test LSP
echo "3. Testing LSP..."
if vim --headless +"lua local clients = vim.lsp.get_active_clients(); print('LSP clients available: ' .. #clients)" +qa 2>/dev/null; then
    echo "✓ LSP accessible"
else
    echo "✗ LSP not accessible"
fi

echo "Test complete!"
