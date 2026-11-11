/* LP Crypto / DisparoWpp — pure, testable data model. No secrets or PII. */
(function(root,factory){
  var m=factory();
  if(typeof module!=="undefined"&&module.exports)module.exports=m;
  root.LPCryptoModel=m;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  "use strict";
  var TZ="America/Fortaleza";
  var fmt=new Intl.DateTimeFormat("en-GB",{timeZone:TZ,year:"numeric",month:"2-digit",day:"2-digit"});
  function ymd(date){if(!date||Number.isNaN(date.getTime()))return null;var x=Object.fromEntries(fmt.formatToParts(date).map(p=>[p.type,p.value]));return x.year+"-"+x.month+"-"+x.day;}
  function campaignDay(c){
    var iso=c.startedAt||c.createdAt;
    if(iso){var day=ymd(new Date(iso));if(day)return day;}
    var m=String(c.period||"").match(/^(\d\d)\/(\d\d)\/(\d{4})$/);
    return m?m[3]+"-"+m[2]+"-"+m[1]:null;
  }
  function today(){return ymd(new Date());}
  function daysBefore(day,n){var p=day.split("-").map(Number),d=new Date(Date.UTC(p[0],p[1]-1,p[2]-n));return d.toISOString().slice(0,10);}
  function validMetric(c,key){return c && typeof c[key]==="number" && Number.isFinite(c[key]) && c[key]>=0;}
  function dedupe(rows){
    var map=new Map();
    (Array.isArray(rows)?rows:[]).forEach(function(c){
      if(!c||typeof c!=="object")return;
      var id=String(c.campaignId||c.id||"");
      if(!id)return;
      var next=Object.assign({},c,{campaignId:id});
      map.set(id,next);
    });
    return Array.from(map.values());
  }
  function filter(rows,filters){
    filters=filters||{};var now=filters.today||today(),period=filters.period||"all";
    var from=filters.from,to=filters.to;
    if(period==="today")from=to=now;
    else if(period==="yesterday")from=to=daysBefore(now,1);
    else if(period==="7d"){from=daysBefore(now,6);to=now;}
    else if(period==="30d"){from=daysBefore(now,29);to=now;}
    else if(period!=="custom"){from=null;to=null;}
    return dedupe(rows).filter(function(c){
      var day=campaignDay(c);
      if(from&&(!day||day<from))return false;
      if(to&&(!day||day>to))return false;
      if(filters.campaign&&filters.campaign!=="all"&&c.campaignId!==filters.campaign)return false;
      if(filters.channel&&filters.channel!=="all"){
        var chans=Array.isArray(c.channelIds)&&c.channelIds.length?c.channelIds:[c.channelId||""];
        if(!chans.includes(filters.channel))return false;
      }
      if(filters.origin&&filters.origin!=="all"&&(c.campaignOrigin||"Não atribuída")!==filters.origin)return false;
      if(filters.status&&filters.status!=="all"){
        var key={sent:"sent",delivered:"delivered",read:"read",replied:"replied",failed:"failures"}[filters.status];
        // Campaign-level selection, not an individual-message status filter.
        if(!key||!validMetric(c,key)||c[key]===0)return false;
      }
      return true;
    });
  }
  function metric(rows,key){
    var valid=rows.filter(c=>validMetric(c,key));
    var total=valid.reduce((a,c)=>a+c[key],0);
    return {value:valid.length===rows.length?total:null,knownTotal:total,complete:valid.length===rows.length,known:valid.length,count:rows.length};
  }
  function rate(n,d){return n==null||d==null||!Number.isFinite(n)||!Number.isFinite(d)||d<=0?null:n/d;}
  function summary(rows){
    var cols={};["sent","delivered","read","replied","failures","contacts","conversions"].forEach(k=>cols[k]=metric(rows,k));
    var val=k=>cols[k].value;
    return {
      metrics:cols,
      campaigns:rows.length,
      deliveryRate:rate(val("delivered"),val("sent")),
      readRate:rate(val("read"),val("delivered")),
      // True person-level response rate is NOT derivable from aggregated broadcasts.
      responseRate:null,
      proxyResponseRate:rate(val("replied"),val("delivered")),
      failureRate:rate(val("failures"),val("sent")),
      uniqueReached:null,
      responseRateReason:"Faltam IDs únicos de contatos entregues e respondentes, com deduplicação entre campanhas.",
      uniqueReason:"A API agregada não permite deduplicar pessoas entre vários disparos."
    };
  }
  function daily(rows){
    var groups=new Map();
    rows.forEach(function(c){
      var day=campaignDay(c);if(!day)return;
      if(!groups.has(day))groups.set(day,[]);
      groups.get(day).push(c);
    });
    return Array.from(groups.entries()).sort((a,b)=>a[0].localeCompare(b[0])).map(function(e){
      var s=summary(e[1]);return {
        day:e[0],campaigns:e[1].length,
        sent:s.metrics.sent.value,delivered:s.metrics.delivered.value,
        read:s.metrics.read.value,replied:s.metrics.replied.value,failures:s.metrics.failures.value,
        deliveryRate:s.deliveryRate,readRate:s.readRate,responseRate:s.responseRate,
        proxyResponseRate:s.proxyResponseRate,failureRate:s.failureRate
      };
    });
  }
  function channels(rows,meta){
    var infos=new Map((meta||[]).map(x=>[String(x.id),x]));
    var groups=new Map();
    rows.forEach(function(c){
      var ids=Array.isArray(c.channelIds)&&c.channelIds.length?c.channelIds:[c.channelId||"unknown"];
      var id=ids.length===1?ids[0]:"multiple";
      if(!groups.has(id))groups.set(id,[]);
      groups.get(id).push(c);
    });
    return Array.from(groups.entries()).map(function(e){
      var info=infos.get(e[0])||{},s=summary(e[1]);
      return {id:e[0],name:e[0]==="multiple"?"Campanhas multi-canal (não rateadas)":info.name||e[1][0].channelName||("Canal "+e[0].slice(0,8)),
        connection:info.status||e[1][0].channelStatus||null,limit:null,summary:s};
    }).sort((a,b)=>(b.summary.metrics.sent.knownTotal)-(a.summary.metrics.sent.knownTotal));
  }
  function errorRows(rows){
    var out=[];
    rows.forEach(function(c){
      var d=c.errorDiagnostics;
      if(!d||!Array.isArray(d.groups))return;
      d.groups.forEach(function(g){out.push(Object.assign({
        campaignId:c.campaignId,name:c.name,day:campaignDay(c),channelId:c.channelId,
        reconciliation:d.summary?.failedTotal!=null&&c.failures!=null&&d.summary.failedTotal!==c.failures?"Divergente":"Sem divergência detectada",
      },g));});
    });
    return out;
  }
  function originGroups(rows){
    var groups=new Map();
    rows.forEach(function(c){var name=c.campaignOrigin||"Não atribuída";if(!groups.has(name))groups.set(name,[]);groups.get(name).push(c);});
    return Array.from(groups.entries()).map(e=>({origin:e[0],summary:summary(e[1])})).sort((a,b)=>b.summary.metrics.sent.knownTotal-a.summary.metrics.sent.knownTotal);
  }
  function pct(x){return x==null?"Não disponível":(x*100).toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2})+"%";}
  function number(x){return x==null?"Não disponível":x.toLocaleString("pt-BR");}
  function csv(rows){
    function escapeValue(v){
      var s=v==null?"Não disponível":String(v);
      if(/^[\s]*[=+\-@\t\r\n]/.test(s))s="'"+s;
      return '"'+s.replace(/"/g,'""')+'"';
    }
    return "\uFEFF"+rows.map(r=>r.map(escapeValue).join(";")).join("\r\n")+"\r\n";
  }
  function thresholds(row,t){
    t=t||{};var s=summary([row]),min=Number(t.minSent||30),maxFail=Number(t.maxFailureRate??0.15),minDelivery=Number(t.minDeliveryRate??0.80);
    if((row.sent||0)<min)return "Amostra pequena";
    if(s.failureRate!=null&&s.failureRate>=maxFail)return "Atenção: falhas";
    if(s.deliveryRate!=null&&s.deliveryRate<minDelivery)return "Atenção: entrega";
    if(s.deliveryRate!=null&&s.deliveryRate>=minDelivery)return "Dentro do critério";
    return "Sem diagnóstico";
  }
  return {TZ,ymd,campaignDay,today,daysBefore,dedupe,filter,metric,rate,summary,daily,channels,errorRows,originGroups,pct,number,csv,thresholds};
});
