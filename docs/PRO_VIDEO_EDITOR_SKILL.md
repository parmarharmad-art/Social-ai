# Pro Video Editor — Claude Skill

This repository includes a reusable Claude skill built from the workflow in the supplied “Claude Master Prompt for Editing” PDF. It converts the prompt into a reusable skill folder.

## Add to Claude Code

1. Download or clone this repository.
2. Copy the entire `.claude/skills/pro-video-editor/` folder into your project, or into your Claude Code user skills directory.
3. Ensure the file is named exactly `SKILL.md`.
4. Open Claude Code in that project and provide a raw video file in a location Claude can access.
5. Ask: **“Use the pro-video-editor skill to analyze and edit this video. Preserve my identity and save a separate output.”**

Project-local location:
`.claude/skills/pro-video-editor/SKILL.md`

User-level location (where supported by your Claude Code setup):
`~/.claude/skills/pro-video-editor/SKILL.md`

## Important limitation

A skill is a reusable set of instructions, not a video-rendering engine. Actual editing/export requires Claude to have access to the video file and suitable editing tools or a connected editor. If those are unavailable, the skill instructs Claude to produce a timestamped edit plan rather than claim that it rendered a finished video.

## Workflow covered

- Whole-video analysis and autonomous edit strategy
- First 1–3 second hook
- Context-aware graphics and B-roll
- Accurate, synchronized captions
- Natural retention editing
- Restrained, synchronized sound design
- Preservation of the original person's identity
- Content-matched style and avoidance of over-editing
- Final quality checks and export guidance
