# X1 — Captação, entrada confirmada no grupo e atribuição aos disparos

## O que o dashboard mede

O painel de X1 agora apresenta **três etapas diferentes**, sem confundir eventos:

1. **Cadastro na LP X1:** originado da planilha `Captação` da fonte
   `1AtxjojmOi3aAFk1gSc1O7Su4pQUSrgsndnNGZkkMU7U`. Filtra
   `utm_source=whatsapp` e `utm_medium=x1`.
   Usa `criado_em` (A), `whatsapp` (D), `utm_source..utm_content` (H:K).
   O mesmo telefone conta **uma vez**, na **primeira inscrição cronológica**
   válida, independentemente da ordem das linhas. Datas no fuso
   `America/Fortaleza`. Linhas sem telefone ficam como inscrições com
   identificação incompleta — não são tratadas como pessoas distintas
   comprovadas.
2. **Entrada confirmada no grupo:** exige evidência real de participação e
   correspondência do telefone a um cadastro X1. Essa fonte **não está**
   disponível por padrão na aba de captação; abrir uma página ou clicar no
   convite não comprova que alguém entrou. Se não existir nenhum evento
   verificado, o dashboard exibe **Não disponível**, e não zero.
3. **Cadastro atribuído ao disparo:** somente com identificador oficial
   **exato** da campanha na UTM `utm_campaign` ou `utm_content`, ou
   `x1-<id>` / `disparo-<id>` (para IDs oficiais da UmClique).
   A UTM `x1-base` é compartilhada, logo **não permite atribuição por disparo**.
   Nenhuma campanha recebe cadastros presumidos.

Os totais do X1 representam a **fonte X1 completa**, e não somente os disparos
selecionados no filtro do dashboard. O filtro altera a tabela de campanhas.
Não se presume que inscrição, grupo, leitura e resposta sejam uma sequência
obrigatória; não calcular taxa cruzada sem IDs relacionados.

## Conciliação rápida de integrantes X1 (listas privadas)

**Conferência direta (13/11/2026):** a conta UmClique do canal Aline
disponibiliza os grupos e suas contagens, mas a integração conectada
**não oferece a relação individual de telefones dos membros**. Não é
possível contabilizar entradas a partir de `participants_count`.

Existem duas abas de importação privadas na planilha operacional:

- **Membros X1 - Mesa 22** — grupo da Mesa da Luisa 22/11
- **Membros X1 - Mesa 17-19-22** — grupo da Mesa da Luisa 17/19/22

As abas estão preparadas com os campos B1:B5, instruções e validação do
campo B3. Não reutilizar a aba `Entradas Grupo X1` para snapshots de
participantes: **presença atual ≠ data de entrada**.

### Uso do lote de participantes (administrador autorizado)

1. Obter uma lista completa e autorizada de membros reais do respectivo
   grupo, pelo administrador ou fornecedor que opere o canal. Não utilizar
   listas compradas, invasões, extensões de raspagem ou contato sem consentimento.
2. Colar na coluna **A8:A**, um telefone por linha, sem nomes, e conferir
   que é a lista do grupo correto. Pode colar centenas de linhas de uma vez.
3. Preencher **B2** com data/hora da conferência no fuso local
   (ex.: `2026-11-13 19:30:00`). Confirmar o ID do grupo em **B1**.
4. Manter **B4** em `lista_participantes` ou `exportacao_grupo`, de
   acordo com a origem da comprovação.
5. **Somente depois de verificar toda a lista**, alterar **B3** de
   `PENDENTE` para `LISTA_VERIFICADA`.

O sincronizador rápido, acionado pelo agendador a cada 5 minutos,
passará a relacionar esses membros com os cadastros X1 na aba
`Captação`. Ele normaliza telefones brasileiros, deduplica pessoas
presentes em mais de um grupo, e registra apenas totais agregados no
dashboard público. Falhas da leitura, lista vazia ou `PENDENTE`
significam **Não disponível**, nunca zero.

O dashboard separa:
- **Cadastros X1 presentes nos grupos**: telefones cadastrados na página
  e encontrados nas listas privadas conferidas. Não indica quando a
  pessoa ingressou no grupo; captura a presença no instante da auditoria.
- **Entradas confirmadas no grupo**: apenas eventos efetivos de entrada
  associados ao telefone, com data verdadeira na aba `Entradas Grupo X1`.
  Uma lista de participantes não é suficiente para preencher essa etapa.

### Caminho para uma fonte 100% automática

Pedir à UmClique, ou ao administrador da instância UAZAPI, uma destas
fontes oficiais e autorizadas:
- consulta autenticada de **membros de grupo** (telefone ou identidade
  correlacionável), com grupo ID e data da consulta; ou
- webhook autenticado de **entrada/saída de participante**, com grupo ID,
  identificador de membro, instante do evento e proteção contra duplicações.

Webhooks UAZAPI podem emitir o evento `groups`, mas a lista detalhada
de membros não está disponível pela conexão UmClique atual. Antes de
ativar qualquer endpoint, validar autenticação, escopo, contrato real
do payload, consentimento e armazenamento privado. Nunca expor tokens,
telefones, nomes ou logs brutos em GitHub/GitHub Pages.

Se for obtida uma lista inicial, ela alimenta **presença conferida**;
eventos futuros autorizados alimentam **novas entradas reais**.

**Segurança e LGPD:** acesso privado apenas à equipe necessária,
objetivo de mensuração de campanha claramente comunicado, retenção
mínima proporcional e nenhuma exportação pública de telefones.

## Nova fonte de comprovação de grupo

Foi criada uma aba privada **Entradas Grupo X1** na planilha operacional
https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit

Colunas (A:F):
- `data_entrada_confirmada`: data/hora em que a participação foi verificada,
  de preferência ISO 8601 `2026-11-13 18:45:00`;
- `whatsapp`: telefone do participante, mantido **somente no Sheets privado**;
- `grupo_id`: identificador do grupo para validação; obrigatório;
- `evidencia`: uma das opções `lista_participantes`,
  `evento_entrada`, `webhook_participante`,
  `verificacao_manual` ou `exportacao_grupo`;
- `status`: `pendente` ou `confirmado`. Só usar confirmado após uma checagem
  real de que a pessoa ingressou no grupo. Clique em convite, visita ou
  mensagem sem confirmação não basta.
- `campanha_id`: campo auxiliar opcional para auditoria; **não** substitui
  a atribuição comprovada pela UTM da página.

Quando uma linha está marcada como `confirmado`, possui evidência aceita,
grupo, data e um telefone que consta na `Captação` X1, ela alimenta
a contagem de **leads X1 participantes confirmados**, sem duplicar pessoas
que aparecem em várias listas/grupos.

**Importante:** as ferramentas conectadas da UmClique permitem consultar
grupos de canais QR Code, mas não forneceram uma fonte confirmada que relacione
cada ingresso a um cadastro X1. A nova aba poderá ser abastecida por auditoria
autorizada de membros ou, futuramente, por webhook com evento de participação.
O sistema não consulta nem envia mensagens em grupos e não modifica grupos.

## Preparar campanhas futuras com UTM rastreável

O disparo deve utilizar um link da **página de captura oficial**, com UTM
única da campanha, por exemplo:

```text
utm_source=whatsapp
utm_medium=x1
utm_campaign=<ID-oficial-do-disparo>
utm_content=x1-<ID-oficial-do-disparo>
```

Se a campanha for um rascunho na UmClique, obter primeiro o ID oficial,
incorporar o identificador no link **antes** de iniciar a transmissão e
preservá-lo na navegação até a planilha `Captação`.

**Não** publicar um domínio ou URL de página inventado. O marcador de
campanha deve ser definido no fluxo de distribuição dos links; campanhas
históricas com apenas `x1-base` permanecem corretamente não atribuídas,
até existir outra fonte documental que comprove relação individual.

## Atualização e confiabilidade

- `scripts/sync_x1.py` consulta a aba `Captação` e tenta consultar
  `Entradas Grupo X1` com a conta de serviço já autorizada.
- `data/x1-attribution.json` recebe apenas contagens agregadas, sem
  telefones, nomes ou IDs nominais.
- O campo `meta.lastCheckedAt` é atualizado após **cada consulta válida**,
  mesmo se os totais não mudarem. Se a leitura falhar, mantém o dado anterior,
  com o horário anterior para diagnosticar falhas.
- O agendador externo solicita campanhas e X1 pelo fluxo rápido a cada 5 minutos; filas ou erros podem causar atrasos. O fluxo de mensageria é independente e solicitado a cada 15 minutos.
- O dashboard mostra a última leitura válida, status de grupo, cadastros
  originais, duplicatas e cobertura de atribuição.
- A exportação pública **X1** contém somente agregados.
- Se a fonte de grupo estiver vazia ou sem comprovação válida, **não**
  apresentar entradas como zero nem inventar taxa de entrada.

## Testes

- `python -m unittest discover -s tests -p 'test_*.py' -v`:
  ordenação cronológica fora de ordem, fuso Fortaleza, duplicados, telefone
  ausente, UTMs genéricas/conflitantes e provas de grupo válidas.
- `node --check assets/dashboard-v2.js`
- Verificar no Actions `Sincronizar disparos UmClique` e conferir
  `data/x1-attribution.json` após execução.

A operação comercial deverá preencher os eventos comprovados do grupo ou
conectar uma fonte de ingresso verificável. Não há número real de entradas
no grupo enquanto isso não acontecer.
