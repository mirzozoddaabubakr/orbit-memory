// Orthographic projection of a rotatable orbital plane, with shaded sphere textures.
const TAU = 2*Math.PI;
function random(seed){return ()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};}
const rng=random(5122);
const dust=Array.from({length:1150},()=>[rng(),rng(),rng(),rng()]);
const hash=(x,y,z)=>{const n=Math.sin(x*127.1+y*311.7+z*74.7)*43758.5453;return n-Math.floor(n);};
function noise(x,y,z){
 const ix=Math.floor(x),iy=Math.floor(y),iz=Math.floor(z);
 const ease=t=>t*t*(3-2*t), a=ease(x-ix),b=ease(y-iy),c=ease(z-iz);
 let sum=0;
 for(let k=0;k<2;k++)for(let j=0;j<2;j++)for(let i=0;i<2;i++)
   sum+=hash(ix+i,iy+j,iz+k)*(i?a:1-a)*(j?b:1-b)*(k?c:1-c);
 return sum;
}
function fbm(x,y,z){return .54*noise(x,y,z)+.29*noise(x*2.1,y*2.1,z*2.1)+.17*noise(x*4.4,y*4.4,z*4.4);}
const textures=new Map();
function sphere(kind){
 if(textures.has(kind))return textures.get(kind);
 const sz=kind==='sun'?240:128,cn=document.createElement('canvas');cn.width=cn.height=sz;
 const ctx=cn.getContext('2d'),im=ctx.createImageData(sz,sz),data=im.data;
 const palettes={ocean:[[21,50,90],[97,155,194]],ember:[[85,42,45],[229,153,119]],violet:[[53,44,90],[175,156,211]],gas:[[91,65,49],[232,192,143]],ice:[[26,70,76],[149,205,196]],stone:[[54,58,76],[172,173,185]]};
 for(let j=0;j<sz;j++)for(let i=0;i<sz;i++){
  const x=(i+.5-sz/2)/(sz/2-1),y=(j+.5-sz/2)/(sz/2-1),d=x*x+y*y;
  if(d>=1)continue;
  const z=Math.sqrt(1-d),off=(j*sz+i)*4,u=Math.atan2(x,z),v=Math.asin(y);
  const n=fbm(x*5+14,y*5,z*5+3),fine=noise(x*70,y*70,z*70);
  let rgb;
  if(kind==='sun'){
    const sw=fbm(x*9+n*3,y*9+n*3,z*9),net=Math.abs(Math.sin((n*4+sw)*10));
    const hot=Math.max(0,Math.min(1,.12+n*.55+sw*.28+net*.22+fine*.17));
    rgb=[239+hot*21,72+hot*153,16+hot*90].map((v,i)=>v+(i?1:0)*Math.pow(1-z,5)*33);
  }else{
    const [lo,hi]=palettes[kind];
    let v0=.2+n*.8; if(kind==='gas'||kind==='violet')v0=.37+.33*Math.sin(v*31+n*3+x*.9)+.17*Math.sin(v*69+n*4)+.15*n;
    if(kind==='ocean')v0=n>.53?.85:.25;
    const light=Math.max(0,-x*.60-y*.42+z*.48),shade=.14+.90*light;
    rgb=lo.map((a,k)=>(a+(hi[k]-a)*v0+(fine-.5)*23)*shade+Math.pow(1-z,5)*24);
    if(kind==='ocean' && n>.58)rgb=rgb.map((a,k)=>a+[21,28,4][k]*shade);
  }
  for(let k=0;k<3;k++)data[off+k]=rgb[k];data[off+3]=Math.min(255,(1-Math.sqrt(d))*sz*210);
 }
 ctx.putImageData(im,0,0);textures.set(kind,cn);return cn;
}
const forms=['ember','ocean','violet','ice','gas','stone'];
const arrangements=[[.57,3.93,18],[.83,2.86,27],[.39,-.55,15],[.76,1.18,17],[.97,.11,24],[.85,4.93,11]];
export function mountUniverse(host,items,openMemory){
 const canvas=host.querySelector('canvas'),layer=host.querySelector('.planet-labels'),ctx=canvas.getContext('2d');
 const backdrop=host.classList.contains('first-memory');
 let angle=0, tilt=.34,zoom=1,drag=null,points=[],raf=0,expanded=false;
 const buttons=items.map((item,i)=>{const btn=document.createElement('button');btn.className='planet-label';btn.title=item.title;btn.textContent=item.title;btn.onclick=()=>openMemory(item.id);layer.append(btn);return btn;});
 function draw(){
  const W=canvas.clientWidth,H=canvas.clientHeight,dpr=Math.min(devicePixelRatio||1,2);
  canvas.width=Math.round(W*dpr);canvas.height=Math.round(H*dpr);ctx.scale(dpr,dpr);
  const sc=Math.min(W/1040,H/370),cx=backdrop?W*(W<540?.68:.76):W*.495,
    cy=backdrop?H*(W<540?.27:.44):H*.50,base=Math.min(W*.45,H*1.34)*zoom;
  ctx.fillStyle='#0b0d15';ctx.fillRect(0,0,W,H);
  function halo(x,y,r,c){const g=ctx.createRadialGradient(x,y,0,x,y,r);c.forEach(([s,col])=>g.addColorStop(s,col));ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2);}
  halo(W*.58,H*.44,W*.59,[[0,'#222136'],[.5,'#141523'],[1,'rgba(8,10,17,0)']]);
  for(const [x,y,z,p] of dust){const sx=x*W,sy=y*H;ctx.fillStyle='rgba('+ (p>.82?'244,202,162':'192,202,228')+','+(.12+z*z*.69)+')';ctx.beginPath();ctx.arc(sx,sy,.28+z*z*.76,0,TAU);ctx.fill();if(z>.992){ctx.fillRect(sx-2.5,sy-.29,5,.58);ctx.fillRect(sx-.29,sy-2.5,.58,5);}}
  const rot=-.18,co=Math.cos(rot),si=Math.sin(rot);
  const pos=(r,a)=>{const X=r*base*Math.cos(a+angle),Y=r*base*Math.sin(a+angle)*tilt;return {x:cx+X*co-Y*si,y:cy+X*si+Y*co,depth:Math.sin(a+angle)};};
  for(const r of [.24,.39,.57,.76,.83,.97,1.13,1.34]){
    ctx.beginPath();ctx.ellipse(cx,cy,base*r,base*r*tilt,rot,0,TAU);ctx.lineWidth=.8;ctx.strokeStyle='rgba(160,158,190,'+(r>1?.14:.30)+')';ctx.stroke();
  }
  const seed=random(678);
  for(let j=0;j<480;j++){const p=pos(.665+(seed()-.5)*.075,seed()*TAU);ctx.fillStyle='rgba(194,175,154,'+(.08+seed()*.48)+')';ctx.fillRect(p.x,p.y,.65+seed()*.95,.8);}
  const sunR=backdrop?Math.min(W*.115,H*.19):Math.max(23,Math.min(46,42*sc))*zoom;
  points=items.map((item,i)=>{const [r,a,sz]=arrangements[i]||[.26+((i*.223)% .82),i*2.39996,9];return {...pos(r,a),i,radius:Math.max(7,sz*sc)*zoom,kind:forms[i%6]};});
  const stars=items.filter(item=>item.isStar);
  if(stars.length){
    const centers=new Map(stars.map((star,j)=>[star.id,pos(stars.length===1?0:.67,j*TAU/stars.length)]));
    points=points.map((point,i)=>{
      const item=items[i],center=centers.get(item.isStar?item.id:item.project_id);
      if(!center)return point;
      if(item.isStar)return {...point,...center,kind:'sun',radius:Math.max(15,25*sc)*zoom};
      const siblings=items.filter(chat=>chat.project_id===item.project_id),j=siblings.indexOf(item);
      const r=.12+.045*(j%3),offset=pos(r,j*2.4);
      ctx.beginPath();ctx.ellipse(center.x,center.y,base*r,base*r*tilt,rot,0,TAU);ctx.stroke();
      return {...point,x:center.x+offset.x-cx,y:center.y+offset.y-cy,radius:Math.max(5,9*sc)*zoom};
    });
  }
  const objects=[...points,...(stars.length?[]:[{x:cx,y:cy,i:-1,radius:sunR,depth:0,kind:'sun'}])].sort((a,b)=>a.depth-b.depth);
  for(const p of objects){
   const {x,y,radius:r,kind}=p;
   if(kind==='sun'){halo(x,y,r*3.6,[[0,'rgba(255,178,90,.67)'],[.25,'rgba(255,166,68,.58)'],[.34,'rgba(255,139,46,.25)'],[.6,'rgba(239,122,42,.08)'],[1,'rgba(255,130,30,0)']]);}
   if(kind==='gas'){ctx.beginPath();ctx.ellipse(x,y,r*1.62,r*.37,-.30,0,TAU);ctx.strokeStyle='rgba(207,177,145,.65)';ctx.lineWidth=r*.15;ctx.stroke();}
   ctx.drawImage(sphere(kind),x-r,y-r,r*2,r*2);
   if(kind==='gas'){ctx.beginPath();ctx.ellipse(x,y,r*1.62,r*.37,-.30,0,Math.PI);ctx.strokeStyle='rgba(193,171,147,.76)';ctx.lineWidth=r*.14;ctx.stroke();}
   if(p.i>=0){const btn=buttons[p.i];btn.style.left=Math.max(52,Math.min(W-52,x))+'px';btn.style.top=(y+r+6)+'px';btn.style.maxWidth=Math.min(155,W*.29)+'px';btn.hidden=items.length>18 && p.i>=18;}
  }
 }
 function requestDraw(){cancelAnimationFrame(raf);raf=requestAnimationFrame(draw);}
 const ro=new ResizeObserver(requestDraw);ro.observe(host);
 if(backdrop){draw();return ()=>{ro.disconnect();cancelAnimationFrame(raf);};}
 const scale=n=>{zoom=Math.max(.65,Math.min(1.8,zoom+n));requestDraw();};
 host.querySelector('[data-map="plus"]').onclick=()=>scale(.12);
 host.querySelector('[data-map="minus"]').onclick=()=>scale(-.12);
 host.querySelector('[data-map="reset"]').onclick=()=>{angle=0;tilt=.34;zoom=1;requestDraw();};
 const expand=host.querySelector('[data-map="expand"]');
 expand.onclick=()=>{expanded=!expanded;host.classList.toggle('expanded',expanded);expand.setAttribute('aria-label',expanded?'Close expanded view':'Expand map');requestDraw();};
 const esc=e=>{if(e.key==='Escape'&&expanded){expanded=false;host.classList.remove('expanded');requestDraw();}};document.addEventListener('keydown',esc);
 canvas.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,initial:angle,tilt};canvas.setPointerCapture(e.pointerId);};
 canvas.onpointermove=e=>{if(!drag)return;angle=drag.initial+(e.clientX-drag.x)*.006;tilt=Math.max(.18,Math.min(.8,drag.tilt+(e.clientY-drag.y)*.002));requestDraw();};
 canvas.onpointerup=e=>{if(drag&&Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<6){const b=canvas.getBoundingClientRect();const p=points.find(p=>Math.hypot(p.x-e.clientX+b.left,p.y-e.clientY+b.top)<p.radius+5);if(p)openMemory(items[p.i].id);}drag=null;};
 canvas.onpointercancel=()=>drag=null;
 draw();return ()=>{ro.disconnect();cancelAnimationFrame(raf);document.removeEventListener('keydown',esc);};
}
