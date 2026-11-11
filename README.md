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

## Integração UmClique (em preparação)

O guia de ativação da integração automática está em **[docs/CONFIGURAR_AUTOMACAO.md](docs/CONFIGURAR_AUTOMACAO.md)**.

**Status:** os endpoints oficiais foram identificados e o sincronizador via GitHub Actions foi implementado. A automação permanece **inativa** até configurar a chave UmClique, os IDs dos canais, a conta de serviço do Google e o token GitHub de publicação.

## Atualização de dados

1. Registrar os novos disparos na planilha operacional, com ID da campanha, período, contatos, envios, falhas e status.
2. Conferir a plataforma e separar `0` de "não apurado".
3. Atualizar `data/disparos.json` no repositório, adicionando campanhas novas ou ajustando as existentes com evidência.
4. Fazer commit no ramo `main`. O site estático passa a usar os dados mais recentes assim que o deploy ocorrer.
5. Não alterar o histórico sem registrar correção e a fonte. Nunca inserir dados pessoais.

**Importante:** até ativar o workflow e as credenciais, a atualização continua manual. Quando o workflow estiver ativo, ele atualizará o Sheets e o JSON do site consultando a API da UmClique a cada aproximadamente 15 minutos. Alterações manuais feitas apenas na planilha não sincronizam automaticamente para o GitHub.

## Publicação da página

✅ O GitHub Pages está ativo no endereço https://ywez.github.io/DisparoWpp/ (abertura e dados verificados em navegador público em 11/11/2026).

Configuração: `Settings → Pages` → `Deploy from a branch` → `main` → `/(root)`.

O arquivo `index.html` já é publicado no site por essa configuração. Os dados são lidos de `data/disparos.json`; atualizações nesse arquivo exigem novo commit para refletir no site.

## Estrutura

- `index.html`: painel web responsivo
- `data/disparos.json`: base agregada de campanhas para o site
- `README.md`: instruções e regras de atualização

Criado a partir dos registros de 9–10/11/2026, com conferência em 11/11/2026.
