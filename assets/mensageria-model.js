/* Pure metrics for UmClique inbox aggregation. Never receives contacts or message text. */
(function(root,factory){
  const api=factory();
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.LPMensageriaModel=api;
})(typeof globalThis!=="undefined"?globalThis:this,function(){
  "use strict";
  const modes=new Set(["all","today","yesterday","7d","30d","custom"]);
  function validDate(value){return typeof value==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(value);}
  function parseIsoDate(value){return validDate(value)?value:null;}
  function windowFor(period,today){
    if(!validDate(today))return null;
    const days={today:0,yesterday:1,"7d":6,"30d":29};
    if(!Object.prototype.hasOwnProperty.call(days,period))return null;
    const previous=(n)=>{
      const parts=today.split("-").map(Number);
      return new Date(Date.UTC(parts[0],parts[1]-1,parts[2]-n)).toISOString().slice(0,10);
    };
    return period==="yesterday"?{from:previous(1),to:previous(1)}:{from:previous(days[period]),to:today};
  }
  function resolve(data,filters,today){
    const period=modes.has(filters.period)?filters.period:"all";
    const owner=filters.owner||"all",channel=filters.channel||"all";
    if(period!=="custom"){
      const found=(data.rollups||[]).find(x=>x.period===period&&x.owner===owner&&x.channel===channel);
      return found||null;
    }
    const from=filters.from||"",to=filters.to||"";
    if(!validDate(from)||!validDate(to)||from>to)return null;
    const rows=(data.daily||[]).filter(x=>x.owner===owner&&x.channel===channel&&x.day>=from&&x.day<=to);
    return {
      period:"custom",owner,channel,
      inbound:rows.reduce((a,b)=>a+b.inbound,0),
      outbound:rows.reduce((a,b)=>a+b.outbound,0),
      contactsWithInbound:null,contactsInConversations:null,
      conversations:null,firstInboundConversations:null,
      lastInboundActiveConversations:null,unread:null,
      customDistinctUnavailable:true
    };
  }
  function daily(data,filters,today){
    const owner=filters.owner||"all",channel=filters.channel||"all";
    let rows=(data.daily||[]).filter(x=>x.owner===owner&&x.channel===channel);
    const win=filters.period==="custom"?
      {from:filters.from||null,to:filters.to||null}:
      windowFor(filters.period,today);
    if(win){
      rows=rows.filter(x=>(!win.from||x.day>=win.from)&&(!win.to||x.day<=win.to));
    }
    return rows.slice().sort((a,b)=>a.day.localeCompare(b.day));
  }
  function ownerRows(data,filters,today){
    return (data.owners||[]).filter(o=>filters.owner==="all"||!filters.owner||o.key===filters.owner)
      .map(owner=>({key:owner.key,name:owner.name,active:owner.active,
        ...(resolve(data,{...filters,owner:owner.key},today)||{})}));
  }
  function channelRows(data,filters,today){
    return (data.channels||[]).filter(c=>filters.channel==="all"||!filters.channel||c.id===filters.channel)
      .map(channel=>({id:channel.id,name:channel.name,
        ...(resolve(data,{...filters,channel:channel.id},today)||{})}));
  }
  function pct(part,total){
    return part==null||total==null||total<=0?null:part/total;
  }
  function sorted(rows,key,desc){
    return rows.slice().sort((a,b)=>{
      const x=a[key],y=b[key];
      if(x==null&&y!=null)return 1;
      if(y==null&&x!=null)return -1;
      if(x==null&&y==null)return 0;
      if(typeof x==="number"&&typeof y==="number")return (x-y)*(desc?-1:1);
      return String(x).localeCompare(String(y),"pt-BR",{numeric:true})*(desc?-1:1);
    });
  }
  return {resolve,daily,ownerRows,channelRows,windowFor,pct,sorted};
});
