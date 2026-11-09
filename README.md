# ReoFTPView

A lightweight, dedicated CCTV web viewer and retention manager designed specifically for **Reolink** (and other FTP-uploading security cameras).

Unlike heavy NVRs or fragile on-the-fly HLS transcoding dashboards, **ReoFTPView**:
1. **Direct HTTP Range Video Streaming:** Serves `.mp4` camera recordings directly using native HTML5 HTTP 206 Range requests. Instant playback, smooth seeking, zero CPU transcoding, and zero `.m3u8` 404 errors.
2. **Native Retention Management:** Automatically deletes recordings older than `RETENTION_DAYS` (default 30 days) and cleans up empty folders in the background.
3. **Sleek Dark Dashboard:** Camera switcher, date navigation ("Today", "Yesterday", or calendar selector), video thumbnail grid, file size badges, and clip download/delete options.
4. **Enhanced Modal Player:** Built-in speed switcher (0.5x, 1x, 2x, 4x), previous/next clip navigation, and keyboard shortcuts (`Esc` to close, `←` / `→` for prev/next).

---

## Quick Start with Docker Compose

```yaml
version: "3.9"

services:
  reoftpview:
    container_name: reoftpview
    build: .
    restart: unless-stopped
    ports:
      - "5000:5000"
    environment:
      - RECORDINGS_PATH=/recordings
      - RETENTION_DAYS=30          # Auto-deletes footage older than 30 days
      - CLEANUP_INTERVAL_HOURS=6   # Runs retention cleanup every 6 hours
    volumes:
      - /mnt/raid/camera/doorbell_ftp:/recordings
```

Web interface reachable at: `http://<YOUR_IP>:5000`

---

## Git Setup (For Portainer Git Deployment)

To deploy directly via Portainer's **Repository** feature:

1. Create a repository on GitHub / Gitea (e.g. `reoftpview`).
2. Inside `C:\src\reoftpview`, run:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of ReoFTPView"
   git branch -M main
   git remote add origin https://github.com/<your-user>/reoftpview.git
   git push -u origin main
   ```
3. In **Portainer**:
   * Stacks $\rightarrow$ **Add stack** $\rightarrow$ Select **Repository**.
   * Enter your Git Repository URL.
   * Target branch: `main`
   * Compose path: `docker-compose.yml`
   * Click **Deploy the stack**.
