# Storage Do App

Este modulo define como o app salva, localiza e remove arquivos de midia usados pelos jobs.

O storage nao deve guardar resultado final estruturado, analise de copy, roteiro, tokens ou status. Esses dados pertencem ao banco/store. O storage cuida apenas de arquivos fisicos como video original, audio extraido e arquivos temporarios necessarios para processamento.

## Objetivo

Permitir dois fluxos sem mudar a API publica do pipeline:

- upload via backend, salvando em disco local;
- upload direto para storage externo, como S3, Cloudflare R2 ou Google Cloud Storage.

Em ambos os casos, o processo deve conseguir limpar os arquivos do job depois que o pipeline finalizar ou falhar.

## Modelo Mental

O app deve trabalhar com uma chave logica de arquivo, nao com caminhos espalhados pelo codigo.

Exemplo de chave:

```text
jobs/{job_id}/input.mp4
jobs/{job_id}/audio.wav
```

Essa chave pode apontar para:

```text
.storage/jobs/{job_id}/input.mp4
```

ou para:

```text
s3://bucket/jobs/{job_id}/input.mp4
```

O pipeline deve depender da interface de storage, nao da implementacao concreta.

## Modulos

### `base.py`
<FEITO>
Define os contratos compartilhados por todos os storages.

Responsabilidades:

- definir `StoredFile`;
- definir `StorageBase`;
- padronizar metodos que o app usa sem conhecer o backend real.

Contrato atual do MVP:

- `save_file`: salva arquivo que ja existe no servidor;
- `save_upload`: salva o arquivo recebido pela API diretamente no storage;
- `exists`: verifica se uma chave existe;
- `delete`: remove um arquivo;
- `delete_prefix`: remove todos os arquivos de um job;
- `uri`: retorna a referencia do arquivo.

Contrato futuro para upload direto em storage externo:

- `UploadTarget`: dados que o frontend precisa para enviar direto ao storage;
- `create_upload_target`: cria alvo de upload direto para storage externo;
- `confirm_upload`: confirma que um arquivo enviado diretamente existe.

Esses itens nao devem entrar como `abstractmethod` agora. Eles pertencem ao fluxo S3/R2/GCP direto e nao fazem parte do `LocalStorage` inicial. Quando esse fluxo for implementado, a base pode ser expandida sem afetar a logica atual de chave, cleanup e pipeline.

### `local.py`
<FEITO>
Implementa storage local em disco.

Responsabilidades:

- salvar arquivo em uma pasta local controlada pelo app;
- salvar upload recebido pela API sem passar por arquivo temporario intermediario;
- garantir que a chave nao escape da pasta raiz;
- criar diretorios automaticamente;
- remover arquivo individual;
- remover todos os arquivos de um job;
- retornar URI local como caminho absoluto.

Exemplo de estrutura local:

```text
.storage/
  jobs/
    {job_id}/
      input.mp4
      audio.wav
```

No fluxo local, o frontend envia o arquivo para a API. A API recebe o arquivo, grava no storage local e inicia o job.

### `s3.py`
<FEITO>
Implementacao futura para AWS S3.

Responsabilidades:

- implementar `save_file` (upload via boto3 `upload_file`, arquivo ja existente em disco);
- implementar `save_upload` (upload via boto3 `upload_fileobj`, stream recebido pela API);
- implementar `exists` (via `head_object`);
- gerar presigned URL para upload direto;
- confirmar se o objeto existe depois do upload;
- remover objeto individual;
- remover objetos por prefixo do job;
- retornar URI do objeto.

Detalhes de implementacao a decidir:

- formato de `uri()`: `s3://{bucket}/{key}` (URI interna) ou URL HTTPS publica/assinada. Isso afeta o que fica salvo em `input_file_uri` no banco;
- `delete_prefix` no S3 exige paginacao: `list_objects_v2` retorna no maximo 1000 objetos por chamada, entao precisa usar paginator ou loop com `ContinuationToken` antes de `delete_objects`;
- configuracao obrigatoria: bucket, region, credenciais (ou role), e endpoint customizado (necessario para R2 reaproveitar essa classe depois);
- traducao de erros do boto3 (`ClientError`, `BotoCoreError`) para `StorageError`, mantendo a mesma interface de erro que `LocalStorage` ja usa;
- upload de arquivo grande: `upload_fileobj` do boto3 ja faz multipart automatico acima de um threshold, mas vale confirmar o `TransferConfig` se os videos passarem de alguns GB.

### `r2.py`
<FEITO>
Implementacao futura para Cloudflare R2.

R2Storage deve reutilizar toda a implementacao de S3Storage e apenas configurar
`endpoint_url`, `region_name`, `uri_scheme` e `backend`:

```python
class R2Storage(S3Storage):
    backend = "r2"

    def __init__(self, account_id: str, bucket: str, access_key: str, secret_key: str) -> None:
        super().__init__(
            bucket=bucket,
            region_name="auto",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            access_key=access_key,
            secret_key=secret_key,
            uri_scheme="r2",
        )
```

`uri_scheme="r2"` e obrigatorio aqui: sem isso, `uri()` herda o default `"s3"` de
`S3Storage` e toda referencia de arquivo R2 fica salva no banco como `s3://bucket/key`,
o que confunde debug e qualquer logica futura que decida comportamento a partir do
prefixo da URI (materializer, por exemplo).

`region_name="auto"` fica fixo dentro do `R2Storage`, nao exposto como parametro do
seu `__init__` — R2 nao tem regioes reais, e deixar configuravel abre espaco pra
alguem passar um valor tipo `"us-east-1"` por engano copiando de exemplo AWS.

Diferencas que exigem atencao, mesmo com API compativel:

- R2 nao cobra egress; S3 cobra — afeta custo se o materializer baixar arquivos com frequencia;
- credenciais de R2 sao um R2 API token (formato access key/secret key), gerado separado do restante da conta Cloudflare;
- nem toda feature do S3 tem equivalente no R2 (storage classes, object lock, replication) — o contrato do app usa apenas save_file, save_upload, exists, delete, delete_prefix, uri e presigned URL, entao isso nao deve ser um problema, mas vale confirmar antes de ir pra producao.

### `gcp.py`
<FEITO>
Implementa storage em Google Cloud Storage.

Diferente de `R2Storage`, `GCPStorage` nao herda de `S3Storage`. Google Cloud Storage nao usa o client boto3 nem a API S3 do app. A implementacao deve usar `google-cloud-storage` e implementar `StorageBase` diretamente.

`GCPStorage` deve seguir o mesmo contrato atual dos outros storages:

- `save_file`: fazer upload de arquivo local usando `blob.upload_from_filename`;
- `save_upload`: fazer upload de stream usando `blob.upload_from_file`;
- `exists`: verificar objeto usando `blob.exists`;
- `delete`: remover objeto usando `blob.delete`;
- `delete_prefix`: remover objetos por prefixo usando `bucket.list_blobs(prefix=...)`;
- `uri`: retornar `gs://{bucket}/{key}`;
- traduzir erros do Google SDK para `StorageError`.

`__init__`:

```python
def __init__(
    self,
    bucket: str,
    credentials_path: str | None = None,
    project: str | None = None,
    uri_scheme: str = "gs",
) -> None:
    ...


### `paths.py`
<FEITO>
Modulo opcional para centralizar as chaves padrao do job.

Responsabilidades:

- gerar `job_prefix(job_id)`;
- gerar `job_input_key(job_id, filename)`;
- gerar `job_audio_key(job_id)`.

Isso evita strings duplicadas como `jobs/{job_id}/...` espalhadas pela API e pelo pipeline.

### `factory.py`

Modulo opcional para construir o storage correto a partir das settings.

Responsabilidades:

- ler `settings.storage_backend`;
- retornar `LocalStorage`, `S3Storage`, `R2Storage` ou `GCPStorage`;
- validar configuracoes obrigatorias de cada backend.

## Fluxo 1: Upload Pelo Backend Com LocalStorage

Este e o fluxo inicial do app.

```text
frontend
-> backend
-> LocalStorage
-> pipeline
-> cleanup
```

Etapas:

1. frontend envia arquivo para a API;
2. backend cria `job_id`;
3. backend chama `save_upload` e grava o upload em `jobs/{job_id}/input.ext`;
4. backend registra o job no banco;
5. pipeline usa o arquivo local para FFmpeg, transcricao e workflows;
6. resultado estruturado fica no banco;
7. arquivos temporarios do job sao apagados ao final.

O banco deve guardar:

- `job_id`;
- `status`;
- `input_file_key`;
- `input_file_uri`;
- `storage_backend`;
- resultado final;
- erro, se existir;
- tokens;
- tempos.

O arquivo de video nao deve ser salvo no banco.

`save_upload` existe para evitar o fluxo ruim:

```text
UploadFile -> /tmp -> storage final
```

O fluxo esperado e:

```text
UploadFile -> storage final
```

Assim a API grava o stream recebido diretamente no destino final do job, reduzindo I/O e evitando uso desnecessario de espaco temporario.

`save_upload` deve proteger contra escrita parcial. A gravacao deve acontecer primeiro em um arquivo temporario na mesma pasta do destino e so depois ser promovida para a chave final.

Fluxo esperado:

```text
jobs/{job_id}/input.mp4.part
-> grava chunks do upload
-> upload terminou com sucesso
-> rename/replace para jobs/{job_id}/input.mp4
```

Se a conexao cair, o disco encher ou qualquer erro acontecer durante a gravacao, o arquivo parcial deve ser apagado antes de propagar `StorageError`.

Com isso, `exists(key)` continua significando que o arquivo final existe de forma completa, nao que existe um arquivo truncado.

## Fluxo 2: Upload Direto Para Storage Externo

Este fluxo entra futuramente quando o app usar S3, R2 ou GCP para receber arquivo direto do navegador.

```text
frontend
-> backend cria upload target
-> frontend envia direto para storage
-> frontend confirma upload no backend
-> pipeline
-> cleanup
```

Etapas:

1. frontend pede ao backend um alvo de upload;
2. backend cria `job_id`;
3. backend gera `UploadTarget` com URL assinada, metodo, headers e key;
4. frontend envia o arquivo direto para S3/R2/GCP;
5. frontend chama backend confirmando o upload;
6. backend chama `confirm_upload(key)`;
7. backend registra o arquivo no job;
8. pipeline processa o arquivo;
9. arquivos do job sao apagados ao final com `delete_prefix`.

Nesse fluxo, o backend nao recebe o arquivo inteiro. Ele apenas autoriza, registra e processa depois.

Esse fluxo nao deve forcar o `LocalStorage` atual a implementar metodos mortos. `create_upload_target`, `confirm_upload` e `UploadTarget` entram quando o primeiro storage externo for construido.

## FFmpeg E Arquivo Local

FFmpeg normalmente trabalha melhor com arquivo local.

Se o arquivo estiver no `LocalStorage`, o pipeline usa o caminho local diretamente.

Se o arquivo estiver em S3/R2/GCP, existem duas opcoes:

- baixar o arquivo para workspace temporario local antes de rodar FFmpeg;
- usar uma URL assinada de leitura se o comando e o provider suportarem bem esse fluxo.

Para o pipeline, isso deve ser encapsulado em uma etapa de materializacao:

```text
StoredFile -> arquivo local temporario para processamento
```

Essa etapa pode ser outro modulo no futuro, por exemplo:

```text
storage/materializer.py
```

Responsabilidades do materializer:

- receber `StoredFile`;
- garantir um arquivo local disponivel;
- devolver `Path` local para FFmpeg/transcriber;
- limpar temporarios apos uso.

## Cleanup

O cleanup deve acontecer mesmo quando o pipeline falhar.

Fluxo esperado:

```text
try:
  processar job
finally:
  storage.delete_prefix(job_prefix)
```

No storage local, `delete_prefix` remove a pasta do job.

Em S3/R2/GCP, `delete_prefix` remove todos os objetos que comecam com `jobs/{job_id}/`.

O resultado final nao depende desses arquivos depois que o pipeline acaba, porque o banco guarda o resultado estruturado.

## Ordem De Implementacao

1. ajustar `StorageBase` com o contrato atual do MVP;
2. implementar `save_upload` no `LocalStorage`;
3. implementar `delete_prefix` no `LocalStorage`;
4. criar helpers de chave em `paths.py`;
5. ajustar API de upload local para salvar em `LocalStorage`;
6. garantir cleanup com `finally`;
7. criar `factory.py`;
8. quando cloud entrar, adicionar `UploadTarget`, `create_upload_target` e `confirm_upload` ao contrato;
9. implementar `S3Storage`, `R2Storage` ou `GCPStorage`;
10. criar materializer se o pipeline precisar processar arquivos remotos.

## Decisao Atual

O primeiro fluxo implementado deve ser local:

```text
frontend -> backend -> LocalStorage
```

O desenho do modulo deve manter espaco para o segundo fluxo:

```text
frontend -> storage externo direto
```

Assim o app consegue iniciar simples sem fechar a porta para S3, Cloudflare R2 ou Google Cloud Storage.
