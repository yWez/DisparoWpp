# Campanha Luisa Pires — identificação de leads pela saudação

A segunda aba de mensageria agora contém um bloco de leads identificados por marcador de entrada.

## Fonte e critério

A API UmClique retorna a mensagem recebida no campo content. O sistema examina somente mensagens cujo is_from_me=false e reconhece saudações iniciais como “Oi, equipe Luisa Pires”, com tolerância a acento, pontuação e caixa. Menções ao nome no meio de outras mensagens não bastam.

É um **indício de origem**, não comprovação de campanha paga: quem enviou uma frase diferente, áudio ou chegou por outros meios pode ficar de fora. A contagem de leads identificados pode subestimar o volume real da campanha. Integração com UTMs por campanha, formulário e CRM poderá confirmar a origem.

Nenhum texto de mensagem é salvo em disco, Google Sheets, log ou frontend. A inspeção ocorre somente em memória durante a sincronização.

## KPIs e deduplicação

- Leads identificados: contatos distintos pela chave HMAC, no dia da primeira ocorrência da saudação.
- Leads em conversa: pessoas identificadas que enviaram mensagens no período.
- Mensagens recebidas / enviadas: todas as mensagens dos contatos identificados no período, mesmo se eles tiverem várias conversas.
- Ranking por atendente: usa o responsável atual da conversa identificadora mais recentemente atualizada. Não indica qual agente enviou cada mensagem.
- Canais: a atribuição de lead usa o canal da conversa identificadora; a atividade do mesmo contato pode incluir outros canais.
- Período personalizado: leads novos usam a primeira ocorrência, sem duplicar. Leads ativos únicos ficam como Não disponível porque somar contagens diárias seria incorreto.

## Privacidade e integrações

Mantida a integração UmClique → Google Sheets → JSON agregado no GitHub Pages, com atualização pelo GitHub Actions.

O estado restrito do Google Sheets recebeu de forma aditiva as colunas lp_scan_version, lp_match_first_day e lp_match_count. A aba restrita Leads - Campanha Luisa contém ID técnico da conversa, chave HMAC de contato, responsável atual, data, canal e contadores. Sem nome ou telefone de lead.

O JSON público recebe apenas contagens por período, responsável, canal e dia. Nenhum ID ou mensagem individual do lead é enviado ao GitHub Pages.

O primeiro ciclo precisa reexaminar as conversas históricas. O novo bloco mostra a própria cobertura de análise, separada da cobertura geral da mensageria. Sem reenvio automático.

## Testes

- Python unittest: saudação e falsos positivos, somente inbound, deduplicação de mensagens/contatos, fuso de Fortaleza, mapeamento por responsável e privacidade.
- Node: filtros por período e responsável, ausência de dados, intervalo personalizado e totais.
- Validação com chave UmClique salva em GitHub Secrets, sem logar mensagens/telefones.

## Limites atuais

O método não identifica áudios e frases não reconhecidas. Atribuição de campanhas sem marcador e conversão em venda dependem de UTM/CRM/checkout. Para lista nominal de contatos seria necessária uma área autenticada com controle de acesso; o site atual é público e mostra somente agregados.
