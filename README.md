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
- **Sensoren:** Spielt gerade (mit Liste, was wo läuft), Mediendateien je Bibliothek, Version; für
  Admins aktive Umwandlungen, Arbeit im Hintergrund, Scan läuft, Knopf „Scan starten".
- **Vorlage** „Licht beim Film": Licht aus beim Start, gedimmt bei Pause, an am Ende.

## Einrichten

1. In Beatera: *Profil → Apps und Zugänge → Schlüssel erstellen*, Rechte **Lesen** und
   **Abspielen**; dazu **Verwaltung**, wenn Ereignisse sofort ankommen sollen und Scans gestartet
   werden dürfen (nur Admin-Konten).
2. In HACS dieses Repository als *benutzerdefiniertes Repository* (Typ Integration) hinzufügen,
   installieren, Home Assistant neu starten.
3. *Einstellungen → Geräte & Dienste → Integration hinzufügen → Beatera*: Adresse (z. B.
   `https://beatera.example.org`) und Schlüssel eingeben.

Für sofortige Ereignisse muss Beatera Home Assistant erreichen können (im selben Netz meist
gegeben) und Home Assistant seine eigene Adresse kennen (*Einstellungen → System → Netzwerk*).
Ohne das fragt die Integration alle 15 Sekunden nach.

## Grenzen

- Ein Player erscheint nur, solange Beatera in diesem Browser bzw. dieser App offen ist. Jeder
  Browser-Tab ist ein eigener Player.
- Auf fremden Lautsprechern nur Musik, Titel für Titel; Filme und Radio laufen über die eigenen
  Player von Beatera.
- Noch nicht: Gruppen und synchrones Abspielen, Beatera-Modi („Szenen"), Kopplung per Code,
  Zuordnung von Home-Assistant-Personen zu Beatera-Benutzern, Durchsagen.
