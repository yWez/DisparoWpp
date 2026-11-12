# Acompanhamento de Mensageria — LP Crypto

**Página:** https://ywez.github.io/DisparoWpp/mensageria.html  
**Base preservada:** o DisparoWpp continua em index.html, sem retirar dashboards de campanhas e atribuição X1.

## Dados reais e atribuição

A conta autenticada da UmClique fornece:
- GET /functions/v1/public-conversations: conversas paginadas, com identificador, canal, contact_id, assigned_agent_id, updated_at e status;
- GET /functions/v1/public-conversations/messages: mensagens paginadas, is_from_me, id, timestamp e conversation_id;
- GET /functions/v1/public-agents: todos os responsáveis cadastrados.

A regra solicitada é: **responsável pelo lead = assigned_agent_id ATUAL da conversa**. Não confundir com sender_agent_id, que pode identificar quem enviou uma mensagem individual. Conversas sem responsável são mantidas em **Não atribuído**. Todos os agentes cadastrados aparecem mesmo quando não há movimentação.

## Canais e escopo

A UmClique retornou seis canais de conversas da conta empresarial, enquanto os dois canais Meta de disparos usam identificadores de outro namespace. Portanto **não relacionar esses IDs arbitrariamente**. A mensageria considera os canais WhatsApp da conta empresarial autenticada (whatsapp_oficial, uazapi, meta, wapi) e apresenta um nome de canal sem telefone/PII.

## Armazenamento seguro

O fluxo adiciona a coleta ao mesmo GitHub Actions agendado (agendado a cada 5 minutos, com atraso possível no GitHub Actions), preservando a sincronização existente de disparos e a conciliação X1.

Uma aba privada do Google Sheets chamada **Mensageria Estado** guarda somente identificadores técnicos de conversas, HMAC do identificador do contato, IDs de canal/responsável, datas e contagens por dia. Sem nome ou telefone de lead, sem mensagem individual. Uma aba visível **Mensageria - Resumo** mostra indicadores agregados por responsável.

O arquivo público data/mensageria.json guarda apenas informações agregadas por período, canal e atendente, sem mensagens, telefones, IDs de contato, nomes de clientes ou tokens.

No primeiro carregamento, são processadas até **120 conversas por execução**; a coleta continua nas execuções seguintes. Até concluir, o site sinaliza cobertura parcial e apresenta os números processados como limites inferiores, não como total definitivo.

Mensagens são deduplicadas pelo identificador e a consulta incremental substitui os valores de cada conversa; não acumula eventos em duplicidade.

## Indicadores e regras

- Mensagens recebidas: is_from_me = false.
- Mensagens enviadas: is_from_me = true.
- Contatos que escreveram: IDs distintos com mensagem recebida, deduplicados no armazenamento privado.
- Conversas movimentadas: conversas distintas com mensagens no período.
- Conversas iniciadas pelo contato: primeira mensagem observada foi recebida; não comprova demanda orgânica.
- Última mensagem recebida: conversa ativa cuja última mensagem foi do cliente, indicador operacional e não diagnóstico automático de atraso.
- Não lidas: unread_count atual, disponível na visão de todo o histórico.
- Filtros: hoje, ontem, 7 dias, 30 dias, todo histórico, personalizado, responsável e canal.
- As janelas pré-definidas permitem calcular contatos únicos de forma exata entre as conversas inspecionadas. O intervalo personalizado NÃO soma contatos-dia como se fossem pessoas únicas: exibe Não disponível para essa métrica.
- Os números por responsável refletem a **carteira atual**, mesmo quando as mensagens são antigas.
- Uma mensagem enviada nas conversas pode ter sido um template disparado; não somar diretamente as métricas de saída com o dashboard de campanhas.
- Datas convertidas para America/Fortaleza.

## Limites e segurança

O site GitHub Pages é público e expõe somente agregados por responsáveis e canais. Não apresenta conteúdo de chats, telefones ou dados nominais de clientes. Para auditoria individual de produtividade, reclamações e reenvios, seria necessário controle de acesso e um projeto específico. Nenhuma mensagem é enviada ou reenviada pelo coletor.

Se a coleta da mensageria falhar, a atualização de campanhas permanece ativa. Os dados atuais permanecem com a data da última sincronização bem-sucedida.

## Testes

- Python unittest de privacidade, paginação, direções de mensagens, datas, deduplicação e responsáveis.
- JavaScript Node de períodos, filtros, contagens, ordenação e indisponibilidade em período personalizado.
- GitHub Actions CI e execução piloto autenticada, sem salvar conteúdo individual nos logs.
- Verificação no navegador após publicar a segunda aba.

> **Cadência atual (12/11/2026):** a sincronização está programada para os minutos 02, 07, 12, 17 etc. do relógio UTC, a cada 5 minutos. O GitHub Actions pode iniciar com atraso ou até omitir uma execução. O painel informa a hora **real** da última coleta e avisa quando ela está desatualizada; a página consulta o JSON publicado a cada minuto quando aberta. Sem garantia de atualização instantânea. O layout de mensageria foi ajustado para que tabelas e indicadores não ultrapassem o card nem no celular.
