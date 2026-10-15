"""Metricool-style mobile dashboard for SocialPilot AI."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, Response

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def metricool_dashboard():
    return HTMLResponse(r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#101828"><meta name="description" content="Plan, create, schedule and review social media content with SocialPilot AI."><link rel="manifest" href="/manifest.webmanifest"><link rel="icon" href="/app-icon.svg" type="image/svg+xml"><title>SocialPilot AI — Dashboard</title>
<style>
:root{--bg:#f4f6fb;--ink:#182230;--muted:#667085;--line:#e4e7ec;--blue:#4263eb;--nav:#101828;--card:#fff;--green:#12b76a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);font:15px/1.45 Inter,system-ui,-apple-system,Segoe UI,sans-serif;color:var(--ink)}
header{background:var(--nav);color:#fff;padding:18px max(16px,calc((100vw - 1180px)/2));display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.brand{font-weight:800;font-size:19px;letter-spacing:-.4px}.brand span{color:#91a7ff}.status{font-size:12px;color:#d0d5dd}
.layout{max-width:1180px;margin:auto;padding:18px;display:grid;grid-template-columns:205px minmax(0,1fr);gap:18px}
nav,.card{background:var(--card);border:1px solid var(--line);border-radius:16px;box-shadow:0 2px 8px #10182808}
nav{padding:12px;height:max-content;position:sticky;top:12px}nav a{display:block;color:#344054;text-decoration:none;padding:11px 12px;border-radius:10px;margin:3px 0;font-weight:600}nav a.active,nav a:hover{background:#eef2ff;color:#3048c8}
main{min-width:0}.top{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin:4px 0 18px}.top h1{font-size:25px;margin:0;letter-spacing:-.8px}.muted{color:var(--muted);font-size:13px}
button,.btn{border:0;border-radius:10px;padding:11px 14px;background:var(--blue);color:white;font:600 14px system-ui;cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:6px}
button.secondary,.btn.secondary{background:#eef2ff;color:#3448b8}button.ghost{background:#fff;border:1px solid var(--line);color:#344054}button:disabled{opacity:.55;cursor:wait}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:16px}.metric{padding:17px}.metric .label{font-size:12px;color:var(--muted);font-weight:650}.metric .num{font-size:25px;font-weight:800;letter-spacing:-.8px;margin:8px 0 2px}.metric .hint{font-size:12px;color:var(--muted)}
.cols{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);gap:14px;margin-bottom:14px}.card{padding:18px;margin-bottom:14px}.card h2{font-size:16px;margin:0 0 5px}.cardhead{display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
label{display:block;font-weight:650;font-size:12px;color:#475467;margin:12px 0 6px}
input,select,textarea{width:100%;border:1px solid #d0d5dd;border-radius:10px;background:#fff;color:var(--ink);padding:11px 12px;font:14px system-ui;min-width:0}
textarea{resize:vertical;min-height:105px}input:focus,select:focus,textarea:focus{outline:2px solid #c7d2fe;border-color:#818cf8}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.notice{padding:11px 12px;background:#f2f4f7;border-radius:10px;font-size:13px;color:#475467;margin-top:12px;overflow-wrap:anywhere}.notice.ok{background:#ecfdf3;color:#027a48}.notice.err{background:#fef3f2;color:#b42318}
.pill{display:inline-block;border-radius:999px;background:#f2f4f7;color:#475467;padding:4px 8px;font-size:11px;font-weight:700}.pill.good{background:#ecfdf3;color:#027a48}.pill.bad{background:#fef3f2;color:#b42318}
.list{display:grid;gap:9px}.post{border:1px solid var(--line);border-radius:12px;padding:12px}.posttop{display:flex;justify-content:space-between;gap:8px;align-items:center}.post p{font-size:13px;white-space:pre-wrap;overflow-wrap:anywhere;margin:9px 0 0}.empty{padding:22px;text-align:center;color:var(--muted);border:1px dashed #d0d5dd;border-radius:12px}
footer{text-align:center;padding:12px;color:var(--muted);font-size:12px}.hidden{display:none}
@media(max-width:850px){.layout{grid-template-columns:1fr;padding:12px}nav{position:static;display:flex;overflow:auto;gap:3px;padding:7px}nav a{white-space:nowrap;margin:0;padding:9px 11px}.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.cols{grid-template-columns:1fr}header{padding:16px}.top h1{font-size:22px}}
@media(max-width:420px){.grid{gap:8px}.metric{padding:13px}.metric .num{font-size:22px}.card{padding:14px}.row{grid-template-columns:1fr}}
</style></head>
<body>
<header><div class="brand">✦ SocialPilot <span>AI</span></div><div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap"><button id="installApp" class="secondary" style="display:none" onclick="installPWA()">＋ Install app</button><div class="status" id="serviceStatus">● Checking service…</div></div></header>
<div class="layout">
<nav aria-label="Main navigation">
<a class="active" href="#overview">▦ Overview</a><a href="#create">✎ Create post</a><a href="#calendar">◷ Planner & queue</a><a href="#analytics">↗ Analytics</a><a href="/studio">▧ Design studio ↗</a><a href="/setup">⚙ Setup ↗</a>
</nav>
<main>
<section id="overview"><div class="top"><div><h1>Good work starts here.</h1><div class="muted">Your Instagram workspace at a glance.</div></div><button class="secondary" onclick="refreshAll()">↻ Refresh</button></div>
<div class="grid">
<div class="card metric"><div class="label">SERVICE</div><div class="num" id="mService">…</div><div class="hint">API availability</div></div>
<div class="card metric"><div class="label">AI TEXT</div><div class="num" id="mAI">…</div><div class="hint">Caption generation</div></div>
<div class="card metric"><div class="label">DATABASE</div><div class="num" id="mDB">…</div><div class="hint">Queue and secure tokens</div></div>
<div class="card metric"><div class="label">QUEUED POSTS</div><div class="num" id="mQueue">—</div><div class="hint">Latest queue records</div></div>
</div></section>
<section class="card" id="settings"><div class="cardhead"><div><h2>Connect your workspace</h2><div class="muted">The automation key stays in this page's memory only; it is not saved to a server or browser storage.</div></div><span class="pill">Private</span></div>
<div class="row"><div><label for="apiKey">Automation API key</label><input id="apiKey" type="password" autocomplete="off" placeholder="Paste key configured in Render"></div><div><label for="uid">Instagram account ID</label><input id="uid" inputmode="numeric" placeholder="Instagram user ID"></div></div>
<div class="actions"><button onclick="saveSettings()">Use for this session</button><button class="secondary" onclick="discoverAccounts()">Find connected account</button><a class="btn secondary" href="/auth/instagram/start">Connect Instagram ↗</a><a class="btn secondary" href="/auth/facebook/start">Facebook login ↗</a></div>
<div id="settingsMsg" class="notice">Enter your automation key and Instagram account ID to load protected reports and queue data.</div></section>
<div class="cols">
<section class="card" id="create"><div class="cardhead"><div><h2>Create content</h2><div class="muted">Generate a draft, then review before scheduling.</div></div><span class="pill">AI Studio</span></div>
<label for="topic">Post topic</label><select id="topic"><option>Automate YouTube Shorts from idea to publishing</option><option>LinkedIn lead generation workflow with AI</option><option>Meta Ads reporting automation with Google Sheets</option><option>WhatsApp lead follow-up automation</option><option>Automate social media content from research to publishing</option><option>Claude AI workflow for marketing campaign briefs</option><option>ChatGPT to Canva: turn a brief into carousel content</option><option>Google Ads weekly reporting automation</option><option>GA4 insights to an automated weekly report</option><option>Connect apps using Make without coding</option><option>Zapier workflow to capture and follow up leads</option><option>n8n workflow for content approval</option><option>MCP explained: connect AI to your work tools</option><option>AI content calendar in Google Sheets</option><option>Repurpose one long video into short-form content</option><option>Human approval step in AI automation</option></select>
<div class="actions"><button onclick="generateContent()">✦ Generate caption & carousel</button><button class="ghost" onclick="makeTemplate()">Use caption template</button></div>
<label for="content">Generated content package (editable)</label><textarea id="content" placeholder="Your AI draft will appear here…"></textarea>
<label for="caption">Instagram caption</label><textarea id="caption" placeholder="Review and edit your final caption…"></textarea>
<label for="imagePrompt">Image prompt</label><textarea id="imagePrompt" style="min-height:72px" placeholder="Describe a clean, readable workflow infographic"></textarea>
<div class="actions"><button class="secondary" onclick="generateImage()">▧ Generate image</button><button class="ghost" onclick="copyCaption()">Copy caption</button></div>
<label for="imageUrl">Public HTTPS image URL</label><input id="imageUrl" type="url" placeholder="Auto-filled after image generation">
<div id="createMsg" class="notice">AI generation requires an OpenAI API key configured on the server. API usage may cost money.</div></section>
<section class="card" id="calendar"><div class="cardhead"><div><h2>Schedule a post</h2><div class="muted">Times are shown in India time on your device.</div></div><span class="pill">Instagram</span></div>
<label for="scheduledAt">Publish date & time</label><input id="scheduledAt" type="datetime-local">
<label for="captionCheck">Ready to schedule?</label><div class="muted">Confirm your caption and image URL. Scheduling does not guarantee Meta will publish successfully.</div>
<div class="actions"><button onclick="schedulePost()">◷ Add to queue</button><button class="secondary" onclick="refreshQueue()">Refresh queue</button></div>
<div id="scheduleMsg" class="notice">Connect Instagram and configure the database before scheduling.</div>
<hr style="border:0;border-top:1px solid var(--line);margin:18px 0">
<h2>Upcoming / recent posts</h2><div class="muted" style="margin:5px 0 12px">Queue statuses are loaded from the server.</div><div id="queue" class="list"><div class="empty">Enter your key above, then refresh the queue.</div></div></section>
</div>
<section class="card" id="analytics"><div class="cardhead"><div><h2>Instagram analytics</h2><div class="muted">Recent media engagement supported by your connected Meta API permissions.</div></div><button class="secondary" onclick="loadReport()">Load report</button></div>
<div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:12px"><div class="card metric"><div class="label">RECENT POSTS</div><div class="num" id="mPosts">—</div></div><div class="card metric"><div class="label">LIKES</div><div class="num" id="mLikes">—</div></div><div class="card metric"><div class="label">COMMENTS</div><div class="num" id="mComments">—</div></div></div>
<div id="report" class="list"><div class="empty">Analytics will appear after you load the report.</div></div><div id="tips" class="notice">Note: the current API returns recent post likes and comments, not full reach, impressions or follower growth.</div></section>
<section class="card"><div class="cardhead"><div><h2>Quick links</h2><div class="muted">Use existing tools inside SocialPilot AI.</div></div></div><div class="actions"><a class="btn secondary" href="/planner">Classic planner ↗</a><a class="btn secondary" href="/studio">Post & video studio ↗</a><a class="btn secondary" href="/api/automation/status">Configuration status ↗</a><a class="btn secondary" href="/health">Health check ↗</a></div></section>
<footer>SocialPilot AI · Built for Kiran Kumar · Instagram publishing depends on Meta permissions and account eligibility.</footer>
</main></div>
<script>
const $=id=>document.getElementById(id);
let apiKey='', uid='';
function message(id,text,type=''){const el=$(id);el.textContent=text;el.className='notice'+(type?' '+type:'')}
function saveSettings(){apiKey=$('apiKey').value.trim();uid=$('uid').value.trim();if(!apiKey||!uid){message('settingsMsg','Enter both the automation API key and Instagram account ID.','err');return}message('settingsMsg','Key and account ID loaded for this page session. Protected data can now be requested.','ok');refreshAll()}
async function discoverAccounts(){apiKey=$('apiKey').value.trim();if(!apiKey){message('settingsMsg','Paste the automation API key from Render first.','err');return}message('settingsMsg','Looking up saved Instagram connections…');try{const d=await request('/api/instagram/connections');const accounts=d.connections||[];if(!accounts.length){message('settingsMsg','No Instagram account token is saved yet. Connect Instagram first; if Meta says API access blocked, live data remains unavailable until Meta restores access.','err');return}uid=accounts[0].instagram_user_id;$('uid').value=uid;message('settingsMsg','Found '+accounts.length+' saved account(s). Selected account ID '+uid+'.','ok');await refreshAll()}catch(e){message('settingsMsg',e.message,'err')}}
async function request(path,opts={}){const headers={...(opts.headers||{})};if(apiKey)headers['X-Automation-Key']=apiKey;if(opts.body)headers['Content-Type']='application/json';const res=await fetch(path,{...opts,headers});let data;try{data=await res.json()}catch{data={detail:'Unexpected server response'}}if(!res.ok)throw Error(data.detail||data.error||'Request failed ('+res.status+')');return data}
async function checkService(){try{await request('/health');$('serviceStatus').textContent='● Service online';$('serviceStatus').style.color='#a6f4c5';$('mService').textContent='Online';}catch(e){$('serviceStatus').textContent='● Service issue';$('mService').textContent='Error'}}
async function refreshStatus(){try{const d=await request('/api/automation/status');$('mAI').textContent=d.ai_text_configured?'Ready':'Off';$('mDB').textContent=d.database_configured?'Ready':'Off';}catch(e){$('mAI').textContent='—';$('mDB').textContent='—'}}
function makeTemplate(){const topic=$('topic').value;$('caption').value=topic+'\n\nSave this workflow for later and share it with someone who needs it.\n\nFollow @officialkiraankumar for practical AI automation workflows.\n\n#AIAutomation #DigitalMarketing #Automation #AITools #KiranKumar';message('createMsg','Caption template ready. Edit it before publishing.','ok')}
async function generateContent(){if(!apiKey){message('createMsg','Enter your automation key above first.','err');return}message('createMsg','Generating content…');try{const d=await request('/api/ai/generate',{method:'POST',body:JSON.stringify({topic:$('topic').value})});$('content').value=d.content;$('caption').value=d.content;const m=d.content.match(/IMAGE PROMPT\s*:\s*([\s\S]*?)(?=\n[A-Z][A-Z ]{2,}\s*:|$)/i);if(m)$('imagePrompt').value=m[1].trim();message('createMsg',d.mode==='template'?'Starter draft created in template mode. Add OPENAI_API_KEY in Render for AI-written content and image generation. Review and edit before scheduling.':'AI draft generated. Review and edit the caption before scheduling.','ok')}catch(e){message('createMsg',e.message,'err')}}
async function generateImage(){if(!apiKey){message('createMsg','Enter your automation key above first.','err');return}const prompt=$('imagePrompt').value.trim();if(!prompt){message('createMsg','Enter an image prompt first or generate the content package.','err');return}message('createMsg','Generating and storing image…');try{const d=await request('/api/ai/image',{method:'POST',body:JSON.stringify({prompt})});$('imageUrl').value=d.image_url;message('createMsg','Image generated and stored. You can now schedule it.','ok')}catch(e){message('createMsg',e.message,'err')}}
async function schedulePost(){if(!apiKey||!uid){message('scheduleMsg','Enter your automation key and Instagram account ID above.','err');return}const image=$('imageUrl').value.trim(),when=$('scheduledAt').value,caption=$('caption').value.trim();if(!image.startsWith('https://')){message('scheduleMsg','Generate an image or enter a public HTTPS image URL.','err');return}if(!when){message('scheduleMsg','Choose a future date and time.','err');return}try{const d=await request('/api/posts/schedule',{method:'POST',body:JSON.stringify({topic:$('topic').value,caption,image_url:image,instagram_user_id:uid,scheduled_at:new Date(when).toISOString()})});message('scheduleMsg','Post #'+d.post_id+' added to queue with status: '+d.status+'.','ok');await refreshQueue()}catch(e){message('scheduleMsg',e.message,'err')}}
async function refreshQueue(){if(!apiKey){$('queue').innerHTML='<div class="empty">Enter the automation key first.</div>';return}try{const d=await request('/api/posts');$('mQueue').textContent=d.posts.length;const posts=d.posts||[];if(!posts.length){$('queue').innerHTML='<div class="empty">No scheduled posts yet. Create one using the form above.</div>';return}$('queue').innerHTML=posts.map(p=>'<article class="post"><div class="posttop"><strong>#'+p.id+' · '+esc(p.scheduled_at)+'</strong><span class="pill '+(p.status==='published'?'good':p.status==='failed'?'bad':'')+'">'+esc(p.status)+'</span></div><p>'+esc(p.caption||'')+'</p>'+(p.last_error?'<div class="notice err">'+esc(p.last_error)+'</div>':'')+'</article>').join('')}catch(e){$('queue').innerHTML='<div class="notice err">'+esc(e.message)+'</div>';message('scheduleMsg',e.message,'err')}}
async function loadReport(){if(!apiKey||!uid){message('settingsMsg','Enter your automation key and Instagram account ID above.','err');return}message('tips','Loading Instagram report…');try{const d=await request('/api/reports/instagram?instagram_user_id='+encodeURIComponent(uid));$('mPosts').textContent=d.posts_returned;$('mLikes').textContent=d.likes_total;$('mComments').textContent=d.comments_total;$('report').innerHTML=(d.posts||[]).map(p=>'<article class="post"><div class="posttop"><strong>'+esc(p.published_at||'Post')+'</strong><span class="pill">♥ '+p.likes+' · Comments '+p.comments+'</span></div><p>'+esc(p.caption||'')+'</p>'+(p.permalink?'<a href="'+safeUrl(p.permalink)+'" target="_blank" rel="noopener">Open Instagram post ↗</a>':'')+'</article>').join('')||'<div class="empty">No recent media returned.</div>';message('tips',(d.growth_recommendations||[]).join(' • ')+' | '+(d.note||''),'ok')}catch(e){$('report').innerHTML='<div class="notice err">'+esc(e.message)+'</div>';message('tips','Analytics unavailable until the account, token and permissions are configured.','err')}}
function copyCaption(){const c=$('caption').value;if(!c){message('createMsg','There is no caption to copy yet.','err');return}if(navigator.clipboard&&navigator.clipboard.writeText)navigator.clipboard.writeText(c).then(()=>message('createMsg','Caption copied.','ok')).catch(()=>fallbackCopy(c));else fallbackCopy(c)}
function fallbackCopy(c){const t=document.createElement('textarea');t.value=c;document.body.appendChild(t);t.select();try{document.execCommand('copy');message('createMsg','Caption copied.','ok')}catch(e){message('createMsg','Copy unavailable; select and copy the caption manually.','err')}t.remove()}
function esc(s){return String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
function safeUrl(s){try{const u=new URL(s);return u.protocol==='https:'?u.href:'#'}catch(e){return '#'}}
async function refreshAll(){await checkService();await refreshStatus();if(apiKey&&uid){await refreshQueue();await loadReport()}}
let installPrompt=null;
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;$('installApp').style.display='inline-flex'});
async function installPWA(){if(!installPrompt){message('settingsMsg','On Android Chrome, open the browser menu and choose Install app or Add to Home screen.','');return}installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;$('installApp').style.display='none'}
if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}))}
checkService();refreshStatus();
</script></body></html>""")


@router.get("/manifest.webmanifest", include_in_schema=False)
async def app_manifest():
    return Response(
        content='{"id":"/dashboard","name":"SocialPilot AI","short_name":"SocialPilot","description":"Create, plan and manage social content","start_url":"/dashboard","scope":"/","display":"standalone","background_color":"#f4f6fb","theme_color":"#101828","icons":[{"src":"/app-icon.svg","sizes":"any","type":"image/svg+xml","purpose":"any maskable"}]}',
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/app-icon.svg", include_in_schema=False)
async def app_icon():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="112" fill="#101828"/><path d="M256 74 300 190 420 234 300 278 256 398 212 278 92 234 212 190Z" fill="#91a7ff"/><circle cx="256" cy="234" r="36" fill="#fff"/></svg>'
    return Response(content=svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})


@router.get("/sw.js", include_in_schema=False)
async def service_worker():
    script = """
const CACHE = 'socialpilot-shell-v1';
const SHELL = ['/dashboard', '/studio', '/planner', '/setup', '/app-icon.svg', '/manifest.webmanifest'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/auth/') || url.pathname === '/mcp') return;
  event.respondWith(fetch(request).then(response => {
    if (response.ok && (url.pathname === '/dashboard' || url.pathname === '/studio' || url.pathname === '/planner' || url.pathname === '/setup' || url.pathname === '/app-icon.svg' || url.pathname === '/manifest.webmanifest')) {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(request, copy));
    }
    return response;
  }).catch(async () => {
    const cached = await caches.match(request);
    return cached || caches.match('/dashboard');
  }));
});
"""
    return Response(content=script, media_type="application/javascript", headers={"Cache-Control": "no-cache"})
