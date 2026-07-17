"""Smoke tests for the crib-items sidebar panel."""

import json
import subprocess
import textwrap
from pathlib import Path


def _render_panel(history: list[dict]) -> dict:
    panel = Path("custom_components/baby_monitor/frontend/crib-items-panel.js")
    script = r"""
      const fs = require("fs");
      const vm = require("vm");
      const code = fs.readFileSync(process.argv[1], "utf8");
      const history = JSON.parse(process.argv[2]);
      let PanelClass;

      class BaseElement {
        attachShadow() {
          const nodes = {};
          const root = {
            innerHTML: "",
            querySelector(sel) {
              if (!nodes[sel]) nodes[sel] = { innerHTML: "", textContent: "" };
              return nodes[sel];
            },
          };
          this.shadowRoot = root;
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
      const title = panel.shadowRoot.querySelector(".title").innerHTML;
      const shell = panel.shadowRoot.innerHTML;
      console.log(JSON.stringify({
        blanks: (grid.match(/- - -/g) || []).length,
        tiles: (grid.match(/class="tile/g) || []).length,
        images: (grid.match(/class="crop-img/g) || []).length,
        hasNewest: grid.includes("item0"),
        hasOldest: grid.includes("item9"),
        hasSafeItem: grid.includes("pacifier"),
        hasEmptyState: grid.includes("No warning or alarm items"),
        hasLive: grid.includes("LIVE") || title.includes("LIVE") || shell.includes("LIVE"),
        hasWarning: grid.includes("WARNING"),
        hasAlarm: grid.includes("ALARM"),
      }));
    """

    result = subprocess.run(
        ["node", "-e", textwrap.dedent(script), str(panel), json.dumps(history)],
        check=True,
        text=True,
        capture_output=True,
    )
    return json.loads(result.stdout)


def test_non_alert_items_are_hidden_and_live_indicator_removed():
    history = [
        {
            "id": "safe1",
            "item": "pacifier",
            "hazard": False,
            "first_seen": 1000,
            "image_url": "/img/safe.jpg",
        }
    ]

    rendered = _render_panel(history)

    assert rendered["hasLive"] is False
    assert rendered["hasSafeItem"] is False
    assert rendered["hasEmptyState"] is True
    assert rendered["images"] == 0


def test_alert_history_rotation_does_not_render_sparse_page():
    history = [
        {
            "id": f"id{i}",
            "item": f"item{i}",
            "hazard": True,
            "first_seen": 1000 - i,
            "image_url": f"/img/{i}.jpg",
        }
        for i in range(10)
    ]

    rendered = _render_panel(history)

    assert rendered["blanks"] == 0
    assert rendered["tiles"] == 9
    assert rendered["hasNewest"] is True
    assert rendered["hasOldest"] is True
    assert rendered["hasAlarm"] is True
