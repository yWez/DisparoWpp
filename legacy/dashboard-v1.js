
    (function () {
      "use strict";
      var campaigns = [];
      var meta = {};
      var br = new Intl.NumberFormat("pt-BR");
      var pc = function (x) { return (Number(x || 0) * 100).toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2}) + "%"; };
      var $ = function (id) { return document.getElementById(id); };
      var el = function (tag, cls, value) {
        var node = document.createElement(tag);
        if (cls) node.className = cls;
        if (value !== undefined) node.textContent = value;
        return node;
      };
      function totals() {
        return campaigns.reduce(function (a, c) {
          a.sent += c.sent;
          a.failures += c.failures;
          a.contacts += c.contacts;
          a.finished += c.status.toLowerCase().indexOf("conclu") >= 0 ? 1 : 0;
          return a;
        },{sent:0,failures:0,contacts:0,finished:0});
      }
      function drawKPIs() {
        var t=totals(),rate=t.sent?t.failures/t.sent:0;
        $("kpiSent").textContent=br.format(t.sent);
        $("kpiFail").textContent=br.format(t.failures);
        $("kpiFailRate").textContent=pc(rate)+" dos envios";
        $("kpiNoFail").textContent=br.format(t.sent-t.failures);
        $("kpiCampaigns").textContent=t.finished+"/"+campaigns.length;
        ["delivered","read","replied","conversions"].forEach(function(key){
          var known=campaigns.filter(function(c){return c[key] !== null && c[key] !== undefined && c[key] !== "";});
          var name=key.charAt(0).toUpperCase()+key.slice(1);
          $("kpi"+name).textContent=known.length?br.format(known.reduce(function(a,c){return a+Number(c[key]);},0)):"—";
          $("kpi"+name+"Coverage").textContent=known.length===0?"Ainda não apurado":(known.length===campaigns.length?"Todas as campanhas":"Parcial: "+known.length+"/"+campaigns.length+" campanhas");
        });
        $("rateNumber").textContent=pc(rate);
        $("ringPercent").textContent=pc(rate);
        $("ring").style.background="conic-gradient(#ed7282 0% "+(rate*100)+"%, #8d74e6 "+(rate*100)+"% 100%)";
        $("periodBadge").textContent=meta.periodLabel||"Período não definido";
        var latestSync=meta.lastSyncedAt?new Date(meta.lastSyncedAt):null;
        if(latestSync && !Number.isNaN(latestSync.getTime())){
          $("updateLabel").textContent="Última sincronização: "+new Intl.DateTimeFormat("pt-BR",{
            dateStyle:"short",timeStyle:"short",timeZone:"America/Fortaleza"
          }).format(latestSync);
          $("footerSource").textContent="Origem: UmClique API • atualização programada no GitHub";
        }else{
          $("updateLabel").textContent="Base conferida em "+(meta.snapshotDate?meta.snapshotDate.split("-").reverse().join("/"):"data não informada")+" • histórico manual";
          $("footerSource").textContent="Origem: conferência manual • sincronização pendente";
        }
        if(meta.spreadsheetUrl) $("sheetLink").href=meta.spreadsheetUrl;
        var worst=campaigns.slice().sort(function(a,b){return (b.failures/b.sent)-(a.failures/a.sent);})[0];
        if(worst){
          $("insightTitle").textContent="Maior taxa: "+worst.name;
          $("insightText").textContent=pc(worst.failures/worst.sent)+" de falhas ("+worst.failures+" de "+worst.sent+" envios). Investigar as causas na plataforma antes de novo envio.";
        }
        var notes=$("caveats"); notes.replaceChildren();
        (meta.caveats||[]).forEach(function(note){notes.appendChild(el("li","",note));});
      }
      function drawVolume() {
        var wrap=$("volumeBars");wrap.replaceChildren();
        var max=Math.max.apply(null,campaigns.map(function(c){return c.sent;}))||1;
        campaigns.forEach(function(c){
          var row=el("div","bar-row");
          row.appendChild(el("span","bar-name",c.name.replace(" - Wes","")));
          var track=el("div","bar-track");
          var width=100*c.sent/max;
          var good=el("div","bar-good"),bad=el("div","bar-bad");
          good.style.width=(width*((c.sent-c.failures)/c.sent))+"%";
          bad.style.width=(width*c.failures/c.sent)+"%";
          good.setAttribute("aria-label",(c.sent-c.failures)+" sem falha registrada");
          bad.setAttribute("aria-label",c.failures+" falhas");
          track.appendChild(good);track.appendChild(bad);row.appendChild(track);
          row.appendChild(el("span","bar-value",br.format(c.sent)));
          wrap.appendChild(row);
        });
        var rates=$("rateBars");rates.replaceChildren();
        campaigns.slice().sort(function(a,b){return (b.failures/b.sent)-(a.failures/a.sent);}).forEach(function(c){
          var row=el("div","ratebar");
          row.appendChild(el("span","",c.name.replace(" - Wes","")));
          var mini=el("div","mini"),bar=el("div");
          bar.style.width=Math.min(100,100*c.failures/c.sent/0.20)+"%";
          mini.appendChild(bar);row.appendChild(mini);
          row.appendChild(el("strong","",pc(c.failures/c.sent)));
          rates.appendChild(row);
        });
      }
      function drawTable() {
        var filter=$("search").value.toLocaleLowerCase("pt-BR"),order=$("sort").value;
        var a=campaigns.filter(function(c){return (c.name+" "+c.status+" "+c.timeLabel).toLocaleLowerCase("pt-BR").indexOf(filter)>=0;});
        if(order==="rate")a.sort(function(x,y){return y.failures/y.sent-x.failures/x.sent;});
        if(order==="fail")a.sort(function(x,y){return y.failures-x.failures;});
        if(order==="sent")a.sort(function(x,y){return y.sent-x.sent;});
        var tbody=$("campaignRows");tbody.replaceChildren();
        if(!a.length){var empty=el("td","loading","Nenhuma campanha encontrada.");empty.colSpan=11;var er=el("tr");er.appendChild(empty);tbody.appendChild(er);return;}
        a.forEach(function(c){
          var tr=el("tr"),stat=el("span","status"),dot=el("span","dot");
          stat.appendChild(dot);stat.appendChild(document.createTextNode(c.status));
          var tdc=el("td");tdc.appendChild(el("strong","",c.name));tr.appendChild(tdc);
          var tdstatus=el("td");tdstatus.appendChild(stat);tr.appendChild(tdstatus);
          tr.appendChild(el("td","",br.format(c.contacts)));
          tr.appendChild(el("td","",br.format(c.sent)));
          tr.appendChild(el("td","table-bad",br.format(c.failures)));
          tr.appendChild(el("td","",br.format(c.sent-c.failures)));
          ["delivered","read","replied"].forEach(function(key){
            tr.appendChild(el("td","",c[key]===null||c[key]===undefined?"—":br.format(Number(c[key]))));
          });
          var pcell=el("td"),pr=el("div","progress"),ptr=el("div","progress-track"),pbar=el("div","progress-bar");
          pbar.style.width=Math.min(100,100*c.failures/c.sent/0.20)+"%";
          ptr.appendChild(pbar);pr.appendChild(ptr);pr.appendChild(el("strong","",pc(c.failures/c.sent)));pcell.appendChild(pr);tr.appendChild(pcell);
          tr.appendChild(el("td","muted small",c.timeLabel));
          tbody.appendChild(tr);
        });
      }
      function safeCsv(x) {return '"'+String(x==null?"":x).replace(/"/g,'""')+'"';}
      function exportCsv() {
        var header=["Campanha","Contatos","Enviados","Falhas","Sem falha registrada","Taxa falha (%)","Status","Tempo no print"];
        var lines=[header].concat(campaigns.map(function(c){return[c.name,c.contacts,c.sent,c.failures,c.sent-c.failures,(100*c.failures/c.sent).toFixed(2),c.status,c.timeLabel];}));
        var csv="\uFEFF"+lines.map(function(row){return row.map(safeCsv).join(";");}).join("\r\n");
        var file=new Blob([csv],{type:"text/csv;charset=utf-8"}),url=URL.createObjectURL(file),link=document.createElement("a");
        link.href=url;link.download="lpcrypto_disparos_2026-11-09_10.csv";document.body.appendChild(link);link.click();link.remove();setTimeout(function(){URL.revokeObjectURL(url);},1000);
      }
      function copySummary() {
        var t=totals();
        var msg="LP CRYPTO | DISPAROS WHATSAPP\nPeríodo: "+(meta.periodLabel||"Não definido")+"\n"+
          "Campanhas concluídas: "+t.finished+"/"+campaigns.length+"\n"+
          "Envios registrados: "+t.sent+"\nFalhas: "+t.failures+" ("+pc(t.sent?t.failures/t.sent:0)+")\n"+
          "Sem falha registrada: "+(t.sent-t.failures)+"\n"+
          "Observação: sem falha não comprova entrega; contatos podem se repetir entre campanhas.";
        if(navigator.clipboard && navigator.clipboard.writeText){
          navigator.clipboard.writeText(msg).then(function(){
            var b=$("copyButton");b.textContent="✓ Resumo copiado";setTimeout(function(){b.textContent="⧉ Copiar resumo";},2500);
          }).catch(function(){window.prompt("Copie o resumo:",msg);});
        }else{window.prompt("Copie o resumo:",msg);}
      }
      function load(){
        fetch("./data/disparos.json",{cache:"no-store"})
          .then(function(r){if(!r.ok)throw Error("HTTP "+r.status);return r.json();})
          .then(function(data){
            if(!data || !Array.isArray(data.campaigns))throw Error("Arquivo de dados inválido");
            meta=data.meta||{};
            campaigns=data.campaigns.map(function(x){
              return Object.assign({},x,{sent:Number(x.sent)||0,contacts:Number(x.contacts)||0,failures:Number(x.failures)||0});
            }).filter(function(x){return x.sent>0&&x.failures>=0&&x.failures<=x.sent;});
            drawKPIs();drawVolume();drawTable();
          })
          .catch(function(err){
            $("volumeBars").replaceChildren(el("div","error","Não foi possível carregar os dados: "+err.message+". Verifique o arquivo data/disparos.json no repositório."));
            $("campaignRows").innerHTML='<tr><td colspan="8" class="loading">Dados indisponíveis.</td></tr>';
            $("insightTitle").textContent="Dados indisponíveis";
            $("insightText").textContent="Confira a publicação da página e o arquivo JSON.";
          });
      }
      $("search").addEventListener("input",drawTable);
      $("sort").addEventListener("change",drawTable);
      $("exportCsv").addEventListener("click",exportCsv);
      $("copyButton").addEventListener("click",copySummary);
      load();
    }());