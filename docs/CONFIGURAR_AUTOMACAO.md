> **Atualização 11/11/2026 — correção do erro HTTP 403:** os sete disparos foram reconhecidos em dois canais Meta. O GitHub bloqueou a tentativa de gravar uma variável automaticamente. Corrigimos o fluxo: agora o sincronizador **descobre os canais diretamente pela API** e não precisa criar variáveis. O workflow **Descobrir canal UmClique** também foi atualizado para apenas validar a descoberta, sem modificar configurações do GitHub.

# Automação UmClique → Google Sheets → DisparoWpp

**Revisão:** 11/11/2026  
**Estado:** código e fluxo preparados, **aguardando configurações privadas** para funcionar.  
**Implementação:** GitHub Actions a cada 15 minutos, sem n8n.

## Endpoints oficiais confirmados

Documentação: https://connect.umcliquedigital.com/docs/api#description/introduction

- Base da API: **https://api.umcliquedigital.com**
- Autenticação: cabeçalho **X-API-Key** com chave gerada em **Configurações → API & Webhooks**.
- **GET /functions/v1/public-broadcasts** — lista transmissões; suporta filtros channel_id, provider, created_from e paginação limit/offset (até 100).
- **GET /functions/v1/public-broadcasts/{id}/metrics** — relatório de uma transmissão.
- **GET /functions/v1/public-broadcasts/{id}/errors** — falhas por transmissão.
- **GET /functions/v1/public-broadcasts/{id}** — detalhes da transmissão.

A listagem traz **id, name, status, total_contacts, sent_count, delivered_count, read_count, failed_count, responded_count, conversion_count, started_at, completed_at, created_at e channels**. O relatório de métricas inclui **counters, queue_by_status, by_channel, conversions, rates**. Percentuais no endpoint são dados em escala 0–100, não 0–1.

O webhook documentado **POST /functions/v1/public-create-webhook-split** encaminha eventos **inbound** (mensagens recebidas de um canal). Não há evento de conclusão de disparo claramente documentado. Por isso usamos consulta programada, que é suficiente para o objetivo.

## Fluxo construído

~~~text
GitHub Actions, a cada 15 minutos
  → API UmClique: lista campanhas do canal LP Crypto / Meta
  → métricas por ID quando necessárias
  → remove dados pessoais e normaliza os contadores
  → concilia os 7 disparos históricos quando o ID oficial puder ser reconhecido
  → Google Sheets: atualiza ou insere campanha pela chave única
  → GitHub: salva dados agregados no JSON público usando PAT restrito
  → GitHub Pages: mostra os indicadores atualizados
~~~

**Arquivos:** scripts/sync_umclique.py, tests/test_sync_umclique.py, .github/workflows/sync-umclique.yml e data/disparos.json.

**Regras:** campanhas são identificadas por ID oficial, os totais são absolutos (nunca incrementos de eventos), e a rotina não duplica campanhas ao reprocessar. Campanhas históricas sem correspondência confiável são colocadas em revisão, não copiadas duas vezes. Telefones, mensagens, contatos e credenciais nunca devem chegar ao repositório público. Dados não apurados não são zero.

## Ativação — 3 credenciais, validação do canal e um teste

### 1. Chave da API UmClique

Acessar a UmClique com permissão de administrador, abrir **Configurações → API & Webhooks** e gerar uma chave de API (prefixo umk_). **Não compartilhar em mensagens, commits ou prints.**

No repositório, acessar [Settings → Secrets and variables → Actions](https://github.com/yWez/DisparoWpp/settings/secrets/actions) e cadastrar o Secret chamado **UMCLIQUE_API_KEY** com a chave privada.

### 2. Descoberta dos canais (automática)

O sistema identifica os dois canais Meta usados nos sete disparos históricos ("Disparo 1 - Wes" até "Disparo 7 - Wes"), conferindo nomes, datas, total de contatos e unicidade dos IDs.

Não é preciso cadastrar um identificador manualmente. Para testar a descoberta:

1. Abra [Actions → Descobrir canal UmClique](https://github.com/yWez/DisparoWpp/actions/workflows/descobrir-canal.yml).
2. Clique em Run workflow, mantendo a branch main.
3. Verifique no Summary o número de canais identificados, sem exibição de chaves.

Se a descoberta se tornar impossível (por exemplo, se a UmClique excluir campanhas históricas), a variável opcional **UMCLIQUE_CHANNEL_IDS** poderá ser usada para indicar os canais autorizados, separados por vírgula. Não precisa ser criada agora.

### 3. Acesso ao Google Sheets

- Abrir https://console.cloud.google.com/ e escolher/criar um projeto.
- Habilitar a **Google Sheets API**.
- Criar uma **Service Account** e uma chave JSON.
- No JSON, copiar o endereço de **client_email** (não é o token).
- Compartilhar a planilha https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit com esse e-mail como **Editor**.
- No GitHub Actions Secrets, criar **GOOGLE_SERVICE_ACCOUNT_JSON** contendo todo o JSON de credenciais. Não adicionar ao repositório.

### 4. Autorização para publicar no GitHub Pages

O token padrão do Actions pode não disparar uma reconstrução do GitHub Pages ao fazer um commit. Para garantir a atualização da página, criar um **Fine-grained Personal Access Token**, restrito **somente** ao repositório yWez/DisparoWpp, com permissão **Contents: Read and write**.

Adicionar esse token em **Actions Secrets** como **GH_PAGES_PUSH_TOKEN**.

### 5. Ativar e testar

Só depois de concluir os itens anteriores:

1. Criar a **Actions Variable UMCLIQUE_SYNC_ENABLED** com o valor exato **true**.
2. Abrir [Actions → Sincronizar disparos UmClique](https://github.com/yWez/DisparoWpp/actions/workflows/sync-umclique.yml).
3. Clicar em **Run workflow**.
4. Conferir o resultado do run e o resumo (campanhas consultadas/atualizadas).
5. Conferir a aba **Disparos WhatsApp** e o campo ID UmClique.
6. Verificar o arquivo data/disparos.json e a página https://ywez.github.io/DisparoWpp/.
7. Executar novamente para confirmar que não duplica campanhas.
8. Fazer um disparo de teste autorizado e observar os resultados nas rodadas seguintes.

Depois disso, o GitHub executará o fluxo a cada ~15 minutos sem precisar abrir o ChatGPT. O agendamento pode atrasar; os dados também dependem de quando a UmClique atualiza os indicadores.

## Proteção da base existente

- As sete campanhas fotografadas estão nas linhas **5–11**.
- A linha **24** contém o total e deve permanecer preservada.
- Novos disparos entram em linhas livres a partir da 12, pulando a 24.
- ID do disparo fica na coluna **M**; entregues/lidos/responderam nas colunas **P–R**.
- O Google Sheets é editado com conta de serviço, não por chave de API pública.
- A planilha não deve ser compartilhada publicamente apenas para o painel funcionar.
- Os primeiros sete IDs ainda precisam ser conciliados; se houver inconsistência, a integração pausa com erro explícito, em vez de produzir total inflado.

## Status verificado neste projeto

- ✅ Endpoints e resposta da API documentados.
- ✅ Script de integração e testes versionados.
- ✅ Workflow agendado versionado e desativado por variável de segurança.
- ✅ Planilha com colunas de API; dashboard pronto para novos indicadores.
- ⏳ Chave UmClique já armazenada no GitHub pelo usuário; ainda faltam acesso Google Sheets e token GitHub de publicação. Os canais são descobertos automaticamente.
- ✅ A primeira consulta autenticada de canais foi realizada pela rotina de descoberta. ⏳ A sincronização completa com Sheets e Pages ainda não foi ativada.

**Nunca envie senhas, tokens ou o JSON da conta de serviço nesta conversa.**
