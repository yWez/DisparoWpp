const assert=require("node:assert/strict");
const M=require("../assets/mensageria-model.js");
const sample={
 owners:[{key:"A",name:"Ana"},{key:"B",name:"Carol"}],
 channels:[{id:"X",name:"Canal LP"},{id:"Y",name:"Suporte"}],
 rollups:[
  {period:"all",owner:"all",channel:"all",inbound:12,outbound:7,
   contactsWithInbound:4,conversations:5,firstInboundConversations:3,
   lastInboundActiveConversations:1},
  {period:"all",owner:"A",channel:"all",inbound:8,outbound:5,
   contactsWithInbound:3,conversations:3},
  {period:"all",owner:"B",channel:"all",inbound:4,outbound:2,
   contactsWithInbound:1,conversations:2},
  {period:"all",owner:"all",channel:"X",inbound:9,outbound:6,contactsWithInbound:3},
  {period:"today",owner:"all",channel:"all",inbound:2,outbound:1,contactsWithInbound:1}
 ],
 daily:[
  {day:"2026-11-10",owner:"all",channel:"all",inbound:10,outbound:6,inboundContacts:3,conversations:4},
  {day:"2026-11-11",owner:"all",channel:"all",inbound:2,outbound:1,inboundContacts:1,conversations:1},
  {day:"2026-11-11",owner:"A",channel:"X",inbound:1,outbound:1,inboundContacts:1,conversations:1}
 ]};
const t=(name,fn)=>{fn();console.log("✓ "+name);};
t("exact unique contacts from server rollup",()=>{
 assert.equal(M.resolve(sample,{period:"all",owner:"all",channel:"all"}, "2026-11-11").contactsWithInbound,4);
});
t("owner breakdown by current ownership",()=>{
 const rows=M.ownerRows(sample,{period:"all",owner:"all",channel:"all"},"2026-11-11");
 assert.deepEqual(rows.map(x=>x.inbound),[8,4]);
});
t("channel filter exact rollup",()=>{
 assert.equal(M.resolve(sample,{period:"all",owner:"all",channel:"X"},"2026-11-11").inbound,9);
});
t("custom period sums messages but not unique contacts",()=>{
 const r=M.resolve(sample,{period:"custom",from:"2026-11-10",to:"2026-11-11",owner:"all",channel:"all"},"2026-11-11");
 assert.equal(r.inbound,12);assert.equal(r.outbound,7);
 assert.equal(r.contactsWithInbound,null);
 assert.equal(r.firstInboundConversations,null);
});
t("custom invalid range returns unavailable",()=>{
 assert.equal(M.resolve(sample,{period:"custom",from:"2026-11-12",to:"2026-11-11",owner:"all",channel:"all"},"2026-11-11"),null);
});
t("7 days anchored in Fortaleza calendar",()=>{
 assert.deepEqual(M.windowFor("7d","2026-11-11"),{from:"2026-11-05",to:"2026-11-11"});
});
t("daily graph respects period and channel",()=>{
 assert.equal(M.daily(sample,{period:"today",owner:"all",channel:"all"},"2026-11-11").length,1);
 assert.equal(M.daily(sample,{period:"all",owner:"A",channel:"X"},"2026-11-11")[0].inbound,1);
});
t("stable sort with unreported last",()=>{
 const x=M.sorted([{name:"A",inbound:null},{name:"B",inbound:3}], "inbound",true);
 assert.equal(x[0].name,"B");
});
const withCampaign={
 ...sample,
 campaign:{
  coverage:{scannedConversations:4,inScopeConversations:10,complete:false},
  rollups:[
   {period:"all",owner:"all",channel:"all",identifiedLeads:3,activeLeads:2,
    inboundFromLeads:14,outboundToLeads:8,markedConversations:4},
   {period:"all",owner:"A",channel:"all",identifiedLeads:2,activeLeads:2,
    inboundFromLeads:11,outboundToLeads:6},
   {period:"all",owner:"B",channel:"all",identifiedLeads:1,activeLeads:0,
    inboundFromLeads:3,outboundToLeads:2},
   {period:"today",owner:"all",channel:"all",identifiedLeads:1,activeLeads:1,
    inboundFromLeads:5,outboundToLeads:1}
  ],
  daily:[
   {day:"2026-11-10",owner:"all",channel:"all",identifiedLeads:2,activeLeads:2,inboundFromLeads:9,outboundToLeads:7},
   {day:"2026-11-11",owner:"all",channel:"all",identifiedLeads:1,activeLeads:1,inboundFromLeads:5,outboundToLeads:1}
  ]
 }
};
t("Luisa total follows detected unique-lead rollup",()=>{
 const got=M.campaignResolve(withCampaign,{period:"all",owner:"all",channel:"all"},"2026-11-11");
 assert.equal(got.identifiedLeads,3);
 assert.equal(got.inboundFromLeads,14);
});
t("Luisa owner filter uses current assigned lead",()=>{
 const owners=M.campaignOwners(withCampaign,{period:"all",owner:"all",channel:"all"},"2026-11-11");
 assert.deepEqual(owners.map(x=>x.identifiedLeads),[2,1]);
});
t("Luisa custom sums first-event leads but avoids double count of active people",()=>{
 const r=M.campaignResolve(withCampaign,{period:"custom",owner:"all",channel:"all",
   from:"2026-11-10",to:"2026-11-11"},"2026-11-11");
 assert.equal(r.identifiedLeads,3);
 assert.equal(r.inboundFromLeads,14);
 assert.equal(r.activeLeads,null);
});
t("Luisa absent snapshot cannot be mistaken for zero",()=>{
 assert.equal(M.campaignResolve(sample,{period:"all",owner:"all",channel:"all"},"2026-11-11"),null);
});
console.log("12 testes JavaScript de mensageria aprovados.");
