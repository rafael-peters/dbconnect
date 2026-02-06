"""
Script para buscar dados completos de pacientes - Medicine Dream
"""

import os
import fdb
from datetime import datetime, time

# Carregar DLL do Firebird client (64 bits) relativa ao script
_dir = os.path.dirname(os.path.abspath(__file__))
fdb.load_api(os.path.join(_dir, 'fbclient.dll'))

CONFIG = {
    'host': 'recepcao-novo',
    'port': 3050,
    'database': r'C:\Genesis\Medicine\Dados\Medicine.fdb',
    'user': 'EXTERNO',
    'password': 'cachorro1410',
    'charset': 'WIN1252'
}

# PDFs ficam em bancos Firebird separados (shards)
# Formula: blob_db_num = (blob_id // 5000) + 1
# Caminho: BLOB_BASE_PATH\Medicine_blob{N}.fdb
BLOB_BASE_PATH = r'C:\Genesis\Medicine\Dados'
BLOB_CONFIG = {
    'user': 'SYSDBA',
    'password': 'masterkey',
    'charset': 'WIN1252'
}

# Mapeamento de tipos de documentos
TIPOS_DOCUMENTO = {
    '1': 'CPF',
    '2': 'CNPJ',
    '101': 'RG',
    '102': 'CNH',
    '103': 'CTPS',
}

# Mapeamento de tipos de telefone
TIPOS_TELEFONE = {
    '1': 'Celular',
    '2': 'Residencial',
    '3': 'Comercial',
    '4': 'Recado',
}

# Mapeamento de situacoes de agenda
SITUACOES_AGENDA = {
    1: 'Agendado',
    2: 'Confirmado',
    3: 'Na fila',
    4: 'Atendido',
    5: 'Cancelado',
    6: 'Faltou',
    7: 'Remarcado',
    8: 'Em atendimento',
    9: 'Aguardando',
    10: 'Finalizado',
}


class MedicineDB:
    def __init__(self):
        self.conn = None

    def conectar(self):
        """Estabelece conexao com o banco"""
        self.conn = fdb.connect(**CONFIG)
        return self

    def desconectar(self):
        """Fecha conexao"""
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self.conectar()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.desconectar()

    # ==================== PACIENTE ====================

    def buscar_paciente_por_id(self, id_paciente):
        """Busca paciente pelo ID do paciente (A6COD)"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT
                p.A6COD,
                cf.A115COD,
                cf.A115NOME,
                cf.A115ENDERECO,
                cf.A115END_NUMERO,
                cf.A115END_COMPLEMENTO,
                cf.A115END_BAIRRO,
                cf.A115CEP,
                pf.A135DATA_NASCIMENTO,
                pf.A135NOME_MAE,
                pf.A135NOME_PAI,
                pf.A135APELIDO,
                p.A6MATRICULA,
                p.A6GRUPO_SANGUINEO,
                p.A6FATOR_RH,
                p.A6DATA_HORA_CADASTRO,
                conv_cli.A115NOME AS CONVENIO_NOME,
                p.A6FK5COD_CONVENIO
            FROM M6PACIENTE p
            INNER JOIN I115CLIENTE_FORNENCEDOR cf ON p.A6FKI115COD = cf.A115COD
            LEFT JOIN I135PESSOA_FISICA pf ON cf.A115COD = pf.A135FK115COD
            LEFT JOIN M5CONVENIO conv ON p.A6FK5COD_CONVENIO = conv.A5COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR conv_cli ON conv.A5FKI115COD = conv_cli.A115COD
            WHERE p.A6COD = ?
        """, (id_paciente,))

        row = cursor.fetchone()
        if not row:
            return None

        id_cliente = row[1]

        paciente = {
            'id': row[0],
            'id_cliente': row[1],
            'nome': row[2],
            'endereco': {
                'logradouro': row[3],
                'numero': row[4],
                'complemento': row[5],
                'bairro': row[6],
                'cep': row[7]
            },
            'data_nascimento': row[8],
            'nome_mae': row[9],
            'nome_pai': row[10],
            'apelido': row[11],
            'matricula': row[12],
            'tipo_sanguineo': f"{row[13]}{row[14]}" if row[13] else None,
            'data_cadastro': row[15],
            'convenio': row[16],
            'convenio_id': row[17],
            'telefones': [],
            'emails': [],
            'documentos': {}
        }

        # Telefones
        cursor.execute("""
            SELECT A128NUMERO, A128TIPO, A128COD_AREA, A128CONTATO
            FROM I128TELEFONES
            WHERE A128FK115COD_CLI_FOR = ?
        """, (id_cliente,))

        for tel in cursor.fetchall():
            paciente['telefones'].append({
                'numero': f"({tel[2]}) {tel[0]}" if tel[2] else tel[0],
                'tipo': tel[1],
                'contato': tel[3]
            })

        # Emails
        cursor.execute("""
            SELECT A129ENDERECO, A129TIPO, A129CONTATO
            FROM I129END_ELETRONICO
            WHERE A129FK115COD_CLI_FOR = ?
        """, (id_cliente,))

        for email in cursor.fetchall():
            paciente['emails'].append({
                'endereco': email[0],
                'tipo': email[1],
                'contato': email[2]
            })

        # Documentos numericos
        cursor.execute("""
            SELECT A130TIPO, A130DOCUMENTO
            FROM I130DOC_NUMERICO
            WHERE A130FK115COD_CLI_FOR = ?
        """, (id_cliente,))

        for doc in cursor.fetchall():
            tipo = doc[0] or 'OUTRO'
            paciente['documentos'][f'NUM_{tipo}'] = doc[1]

        # Documentos string
        cursor.execute("""
            SELECT A131TIPO, A131DOCUMENTO
            FROM I131DOC_STRING
            WHERE A131FK115COD_CLI_FOR = ?
        """, (id_cliente,))

        for doc in cursor.fetchall():
            tipo = doc[0] or 'OUTRO'
            paciente['documentos'][f'STR_{tipo}'] = doc[1]

        cursor.close()
        return paciente

    def buscar_paciente_por_nome(self, nome):
        """Busca pacientes pelo nome (parcial)"""
        cursor = self.conn.cursor()

        cursor.execute("""
            SELECT FIRST 20
                p.A6COD,
                cf.A115NOME,
                pf.A135DATA_NASCIMENTO
            FROM M6PACIENTE p
            INNER JOIN I115CLIENTE_FORNENCEDOR cf ON p.A6FKI115COD = cf.A115COD
            LEFT JOIN I135PESSOA_FISICA pf ON cf.A115COD = pf.A135FK115COD
            WHERE UPPER(cf.A115NOME) CONTAINING UPPER(?)
            ORDER BY cf.A115NOME
        """, (nome,))

        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'id': row[0],
                'nome': row[1],
                'data_nascimento': row[2]
            })

        cursor.close()
        return resultados

    def listar_pacientes(self, limite=10):
        """Lista os ultimos pacientes cadastrados"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                p.A6COD,
                cf.A115NOME,
                pf.A135DATA_NASCIMENTO,
                p.A6DATA_HORA_CADASTRO
            FROM M6PACIENTE p
            INNER JOIN I115CLIENTE_FORNENCEDOR cf ON p.A6FKI115COD = cf.A115COD
            LEFT JOIN I135PESSOA_FISICA pf ON cf.A115COD = pf.A135FK115COD
            WHERE cf.A115NOME IS NOT NULL
            ORDER BY p.A6DATA_HORA_CADASTRO DESC
        """)

        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                'id': row[0],
                'nome': row[1],
                'data_nascimento': row[2],
                'data_cadastro': row[3]
            })

        cursor.close()
        return resultados

    # ==================== PRONTUARIO ====================

    def buscar_consultas(self, id_paciente, limite=20):
        """Busca historico de consultas/agendamentos do paciente"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                a.A27COD,
                a.A27DATA,
                a.A27HORA_INI_AGENDA,
                uc.A115NOME AS PROFISSIONAL,
                a.A27FK84COD_SITUACAO,
                a.A27OBSERVACAO,
                a.A27ANOTACAO
            FROM M27AGENDA a
            LEFT JOIN M31USUARIO u ON a.A27FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            WHERE a.A27FK6COD_PACIENTE = ?
            ORDER BY a.A27DATA DESC, a.A27HORA_INI_AGENDA DESC
        """, (id_paciente,))

        consultas = []
        for row in cursor.fetchall():
            consulta = {
                'id': row[0],
                'data': row[1],
                'hora': row[2],
                'profissional': row[3],
                'situacao': row[4],
                'observacao': row[5],
                'anotacao': row[6],
                'textos': []  # Textos de atendimento da consulta
            }

            # Buscar textos de atendimento desta consulta (M51)
            cursor2 = self.conn.cursor()
            cursor2.execute("""
                SELECT A51ITEM_PALHETA, A51TEXTO
                FROM M51ATENDIMENTO_AGENDA_TEXTO
                WHERE A51COD_AGENDA = ?
                ORDER BY A51ITEM_PALHETA
            """, (row[0],))

            for texto_row in cursor2.fetchall():
                if texto_row[1]:  # Se tem texto
                    consulta['textos'].append({
                        'palheta': texto_row[0],
                        'texto': texto_row[1]
                    })
            cursor2.close()

            consultas.append(consulta)

        cursor.close()
        return consultas

    def buscar_evolucoes(self, id_paciente, limite=20):
        """Busca evolucoes/textos de atendimento do paciente (M51)"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                a.A27COD,
                a.A27DATA,
                a.A27HORA_INI_AGENDA,
                uc.A115NOME AS PROFISSIONAL,
                t.A51ITEM_PALHETA,
                t.A51TEXTO
            FROM M51ATENDIMENTO_AGENDA_TEXTO t
            INNER JOIN M27AGENDA a ON t.A51COD_AGENDA = a.A27COD
            LEFT JOIN M31USUARIO u ON a.A27FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            WHERE a.A27FK6COD_PACIENTE = ?
            AND t.A51TEXTO IS NOT NULL
            ORDER BY a.A27DATA DESC, a.A27HORA_INI_AGENDA DESC
        """, (id_paciente,))

        evolucoes = []
        for row in cursor.fetchall():
            evolucoes.append({
                'id_agenda': row[0],
                'data': row[1],
                'hora': row[2],
                'profissional': row[3],
                'palheta': row[4],
                'texto': row[5]
            })

        cursor.close()
        return evolucoes

    def buscar_documentos(self, id_paciente, limite=20):
        """Busca documentos do prontuario do paciente"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                d.A171COD,
                d.A171DATA_HORA,
                uc.A115NOME AS PROFISSIONAL,
                d.A171DOCUMENTO
            FROM M171DOCUMENTOS d
            LEFT JOIN M31USUARIO u ON d.A171FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            WHERE d.A171FK6COD_PACIENTE = ?
            ORDER BY d.A171DATA_HORA DESC
        """, (id_paciente,))

        documentos = []
        for row in cursor.fetchall():
            documentos.append({
                'id': row[0],
                'data_hora': row[1],
                'profissional': row[2],
                'conteudo': row[3]
            })

        cursor.close()
        return documentos

    def buscar_preconsultas(self, id_paciente, limite=20):
        """Busca pre-consultas (sinais vitais) do paciente"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                A74DATA,
                A74HORA,
                A74PRESSAO_ARTERIAL_MAX,
                A47PRESSAO_ARTERIAL_MIN,
                A74PESO,
                A74ALTURA,
                A74CA_IMC,
                A74FREQ_CARDIACA,
                A74FREQ_RESPIRATORIA,
                A74TEMPERATURA,
                A74SATURACAO,
                A74HGT
            FROM M74PRECONSULTA
            WHERE A74FK6COD_PACIENTE = ?
            ORDER BY A74DATA DESC, A74HORA DESC
        """, (id_paciente,))

        preconsultas = []
        for row in cursor.fetchall():
            preconsultas.append({
                'data': row[0],
                'hora': row[1],
                'pa_max': row[2],
                'pa_min': row[3],
                'peso': row[4],
                'altura': row[5],
                'imc': row[6],
                'freq_cardiaca': row[7],
                'freq_respiratoria': row[8],
                'temperatura': row[9],
                'saturacao': row[10],
                'hgt': row[11]
            })

        cursor.close()
        return preconsultas

    def buscar_receitas(self, id_paciente, limite=20):
        """Busca receitas prescritas do paciente"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                r.A54COD,
                r.A54DATA_HORA,
                uc.A115NOME AS PROFISSIONAL,
                r.A54OBSERVACAO
            FROM M54RECEITA_PRESCRITA r
            LEFT JOIN M31USUARIO u ON r.A54FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            WHERE r.A54FK6COD_PACIENTE = ?
            ORDER BY r.A54DATA_HORA DESC
        """, (id_paciente,))

        receitas = []
        for row in cursor.fetchall():
            receita = {
                'id': row[0],
                'data_hora': row[1],
                'profissional': row[2],
                'observacao': row[3],
                'itens': []
            }

            # Buscar itens da receita
            cursor2 = self.conn.cursor()
            cursor2.execute("""
                SELECT A55DESCRICAO_MEDICAMENTO, A55POSOLOGIA, A55QT_PRESCRITO
                FROM M55ITENS_PRESCRITOS
                WHERE A55FK54COD_RECEITA = ?
                ORDER BY A55ITEM
            """, (row[0],))

            for item in cursor2.fetchall():
                receita['itens'].append({
                    'medicamento': item[0],
                    'posologia': item[1],
                    'quantidade': item[2]
                })
            cursor2.close()

            receitas.append(receita)

        cursor.close()
        return receitas

    # ==================== PDFs (M250/M999 BLOBS) ====================

    def buscar_pdfs(self, id_paciente, limite=50):
        """Busca lista de PDFs do paciente (M250DOCUMENTOS_OLE)"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                d.A250ITEM,
                d.A250NOME,
                d.A250DATA_INSERCAO,
                d.A259FK999COD_BLOB,
                d.A250TIPO_DOCUMENTO
            FROM M250DOCUMENTOS_OLE d
            WHERE d.A250FK6COD_PACIENTE = ?
            ORDER BY d.A250DATA_INSERCAO DESC
        """, (id_paciente,))

        pdfs = []
        for row in cursor.fetchall():
            pdfs.append({
                'id': row[0],
                'nome': row[1],
                'data': row[2],
                'blob_id': row[3],
                'tipo': row[4]
            })

        cursor.close()
        return pdfs

    # ==================== FINANCEIRO (I106 LANCAMENTOS) ====================

    def buscar_lancamentos(self, id_paciente, limite=50):
        """Busca lancamentos financeiros do paciente"""
        cursor = self.conn.cursor()

        cursor.execute(f"""
            SELECT FIRST {limite}
                l.A106COD,
                l.A106DATA,
                l.A106VALOR,
                l.A106TEXTO,
                l.A106CATIPO,
                l.A106NUM_DOCUMENTO,
                l.A106OBSERVACAO,
                l.A106DATA_REALIZADO,
                l.A106VALOR_REALIZADO,
                l.A106VAL_DESCONTO,
                l.A106VAL_ACRESCIMO,
                c.A104NOME
            FROM I106LANCAMENTO l
            LEFT JOIN I104CONTAS c ON l.A106FK104COD_CONTA = c.A104COD
            INNER JOIN I115CLIENTE_FORNENCEDOR cf ON l.A106FK115COD_CLI_FORN = cf.A115COD
            INNER JOIN M6PACIENTE p ON p.A6FKI115COD = cf.A115COD
            WHERE p.A6COD = ?
            AND l.A106ELIMINADO = 'N'
            ORDER BY l.A106DATA DESC, l.A106COD DESC
        """, (id_paciente,))

        lancamentos = []
        for row in cursor.fetchall():
            lancamentos.append({
                'id': row[0],
                'data': row[1],
                'valor': float(row[2]) if row[2] else 0,
                'texto': row[3],
                'tipo': row[4],
                'num_documento': row[5],
                'observacao': row[6],
                'data_realizado': row[7],
                'valor_realizado': float(row[8]) if row[8] else None,
                'desconto': float(row[9]) if row[9] else None,
                'acrescimo': float(row[10]) if row[10] else None,
                'conta': row[11]
            })

        cursor.close()
        return lancamentos

    def buscar_blob_pdf(self, blob_id):
        """Conecta ao banco blob correto e retorna os bytes do PDF"""
        blob_db_num = (blob_id // 5000) + 1
        blob_db_path = os.path.join(BLOB_BASE_PATH, f'Medicine_blob{blob_db_num}.fdb')

        conn_blob = fdb.connect(
            host=CONFIG['host'],
            port=CONFIG['port'],
            database=blob_db_path,
            user=BLOB_CONFIG['user'],
            password=BLOB_CONFIG['password'],
            charset=BLOB_CONFIG['charset']
        )

        try:
            cursor = conn_blob.cursor()
            cursor.execute("""
                SELECT A999BLOB
                FROM M999BLOBS
                WHERE A999COD = ?
            """, (blob_id,))

            row = cursor.fetchone()
            if row and row[0]:
                blob = row[0]
                if hasattr(blob, 'read'):
                    return blob.read()
                return bytes(blob)
            return None
        finally:
            conn_blob.close()


# ==================== FORMATACAO ====================

def formatar_data(data):
    """Formata data para exibicao"""
    if data:
        if isinstance(data, datetime):
            return data.strftime('%d/%m/%Y')
        try:
            return data.strftime('%d/%m/%Y')
        except:
            return str(data)
    return '-'


def formatar_hora(hora):
    """Formata hora para exibicao"""
    if hora:
        if isinstance(hora, time):
            return hora.strftime('%H:%M')
        if isinstance(hora, datetime):
            return hora.strftime('%H:%M')
        try:
            return hora.strftime('%H:%M')
        except:
            return str(hora)[:5]
    return '-'


def formatar_data_hora(dt):
    """Formata data e hora para exibicao"""
    if dt:
        if isinstance(dt, datetime):
            return dt.strftime('%d/%m/%Y %H:%M')
        try:
            return dt.strftime('%d/%m/%Y %H:%M')
        except:
            return str(dt)
    return '-'


def exibir_paciente(paciente):
    """Exibe dados do paciente formatados"""
    print("\n" + "=" * 60)
    print(f"PACIENTE: {paciente['nome']}")
    print("=" * 60)

    print(f"\nID Paciente: {paciente['id']}")
    if paciente['apelido']:
        print(f"Apelido: {paciente['apelido']}")
    print(f"Data Nascimento: {formatar_data(paciente['data_nascimento'])}")

    if paciente['nome_mae']:
        print(f"Mae: {paciente['nome_mae']}")
    if paciente['nome_pai']:
        print(f"Pai: {paciente['nome_pai']}")

    if paciente['tipo_sanguineo']:
        print(f"Tipo Sanguineo: {paciente['tipo_sanguineo']}")

    # Endereco
    end = paciente['endereco']
    if end['logradouro']:
        endereco_completo = end['logradouro']
        if end['numero']:
            endereco_completo += f", {end['numero']}"
        if end['complemento']:
            endereco_completo += f" - {end['complemento']}"
        if end['bairro']:
            endereco_completo += f" | {end['bairro']}"
        if end['cep']:
            endereco_completo += f" | CEP: {end['cep']}"
        print(f"\nEndereco: {endereco_completo}")

    # Telefones
    if paciente['telefones']:
        print("\nTelefones:")
        for tel in paciente['telefones']:
            tipo_nome = TIPOS_TELEFONE.get(str(tel['tipo']), tel['tipo']) if tel['tipo'] else ""
            tipo_str = f" ({tipo_nome})" if tipo_nome else ""
            contato = f" - {tel['contato']}" if tel['contato'] else ""
            print(f"  - {tel['numero']}{tipo_str}{contato}")

    # Emails
    if paciente['emails']:
        print("\nEmails:")
        for email in paciente['emails']:
            tipo = f" ({email['tipo']})" if email['tipo'] else ""
            print(f"  - {email['endereco']}{tipo}")

    # Documentos
    if paciente['documentos']:
        print("\nDocumentos:")
        for tipo, valor in paciente['documentos'].items():
            tipo_limpo = tipo.replace('NUM_', '').replace('STR_', '')
            tipo_nome = TIPOS_DOCUMENTO.get(tipo_limpo, tipo_limpo)
            if tipo_nome == 'CPF' and valor:
                v = str(int(valor)).zfill(11)
                valor = f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
            print(f"  - {tipo_nome}: {valor}")

    # Convenio
    if paciente['convenio']:
        print(f"\nConvenio: {paciente['convenio']}")

    print(f"\nCadastrado em: {formatar_data(paciente['data_cadastro'])}")


def exibir_consultas(consultas, mostrar_textos=True):
    """Exibe lista de consultas"""
    print("\n" + "=" * 70)
    print("HISTORICO DE CONSULTAS")
    print("=" * 70)

    if not consultas:
        print("Nenhuma consulta encontrada.")
        return

    for c in consultas:
        situacao = SITUACOES_AGENDA.get(c['situacao'], c['situacao'])
        print(f"\n{formatar_data(c['data'])} {formatar_hora(c['hora'])} | {c['profissional'] or '-'}")
        print(f"  Situacao: {situacao}")
        if c['observacao']:
            print(f"  Obs: {c['observacao'][:60]}...")
        if c['anotacao']:
            print(f"  Anotacao: {c['anotacao'][:60]}...")

        # Mostrar textos de atendimento da consulta
        if mostrar_textos and c.get('textos'):
            print("  --- Evolucao/Atendimento ---")
            for t in c['textos']:
                texto = t['texto'].replace('\n', '\n    ')
                print(f"    {texto}")


def exibir_evolucoes(evolucoes):
    """Exibe lista de evolucoes/textos de atendimento"""
    print("\n" + "=" * 70)
    print("EVOLUCOES / TEXTOS DE ATENDIMENTO")
    print("=" * 70)

    if not evolucoes:
        print("Nenhuma evolucao encontrada.")
        return

    for e in evolucoes:
        print(f"\n{formatar_data(e['data'])} {formatar_hora(e['hora'])} | {e['profissional'] or '-'}")
        print("-" * 50)
        if e['texto']:
            print(e['texto'])


def exibir_preconsultas(preconsultas):
    """Exibe lista de pre-consultas (sinais vitais)"""
    print("\n" + "=" * 70)
    print("HISTORICO DE SINAIS VITAIS (PRE-CONSULTA)")
    print("=" * 70)

    if not preconsultas:
        print("Nenhuma pre-consulta encontrada.")
        return

    for p in preconsultas:
        print(f"\n{formatar_data(p['data'])} {formatar_hora(p['hora'])}")

        linha = []
        if p['pa_max'] and p['pa_min']:
            linha.append(f"PA: {p['pa_max']}x{p['pa_min']} mmHg")
        if p['freq_cardiaca']:
            linha.append(f"FC: {p['freq_cardiaca']} bpm")
        if p['freq_respiratoria']:
            linha.append(f"FR: {p['freq_respiratoria']} irpm")
        if linha:
            print(f"  {' | '.join(linha)}")

        linha2 = []
        if p['peso']:
            linha2.append(f"Peso: {p['peso']} kg")
        if p['altura']:
            linha2.append(f"Altura: {p['altura']} cm")
        if p['imc']:
            linha2.append(f"IMC: {p['imc']:.1f}")
        if linha2:
            print(f"  {' | '.join(linha2)}")

        linha3 = []
        if p['temperatura']:
            linha3.append(f"Temp: {p['temperatura']} C")
        if p['saturacao']:
            linha3.append(f"SpO2: {p['saturacao']}%")
        if p['hgt']:
            linha3.append(f"HGT: {p['hgt']} mg/dL")
        if linha3:
            print(f"  {' | '.join(linha3)}")


def exibir_receitas(receitas):
    """Exibe lista de receitas"""
    print("\n" + "=" * 70)
    print("HISTORICO DE RECEITAS")
    print("=" * 70)

    if not receitas:
        print("Nenhuma receita encontrada.")
        return

    for r in receitas:
        print(f"\n{formatar_data_hora(r['data_hora'])} | {r['profissional'] or '-'}")
        if r['observacao']:
            print(f"  Obs: {r['observacao']}")

        if r['itens']:
            print("  Medicamentos:")
            for item in r['itens']:
                med = item['medicamento'] or '-'
                pos = item['posologia'] or ''
                qt = f" (Qt: {item['quantidade']})" if item['quantidade'] else ""
                print(f"    - {med}")
                if pos:
                    print(f"      {pos}{qt}")


def exibir_documentos(documentos):
    """Exibe lista de documentos"""
    print("\n" + "=" * 70)
    print("DOCUMENTOS DO PRONTUARIO")
    print("=" * 70)

    if not documentos:
        print("Nenhum documento encontrado.")
        return

    for d in documentos:
        print(f"\n{formatar_data_hora(d['data_hora'])} | {d['profissional'] or '-'}")
        if d['conteudo']:
            # Limitar tamanho do conteudo
            conteudo = d['conteudo'][:200]
            if len(d['conteudo']) > 200:
                conteudo += "..."
            print(f"  {conteudo}")


# ==================== MENU PRINCIPAL ====================

def menu_prontuario(db, id_paciente, nome_paciente):
    """Submenu de prontuario"""
    while True:
        print(f"\n{'='*60}")
        print(f"PRONTUARIO: {nome_paciente} (ID: {id_paciente})")
        print("="*60)
        print("\n1 - Historico de consultas (com evolucao)")
        print("2 - Evolucoes/Atendimentos")
        print("3 - Sinais vitais (pre-consulta)")
        print("4 - Receitas")
        print("5 - Documentos")
        print("0 - Voltar")

        opcao = input("\nEscolha: ").strip()

        if opcao == '0':
            break

        elif opcao == '1':
            consultas = db.buscar_consultas(id_paciente)
            exibir_consultas(consultas, mostrar_textos=True)

        elif opcao == '2':
            evolucoes = db.buscar_evolucoes(id_paciente)
            exibir_evolucoes(evolucoes)

        elif opcao == '3':
            preconsultas = db.buscar_preconsultas(id_paciente)
            exibir_preconsultas(preconsultas)

        elif opcao == '4':
            receitas = db.buscar_receitas(id_paciente)
            exibir_receitas(receitas)

        elif opcao == '5':
            documentos = db.buscar_documentos(id_paciente)
            exibir_documentos(documentos)

        else:
            print("Opcao invalida.")


def main():
    print("=" * 60)
    print("SISTEMA DE CONSULTA DE PACIENTES - Medicine Dream")
    print("=" * 60)

    with MedicineDB() as db:
        while True:
            print("\nOpcoes:")
            print("1 - Buscar paciente por ID")
            print("2 - Buscar paciente por nome")
            print("3 - Listar ultimos pacientes")
            print("4 - Acessar prontuario por ID")
            print("0 - Sair")

            opcao = input("\nEscolha: ").strip()

            if opcao == '0':
                print("\nAte logo!")
                break

            elif opcao == '1':
                id_pac = input("Digite o ID do paciente: ").strip()
                if id_pac.isdigit():
                    paciente = db.buscar_paciente_por_id(int(id_pac))
                    if paciente:
                        exibir_paciente(paciente)
                    else:
                        print("Paciente nao encontrado.")
                else:
                    print("ID invalido.")

            elif opcao == '2':
                nome = input("Digite parte do nome: ").strip()
                if nome:
                    resultados = db.buscar_paciente_por_nome(nome)
                    if resultados:
                        print(f"\n{len(resultados)} paciente(s) encontrado(s):")
                        print("-" * 60)
                        for p in resultados:
                            nasc = formatar_data(p['data_nascimento'])
                            print(f"ID: {p['id']:>6} | {p['nome'][:40]:<40} | Nasc: {nasc}")

                        ver = input("\nDigite o ID para ver detalhes (ou Enter para voltar): ").strip()
                        if ver.isdigit():
                            paciente = db.buscar_paciente_por_id(int(ver))
                            if paciente:
                                exibir_paciente(paciente)

                                # Opcao de ver prontuario
                                pront = input("\nVer prontuario? (s/n): ").strip().lower()
                                if pront == 's':
                                    menu_prontuario(db, paciente['id'], paciente['nome'])
                    else:
                        print("Nenhum paciente encontrado.")

            elif opcao == '3':
                qtd = input("Quantos pacientes listar? (padrao 10): ").strip()
                limite = int(qtd) if qtd.isdigit() else 10
                resultados = db.listar_pacientes(limite)

                if resultados:
                    print(f"\nUltimos {len(resultados)} pacientes cadastrados:")
                    print("-" * 70)
                    for p in resultados:
                        nasc = formatar_data(p['data_nascimento'])
                        cad = formatar_data(p['data_cadastro'])
                        print(f"ID: {p['id']:>6} | {p['nome'][:35]:<35} | Nasc: {nasc} | Cad: {cad}")
                else:
                    print("Nenhum paciente encontrado.")

            elif opcao == '4':
                id_pac = input("Digite o ID do paciente: ").strip()
                if id_pac.isdigit():
                    paciente = db.buscar_paciente_por_id(int(id_pac))
                    if paciente:
                        menu_prontuario(db, paciente['id'], paciente['nome'])
                    else:
                        print("Paciente nao encontrado.")
                else:
                    print("ID invalido.")

            else:
                print("Opcao invalida.")


if __name__ == "__main__":
    main()
