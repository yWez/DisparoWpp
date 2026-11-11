
(function(){
"use strict";
const M=window.LPCryptoModel,$=id=>document.getElementById(id),fmt=new Intl.NumberFormat("pt-BR");
const state={rows:[],channels:[],meta:{},funnel:{},ready:false,filters:{period:"all",campaign:"all",channel:"all",status:"all",origin:"all",from:"",to:""},search:"",rankSort:"day",rankDir:-1,minSent:30,maxFail:15,minDelivery:80,sortDaily:"day",sortChannel:"sent"};
const E=(tag,cls="",value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=String(value);return n};
const N=x=>M.number(x),P=x=>M.pct(x),kpi=(label,value,hint,tone)=>{let a=E("article","v2-kpi "+(tone||"")),v=E("strong","metric"+(value==="Não disponível"?" na":""),value);a.append(E("span","label",label),v,E("small","",hint));return a};
const all=()=>M.filter(state.rows,state.filters);
function segment(id,title,desc){
 const box=E("section","v2-section");box.id=id;
 const heading=E("div","v2-section-head"),group=E("div","");group.append(E("h2","",title),E("p","",desc));heading.append(group);box.append(heading);return box;
}
function init(){
 document.body.classList.add("v2-active");
 const main=document.querySelector("main.container"),filters=E("section","v2-filter");filters.id="globalFilters";
 filters.innerHTML=`
 <div class="v2-filterbar"><div><h2>Inteligência de campanhas</h2><p>Indicadores, comparativos e causas de falhas com uma única seleção</p></div><button type="button" class="v2-reset" id="v2Reset">Limpar filtros</button></div>
 <div class="v2-filters">
 <div class="v2-field"><label for="v2Period">Período de disparo</label><select id="v2Period"><option value="all">Todo o histórico</option><option value="today">Hoje</option><option value="yesterday">Ontem</option><option value="7d">Últimos 7 dias</option><option value="30d">Últimos 30 dias</option><option value="custom">Intervalo personalizado</option></select></div>
 <div class="v2-field"><label for="v2Campaign">Campanha</label><select id="v2Campaign"><option value="all">Todas as campanhas</option></select></div>
 <div class="v2-field"><label for="v2Channel">Número / canal API</label><select id="v2Channel"><option value="all">Todos os canais</option></select></div>
 <div class="v2-field"><label for="v2Status">Status</label><select id="v2Status"><option value="all">Todos os status</option><option value="sent">Com mensagens enviadas</option><option value="delivered">Com entregas</option><option value="read">Com leituras</option><option value="replied">Com respostas</option><option value="failed">Com falhas</option></select></div></div>
 <div class="v2-dates" id="v2Dates" hidden><div class="v2-field"><label for="v2From">De</label><input type="date" id="v2From"></div><div class="v2-field"><label for="v2To">Até</label><input type="date" id="v2To"></div></div>
 <div class="v2-field" style="margin-top:14px;max-width:360px"><label for="v2Origin">Origem da campanha</label><select id="v2Origin"><option value="all">Todas as origens</option></select></div>
 <p class="v2-status-note">O filtro de status seleciona <strong>campanhas com ao menos um evento</strong> nesse estado, não cada destinatário individualmente. Todos os números exibidos são agregados dos disparos selecionados.</p>`;
 const deck=E("section","v2-kpis");deck.id="v2Kpis";
 const alert=E("div","v2-alert");alert.id="v2Alert";alert.setAttribute("role","status");
 const loading=E("div","v2-status");loading.id="v2LoadStatus";
 main.insertBefore(filters,main.firstElementChild);main.insertBefore(deck,main.children[1]);main.insertBefore(alert,main.children[2]);main.insertBefore(loading,main.children[3]);
 const daily=segment("diario","Evolução por dia","O dia é o início local da campanha (America/Fortaleza), não o momento individual de abertura ou resposta.");
 daily.insertAdjacentHTML("beforeend",`<div class="v2-grid-2"><div class="v2-panel"><h3>Volumes diários</h3><p>Envios, entregas, leituras, respostas e falhas</p><div id="v2DailyChart"></div></div><div class="v2-panel"><h3>Taxas por dia</h3><p>Entrega, leitura e falha</p><div id="v2RatesChart"></div></div></div><div class="v2-panel" style="margin-top:15px"><div class="v2-flex"><h3>Comparativo diário</h3><button class="v2-action" id="v2DailyCsv">Exportar CSV</button></div><div id="v2DailyTable" class="v2-table-scroll"></div></div>`);
 const channels=segment("canais","Desempenho por canal/API","A API fornece IDs de canais; a identificação é um nome de canal quando disponível, não necessariamente o telefone completo.");
 channels.insertAdjacentHTML("beforeend",`<div class="v2-panel"><div id="v2ChannelsTable" class="v2-table-scroll"></div><p class="v2-muted">Limites de envio não foram confirmados neste endpoint. Status de conexão só aparece se a API o fornecer.</p></div>`);
 $("campanhas").before(daily,channels);
 const errors=segment("falhas","Diagnóstico de falhas","Códigos e explicações reais da UmClique, nunca suposições de que todos os telefones são inválidos.");
 errors.insertAdjacentHTML("beforeend",`<div class="v2-panel"><div class="v2-flex"><h3>Grupos de erros por disparo</h3><button class="v2-action" id="v2ErrorCsv">Exportar causas</button></div><div id="v2ErrorsTable" class="v2-table-scroll"></div><div class="v2-blocked" style="margin-top:13px"><strong>Dados pessoais não são públicos.</strong> Os códigos são agregados; contato, telefone e recuperação individual requerem uma área autenticada e permissão específica. Não enviamos reprocessamentos automáticos.</div></div>`);
 const origins=segment("origens","Origem e atribuição","Origem por campanha cadastrada, sem sobrescrever a primeira origem de contatos.");
 origins.insertAdjacentHTML("beforeend",`<div class="v2-panel"><div id="v2OriginsTable" class="v2-table-scroll"></div><div class="v2-blocked" style="margin-top:12px">Origens são associadas por ID no arquivo data/origins.json. Atribuição por pessoa e multitoques dependerá da integração com CRM/captação.</div></div>`);
 const funnel=segment("funil","Funil comercial","Etapas independentes: somente mensurar conversão de indivíduos vinculados por IDs.");
 funnel.insertAdjacentHTML("beforeend",`<div class="v2-panel"><div id="v2FunnelBars"></div><div class="v2-blocked">As quatro primeiras contagens são de campanhas, com possíveis pessoas repetidas. Inscrição, grupo, live e compras permanecem indisponíveis até conciliar suas fontes. Taxas entre etapas não são apresentadas sem populações relacionadas.</div></div>`);
 const exports=segment("exportacoes","Exportações","CSVs em UTF-8 com BOM e delimitador compatível com Excel, sempre com os filtros ativos.");
 exports.insertAdjacentHTML("beforeend",`<div class="v2-panel"><div id="v2Exports" class="v2-exports"></div><p class="v2-muted">Contatos com falhas e respondentes individuais são exportações privadas: não ficam disponíveis no site público.</p></div>`);
 document.querySelector("aside.note-box").before(errors,origins,funnel,exports);
 $("campanhas").querySelector("h2").textContent="Ranking de campanhas";
 $("campanhas").querySelector("p").textContent="Todos os indicadores ordenáveis; critérios de desempenho ajustáveis.";
 $("search").placeholder="Buscar na tabela...";
 $("v2Reset").addEventListener("click",()=>{state.filters={period:"all",campaign:"all",channel:"all",status:"all",origin:"all",from:"",to:""};reset();render();});
 for(const name of ["Period","Campaign","Channel","Status","Origin"]){
  $("v2"+name).addEventListener("change",e=>{state.filters[name.toLowerCase()]=e.target.value;$("v2Dates").hidden=state.filters.period!=="custom";render()});
 }
 for(const name of ["From","To"])$("v2"+name).addEventListener("change",e=>{state.filters[name.toLowerCase()]=e.target.value;render()});
 $("search").addEventListener("input",e=>{state.search=e.target.value.toLocaleLowerCase("pt-BR");rank()});
 $("exportCsv").addEventListener("click",()=>download("campanhas"));
 $("v2DailyCsv").addEventListener("click",()=>download("diario"));
 $("v2ErrorCsv").addEventListener("click",()=>download("erros"));
 $("copyButton").addEventListener("click",copy);
 createExports();
}
function reset(){for(let [name,key] of [["Period","period"],["Campaign","campaign"],["Channel","channel"],["Status","status"],["Origin","origin"],["From","from"],["To","to"]])$("v2"+name).value=state.filters[key];$("v2Dates").hidden=state.filters.period!=="custom";}
function options(sel,rows,defaultLabel,current){sel.replaceChildren(new Option(defaultLabel,"all"));rows.forEach(r=>sel.add(new Option(r.label,r.id)));sel.value=Array.from(sel.options).some(o=>o.value===current)?current:"all";}
function fillOptions(){
 options($("v2Campaign"),state.rows.map(x=>({id:x.campaignId,label:x.name})).sort((a,b)=>a.label.localeCompare(b.label)),"Todas as campanhas",state.filters.campaign);
 const map=new Map();state.rows.forEach(c=>{let ids=c.channelIds?.length?c.channelIds:[c.channelId];ids.filter(Boolean).forEach(id=>{let info=state.channels.find(x=>x.id===id);map.set(id,(info?.name||c.channelName||"Canal "+id.slice(0,8))+" · "+id.slice(0,8));});});
 options($("v2Channel"),Array.from(map,([id,label])=>({id,label})),"Todos os canais",state.filters.channel);
 options($("v2Origin"),Array.from(new Set(state.rows.map(x=>x.campaignOrigin||"Não atribuída"))).map(id=>({id,label:id})),"Todas as origens",state.filters.origin);
}
function render(){
 if(!state.ready)return;
 const rows=all(),s=M.summary(rows),t=k=>M.number(s.metrics[k].value);
 $("v2Kpis").replaceChildren(...[
 ["Enviadas",t("sent"),"Mensagens por campanha",""],
 ["Entregues",t("delivered"),"Entregas confirmadas pela API","positive"],
 ["Lidas",t("read"),"Leituras por campanha",""],
 ["Respondidas",t("replied"),"Podem repetir contatos entre campanhas",""],
 ["Falhas",t("failures"),"Falhas registradas pela API","negative"],
 ["Taxa de entrega",M.pct(s.deliveryRate),"Entregues ÷ enviadas","positive"],
 ["Taxa de leitura",M.pct(s.readRate),"Lidas ÷ entregues",""],
 ["Taxa de resposta","Não disponível","Exige contatos únicos respondentes ÷ contatos únicos entregues","unknown"],
 ["Taxa de falha",M.pct(s.failureRate),"Falhas ÷ enviadas","negative"],
 ["Leads únicos","Não disponível","Deduplicação entre campanhas não fornecida","unknown"]
 ].map(x=>kpi(...x)));
 $("v2Alert").textContent=rows.length+" campanha(s) selecionada(s). Contatos e respondentes podem aparecer em mais de uma campanha. A taxa de resposta por mensagens (proxy) é "+M.pct(s.proxyResponseRate)+"; não equivale à taxa de pessoas únicas.";
 const sync=state.meta.lastSyncedAt?new Date(state.meta.lastSyncedAt):null;
 $("updateLabel").textContent=sync&&!isNaN(sync)?("Dados atualizados em "+sync.toLocaleString("pt-BR",{timeZone:"America/Fortaleza",dateStyle:"short",timeStyle:"short"})):"Sincronização não disponível";
 $("footerSource").textContent="UmClique API • agregados por campanha • horário America/Fortaleza";
 $("periodBadge").textContent=rows.length+" campanhas";
 $("v2LoadStatus").textContent="Fonte: UmClique API • data inicial de cada campanha • dados filtrados";
 $("caveats").replaceChildren(...(state.meta.caveats||[]).map(x=>E("li","",x)));
 if(state.meta.spreadsheetUrl)$("sheetLink").href=state.meta.spreadsheetUrl;
 oldCharts(rows,s);daily(rows);channels(rows);rank();errors(rows);origins(rows);funnel(s);
}
function oldCharts(rows,s){
 const bars=$("volumeBars");bars.replaceChildren();const mx=Math.max(1,...rows.map(x=>x.sent||0));
 rows.forEach(c=>{const r=E("div","bar-row"),track=E("div","bar-track"),good=E("div","bar-good"),bad=E("div","bar-bad");good.style.width=(100*Math.max(0,(c.sent||0)-(c.failures||0))/mx)+"%";bad.style.width=(100*(c.failures||0)/mx)+"%";track.append(good,bad);r.append(E("span","bar-name",c.name),track,E("span","bar-value",M.number(c.sent)));bars.append(r);});
 if(!rows.length)bars.append(E("p","v2-empty","Sem campanhas."));
 const rates=$("rateBars");rates.replaceChildren();rows.slice().sort((a,b)=>(b.failures/b.sent)-(a.failures/a.sent)).forEach(c=>{const r=E("div","ratebar"),track=E("div","mini"),v=E("div");v.style.width=Math.min(100,100*(c.sent?c.failures/c.sent:0)/.2)+"%";track.append(v);r.append(E("span","",c.name),track,E("strong","",M.pct(M.rate(c.failures,c.sent))));rates.append(r);});
 $("rateNumber").textContent=M.pct(s.failureRate);$("ringPercent").textContent=M.pct(s.failureRate);
 const pct=Math.max(0,Math.min(100,100*(s.failureRate||0)));
 $("ring").style.background="conic-gradient(#ed7282 0% "+pct+"%,#8d74e6 "+pct+"% 100%)";
 const worst=rows.filter(x=>x.sent>0).sort((a,b)=>b.failures/b.sent-a.failures/a.sent)[0];
 $("insightTitle").textContent=worst?"Maior taxa de falhas: "+worst.name:"Sem campanhas";
 $("insightText").textContent=worst?M.pct(M.rate(worst.failures,worst.sent))+" das mensagens com falha. Abra o diagnóstico para ver códigos, sem presumir causa.":"Altere o período ou o canal.";
}
function drawChart(target,days,series,isRate=false){
 const host=$(target);host.replaceChildren();
 if(!days.length){host.append(E("div","v2-empty","Sem dados neste período."));return;}
 const palette=["#8365dd","#42a48d","#ec7a86","#d29d42","#517ab6"],w=620,h=230,L=43,T=13,B=40,R=12,IW=w-L-R,IH=h-T-B;
 const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox","0 0 "+w+" "+h);svg.setAttribute("class","v2-chart");svg.setAttribute("role","img");
 function node(tag,props,txt){const x=document.createElementNS(ns,tag);Object.entries(props||{}).forEach(([k,v])=>x.setAttribute(k,v));if(txt!==undefined)x.textContent=String(txt);svg.append(x);return x;}
 const nums=days.flatMap(d=>series.map(s=>d[s.key]).filter(x=>x!=null));
 if(!nums.length){host.append(E("p","v2-empty","Indicadores não disponíveis."));return;}
 const max=isRate?Math.max(.05,Math.min(1,Math.max(...nums)*1.15)):Math.max(1,Math.max(...nums)*1.15);
 const X=i=>L+(days.length===1?IW/2:IW*i/(days.length-1)),Y=x=>T+IH*(1-x/max);
 for(let j=0;j<5;j++){const y=T+IH*j/4;node("line",{x1:L,y1:y,x2:w-R,y2:y,class:"gridline"});node("text",{x:L-6,y:y+3,"text-anchor":"end"},isRate?Math.round(max*100*(1-j/4))+"%":Math.round(max*(1-j/4)));}
 days.forEach((d,i)=>node("text",{x:X(i),y:h-13,"text-anchor":"middle"},d.day.slice(8)+"/"+d.day.slice(5,7)));
 series.forEach((s,k)=>{
  let points=[];const color=palette[k%palette.length];
  function flush(){if(points.length>1)node("polyline",{points:points.map(p=>p.x+","+p.y).join(" "),class:"series",stroke:color});points=[];}
  days.forEach((d,i)=>{let v=d[s.key];if(v==null){flush();return;}points.push({x:X(i),y:Y(v)});
   const c=node("circle",{cx:X(i),cy:Y(v),r:5,fill:color,class:"point",tabindex:0,role:"button","aria-label":s.name+" "+d.day});
   const t=document.createElementNS(ns,"title");t.textContent=d.day+" · "+s.name+": "+(isRate?M.pct(v):M.number(v))+" · clique para filtrar";c.append(t);
   const go=()=>{state.filters.period="custom";state.filters.from=d.day;state.filters.to=d.day;reset();render();};
   c.addEventListener("click",go);c.addEventListener("keydown",ev=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();go();}});
  });flush();
 });
 host.append(svg);const leg=E("div","v2-legend");series.forEach((s,i)=>{const v=E("span","v2-legend-item"),dot=E("i","v2-legend-dot");dot.style.background=palette[i%palette.length];v.append(dot,E("span","",s.name));leg.append(v);});host.append(leg);
}
function drawTable(host,columns,rows,formatter,sortBy="sent",dir=-1,onSort=null){
 host.replaceChildren();
 if(!rows.length){host.append(E("p","v2-empty","Nenhum registro corresponde aos filtros."));return;}
 const table=E("table"),thead=E("thead"),head=E("tr"),tbody=E("tbody");
 columns.forEach(([key,label])=>{const th=E("th"),b=E("button","sort",label+(sortBy===key?" ⇅":""));b.type="button";b.addEventListener("click",()=>onSort&&onSort(key));th.append(b);head.append(th);});thead.append(head);
 rows.slice().sort((a,b)=>{let x=a[sortBy],y=b[sortBy];if(x==null&&y!=null)return 1;if(y==null&&x!=null)return -1;if(x==null&&y==null)return 0;return (typeof x==="number"&&typeof y==="number"?(x-y):String(x).localeCompare(String(y),"pt-BR",{numeric:true}))*dir;}).forEach(c=>{const tr=E("tr");columns.forEach(([key])=>{const td=E("td"),v=c[key];if(key==="quality"){td.append(E("span","v2-pill "+(v.startsWith("Atenção")?"warn":v==="Dentro do critério"?"":"neutral"),v));}else td.textContent=formatter(key,v,c);tr.append(td);});tbody.append(tr);});
 table.append(thead,tbody);host.append(table);
}
function daily(rows){
 const series=M.daily(rows);
 drawChart("v2DailyChart",series,[["sent","Enviadas"],["delivered","Entregues"],["read","Lidas"],["replied","Respostas"],["failures","Falhas"]].map(([key,name])=>({key,name})));
 drawChart("v2RatesChart",series,[["deliveryRate","Entrega"],["readRate","Leitura"],["failureRate","Falha"]].map(([key,name])=>({key,name})),true);
 drawTable($("v2DailyTable"),[["day","Data"],["campaigns","Disparos"],["sent","Enviadas"],["delivered","Entregues"],["read","Lidas"],["replied","Respostas"],["failures","Falhas"],["deliveryRate","Tx. entrega"],["readRate","Tx. leitura"],["failureRate","Tx. falha"]],series,
 (key,v)=>key.endsWith("Rate")?M.pct(v):M.number(v),state.sortDaily,-1,key=>{state.sortDaily=key;daily(all())});
}
function channels(rows){
 const series=M.channels(rows,state.channels).map(c=>{const s=c.summary;return {id:c.id,name:c.name+" · "+c.id.slice(0,8),connection:c.connection||"Não disponível",campaigns:s.campaigns,sent:s.metrics.sent.value,delivered:s.metrics.delivered.value,read:s.metrics.read.value,replied:s.metrics.replied.value,failures:s.metrics.failures.value,deliveryRate:s.deliveryRate,readRate:s.readRate,responseRate:s.responseRate,failureRate:s.failureRate,
 quality:M.thresholds({sent:s.metrics.sent.value,delivered:s.metrics.delivered.value,failures:s.metrics.failures.value},{minSent:state.minSent,maxFailureRate:state.maxFail/100,minDeliveryRate:state.minDelivery/100})};});
 drawTable($("v2ChannelsTable"),[["name","Número/API"],["connection","Conexão"],["campaigns","Disparos"],["sent","Enviadas"],["delivered","Entregues"],["read","Lidas"],["replied","Respostas"],["failures","Falhas"],["deliveryRate","Tx. entrega"],["readRate","Tx. leitura"],["responseRate","Tx. resposta"],["failureRate","Tx. falha"],["quality","Diagnóstico"]],series,
 (key,v)=>key.endsWith("Rate")?M.pct(v):typeof v==="number"?M.number(v):v??"Não disponível",state.sortChannel,-1,key=>{state.sortChannel=key;channels(all())});
}
function rank(){
 const rows=all().filter(c=>!state.search||(c.name+" "+(c.campaignOrigin||"")).toLocaleLowerCase("pt-BR").includes(state.search));
 const data=rows.map(c=>{const s=M.summary([c]);return {id:c.campaignId,name:c.name,day:M.campaignDay(c)||"Não disponível",channel:(state.channels.find(x=>x.id===c.channelId)?.name||c.channelName||"Canal")+" · "+(c.channelId||"").slice(0,8),
 sent:c.sent,delivered:c.delivered,read:c.read,replied:c.replied,failures:c.failures,deliveryRate:s.deliveryRate,readRate:s.readRate,responseRate:s.responseRate,failureRate:s.failureRate,
 quality:M.thresholds(c,{minSent:state.minSent,maxFailureRate:state.maxFail/100,minDeliveryRate:state.minDelivery/100})};});
 const cols=[["name","Campanha"],["day","Data"],["channel","Número/API"],["sent","Enviadas"],["delivered","Entregues"],["read","Lidas"],["replied","Respostas"],["failures","Falhas"],["deliveryRate","Tx. entrega"],["readRate","Tx. leitura"],["responseRate","Tx. resposta"],["failureRate","Tx. falha"],["quality","Classificação"]];
 const wrap=document.querySelector(".table-card .table-wrap");wrap.replaceChildren();drawTable(wrap,cols,data,(k,v)=>k.endsWith("Rate")?M.pct(v):typeof v==="number"?M.number(v):v??"Não disponível",state.rankSort,state.rankDir,key=>{state.rankDir=state.rankSort===key?-state.rankDir:-1;state.rankSort=key;rank()});
 if(!$("v2Thresholds")){const box=E("div","v2-thresholds");box.id="v2Thresholds";
 [["minSent","Volume mín.",0,100000],["maxFail","Falha alerta ≥ %",0,100],["minDelivery","Meta entrega ≥ %",0,100]].forEach(([key,label,min,max])=>{const w=E("label","",label),input=E("input");input.type="number";input.value=state[key];input.min=min;input.max=max;input.addEventListener("change",()=>{let n=Number(input.value);if(Number.isFinite(n)&&n>=min&&n<=max){state[key]=n;rank();}else input.value=state[key];});w.append(input);box.append(w);});
 $("campanhas").append(box);}
}
function errors(rows){
 const groups=M.errorRows(rows),host=$("v2ErrorsTable");
 if(!rows.some(c=>c.errorDiagnostics&&Array.isArray(c.errorDiagnostics.groups))){host.replaceChildren(E("p","v2-empty","Aguardando a primeira consulta /errors. A quantidade de falhas não permite inferir a causa."));return;}
 drawTable(host,[["name","Campanha"],["day","Data"],["code","Código API"],["type","Tipo"],["title","Motivo"],["description","Descrição técnica"],["count","Casos"],["reconciliation","Conciliação"],["recoverability","Recuperação"],["suggestion","Ação sugerida"]],groups,
 (k,v)=>typeof v==="number"?M.number(v):v??"Não disponível","count",-1,null);
 const mismatch=rows.filter(c=>c.errorDiagnostics?.summary?.failedTotal!=null&&c.failures!=null&&c.errorDiagnostics.summary.failedTotal!==c.failures);
 if(mismatch.length)host.append(E("div","v2-error","Atenção: relatório de causas diverge do total de mensagens com falha em "+mismatch.length+" campanha(s). Grupos podem incluir tentativas ou contagens distintas; não somar como contatos únicos."));
 host.append(E("p","v2-muted","Os grupos podem não explicar todas as falhas. Telefones e nomes ficam em ambiente restrito."));
}
function origins(rows){
 const groups=M.originGroups(rows).map(x=>({name:x.origin,campaigns:x.summary.campaigns,sent:x.summary.metrics.sent.value,delivered:x.summary.metrics.delivered.value,replied:x.summary.metrics.replied.value,failures:x.summary.metrics.failures.value}));
 drawTable($("v2OriginsTable"),[["name","Origem"],["campaigns","Campanhas"],["sent","Enviadas"],["delivered","Entregues"],["replied","Respostas"],["failures","Falhas"]],groups,
 (k,v)=>typeof v==="number"?M.number(v):v??"Não disponível","sent",-1,null);
}
function funnelRows(s){
 const external=state.funnel?.stages||{},safe=k=>(external[k]?.verified===true&&typeof external[k]?.count==="number"?external[k].count:null);
 return [["Enviadas",s.metrics.sent.value],["Entregues",s.metrics.delivered.value],["Lidas",s.metrics.read.value],["Responderam (por campanha)",s.metrics.replied.value],["Inscrições",safe("registrations")],["Entradas no grupo",safe("groupJoins")],["Participantes da live",safe("liveAttendees")],["Compras",safe("purchases")]];
}
function funnel(s){
 const host=$("v2FunnelBars");host.replaceChildren();const data=funnelRows(s),max=Math.max(1,...data.map(x=>x[1]||0));
 data.forEach(([name,v])=>{const row=E("div","v2-stage"),track=E("div","track"),bar=E("div","fill");bar.style.width=(100*(v||0)/max)+"%";track.append(bar);row.append(E("span","",name),track,E("span","value",M.number(v)));host.append(row);});
 host.append(E("p","v2-muted","Conversões entre etapas: Não disponível. São populações diferentes até reconciliação de IDs."));
}
const TYPES=[["geral","Relatório geral"],["campanhas","Por campanha"],["diario","Por dia"],["canais","Por número/API"],["erros","Causas das falhas"],["respostas","Respostas agregadas"],["funil","Funil"],["contatos","Contatos com falha · privado",true],["respondentes","Respondentes · privado",true]];
function createExports(){TYPES.forEach(([type,label,blocked])=>{const b=E("button","v2-action",(blocked?"🔒 ":"↓ ")+label);b.type="button";b.disabled=!!blocked;if(blocked)b.title="Exige exportação autenticada em ambiente restrito";else b.addEventListener("click",()=>download(type));$("v2Exports").append(b);});}
function download(type){
 const rows=all(),s=M.summary(rows),rate=x=>x==null?"Não disponível":(x*100).toFixed(2)+"%",count=x=>x==null?"Não disponível":x;
 const pack=(head,items)=>[head,...items];let out=[];
 if(type==="geral")out=pack(["Indicador","Total","Denominador"],[
 ["Campanhas",s.campaigns,"IDs oficiais"],...["sent","delivered","read","replied","failures"].map(k=>[k,count(s.metrics[k].value),"Por campanha"]),
 ["Taxa entrega",rate(s.deliveryRate),"Entregues / enviadas"],["Taxa leitura",rate(s.readRate),"Lidas / entregues"],["Taxa resposta","Não disponível","Contatos únicos de respostas / contatos únicos entregues"],["Taxa falha",rate(s.failureRate),"Falhas / enviadas"],["Leads únicos","Não disponível","Deduplicação entre campanhas"]
 ]);
 if(type==="campanhas")out=pack(["ID campanha","Campanha","Data","ID canal","Origem","Enviadas","Entregues","Lidas","Respostas","Falhas","Tx. entrega","Tx. leitura","Tx. resposta única","Tx. falha"],
 rows.map(c=>{const v=M.summary([c]);return[c.campaignId,c.name,M.campaignDay(c),c.channelId,c.campaignOrigin||"Não atribuída",count(c.sent),count(c.delivered),count(c.read),count(c.replied),count(c.failures),rate(v.deliveryRate),rate(v.readRate),"Não disponível",rate(v.failureRate)];}));
 if(type==="diario")out=pack(["Data","Campanhas","Enviadas","Entregues","Lidas","Respostas","Falhas","Tx. entrega","Tx. leitura","Tx. falha"],
 M.daily(rows).map(x=>[x.day,x.campaigns,x.sent,x.delivered,x.read,x.replied,x.failures,rate(x.deliveryRate),rate(x.readRate),rate(x.failureRate)]));
 if(type==="canais")out=pack(["Canal ID","Nome","Conexão","Campanhas","Enviadas","Entregues","Lidas","Respostas","Falhas","Tx. entrega","Tx. leitura","Tx. falha"],
 M.channels(rows,state.channels).map(x=>{const s=x.summary;return[x.id,x.name,x.connection||"Não disponível",s.campaigns,...["sent","delivered","read","replied","failures"].map(k=>count(s.metrics[k].value)),rate(s.deliveryRate),rate(s.readRate),rate(s.failureRate)];}));
 if(type==="erros")out=pack(["ID campanha","Campanha","Data","Código","Tipo","Motivo","Descrição","Casos","Conciliação","Tratamento","Ação"],M.errorRows(rows).map(x=>[x.campaignId,x.name,x.day,x.code,x.type,x.title,x.description,x.count,x.reconciliation,x.recoverability,x.suggestion]));
 if(type==="respostas")out=pack(["ID campanha","Campanha","Data","Respostas agregadas","Nota"],rows.map(x=>[x.campaignId,x.name,M.campaignDay(x),count(x.replied),"Sem dados nominais no site público"]));
 if(type==="funil")out=pack(["Etapa","Contagem","Taxa"],funnelRows(s).map(x=>[x[0],count(x[1]),"Não disponível entre populações não vinculadas"]));
 const blob=new Blob([M.csv(out)],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(blob),a=E("a");a.href=url;a.download="LP_Crypto_"+type+"_"+M.today()+".csv";document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),5000);
}
function copy(){
 const s=M.summary(all()),message="LP Crypto | Disparos\nCampanhas: "+s.campaigns+"\nEnviadas: "+M.number(s.metrics.sent.value)+"\nEntregues: "+M.number(s.metrics.delivered.value)+"\nFalhas: "+M.number(s.metrics.failures.value)+"\nResposta por pessoas únicas: não disponível";
 if(navigator.clipboard?.writeText)navigator.clipboard.writeText(message).then(()=>{$("copyButton").textContent="✓ Copiado";setTimeout(()=>$("copyButton").textContent="⧉ Copiar resumo",2200)}).catch(()=>window.prompt("Copie:",message));else window.prompt("Copie:",message);
}
async function get(url,required=true){const r=await fetch(url,{cache:"no-store"});if(!r.ok){if(!required&&r.status===404)return null;throw new Error("HTTP "+r.status+" ao carregar "+url)}return r.json();}
async function load(){
 $("v2LoadStatus").textContent="Consultando dados da UmClique…";
 try{
  const [d,f]=await Promise.all([get("./data/disparos.json"),get("./data/funnel.json",false)]);
  if(!Array.isArray(d?.campaigns))throw new Error("Arquivo de campanhas inválido");
  state.rows=M.dedupe(d.campaigns);state.channels=Array.isArray(d.channels)?d.channels:[];state.meta=d.meta||{};state.funnel=f||{};state.ready=true;fillOptions();reset();render();
 }catch(ex){$("v2Kpis").replaceChildren(E("div","v2-error","Dados indisponíveis: "+String(ex?.message||ex)));$("v2LoadStatus").replaceChildren(E("div","v2-error","Confira o GitHub Actions e tente novamente."));const b=E("button","v2-action","Tentar novamente");b.addEventListener("click",load);$("v2LoadStatus").append(b);}
}
init();load();
window.LPCryptoV2={mounted:true,state:()=>({campaigns:state.rows.length,filters:{...state.filters}})};
})();
