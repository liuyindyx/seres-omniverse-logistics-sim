"""
Records the ~3.5-minute 1920x1080 3D Omniverse Digital Twin Guided Presentation Video
by stepping window.setDirectorTime(t) over a persistent Chrome DevTools Protocol (CDP)
WebSocket connection and piping frames directly into FFmpeg with the neural voiceover.
"""

import os
import sys
import time
import json
import base64
import shutil
import subprocess
import urllib.request
import websocket
import imageio_ffmpeg


def record_video():
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    docs_dir = os.path.join(project_root, "docs")
    video_dir = os.path.join(docs_dir, "video")
    os.makedirs(video_dir, exist_ok=True)

    manifest_path = os.path.join(docs_dir, "video_assets", "presentation_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    total_sec = float(manifest["total_duration_sec"])
    master_wav = os.path.join(docs_dir, "video_assets", "master_narration.wav")
    output_mp4 = os.path.join(video_dir, "Seres_Omniverse_3D_Logistics_Presentation.mp4")

    chrome_exe = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    profile_dir = os.path.join(docs_dir, ".chrome_video_profile")
    if os.path.exists(profile_dir):
        shutil.rmtree(profile_dir, ignore_errors=True)
    os.makedirs(profile_dir, exist_ok=True)

    port = 9244
    chrome_cmd = [
        chrome_exe,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu-sandbox",
        "--enable-webgl",
        "--ignore-gpu-blocklist",
        f"--user-data-dir={profile_dir}",
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        "--window-size=1920,1080",
        "--hide-scrollbars",
        "http://localhost:8765/index.html"
    ]

    print(f"[Recorder] Launching headless Chrome on CDP port {port}...")
    chrome_proc = subprocess.Popen(chrome_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        # Wait for CDP endpoint to become ready
        ws_url = None
        for _ in range(30):
            time.sleep(0.3)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json") as resp:
                    tabs = json.loads(resp.read().decode("utf-8"))
                    for tab in tabs:
                        if tab.get("type") == "page" and "webSocketDebuggerUrl" in tab:
                            ws_url = tab["webSocketDebuggerUrl"]
                            break
                if ws_url:
                    break
            except Exception:
                pass

        if not ws_url:
            raise RuntimeError("Failed to connect to Chrome DevTools Protocol WebSocket.")

        print(f"[Recorder] Connected to CDP WebSocket: {ws_url}")
        ws = websocket.create_connection(ws_url, timeout=30)
        msg_id = 0

        def cdp_call(method, params=None):
            nonlocal msg_id
            msg_id += 1
            payload = {"id": msg_id, "method": method, "params": params or {}}
            ws.send(json.dumps(payload))
            while True:
                raw = ws.recv()
                data = json.loads(raw)
                if data.get("id") == msg_id:
                    return data.get("result", {})

        # Lock exact 1920x1080 viewport
        cdp_call("Page.enable")
        cdp_call("Runtime.enable")
        cdp_call("Emulation.setDeviceMetricsOverride", {
            "width": 1920,
            "height": 1080,
            "deviceScaleFactor": 1,
            "mobile": False
        })

        # Wait for Three.js scene and setDirectorTime to be ready
        print("[Recorder] Waiting for Three.js 3D WebGL scene initialization...")
        for _ in range(40):
            res = cdp_call("Runtime.evaluate", {
                "expression": "typeof window.setDirectorTime === 'function'",
                "returnByValue": True
            })
            if res.get("result", {}).get("value") is True:
                break
            time.sleep(0.2)
        time.sleep(1.0)

        # Warm-up frame at t=0
        cdp_call("Runtime.evaluate", {"expression": "window.setDirectorTime(0.0)"})
        time.sleep(0.3)

        fps = 5.0
        total_frames = int(total_sec * fps)
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        ffmpeg_cmd = [
            ffmpeg_exe,
            "-y",
            "-f", "image2pipe",
            "-vcodec", "mjpeg",
            "-r", str(fps),
            "-i", "-",
            "-i", master_wav,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-r", "24",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-shortest",
            output_mp4
        ]

        print(f"[Recorder] Capturing {total_frames} 3D WebGL frames ({total_sec:.1f}s @ {fps} FPS -> 24 FPS MP4)...")
        ffmpeg_proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        t0 = time.time()
        for frame_idx in range(total_frames):
            cur_t = round(frame_idx / fps, 3)
            cdp_call("Runtime.evaluate", {"expression": f"window.setDirectorTime({cur_t})"})
            shot = cdp_call("Page.captureScreenshot", {"format": "jpeg", "quality": 88})
            img_bytes = base64.b64decode(shot["data"])
            ffmpeg_proc.stdin.write(img_bytes)

            if frame_idx % 50 == 0 or frame_idx == total_frames - 1:
                elapsed = time.time() - t0
                rate = (frame_idx + 1) / max(0.1, elapsed)
                print(f"  -> Frame {frame_idx+1}/{total_frames} (sim t={cur_t:.1f}s/{total_sec:.1f}s) | {rate:.1f} fps capture")

        ffmpeg_proc.stdin.close()
        ffmpeg_proc.wait()
        ws.close()

        print(f"\n[Recorder] Video successfully encoded: {output_mp4} ({os.path.getsize(output_mp4) / (1024*1024):.2f} MB)")

    finally:
        chrome_proc.terminate()
        try:
            chrome_proc.wait(timeout=3)
        except Exception:
            chrome_proc.kill()
        shutil.rmtree(profile_dir, ignore_errors=True)


if __name__ == "__main__":
    record_video()
