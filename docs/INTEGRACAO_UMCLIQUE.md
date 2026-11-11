# Plano de integração — UmClique → Google Sheets → DisparoWpp

**Projeto:** LP Crypto · Operação comercial de Black Friday 2026  
**Estado:** estrutura preparada; integração com a conta UmClique ainda **não conectada**.  
**Responsável pela ativação:** operação técnica + responsável com permissão de administrador na UmClique.

## 1. O que foi verificado

- A umClique divulga analytics de **enviados, entregues, lidos e falhas por campanha**.
- A empresa descreve integrações via webhook e API REST em páginas públicas.
- **Não foi identificada documentação pública verificável sobre endpoint de relatório por disparo ou webhook específico de conclusão de campanha.** Não presumir que um webhook de atendimento contenha as métricas da ferramenta de disparos.
- Existe a planilha operacional: https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit, aba `Disparos WhatsApp`.
- Existe o site público https://ywez.github.io/DisparoWpp/, que lê `data/disparos.json` desta branch.
- Esta branch e o site são públicos: somente informação **agregada**.

Documentação pública consultada:
- https://umcliquedigital.com.br/um-clique-digital-lp-1/
- https://umcliquedigital.com.br/5-formas-integrar-api-oficial-whatsapp-coex-sistemas-internos/
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/

## 2. Perguntas para o suporte UmClique — pré-requisito técnico

Enviar ao suporte:

1. Nosso plano habilita a API de **listagem de campanhas/disparos em massa** e **consulta dos indicadores de cada campanha**?
2. Existe evento webhook de `disparo/campanha criada`, `iniciada`, `concluída` ou `atualização de relatório`? Quais **nomes exatos**?
3. Quais são URL base, caminhos, método, esquema de autenticação, escopos, paginação e limites de requisições?
4. Qual endpoint devolve, por campanha, **ID imutável, nome, data/hora, total de contatos, enviados, falhas, entregues, lidos, respostas, status e canal**?
5. Qual é um **exemplo real de resposta JSON** de campanha e de um **evento webhook**, com dados pessoais removidos?
6. O webhook traz **campaignId/broadcastId**? Se ele só envia eventos por mensagem, como correlacionar cada mensagem ao disparo?
7. Há assinatura HMAC, segredo verificável, IPs de origem e política de reentregas? Qual é o mecanismo exato?
8. É possível recuperar histórico das campanhas já concluídas e atualizar estatísticas após o término (leituras podem ocorrer depois)?

Sem essas informações **não é seguro especificar endpoints nem mapear eventos como se estivessem confirmados**.

## 3. Arquitetura recomendada (baixo código, com n8n)

```text
UmClique (evento de campanha, SE existir)
   ↓ HTTPS webhook com autenticação/assinatura verificada
n8n (URL de produção)
   ↓ identificar campaign_id e enfileirar atualização
UmClique API REST (endpoint de estatísticas CONFIRMADO PELO SUPORTE)
   ↓ resposta completa por campanha, idealmente reconsultada após 5/30 min
n8n normaliza os campos → valida → remove PII → deduplica por campaign_id
   ├─→ Google Sheets: localizar por ID UmClique e UPDATE / APPEND (nunca somar de novo)
   └─→ GitHub: atualizar data/disparos.json via Contents API
              ↓ GitHub Pages lê JSON atualizado
https://ywez.github.io/DisparoWpp/
```

**Alternativa se não houver webhook de campanha:** `Schedule Trigger` no n8n a cada 5 ou 15 minutos → consultar a API por campanhas alteradas → mesmo restante do fluxo. Se a API não oferecer listagem/relatório de campanhas, confirmar com o suporte a possibilidade de exportação automatizada ou relatório agendado. **Webhook de mensagem sozinho não basta** caso falte o vínculo com a campanha.

### A. Configuração no n8n

1. Criar workflow `LP Crypto · Sincronizar Disparos`.
2. Adicionar **Webhook Trigger** (POST, produção) se o suporte confirmar o evento; habilitar autenticação e validar a assinatura conforme a especificação verdadeira da UmClique. Se não houver evento, usar **Schedule Trigger**.
3. **HTTP Request** com credencial segura da UmClique e endpoint oficial de relatório; não copiar token em um nó público.
4. **Code / Set** para converter a resposta num objeto normalizado (contrato abaixo). Rejeitar `campaign_id` ausente, valores negativos ou falhas superiores a envios. Campos ausentes ficam `null`, não `0`.
5. **Google Sheets**: buscar `ID UmClique` (coluna M) e atualizar a campanha encontrada; se não existir, anexar nova linha **a partir da linha 13**. As linhas 5–11 vieram do print e ainda não têm IDs oficiais. Conferir conciliação da base histórica antes de anexar importações antigas.
6. **GitHub** (via HTTP Request): ler `data/disparos.json`, obter SHA do blob, construir JSON agregado sem PII, fazer `PUT /repos/yWez/DisparoWpp/contents/data/disparos.json` com `content` em base64 e o SHA atual. **Não sobrescrever o JSON apenas com a campanha do webhook.** Preservar as demais.
7. Configurar retry/log de erros, aviso à operação, fila sequencial de gravações no GitHub e reconciliação periódica para corrigir eventos perdidos.
8. Fazer um disparo de teste autorizado e verificar dashboard + planilha. Ativar produção somente após validar ponta a ponta.

**Credenciais:** chave UmClique, autenticação do webhook, OAuth Google Sheets e token GitHub fine-grained com `Contents: Read/Write` **somente neste repositório** ficam no cofre do n8n/secret manager. Nunca em JSON, Google Sheets, prints, ChatGPT ou arquivos públicos.

### B. Contrato interno mínimo (não é o formato da API UmClique!)

```json
{
  "campaign_id": "EXEMPLO-ID-OFICIAL-A-CONFIRMAR",
  "name": "Disparo Exemplo - Wes",
  "status": "completed",
  "channel": "Meta API Oficial",
  "template": "convite_evento...",
  "started_at": null,
  "completed_at": null,
  "updated_at": null,
  "metrics": {
    "contacts": 150,
    "sent": 150,
    "failures": 18,
    "delivered": null,
    "read": null,
    "replied": null
  }
}
```

Os campos e valores acima são **exemplo didático**. O mapeamento para o JSON real da UmClique será definido a partir da documentação e de um retorno de teste.

### C. Destinos e regras de consolidação

| Destino | Coluna / campo | Regra |
|---|---|---|
| Sheets · Disparos WhatsApp | M: ID UmClique | Chave única de atualização (não nome) |
| Sheets · Disparos WhatsApp | D/E/F | Contatos / enviados / falhas, na semântica da plataforma |
| Sheets · Disparos WhatsApp | G/H | Sem falha e % falhas, calculados; **não são entregas confirmadas** |
| Sheets · Disparos WhatsApp | P/Q/R | Entregues / lidos / respostas, apenas quando disponíveis |
| Sheets · Disparos WhatsApp | S/T/U | Última sincronização / origem / conciliação |
| GitHub · data/disparos.json | campaigns[].id | **Mesmo campaign_id** após a conciliação |
| GitHub · data/disparos.json | campaigns[].sent/failures | Atualização por total absoluto (não incremento) |
| GitHub Pages | cards, tabela, taxas | Recalculados do JSON quando o visitante carrega a página |

O total da planilha permanece na **linha 12**. As fórmulas das colunas D–H somam as linhas 5–11 e a partir da 13, pulando a linha do próprio total. As sete campanhas iniciais não serão automaticamente relacionadas à UmClique sem seus IDs.

### D. Casos que exigem atenção

- Se chegar o mesmo webhook novamente, **atualizar a mesma campanha**, não criar outra nem somar os valores.
- Uma campanha `concluída` pode ter leituras novas depois; reagendar consulta e alterar totais.
- `enviado`, `entregue`, `lido`, `falhou` e `respondeu` não são equivalentes.
- Se uma atualização do GitHub falhar depois de atualizar Sheets, reprocessar a campanha a partir da fonte. Não considerar a sincronização concluída até os dois destinos confirmarem.
- Se o evento traz telefone, nome ou conteúdo da mensagem, **descartar antes do GitHub** e limitar dados pessoais no Sheets conforme necessidade e LGPD.
- Validar fuso `America/Fortaleza` e datas originais (não inferir o dia pelo texto “há 1 dia”).
- Evitar que múltiplas execuções gravem no mesmo arquivo simultaneamente; serializar updates ou reconciliar estado antes de salvar.

## 4. Checklist de go-live

- [ ] Plano habilitado e documentação oficial recebida
- [ ] Credenciais criadas com privilégio mínimo
- [ ] Evento de campanha ou endpoint de relatório confirmado
- [ ] Exemplo real sem PII validado em teste
- [ ] IDs das 7 campanhas históricas conciliados (se disponíveis)
- [ ] Conexão OAuth com a planilha operacional
- [ ] Token GitHub de Contents limitado ao repo
- [ ] Primeira campanha-teste refletida no Sheets
- [ ] Mesma campanha-teste refletida no site
- [ ] Reentrega do mesmo evento não gera duplicidade
- [ ] Falhas de integração geram alerta e retry
- [ ] Reconciliação periódica funcionando

**Importante:** este documento é o **projeto técnico**, não afirma que a UmClique já esteja conectada ou que uma sincronização automática esteja ativa.
