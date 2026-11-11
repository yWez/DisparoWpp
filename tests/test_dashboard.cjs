
const assert=require("node:assert/strict");
const M=require("../assets/model.js");
const campaign=(id,iso,channelId,sent,delivered,read,replied,failures)=>({
 id,campaignId:id,name:id,startedAt:iso,channelId,channelIds:[channelId],
 sent,delivered,read,replied,failures,contacts:sent
});
const rows=[
 campaign("D1","2026-11-09T23:15:00Z","chA",100,85,60,8,12),
 campaign("D2","2026-11-10T01:00:00Z","chB",50,40,20,3,10),
 campaign("D3","2026-11-10T15:00:00Z","chA",50,null,15,2,4)
];
function check(name,fn){fn();console.log("✓ "+name);}
check("fuso Fortaleza atravessa meia-noite corretamente",()=>{
 assert.equal(M.campaignDay(rows[0]),"2026-11-09");
 assert.equal(M.campaignDay(rows[1]),"2026-11-09");
 assert.equal(M.campaignDay(rows[2]),"2026-11-10");
});
check("filtro de período personalizado inclusivo",()=>{
 assert.equal(M.filter(rows,{period:"custom",from:"2026-11-10",to:"2026-11-10"}).length,1);
});
check("filtro global canal e status",()=>{
 assert.deepEqual(M.filter(rows,{channel:"chA",status:"replied"}).map(x=>x.campaignId),["D1","D3"]);
 assert.deepEqual(M.filter(rows,{channel:"chB",status:"failed"}).map(x=>x.campaignId),["D2"]);
});
check("não infere taxa com métrica parcial",()=>{
 const s=M.summary(rows);
 assert.equal(s.metrics.sent.value,200);
 assert.equal(s.metrics.delivered.value,null);
 assert.equal(s.deliveryRate,null);
 assert.equal(s.readRate,null);
 assert.equal(s.responseRate,null);
 assert.equal(s.uniqueReached,null);
});
check("taxas com denominadores corretos",()=>{
 const s=M.summary(rows.slice(0,2));
 assert.equal(s.metrics.delivered.value,125);
 assert.equal(s.deliveryRate,125/150);
 assert.equal(s.readRate,80/125);
 assert.equal(s.failureRate,22/150);
 assert.equal(s.responseRate,null);
 assert.equal(s.proxyResponseRate,11/125);
});
check("agrega por dia de início da campanha",()=>{
 const d=M.daily(rows);
 assert.equal(d.length,2);
 assert.equal(d[0].day,"2026-11-09");
 assert.equal(d[0].campaigns,2);
 assert.equal(d[0].sent,150);
 assert.equal(d[1].day,"2026-11-10");
});
check("canal agrupado sem duplicar campanhas",()=>{
 const c=M.channels(rows,[{id:"chA",name:"Canal A",status:"connected"},{id:"chB",name:"Canal B"}]);
 assert.equal(c.length,2);
 assert.equal(c.find(x=>x.id==="chA").summary.metrics.sent.value,150);
 assert.equal(c.find(x=>x.id==="chA").connection,"connected");
});
check("deduplicação por ID de campanha",()=>{
 assert.equal(M.dedupe([rows[0],rows[0],rows[1]]).length,2);
});
check("sem dados não representa pessoas únicas",()=>{
 assert.equal(M.summary([]).uniqueReached,null);
 assert.equal(M.summary([]).responseRate,null);
 assert.equal(M.rate(0,0),null);
});
check("CSV Excel inclui BOM e neutraliza fórmulas",()=>{
 const csv=M.csv([["ID","Telefone"],["123","=HYPERLINK(1)"],["=cmd","-1"]]);
 assert.ok(csv.startsWith("\uFEFF"));
 assert.ok(csv.includes("'=HYPERLINK"));
 assert.ok(csv.includes("'-1"));
 assert.ok(csv.includes(";"));
});
check("análises de erros preservam vínculo por campanha",()=>{
 const r=Object.assign({},rows[0],{errorDiagnostics:{groups:[{code:"131049",count:2,title:"Bloqueio"}]}});
 const a=M.errorRows([r]);
 assert.equal(a.length,1);assert.equal(a[0].campaignId,"D1");assert.equal(a[0].count,2);
});
check("origem desconhecida não é inventada",()=>{
 assert.equal(M.originGroups(rows)[0].origin,"Não atribuída");
});
console.log("12 verificações de modelagem concluídas.");
