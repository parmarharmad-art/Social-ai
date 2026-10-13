"""Built-in, mobile-friendly social post and short-video studio."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

STUDIO_HTML = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>SocialPilot AI Studio</title>
<style>
:root{color-scheme:dark;--bg:#09111f;--panel:#111d30;--line:#2b3b53;--blue:#3984ff;--text:#edf4ff;--muted:#9aabc4}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px system-ui,-apple-system,Segoe UI,sans-serif}
header{position:sticky;top:0;z-index:5;background:#0c1728;border-bottom:1px solid var(--line);padding:12px 16px;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
h1{font-size:18px;margin:0}header small{color:var(--muted)}main{max-width:1320px;margin:auto;padding:14px;display:grid;grid-template-columns:300px minmax(280px,1fr) 260px;gap:14px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px;min-width:0}.panel h2{font-size:14px;margin:0 0 10px}.group{padding-bottom:14px;margin-bottom:14px;border-bottom:1px solid var(--line)}label{display:block;color:var(--muted);font-size:12px;margin:8px 0 5px}
input,select,textarea{width:100%;background:#081322;color:var(--text);border:1px solid #354863;border-radius:8px;padding:10px;font:inherit}textarea{resize:vertical;min-height:64px}
button,.button{cursor:pointer;border:0;border-radius:9px;padding:10px 12px;font:inherit;background:var(--blue);color:white;display:inline-flex;align-items:center;justify-content:center;gap:6px;text-decoration:none}
button.secondary{background:#24364e}button.warn{background:#8f3445}button:disabled{opacity:.5;cursor:default}.btnrow{display:flex;gap:7px;flex-wrap:wrap}.btnrow button{flex:1}
.center{display:flex;flex-direction:column;gap:10px;align-items:center}.toolbar{display:flex;gap:7px;flex-wrap:wrap;justify-content:center}
.stagewrap{width:100%;max-width:570px;background:#07101d;border:1px solid var(--line);border-radius:12px;padding:10px;display:flex;justify-content:center;align-items:center}
canvas{display:block;width:100%;height:auto;max-height:72vh;object-fit:contain;touch-action:none;background:#fff;border-radius:4px}
.hint{color:var(--muted);font-size:12px;line-height:1.5}.status{min-height:36px;color:#9bd4ff;font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere}
.template{width:100%;text-align:left;background:#1c2c43;margin:4px 0}.template strong{display:block}.template small{color:#b8c7dc}
.pill{border:1px solid #355075;color:#b9d4ff;border-radius:99px;padding:4px 8px;font-size:11px}
@media(max-width:950px){main{grid-template-columns:1fr}.center{order:-1}.stagewrap{max-width:540px}.panel{width:100%}header{position:static}canvas{max-height:none}}
</style></head>
<body>
<header><div><h1>SocialPilot AI · Studio</h1><small>Built-in post designer + short-video maker · no Canva account required</small></div><div class="btnrow"><a class="button" href="/planner">Content Planner</a><a class="button" href="/health">Service status</a></div></header>
<main>
<aside class="panel">
<div class="group"><h2>Start with a template</h2>
<button class="template" onclick="useTemplate('automation')"><strong>AI Automation Workflow</strong><small>Dark SaaS infographic · 4:5</small></button>
<button class="template" onclick="useTemplate('tip')"><strong>One Practical Tip</strong><small>Big headline + takeaway</small></button>
<button class="template" onclick="useTemplate('quote')"><strong>Bold Creator Post</strong><small>Minimal text-led design</small></button>
<button class="template" onclick="useTemplate('video')"><strong>Short Video Cover</strong><small>Vertical reel-style title</small></button>
</div>
<div class="group"><h2>Add elements</h2><div class="btnrow"><button onclick="addText()">＋ Text</button><button class="secondary" onclick="addShape()">＋ Shape</button></div>
<label>Upload photo/logo/background</label><input type="file" id="upload" accept="image/*">
<label>Background colour</label><input id="bg" type="color" value="#0b1730" onchange="state.bg=this.value;draw()">
<label>Canvas format</label><select id="format" onchange="changeFormat()"><option value="post">Instagram post · 1080×1350</option><option value="square">Square · 1080×1080</option><option value="story">Story/Reel · 1080×1920</option><option value="landscape">Landscape · 1920×1080</option></select>
</div>
<div class="group"><h2>AI helpers</h2>
<label>Automation API key (only used for this request)</label><input id="key" type="password" autocomplete="off" placeholder="Server automation key">
<label>Topic or brief</label><textarea id="brief" placeholder="e.g. 5 steps to automate Instagram lead follow-up"></textarea>
<div class="btnrow"><button onclick="makeAIContent()">Generate copy</button><button class="secondary" onclick="makeAIImage()">Generate image</button></div>
<p class="hint">AI buttons need the configured server AI API and may incur usage charges. You can design, edit and export without AI.</p>
</div>
<div class="group"><h2>Save & export</h2><div class="btnrow"><button onclick="exportPNG()">Download PNG</button><button class="secondary" onclick="saveProject()">Save project</button></div>
<div class="btnrow"><button class="secondary" onclick="loadProject()">Load saved</button><button class="secondary" onclick="downloadProject()">Export JSON</button></div>
<label>Video length</label><select id="duration"><option value="6">6 seconds</option><option value="10">10 seconds</option><option value="15">15 seconds</option></select>
<button style="width:100%;margin-top:8px" onclick="exportVideo()">Create animated video (WebM)</button>
<p class="hint">Video export uses your browser. It downloads WebM; MP4 conversion and AI voice generation are not included in this first built-in version.</p>
</div>
</aside>
<section class="center">
<div class="toolbar"><span class="pill" id="dims">1080 × 1350</span><button class="secondary" onclick="undo()">Undo</button><button class="secondary" onclick="redo()">Redo</button><button class="secondary" onclick="duplicate()">Duplicate selected</button><button class="warn" onclick="deleteSelected()">Delete selected</button></div>
<div class="stagewrap"><canvas id="canvas" width="540" height="675" aria-label="Editable design canvas"></canvas></div>
<p class="hint">Tap an element to select it. Drag to reposition. Select text to edit it in the right panel. Export PNG or an animated WebM video.</p>
<div id="status" class="status" role="status">Ready. Choose a template or add your own text and images.</div>
</section>
<aside class="panel">
<div class="group"><h2>Selected element</h2>
<label>Text</label><textarea id="text" placeholder="Select a text element" oninput="updateSelected('text',this.value)"></textarea>
<label>Text / shape colour</label><input type="color" id="color" value="#ffffff" onchange="updateSelected('color',this.value)">
<label>Font size</label><input type="range" id="fontSize" min="12" max="100" value="38" oninput="updateSelected('fontSize',+this.value)">
<label>Font weight</label><select id="weight" onchange="updateSelected('weight',this.value)"><option value="400">Regular</option><option value="600">Semi-bold</option><option value="800">Bold</option><option value="900">Extra bold</option></select>
<label>Alignment</label><select id="align" onchange="updateSelected('align',this.value)"><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select>
<label>Element width (%)</label><input type="range" id="width" min="10" max="100" value="80" oninput="updateSelected('w',+this.value/100*state.w)">
<label>Element opacity</label><input type="range" id="opacity" min="10" max="100" value="100" oninput="updateSelected('opacity',+this.value/100)">
<div class="btnrow"><button class="secondary" onclick="moveLayer(-1)">Send backward</button><button class="secondary" onclick="moveLayer(1)">Bring forward</button></div>
</div>
<div class="group"><h2>Brand kit</h2>
<label>Brand / watermark</label><input id="brand" value="Kiran Kumar • AI Automation">
<button style="width:100%;margin-top:8px" onclick="addBrand()">Add brand watermark</button>
<p class="hint">Brand text can be changed for each project.</p>
</div>
<div><h2>Scene / video notes</h2><p class="hint">Video export animates the current design as a short vertical clip with a subtle motion effect. For multi-scene videos, create and export separate scenes, then assemble in a future version.</p></div>
</aside>
</main>
<script>
const canvas=document.getElementById('canvas'),ctx=canvas.getContext('2d');
let state={w:1080,h:1350,bg:'#0b1730',items:[],selected:null};
let history=[],future=[],drag=null;
function status(s){document.getElementById('status').textContent=s}
function snapshot(){history.push(JSON.stringify(state));if(history.length>40)history.shift();future=[]}
function scale(){return canvas.width/state.w}
function draw(){ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle=state.bg;ctx.fillRect(0,0,canvas.width,canvas.height);
for(const it of state.items){ctx.save();ctx.globalAlpha=it.opacity??1;
if(it.type==='image'&&it.src){const im=new Image();im.onload=()=>{ctx.save();ctx.globalAlpha=it.opacity??1;ctx.drawImage(im,it.x*scale(),it.y*scale(),it.w*scale(),it.h*scale());ctx.restore();if(state.selected===it.id)selection(it)};im.src=it.src;}
else if(it.type==='shape'){ctx.fillStyle=it.color||'#3984ff';roundRect(ctx,it.x*scale(),it.y*scale(),it.w*scale(),it.h*scale(),it.radius||18);ctx.fill()}
else if(it.type==='text'){ctx.fillStyle=it.color||'#fff';ctx.font=(it.weight||700)+' '+(it.fontSize||40)*scale()+'px system-ui, sans-serif';ctx.textAlign=it.align||'left';ctx.textBaseline='top';const maxW=it.w*scale();let y=it.y*scale();const lines=wrap(it.text||'',maxW);for(const line of lines){ctx.fillText(line,(it.align==='center'?it.x*scale()+maxW/2:it.align==='right'?it.x*scale()+maxW:it.x*scale()),y);y+=(it.fontSize||40)*scale()*1.18}}
ctx.restore();if(state.selected===it.id&&it.type!=='image')selection(it)}
}
function roundRect(c,x,y,w,h,r){c.beginPath();c.roundRect(x,y,w,h,r)}
function wrap(text,max){const out=[];for(const para of String(text).split('\n')){let line='';for(const word of para.split(/\s+/)){const test=line?line+' '+word:word;if(ctx.measureText(test).width>max&&line){out.push(line);line=word}else line=test}out.push(line)}return out}
function selection(it){ctx.save();ctx.strokeStyle='#47a5ff';ctx.lineWidth=2;ctx.setLineDash([5,4]);ctx.strokeRect(it.x*scale(),it.y*scale(),it.w*scale(),it.h*scale());ctx.setLineDash([]);ctx.restore()}
function addText(text='Your headline here'){snapshot();const it={id:crypto.randomUUID(),type:'text',text,x:90,y:120,w:900,h:220,fontSize:64,weight:800,color:'#ffffff',align:'left',opacity:1};state.items.push(it);state.selected=it.id;draw();syncControls()}
function addShape(){snapshot();const it={id:crypto.randomUUID(),type:'shape',x:100,y:450,w:880,h:170,color:'#2877ee',radius:24,opacity:1};state.items.push(it);state.selected=it.id;draw();syncControls()}
function addBrand(){snapshot();state.items.push({id:crypto.randomUUID(),type:'text',text:document.getElementById('brand').value||'Kiran Kumar • AI Automation',x:65,y:state.h-75,w:950,h:45,fontSize:25,weight:600,color:'#9ed5ff',align:'left',opacity:.95});state.selected=state.items[state.items.length-1].id;draw();syncControls()}
function updateSelected(k,v){const it=state.items.find(i=>i.id===state.selected);if(!it)return;it[k]=v;draw()}
function syncControls(){const it=state.items.find(i=>i.id===state.selected);document.getElementById('text').value=it?.type==='text'?it.text:'';document.getElementById('color').value=/^#[0-9a-f]{6}$/i.test(it?.color||'')?it.color:'#ffffff';document.getElementById('fontSize').value=it?.fontSize||38;document.getElementById('weight').value=it?.weight||800;document.getElementById('align').value=it?.align||'left';document.getElementById('width').value=it?Math.round(it.w/state.w*100):80;document.getElementById('opacity').value=Math.round((it?.opacity??1)*100)}
function hit(x,y){for(let i=state.items.length-1;i>=0;i--){const it=state.items[i];if(x>=it.x&&x<=it.x+it.w&&y>=it.y&&y<=it.y+it.h)return it}return null}
function coords(e){const r=canvas.getBoundingClientRect();return{x:(e.clientX-r.left)*state.w/r.width,y:(e.clientY-r.top)*state.h/r.height}}
canvas.addEventListener('pointerdown',e=>{const p=coords(e),it=hit(p.x,p.y);state.selected=it?.id||null;drag=it?{id:it.id,x:p.x,y:p.y,ix:it.x,iy:it.y}:null;if(drag){snapshot();canvas.setPointerCapture(e.pointerId)}syncControls();draw()});
canvas.addEventListener('pointermove',e=>{if(!drag)return;const p=coords(e),it=state.items.find(i=>i.id===drag.id);if(it){it.x=Math.max(0,Math.min(state.w-it.w,drag.ix+p.x-drag.x));it.y=Math.max(0,Math.min(state.h-it.h,drag.iy+p.y-drag.y));draw()}});
canvas.addEventListener('pointerup',()=>{drag=null});
document.getElementById('upload').addEventListener('change',e=>{const f=e.target.files?.[0];if(!f)return;const reader=new FileReader();reader.onload=()=>{const im=new Image();im.onload=()=>{snapshot();const ratio=Math.min(900/im.width,600/im.height);const it={id:crypto.randomUUID(),type:'image',src:reader.result,x:90,y:150,w:im.width*ratio,h:im.height*ratio,opacity:1};state.items.push(it);state.selected=it.id;draw();syncControls();status('Image added. Drag it to reposition.');};im.src=reader.result};reader.readAsDataURL(f)});
function changeFormat(){snapshot();const f=document.getElementById('format').value;const dims={post:[1080,1350],square:[1080,1080],story:[1080,1920],landscape:[1920,1080]}[f];state.w=dims[0];state.h=dims[1];canvas.width=540;canvas.height=Math.round(540*state.h/state.w);document.getElementById('dims').textContent=state.w+' × '+state.h;draw()}
function useTemplate(type){snapshot();const w=state.w,h=state.h;state.items=[];state.selected=null;
if(type==='automation'){state.bg='#09172d';state.items=[{id:crypto.randomUUID(),type:'shape',x:w*.07,y:h*.07,w:w*.86,h:h*.86,color:'#122b4c',radius:36,opacity:1},{id:crypto.randomUUID(),type:'text',text:'AI AUTOMATION',x:w*.12,y:h*.13,w:w*.78,h:h*.12,fontSize:w*.075,weight:900,color:'#68c9ff',align:'left',opacity:1},{id:crypto.randomUUID(),type:'text',text:'From manual work\\nto smart workflows',x:w*.12,y:h*.27,w:w*.78,h:h*.25,fontSize:w*.09,weight:800,color:'#ffffff',align:'left',opacity:1},{id:crypto.randomUUID(),type:'text',text:'TRIGGER  →  AI  →  ACTION\\n\\n1. Capture the request\\n2. Let AI draft the result\\n3. Review and approve\\n4. Automate the repeat task',x:w*.12,y:h*.56,w:w*.76,h:h*.25,fontSize:w*.038,weight:600,color:'#c8dcf5',align:'left',opacity:1},{id:crypto.randomUUID(),type:'text',text:'Kiran Kumar • AI Automation',x:w*.12,y:h*.86,w:w*.78,h:h*.04,fontSize:w*.025,weight:600,color:'#68c9ff',align:'left',opacity:1}]}
else if(type==='tip'){state.bg='#f2f6fc';state.items=[{id:crypto.randomUUID(),type:'text',text:'ONE PRACTICAL TIP',x:w*.09,y:h*.12,w:w*.82,h:h*.08,fontSize:w*.045,weight:900,color:'#1765d1',align:'left',opacity:1},{id:crypto.randomUUID(),type:'text',text:'Automate the\\nboring first.',x:w*.09,y:h*.27,w:w*.82,h:h*.24,fontSize:w*.105,weight:900,color:'#0d1d33',align:'left',opacity:1},{id:crypto.randomUUID(),type:'shape',x:w*.09,y:h*.61,w:w*.82,h:h*.19,color:'#dcecff',radius:24,opacity:1},{id:crypto.randomUUID(),type:'text',text:'Pick one repeated task. Write the steps. Automate only after the manual process works.',x:w*.14,y:h*.65,w:w*.72,h:h*.13,fontSize:w*.039,weight:600,color:'#173453',align:'left',opacity:1},{id:crypto.randomUUID(),type:'text',text:'Kiran Kumar • AI Automation',x:w*.09,y:h*.88,w:w*.82,h:h*.04,fontSize:w*.026,weight:600,color:'#1765d1',align:'left',opacity:1}]}
else if(type==='quote'){state.bg='#25134a';state.items=[{id:crypto.randomUUID(),type:'text',text:'BUILD SMARTER.',x:w*.09,y:h*.2,w:w*.82,h:h*.1,fontSize:w*.085,weight:900,color:'#c5a6ff',align:'left',opacity:1},{id:crypto.randomUUID(),type:'text',text:'Don’t automate\\nchaos. Improve the\\nworkflow first.',x:w*.09,y:h*.34,w:w*.82,h:h*.32,fontSize:w*.085,weight:900,color:'#ffffff',align:'left',opacity:1},{id:crypto.randomUUID(),type:'text',text:'Kiran Kumar • AI Automation',x:w*.09,y:h*.84,w:w*.82,h:h*.05,fontSize:w*.027,weight:600,color:'#d9c9ff',align:'left',opacity:1}]}
else {state.bg='#06172d';state.items=[{id:crypto.randomUUID(),type:'shape',x:w*.07,y:h*.07,w:w*.86,h:h*.86,color:'#112f50',radius:36,opacity:1},{id:crypto.randomUUID(),type:'text',text:'AI WORKFLOW',x:w*.1,y:h*.24,w:w*.8,h:h*.1,fontSize:w*.06,weight:800,color:'#65d6ff',align:'center',opacity:1},{id:crypto.randomUUID(),type:'text',text:'ONE IDEA.\\nTHREE SMART STEPS.',x:w*.1,y:h*.38,w:w*.8,h:h*.24,fontSize:w*.09,weight:900,color:'#ffffff',align:'center',opacity:1},{id:crypto.randomUUID(),type:'text',text:'Save this Reel for later',x:w*.1,y:h*.72,w:w*.8,h:h*.06,fontSize:w*.035,weight:600,color:'#c9d9ee',align:'center',opacity:1}]}
state.selected=state.items[1]?.id||state.items[0]?.id;document.getElementById('bg').value=state.bg;draw();syncControls();status('Template loaded. Tap text to edit, then export.')}
function deleteSelected(){if(!state.selected)return;snapshot();state.items=state.items.filter(i=>i.id!==state.selected);state.selected=null;draw();syncControls()}
function duplicate(){const it=state.items.find(i=>i.id===state.selected);if(!it)return;snapshot();const c=JSON.parse(JSON.stringify(it));c.id=crypto.randomUUID();c.x=Math.min(state.w-c.w,c.x+30);c.y=Math.min(state.h-c.h,c.y+30);state.items.push(c);state.selected=c.id;draw();syncControls()}
function moveLayer(d){const i=state.items.findIndex(it=>it.id===state.selected);if(i<0)return;snapshot();const j=Math.max(0,Math.min(state.items.length-1,i+d));const [it]=state.items.splice(i,1);state.items.splice(j,0,it);draw()}
function undo(){if(!history.length)return;future.push(JSON.stringify(state));state=JSON.parse(history.pop());draw();syncControls()}
function redo(){if(!future.length)return;history.push(JSON.stringify(state));state=JSON.parse(future.pop());draw();syncControls()}
function exportPNG(){draw();const a=document.createElement('a');a.download='socialpilot-design.png';a.href=canvas.toDataURL('image/png');a.click();status('PNG downloaded.')}
function saveProject(){localStorage.setItem('socialpilot-studio-project',JSON.stringify(state));status('Project saved in this browser on this device.')}
function loadProject(){const raw=localStorage.getItem('socialpilot-studio-project');if(!raw){status('No saved project found on this device.');return}state=JSON.parse(raw);canvas.width=540;canvas.height=Math.round(540*state.h/state.w);document.getElementById('dims').textContent=state.w+' × '+state.h;document.getElementById('bg').value=state.bg;draw();syncControls();status('Saved project loaded.')}
function downloadProject(){const b=new Blob([JSON.stringify(state,null,2)],{type:'application/json'}),a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='socialpilot-project.json';a.click();URL.revokeObjectURL(a.href)}
async function makeAIContent(){try{const key=document.getElementById('key').value.trim(),topic=document.getElementById('brief').value.trim();if(!key||!topic)throw Error('Enter the server automation key and a topic.');status('Generating copy…');const r=await fetch('/api/ai/generate',{method:'POST',headers:{'Content-Type':'application/json','X-Automation-Key':key},body:JSON.stringify({topic})}),d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');const text=d.content.split(/CAPTION:/i)[0].replace(/HOOK:|SLIDE \d+:/gi,'').trim();snapshot();const it={id:crypto.randomUUID(),type:'text',text:text.slice(0,850),x:Math.round(state.w*.09),y:Math.round(state.h*.14),w:Math.round(state.w*.82),h:Math.round(state.h*.62),fontSize:Math.round(state.w*.044),weight:700,color:state.bg==='#f2f6fc'?'#10243c':'#ffffff',align:'left',opacity:1};state.items.push(it);state.selected=it.id;draw();syncControls();status('AI copy added to canvas. Edit for readability before export.')}catch(e){status('AI copy failed: '+e.message)}}
async function makeAIImage(){try{const key=document.getElementById('key').value.trim(),prompt=document.getElementById('brief').value.trim();if(!key||!prompt)throw Error('Enter the server automation key and an image brief.');status('Generating image…');const r=await fetch('/api/ai/image',{method:'POST',headers:{'Content-Type':'application/json','X-Automation-Key':key},body:JSON.stringify({prompt})}),d=await r.json();if(!r.ok)throw Error(d.detail||'Request failed');const resp=await fetch(d.image_url),blob=await resp.blob(),reader=new FileReader();reader.onload=()=>{const im=new Image();im.onload=()=>{snapshot();const ratio=Math.min(state.w*.8/im.width,state.h*.5/im.height),it={id:crypto.randomUUID(),type:'image',src:reader.result,x:state.w*.1,y:state.h*.2,w:im.width*ratio,h:im.height*ratio,opacity:1};state.items.push(it);state.selected=it.id;draw();syncControls();status('Generated image added to the canvas.')} ;im.src=reader.result};reader.readAsDataURL(blob)}catch(e){status('AI image failed: '+e.message)}}
function exportVideo(){if(!canvas.captureStream||!window.MediaRecorder){status('This browser does not support in-browser video export. Try Chrome on Android or desktop.');return}const secs=+document.getElementById('duration').value;draw();let stream;try{stream=canvas.captureStream(30)}catch(e){status('Video export could not start: '+e.message);return}const mime=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(t=>MediaRecorder.isTypeSupported(t));if(!mime){status('This browser has no supported WebM encoder.');return}const rec=new MediaRecorder(stream,{mimeType:mime}),chunks=[];rec.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};rec.onstop=()=>{const blob=new Blob(chunks,{type:mime}),a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='socialpilot-video.webm';a.click();stream.getTracks().forEach(t=>t.stop());status('Animated video exported as WebM. MP4 is not produced by this browser-only editor.')};rec.start();const start=performance.now();function frame(now){const t=(now-start)/1000;ctx.save();ctx.clearRect(0,0,canvas.width,canvas.height);ctx.translate(0,Math.sin(t*1.4)*4);draw();ctx.restore();if(t<secs)requestAnimationFrame(frame);else rec.stop()}requestAnimationFrame(frame);status('Recording animated video for '+secs+' seconds… keep this page open.')}
useTemplate('automation');
</script></body></html>'''


@router.get("/studio", response_class=HTMLResponse)
async def design_studio():
    return HTMLResponse(STUDIO_HTML)
