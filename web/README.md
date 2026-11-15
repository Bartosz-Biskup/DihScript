# DihScript — web UI

Static frontend for the DihScript API. **Zero JavaScript on purpose** —
the whole thing is `index.html` + `styles.css`, so you can write the JS yourself.

## Preview it

Just open `index.html` in a browser, or serve the folder:

```bash
cd web
python3 -m http.server 5500
# → http://localhost:5500
```

(To serve it from FastAPI instead, mount `StaticFiles` on `/` in
`src/api/main.py` — but you don't need that while learning.)

## The API (what your JS will talk to)

| Endpoint | Method | Request body | Response |
| --- | --- | --- | --- |
| `/fix` | `POST` | `{ mode, script, length, target_audience?, call_to_action?, email }` | `{ script, info, error, changes: [{ start_char, end_char, reason }] }` |
| `/subscriber` | `POST` | `{ name, email }` | `{ name, email, run_count }` |

- `mode` is `"watch"` or `"sell"` — the radio buttons already carry these values.
- `length` is `30`, `60` or `90` (number, not string — `parseInt` it or send JSON).
- In `sell` mode the API **requires** `target_audience` and `call_to_action`.

## Element hooks (ids your JS should use)

Form: `#fix-form` (submit button: `#submit-button`)

| Field | `id` / `name` |
| --- | --- |
| Script | `#field-script` / `script` |
| Mode | `#mode-watch`, `#mode-sell` / `mode` |
| Length | `#length-30`, `#length-60`, `#length-90` / `length` |
| Audience (sell) | `#field-audience` / `target_audience` |
| CTA (sell) | `#field-cta` / `call_to_action` |
| Name | `#field-name` / `name` |
| Email | `#field-email` / `email` |

Results: `#results` · `#result-script` · `#result-info` · `#result-changes`
· `#result-changes-count` · `#result-length-badge` · `#result-error`
· `#result-error-text`

## Suggested exercise (in order)

1. Intercept the form: `submit` listener + `preventDefault()`, read it with
   `new FormData(form)`.
2. `fetch("http://localhost:8000/fix", { method: "POST", body: JSON.stringify(...) })`
   — remember `Content-Type: application/json` and `parseInt` on `length`.
3. Fill `#result-script` (`textContent`, it keeps line breaks), `#result-info`,
   and build one `<li class="change">` per change (template in `index.html`).
4. Show `#result-error` on failure (remove `hidden`, set `#result-error-text`).
5. Polish: add `.is-loading` to `#submit-button` and `#results` while waiting
   (spinner + skeleton shimmer are already styled in CSS).
6. Validate the sell-mode fields yourself in JS — they're revealed by CSS
   alone, so `required` is deliberately left off them.
