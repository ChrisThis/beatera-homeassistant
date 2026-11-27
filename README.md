# Beatera für Home Assistant

Verbindet [Beatera](https://github.com/ChrisThis/beatera), die selbst gehostete Mediathek für Musik
und Video, mit Home Assistant.

## Was es kann

- **Player je Gerät:** Jeder Browser und jede App, in der Beatera gerade offen ist, erscheint als
  Media Player: Titel, Bild, Position, Lautstärke; Abspielen, Pause, Stopp, Weiter, Zurück, Spulen,
  Lautstärke. Über die Medienauswahl lassen sich Filme, Serien, Alben und Playlists starten.
- **Musik auf anderen Lautsprechern:** Unter *Medien → Beatera* lassen sich Titel auf Sonos,
  Chromecast und jedem anderen Player von Home Assistant abspielen.
- **Ereignisse** `beatera_event` sofort bei Start, Pause, Fortsetzen und Ende einer Wiedergabe sowie
  nach einem Scan (`event`: `playback.started` …, `type`: `movie`, `episode`, `recording` …,
  dazu `user`, `title`, `session`, `position`).
- **Modi („Beatera-Szenen"):** in Beatera unter *Profil → Home Assistant* angelegt; je Modus ein
  Knopf, dazu die Aktion `beatera.start_mode` (Player, Lautstärke, Zufall, Einblenden wählbar).
- **Durchsagen:** Töne und Sprachausgabe (`tts.speak`) auf Beatera-Playern; danach läuft weiter, was
  vorher lief. Home Assistant schickt den Ton an Beatera (höchstens 10 MB).
- **Alles pausieren:** Aktion `beatera.pause_all`.
- **Geräte des Haushalts:** Mit einem Admin-Konto erscheinen auch die Player der Personen, die das
  im Profil erlaubt haben (nie Kinderkonten).
- **Sensoren:** Spielt gerade (mit Liste, was wo läuft), Mediendateien je Bibliothek, Version; für
  Admins aktive Umwandlungen, Arbeit im Hintergrund, Scan läuft, Knopf „Scan starten".
- **Vorlagen:** „Licht beim Film" (Licht aus beim Start, gedimmt bei Pause, an am Ende) und
  „Modus beim Heimkommen" (vorgemerkter Modus startet, sobald jemand heimkommt).

## Einrichten

1. In HACS dieses Repository als *benutzerdefiniertes Repository* (Typ Integration) hinzufügen,
   installieren, Home Assistant neu starten.
2. In Beatera: *Profil → Home Assistant → Kopplungscode erstellen* (gilt 10 Minuten, einmal).
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Beatera*: Adresse (z. B.
   `https://beatera.example.org`) und den Kopplungscode eingeben.

Das Logo bringt die Integration selbst mit (Ordner `brand/`); Home Assistant zeigt es ab Version
2026.3, ältere Versionen zeigen einen Platzhalter.

Statt des Codes geht auch ein Schlüssel aus *Profil → Apps und Zugänge* (Rechte **Lesen** und
**Abspielen**, für sofortige Ereignisse und Scans dazu **Verwaltung**). Kopplungscode und Modi
brauchen Beatera 0.20 oder neuer.

Für sofortige Ereignisse muss Beatera Home Assistant erreichen können (im selben Netz meist
gegeben) und Home Assistant seine eigene Adresse kennen (*Einstellungen → System → Netzwerk*).
Ohne das fragt die Integration alle 15 Sekunden nach.

## Grenzen

- Ein Player erscheint nur, solange Beatera in diesem Browser bzw. dieser App offen ist. Jeder
  Browser-Tab ist ein eigener Player.
- Auf fremden Lautsprechern nur Musik, Titel für Titel; Filme und Radio laufen über die eigenen
  Player von Beatera.
- Noch nicht: Gruppen und synchrones Abspielen (mit der Beatera-App), Modi auf fremden
  Lautsprechern, frei wählbare Zuordnung von Home-Assistant-Personen zu Beatera-Benutzern.
