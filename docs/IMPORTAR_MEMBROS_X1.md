# Membros X1 — importação em lote, auditoria e prova de ingresso

## Status do acesso
No canal QR/UAZAPI **Aline** a UmClique devolveu 17 grupos e a contagem atual de participantes. Para os grupos de campanha:
- **A Mesa da Luisa 22/11 - Black LP**: 388 participantes na consulta de 13/11/2026.
- **A Mesa da Luísa | 17, 19 e 22/11 | Black LP**: 698 participantes na mesma consulta.

A API conectada **não fornece o telefone/JID de cada membro**, portanto **não é possível cruzar esses totais com a Captação X1**. Um mesmo membro pode aparecer nos dois grupos, os totais contêm pessoas anteriores aos disparos e podem incluir administradores. Não somar totais como leads únicos nem registrar participantes fictícios.

## Abas privadas já criadas

Na [planilha operacional](https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit):

- [Membros X1 - Mesa 22](https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit#gid=826230471)
- [Membros X1 - Mesa 17-19-22](https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit#gid=1508225503)
- [Entradas Grupo X1](https://docs.google.com/spreadsheets/d/1CPgLkw8jXIT_L9dATUU4gqsjl1vN3V0ANa7zfYQzs3k/edit#gid=342294628) — somente eventos de ingresso comprovados

### Como fazer um lote, sem preencher cada lead manualmente

1. Obter do administrador do grupo a **lista real de participantes**, com telefones do WhatsApp, por recurso oficial do provedor ou exportação autorizada. Não usar lista de destinatários do disparo como se fosse lista de membros.
2. Abrir a aba correspondente ao grupo. Colar os telefones, **um por linha, a partir de A8**, exclusivamente de uma lista de membros atual e conferida. Não colocar nomes ou observações na coluna A.
3. Informar em **B2** a data e hora da conferência (exemplo `2026-11-13 21:30:00`), do fuso `America/Fortaleza`.
4. Confirmar em **B1** o ID oficial do grupo (já preenchido; não alterar) e em **B4** a evidência `lista_participantes` ou `exportacao_grupo`.
5. **Só depois de conferir a origem da lista**, mudar **B3** de `PENDENTE` para `LISTA_VERIFICADA`. Caso contrário, deixar `PENDENTE`.
6. Repetir na outra aba. O sincronizador já integrado ao fluxo rápido consulta os dois grupos de forma independente a cada execução; pode sofrer atrasos por filas do GitHub.

**Resultado:** o sistema normaliza números, remove repetições entre linhas e grupos e cruza os telefones em memória com a `Captação` da landing page. O arquivo público contém só contagens por grupo, sem dados pessoais. Não substitua as listas se o grupo não foi conferido.

### Duas medidas diferentes

- **Cadastros X1 encontrados nos grupos:** interseção entre os cadastros de LP X1 e as listas verificadas de membros **na data de conferência**. Isso prova presença naquela data, não data de ingresso. Se só um grupo tiver lista verificada, a análise é **parcial**, e a taxa consolidada fica indisponível.
- **Entradas no grupo após o cadastro X1:** somente eventos efetivos e datados de ingresso, com telefone e evidência `evento_entrada` ou `webhook_participante`, ou `verificacao_manual` de um **evento de entrada** (não simples visualização da lista). A data do ingresso deve ser posterior ou igual à inscrição X1. Estes eventos ficam na aba `Entradas Grupo X1`.
- **Atribuição por disparo:** ainda depende de UTM exclusiva por campanha. Mesmo que o contato esteja no grupo, `x1-base` não revela qual disparo o originou.

A lista de membros não comprova que alguém entrou **por causa** do disparo ou **quando** entrou. Não transforme snapshots em eventos de entrada.

## Segurança e manutenção

As abas e os telefones estão somente no Sheets operacional privado. Não compartilhar a lista em GitHub, navegador público ou WhatsApp de suporte. Limitar os editores da planilha aos responsáveis e respeitar LGPD/consentimento. O workflow público nunca armazena o telefone ou JID do membro.

Código: `scripts/x1_roster.py`, integrado a `scripts/sync_x1.py`. Fonte: duas abas de roster privadas, controles B1–B4 e telefones A8:A. O status é `unavailable`, `partial` ou `verified`.

## Automatização total (dependência de acesso do provedor)

A API UmClique conectada confirma a contagem de participantes, mas **não expôs os membros individualmente nem seus eventos de ingresso**. O painel web da UmClique exige autenticação do administrador para verificar se há exportação de membros. Uma opção de integração futura é usar a API UAZAPI de grupos **com autorização explícita do provedor e endpoint documentado**, ou webhook `groups`, preservando credenciais num backend privado. Não configurar webhook sobre a instância existente sem conferir os webhooks ativos, pois poderá substituí-los/interrompê-los.

**Dependência real:** obter uma exportação autorizada dos membros dos grupos ou acesso de leitura a evento/listagem de participantes. Até essa obtenção, o cruzamento X1 permanece sem base de comparação.
