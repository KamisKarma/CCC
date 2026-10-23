# CCC Level 6 – Übergabe an die nächste KI

## Stand

| Datei | Start | jetzt (`loesungen/`) |
|---|---|---|
| small | 332 | 108 |
| medium | 26.234 | 5.977 |
| large | 22.525 | 5.288 |
| enormous | 20.254 | 4.704 |
| **gesamt** | **69.345** | **16.077** |

- **Ziel des Users: unter 15.000 Zeilen.** Es fehlen noch etwa 1.080.
- Alle 550 Programme sind mit `check6.py` geprüft: Jedes erzeugt das Muster genau so oft wie gefordert.
- Score = Gesamtzahl der Programmzeilen über alle Dateien, weniger ist besser. Pro Zeile kostet es gleich viel, ob 1 oder 6 Laser etwas tun.

## Ordner

- `loesungen/`: beste geprüfte Ausgaben zum Hochladen.
- `eingaben/`: Inputs, Beispiel und Aufgaben-PDF.
- `code_python/`:
  - `level1–5.py`: Simulator-Bausteine. **`level5.simulate(r, rows, program)` ist der maßgebliche Prüfer.**
  - `check6.py <in> <out>` prüft eine ganze Ausgabedatei.
  - `merge_cs.py` übernimmt pro Muster das kürzere geprüfte Programm.
  - `level6*.py`, `run6*.py`, `worker6.py`: frühe gierige Python-Planer. Sie sind überholt.
  - `agent_py/dbl.py`: unfertiger Python-Prototyp des Doppel-Linien-Sweeps.
- `code_csharp/beam_search/`: **der Planer, der fast alle Gewinne gebracht hat** (.NET 9; `dotnet run -c Release -- <mode> ...`).
  - Modi:
    - `check <name> <out>`
    - `opt <names,komma> <sekunden> <threads>`
    - `tune <name> <step> <threads> key=val...`
    - `cyc2 <names> <threads>`
    - `chain <names> <threads> [lim]`
    - `one <name> <idx>`
  - Gewichte über `key=val`: `W` (Beam-Breite), `wH` (Halo-Strafe), `seed`, `dbl`, `wP`, `wS` …
  - Achtung: Pfade sind fest eingetragen (`Root = C:\Users\josch\OneDrive\Desktop\CCC`, Ausgabe `Lösungen\level6_cs`, Seeds aus `Lösungen\level6`). Vor dem Start anpassen.
- `code_csharp/sweep_planner/`: Doppel-Linien-Sweep (`Planner.cs`, `Engine.cs`) mit Beam-Abschluss (`Finish.cs`). Hat nur 2 large-Muster verbessert.

Auf dem Rechner gibt es nur Python 3.10/3.12, .NET 9 und Java, kein C/C++/Rust/Go.

## Regeln mit Fallstricken

- 6 Emitter starten aus an den Ecken: (r,0), (0,r), (0,3r), (r,4r), (2r,3r), (2r,r).
  - `F` = Ring-Index +1 (im Uhrzeigersinn), `B` = −1, `T` = an/aus, `-` = nichts.
  - **Pro Emitter und Zeile nur ein Befehl:** Bewegen und Umschalten im selben Takt geht nicht.
- Jeder aktive Strahl läuft über alle inneren Zellen bis zum Rand. Ergebnis pro Zelle je nach Trefferzahl k:
  - k=2 → Materie M
  - k≥3 → gelöscht (O)
  - k=1 → keine Änderung
  - Materie bleibt stehen.
- Abgabe, sobald alle Musterzellen M sind und keine Halo-Zelle M ist. Halo = die 6 Hex-Nachbarn (0,±2) und (±1,±1) der Musterzellen, die selbst nicht zum Muster gehören.
  - Danach werden nur die Musterzellen auf O gesetzt.
  - Zellen, die im Abgabe-Takt entstehen, sind damit auch weg.
- **Materie außerhalb von Muster ∪ Halo ist für immer egal.** Die ersten Python-Planer haben nur Kreuzungen im Muster erlaubt, das war viel zu streng.
- Die gezählten Abgaben müssen genau dem geforderten Count entsprechen. Das Programm endet am besten im Takt der letzten Abgabe.

## Geometrie

- Gegenläufige Paare: (e0,e3) auf Zeilen, (e1,e4) auf x−y-Diagonalen, (e2,e5) auf x+y-Diagonalen. Stehen beide Emitter eines Paars auf derselben Linie und sind an, wird **die ganze Linie in einem Takt zu M** (Doppel-Linie).
- Beim Start stehen alle drei Paare schon auf Linien durch die Mitte: e0/e3 auf Zeile r, e1/e4 auf x−y=r, e2/e5 auf x+y=3r.
- Ein Paar um eine Linie verschieben kostet 1 Takt (z. B. e0 F + e3 B = eine Zeile hoch).
- Mit 6 Lasern kreuzen sich bis zu 12 nicht-parallele Paare pro Takt. Treffen sich 3 Strahlen in einer Zelle, wird sie gelöscht.

## Was funktioniert hat (Beam-Search in C#)

1. **Exakte Beam-Search** über Emitter-Positionen, an/aus und die Bits von Muster ∪ Halo, mit allen 4.096 Zügen pro Takt und exakter inkrementeller Simulation. Sie brachte den Sprung von 43k auf 26k in einem Durchlauf mit W=50.
2. **Starke Halo-Strafe** (`wH` 60–200 statt 20) bei large/enormous, etwa 12 % besser.
3. **„cell-sum“-Heuristik**: Summe über alle fehlenden Musterzellen der billigsten Kosten, ein kreuzendes Strahlpaar dorthin zu bringen. Sie ersetzt die Paar-Distanz-Summe und war etwa 20 % besser bei large und 10–15 % bei enormous.
4. **Doppel-Linien-Potenzial** in der Heuristik: Paare werden zu Linien gezogen, die viele fehlende Musterzellen und wenige Halo-Zellen haben.
5. **Portfolio**: mehrere Seeds und Gewichtssätze, pro Muster das beste behalten.
6. **Suffix-Modus**: das beste Programm an k Stellen abschneiden und das Ende neu suchen. Damit lassen sich auch Programme aus anderen Quellen polieren.
7. Workflow: Jeder Optimierer schreibt in einen eigenen Ordner, `merge_cs.py` nimmt pro Muster das kürzere Programm, das `simulate` exakt besteht.

## Was nicht funktioniert hat

- **Reiner Doppel-Linien-Sweep**, eine Linie pro Takt mit den 4 anderen Emittern als Halo-Löschern:
  - Fast jedes enormous-Muster hat in jeder Richtung Linien mit 5–9 Halo-Zellen, pro Takt sind aber höchstens 4 löschbar.
  - Kreuzungen zwischen Löschern verschiedener Richtungen landen oft auf Halo-Zellen fertiger Linien.
  - Das Aufräumen kostet 5–11 Extra-Takte.
  - Ergebnis: 0 Gewinne bei enormous und medium, 2 bei large (53→48, 57→49).
- **Breitere Beams bei medium** (W=1000 auf den 43 längsten Programmen) brachten nur 49 Zeilen.
- **Gierige Planer** (`level6*.py`) sind weit schlechter als die Beam-Search.

## Analyse medium (wichtigster Rest-Hebel)

210 Muster, Radius 3–5, Ø 12 Zellen, Count Ø 9,7 (max 19). Kosten pro Wiederholung nach der ersten Abgabe:

| Takte pro Wiederholung | Muster |
|---|---|
| 1 | 7 |
| 2 | 101 (driftende Ketten, von der Beam-Search gefunden) |
| 3 | 50 |
| 4–9 | ~45 (dichte Blobs bei r=5) |

- Eine exhaustive Suche nach Periode-2-Zyklen (Konfigurationen A/B abwechselnd) fand nur 28 von 210 Mustern; die wurden angewendet.
- Eine Ketten-Suche (Abgabe alle 2 Takte ohne Rückkehr zur Startkonfiguration) war zu langsam und braucht Pruning.

## Offene Ideen für die letzten ~1.100 Zeilen

1. **Zwei Doppel-Linien gleichzeitig**, z. B. Zeilen plus eine Diagonalfamilie, während die dritte Familie auf beiden Linien Halo-Zellen löscht. Damit wäre etwa die halbe Linienzahl pro Wiederholung möglich. Das zielt auf die ~45 dichten medium-Muster mit je ~10 Wiederholungen: Jeder gesparte Takt pro Wiederholung bringt ~9 Zeilen.
2. **2-Takt-Ketten-Suche mit Pruning** für die 50 Muster mit 3 Takten pro Wiederholung: Suche über die Konfigurationen direkt nach einer Abgabe.
3. **Hybrid bei large/enormous**: nur die sauberen Linien sweepen (≤4 Halo-Zellen, Löscher können folgen), den Rest per Beam-Search fertig bauen, danach Suffix-Politur.
4. Längere Portfolio-Läufe mit cell-sum-Heuristik und größerem W auf enormous. Die Einzelläufe sättigen aber schon.

## Praktische Hinweise

- Windows: Zwei Prozesse, die dieselbe Datei per `os.replace` ersetzen, verlieren Updates oder werfen PermissionError. Darum schreibt pro Datei nur ein Prozess, oder es gibt einen Mutex mit Merge-on-write, wie in der C#-Beam-Search.
- Jedes neue Programm vor dem Übernehmen mit `level5.simulate` prüfen, `== count`, nicht `>=`.
- Die Bearbeitungszeit war durch das Nutzungslimit begrenzt. Lange Läufe als lokale Prozesse im Hintergrund kosten kein KI-Limit.
