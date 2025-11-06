# Presenter Notes: Benchmarking and Profiling

These notes are designed to help you deliver an effective 1-hour seminar on benchmarking and profiling.

## Presentation Structure

**Total Slides**: 68 (main) + 10 (bonus)  
**Estimated Time**: 60 minutes  
**Format**: Marp slide deck

## Timing Guide

| Section | Slides | Time | Notes |
|---------|--------|------|-------|
| Introduction & Agenda | 1-7 | 5 min | Set expectations, explain why this matters |
| Part 1: Performance Analysis Intro | 8-12 | 5 min | Foundational concepts |
| Part 2: Profiling Tools | 13-28 | 12 min | Core tools demo, most technical |
| Part 3: Benchmarking | 29-38 | 8 min | Practical examples |
| Part 4: Memory Analysis | 39-48 | 8 min | Critical for spatial data |
| Part 5: QGIS-Specific | 49-55 | 7 min | Team-relevant content |
| Part 6: Real Examples | 56-62 | 8 min | Connect to GEEST work |
| Part 7: Best Practices | 63-68 | 5 min | Actionable takeaways |
| Q&A / Discussion | - | 12 min | Interactive, address questions |

**Buffer**: ~10 minutes built into timing for questions and demos

## Key Messages to Emphasize

1. **Always measure before optimizing** - This is the #1 rule
2. **Focus on bottlenecks** - 80/20 principle applies
3. **QGIS-specific optimizations** - Spatial indices, feature requests
4. **Memory matters** - Especially for geospatial data
5. **Automate benchmarking** - Catch regressions early

## Recommended Flow

### Opening (5 min)
- Start with the "Why Performance Matters" slide
- Connect to recent GEEST performance discussions
- Set the agenda clearly

### Middle (40 min)
- **Demo-focused**: Show actual profiling on GEEST code
- **Interactive**: Ask team about their performance pain points
- **Practical**: Use examples from actual workflows

### Closing (15 min)
- Summarize key takeaways
- Discuss next steps for GEEST
- Open Q&A
- Practical exercise suggestion

## Suggested Demos

### Demo 1: Quick cProfile (5 min)
```bash
# Profile a real GEEST operation
cd /path/to/GEEST
python -m cProfile -o profile.prof admin.py build
python -m pstats profile.prof
```

Show the output and identify top time consumers.

### Demo 2: SnakeViz Visualization (3 min)
```bash
snakeviz profile.prof
```

Open in browser, show interactive exploration of the profile.

### Demo 3: Memory Profiler (Optional, 3 min)
Add @profile to a GEEST function and show line-by-line memory usage.

## Interactive Elements

### Poll Questions
1. "Who has profiled Python code before?" (show of hands)
2. "What's the biggest performance issue you've encountered in GEEST?"
3. "Who's familiar with spatial indices?"

### Discussion Points
- **Slide 7**: "What are your performance pain points?"
- **Slide 46**: "Have you encountered memory issues?"
- **Slide 62**: "What should we optimize first in GEEST?"

### Hands-on Exercise (Optional)
If time permits, have team members:
1. Profile a simple function using cProfile
2. Identify the hotspot
3. Share findings (5-7 minutes)

## Adaptation Tips

### For a 30-minute Version
Focus on slides: 1-7, 13-20, 29-32, 49-55, 63-68
- Skip: Detailed tool demos, bonus content
- Keep: Core concepts, QGIS-specific, best practices

### For a 90-minute Version
- Add all bonus slides (69-78)
- Include live coding demos
- Add hands-on exercises
- Extended Q&A and discussion

### For Different Skill Levels

**Junior Developers**: 
- More time on basics (Part 1-2)
- Step-by-step tool installation
- Simple examples first

**Senior Developers**:
- Quick through basics
- Focus on advanced topics (bonus slides)
- Deep dive on specific tools

## Technical Setup

### Before Starting
1. **Install Marp CLI** (if presenting from source):
   ```bash
   npm install -g @marp-team/marp-cli
   marp -s benchmarking-and-profiling.md
   ```

2. **Or use generated PDF**: `benchmarking-and-profiling.pdf`

3. **Have ready**:
   - Terminal for live demos
   - GEEST repository cloned
   - Profiling tools installed
   - Quick reference guide printed/available

### During Presentation
- **Use presenter view** if available
- **Keep terminal ready** for demos
- **Have backup slides** as PDF in case of issues

## Backup Plans

### If demos fail
- Use pre-generated output screenshots
- Walk through the quick reference guide examples
- Focus on concepts rather than live execution

### If running short on time
- Skip bonus slides
- Abbreviate Part 3 (Benchmarking)
- Move to Q&A early

### If running long
- Extend Q&A
- Add bonus content
- Do extended demos

## Post-Presentation

### Follow-up Actions
1. Share slides, quick reference, and presenter notes
2. Set up profiling infrastructure in GEEST
3. Create initial benchmarks for critical paths
4. Schedule follow-up session if interest is high

### Feedback Questions
- "Which tools are you most interested in trying?"
- "What performance issues should we prioritize?"
- "Would you like a follow-up hands-on workshop?"

## Common Questions & Answers

**Q: "Which profiler should I use?"**
A: Start with cProfile for overview, then line_profiler for details. For memory, use memory_profiler. See slide 63.

**Q: "How do I profile QGIS plugins specifically?"**
A: Use the decorator pattern shown in slides 24-25, log to QgsMessageLog.

**Q: "When should I optimize?"**
A: Only after profiling shows a bottleneck. See slide 11 for the workflow.

**Q: "How do spatial indices help?"**
A: They enable O(log n) instead of O(n) spatial queries. Demo on slide 52.

**Q: "What about parallel processing?"**
A: Covered in slides 57-58. Good for independent operations, but has overhead.

## Resources Provided

1. **Main Presentation**: `benchmarking-and-profiling.md`
2. **Quick Reference**: `quick-reference.md`
3. **HTML Version**: `benchmarking-and-profiling.html`
4. **PDF Version**: `benchmarking-and-profiling.pdf`
5. **This Guide**: `PRESENTER-NOTES.md`

## Tips for Success

✅ **DO**:
- Start with why performance matters to the team
- Use real GEEST examples
- Keep demos short and focused
- Encourage questions throughout
- Connect to current work

❌ **DON'T**:
- Get bogged down in tool details
- Assume everyone knows the basics
- Skip the hands-on elements
- Rush through important concepts
- Forget to summarize key points

## Final Checklist

Before presenting:
- [ ] Test presentation in your environment
- [ ] Install/verify profiling tools work
- [ ] Have GEEST repository ready for demos
- [ ] Print or have quick reference available
- [ ] Test projector/screen sharing
- [ ] Have backup PDF ready
- [ ] Prepare your opening question/ice breaker
- [ ] Review timing for your specific audience

## Contact & Contributions

If you present this and have suggestions for improvement, please update these notes or share feedback with the team.

**Good luck with your presentation!** 🎯
