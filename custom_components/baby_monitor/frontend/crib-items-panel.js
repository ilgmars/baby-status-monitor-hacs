/*
 * crib-items-panel - full-page CCTV wall of the objects seen in the crib,
 * registered by the integration as a sidebar panel ("Crib items"). No manual
 * resource setup: the integration serves this file and registers the panel.
 *
 * Home Assistant passes `hass` on every state change; the panel finds the
 * crib-items sensor by its attributes (an `items` array on a sensor whose id
 * mentions crib_items), so it works whatever the entity ended up named.
 */
class CribItemsPanel extends HTMLElement {
  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _findState() {
    const states = this._hass ? this._hass.states : {};
    let fallback = null;
    for (const [id, st] of Object.entries(states)) {
      if (!id.startsWith("sensor.")) continue;
      const items = st.attributes && st.attributes.items;
      if (Array.isArray(items)) {
        if (id.includes("crib_items")) return st;
        fallback = fallback || st;
      }
    }
    return fallback;
  }

  _render() {
    if (!this._built) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; height: 100%; background: var(--primary-background-color, #111); color: var(--primary-text-color, #eee); font-family: sans-serif; }
          .wall {
            min-height: 100%; padding: 24px; box-sizing: border-box;
          }
          .bar {
            display: flex; justify-content: space-between; align-items: center;
            font-size: 14px; font-weight: bold; text-transform: uppercase;
            margin-bottom: 18px; opacity: .9;
          }
          .grid {
            display: grid; gap: 14px;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: repeat(3, 1fr);
            height: calc(100vh - 100px);
          }
          @media (max-width: 800px) {
            .grid {
              grid-template-columns: 1fr;
              grid-template-rows: auto;
              height: auto;
            }
          }
          .tile {
            border: 1px solid var(--divider-color, #333); border-radius: 6px;
            background: var(--secondary-background-color, #222);
            position: relative; display: flex; align-items: center; justify-content: center;
            text-align: center; padding: 10px; font-size: 16px; word-break: break-word;
            overflow: hidden;
          }
          @media (max-width: 800px) {
            .tile { aspect-ratio: 4 / 3; }
          }
          .tile.empty { color: var(--disabled-text-color, #777); }
          .tile.hazard { border-color: #ff5252; color: #ff8a8a; }
          .tile.warning { border-color: #ffb300; color: #ffd27a; }
          .tile.state-empty { grid-column: 1 / -1; grid-row: 1 / -1; }
          .label { z-index: 2; background: rgba(0,0,0,0.7); color: #fff; padding: 4px 8px; border-radius: 4px; font-weight: 500; }
          .caption {
            position: absolute; left: 0; right: 0; bottom: 0; z-index: 2;
            display: flex; align-items: center; gap: 10px; justify-content: flex-start;
            padding: 8px 10px; box-sizing: border-box;
            background: linear-gradient(transparent, rgba(0,0,0,0.82) 28%, rgba(0,0,0,0.88));
            color: #fff; text-align: left; font-weight: 600;
          }
          .caption-time {
            flex: 0 0 auto; font-family: monospace; font-size: 12px;
            background: rgba(0,0,0,0.7); padding: 2px 5px; border-radius: 4px;
          }
          .caption-text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
          .flag { position: absolute; top: 7px; left: 7px; z-index: 2;
                  font-size: 11px; letter-spacing: 1px; color: #ff5252; background: rgba(0,0,0,0.7); font-weight: bold; padding: 2px 6px; border-radius: 4px; }
          .badge-new { position: absolute; top: 7px; right: 7px; background: #2196F3; color: #fff; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; z-index: 2; }
          .crop-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.85; z-index: 0; }
          .note { margin-top: 16px; font-size: 12px; color: var(--secondary-text-color, #aaa); }
        </style>
        <div class="wall">
          <div class="bar">
            <span class="title">Crib camera &mdash; alerts</span>
          </div>
          <div class="grid"></div>
          <div class="note"></div>
        </div>`;
      this._built = true;
    }

    const st = this._findState();
    const currentItems = st && Array.isArray(st.attributes.items) ? st.attributes.items : [];
    const historyItems = st && Array.isArray(st.attributes.history) ? st.attributes.history : [];
    const items = historyItems.length ? historyItems : currentItems;

    const alertItems = items.filter((it) => it && (it.hazard || it.warning || it.alarm));
    const sortedItems = alertItems.slice().sort((a, b) => {
      const ta = a.first_seen || 0;
      const tb = b.first_seen || 0;
      return tb - ta;
    });

    const pageSize = 9;
    const pageCount = Math.max(1, Math.ceil(sortedItems.length / pageSize));
    const page = Math.floor(Date.now() / 15000) % pageCount;
    let cells = sortedItems.slice(page * pageSize, page * pageSize + pageSize);
    if (cells.length && cells.length < pageSize && sortedItems.length >= pageSize) {
      cells = sortedItems.slice(0, pageSize - cells.length).concat(cells);
    }
    while (cells.length < pageSize) cells.push(null);

    const esc = (s) =>
      String(s).replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    const apiHost = st && st.attributes._api_host ? st.attributes._api_host : "";
    const apiToken = st && st.attributes._api_token ? st.attributes._api_token : "";

    const grid = this.shadowRoot.querySelector(".grid");
    if (!sortedItems.length) {
      grid.innerHTML = `<div class="tile empty state-empty"><span class="label">No warning or alarm items</span></div>`;
    } else {
      grid.innerHTML = cells
        .map((it) => {
          if (!it) return `<div class="tile empty"><span class="label">- - -</span></div>`;
          const alarm = Boolean(it.hazard || it.alarm);
          const alertLabel = alarm ? "ALARM" : "WARNING";
          const alertClass = alarm ? " hazard" : " warning";
          const flag = `<span class="flag">${esc(alertLabel)}</span>`;

          let newBadge = "";
          let timeLabel = "--:--";
          if (it.first_seen) {
            const isNew = (Date.now() / 1000 - it.first_seen) <= 600;
            if (isNew) {
              newBadge = '<span class="badge-new">NEW</span>';
            }
            const d = new Date(it.first_seen * 1000);
            timeLabel = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', hour12: false});
          }

          let imgHtml = "";
          if (it.image_url) {
            imgHtml = `<img class="crop-img" src="${esc(it.image_url)}" onerror="this.style.display='none'">`;
          } else if (it.id && apiHost) {
            const tokenQuery = apiToken ? `?token=${encodeURIComponent(apiToken)}` : "";
            const src = `${apiHost}/api/item-image/${encodeURIComponent(it.id)}${tokenQuery}`;
            imgHtml = `<img class="crop-img" src="${esc(src)}" onerror="this.style.display='none'">`;
          }

          return `<div class="tile${alertClass}">${imgHtml}${newBadge}<div class="caption"><span class="caption-time">${esc(timeLabel)}</span><span class="caption-text">${esc(
            it.item || "object"
          )}</span></div>${flag}</div>`;
        })
        .join("");
    }

    this.shadowRoot.querySelector(".title").innerHTML =
      `Crib camera &mdash; alerts&nbsp;&nbsp;${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit', hour12: false})}`;
    this.shadowRoot.querySelector(".note").textContent = st
      ? `source: ${st.entity_id}${sortedItems.length > 9 ? ` · page ${page + 1}/${pageCount}` : ""}`
      : "waiting for the crib-items sensor (update the Baby Monitor integration)...";
  }
}

customElements.define("crib-items-panel", CribItemsPanel);
