#!/usr/bin/env python3
"""Browserpruefung der Navigation und des horizontalen Seitenueberlaufs.

Optional: pip install playwright && playwright install chromium webkit
Aufruf: python scripts/pruefe_mobil.py
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread

from playwright.sync_api import Error as PlaywrightError, sync_playwright

DOCS = Path(__file__).resolve().parent.parent / "docs"


def neueste_ausgabe() -> str:
    """Die jeweils aktuelle Wochenausgabe.

    Stand hier fest verdrahtet und zeigte deshalb auf KW 37, als es laengst
    KW 38 gab: Geprueft wurde eine Ausgabe, die niemand mehr aufruft, und die
    neue gar nicht. Ein Pruefskript, das an der Wirklichkeit vorbeisieht, ist
    schlimmer als keines.
    """
    register = json.loads(
        (DOCS.parent / "data" / "ausgaben.json").read_text(encoding="utf-8"))
    jahr = max(register, key=int)
    return f"ausgaben/{jahr}/kw{max(register[jahr], key=int)}.html"


def neuester_report() -> str:
    """Der zuletzt datierte Report — aus demselben Grund nicht fest benannt."""
    return f"report/{max(p.name for p in (DOCS / 'report').glob('*.html'))}"


SEITEN = ["index.html", "termine.html", "suche.html", "befunde.html",
          "gremien.html", "themen/index.html", "themen/drei-eichen-vi.html",
          "ausgaben/index.html", neueste_ausgabe(), neuester_report()]


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class Server(ThreadingHTTPServer):
    """Der Testserver schweigt auch, wenn der Browser die Verbindung kappt.

    Ein Browser, der eine Seite fertig geladen hat, schliesst offene
    Verbindungen ohne Abmeldung — der Server meldet das als
    ConnectionResetError samt Traceback. Das ist erwartetes Verhalten und
    kein Fehler, sieht in der Ausgabe des taeglichen Laufs aber aus wie
    einer. Wer Rauschen nicht abstellt, liest irgendwann ueber die echten
    Meldungen hinweg.
    """

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
            super().handle_error(request, client_address)


def main():
    server = Server(("127.0.0.1", 0), partial(Handler, directory=str(DOCS)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    checks = 0
    try:
        with sync_playwright() as p:
            for engine in (p.chromium, p.webkit):
                try:
                    browser = engine.launch()
                except PlaywrightError as fehler:
                    # Die Browser liegen ausserhalb des Pakets in
                    # ~/Library/Caches/ms-playwright und wandern **nicht** mit,
                    # wenn `uv run --with playwright` eine neuere Version
                    # aufloest: Dann sucht das Paket einen Build, den es lokal
                    # nicht gibt. Das ist ein Einrichtungsstand und kein Befund
                    # an den Seiten — ein Traceback verwechselt beides.
                    print(f"   Browser nicht einsatzbereit ({engine.name}):",
                          file=sys.stderr)
                    print(f"     {str(fehler).splitlines()[0][:120]}", file=sys.stderr)
                    print("   Nachholen mit: uv run --with playwright "
                          "playwright install chromium webkit", file=sys.stderr)
                    raise SystemExit(2) from None
                # Die Navigation muss ohne JavaScript vollstaendig benutzbar sein.
                context = browser.new_context(java_script_enabled=False)
                page = context.new_page()
                for width in (320, 390, 620, 621, 1024):
                    page.set_viewport_size({"width": width, "height": 844})
                    for path in SEITEN:
                        # Ein zweiter Versuch, falls die Seite gerade neu
                        # geschrieben wird — das passiert, wenn direkt nach
                        # einem Bauflauf geprueft wird.
                        response = page.goto(f"{origin}/{path}")
                        if response.status != 200:
                            page.wait_for_timeout(300)
                            response = page.goto(f"{origin}/{path}")
                        assert response.status == 200, (path, response.status)
                        page.evaluate("document.fonts.ready")
                        result = page.evaluate("""() => {
                          const nav = document.querySelector('.brandbar nav');
                          const bounds = nav.getBoundingClientRect();
                          const links = [...nav.querySelectorAll('a')];
                          return {
                            width: document.documentElement.clientWidth,
                            scrollWidth: document.documentElement.scrollWidth,
                            links: links.map(a => {
                              const r = a.getBoundingClientRect();
                              return {text:a.textContent, height:r.height,
                                inside:r.left >= bounds.left - 1 && r.right <= bounds.right + 1
                                  && r.top >= bounds.top - 1 && r.bottom <= bounds.bottom + 1};
                            }),
                            // Aufklapper sind Tippziele wie Links und wurden
                            // bisher nicht gemessen: Die Pruefung sah nur die
                            // Navigationsleiste, meldete aber „mobile
                            // Tippziele >=44px". Ein neuer <summary> kam mit
                            // 27 px durch.
                            falter: [...document.querySelectorAll('details > summary')]
                              .map(d => {
                                const r = d.getBoundingClientRect();
                                return {text:d.textContent.trim().slice(0,40), height:r.height};
                              })
                          };
                        }""")
                        label = f"{engine.name} {width}px {path}"
                        assert result["scrollWidth"] <= result["width"] + 1, (label, result)
                        assert len(result["links"]) == 7, label
                        assert all(a["inside"] for a in result["links"]), (label, result)
                        if width <= 620:
                            assert all(a["height"] >= 44 for a in result["links"]), label
                            zu_klein = [d for d in result["falter"] if d["height"] < 44]
                            assert not zu_klein, (label, zu_klein)
                        # Auch der letzte Link muss per Tastatur erreichbar bleiben.
                        page.locator('.brandbar nav a').first.focus()
                        for _ in range(6):
                            # WebKit folgt unter macOS der Safari-Voreinstellung:
                            # Option-Tab nimmt Links in die Tab-Reihenfolge auf.
                            page.keyboard.press("Alt+Tab" if engine.name == "webkit"
                                                and sys.platform == "darwin" else "Tab")
                        assert page.locator('.brandbar nav a').last.evaluate(
                            "a => a === document.activeElement"), label
                        checks += 1
                page.set_viewport_size({"width": 320, "height": 844})
                page.goto(origin + "/index.html")
                page.locator('.brandbar nav a').last.click()
                assert page.url == origin + "/gremien.html", engine.name

                # Mit JavaScript und als Telefon. Die Suche baut ihre
                # Trefferliste erst im Browser auf — ohne JavaScript ist die
                # Seite leer, und genau dort lag ein Ueberlauf: Ein Dateiname
                # ohne Trennstelle war breiter als das Fenster und liess sich
                # seitlich wegschieben. Eine Pruefung, die den Inhalt nie
                # rendert, sieht so etwas nicht.
                for geraet in ("iPhone 13", "iPhone 14 Pro Max"):
                    handy = browser.new_context(**p.devices[geraet])
                    h = handy.new_page()
                    for pfad in SEITEN:
                        h.goto(f"{origin}/{pfad}")
                        h.wait_for_timeout(400)
                        mass = h.evaluate("""() => ({
                          breite: document.documentElement.clientWidth,
                          rollbreite: document.documentElement.scrollWidth
                        })""")
                        assert mass["rollbreite"] <= mass["breite"] + 1, \
                            (engine.name, geraet, pfad, mass)
                        checks += 1
                    # Ein Suchbegriff bringt Treffer und Einordnungen ins Bild.
                    h.goto(f"{origin}/suche.html")
                    h.fill("#q", "Satzung")
                    h.wait_for_timeout(400)
                    mass = h.evaluate("""() => ({
                      breite: document.documentElement.clientWidth,
                      rollbreite: document.documentElement.scrollWidth,
                      treffer: document.querySelectorAll("article.vorgang").length
                    })""")
                    assert mass["treffer"] > 0, (engine.name, geraet, "keine Treffer")
                    assert mass["rollbreite"] <= mass["breite"] + 1, \
                        (engine.name, geraet, "suche mit Suchbegriff", mass)
                    checks += 1
                    handy.close()
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(f"{checks} Ansichten in Chromium/WebKit geprueft: alle Links sichtbar, "
          "mobile Tippziele >=44px, kein Seitenueberlauf, Tastatur und Navigation "
          "erfolgreich — ohne JavaScript bei fuenf Breiten und zusaetzlich als "
          "iPhone mit JavaScript, samt aufgebauter Trefferliste.")


if __name__ == "__main__":
    main()
