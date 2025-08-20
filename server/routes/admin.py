import os, time
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import HTMLResponse
from ..config import KITE_ACCESS_TOKEN
from ..storage import log_event

router = APIRouter()

@router.get('/admin', response_class=HTMLResponse)
async def admin_form():
    html = f'''<html><body style="font-family:system-ui;max-width:560px;margin:40px auto;">
    <h2>UnoClick Admin</h2>
    <form method="post" action="/admin/token">
      <label>KITE Access Token (daily)</label><br/>
      <input type="text" name="access_token" style="width:100%;padding:.6rem" /><br/><br/>
      <button type="submit" style="padding:.6rem 1rem">Save</button>
    </form>
    <p>Current key set: <b>{'YES' if bool(os.getenv('KITE_ACCESS_TOKEN', KITE_ACCESS_TOKEN)) else 'NO'}</b></p>
    <p><a href="/portfolio">View portfolio</a> · <a href="/logs">Download logs</a></p>
    </body></html>'''
    return HTMLResponse(html)

@router.post('/admin/token')
async def admin_set_token(access_token: str = Form(...)):
    os.environ['KITE_ACCESS_TOKEN'] = access_token
    log_event({"ts": time.time(), "evt": "admin_token_set"})
    return {"ok": True}
