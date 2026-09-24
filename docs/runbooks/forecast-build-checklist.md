# Forecast-Build-Checkliste (On-Call, deterministisch)

## Ziel
Ein gültiges `governance/forecast.json`-Artefakt erzeugen und gegen das Schema validieren.

## Voraussetzungen
- Ausführung aus dem Repository-Root.
- Python-Umgebung mit den Repo-Abhängigkeiten.

## 1) Compiler mit Forecast-Hook ausführen
```bash
python tools/rule_compiler.py \
  --template templates/mitre-techniques/T1110-password-spray.compiler.json \
  --params tools/rule_params.example.yaml \
  --repo . \
  --forecast \
  --compiled-output governance/compiled-rules.json
```

**Soll-Ergebnis**
- Exit-Code `0`
- `governance/forecast.json` wurde erzeugt/aktualisiert.

## 2) Artefakt-Existenz prüfen
```bash
test -f governance/forecast.json
```

**Soll-Ergebnis**
- Exit-Code `0`

## 3) Forecast gegen Schema validieren
```bash
python tools/validate_json.py \
  --schema tools/forecast.schema.json \
  --input governance/forecast.json
```

**Soll-Ergebnis**
- Exit-Code `0`
- Erfolgsmeldung `Validated governance/forecast.json against tools/forecast.schema.json`

## 4) Optional: Drift gegen Vorversion prüfen
```bash
diff -u governance/forecast.json governance/forecast.json.prev
```

**Hinweis**
- Nur verwenden, wenn eine Vorversion vorhanden ist.
- Unterschied muss im Change-Kontext begründbar sein (z. B. neue Regeln/Parameter).

## 5) On-Call-Protokoll (Kurztext)
```text
Forecast-Build erfolgreich:
- rule_compiler --forecast: OK
- governance/forecast.json: vorhanden
- Schema-Validierung: OK
- Drift: none/expected/unexpected
```
