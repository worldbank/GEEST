-- Test script to verify Neovim configuration loads properly
print("🎯 GEEST Neovim Configuration Test")
print("=======================================")

-- Test basic configuration
if vim.g.mapleader == " " then
  print("✅ Leader key set correctly")
else
  print("❌ Leader key not set")
end

-- Test if lazy.nvim is available
local lazy_available = pcall(require, "lazy")
if lazy_available then
  print("✅ Lazy.nvim plugin manager loaded")

  -- Check if some key plugins are installed
  local plugins_to_check = {
    "alpha",
    "telescope",
    "nvim-treesitter",
    "nvim-lspconfig",
    "nvim-cmp",
    "gitsigns"
  }

  print("\n📦 Plugin Status:")
  for _, plugin in ipairs(plugins_to_check) do
    local ok = pcall(require, plugin)
    if ok then
      print("  ✅ " .. plugin)
    else
      print("  ⏳ " .. plugin .. " (needs installation)")
    end
  end
else
  print("❌ Lazy.nvim not available")
end

print("\n🔧 Configuration files:")
local config_files = {
  "config.options",
  "config.keymaps",
  "config.autocmds"
}

for _, config in ipairs(config_files) do
  local ok = pcall(require, config)
  if ok then
    print("  ✅ " .. config)
  else
    print("  ❌ " .. config)
  end
end

print("\n💡 To start with dashboard:")
print("   nvim --cmd \"set rtp+=./.nvim\"")
print("\n🚀 Ready to code!")
