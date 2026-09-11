/**
 * Schritt 4 — Vorlagen aus src/ zu eigenstaendigen Dokumenten in docs/ vorrendern.
 *
 * Warum: Die Vorlagen bauen Diagramme und lange Listen per JavaScript auf. Viele
 * Umgebungen fuehren aber kein JavaScript aus — iOS Quick Look, die Dateivorschau
 * von GitHub, E-Mail-Clients, Druckansichten. Dort waeren die Seiten sonst leer.
 * Wir fuehren die Aufbauskripte deshalb einmal hier aus und schreiben das
 * fertige Ergebnis als statisches HTML.
 *
 *   npm install jsdom
 *   node scripts/04_vorrendern.js
 */
const { JSDOM } = require("jsdom");
const fs = require("fs");
const path = require("path");

const WURZEL = path.resolve(__dirname, "..");
const QUELLE = path.join(WURZEL, "src");
const ZIEL = path.join(WURZEL, "docs");

/* Nach dem Vorrendern bleibt nur noch dieses kleine Skript uebrig. Es bindet die
   Hinweisfenster an die beim Rendern gesetzten data-tip-Attribute. Faellt es aus,
   fehlen lediglich die Tooltips — der Inhalt steht bereits im HTML. */
const TOOLTIP_JS = `
(function(){
  var tip=document.getElementById("tip"); if(!tip) return;
  function show(t){tip.textContent=t;tip.style.opacity="1";}
  function move(e){tip.style.left=e.clientX+"px";tip.style.top=e.clientY+"px";}
  function hide(){tip.style.opacity="0";}
  var n=document.querySelectorAll("[data-tip]");
  for(var i=0;i<n.length;i++){
    (function(el){
      var t=el.getAttribute("data-tip");
      el.addEventListener("mouseenter",function(){show(t);});
      el.addEventListener("mousemove",move);
      el.addEventListener("mouseleave",hide);
    })(n[i]);
  }
})();`;

/* Die woechentlichen Ausgaben entstehen in Schritt 05, die Startseite in Schritt 06 —
   beide sind bereits statisch. Hier laeuft nur durch, was Inhalt per JavaScript aufbaut. */
const SEITEN = [
  ["report.html", "report/2026-09-09.html",
   "Datenanalyse der Gremienarbeit der Stadt Bad Waldsee, Januar 2024 bis September 2026."],
];

const NAVIGATION = JSON.parse(
  fs.readFileSync(path.join(__dirname, "navigation.json"), "utf8"));

function kopfEintrag(d, tag, attrs) {
  const e = d.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  return e;
}

function rendern(quelle, ziel, beschreibung) {
  return new Promise((fertig, fehler) => {
    const dom = new JSDOM(fs.readFileSync(quelle, "utf8"), {
      runScripts: "dangerously",
      pretendToBeVisual: true,
    });
    dom.window.addEventListener("error", (e) => fehler(e.error || e.message));

    setTimeout(() => {
      const d = dom.window.document;

      // Aufbauskripte entfernen — ihr Ergebnis steht jetzt im DOM.
      [...d.querySelectorAll("script")].forEach((s) => s.remove());
      if (d.querySelector("[data-tip]")) {
        const s = d.createElement("script");
        s.textContent = TOOLTIP_JS;
        d.body.appendChild(s);
      }

      // Die Navigationsleiste stammt aus scripts/navigation.json — derselben
      // Quelle, aus der die Bauskripte sie erzeugen. Sonst muesste man beim
      // Hinzufuegen einer Seite daran denken, den Report von Hand nachzuziehen.
      const leiste = d.querySelector('nav[aria-label="Bereiche"]');
      if (leiste) {
        const hoch = path.dirname(ziel).endsWith("report") ? "../" : "";
        leiste.innerHTML = "\n    " + NAVIGATION.map((e) => {
          const hier = e.name === "report" ? ' aria-current="page"' : "";
          return `<a href="${hoch}${e.ziel}"${hier}>${e.text}</a>`;
        }).join('\n    <span aria-hidden="true">/</span>\n    ') + "\n  ";
      }

      d.documentElement.setAttribute("lang", "de");
      if (!d.querySelector("meta[charset]")) {
        d.head.insertBefore(kopfEintrag(d, "meta", { charset: "utf-8" }), d.head.firstChild);
      }
      if (!d.querySelector("meta[name=viewport]")) {
        d.head.insertBefore(
          kopfEintrag(d, "meta", { name: "viewport", content: "width=device-width, initial-scale=1" }),
          d.head.firstChild);
      }
      d.head.appendChild(kopfEintrag(d, "meta", { name: "description", content: beschreibung }));

      fs.writeFileSync(ziel, "<!doctype html>\n" + d.documentElement.outerHTML + "\n");

      const marken = d.querySelectorAll("svg rect, svg circle, svg polyline").length;
      const punkte = d.querySelectorAll("li").length;
      const kb = (fs.statSync(ziel).size / 1024).toFixed(0);
      console.log(`  ${path.basename(ziel).padEnd(50)} ${kb.padStart(3)} KB  ` +
                  `SVG-Marken ${String(marken).padStart(3)}  Listenpunkte ${String(punkte).padStart(3)}`);
      fertig();
    }, 800);
  });
}

(async () => {
  fs.mkdirSync(ZIEL, { recursive: true });
  console.log("Vorrendern src/ → docs/");
  for (const [von, nach, beschreibung] of SEITEN) {
    const ziel = path.join(ZIEL, nach);
    fs.mkdirSync(path.dirname(ziel), { recursive: true });
    await rendern(path.join(QUELLE, von), ziel, beschreibung);
  }
  console.log("Fertig. Die Dokumente in docs/ kommen ohne JavaScript aus.");
})();
