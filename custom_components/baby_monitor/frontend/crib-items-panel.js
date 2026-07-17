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
          .rec { display: flex; align-items: center; gap: 8px; color: #ff5252; }
          .dot { width: 10px; height: 10px; border-radius: 50%; background: #ff5252;
                 animation: blink 1.4s steps(1) infinite; }
          @keyframes blink { 50% { opacity: 0; } }
          @media (prefers-reduced-motion: reduce) { .dot { animation: none; } }
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
          .label { z-index: 2; background: rgba(0,0,0,0.7); color: #fff; padding: 4px 8px; border-radius: 4px; font-weight: 500; }
          .flag { position: absolute; bottom: 7px; left: 0; right: 0; z-index: 2;
                  font-size: 11px; letter-spacing: 1px; color: #ff5252; background: rgba(0,0,0,0.7); font-weight: bold; }
          .badge-new { position: absolute; top: 7px; right: 7px; background: #2196F3; color: #fff; font-size: 10px; font-weight: bold; padding: 2px 6px; border-radius: 4px; z-index: 2; }
          .timestamp { position: absolute; top: 7px; left: 7px; background: rgba(0,0,0,0.7); color: #fff; font-size: 10px; padding: 2px 4px; border-radius: 4px; z-index: 2; }
          .crop-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; opacity: 0.85; z-index: 0; }
          .note { margin-top: 16px; font-size: 12px; color: var(--secondary-text-color, #aaa); }
        </style>
        <div class="wall">
          <div class="bar">
            <span class="title">Crib camera &mdash; objects</span>
            <span class="rec"><span class="dot"></span><span>LIVE</span></span>
          </div>
          <div class="grid"></div>
          <div class="note"></div>
        </div>`;
      this._built = true;
    }

    const st = this._findState();
    const items = st ? st.attributes.items || [] : [];
    
    // Sort items by newest (first_seen descending)
    const sortedItems = items.slice().sort((a, b) => {
      const ta = a.first_seen || 0;
      const tb = b.first_seen || 0;
      return tb - ta;
    });

    const cells = sortedItems.slice(0, 9); // max 9 items
    while (cells.length < 9) cells.push(null);

    const esc = (s) =>
      String(s).replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

    const apiHost = st && st.attributes._api_host ? st.attributes._api_host : "";
    const apiToken = st && st.attributes._api_token ? st.attributes._api_token : "";

    this.shadowRoot.querySelector(".grid").innerHTML = cells
      .map((it) => {
        if (!it) return `<div class="tile empty"><span class="label">- - -</span></div>`;
        const haz = it.hazard ? " hazard" : "";
        const flag = it.hazard ? '<span class="flag">&#9888; HAZARD</span>' : "";
        
        let newBadge = "";
        let timeLabel = "";
        if (it.first_seen) {
          const isNew = (Date.now() / 1000 - it.first_seen) <= 600;
          if (isNew) {
            newBadge = '<span class="badge-new">NEW</span>';
          }
          const d = new Date(it.first_seen * 1000);
          timeLabel = `<span class="timestamp">${d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', hour12: false})}</span>`;
        }

        let imgHtml = "";
        if (it.image_url) {
          imgHtml = `<img class="crop-img" src="${esc(it.image_url)}" onerror="this.style.display='none'">`;
        } else if (it.id && apiHost) {
          const tokenQuery = apiToken ? `?token=${encodeURIComponent(apiToken)}` : "";
          const src = `${apiHost}/api/item-image/${encodeURIComponent(it.id)}${tokenQuery}`;
          imgHtml = `<img class="crop-img" src="${esc(src)}" onerror="this.style.display='none'">`;
        }

        return `<div class="tile${haz}">${imgHtml}${timeLabel}${newBadge}<span class="label">${esc(
          it.item || "object"
        )}</span>${flag}</div>`;
      })
      .join("");

    this.shadowRoot.querySelector(".title").innerHTML =
      `Crib camera &mdash; objects&nbsp;&nbsp;${new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit', hour12: false})}`;
    this.shadowRoot.querySelector(".note").textContent = st
      ? `source: ${st.entity_id}`
      : "waiting for the crib-items sensor (update the Baby Monitor integration)...";
  }
}

customElements.define("crib-items-panel", CribItemsPanel);
