/*
 * crib-items-card - a CCTV-style grid of the objects the monitor has seen in the crib.
 *
 * Reads the `items` attribute of the "Crib items [LLM]" sensor (an array of
 * {item, hazard}) published by baby/status/scene_items and lays each one out as a
 * little surveillance tile: green-on-black monospace, corner brackets, a blinking
 * REC dot, and a red HAZARD frame for anything flagged dangerous.
 *
 * Install: copy to <config>/www/crib-items-card.js, add it as a dashboard resource
 * (Settings -> Dashboards -> ... -> Resources -> Add, URL /local/crib-items-card.js,
 * type JavaScript module), then use the card config in examples/dashboard.yaml.
 *
 * No build step, no dependencies - vanilla custom element.
 */
class CribItemsCard extends HTMLElement {
  setConfig(config) {
    if (!config.entity) throw new Error("crib-items-card: 'entity' is required");
    this._config = config;
    this._min = config.min_tiles ?? 6;
    this._built = false;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  getCardSize() {
    return 3;
  }

  _render() {
    if (!this._hass || !this._config) return;
    const st = this._hass.states[this._config.entity];
    const items = (st && st.attributes && st.attributes.items) || [];

    if (!this._built) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.innerHTML = `
        <style>
          :host { display: block; }
          .cam {
            background: #0a0e0a; border: 1px solid #1e2a1e; border-radius: 8px;
            padding: 12px; font-family: "Courier New", monospace; color: #4fdf6a;
            position: relative; overflow: hidden;
          }
          .cam::after {
            content: ""; position: absolute; inset: 0; pointer-events: none;
            background: repeating-linear-gradient(
              0deg, rgba(0,0,0,0) 0px, rgba(0,0,0,0) 2px,
              rgba(0,0,0,0.18) 3px, rgba(0,0,0,0) 4px);
          }
          .bar {
            display: flex; justify-content: space-between; align-items: center;
            font-size: 12px; letter-spacing: 1px; text-transform: uppercase;
            margin-bottom: 10px; opacity: .85;
          }
          .rec { display: flex; align-items: center; gap: 6px; color: #ff5252; }
          .dot {
            width: 9px; height: 9px; border-radius: 50%; background: #ff5252;
            animation: blink 1.4s steps(1) infinite;
          }
          @keyframes blink { 50% { opacity: 0; } }
          .grid {
            display: grid; grid-template-columns: repeat(var(--cols, 3), 1fr); gap: 8px;
          }
          .tile {
            aspect-ratio: 4 / 3; border: 1px solid #1e2a1e; border-radius: 5px;
            background: radial-gradient(ellipse at center, #12180f 0%, #070a07 100%);
            position: relative; display: flex; align-items: center; justify-content: center;
            text-align: center; padding: 6px; font-size: 13px; word-break: break-word;
          }
          .tile.empty { color: #24361f; }
          .tile.hazard { border-color: #ff5252; color: #ff8a8a; }
          .tile .corner {
            position: absolute; width: 9px; height: 9px; border: 2px solid #4fdf6a; opacity: .6;
          }
          .tile.hazard .corner { border-color: #ff5252; }
          .c0 { top: 4px; left: 4px; border-right: 0; border-bottom: 0; }
          .c1 { top: 4px; right: 4px; border-left: 0; border-bottom: 0; }
          .c2 { bottom: 4px; left: 4px; border-right: 0; border-top: 0; }
          .c3 { bottom: 4px; right: 4px; border-left: 0; border-top: 0; }
          .label { z-index: 1; }
          .flag {
            position: absolute; bottom: 4px; left: 0; right: 0; font-size: 10px;
            letter-spacing: 1px; color: #ff5252;
          }
        </style>
        <div class="cam">
          <div class="bar">
            <span class="title"></span>
            <span class="rec"><span class="dot"></span><span>REC</span></span>
          </div>
          <div class="grid"></div>
        </div>`;
      this._built = true;
    }

    const cols = this._config.columns ?? 3;
    this.shadowRoot.querySelector(".grid").style.setProperty("--cols", cols);
    this.shadowRoot.querySelector(".title").textContent =
      this._config.title ?? "Crib camera - objects";

    const cells = items.slice();
    while (cells.length < this._min) cells.push(null); // pad to a full grid

    const now = new Date().toLocaleTimeString();
    this.shadowRoot.querySelector(".grid").innerHTML = cells
      .map((it) => {
        if (!it) {
          return `<div class="tile empty">
            ${corners()}<span class="label">- - -</span></div>`;
        }
        const haz = it.hazard ? " hazard" : "";
        const flag = it.hazard ? `<span class="flag">&#9888; HAZARD</span>` : "";
        return `<div class="tile${haz}">
          ${corners()}<span class="label">${esc(it.item || "object")}</span>${flag}</div>`;
      })
      .join("");

    // timestamp in the title bar, CCTV-style
    this.shadowRoot.querySelector(".title").textContent =
      `${this._config.title ?? "Crib camera - objects"}  ${now}`;

    function corners() {
      return `<i class="corner c0"></i><i class="corner c1"></i>
              <i class="corner c2"></i><i class="corner c3"></i>`;
    }
    function esc(s) {
      return String(s).replace(/[&<>"']/g, (c) =>
        ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
    }
  }
}

customElements.define("crib-items-card", CribItemsCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: "crib-items-card",
  name: "Crib Items (CCTV)",
  description: "CCTV-style grid of objects the baby monitor has seen in the crib.",
});
