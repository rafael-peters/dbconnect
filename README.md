# dbconnect - Medicine Dream Database Connector

Script Python para consulta de dados de pacientes e prontuarios do sistema **Medicine Dream**, conectando diretamente ao banco de dados Firebird 2.5.

## Conexao

| Parametro | Valor |
|-----------|-------|
| **SGBD** | Firebird 2.5 |
| **Porta** | 3050 |
| **Servidor** | `recepcao-novo` |
| **Caminho do banco** | `C:\Genesis\Medicine\Dados\Medicine.fdb` |
| **Usuario** | `EXTERNO` |
| **Senha** | `cachorro1410` |
| **Charset** | `WIN1252` |
| **Biblioteca Python** | `fdb` (requer `fbclient.dll` 64 bits) |

### Sobre a DLL do Firebird Client

O script depende do `fbclient.dll` (64 bits) na mesma pasta do script. A DLL original do servidor (`D:\Genesis\Medicine\fbclient.dll`) e 32 bits. Foi utilizada a versao embedded 64 bits do Firebird 2.5 (`fbembed.dll` renomeada para `fbclient.dll`), obtida do release oficial:

```
https://github.com/FirebirdSQL/firebird/releases/download/R2_5_9/Firebird-2.5.9.27139-0_x64_embed.zip
```

DLLs de suporte necessarias na mesma pasta: `ib_util.dll`, `icudt30.dll`, `icuin30.dll`, `icuuc30.dll`, `msvcp80.dll`, `msvcr80.dll`.

### App de acesso alternativo

O **IBExpert** pode ser usado para acessar a base diretamente. Fica na pasta `Manutencao` do PC Servidor, no disco da pasta Genesis (geralmente `C:\Genesis`). Pressione F12 para abrir o SQL Editor.

---

## Estrutura do Banco de Dados

### IDs importantes

O sistema possui dois IDs distintos para pacientes:

| Campo | Tabela | Descricao |
|-------|--------|-----------|
| **`A6COD`** | `M6PACIENTE` | **ID do Paciente** - Usado no sistema Medicine Dream |
| `A115COD` | `I115CLIENTE_FORNENCEDOR` | ID do Cliente/Fornecedor - Chave interna |

A busca deve sempre usar `A6COD` para corresponder ao ID visivel no sistema. O `A115COD` e usado internamente para JOINs com telefones, emails e documentos.

---

### Tabelas de Paciente

#### `I115CLIENTE_FORNENCEDOR` - Dados basicos da pessoa

| Campo | Descricao |
|-------|-----------|
| `A115COD` | ID (PK) |
| `A115NOME` | Nome completo |
| `A115ENDERECO` | Logradouro |
| `A115END_NUMERO` | Numero |
| `A115END_COMPLEMENTO` | Complemento |
| `A115END_BAIRRO` | Bairro |
| `A115CEP` | CEP |
| `A115FK133COD_CIDADE` | FK cidade |
| `A115ATIVO` | Status ativo |
| `A115DATA_CADASTRO` | Data de cadastro |

#### `I135PESSOA_FISICA` - Dados pessoais

| Campo | Descricao |
|-------|-----------|
| `A135FK115COD` | FK para `I115CLIENTE_FORNENCEDOR` |
| `A135DATA_NASCIMENTO` | Data de nascimento |
| `A135NOME_MAE` | Nome da mae |
| `A135NOME_PAI` | Nome do pai |
| `A135APELIDO` | Apelido |
| `A135FKM62COD_SEXO` | FK sexo |
| `A135FKM52COD_ESTADO_CIVIL` | FK estado civil |
| `A135FKM61COD_COR` | FK cor/raca |
| `A135FKM9COD_ESCOLARIDADE` | FK escolaridade |

#### `M6PACIENTE` - Dados do paciente

| Campo | Descricao |
|-------|-----------|
| `A6COD` | **ID do Paciente (PK)** - Usado no sistema |
| `A6FKI115COD` | FK para `I115CLIENTE_FORNENCEDOR` |
| `A6FK5COD_CONVENIO` | FK convenio |
| `A6MATRICULA` | Matricula do convenio |
| `A6GRUPO_SANGUINEO` | Grupo sanguineo |
| `A6FATOR_RH` | Fator RH |
| `A6DATA_HORA_CADASTRO` | Data/hora do cadastro |
| `A6LOCAL_NASCIMENTO` | Local de nascimento |
| `A6OBSERVACAO2` | Observacoes |

#### `I128TELEFONES` - Telefones

| Campo | Descricao |
|-------|-----------|
| `A128FK115COD_CLI_FOR` | FK para `I115CLIENTE_FORNENCEDOR` |
| `A128NUMERO` | Numero do telefone |
| `A128TIPO` | Tipo: 1=Celular, 2=Residencial, 3=Comercial, 4=Recado |
| `A128COD_AREA` | DDD |
| `A128CONTATO` | Nome do contato |

#### `I129END_ELETRONICO` - Emails

| Campo | Descricao |
|-------|-----------|
| `A129FK115COD_CLI_FOR` | FK para `I115CLIENTE_FORNENCEDOR` |
| `A129ENDERECO` | Endereco de email |
| `A129TIPO` | Tipo |
| `A129CONTATO` | Contato |

#### `I130DOC_NUMERICO` - Documentos numericos

| Campo | Descricao |
|-------|-----------|
| `A130FK115COD_CLI_FOR` | FK para `I115CLIENTE_FORNENCEDOR` |
| `A130TIPO` | Tipo: 1=CPF, 2=CNPJ |
| `A130DOCUMENTO` | Numero do documento |

#### `I131DOC_STRING` - Documentos texto

| Campo | Descricao |
|-------|-----------|
| `A131FK115COD_CLI_FOR` | FK para `I115CLIENTE_FORNENCEDOR` |
| `A131TIPO` | Tipo: 101=RG |
| `A131DOCUMENTO` | Numero do documento |

#### `M5CONVENIO` - Convenios

| Campo | Descricao |
|-------|-----------|
| `A5COD` | ID (PK) |
| `A5FKI115COD` | FK para `I115CLIENTE_FORNENCEDOR` (nome do convenio) |
| `A5NOME_FANTASIA` | Nome fantasia |
| `A5REGISTRO_ANS` | Registro ANS |

---

### Tabelas de Prontuario

#### `M27AGENDA` - Consultas/Agendamentos

| Campo | Descricao |
|-------|-----------|
| `A27COD` | ID (PK) |
| `A27FK6COD_PACIENTE` | FK para `M6PACIENTE` (usa `A6COD`) |
| `A27FK31COD_USUARIO` | FK para `M31USUARIO` (profissional) |
| `A27DATA` | Data da consulta |
| `A27HORA_INI_AGENDA` | Hora de inicio |
| `A27FK84COD_SITUACAO` | Situacao do agendamento |
| `A27OBSERVACAO` | Observacao |
| `A27ANOTACAO` | Anotacao |

**Situacoes da Agenda** (campo `A27FK84COD_SITUACAO`):

| Codigo | Descricao |
|--------|-----------|
| 1 | Agendado |
| 2 | Confirmado |
| 3 | Na fila |
| 4 | Atendido |
| 5 | Cancelado |
| 6 | Faltou |
| 7 | Remarcado |
| 8 | Em atendimento |
| 9 | Aguardando |
| 10 | Finalizado |

#### `M51ATENDIMENTO_AGENDA_TEXTO` - Evolucoes/Textos de atendimento

**Esta e a tabela principal dos registros de consulta diarios.** Contem o texto livre que o profissional escreve durante o atendimento.

| Campo | Descricao |
|-------|-----------|
| `A51COD_AGENDA` | FK para `M27AGENDA` |
| `A51ITEM_PALHETA` | Numero da palheta/aba |
| `A51TEXTO` | **Texto da evolucao/atendimento** |

> **Nota:** Nem `M50ATENDIMENTO_TEXTO` contem os textos de consulta diarios. A M50 e para historico geral do paciente, enquanto a **M51 e ligada a cada consulta especifica** (via `A27COD` da agenda).

#### `M171DOCUMENTOS` - Documentos do prontuario

| Campo | Descricao |
|-------|-----------|
| `A171COD` | ID (PK) |
| `A171FK6COD_PACIENTE` | FK paciente |
| `A171FK27COD_AGENDA` | FK agenda |
| `A171FK31COD_USUARIO` | FK profissional |
| `A171DATA_HORA` | Data/hora |
| `A171DOCUMENTO` | Conteudo do documento |

#### `M74PRECONSULTA` - Sinais vitais

| Campo | Descricao |
|-------|-----------|
| `A74FK6COD_PACIENTE` | FK paciente |
| `A74DATA` | Data |
| `A74HORA` | Hora |
| `A74PRESSAO_ARTERIAL_MAX` | PA sistolica |
| `A47PRESSAO_ARTERIAL_MIN` | PA diastolica |
| `A74PESO` | Peso (kg) |
| `A74ALTURA` | Altura (cm) |
| `A74CA_IMC` | IMC calculado |
| `A74FREQ_CARDIACA` | Frequencia cardiaca (bpm) |
| `A74FREQ_RESPIRATORIA` | Frequencia respiratoria (irpm) |
| `A74TEMPERATURA` | Temperatura (C) |
| `A74SATURACAO` | Saturacao O2 (%) |
| `A74HGT` | Glicemia capilar (mg/dL) |

#### `M54RECEITA_PRESCRITA` - Receitas

| Campo | Descricao |
|-------|-----------|
| `A54COD` | ID (PK) |
| `A54FK6COD_PACIENTE` | FK paciente |
| `A54FK31COD_USUARIO` | FK profissional |
| `A54DATA_HORA` | Data/hora |
| `A54OBSERVACAO` | Observacao |

#### `M55ITENS_PRESCRITOS` - Itens de receita

| Campo | Descricao |
|-------|-----------|
| `A55FK54COD_RECEITA` | FK para `M54RECEITA_PRESCRITA` |
| `A55ITEM` | Numero do item |
| `A55DESCRICAO_MEDICAMENTO` | Nome do medicamento |
| `A55POSOLOGIA` | Posologia |
| `A55QT_PRESCRITO` | Quantidade prescrita |

---

### Tabelas Auxiliares

#### `M31USUARIO` - Profissionais/Usuarios do sistema

| Campo | Descricao |
|-------|-----------|
| `A31COD` | ID (PK) |
| `A31FKI115COD` | FK para `I115CLIENTE_FORNENCEDOR` (nome do profissional) |
| `A31CRM` | Registro CRM |
| `A31APELIDO` | Apelido |

> **Nota:** O nome do profissional nao esta diretamente em `M31USUARIO`. E obtido via JOIN com `I115CLIENTE_FORNENCEDOR` usando `A31FKI115COD`.

#### `F34MEDICOS` - Medicos

| Campo | Descricao |
|-------|-----------|
| `A34COD` | ID (PK) |
| `A34FKI115COD` | FK para `I115CLIENTE_FORNENCEDOR` |
| `A34CRM` | CRM |
| `A34ESPECIALIDADE` | Especialidade |

---

### Tabelas mapeadas mas ainda nao implementadas

| Tabela | Descricao |
|--------|-----------|
| `M50ATENDIMENTO_TEXTO` | Historico geral do paciente (nao ligado a consulta) |
| `M87GESTACAO` | Dados de gestacao |
| `M88GESTACAO_EVOLUCAO` | Evolucao da gestacao |
| `M89GESTACAO_FILHOS` | Filhos da gestacao |
| `M60TIPO_PARTO` | Tipos de parto |
| `M250DOCUMENTOS_OLE` | Documentos OLE/PDFs (ligados a blobs em `C:\Genesis\Medicine\Dados`) |
| `F1PRODUTO` | Produtos |
| `M21PROCEDIMENTO` | Procedimentos |
| `M122TABELA_INTERNA_PROCEDIMENTO` | Tabela interna de procedimentos |

---

## Relacoes entre tabelas

```
M6PACIENTE (A6COD = ID do sistema)
    |
    +-- A6FKI115COD --> I115CLIENTE_FORNENCEDOR (A115COD)
    |                       |
    |                       +-- I128TELEFONES (A128FK115COD_CLI_FOR)
    |                       +-- I129END_ELETRONICO (A129FK115COD_CLI_FOR)
    |                       +-- I130DOC_NUMERICO (A130FK115COD_CLI_FOR)
    |                       +-- I131DOC_STRING (A131FK115COD_CLI_FOR)
    |                       +-- I135PESSOA_FISICA (A135FK115COD)
    |
    +-- A6FK5COD_CONVENIO --> M5CONVENIO (A5COD)
    |                           +-- A5FKI115COD --> I115CLIENTE_FORNENCEDOR (nome do convenio)
    |
    +-- A6COD <-- M27AGENDA (A27FK6COD_PACIENTE)
    |                |
    |                +-- A27FK31COD_USUARIO --> M31USUARIO (A31COD)
    |                |                            +-- A31FKI115COD --> I115CLIENTE_FORNENCEDOR (nome)
    |                |
    |                +-- A27COD <-- M51ATENDIMENTO_AGENDA_TEXTO (A51COD_AGENDA) ** EVOLUCOES **
    |
    +-- A6COD <-- M74PRECONSULTA (A74FK6COD_PACIENTE)
    +-- A6COD <-- M54RECEITA_PRESCRITA (A54FK6COD_PACIENTE)
    |                +-- A54COD <-- M55ITENS_PRESCRITOS (A55FK54COD_RECEITA)
    +-- A6COD <-- M171DOCUMENTOS (A171FK6COD_PACIENTE)
```

---

## Instalacao

### Requisitos

- Python 3.8+
- Acesso de rede ao servidor `recepcao-novo` na porta `3050`

### Dependencias

```bash
pip install fdb
```

### Arquivos necessarios

Os seguintes arquivos devem estar na mesma pasta do script:

| Arquivo | Descricao |
|---------|-----------|
| `paciente.py` | Script principal |
| `fbclient.dll` | Firebird client 64 bits |
| `ib_util.dll` | Dependencia Firebird |
| `icudt30.dll` | Dependencia ICU |
| `icuin30.dll` | Dependencia ICU |
| `icuuc30.dll` | Dependencia ICU |
| `msvcp80.dll` | Runtime MSVC |
| `msvcr80.dll` | Runtime MSVC |

---

## Uso

### Menu interativo

```bash
python paciente.py
```

```
============================================================
SISTEMA DE CONSULTA DE PACIENTES - Medicine Dream
============================================================

Opcoes:
1 - Buscar paciente por ID
2 - Buscar paciente por nome
3 - Listar ultimos pacientes
4 - Acessar prontuario por ID
0 - Sair
```

### Submenu de prontuario

```
1 - Historico de consultas (com evolucao)
2 - Evolucoes/Atendimentos
3 - Sinais vitais (pre-consulta)
4 - Receitas
5 - Documentos
0 - Voltar
```

### Uso como modulo

```python
from paciente import MedicineDB, exibir_paciente

with MedicineDB() as db:
    # Buscar paciente por ID
    paciente = db.buscar_paciente_por_id(50482)
    exibir_paciente(paciente)

    # Buscar por nome
    resultados = db.buscar_paciente_por_nome('Silva')

    # Prontuario
    consultas = db.buscar_consultas(50482)
    evolucoes = db.buscar_evolucoes(50482)
    preconsultas = db.buscar_preconsultas(50482)
    receitas = db.buscar_receitas(50482)
    documentos = db.buscar_documentos(50482)
```

---

## Licoes aprendidas durante o desenvolvimento

1. **DLL 32 vs 64 bits**: A DLL `fbclient.dll` que acompanha o Medicine Dream e 32 bits. Python 64 bits requer a versao 64 bits da DLL (obtida do Firebird embedded).

2. **Dois IDs de paciente**: O sistema usa `A6COD` (M6PACIENTE) como ID visivel. O `A115COD` (I115CLIENTE_FORNENCEDOR) e uma chave interna diferente. Sempre buscar por `A6COD`.

3. **Nome do profissional**: Nao esta diretamente na tabela `M31USUARIO`. Requer JOIN com `I115CLIENTE_FORNENCEDOR` via `A31FKI115COD`.

4. **Evolucoes de consulta**: Os textos de atendimento estao em `M51ATENDIMENTO_AGENDA_TEXTO`, ligados a `M27AGENDA` via `A51COD_AGENDA`. A tabela `M50ATENDIMENTO_TEXTO` e para historico geral do paciente, nao para registros diarios de consulta.

5. **Nome da tabela**: `I115CLIENTE_FORNENCEDOR` tem um "N" extra (FORNE**N**CEDOR, nao FORNECEDOR).

---

## Proximos passos

- [ ] Implementar busca de procedimentos (`F1PRODUTO`, `M21PROCEDIMENTO`, `M122TABELA_INTERNA_PROCEDIMENTO`)
- [ ] Implementar dados de gestacao (`M87GESTACAO`, `M88GESTACAO_EVOLUCAO`, `M89GESTACAO_FILHOS`)
- [ ] Extrair PDFs de `M250DOCUMENTOS_OLE` (blobs em `C:\Genesis\Medicine\Dados`)
- [ ] Investigar onde ficam os textos de consultas recentes (pos-2021)
- [ ] Mapear tabelas de situacao de agenda para confirmar codigos
- [ ] Adicionar filtro por data nas consultas e evolucoes
- [ ] Criar interface web (Flask/FastAPI) para consultas
- [ ] Exportar dados do paciente para PDF/relatorio
