(function(){
"use strict";
const $=id=>document.getElementById(id),A=window.LPMensageriaModel,B=window.LPCryptoModel;
const state={data:null,error:null,filters:{period:"all",owner:"all",channel:"all",from:"",to:""},search:"",sortKey:"inbound",desc:true};
function el(tag,cls,text){const x=document.createElement(tag);if(cls)x.className=cls;if(text!==undefined)x.textContent=String(text);return x;}
const n=x=>x==null?"Não disponível":Number(x).toLocaleString("pt-BR");
const ready=()=>!!(state.data?.meta?.lastSyncedAt&&state.data?.rollups?.length);
function value(x){return x==null?"Não disponível":(state.data?.meta?.complete?"":"≥ ")+n(x);}
function opts(id,values,defaultText,current){const s=$(id);s.replaceChildren(new Option(defaultText,"all"));values.forEach(v=>s.add(new Option(v.name,v.key||v.id)));s.value=current;}
function syncControls(){for(const k of ["period","owner","channel"])$(k).value=state.filters[k];$("startDate").value=state.filters.from;$("endDate").value=state.filters.to;$("customDates").hidden=state.filters.period!=="custom";}
function roll(filters=state.filters){return ready()?A.resolve(state.data,filters,B.today()):null;}
function dateRows(filters=state.filters){return ready()?A.daily(state.data,filters,B.today()):[];}
function coverage(){
 const m=state.data?.meta||{},total=m.inScopeConversations||0,done=m.scannedConversations||0,pct=total?Math.min(100,done/total*100):0;
 $("coverageTitle").textContent=ready()?(m.complete?"Histórico inspecionado":"Leitura progressiva da caixa de entrada"):"Aguardando primeira coleta real da UmClique";
 $("coverageText").textContent=ready()?(m.complete?"Todos os registros em escopo foram examinados na última sincronização.":"Os indicadores ainda cobrem apenas as conversas processadas; os números são parciais."):"Assim que a primeira sincronização terminar, aparecerão aqui os indicadores reais.";
 $("coverageTag").textContent=ready()?(m.complete?"Completo":"Cobertura parcial"):"Não iniciado";
 $("coverageTag").className="coverage-tag "+(m.complete?"good":"warn");
 $("coverageFill").style.width=pct+"%";
 $("coverageCount").textContent=ready()?n(done)+" de "+n(total)+" conversas ("+pct.toFixed(1).replace(".",",")+"%)":"Conversas ainda não apuradas";
 $("lastUpdated").textContent=m.lastSyncedAt?"Atualizado: "+new Date(m.lastSyncedAt).toLocaleString("pt-BR",{timeZone:"America/Fortaleza",dateStyle:"short",timeStyle:"short"}):"Última sincronização: —";
}
function kpis(){
 const host=$("kpiGrid");host.replaceChildren();
 if(!ready()){host.append(el("p","empty","Nenhuma métrica publicada até agora. Aguardando consulta autenticada."));return;}
 const x=roll();
 const cards=[
  ["MENSAGENS RECEBIDAS",x?.inbound,"Mensagens que chegaram ao WhatsApp"],
  ["MENSAGENS ENVIADAS",x?.outbound,"Mensagens da caixa de entrada, incluindo possíveis templates"],
  ["CONTATOS QUE ESCREVERAM",x?.contactsWithInbound,"Identificados de forma distinta entre conversas"],
  ["CONVERSAS MOVIMENTADAS",x?.conversations,"Conversas com mensagens neste período"],
  ["INICIADAS PELO CONTATO",x?.firstInboundConversations,"Primeira mensagem registrada foi recebida"],
  ["ÚLTIMA MENSAGEM RECEBIDA",x?.lastInboundActiveConversations,"Conversas ativas cujo último evento veio do lead"],
  ["CONTATOS COM MOVIMENTO",x?.contactsInConversations,"Pessoas distintas com mensagens no período"],
  ["NÃO LIDAS (AGORA)",x?.unread,"Disponível somente em todo o histórico"]
 ];
 for(const [label,amount,help] of cards){
  const box=el("article","kpi");box.append(el("small","",label),el("strong",amount==null?"no-data":"",value(amount)),el("p","",help));
  if(!state.data.meta.complete&&amount!=null)box.append(el("span","partial","COBERTURA PARCIAL"));
  host.append(box);
 }
}
function drawTrend(){
 const host=$("trendChart");host.replaceChildren();if(!ready()){host.append(el("p","empty","Aguardando histórico de mensagens."));return;}
 const days=dateRows();if(!days.length){host.append(el("p","empty","Nenhuma mensagem encontrada nesse período."));return;}
 const series=days.slice(-24),max=Math.max(1,...series.flatMap(d=>[d.inbound,d.outbound]))*1.15;
 const w=660,h=240,L=43,R=15,T=18,B=34,wi=w-L-R,hi=h-T-B;
 const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox","0 0 "+w+" "+h);svg.setAttribute("role","img");
 function child(tag,attrs={},text){const p=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))p.setAttribute(k,String(v));if(text!==undefined)p.textContent=String(text);svg.append(p);return p;}
 const X=i=>L+wi*(series.length===1?.5:i/(series.length-1)),Y=v=>T+hi*(1-v/max);
 for(let i=0;i<5;i++){const y=T+hi*i/4;child("line",{class:"grid",x1:L,y1:y,x2:w-R,y2:y});child("text",{class:"axis-label",x:L-7,y:y+3,"text-anchor":"end"},Math.round(max*(1-i/4)));}
 const step=Math.max(1,Math.ceil(series.length/9));series.forEach((d,i)=>{if(i%step===0||i===series.length-1)child("text",{class:"axis-label",x:X(i),y:h-10,"text-anchor":"middle"},d.day.slice(8)+"/"+d.day.slice(5,7));});
 for(const [key,color,label] of [["inbound","#9475eb","Recebidas"],["outbound","#26aa98","Enviadas"]]){
  if(series.length>1)child("polyline",{class:"line",stroke:color,points:series.map((d,i)=>X(i)+","+Y(d[key])).join(" ")});
  series.forEach((d,i)=>{
   const dot=child("circle",{class:"point",cx:X(i),cy:Y(d[key]),r:4.5,fill:color,tabindex:0,role:"button"});
   const tt=document.createElementNS(ns,"title");tt.textContent=d.day+" · "+label+": "+n(d[key])+" · clique para filtrar";dot.append(tt);
   function select(){state.filters.period="custom";state.filters.from=d.day;state.filters.to=d.day;syncControls();render();}
   dot.addEventListener("click",select);dot.addEventListener("keydown",e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();select();}});
  });
 }
 host.append(svg);
}
function channels(){
 const host=$("channelList");host.replaceChildren();if(!ready()){host.append(el("p","empty","Aguardando canais."));return;}
 const rows=A.channelRows(state.data,state.filters,B.today());
 if(!rows.length){host.append(el("p","empty","Nenhum canal para os filtros."));return;}
 for(const row of rows){
  const box=el("article","channel-item"),left=el("div"),right=el("div","channel-numbers");
  left.append(el("strong","channel-name",row.name),el("span","channel-meta","Recebidas: "+value(row.inbound)+" · Enviadas: "+value(row.outbound)));
  right.append(el("strong","",value(row.contactsWithInbound)),el("small","","contatos que escreveram"));
  box.append(left,right);host.append(box);
 }
}
function owners(){
 const host=$("ownerRows");host.replaceChildren();if(!ready()){const tr=el("tr"),td=el("td","empty","Aguardando dados.");td.colSpan=7;tr.append(td);host.append(tr);return;}
 const owners=A.ownerRows(state.data,state.filters,B.today()).filter(x=>x.name.toLocaleLowerCase("pt-BR").includes(state.search));
 if(!owners.length){const tr=el("tr"),td=el("td","empty","Nenhum responsável nesse filtro.");td.colSpan=7;tr.append(td);host.append(tr);return;}
 for(const r of A.sorted(owners,state.sortKey,state.desc)){
  const tr=el("tr"),name=el("td");
  name.append(el("span","",r.name));
  if(r.key==="unassigned")name.append(el("span","status muted"," Sem atribuição"));
  else if(r.active===false)name.append(el("span","status muted"," Inativo"));
  tr.append(name);
  for(const key of ["inbound","outbound","contactsWithInbound","conversations","firstInboundConversations","lastInboundActiveConversations"])
    tr.append(el("td","",value(r[key])));
  host.append(tr);
 }
 $("ownerTableNote").textContent=owners.length+" responsáveis exibidos · "+(state.data.meta.complete?"cobertura integral":"cobertura parcial");
}
function byDay(){
 const body=$("dailyRows");body.replaceChildren();
 if(!ready()||!dateRows().length){const tr=el("tr"),td=el("td","empty","Nenhum registro diário.");td.colSpan=5;tr.append(td);body.append(tr);return;}
 for(const day of dateRows().slice().reverse().slice(0,120)){
  const tr=el("tr");
  for(const k of ["day","inbound","outbound","inboundContacts","conversations"]){
   tr.append(el("td","",k==="day"?day.day.split("-").reverse().join("/"):value(day[k])));
  }
  body.append(tr);
 }
}
function render(){coverage();kpis();drawTrend();channels();owners();byDay();
 const u=$("caveats");u.replaceChildren();
 for(const note of state.data?.meta?.caveats||["Dados parciais; aguarde a primeira coleta."])u.append(el("li","",note));
}
function exportRows(kind){
 if(!ready())return null;
 const x=roll(),t=B.today(),completeness=state.data.meta.complete?"Completo":"Parcial";
 if(kind==="geral")return[["Indicador","Valor","Observação"],
  ["Mensagens recebidas",x?.inbound??"Não disponível","is_from_me=false"],
  ["Mensagens enviadas",x?.outbound??"Não disponível","is_from_me=true"],
  ["Contatos distintos que escreveram",x?.contactsWithInbound??"Não disponível","Deduplicados entre conversas analisadas"],
  ["Conversas movimentadas",x?.conversations??"Não disponível","Conversas com mensagens no período"],
  ["Conversas iniciadas pelo contato",x?.firstInboundConversations??"Não disponível","Primeira mensagem da conversa recebida"],
  ["Última mensagem recebida",x?.lastInboundActiveConversations??"Não disponível","Conversa ativa; não é um SLA"],
  ["Cobertura",completeness,"Não inferir total quando parcial"]];
 if(kind==="responsaveis")return[["Responsável atual","Recebidas","Enviadas","Contatos distintos que escreveram","Conversas","Iniciadas pelo contato","Última mensagem recebida","Cobertura"],
  ...A.ownerRows(state.data,state.filters,t).map(x=>[x.name,x.inbound??"Não disponível",x.outbound??"Não disponível",x.contactsWithInbound??"Não disponível",x.conversations??"Não disponível",x.firstInboundConversations??"Não disponível",x.lastInboundActiveConversations??"Não disponível",completeness])];
 if(kind==="canais")return[["Canal","Recebidas","Enviadas","Contatos distintos que escreveram","Conversas","Cobertura"],
  ...A.channelRows(state.data,state.filters,t).map(x=>[x.name,x.inbound??"Não disponível",x.outbound??"Não disponível",x.contactsWithInbound??"Não disponível",x.conversations??"Não disponível",completeness])];
 if(kind==="diario")return[["Dia","Recebidas","Enviadas","Contatos-dia","Conversas-dia","Cobertura"],
  ...dateRows().map(x=>[x.day,x.inbound,x.outbound,x.inboundContacts,x.conversations,completeness])];
 return null;
}
function exportCsv(kind){
 const data=exportRows(kind);if(!data)return;
 const blob=new Blob([B.csv(data)],{type:"text/csv;charset=utf-8"}),href=URL.createObjectURL(blob),a=el("a");
 a.href=href;a.download="LP_Crypto_Mensageria_"+kind+"_"+B.today()+".csv";document.body.append(a);a.click();a.remove();
 setTimeout(()=>URL.revokeObjectURL(href),5000);
}
function hook(){
 $("period").addEventListener("change",e=>{state.filters.period=e.target.value;syncControls();render();});
 for(const[id,key]of[["owner","owner"],["channel","channel"],["startDate","from"],["endDate","to"]])
  $(id).addEventListener("change",e=>{state.filters[key]=e.target.value;render();});
 $("ownerSearch").addEventListener("input",e=>{state.search=e.target.value.toLocaleLowerCase("pt-BR");owners();});
 $("resetFilters").addEventListener("click",()=>{state.filters={period:"all",owner:"all",channel:"all",from:"",to:""};state.search="";$("ownerSearch").value="";syncControls();render();});
 document.querySelectorAll("th button[data-sort]").forEach(x=>x.addEventListener("click",()=>{
  const key=x.dataset.sort;state.desc=state.sortKey===key?!state.desc:key!=="name";state.sortKey=key;owners();
 }));
 for(const[id,type]of[["generalCsv","geral"],["ownerCsv","responsaveis"],["ownerCsvSecond","responsaveis"],["channelCsv","canais"],["dailyCsv","diario"],["dailyCsvSecond","diario"]])
  $(id).addEventListener("click",()=>exportCsv(type));
}
async function load(){
 try{
  const response=await fetch("./data/mensageria.json",{cache:"no-store"});
  if(!response.ok)throw Error("HTTP "+response.status);
  const data=await response.json();
  if(!data?.meta||!Array.isArray(data.owners)||!Array.isArray(data.rollups))throw Error("Dados de mensageria inválidos");
  state.data=data;state.error=null;
  opts("owner",data.owners,"Todos os responsáveis",state.filters.owner);
  opts("channel",data.channels,"Todos os canais",state.filters.channel);
  syncControls();render();
 }catch(e){
  state.error=String(e?.message||e);$("coverageTitle").textContent="Erro ao carregar a mensageria";
  $("coverageText").textContent="Confira a sincronização autenticada no GitHub.";
  $("kpiGrid").replaceChildren(el("div","error","Dados indisponíveis: "+state.error));
 }
}
hook();load();
window.setInterval(()=>{if(document.visibilityState!=="hidden")load();},120000);
window.LPMensageria={getState:()=>({filters:{...state.filters},ready:ready(),error:state.error})};
})();