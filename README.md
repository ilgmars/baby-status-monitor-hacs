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
- LLM scene narration (needs `SCENE_LLM=on` on the server): "Latest status" (one-line
  description of what is going on, with a time stamp attribute), "Danger" (binary: immediate hazards - loose objects, bags, coins, blocked airway,
  stuck limb, climbing) and "Warning" (binary: worth a look - stain/wet spot, asleep
  on tummy), each with a reason sensor that clears together with the flag, plus "Baby position"
  (back/tummy/side/sitting/standing), "Face covered", and "Baby visible"

Health self-diagnostics: "Sys LLM health" (ok/error/off - the scene narrator and its
proxy; last success + error text in attributes) and "Sys audio health" (ok/silent - the
cry detector's audio feed). "Camera online" covers the video stream as before.

## Dashboard

`examples/dashboard.yaml` is a ready-made Lovelace view (live stream on top, one
tile per status) - replace the placeholder credentials/host and adjust entity ids.
Entity names carry a source tag: `[ML]` = local detectors, `[LLM]` = scene narration.

### Crib-items CCTV card

`www/crib-items-card.js` is a small dependency-free custom card that renders the
objects the monitor has seen in the crib (the "Crib items [LLM]" sensor) as a
CCTV-style grid - green-on-black tiles, a blinking REC dot, and a red HAZARD frame
for anything flagged dangerous. To use it:

1. Copy `www/crib-items-card.js` to your HA `config/www/` folder.
2. Add it as a resource: Settings -> Dashboards -> (top-right menu) Resources ->
   Add resource, URL `/local/crib-items-card.js`, type "JavaScript module".
3. The card is already wired in `examples/dashboard.yaml`
   (`type: custom:crib-items-card`).

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
