# Frontend run & deployment notes

## Local run
Run the FastAPI backend from `backend/` and it will now also serve:
- UI static files from `frontend/` at `/`
- demo files from `sample_data/` at `/sample_data`

## Server scenario: will frontend repo changes be visible without a separate data push?
Yes—if your server deployment actually pulls/builds the latest repo and restarts the app.

Because `backend/app.py` now mounts the `frontend/` directory directly, frontend changes are included with the backend deploy artifact. You do **not** need a separate frontend data/static push step in this setup.

If changes still do not appear, common causes are:
- stale browser/CDN cache
- deployment still running an older image/commit
- server startup path not using this repository version
