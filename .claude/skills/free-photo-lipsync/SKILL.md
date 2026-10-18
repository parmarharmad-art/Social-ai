---
name: free-photo-lipsync
description: Build, debug, and verify a genuinely audio-driven talking-photo/lip-sync pipeline using free open-source models. Use when a user uploads a portrait and expects realistic mouth movement synced to generated Hindi speech, or when SadTalker/MuseTalk/other lip-sync attempts fail. Never substitute a voiceover-only slideshow and never claim success without validating a playable MP4.
---

# Free Photo Lip-Sync — delivery skill

## User acceptance criteria

Treat the task as incomplete until all applicable checks pass:

1. User supplies **one portrait photo**; do not require a separately uploaded narration file if the user asked for photo-only input.
2. The user can enter or approve Hindi script text. Generate speech from that text with a no-key TTS option (try Edge TTS first; use gTTS only as a fallback when network/service works). Do not invent an OpenAI key or use a paid API.
3. An open-source talking-head model animates the portrait to the speech. Audio over a static image, a waveform, zoom/pan, or subtitles alone is **not lip-sync**.
4. Produce an MP4 containing both video and audio streams. Check that file exists, is non-empty, decodes, has a video stream and an audio stream, and its duration is plausible relative to the narration.
5. Clearly distinguish model output validation from human visual quality review. Do not call lip movement “realistic” without watching/inspecting the rendered result.
6. If hosted GPU or model download is unavailable, report the exact blocking error and preserve a reproducible next step. Do not say the project is completed.

## Repository-specific context

- Project: `parmarharmad-art/Social-ai`.
- Existing notebook: `social-content/Free_Hindi_Photo_LipSync_Colab.ipynb`.
- Notebook has been updated to accept one portrait photo, ask for Hindi script (with an editable default), generate speech with no-key Edge TTS, normalize audio, and run upstream SadTalker. This change is committed but the notebook has not yet been executed in Colab; verify it end-to-end before claiming success.
- Upstream model: https://github.com/OpenTalker/SadTalker (open-source Apache-2.0 per its README). SadTalker is an audio-driven single-image talking-head animation model.
- Wav2Lip upstream: https://github.com/Rudrabha/Wav2Lip. Its classic open-source model is for syncing an existing video to audio; do not present it as a direct single-photo animation solution. Check its current license/usage terms before any deployment.
- Existing Colab notebook URL: https://colab.research.google.com/github/parmarharmad-art/Social-ai/blob/main/social-content/Free_Hindi_Photo_LipSync_Colab.ipynb.

## Required engineering workflow

### 1. Inspect before editing

- Read the notebook JSON and any referenced scripts/workflows.
- Identify the exact first failure from the latest logs/traceback. Do not repeatedly switch models without reading the error.
- Check Colab Python, PyTorch, TorchVision, CUDA availability, checkpoint URLs, and required model files. Avoid blindly reinstalling Colab's preinstalled Torch.
- Make changes narrowly and add validation. Never commit generated user photos, audio, tokens, model checkpoints, or other private files.

### 2. Build the photo-only user path

- Notebook UI should request a single image and a Hindi script text (or provide a clearly labelled editable script variable). Audio upload must be optional, not mandatory.
- Generate a narration WAV using a free/no-key TTS path. Normalize it with ffmpeg to mono 16 kHz PCM WAV before model inference.
- If TTS fails, stop with a useful error. Do not silently create a silent video or fall back to a static-photo video.
- Validate image decoding, script non-emptiness, audio duration, and the normalized WAV before inference.

### 3. Run the real animation model

- Prefer the existing SadTalker integration first to avoid unnecessary model churn.
- Use the upstream installation instructions and a compatible runtime. Free Colab GPU is best-effort, not guaranteed; never promise unlimited GPU.
- Download checkpoints only from the upstream project's documented locations. Check each expected checkpoint exists and is plausibly non-empty before inference.
- Use checked subprocess calls and preserve the full first traceback. Do not hide installation or inference errors.
- Do not use paid APIs, API keys, hosted paid inference, or credit-based services for this user unless they explicitly change the free-only constraint.
- Only evaluate an alternative model when the current failure is identified and the alternative actually supports **single-image + audio** animation on a free runtime.

### 4. Verify output

Use ffprobe/ffmpeg or an equivalent decoder to confirm:

- output is a real, non-empty MP4;
- at least one video stream and one audio stream exist;
- video dimensions and duration are readable;
- the output can be decoded without an error;
- output duration is not zero and is consistent with the audio.

Where feasible, render a preview in the notebook and let the user inspect mouth movement. Automated stream checks do not prove visual realism or phoneme-level synchronization.

### 5. Test and report honestly

- Add a small validation/test for the output checker and notebook input flow when feasible.
- Run every available test and inspect the GitHub Actions run, not just the commit status. If the connector cannot trigger Actions, state that limitation and give the exact workflow link.
- Never say “working”, “done”, or “successful” based only on code committed.
- Report separately: code committed, CI run status, MP4 artifact created, and visual lip-sync reviewed.
- When a run fails, include the first actionable error and make the next change based on that error.

## Failure diagnosis map

- **TTS returns no file / network error:** stop; test the TTS service separately, verify the WAV is non-empty and duration > 0.2 s, then retry once. Do not continue with stale audio.
- **TorchVision / BasicSR import error:** inspect installed versions and the exact missing import; apply a narrow compatibility patch only when the traceback supports it.
- **CUDA unavailable / out of memory:** explain that the current free runtime has no usable GPU; offer a smaller supported setting only if the model supports it. Do not imply CPU inference will be fast.
- **Checkpoint missing or suspiciously small:** inspect upstream download output and verify required filenames/sizes before inference.
- **Inference finishes but no MP4:** inspect the final logs and output tree; fail the run rather than creating a placeholder.
- **MP4 has no audio/video stream or cannot decode:** reject it and fix muxing/encoding before delivery.
- **Video plays but mouth barely moves:** inspect source photo quality, face crop, audio quality, and model settings; do not label a voiceover-only result as lip-sync.
- **Free hosted service rejects the input or is busy:** do not keep retrying an incompatible service blindly; use the repo's open-source notebook path and log the actual failure.

## Final response format

Give a short status with four independent lines:
- Skill: created/updated + path
- Code: exact files changed
- Execution: workflow/test status (or not run)
- Output: MP4 link only if a real artifact was produced and verified

Be direct, practical, and honest. The target is a working deliverable, not a reassuring status message.
