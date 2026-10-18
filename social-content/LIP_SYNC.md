# Photo lip-sync (SadTalker adapter)

`social-content/lip_sync_sadtalker.py` is an optional adapter for animating one portrait image from a narration audio file.

## Requirements

- A working checkout of [OpenTalker/SadTalker](https://github.com/OpenTalker/SadTalker)
- SadTalker's required checkpoints/model files and Python dependencies installed
- `ffmpeg`
- A compatible runtime; a GPU is strongly recommended

The upstream project describes the single-image + audio workflow and publishes its source code. The code being open source does **not** mean hosted GPU inference is always free, available, or fast. This repository does not bundle model weights or claim a hosted inference service is configured.

## Run

Create a Hindi audio file first, then run:

```bash
python social-content/lip_sync_sadtalker.py \
  --sadtalker-dir /path/to/SadTalker \
  --image /path/to/portrait.jpg \
  --audio /path/to/hindi-voice.wav \
  --output /path/to/talking-photo.mp4
```

Optional face enhancement:

```bash
python social-content/lip_sync_sadtalker.py \
  --sadtalker-dir /path/to/SadTalker \
  --image /path/to/portrait.jpg \
  --audio /path/to/hindi-voice.wav \
  --enhancer gfpgan \
  --output /path/to/talking-photo.mp4
```

The script checks that the image and audio exist, invokes SadTalker, and errors if it cannot find a non-empty MP4. It does not silently substitute a still-image video.

## Important limitation

This adapter is not yet connected to the current GitHub Actions workflow or the web upload page. GitHub-hosted standard runners do not provide a guaranteed free GPU, so running SadTalker there is not a dependable free inference strategy. No successful lip-sync output is claimed until a real run produces and validates an MP4.

For commercial use, review the upstream model/checkpoint licenses and applicable terms before publishing generated content.
