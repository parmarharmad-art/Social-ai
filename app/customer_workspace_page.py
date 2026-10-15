"""Mobile-friendly session-based workspace UI for SocialPilot AI."""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

router = APIRouter()


@router.get("/workspace", response_class=HTMLResponse)
async def workspace_page(request: Request):
    if not request.cookies.get("socialpilot_session"):
        return RedirectResponse("/account", status_code=303)
    return HTMLResponse(r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#101828"><title>SocialPilot AI — My workspace</title>
<style>
body{margin:0;background:#f4f6fb;color:#182230;font:15px/1.5 system-ui}header{background:#101828;color:#fff;padding:18px}main{max-width:850px;margin:20px auto;padding:0 14px}.card{background:#fff;border:1px solid #e4e7ec;border-radius:14px;padding:18px;margin:14px 0}button,a{display:inline-block;border:0;border-radius:8px;padding:11px 14px;background:#4263eb;color:white;text-decoration:none;font:inherit;cursor:pointer}a.secondary,button.secondary{background:#eef2ff;color:#253b80}input,textarea{box-sizing:border-box;width:100%;padding:11px;margin:6px 0 12px;border:1px solid #cfd6e4;border-radius:8px;font:inherit}.muted{color:#667085}.item{border-top:1px solid #eaecf0;padding:12px 0;overflow-wrap:anywhere}.msg{padding:10px;background:#f2f4f7;border-radius:8px;white-space:pre-wrap}.actions{display:flex;gap:8px;flex-wrap:wrap}
</style></head><body><header><strong>✦ SocialPilot AI</strong> <span class="muted">/ My workspace</span></header>
<main><h1>My workspace</h1><p class="muted">Your connected social accounts and scheduled posts. Each list is restricted to your signed-in workspace.</p>
<div class="card"><h2>Instagram account</h2><div id="connections">Checking connection…</div><div class="actions"><a href="/auth/instagram/start">Connect Instagram</a><a class="secondary" href="/account">Account settings</a></div></div>
<div class="card"><h2>Create content & schedule</h2><label>Post topic</label><input id="topic" placeholder="e.g. WhatsApp lead follow-up automation"><button id="generate" class="secondary">Generate carousel draft & caption</button><label>Generated content package (editable)</label><textarea id="draft" rows="7" placeholder="Your hook, slide plan, caption and image prompt will appear here"></textarea><label>Instagram account ID</label><input id="uid" placeholder="Choose a connected account above"><label>Public HTTPS image URL</label><input id="img" type="url" placeholder="https://.../image.jpg"><label>Caption</label><textarea id="caption" rows="4" placeholder="Write your post caption"></textarea><label>Publish time (include your local time)</label><input id="when" type="datetime-local"><button id="schedule">Add to queue</button><p id="scheduleMsg" class="msg">Connect Instagram first. Publishing depends on Meta permissions.</p></div>
<div class="card"><h2>Scheduled posts</h2><button class="secondary" id="refresh">Refresh</button><div id="posts">Loading…</div></div>
<div class="card"><button class="secondary" id="logout">Log out</button><a class="secondary" href="/dashboard">Open classic dashboard</a></div></main>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
async function api(path,opts={}){const r=await fetch(path,{...opts,credentials:'same-origin',headers:{'Content-Type':'application/json',...(opts.headers||{})}});let d={};try{d=await r.json()}catch{}if(!r.ok)throw Error(d.detail||'Request failed ('+r.status+')');return d}
async function load(){try{const me=await api('/api/account/me');const [c,p]=await Promise.all([api('/api/customer/instagram/connections'),api('/api/customer/posts')]);$('connections').innerHTML=c.connections.length?c.connections.map(x=>'<div class="item"><strong>Instagram ID '+esc(x.instagram_user_id)+'</strong><p class="muted">'+esc(x.auth_method)+' · Connected '+esc(x.connected_at||'')+'</p><button class="secondary" onclick="chooseAccount(\''+esc(x.instagram_user_id)+'\')">Use this account</button></div>').join(''):'<p class="muted">No Instagram account linked to this workspace yet.</p>';$('posts').innerHTML=p.posts.length?p.posts.map(x=>'<div class="item"><strong>#'+esc(x.id)+' · '+esc(x.status)+'</strong><p>'+esc(x.scheduled_at)+'</p><p>'+esc(x.caption)+'</p>'+(x.last_error?'<p class="muted">'+esc(x.last_error)+'</p>':'')+'</div>').join(''):'<p class="muted">No posts in this workspace yet.</p>';}catch(e){$('connections').textContent=e.message;$('posts').textContent='Could not load posts. Please log in again at /account.'}}
window.chooseAccount=id=>{$('uid').value=id;$('scheduleMsg').textContent='Selected Instagram account '+id};
$('refresh').onclick=load;
$('generate').onclick=async()=>{try{const topic=$('topic').value.trim();if(topic.length<3)throw Error('Enter a topic first.');$('scheduleMsg').textContent='Generating content…';const d=await api('/api/customer/content',{method:'POST',body:JSON.stringify({topic})});$('draft').value=d.content||'';const m=(d.content||'').match(/CAPTION:\s*([\s\S]*?)(?=\n(?:CTA|HASHTAGS|IMAGE PROMPT):|$)/i);$('caption').value=m?m[1].trim():d.content;$('scheduleMsg').textContent=(d.mode==='ai'?'AI draft generated.':'Template draft generated.')+' Review the draft before scheduling.'}catch(e){$('scheduleMsg').textContent=e.message}};
$('schedule').onclick=async()=>{try{if(!$('when').value)throw Error('Choose a publish date and time.');const scheduled_at=new Date($('when').value).toISOString();const d=await api('/api/customer/posts',{method:'POST',body:JSON.stringify({instagram_user_id:$('uid').value.trim(),image_url:$('img').value.trim(),caption:$('caption').value.trim(),scheduled_at})});$('scheduleMsg').textContent='Post #'+d.post_id+' added to queue.';await load()}catch(e){$('scheduleMsg').textContent=e.message}};
$('logout').onclick=async()=>{await api('/api/account/logout',{method:'POST'});location.href='/account'};
load();
</script></body></html>""")
