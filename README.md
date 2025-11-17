# Streaming Traffic Redirecter

## Overview

**Streaming Traffic Redirecter or STR** is a modular, production-ready live streaming system built with Docker.  
It integrates Nginx RTMP for ingestion, FFmpeg for transcoding, FastAPI for orchestration and dashboard control, and Prometheus + Grafana for observability.

This stack is designed for developers and system administrators who need a customizable, secure, and scalable foundation for managing live video streams.

---

## Architecture

| Service | Description |
|----------|-------------|
| **nginx-rtmp** | Handles RTMP ingest and HLS distribution. |
| **ffmpeg-worker** | Transcodes incoming streams into multiple bitrates for adaptive streaming. |
| **python-app (FastAPI)** | Manages stream authentication, orchestration, metrics, and dashboard. |
| **proxy** | Reverse proxy with HTTPS support (via Nginx or Traefik). |
| **prometheus** | Collects metrics from FastAPI and system-level data. |
| **grafana** | Visualizes metrics for monitoring and performance tracking. |

---

## Features

- Secure RTMP ingestion with key-based authentication.  
- Multi-bitrate transcoding pipeline using FFmpeg.  
- Web-based dashboard (FastAPI + Jinja templates).  
- Real-time stream updates via WebSocket.  
- Prometheus metrics export and Grafana visualization.  
- HTTPS-ready reverse proxy configuration.  
- Modular architecture allowing independent scaling of services.

---

## Getting Started

### Requirements
- Docker Engine and Docker Compose installed.
- Domain name (for HTTPS support).
- Optional: public server (VPS or bare metal).

### Setup

1. Copy and modify environment configuration:

```bash
cp .env.example .env
```

Example `.env`:
```env
DOMAIN=stream.example.com
ADMIN_USERNAME=admin
ADMIN_PASSWORD=changeme
JWT_SECRET=supersecretkey
HLS_PATH=/data/hls
```

2. Build and launch all services:

```bash
docker compose up -d --build
```

3. Access the following services:
- Dashboard: http://your-domain:8000  
- Prometheus: http://your-domain:9090  
- Grafana: http://your-domain:3000  

RTMP ingest URL example:
```
rtmp://your-domain/live/yourstreamkey
```

---

## Usage

### Add a Stream Key via Dashboard
Go to the admin dashboard and add stream keys directly from the web interface.

### Add via API
```bash
curl -X POST http://your-domain:8000/add_stream   -H "Authorization: Bearer <JWT_TOKEN>"   -d "key=teststream"
```

### Stream Input
Push your video feed using OBS or FFmpeg:
```bash
ffmpeg -re -i input.mp4 -c copy -f flv rtmp://your-domain/live/teststream
```

### Stream Playback
```bash
https://your-domain/hls/teststream/playlist.m3u8
```

Or locally test:
```bash
ffplay https://your-domain/hls/teststream/playlist.m3u8
```

---

## Monitoring and Metrics

- Prometheus metrics endpoint: `http://your-domain:8000/metrics`
- Grafana dashboard: `http://your-domain:3000`

Monitor:
- Active stream count.
- Stream duration.
- Transcoding performance.
- API and system metrics.

---

## Customization

### Modify Transcoding Settings
Edit `ffmpeg/scripts/start_transcode.sh`:
```bash
ffmpeg -i $INPUT -c:v libx264 -b:v 2500k -s 1280x720 -f hls $OUTPUT
```
You can adjust codec, resolution, and bitrate.

### Add Recording Support
Enable automatic recording:
```bash
ffmpeg -i rtmp://localhost/live/$STREAM_KEY -c copy recordings/$STREAM_KEY_%Y%m%d%H%M.mp4
```

### Use Cloud Storage
To output directly to S3 or MinIO:
```bash
-s3 "s3://mybucket/hls/$STREAM_KEY/"
```

### Customize Dashboard UI
Dashboard templates are in `python-app/templates/`.  
Modify these files to adjust branding or embed additional features.

---

## Example Customization Scenarios

### 1. Education Platform
- Integrate user authentication (e.g., OAuth2).  
- Allow each instructor to create unique stream keys.  
- Store recorded lectures automatically.

### 2. Sports Broadcasting
- Enable multi-bitrate for mobile/HD viewers.  
- Embed a scoreboard overlay in FFmpeg filters.  
- Use Grafana for live bitrate and latency monitoring.

### 3. Corporate Streaming
- Add LDAP-based login to FastAPI.  
- Use internal certificate for HTTPS via proxy.  
- Integrate audit logging of streams.

---

## Future Enhancements

- Role-based user system.  
- On-demand stream recording via REST API.  
- Horizontal scaling with Redis job queue for FFmpeg workers.  
- Automatic HTTPS management using Traefik.  
- WebSocket chat integration for live events.  
- Stream expiration and automatic cleanup.  

---

## Troubleshooting

### Check Logs
```bash
docker compose logs -f python-app
```

### Reset Streams Database
```bash
docker exec -it python-app rm data/streams.db
```

### Validate Playback
Use `ffplay` or `VLC` to confirm HLS output works.

---

## License

MIT License.  
Developed for scalable and customizable live streaming infrastructure.

---

## Author Notes

STR is modular and extensible.  
It can be integrated with external systems, scaled horizontally, or customized for diverse streaming applications.
