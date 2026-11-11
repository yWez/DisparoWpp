
# LP Crypto • DisparoWpp v2 — Inteligência comercial

O projeto **evolui o dashboard atual**, mantendo GitHub Pages, API da UmClique, Google Sheets e GitHub Actions existente. O site público continua lendo `data/disparos.json`. Fonte oficial: https://connect.umcliquedigital.com/docs/api#description/introduction

## O que foi implementado

- Filtros globais de hoje, ontem, 7 dias, 30 dias, intervalo personalizado, ID de campanha, ID de canal, status presente na campanha e origem atribuída.
- KPIs de envio, entrega, leitura, resposta, falha; taxas de entrega/leitura/falha; respostas por pessoa e leads únicos identificados como **não disponíveis**.
- Séries temporais dos volumes/taxas por data de início da campanha, click-to-filter e tabela diária.
- Comparação dos canais Meta por IDs, aliases e status de conexão (se retornado pela API); classificação por limiares operacionais ajustáveis.
- Ranking de campanhas com ordenação por indicador, pesquisa e alertas de qualidade configuráveis.
- Erros agrupados **por código real da UmClique**, título, descrição técnica, contagem, tipo e recomendação de revisão; CSV apenas agregado.
- Origem por campanha via `data/origins.json` (sem inventar origens individuais), funil futuro via `data/funnel.json`.
- Exportação CSV geral, campanhas, dias, canais, falhas agregadas, respostas agregadas e funil; UTF-8 BOM, delimitador Excel e neutralização de células que poderiam virar fórmulas.
- Interface responsiva e data da última atualização da base, com estados de carregamento/erro.

## Fontes, escopo e fórmulas

- Taxa de entrega = entregues ÷ enviadas. Taxa de leitura = lidas ÷ entregues. Taxa de falha = falhas ÷ enviadas. São **agregados por campanha**, calculados somente quando numerador e denominador estiverem disponíveis.
- **Taxa de resposta por pessoas únicas: N/D.** O endpoint de métricas oferece contagem de respostas por campanha; sem deduplicar pessoas entregues e respondentes entre campanhas, não é honesto chamar `respostas / entregues` de taxa de pessoas únicas. Uma proporção agregada é identificada separadamente como *proxy*.
- **Leads únicos: N/D**. `total_contacts` de vários disparos não representa pessoas distintas.
- **Filtro de status** seleciona campanhas que possuem mensagens naquele status. Sem registros individuais, os demais KPIs permanecem os totais dessas campanhas, não de um subconjunto arbitrário de destinatários.
- **Dia** significa a data de início do disparo em `America/Fortaleza`, não a data exata do evento de leitura/entrega/resposta. Eventos por dia exigiriam logs temporais individuais.
- Se a API informar uma campanha com múltiplos canais, seus contadores não são atribuídos integralmente a cada canal. É necessário rateio autorizado por métricas específicas.
- Ausência de métrica, fonte ou denominador não equivale a zero. Funil e origens não têm dados fictícios.

## Diagnóstico de erros e proteção de contato

O endpoint `GET /functions/v1/public-broadcasts/{id}/errors` devolve `groups` por código, com título, explicação, ação e quantidade. `scripts/enrichment.py` exclui `sample` (telefones parcialmente ocultos), `raw_examples`, nomes, logs e conteúdos individuais antes de publicar JSON. A classificação de recuperabilidade é **conservadora** e não autoriza reenvio.

Os endpoints privados de destinatários/logs poderão permitir uma exportação **restrita**, com nome, telefone, status, motivo e data, somente depois de configurar um destino privado, permissão adequada e mapeamento validado. A página pública não disponibiliza CSV nominal nem inicia reenvios.

## Atribuição e funil

`data/origins.json` contém `campaignOrigins` indexado por ID oficial. Um contato pode participar de várias campanhas; primeira origem imutável, multi-touch e deduplicação de pessoas dependerão de CRM/captação em ambiente restrito.

`data/funnel.json` contém `registrations`, `groupJoins`, `liveAttendees`, `purchases` como `count:null`, `verified:false` e `source:null`. São necessárias as integrações e identidades da captura, grupos, live, checkout e CRM. **Não** calcular conversão sequencial entre populações não relacionadas.

Conversões da UmClique não substituem a conciliação de venda paga.

## Automações preservadas

- Listagem: `GET /functions/v1/public-broadcasts` com paginação e canais Meta autorizados.
- Métricas: `GET /functions/v1/public-broadcasts/{id}/metrics`.
- **Novos enriquecimentos (somente agregados):** `/functions/v1/public-broadcasts/{id}/errors` e `/functions/v1/public-channels`.
- Fluxo existente: UmClique → `scripts/sync_umclique.py` → Google Sheets → `data/disparos.json` → GitHub Pages.
- GitHub Actions continua agendado de 15 em 15 minutos, com retries limitados. Segredos somente em GitHub Secrets; `UMCLIQUE_SYNC_ENABLED=false` interrompe as próximas execuções agendadas.

## Testes

CI: `python -m unittest discover -s tests -p "test_*.py" -v`, `node --check assets/model.js assets/dashboard-v2.js` e `node tests/test_dashboard.cjs`.

Casos: taxas e denominadores, métricas faltantes, datas/fuso, filtros, origem ausente, canais, deduplicação por ID, erros por grupo, saneamento de exemplos pessoais, CSV e sintaxe.

Os dados mostrados no painel vêm da API real. **Exemplos sintéticos existem exclusivamente nos testes.**

## Pendências dependentes de integração

1. Consultar `/errors` autenticado no primeiro run da nova versão e conferir grupos/códigos.
2. Obter contatos entregues/respondentes únicos e relação entre campanhas em ambiente autenticado.
3. Criar área de acesso restrito para lista nominal e exportações de recuperação (sem reenvio automático).
4. Integrar formulário/CRM, entrada no grupo, live e checkout com IDs conciliáveis.
5. Confirmar limites de envio e estado de conexão para cada canal, caso a API disponibilize dados.
