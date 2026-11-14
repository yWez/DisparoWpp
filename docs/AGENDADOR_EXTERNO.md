# LP Crypto — atualização confiável sem depender do cron do GitHub

## Diagnóstico realizado em 13/11/2026

A API autenticada da UmClique retornou **20 transmissões** desde 09/11/2026.
O dashboard antigo só armazenava **9**, porque restringia a consulta a
dois canais históricos da Meta. Na conta há campanhas Meta e UAZAPI/QR Code,
além de outras transmissões que não pertenciam aos dois canais iniciais.

A sincronização GitHub Actions agendada a cada cinco minutos não executava
com essa frequência: houve intervalos de **horas** entre os jobs. O GitHub
documenta atrasos e possíveis descartes de execuções agendadas. Não devemos
usar o cron do GitHub como único mecanismo para monitoramento comercial.

## Arquitetura corrigida

1. `scripts/sync_umclique.py` consulta **todas as campanhas da conta**
   autenticada (sem limitar por provedor/canal histórico). Identifica Meta,
   UAZAPI/QR Code ou provedor não identificado, sem fabricar contadores.
2. `.github/workflows/sync-campaigns-fast.yml` executa apenas campanhas,
   Google Sheets e publicação agregada, sem reler milhares de mensagens.
   Tem cron GitHub de 5 minutos **somente como fallback**.
3. `.github/workflows/sync-umclique.yml` atualiza apenas mensageria, e usa
   agendamento interno a cada 30 minutos como fallback.
4. **Agendador externo Google Apps Script** (arquivo
   [`ops/agendador-externo-apps-script.gs`](../ops/agendador-externo-apps-script.gs))
   aciona o workflow de campanhas e X1 a cada 5 minutos e o de mensageria a cada 15 minutos
   através da API do GitHub. O agendador fica fora do GitHub; atrasos no cron
   interno não impedem os pedidos externos. O GitHub ainda pode ter filas
   e falhas: disparo aceito não significa sincronização concluída.
5. Os workflows usam o mesmo grupo de concorrência para evitar alterações
   concorrentes na planilha/JSON; o commit continua sem `force push`.

## Instalação do agendador externo — ação de administrador necessária

**Uma única vez, com a conta Google da operação.** Não precisa ativar
faturamento no Google Cloud, nem cadastrar a chave da UmClique fora do
GitHub: somente a permissão para acionar workflows.

1. No GitHub, crie um token **fine-grained** em
   https://github.com/settings/personal-access-tokens/new.
   Selecione **Resource owner: yWez**; **Only select repositories: DisparoWpp**;
   em Repository permissions habilite **Actions: Read and write**.
   Defina expiração e anote quando precisará renovar.
   **Nunca envie esse token pelo chat nem publique em código.**
2. Entre em https://script.google.com/home/projects/create para criar
   um projeto **standalone e privado** chamado `LP Crypto - Agendador`.
   Não faça script vinculado à planilha compartilhada, para evitar expor
   propriedades secretas a editores externos.
3. Copie integralmente o conteúdo de
   [agendador-externo-apps-script.gs](../ops/agendador-externo-apps-script.gs)
   para o arquivo `Código.gs`, substituindo o exemplo inicial. Salve.
4. No editor do Apps Script, abra **Configurações do projeto → Propriedades
   do script → Adicionar propriedade**. Nome: `GITHUB_ACTIONS_TOKEN`.
   Valor: token fine-grained do passo 1. Salve. O segredo **não** deve aparecer
   no código nem nos logs.
5. No seletor de funções, escolha `instalarAgendadorLP` e clique em
   **Executar**, aceitando as permissões necessárias para UrlFetchApp e
   gatilhos temporizados. A instalação primeiro testa duas requisições;
   só cria os gatilhos se o GitHub responder HTTP **204**.
6. Execute `statusAgendadorLP` e confira em **Execuções** que há gatilhos
   ativos para CAMPANHAS (5 min, incluindo X1) e MENSAGERIA_X1 (15 min, nome histórico do gatilho de mensageria).
7. Confira o resultado final dos workflows, não apenas o disparo, em:
   - https://github.com/yWez/DisparoWpp/actions/workflows/sync-campaigns-fast.yml
   - https://github.com/yWez/DisparoWpp/actions/workflows/sync-umclique.yml

### Operação

- O script armazena apenas o token no Script Properties, e as datas/HTTP
  de requisição aceitas. Nunca guarda mensagens, leads ou telefones.
- `statusAgendadorLP()`: retorna datas e eventuais erros sem revelar token.
- `desativarAgendadorLP()`: remove somente os gatilhos dessa operação.
- Token expirado ou revogado: configurar novo valor de
  `GITHUB_ACTIONS_TOKEN`; o campo `LAST_ERROR_CAMPANHAS` mostrará
  o status HTTP sem expor o segredo.
- Se o GitHub responder HTTP 204, significa que **aceitou** o pedido;
  a conclusão deve ser verificada na aba Actions.
- Fila do GitHub, latência da UmClique, paginação, atualização do Google Sheets
  e publicação do GitHub Pages ainda adicionam tempo. **Não há SLA
  garantido de cinco minutos**.
- Um heartbeat periódico confirma a consulta sem reescrever o site a
  cada cinco minutos quando não há alterações nos dados.
- Caso a campanha não esteja na UmClique, o código não inventará sua
  presença: investigar a conta/provedor e a data do envio.

## Monitoramento e escalonamento

- Verificar `data/disparos.json > meta.lastSyncedAt` e não confundir
  arquivo atualizado com evento de envio recebido em tempo real.
- Quando a hora de atualização ultrapassar 15–20 minutos:
  conferir primeiro os dois workflows acima, depois o relatório
  `statusAgendadorLP()`, e por fim a API da UmClique.
- Se houver necessidade de **SLA contratual real** com tolerância a falha
  de região, recomenda-se Cloud Run/Cloud Scheduler + armazenamento gerenciado,
  com faturamento e alertas de incidentes. Apps Script resolve o problema
  atual de depender exclusivamente do cron do GitHub, mas não equivale
  a infraestrutura de alta disponibilidade.
