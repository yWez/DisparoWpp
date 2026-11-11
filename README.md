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
