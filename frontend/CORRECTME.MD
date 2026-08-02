# Historico E Busca De Jobs

## Objetivo

Criar uma pagina em que o usuario possa consultar todos os seus projetos,
localizar um job pelo identificador e filtrar o historico sem carregar todos os
registros do banco de uma vez.

Os jobs ainda nao possuem titulo. Por isso, a busca inicial deve aceitar o
`job_id` exibido ao usuario e combinar essa busca com filtros de status e tipo
de pipeline. Nao pesquisar dentro de `input_json`, `output_json`, transcricao ou
erros internos. Uma busca textual por nome exige adicionar um campo publico de
nome do projeto em uma evolucao separada.

## 1. Expandir A Consulta No Backend

Arquivos principais:

- `src/app/store/jobs.py`;
- `src/app/api/routers/jobs.py`;
- `src/app/schemas/jobs.py`.

Implementar:

- manter `GET /v1/jobs` restrito ao usuario autenticado;
- aceitar filtros opcionais por `job_id`, `status` e `pipeline_type`;
- manter ordenacao deterministica por `created_at DESC, id DESC`;
- retornar informacao de paginacao suficiente para indicar se existe uma
  proxima pagina;
- executar filtros e paginacao no banco, nunca em uma lista completa carregada
  na memoria;
- validar limites e valores aceitos antes de executar a consulta;
- revisar os indices de `jobs` para evitar degradacao conforme o historico
  crescer.

## 2. Atualizar Contrato E Cliente

Arquivos principais:

- `frontend/src/shared/api/generated/schema.ts`;
- `frontend/src/features/jobs/api/jobs-api.ts`;
- `frontend/src/features/jobs/hooks/use-user-jobs.ts`.

Implementar:

- regenerar o contrato OpenAPI depois das alteracoes do backend;
- estender `listUserJobs(...)` com os filtros suportados pela API;
- incluir pagina e filtros na query key do TanStack Query;
- encaminhar `AbortSignal` para cancelar consultas abandonadas;
- manter o polling apenas quando a pagina retornada possuir job `uploaded` ou
  `running`;
- usar os tipos gerados pelo OpenAPI sem duplicar contratos manualmente.

## 3. Construir A Pagina De Historico

Arquivos principais:

- `frontend/src/routes/jobs-history-route.tsx`;
- `frontend/src/features/jobs/components/jobs-history-list.tsx`;
- `frontend/src/features/jobs/components/jobs-history-item.tsx`.

Implementar:

- registrar a rota autenticada `/app/jobs`;
- apresentar tipo, status, identificador e data de cada projeto;
- abrir jobs ativos ou com falha na pagina de status;
- abrir jobs concluidos diretamente na pagina de resultado;
- criar estados distintos para carregamento, erro, historico vazio e busca sem
  resultados;
- reutilizar os componentes visuais existentes sem exibir JSON bruto ou
  metadados internos.

## 4. Adicionar Busca, Filtros E Paginacao

Arquivos principais:

- `frontend/src/features/jobs/components/jobs-history-filters.tsx`;
- `frontend/src/features/jobs/hooks/use-jobs-history-filters.ts`;
- `frontend/src/app/router.tsx`;
- componentes de navegacao que apontarem para o historico.

Implementar:

- permitir busca por `job_id`;
- filtrar por status e por tipo de pipeline;
- manter busca, filtros e pagina na query string da URL;
- voltar para a primeira pagina quando um filtro mudar;
- fornecer controles claros para avancar, voltar e limpar filtros;
- adicionar acesso ao historico na navegacao autenticada e no dashboard;
- preservar os filtros quando o usuario abrir um job e voltar para a lista.

## 5. Sincronizar E Validar

Implementar e verificar:

- invalidar as queries do historico depois da criacao de um job;
- confirmar que mudancas de status aparecem sem recarregar toda a aplicacao;
- confirmar que nenhum filtro permite acessar jobs de outro usuario;
- testar pagina vazia, busca sem resultado, filtros combinados e varias paginas;
- testar navegacao para status e resultado de acordo com o estado do job;
- validar responsividade, navegacao por teclado e leitores de tela;
- executar testes do backend e frontend, lint e build de producao.
