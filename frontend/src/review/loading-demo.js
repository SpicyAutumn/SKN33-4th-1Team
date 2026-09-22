const search=document.querySelector('#search-stage'),loading=document.querySelector('#loading-stage'),answer=document.querySelector('#answer-stage');
let timer;
function finish(){clearTimeout(timer);loading.hidden=true;document.dispatchEvent(new Event("heritage-tour-stop"));answer.hidden=false;answer.focus();}
function start(){clearTimeout(timer);search.hidden=true;answer.hidden=true;loading.hidden=false;document.dispatchEvent(new Event("heritage-tour-start"));document.activeElement?.blur();timer=setTimeout(finish,16000);}
document.querySelector('#demo-search').addEventListener('submit',e=>{e.preventDefault();start();});
document.querySelector('#replay-demo').onclick=start;
document.querySelector('#skip-demo').onclick=finish;
