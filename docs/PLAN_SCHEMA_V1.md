# Plan JSON v1

Un plan est un objet JSON UTF-8, indenté, avec `schema_version: 1`.

```json
{"schema_version":1,"plan_id":"uuid","source":{"path":"/app/inbox/file.mp4","sha256":"..."},"category":"anime|football|autre","status":"pending_human_review|approved|rendered|failed","scenes":[{"id":"scene-001","start_seconds":0.0,"end_seconds":3.2,"thumbnail":"workspace/...jpg","selected":true}],"exports":[{"profile":"youtube|vertical","output":"output/...mp4","status":"pending"}],"human_validation":{"approved":false,"approved_at":null}}
```

Toutes les scènes détectées sont présentes. `selected` est une proposition modifiable, jamais une suppression automatique. Le rendu exige `status: "approved"` et `human_validation.approved: true`.

## Extension de proposition highlight

Un plan peut inclure proposal avec kind, ersion, strategy et stimated_duration_seconds. Une proposition reste pending_human_review : elle ne peut pas être rendue avant approbation humaine.

