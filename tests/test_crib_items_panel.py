"""Smoke tests for the crib-items sidebar panel."""

import json
import subprocess
import textwrap
from pathlib import Path


def test_history_rotation_does_not_render_sparse_page():
    panel = Path("custom_components/baby_monitor/frontend/crib-items-panel.js")
    script = r"""
      const fs = require("fs");
      const vm = require("vm");
      const code = fs.readFileSync(process.argv[1], "utf8");
      let PanelClass;

      class BaseElement {
        attachShadow() {
          const nodes = {};
          this.shadowRoot = {
            querySelector(sel) {
              if (!nodes[sel]) nodes[sel] = { innerHTML: "", textContent: "" };
              return nodes[sel];
            },
          };
        }
      }

      class FixedDate extends Date {
        constructor(...args) {
          super(...(args.length ? args : [15000]));
        }
        static now() {
          return 15000;
        }
      }

      const context = {
        HTMLElement: BaseElement,
        customElements: { define(_name, cls) { PanelClass = cls; } },
        Date: FixedDate,
        console,
        encodeURIComponent,
      };
      vm.createContext(context);
      vm.runInContext(code, context);

      const history = Array.from({ length: 10 }, (_v, i) => ({
        id: `id${i}`,
        item: `item${i}`,
        hazard: false,
        first_seen: 1000 - i,
        image_url: `/img/${i}.jpg`,
      }));
      const panel = new PanelClass();
      panel.hass = {
        states: {
          "sensor.bedroom_baby_monitor_crib_items_llm": {
            entity_id: "sensor.bedroom_baby_monitor_crib_items_llm",
            attributes: { items: [], history },
          },
        },
      };

      const grid = panel.shadowRoot.querySelector(".grid").innerHTML;
      console.log(JSON.stringify({
        blanks: (grid.match(/- - -/g) || []).length,
        tiles: (grid.match(/class="tile/g) || []).length,
        hasNewest: grid.includes("item0"),
        hasOldest: grid.includes("item9"),
      }));
    """

    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script), str(panel)],
        check=True,
        text=True,
        capture_output=True,
    )
    rendered = json.loads(result.stdout)
    assert rendered == {"blanks": 0, "tiles": 9, "hasNewest": True, "hasOldest": True}
