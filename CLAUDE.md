# CLAUDE.md - Contexto do Projeto dbconnect

## O que e este projeto

Script Python para acessar o banco de dados do **Medicine Dream** (sistema medico) via Firebird 2.5. Conecta ao servidor `recepcao-novo:3050` e consulta dados de pacientes e prontuarios.

## Arquitetura

- **`paciente.py`** - Script unico com a classe `MedicineDB` que encapsula todas as queries.
- **`fbclient.dll`** + DLLs de suporte - Firebird client 64 bits (embedded renomeado).
- Banco de dados remoto: `C:\Genesis\Medicine\Dados\Medicine.fdb` no servidor.

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

### Tabelas ainda nao implementadas
- `M50ATENDIMENTO_TEXTO` - Historico geral (nao ligado a consulta)
- `M87/M88/M89GESTACAO*` - Gestacao
- `M250DOCUMENTOS_OLE` - PDFs (blobs)
- `F1PRODUTO`, `M21PROCEDIMENTO`, `M122TABELA_INTERNA_PROCEDIMENTO` - Procedimentos

## Comandos uteis

```bash
# Instalar dependencia
pip install fdb

# Executar menu interativo
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
