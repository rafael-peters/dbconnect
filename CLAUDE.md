# CLAUDE.md - Contexto do Projeto dbconnect

## O que e este projeto

Script Python para acessar o banco de dados do **Medicine Dream** (sistema medico) via Firebird 2.5. Conecta ao servidor `recepcao-novo:3050` e consulta dados de pacientes e prontuarios.

## Arquitetura

- **`paciente.py`** - Classe `MedicineDB` que encapsula todas as queries (pacientes, prontuario, PDFs).
- **`app.py`** - Interface web Flask com dark theme (SPA). Roda em `http://localhost:5000`.
- **`fbclient.dll`** + DLLs de suporte - Firebird client 64 bits (embedded renomeado).
- Banco de dados remoto: `C:\Genesis\Medicine\Dados\Medicine.fdb` no servidor.
- Bancos de blobs (PDFs): `C:\Genesis\Medicine\Dados\Medicine_blob{N}.fdb` no servidor.

## Conexao

```python
CONFIG = {
    'host': 'recepcao-novo',
    'port': 3050,
    'database': r'C:\Genesis\Medicine\Dados\Medicine.fdb',
    'user': 'EXTERNO',
    'password': 'cachorro1410',
    'charset': 'WIN1252'
}
```

Usa a biblioteca `fdb` com `fbclient.dll` carregada via `fdb.load_api()`.

## Armadilhas conhecidas

1. **IDs**: O ID visivel no sistema e `A6COD` (tabela `M6PACIENTE`), **NAO** `A115COD` (tabela `I115CLIENTE_FORNENCEDOR`). Buscar sempre por `A6COD`.

2. **Nome do profissional**: Nao existe campo nome em `M31USUARIO`. Fazer JOIN: `M31USUARIO.A31FKI115COD -> I115CLIENTE_FORNENCEDOR.A115COD` para obter `A115NOME`.

3. **Evolucoes de consulta**: Textos de atendimento diario estao em `M51ATENDIMENTO_AGENDA_TEXTO` (ligada a `M27AGENDA`), **NAO** em `M50ATENDIMENTO_TEXTO` (historico geral).

4. **Nome da tabela**: E `I115CLIENTE_FORNENCEDOR` (com N extra: FORNE**N**CEDOR).

5. **DLL 32 vs 64 bits**: O `fbclient.dll` do servidor e 32 bits. Este projeto usa a versao 64 bits (do Firebird embedded) para compatibilidade com Python 64 bits.

6. **Charset**: O banco usa `WIN1252`. Caracteres acentuados podem aparecer com encoding incorreto no terminal.

7. **Blobs retornam BlobReader**: Campos blob do Firebird (como `A999BLOB` e `A171DOCUMENTO`) retornam `fdb.fbcore.BlobReader`, nao `bytes`. Sempre usar `.read()` para extrair os bytes. Tentar `bytes(blob)` causa `TypeError`.

8. **Caminho dos blobs**: Os bancos de blob (`Medicine_blob{N}.fdb`) ficam em `C:\Genesis\Medicine\Dados\` no servidor, NAO em `G:\DADOS - Teste\`.

9. **Colunas M250**: A tabela `M250DOCUMENTOS_OLE` NAO tem colunas `A250COD`, `A250DATA`, `A250HORA`, `A250FK31COD_USUARIO`. Os nomes reais sao: `A250ITEM`, `A250DATA_INSERCAO`, `A250TIPO_DOCUMENTO`, etc.

## Estrutura de tabelas - resumo rapido

### Paciente
- `M6PACIENTE` -> `I115CLIENTE_FORNENCEDOR` (dados basicos)
- `I135PESSOA_FISICA` (nascimento, pais, apelido)
- `I128TELEFONES`, `I129END_ELETRONICO` (contatos)
- `I130DOC_NUMERICO` (CPF tipo=1), `I131DOC_STRING` (RG tipo=101)
- `M5CONVENIO` (convenio, via `I115` para nome)

### Prontuario
- `M27AGENDA` (consultas, FK paciente = `A27FK6COD_PACIENTE`)
- `M51ATENDIMENTO_AGENDA_TEXTO` (evolucoes, FK agenda = `A51COD_AGENDA`)
- `M74PRECONSULTA` (sinais vitais)
- `M54RECEITA_PRESCRITA` + `M55ITENS_PRESCRITOS` (receitas)
- `M171DOCUMENTOS` (documentos do prontuario)

### PDFs (blobs em bancos Firebird separados)

Os PDFs NAO ficam no banco principal. Estao distribuidos em bancos shard separados.

**Metadados** - `M250DOCUMENTOS_OLE` (no banco principal `Medicine.fdb`):
- `A250FK6COD_PACIENTE` = FK paciente (usa `A6COD`)
- `A250ITEM` = Numero sequencial do documento
- `A250NOME` = Nome/descricao do documento
- `A250DATA_INSERCAO` = Data de insercao (datetime)
- `A250DOCUMENTO` = Conteudo OLE (geralmente nulo, o PDF real fica no blob)
- `A259FK999COD_BLOB` = **ID do blob no banco shard** (chave para buscar o PDF)
- `A250TIPO_DOCUMENTO` = Tipo do documento (ex: "PDF")
- `A250FK10COD_GRUPO_HISTORICO` = FK grupo historico

**Binarios** - `M999BLOBS` (em bancos shard `Medicine_blob{N}.fdb`):
- `A999COD` = ID do blob (PK) - corresponde a `A259FK999COD_BLOB`
- `A999BLOB` = Conteudo binario do PDF (retorna `fdb.fbcore.BlobReader`, usar `.read()`)

**Localizacao dos shards:**
- Caminho: `C:\Genesis\Medicine\Dados\Medicine_blob{N}.fdb` (no servidor `recepcao-novo`)
- Formula: `N = (A259FK999COD_BLOB // 5000) + 1`
- Credenciais: `SYSDBA` / `masterkey`
- Exemplo: blob_id `23166` -> shard `5` -> `Medicine_blob5.fdb`

**Armadilhas dos blobs:**
1. O caminho `G:\DADOS - Teste` NAO funciona. O caminho correto e `C:\Genesis\Medicine\Dados`.
2. O campo `A999BLOB` retorna `fdb.fbcore.BlobReader`, nao `bytes`. Usar `blob.read()` para obter os bytes.
3. A tabela M250 NAO tem colunas `A250COD`, `A250DATA`, `A250HORA`, `A250FK31COD_USUARIO` (nomes que parecem logicos mas nao existem).

### Tabelas ainda nao implementadas
- `M50ATENDIMENTO_TEXTO` - Historico geral (nao ligado a consulta)
- `M87/M88/M89GESTACAO*` - Gestacao
- `F1PRODUTO`, `M21PROCEDIMENTO`, `M122TABELA_INTERNA_PROCEDIMENTO` - Procedimentos

## Comandos uteis

```bash
# Instalar dependencias
pip install fdb flask

# Interface web
python app.py
# -> http://localhost:5000

# Menu interativo (terminal)
python paciente.py

# Usar como modulo
python -c "from paciente import MedicineDB; db = MedicineDB().conectar(); print(db.buscar_paciente_por_id(50482)['nome']); db.desconectar()"
```

## Padrao de query para obter nome do profissional

```sql
SELECT uc.A115NOME AS PROFISSIONAL
FROM <tabela> t
LEFT JOIN M31USUARIO u ON t.<FK_USUARIO> = u.A31COD
LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
```
