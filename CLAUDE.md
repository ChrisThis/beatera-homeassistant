# beatera-homeassistant – Arbeitsregeln

Home-Assistant-Integration für Beatera (Python, HACS-Format mit `custom_components/beatera/`). Reiner Client der Beatera-API und des Echtzeit-Kanals. Details: Abschnitt 11.1 des Plans.

Der Gesamtplan für alle Beatera-Repos steht im Hauptrepo `beatera` unter
`docs/BUILD_PLAN.md` und wird laufend ergänzt: vor Vorschlägen lesen, neue
Anforderungen dort einarbeiten.

Diese Regeln gelten für alle Beatera-Repos (`beatera`, `beatera-app`,
`beatera-homeassistant`).

## 1. Nichts bauen ohne ausdrückliches "Bauen"

Nichts bauen, außer der Auftraggeber schreibt ausdrücklich das Wort **"Bauen"**.

- Ohne "Bauen": nur lesen, analysieren, Fragen beantworten, Vorschläge und
  Pläne machen. Keine Projektdateien anlegen, ändern oder löschen, keinen Code
  schreiben, keine Build-/Install-/Deploy-Befehle ausführen.
- "mach mal", "können wir X", "ich brauche X" oder ein zustimmendes "ok"
  zählen **nicht** als Freigabe. Im Zweifel den Plan vorstellen und warten.
- "Bauen" gibt nur das frei, was gerade besprochen wurde. Der nächste Schritt
  braucht wieder ein "Bauen".
- Ausgenommen sind Plan und Regeln selbst, wenn der Auftraggeber darum bittet.

## 2. Git: `ki-dev` und Releases

- Jede Änderung wird auf den Branch **`ki-dev`** gepusht, nie direkt auf `main`.
- Eine neue Version (Versionsnummer, Tag, Merge nach `main`) entsteht **nur**
  auf die ausdrückliche Ansage **"release und push"**.
- Jede Änderung bekommt einen Eintrag in `CHANGELOG.md` unter
  "Unveröffentlicht", in Nutzersprache, auf Deutsch und Englisch.

## 3. Tests nur lokal

- Tests und Lint laufen **nur lokal** auf dem Entwicklungsrechner, nicht auf
  GitHub. In `.github/workflows` gibt es keine Test-Schritte.
- Vor jedem Push auf `ki-dev` die Tests lokal ausführen. Nur bei grünem
  Ergebnis pushen und das Ergebnis im Bericht nennen.
- Tests in einer echten Home-Assistant-Installation führt der Auftraggeber aus; im Bericht klar trennen, was lokal geprüft wurde und was dort noch zu prüfen ist.

## 4. Zugangsdaten

- Passwörter, Tokens, API-Schlüssel und Signier-Zertifikate liegen nie im
  Repo, sondern in nicht eingecheckten Dateien.
- Zugangsdaten nicht im Chat ausgeben; beim Prüfen solcher Dateien Werte
  maskieren.

## 5. Daten des Auftraggebers

- Entwickelt und getestet wird nur gegen die Vorschau-Instanz und den
  Testordner `00_Beatera_Medien_Test`, nie gegen Produktion oder die echten
  Bibliotheken.

## 6. Hilfe immer mitpflegen

- Die Hilfe in Beatera (`beatera/resources/help/de` und `/en`, je Kapitel eine Markdown-Datei)
  beschreibt Bedienung und Verhalten. Sie wird **bei jeder Änderung**, die Bedienung, Verhalten,
  Einrichtung oder Grenzen betrifft, im selben Commit angepasst, auf Deutsch und Englisch.
- Das gilt auch für die Repos `beatera-app` und `beatera-homeassistant`: Ändert sich dort etwas
  für die Benutzer, wird das passende Kapitel im Hauptrepo nachgezogen (z. B. „Home Assistant").
- Vor jedem „release und push" prüfen, dass die Hilfe zum Stand passt; im Bericht nennen, welche
  Kapitel geändert wurden.
