/* Progressive enhancement for bounded LP Crypto data lists.
   Uses only already rendered data. No network, credentials or metrics changes. */
(function(){
 "use strict";
 const SELECTOR=".table-wrap, .v2-table-scroll, .table-scroll, .bar-list, .ratebars, .channel-list";
 const labels={campaignRows:"Histórico de campanhas",volumeBars:"Volume por campanha",
  rateBars:"Qualidade dos disparos",ownerRows:"Carteira dos responsáveis",
  dailyRows:"Movimento por dia",luisaDayRows:"Entradas identificadas por dia",
  luisaOwnerRows:"Leads por responsável",v2DailyTable:"Comparativo diário",
  v2ChannelsTable:"Comparativo por canal",v2ErrorsTable:"Diagnóstico de falhas",
  v2X1Table:"Rastreamento X1",v2X1Days:"Evolução dos cadastros X1",
  v2CopiesTable:"Desempenho por mensagem",v2OriginsTable:"Origens dos disparos"};
 const attached=new WeakSet(),pending=new WeakSet(),formatter=new Intl.NumberFormat("pt-BR");
 const resizeObserver=typeof ResizeObserver==="function"?new ResizeObserver(entries=>{
  entries.forEach(entry=>schedule(entry.target));
 }):null;
 function countRows(el){
  const tbody=el.querySelector("tbody");
  if(tbody)return Array.from(tbody.rows).filter(tr=>!tr.querySelector(".empty, .loading, .v2-empty")).length;
  if(el.classList.contains("bar-list"))return el.querySelectorAll(".bar-row").length;
  if(el.classList.contains("ratebars"))return el.querySelectorAll(".ratebar").length;
  if(el.classList.contains("channel-list"))return el.querySelectorAll(".channel-item").length;
  return null;
 }
 function labelFor(el){
  if(labels[el.id])return labels[el.id];
  const child=el.querySelector("tbody[id]");
  if(child&&labels[child.id])return labels[child.id];
  const host=el.closest(".campaign-columns > div, .panel, .v2-panel, .table-card, .campaign-panel");
  return (host&&host.querySelector("h2,h3")?.textContent?.trim())||"Lista de resultados";
 }
 function schedule(el){
  if(pending.has(el))return;
  pending.add(el);
  requestAnimationFrame(()=>{pending.delete(el);refresh(el);});
 }
 function refresh(el){
  if(!el.isConnected)return;
  const foot=el.nextElementSibling;
  if(!foot||!foot.classList.contains("lp-scroll-foot"))return;
  const count=countRows(el);
  const vertical=el.scrollHeight>el.clientHeight+5;
  const horizontal=el.scrollWidth>el.clientWidth+5;
  const countLabel=foot.querySelector(".lp-scroll-count");
  const tip=foot.querySelector(".lp-scroll-tip");
  foot.hidden=!(count!=null&&count>0)&&!vertical&&!horizontal;
  countLabel.textContent=count==null?"Resultados da seleção":
   formatter.format(count)+(count===1?" registro":" registros")+" na seleção";
  tip.hidden=!(vertical||horizontal);
  tip.classList.toggle("lp-horizontal",!vertical&&horizontal);
  tip.textContent=vertical&&horizontal?"Role para ver mais · deslize para as colunas":
   vertical?"Role para ver todos os registros":"Deslize para ver todas as colunas";
  if(vertical||horizontal){
   el.tabIndex=0;
   el.setAttribute("role","region");
   el.setAttribute("aria-label",labelFor(el)+" — área com rolagem");
  }else{
   el.removeAttribute("tabindex");el.removeAttribute("role");el.removeAttribute("aria-label");
  }
 }
 function attach(el){
  if(attached.has(el))return;
  attached.add(el);el.classList.add("lp-scroll-region");
  const foot=document.createElement("div");foot.className="lp-scroll-foot";foot.hidden=true;
  const count=document.createElement("span");count.className="lp-scroll-count";
  const tip=document.createElement("span");tip.className="lp-scroll-tip";
  foot.append(count,tip);el.after(foot);
  new MutationObserver(()=>schedule(el)).observe(el,{subtree:true,childList:true});
  if(resizeObserver)resizeObserver.observe(el);
  schedule(el);
 }
 function init(){document.querySelectorAll(SELECTOR).forEach(attach);}
 if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",init,{once:true});
 else init();
 window.LPScrollAreas={refreshAll:init};
})();