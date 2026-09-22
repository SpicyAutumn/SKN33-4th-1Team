if(new URLSearchParams(window.location.search).get('embed')==='1')document.documentElement.classList.add('embedded-tour');
import photos from '../data/heritagePhotos.json';
import regions from '../data/heritagePreviewRegions.json';
const $ = selector => document.querySelector(selector);
const shuffle = () => { const items=[...photos]; for(let i=items.length-1;i>0;i--){const j=Math.floor(Math.random()*(i+1));[items[i],items[j]]=[items[j],items[i]];}return items; };
let deck=shuffle(),index=0,paused=false;
const motion=matchMedia('(prefers-reduced-motion: reduce)');
let travelTimers=[],travelVersion=0;
function clearTravel(){travelVersion++;travelTimers.forEach(clearTimeout);travelTimers=[];}
const eastRegions=new Set(['gangwon','chungbuk','gyeongbuk','daegu','ulsan','busan','gyeongnam']);
function placeHeritage(){
 const tour=$('.tour'),card=$('.heritage');
 if(matchMedia('(max-width:700px)').matches){card.style.left='';card.style.top='';return;}
 const host=tour.getBoundingClientRect(),pin=$('#marker').getBoundingClientRect();
 const x=pin.left+pin.width/2-host.left,y=pin.top+pin.height/2-host.top;
 const width=card.offsetWidth,height=card.offsetHeight;
 const preferred=tour.dataset.side==='left'?x-width-32:x+32;
 card.style.left=Math.max(8,Math.min(host.width-width-8,preferred))+'px';
 card.style.top=Math.max(24,Math.min(host.height-height-16,y-height*.45))+'px';
}
new ResizeObserver(placeHeritage).observe($('.tour'));
new ResizeObserver(placeHeritage).observe($('.heritage'));
function moveMap(point,zoom){
 $('#satellite').style.transform='none';
 $('#marker').style.left=(point[0]/550*100)+'%';$('#marker').style.top=(point[1]/500*100)+'%';
 $('.tour').dataset.view='fixed';
 placeHeritage();
}
function render(){
 clearTravel();
 $('#heritage-content').classList.add('is-changing');
 $('#marker').classList.add('is-changing');
 $('#satellite').classList.add('is-changing');
 // Preserve the displayed heritage coordinates throughout fade-out.
 // The pin and card both fade for 800 ms; update only once fully invisible.
 if($('#marker').dataset.region && !motion.matches){
   travelTimers.push(setTimeout(showRegion,850));
 }else showRegion();
}
async function showRegion(){
  const version=travelVersion;
  $('#heritage-content').classList.add('is-changing');
 $('#marker').classList.add('is-changing');
 $('#satellite').classList.add('is-changing');
  const p=deck[index];
  // Decode the next photo before revealing it alongside the map movement.
  const preload=new Image();preload.src=p.image;
  await Promise.race([preload.decode().catch(()=>{}),new Promise(resolve=>setTimeout(resolve,3500))]);
  if(version!==travelVersion)return;
  const region=p.id.replace('-nature',''),location=regions[region],point=location.point,label=location.label;
  $('#marker').dataset.region=region;
  $('.tour').dataset.side=eastRegions.has(region)?'right':'left';
  $('#satellite').querySelectorAll('[data-region]').forEach(path=>path.classList.toggle('selected-region',path.dataset.region===region));
  moveMap(point,false);

  $('#region-label').textContent=label; $('#photo-region').textContent=label; $('#category').textContent=p.category;
  $('#name').textContent=p.name; $('#description').textContent=p.description;
  $('#photo').hidden=false; $('#photo-error').hidden=true; $('#photo').src=p.image; $('#photo').alt=p.title;
  $('#attribution').textContent=p.attribution; $('#copyright').textContent=p.copyright_display || '';
  $('#license').textContent=p.kogl_label; $('#license').href=p.license_url; $('#original').href=p.source_page;
  $('#counter').textContent=`${index+1} / ${deck.length} · 문화·자연유산 순환`;
  document.querySelectorAll('#regions button').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.region===region)));
  $('#marker').classList.remove('region-enter');
  $('#heritage-content').classList.remove('enter');
  const reveal=()=>{if(version!==travelVersion)return;moveMap(point,!motion.matches);$('#heritage-content').classList.remove('is-changing');$('#marker').classList.remove('is-changing');$('#satellite').classList.remove('is-changing');};
  if(motion.matches)reveal();else travelTimers.push(setTimeout(reveal,650));
}
function advance(){if(++index>=deck.length){const last=deck.at(-1).id;deck=shuffle();if(deck[0].id===last)[deck[0],deck[1]]=[deck[1],deck[0]];index=0;}render();}
photos.filter(p=>!p.id.endsWith('-nature')).forEach(p=>{const b=document.createElement('button');b.textContent=p.region;b.dataset.region=p.id;b.onclick=()=>{index=deck.findIndex(item=>item.id===p.id);render();};$('#regions').append(b);});
$('#next').onclick=advance;
$('#pause').onclick=()=>{paused=!paused;$('#pause').setAttribute('aria-pressed',String(paused));$('#pause').textContent=paused?'자동 넘김 재개':'자동 넘김 멈춤';};
document.addEventListener('heritage-tour-start',()=>{clearTravel();$('#marker').dataset.region='';showRegion();});
document.addEventListener('heritage-tour-stop',clearTravel);
motion.addEventListener('change',()=>{clearTravel();showRegion();});
$('#satellite').onerror=()=>{$('#map-error').hidden=false;$('#marker').hidden=true;};
$('#photo').onerror=()=>{$('#photo').hidden=true;$('#photo-error').hidden=false;};
setInterval(()=>{if(paused||motion.matches||document.hidden||$('.tour').getClientRects().length===0||$('.tour').matches(':hover')||$('main').contains(document.activeElement))return;advance();},7000);
render();
