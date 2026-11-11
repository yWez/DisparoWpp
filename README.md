# LP Crypto · Disparos WhatsApp

Painel de acompanhamento das campanhas de WhatsApp, criado para acesso rápido da Ana e do time comercial.

## Visualização

- **Página pública ativa e verificada em 11/11/2026:** https://ywez.github.io/DisparoWpp/
- Fonte operacional: [Planilha LP Crypto – Disparos WhatsApp](https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit)
- Indicadores públicos agregados: `data/disparos.json`

**Privacidade:** este repositório é público. Não adicionar números de WhatsApp, nomes de contatos, respostas individuais, listas de clientes, credenciais ou links privados com tokens. O painel só apresenta contagens agregadas de campanhas.

## Como funciona

A página `index.html` carrega o arquivo `data/disparos.json` e calcula automaticamente totais, taxa de falhas, ranking e comparações. Os registros individuais são por **campanha**, e não por contato.

As contagens foram extraídas do print da plataforma e conferidas com a aba `Disparos WhatsApp` do Google Sheets. **Status "Concluída" não comprova entrega, leitura ou resposta.** "Sem falha registrada" não deve ser apresentado como "entregues". Os rótulos de tempo relativos no print não estabelecem horários exatos por dia.

## Integração UmClique (ativa por agendamento)

O guia de ativação da integração automática está em **[docs/CONFIGURAR_AUTOMACAO.md](docs/CONFIGURAR_AUTOMACAO.md)**.

**Status (11/11/2026):** a primeira sincronização completa foi executada com sucesso; a planilha e a página foram conferidas com 8 campanhas distintas, 902 envios e 107 falhas. O GitHub Actions foi habilitado para executar a cada 15 minutos (execuções podem sofrer atraso pela plataforma). A descoberta dos dois canais Meta é automática e os Secrets já foram cadastrados pelo administrador. Para pausar as execuções agendadas, defina a variável de repositório `UMCLIQUE_SYNC_ENABLED` como `false`.

## Inteligência comercial v2

A mesma página e as mesmas integrações foram evoluídas, sem recriar o projeto.

- **Filtros globais:** período, campanha, canal Meta, status presente e origem declarada.
- **KPIs auditáveis:** enviados, entregues, lidos, respostas e falhas, taxas com denominadores claros. Pessoas únicas e resposta por contatos únicos mostram `Não disponível` até integração de identidades.
- **Análises:** séries diárias, comparativo por canal, ranking de campanhas, erros agrupados por código real, segmentos por origem e estrutura do funil.
- **Exportações:** CSV com dados agregados e filtros aplicados. Relatórios nominais/telefones nunca são publicados no GitHub Pages.
- **Integração preservada:** a consulta a UmClique, atualização no Google Sheets, GitHub Actions e GitHub Pages seguem operando. O enriquecimento `/errors` e `/public-channels` é opcional e tolera indisponibilidade temporária.

**Detalhes de métricas, privacidade, limitações e testes:** [docs/INTELIGENCIA_COMERCIAL_V2.md](docs/INTELIGENCIA_COMERCIAL_V2.md).

## Captação X1 e desempenho por copy (11/11/2026)

A nova seção **Conversões X1** utiliza a aba Captação do arquivo LP Crypto Black 2026 com filtro estrito utm_source=whatsapp e utm_medium=x1. Não mistura criativos pagos cujo nome contém X1. O primeiro cruzamento conferido encontrou **42 cadastros únicos**, com **42 telefones distintos**, todos identificados com utm_content=x1-base. Esses cadastros **não provam entrada no grupo**, que continua N/D até receber dados de participação.

**Atribuição histórica por disparo: não disponível.** O valor compartilhado x1-base não identifica qual broadcast levou à inscrição; a página mostra isso claramente, sem ratear os 42 leads entre os 8 disparos. Para atribuição futura, cada campanha deve usar UTM exclusiva, por exemplo utm_content=x1-<8 primeiros caracteres do ID oficial da transmissão>, ou integrar logs privados de destinatários por telefone + horário. Nunca incorporar telefones em UTMs ou URLs.

A nova seção **Performance por copy** agrupa pelo campo Template (parcial) da aba Disparos WhatsApp, computando envios, entregas, leituras, respostas, taxa de leitura e respostas/entregues (proxy). Só indica uma copy vencedora quando houver ao menos 2 modelos distintos e base mínima de 30 entregas. Na primeira análise, os 8 disparos usaram **apenas um template**, convite_evento_base_quente_mkt; portanto ainda não é possível afirmar qual copy é melhor que outra.

**Atualização automática:** scripts/sync_x1.py lê somente colunas A, D e H:K da Captação por uma conta de serviço já prevista no workflow, deduplica em memória e publica exclusivamente contagens em data/x1-attribution.json. O mesmo agendamento GitHub Actions da UmClique tenta atualizar esses agregados a cada 15 minutos e publica o site quando os dados mudarem. Para isso, a conta de serviço cadastrada no Secret GOOGLE_SERVICE_ACCOUNT_JSON precisa ter permissão de leitura na **planilha de Captação**, além da planilha operacional. Se não tiver, a sincronização da UmClique segue normalmente, mas a fotografia inicial de X1 permanece até liberar acesso. Consulte a execução em Actions antes de considerar a atualização da Captação validada.

## Atualização dos dados

A fonte oficial é a API da UmClique. O workflow `.github/workflows/sync-umclique.yml` consulta campanhas dos dois canais Meta e atualiza a aba **Disparos WhatsApp** da planilha e `data/disparos.json`, ambos por ID de campanha (sem somar eventos repetidos). A página lê o JSON e exibe a última sincronização.

- **Rotina automática:** a cada 15 minutos, sujeita à fila e disponibilidade do GitHub.
- **Teste manual:** [Actions → Sincronizar disparos UmClique](https://github.com/yWez/DisparoWpp/actions/workflows/sync-umclique.yml).
- **Pausa de emergência:** em Settings → Secrets and variables → Actions → Variables, criar/editar `UMCLIQUE_SYNC_ENABLED` para `false`.
- **Dados históricos:** Disparos 1–7 reconciliados; Disparo 4 duplicado foi corrigido e o nome agora é normalizado. Disparo 8 entrou pela API.
- **Atenção:** alterações manuais somente no Google Sheets **não** retornam automaticamente para a UmClique ou para o JSON; o sincronizador parte da UmClique.
- **Privacidade:** nada de contatos individuais, telefones, tokens ou conteúdos de mensagens no repositório.

## Publicação da página

✅ O GitHub Pages está ativo no endereço https://ywez.github.io/DisparoWpp/ (abertura e dados verificados em navegador público em 11/11/2026).

Configuração: `Settings → Pages` → `Deploy from a branch` → `main` → `/(root)`.

O arquivo `index.html` já é publicado no site por essa configuração. Os dados são lidos de `data/disparos.json`; atualizações nesse arquivo exigem novo commit para refletir no site.

## Estrutura

- `index.html`: painel web responsivo
- `data/disparos.json`: base agregada de campanhas para o site
- `README.md`: instruções e regras de atualização

Criado a partir dos registros de 9–10/11/2026, com conferência em 11/11/2026.
