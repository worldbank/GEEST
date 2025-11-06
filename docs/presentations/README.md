# GEEST Presentations

This directory contains presentation materials for the GEEST project.

## Available Presentations

### Benchmarking and Profiling

**File**: `benchmarking-and-profiling.md`  
**Format**: Marp (Markdown Presentation Ecosystem)  
**Duration**: ~1 hour  
**Audience**: Development team

A comprehensive presentation covering:
- Profiling tools and techniques for Python
- Benchmarking strategies and best practices
- Memory analysis and optimization
- QGIS-specific performance considerations
- Real-world examples applicable to GEEST
- Hands-on demonstrations and exercises

## Viewing the Presentations

### Option 1: Marp CLI (Recommended)

Install Marp CLI:

```bash
npm install -g @marp-team/marp-cli
```

View the presentation:

```bash
# Generate HTML
marp benchmarking-and-profiling.md -o benchmarking-and-profiling.html

# Generate PDF
marp benchmarking-and-profiling.md -o benchmarking-and-profiling.pdf --allow-local-files

# Live preview with auto-reload
marp -s benchmarking-and-profiling.md
```

### Option 2: Marp for VS Code

1. Install the [Marp for VS Code](https://marketplace.visualstudio.com/items?itemName=marp-team.marp-vscode) extension
2. Open `benchmarking-and-profiling.md` in VS Code
3. Click the "Open Preview to the Side" button or press `Ctrl+K V`
4. Use the preview to navigate slides

### Option 3: Online Marp Editor

1. Go to [Marp Web](https://web.marp.app/)
2. Copy and paste the content of `benchmarking-and-profiling.md`
3. View and present directly in the browser

### Option 4: Export for PowerPoint

If you need PowerPoint format:

```bash
# Export as PPTX
marp benchmarking-and-profiling.md -o benchmarking-and-profiling.pptx
```

## Presenting Tips

### Navigation
- **Next slide**: Arrow Right, Space, or Page Down
- **Previous slide**: Arrow Left or Page Up
- **Full screen**: F11 (in browser) or F5 (in PDF viewer)

### Presenter Mode
When using HTML output, you can add presenter notes:

```markdown
---
<!-- This is a presenter note -->
Content visible to audience
---
```

### Customization

The presentation uses Marp's default theme with custom styling. To modify:

1. Edit the frontmatter in the markdown file:
```yaml
---
marp: true
theme: default  # or custom theme name
paginate: true
---
```

2. Adjust the inline CSS in the style block

3. Create a custom theme (see [Marp themes documentation](https://marpit.marp.app/theme-css))

## Adapting the Presentation

### For Different Audiences

**For Management** (30 min version):
- Focus on slides: 1-6, 15-18, 47-54, 66-68

**For Junior Developers** (2 hour version):
- Add more hands-on exercises after slides 46, 55, 65
- Include live coding demonstrations

**For Technical Deep-Dive**:
- Add bonus slides (69+)
- Extend examples with actual GEEST code

### Adding Your Own Content

To add slides:
1. Insert between `---` separators
2. Use markdown formatting
3. Add code blocks with syntax highlighting
4. Include images with `![alt text](path/to/image.png)`

Example:
```markdown
---

## Your New Slide Title

- Bullet point 1
- Bullet point 2

\`\`\`python
# Your code example
def example_function():
    return "Hello, GEEST!"
\`\`\`

---
```

## Additional Resources

- [Marp Documentation](https://marp.app/)
- [Marpit Framework](https://marpit.marp.app/)
- [Markdown Guide](https://www.markdownguide.org/)

## Contributing

To add new presentations:
1. Create a new `.md` file in this directory
2. Add Marp frontmatter
3. Update this README with presentation details
4. Submit a pull request

## License

These presentations are part of the GEEST project and follow the same license terms.
