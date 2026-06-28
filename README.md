# Baby Status Monitor for Home Assistant

A Home Assistant integration for the self-hosted Baby Status Monitor. It reads the
dashboard's HTTP API and creates entities for breathing, presence, crying, movement,
sleep, and a live camera. No MQTT, no broker, no bridge.

## Entities

- Respiration rate (bpm)
- Baby present
- Crying, plus a cry-reason sensor (hungry, tired, belly pain, and so on)
- Movement
- Sleep state
- Breathing detected, and a breathing-detection-degraded flag
- Camera online
- A Live camera with real video from the go2rtc restream

## Install

### HACS

1. In HACS open the top-right menu and choose Custom repositories.
2. Add this repository's URL with the category Integration.
3. Install "Baby Status Monitor", then restart Home Assistant.

### Manual

Copy `custom_components/baby_monitor` into your Home Assistant `config/custom_components/`
folder so you have `config/custom_components/baby_monitor/manifest.json`, then restart
Home Assistant.

## Configure

Go to Settings, Devices & Services, Add Integration, and pick "Baby Status Monitor". Fill in:

- Dashboard URL, for example `https://192.168.1.10`
- API token: the `API_TOKEN` value from the server's `.env` (run `grep ^API_TOKEN= .env`
  on the server and copy the value after the `=`)
- Live stream URL: leave blank to use the go2rtc restream at `rtsp://<host>:8554/cam`; set
  it if your camera has a different name or you want another source

The integration polls every few seconds and accepts the self-signed LAN certificate, so a
local HTTPS dashboard works without extra setup.

## License

MIT
