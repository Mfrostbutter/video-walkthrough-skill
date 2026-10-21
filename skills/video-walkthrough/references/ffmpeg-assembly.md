# ffmpeg assembly: the filter graph, the numbers, the checks

## Per-scene mux

Inputs: `0` the clip (silent h264, trimmed at `start()`), `1` the scene WAV, `2` the lower-third PNG (optional).

```
[0:v]tpad=stop_mode=clone:stop_duration=60,trim=duration=DUR,setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.5[v0]
[2:v]format=rgba,fade=t=in:st=0.8:d=0.4:alpha=1,fade=t=out:st=DUR-2.4:d=0.4:alpha=1[lt]
[v0][lt]overlay=x=64:y=H-h-64:shortest=0[v]
[1:a]adelay=600|600,apad,atrim=duration=DUR[a]
```

- `DUR = VO_LEAD + vo_seconds + TAIL` (0.6 + VO + 1.6). The clip was recorded to at least VO + 2.0 s after
  `start()`, so `tpad` only matters when a capture ran short; it clones the last frame rather than failing.
- `fade=t=in` on the first scene only. Scene cuts are hard; the cards animate themselves on load.
- The lower third fades in at 0.8 s and out 2 s before the scene ends, so it never sits over a cut. Position
  bottom-left at 64 px; move it if the app's UI has content there.
- `adelay` shifts the VO by `VO_LEAD`; `apad` + `atrim` give every part the same length as its video, which
  concat with `-c copy` needs. Encode `-c:v libx264 -pix_fmt yuv420p -r 30 -c:a aac -b:a 160k -ar 48000`.
- Review: `-preset veryfast -crf 23`. Final: `-preset slow -crf 18`. On an M-series laptop a 4-minute cut
  renders in about 1 minute at review and 3 to 4 at final. Different output names so a player holding the
  review file never blocks the final write.

## Concat and outro

Parts are listed in `concat.txt` and joined with `-f concat -safe 0 -c copy -movflags +faststart`. Every part
must share codec, resolution, frame rate and audio layout, which the per-scene encode guarantees. The outro is a
5 s loop of `overlays/outro.png` with an `anullsrc` silent track and a 0.8 s fade to black.

## Checks before calling a cut done

- `ffprobe -show_entries format=duration:stream=codec_name,width,height` on the output: h264 1920x1080 plus aac.
- Frame grid of the cut: `FINAL=1 QUALITY=review python scripts/frames.py` (six frames, 3x2). Look at it.
- VO lead on one scene: `ffmpeg -i out/work-<cut>/scene_02.mp4 -af silencedetect=n=-40dB:d=0.3 -f null -`
  should report a first silence ending near 0.6 s.
- Per-clip grids before assembly: `python scripts/frames.py` after every capture run. A failed save shows as a
  toast in the last frame; a wrong page shows in the first.

## Inserting or re-shooting scenes

- Re-shoot one scene: `CUT=admin python scripts/capture.py 07`; `clips.json` merges, re-assemble.
- Insert before the closing card: rename the closing scene's files to the next id (`vo/<cut>/09.mp3` to
  `10.mp3`, the content-addressed wav likewise, the manifest `id`, `captures/<cut>/scene_09.mp4` to
  `scene_10.mp4`, the `clips.json` key), then add the new `## 09` section to the script, its lower third, run
  `run_vo.sh <cut>` (only 09 is billed), `render_overlays.py`, `capture.py 09`, `frames.py`, assemble.
- Changed narration on an existing scene: edit the section, rerun `run_vo.sh` (hash skip regenerates that scene
  only), re-shoot if the beats moved, re-assemble.

## Traps met so far

- A fake cursor parked in the corner of every card scene: call `hide_cursor()` on cards.
- A capture that recorded the app's home page: the `goto` raced the post-login redirect. `open_page` waits for
  `networkidle`, then navigates and waits for the page's anchor selector, three tries.
- A scene recorded while the capture script was being edited ran the old code; the module is loaded once per run.
- `httpx` does not send cookies back to a dotless host such as `localhost`; set the session cookie header
  yourself when a verification script logs into the subject app.
- An n8n credential field does not switch to expression mode when `{{` is typed into it; hover the field and
  click its Expression toggle first, then type into the inline editor, which auto-closes the braces.
