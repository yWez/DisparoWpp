/**
 * LP Crypto — agendador externo dedicado às campanhas UmClique.
 *
 * Projeto STANDALONE em https://script.google.com/home/projects/create
 * Segredo GITHUB_ACTIONS_TOKEN configurado SOMENTE em Propriedades do Script.
 * Token GitHub fine-grained: repositório DisparoWpp, Actions: Read and write.
 *
 * A cada 5 min solicita ao GitHub a execução do workflow RÁPIDO;
 * o GitHub continua responsável por UmClique, Sheets, JSON e GitHub Pages.
 * Nenhuma chave UmClique ou dado de lead reside neste Apps Script.
 */
const LP_CONFIG = Object.freeze({
  dispatchUrl: 'https://api.github.com/repos/yWez/DisparoWpp/actions/workflows/sync-campaigns-fast.yml/dispatches',
  timezone: 'America/Fortaleza',
  minBetweenSuccessMs: 4 * 60 * 1000,
  triggerFunction: 'dispararAtualizacaoLP',
  triggerEveryMinutes: 5
});

/** Executar UMA vez no editor após configurar GITHUB_ACTIONS_TOKEN. */
function instalarAgendadorLP() {
  const key = PropertiesService.getScriptProperties().getProperty('GITHUB_ACTIONS_TOKEN');
  if (!key || !key.trim()) {
    throw new Error('Configure GITHUB_ACTIONS_TOKEN nas Propriedades do Script. Nunca cole a chave no código.');
  }
  // Validate credentials BEFORE scheduling repeated requests.
  dispararAtualizacaoLP(true);
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === LP_CONFIG.triggerFunction)
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger(LP_CONFIG.triggerFunction)
    .timeBased().everyMinutes(LP_CONFIG.triggerEveryMinutes).create();
  console.log('Agendador externo LP Crypto instalado: checagem a cada 5 minutos.');
}

/**
 * Uma chamada cria uma solicitação GitHub workflow_dispatch (HTTP 204).
 * NÃO significa que a coleta foi concluída: conferir Actions para resultado.
 */
function dispararAtualizacaoLP(forcar) {
  const lock = LockService.getScriptLock();
  if (!lock.tryLock(30000)) {
    console.log('Outra instância já está disparando; ignorando duplicação.');
    return;
  }
  try {
    const props = PropertiesService.getScriptProperties();
    const now = Date.now();
    const last = Number(props.getProperty('LAST_DISPATCH_OK_MS') || 0);
    if (!forcar && now - last < LP_CONFIG.minBetweenSuccessMs) {
      console.log('Último disparo aceito há menos de 4 minutos; ignorando duplicação.');
      return;
    }
    const token = (props.getProperty('GITHUB_ACTIONS_TOKEN') || '').trim();
    if (!token) throw new Error('GITHUB_ACTIONS_TOKEN não configurado');
    const res = UrlFetchApp.fetch(LP_CONFIG.dispatchUrl, {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify({ref: 'main'}),
      headers: {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Authorization': 'Bearer ' + token,
        'User-Agent': 'LP-Crypto-Scheduler'
      },
      muteHttpExceptions: true
    });
    const status = res.getResponseCode();
    if (status !== 204) {
      props.setProperty('LAST_DISPATCH_ERROR',
        JSON.stringify({status: status, at: new Date(now).toISOString()}));
      throw new Error('GitHub recusou o disparo. HTTP ' + status +
        '. Confira permissão Actions:write e validade do token.');
    }
    props.setProperty('LAST_DISPATCH_OK_MS', String(now));
    props.setProperty('LAST_DISPATCH_OK_AT', new Date(now).toISOString());
    props.deleteProperty('LAST_DISPATCH_ERROR');
    console.log('GitHub aceitou execução de atualização de campanhas às ' +
      Utilities.formatDate(new Date(now), LP_CONFIG.timezone, 'dd/MM/yyyy HH:mm:ss'));
  } finally {
    lock.releaseLock();
  }
}

/** Inspecionar o status na tela Execuções, sem exibir o token. */
function statusAgendadorLP() {
  const props = PropertiesService.getScriptProperties();
  const triggers = ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === LP_CONFIG.triggerFunction);
  console.log(JSON.stringify({
    configurado: Boolean(props.getProperty('GITHUB_ACTIONS_TOKEN')),
    acionadoresAtivos: triggers.length,
    ultimaSolicitacaoAceita: props.getProperty('LAST_DISPATCH_OK_AT') || null,
    ultimoErro: props.getProperty('LAST_DISPATCH_ERROR') || null
  }, null, 2));
}

/** Desativar somente o agendador LP Crypto. */
function desativarAgendadorLP() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === LP_CONFIG.triggerFunction)
    .forEach(t => ScriptApp.deleteTrigger(t));
  console.log('Agendador externo desativado.');
}
