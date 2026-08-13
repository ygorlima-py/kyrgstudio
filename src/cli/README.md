# Kyrg CLI

Prompts de construcao do cliente de terminal do Kyrg Studio. Execute uma etapa
por vez e leia novamente o OpenAPI e os arquivos atuais antes de alterar o
codigo.

## Regras Para Todas As Etapas

- Trabalhe somente dentro de `src/cli`, nos testes do CLI e no empacotamento
  necessario em `pyproject.toml`.
- Nao coloque logica de terminal em `app.api`, `app.auth`, `app.store` ou
  `app.worker`.
- Use os contratos existentes no OpenAPI e nos schemas publicos.
- Nao invente endpoints, campos, codigos de erro ou regras de negocio.
- Nao imprima access tokens, refresh tokens, senhas ou dados internos.
- Mantenha as operacoes testaveis sem banco, RabbitMQ, worker ou Docker.
- Antes de editar, leia os arquivos envolvidos e confira o estado atual do
  repositorio.
- Depois de editar, execute somente as validacoes relacionadas a etapa.

## 1. Contrato Do CLI
[FEITO]
```text
Execute somente a etapa de definicao do contrato do CLI.

Leia o OpenAPI atual, os contratos de autenticacao e os schemas publicos de
jobs. Nao implemente comandos nem altere o backend.

Defina uma especificacao curta para o MVP com estes comandos:

- kyrg --help;
- kyrg --version;
- kyrg login;
- kyrg logout;
- kyrg analyze FILE;
- kyrg adapt FILE;
- kyrg status JOB_ID;
- kyrg result JOB_ID.

Para cada comando documente finalidade, argumentos, opcoes, entrada
interativa, saida esperada, erros publicos e codigo de saida. Defina tambem
como o usuario configura a URL da API e como a sessao sera mantida localmente.

Se algum endpoint ou campo nao existir, marque a lacuna e proponha reutilizar
o contrato existente, sem inventar uma API.

Ao final, entregue apenas a especificacao e uma lista de decisoes pendentes.
``` 

## 2. Fundacao E Empacotamento
[FEITO]
```text
Execute somente a etapa de fundacao e empacotamento do CLI.

Use a estrutura `src/cli/` e mantenha o cliente isolado do restante da
aplicacao. Implemente apenas:

- ponto de entrada do comando kyrg;
- comandos --help e --version;
- organizacao inicial de commands, config, api_client, output e errors;
- configuracao do entry point no pyproject.toml;
- tipagem e docstrings dos contratos publicos.

Use a biblioteca CLI ja existente no projeto. Se nao houver, escolha uma
dependencia pequena e justifique a escolha antes de adiciona-la.

O comando `kyrg --help` deve funcionar sem banco, Docker, RabbitMQ, API ou
variaveis de credencial. Nao implemente login, upload ou chamadas HTTP.

Valide importacao, `kyrg --help`, `kyrg --version` e o build do pacote.
``` 

## 3. Configuracao Local E Sessao
[Feito]
```text
Execute somente a etapa de configuracao local e persistencia de sessao.

Leia o contrato definido para o CLI e implemente em `src/cli/config.py`:

- URL base da API por opcao, variavel de ambiente e arquivo local, nesta ordem
  de precedencia;
- caminho de configuracao compativel com Linux, macOS e Windows;
- armazenamento local da sessao com permissoes restritas;
- leitura, gravacao e limpeza da sessao;
- validacao de configuracao ausente ou invalida.

Defina claramente qual valor vence quando a mesma configuracao aparece em mais
de um lugar. Nunca grave senha ou token em texto exibido no terminal. Nao faca
chamadas HTTP nesta etapa.

Crie testes unitarios para precedencia, configuracao invalida, sessao ausente,
sessao gravada e limpeza da sessao. Nao altere o backend.
``` 

## 4. Cliente HTTP E Erros Publicos
[FEITO]
```text
Execute somente a etapa de cliente HTTP do CLI.

Leia o OpenAPI atual e implemente `src/cli/api_client.py` usando os endpoints
que realmente existem. O cliente deve:

- receber a URL base e um transporte injetavel;
- enviar cookies ou o mecanismo de autenticacao definido pela API;
- aceitar timeout e cancelamento quando a biblioteca escolhida suportar;
- converter respostas de erro para um erro interno do CLI;
- preservar somente codigo, mensagem e detalhes publicos permitidos;
- nunca incluir tokens, cookies, senhas ou resposta interna nas mensagens.

Nao duplique regras de negocio do backend. Nao crie endpoints ficticios. Se a
API nao possuir uma operacao necessaria, registre a lacuna e pare nessa parte.

Crie testes unitarios com transporte falso para sucesso, timeout, JSON invalido,
401, 403, 404, 409, 422, 500 e 503.
``` 

## 5. Login E Logout
[Feito]

```text
Execute somente a etapa de autenticacao do CLI.

Com base no OpenAPI atual, implemente `kyrg login` e `kyrg logout` usando os
contratos existentes. O login deve:

- solicitar email e senha sem exibir a senha;
- chamar somente o endpoint real de login;
- salvar apenas os dados de sessao necessarios, com protecao local;
- mostrar uma mensagem publica de sucesso ou falha;
- retornar codigo de saida previsivel.

O logout deve limpar a sessao local mesmo se a API estiver indisponivel, sem
exibir tokens. Se existir endpoint de logout, use-o; caso contrario, documente
que o logout local e a unica operacao disponivel.

Nao implemente Google, cadastro ou redefinicao de senha nesta etapa. Crie testes
para login bem-sucedido, credenciais invalidas, sessao salva, logout local e
falha de rede.
``` 

## 6. Analise E Adaptacao
[Feito]
```text
Execute somente a etapa dos comandos `kyrg analyze FILE` e `kyrg adapt FILE`.

Leia os schemas publicos e o endpoint real de criacao de job. Implemente:

- validacao local de existencia, nome, extensao e tamanho do arquivo;
- montagem do multipart exatamente como a API espera;
- `analyze` sem enviar user_profile quando o contrato nao exigir;
- `adapt` solicitando e validando os campos obrigatorios de user_profile;
- exibicao do job_id e do status publico retornado;
- suporte a timeout e interrupcao sem deixar arquivos temporarios abandonados.

Nao execute hashing, JWT, transcricao ou regras de pipeline no CLI. Nao envie
paths locais como se fossem paths de storage. Nao exponha o conteudo completo da
resposta nem tokens em logs.

Crie testes unitarios com arquivo temporario e cliente HTTP falso para os dois
fluxos, validacao de arquivo, cancelamento, erro 422 e erro 503.
``` 

## 7. Status E Resultado
[Feito]

```text
Execute somente a etapa dos comandos `kyrg status JOB_ID` e
`kyrg result JOB_ID`.

Use apenas os endpoints e campos existentes no OpenAPI. Implemente:

- validacao de JOB_ID antes da chamada;
- consulta do status publico;
- exibicao clara dos estados uploaded, running, completed e failed;
- tratamento de resultado ainda indisponivel;
- exibicao do resultado sem JSON bruto quando houver contrato publico;
- ocultacao de input, output interno, paths de storage e detalhes tecnicos;
- codigo de saida diferente para sucesso, job inexistente, resultado pendente
  e falha do job.

Nao implemente polling automatico nesta etapa, a menos que ele esteja previsto
explicitamente no contrato do CLI. Se polling for necessario, documente o
intervalo, limite e cancelamento antes de codificar.

Crie testes para cada estado publico e para jobs de outro usuario.
``` 

## 8. Saida, Formato E Experiencia De Terminal
[Feito]

```text
Execute somente a etapa de saida e experiencia de terminal.

Leia todos os comandos ja implementados e padronize `src/cli/output.py` para:

- saida humana legivel por padrao;
- formato JSON opcional, se previsto no contrato do CLI;
- mensagens curtas e acionaveis;
- uso consistente de stdout para sucesso e stderr para erros;
- codigos de saida documentados;
- suporte basico a terminal sem cor, redirecionamento e CI.

Nao altere contratos da API. Nao mostre dados sensiveis em nenhum formato.
Garanta que erros publicos mantenham o codigo da API sem vazar stack trace.

Crie testes para saida humana, saida JSON, terminal sem cores, redirecionamento
e mensagens de erro.
``` 

### Codigos De Saida

- `0`: comando concluido com sucesso;
- `1`: erro esperado generico;
- `2`: argumento, configuracao ou entrada local invalida;
- `3`: autenticacao rejeitada ou sessao invalida;
- `4`: job ou recurso nao encontrado;
- `5`: operacao em conflito, como resultado ainda nao disponivel;
- `6`: API indisponivel ou timeout de rede;
- `7`: erro publico da API ou infraestrutura;
- `8`: job encontrado, mas finalizado com falha;
- `130`: operacao interrompida pelo usuario.

## 9. Testes E Validacao Final
[FEITO]
```text
Execute somente a etapa de validacao final do CLI.

Leia a implementacao completa e verifique, sem alterar o backend:

- `kyrg --help` e `kyrg --version` sem infraestrutura;
- login, logout, analyze, adapt, status e result com cliente HTTP falso;
- ausencia de tokens, senhas e cookies em stdout, stderr e logs;
- codigos de saida documentados;
- configuracao por ambiente e arquivo local;
- compatibilidade com terminal nao interativo;
- tratamento de timeout, 401, 403, 404, 409, 422, 500 e 503;
- empacotamento e funcionamento do entry point instalado.

Execute os testes unitarios do CLI, lint, type checking e build do pacote.
Corrija somente problemas introduzidos pelo CLI. Ao final, informe arquivos
alterados, comandos executados, resultados e lacunas reais.
``` 

## Decisoes Pendentes

- Confirmar a biblioteca CLI adotada no `pyproject.toml`.
- Confirmar o mecanismo de autenticacao aceito pelo endpoint de login.
- Confirmar se o logout possui endpoint remoto ou sera somente local.
- Confirmar se o CLI usara cookies, access token ou ambos na sessao local.
- Confirmar se a API oferece um endpoint publico para resultado de job.
- Confirmar se a saida JSON sera necessaria no MVP.
- Definir politica de permissao e localizacao do arquivo de sessao em cada
  sistema operacional.
- Definir politica de expiracao e renovacao da sessao do CLI.
