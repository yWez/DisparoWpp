/**
 * LP Crypto — scheduler externo. Standalone Apps Script:
 * https://script.google.com/home/projects/create
 *
 * Defina GITHUB_ACTIONS_TOKEN em Configurações > Propriedades do Script.
 * Token fine-grained GitHub: Actions (Read & write), apenas DisparoWpp.
 * NÃO coloque o segredo no código nem no Google Sheets compartilhado.
 *
 * 5 minutos: novas campanhas, métricas e Google Sheets.
 * 15 minutos: mensageria, X1, campanha Luisa + campanhas.
 * Os fluxos GitHub preservam Secrets UmClique e Google e publicam agregados.
 */
const LP = Object.freeze({
  api: 'https://api.github.com/repos/yWez/DisparoWpp/actions/workflows/',
  timezone:'America/Fortaleza',
  jobs:[
    {handler:'dispararCampanhasLP', workflow:'sync-campaigns-fast.yml',
     label:'CAMPANHAS', minutes:5},
    {handler:'dispararMensageriaLP', workflow:'sync-umclique.yml',
     label:'MENSAGERIA_X1', minutes:15}
  ]
});

function dispararCampanhasLP() {
  return enviarWorkflowLP_('sync-campaigns-fast.yml','CAMPANHAS',4,false);
}

function dispararMensageriaLP() {
  return enviarWorkflowLP_('sync-umclique.yml','MENSAGERIA_X1',14,false);
}

function enviarWorkflowLP_(filename,key,minMinutes,force) {
  const lock=LockService.getScriptLock();
  if(!lock.tryLock(30000)) {
    console.log('Outra execução de agendamento está em curso.');
    return false;
  }
  try {
    const props=PropertiesService.getScriptProperties();
    const last=Number(props.getProperty('LAST_OK_MS_'+key)||0);
    const now=Date.now();
    if(!force && now-last < minMinutes*60000) return false;
    const token=(props.getProperty('GITHUB_ACTIONS_TOKEN')||'').trim();
    if(!token) throw new Error('GITHUB_ACTIONS_TOKEN não configurado em Propriedades do Script');
    const response=UrlFetchApp.fetch(LP.api+filename+'/dispatches',{
      method:'post',
      contentType:'application/json',
      payload:JSON.stringify({ref:'main'}),
      headers:{
        Accept:'application/vnd.github+json',
        'X-GitHub-Api-Version':'2022-11-28',
        Authorization:'Bearer '+token,
        'User-Agent':'LP-Crypto-Agendador'
      },
      muteHttpExceptions:true
    });
    const status=response.getResponseCode();
    if(status!==204) {
      props.setProperty('LAST_ERROR_'+key,
          JSON.stringify({at:new Date(now).toISOString(),status}));
      throw new Error('Disparo '+key+' recusado pelo GitHub. HTTP '+status);
    }
    props.setProperty('LAST_OK_MS_'+key,String(now));
    props.setProperty('LAST_OK_AT_'+key,new Date(now).toISOString());
    props.deleteProperty('LAST_ERROR_'+key);
    console.log(key+': solicitação aceita pelo GitHub em '+
      Utilities.formatDate(new Date(now),LP.timezone,'dd/MM/yyyy HH:mm:ss')+
      '. Consulte o GitHub Actions para confirmar conclusão.');
    return true;
  }finally {
    lock.releaseLock();
  }
}

/** Uma vez após configurar Script Properties; valida acesso antes de instalar. */
function instalarAgendadorLP() {
  const props=PropertiesService.getScriptProperties();
  if(!(props.getProperty('GITHUB_ACTIONS_TOKEN')||'').trim())
    throw new Error('Adicione GITHUB_ACTIONS_TOKEN nas Propriedades do Script primeiro.');
  // Testes de autenticação: não cria gatilho se a chave falhar.
  enviarWorkflowLP_('sync-campaigns-fast.yml','CAMPANHAS',4,true);
  enviarWorkflowLP_('sync-umclique.yml','MENSAGERIA_X1',14,true);
  const handlers=new Set(LP.jobs.map(j=>j.handler));
  ScriptApp.getProjectTriggers()
    .filter(t=>handlers.has(t.getHandlerFunction()))
    .forEach(t=>ScriptApp.deleteTrigger(t));
  LP.jobs.forEach(j=>{
    ScriptApp.newTrigger(j.handler).timeBased().everyMinutes(j.minutes).create();
  });
  console.log('Instalados 2 gatilhos: campanhas / 5 min, mensageria+X1 / 15 min.');
}

function statusAgendadorLP() {
  const props=PropertiesService.getScriptProperties();
  const handlers=ScriptApp.getProjectTriggers().map(x=>x.getHandlerFunction());
  const result=LP.jobs.map(j=>({
    nome:j.label,intervaloMin:j.minutes,ativo:handlers.includes(j.handler),
    ultimoPedidoAceito:props.getProperty('LAST_OK_AT_'+j.label)||'Não registrado',
    ultimoErro:props.getProperty('LAST_ERROR_'+j.label)||null
  }));
  console.log(JSON.stringify(result,null,2));
}

function desativarAgendadorLP() {
  const handlers=new Set(LP.jobs.map(j=>j.handler));
  ScriptApp.getProjectTriggers()
    .filter(t=>handlers.has(t.getHandlerFunction()))
    .forEach(t=>ScriptApp.deleteTrigger(t));
  console.log('Agendadores LP Crypto removidos.');
}
