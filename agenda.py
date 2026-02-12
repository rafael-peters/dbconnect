"""
Queries de agenda/consultas para o dashboard - Medicine Dream
"""

import fdb
from datetime import time as dt_time
from paciente import CONFIG


def _time_to_minutes(t):
    """Converte time para minutos (int). Retorna None se nulo."""
    if t is None:
        return None
    if isinstance(t, dt_time):
        return t.hour * 60 + t.minute
    return None


SITUACOES = {
    1: 'Agendado', 2: 'Na Fila', 3: 'Em Atendimento', 4: 'Executado',
    6: 'Cancelado', 7: 'Anotacao', 8: 'Estornado', 10: 'Excluido', 11: 'Nao Compareceu'
}


class AgendaDB:
    def __init__(self):
        self.conn = None

    def conectar(self):
        self.conn = fdb.connect(**CONFIG)
        return self

    def desconectar(self):
        if self.conn:
            self.conn.close()

    def __enter__(self):
        return self.conectar()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.desconectar()

    def agenda_dia(self, data=None, profissional=None):
        """Agenda completa do dia"""
        cursor = self.conn.cursor()

        sql = """
            SELECT
                a.A27COD,
                a.A27HORA_INI_AGENDA,
                p.A6COD AS PACIENTE_ID,
                pc.A115NOME AS PACIENTE,
                uc.A115NOME AS PROFISSIONAL,
                s.A84NOME AS SITUACAO,
                a.A27FK84COD_SITUACAO AS SITUACAO_ID,
                a.A27HORA_ENTROU_NA_FILA,
                a.A27TEMPO_NA_FILA,
                a.A27HORA_INI_ATENDIMENTO,
                a.A27TEMPO_ATENDIMENTO,
                a.A27OBSERVACAO,
                (SELECT LIST(DISTINCT pr.A21ALIASES, ', ')
                 FROM M28PROCEDIMENTO_AGENDA pa
                 LEFT JOIN M21PROCEDIMENTO pr ON pa.A28FK21COD_PROCEDIMENTO = pr.A21COD
                 WHERE pa.A28FK27COD_AGENDA = a.A27COD
                 AND pr.A21ALIASES IS NOT NULL
                ) AS PROCEDIMENTO,
                a.A27TEMPO_AGENDA
            FROM M27AGENDA a
            INNER JOIN M6PACIENTE p ON a.A27FK6COD_PACIENTE = p.A6COD
            INNER JOIN I115CLIENTE_FORNENCEDOR pc ON p.A6FKI115COD = pc.A115COD
            LEFT JOIN M31USUARIO u ON a.A27FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            LEFT JOIN M84SITUACAO_PROCEDIMENTO s ON a.A27FK84COD_SITUACAO = s.A84COD
            WHERE a.A27DATA = COALESCE(?, CURRENT_DATE)
              AND a.A27FK6COD_PACIENTE IS NOT NULL
        """
        params = [data]

        if profissional:
            sql += " AND a.A27FK31COD_USUARIO = ?"
            params.append(profissional)

        sql += " ORDER BY a.A27HORA_INI_AGENDA"

        cursor.execute(sql, params)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'id': row[0],
                'hora': row[1],
                'paciente_id': row[2],
                'paciente': row[3],
                'profissional': row[4],
                'situacao': row[5],
                'situacao_id': row[6],
                'hora_fila': row[7],
                'tempo_fila': _time_to_minutes(row[8]),
                'hora_atendimento': row[9],
                'tempo_atendimento': _time_to_minutes(row[10]),
                'observacao': row[11],
                'procedimento': row[12],
                'duracao': _time_to_minutes(row[13])
            })
        cursor.close()
        return resultado

    def agenda_semana(self, data_ref=None, profissional=None):
        """Agenda da semana inteira (seg-sab) para visualizacao calendario.
        data_ref: qualquer data da semana desejada (default: hoje)"""
        cursor = self.conn.cursor()

        # Calcular segunda-feira da semana no SQL
        # EXTRACT(WEEKDAY FROM date) retorna 0=domingo..6=sabado no Firebird
        sql = """
            SELECT
                a.A27DATA,
                a.A27HORA_INI_AGENDA,
                a.A27TEMPO_AGENDA,
                p.A6COD AS PACIENTE_ID,
                pc.A115NOME AS PACIENTE,
                uc.A115NOME AS PROFISSIONAL,
                s.A84NOME AS SITUACAO,
                a.A27FK84COD_SITUACAO AS SITUACAO_ID,
                (SELECT LIST(DISTINCT pr.A21ALIASES, ', ')
                 FROM M28PROCEDIMENTO_AGENDA pa
                 LEFT JOIN M21PROCEDIMENTO pr ON pa.A28FK21COD_PROCEDIMENTO = pr.A21COD
                 WHERE pa.A28FK27COD_AGENDA = a.A27COD
                 AND pr.A21ALIASES IS NOT NULL
                ) AS PROCEDIMENTO,
                a.A27HORA_ENTROU_NA_FILA,
                a.A27TEMPO_NA_FILA,
                a.A27HORA_INI_ATENDIMENTO,
                a.A27TEMPO_ATENDIMENTO,
                a.A27OBSERVACAO
            FROM M27AGENDA a
            INNER JOIN M6PACIENTE p ON a.A27FK6COD_PACIENTE = p.A6COD
            INNER JOIN I115CLIENTE_FORNENCEDOR pc ON p.A6FKI115COD = pc.A115COD
            LEFT JOIN M31USUARIO u ON a.A27FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            LEFT JOIN M84SITUACAO_PROCEDIMENTO s ON a.A27FK84COD_SITUACAO = s.A84COD
            WHERE a.A27DATA BETWEEN
                DATEADD(-EXTRACT(WEEKDAY FROM COALESCE(?, CURRENT_DATE)) + 1 DAY TO COALESCE(?, CURRENT_DATE))
                AND
                DATEADD(-EXTRACT(WEEKDAY FROM COALESCE(?, CURRENT_DATE)) + 7 DAY TO COALESCE(?, CURRENT_DATE))
              AND a.A27FK6COD_PACIENTE IS NOT NULL
        """
        params = [data_ref, data_ref, data_ref, data_ref]

        if profissional:
            sql += " AND a.A27FK31COD_USUARIO = ?"
            params.append(profissional)

        sql += " ORDER BY a.A27DATA, a.A27HORA_INI_AGENDA"

        cursor.execute(sql, params)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'data': row[0],
                'hora': row[1],
                'duracao': _time_to_minutes(row[2]) or 15,
                'paciente_id': row[3],
                'paciente': row[4],
                'profissional': row[5],
                'situacao': row[6],
                'situacao_id': row[7],
                'procedimento': row[8],
                'hora_fila': row[9],
                'tempo_fila': _time_to_minutes(row[10]),
                'hora_atendimento': row[11],
                'tempo_atendimento': _time_to_minutes(row[12]),
                'observacao': row[13]
            })
        cursor.close()
        return resultado

    def profissionais(self):
        """Lista profissionais distintos que tem agendamentos"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT a.A27FK31COD_USUARIO, uc.A115NOME
            FROM M27AGENDA a
            LEFT JOIN M31USUARIO u ON a.A27FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            WHERE a.A27FK31COD_USUARIO IS NOT NULL
              AND uc.A115NOME IS NOT NULL
            ORDER BY uc.A115NOME
        """)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({'id': row[0], 'nome': row[1]})
        cursor.close()
        return resultado

    def resumo_dia(self, data=None):
        """Cards resumo do dia - contagens por situacao"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                COUNT(*) AS TOTAL,
                SUM(CASE WHEN a.A27FK84COD_SITUACAO = 4 THEN 1 ELSE 0 END) AS EXECUTADOS,
                SUM(CASE WHEN a.A27FK84COD_SITUACAO = 1 THEN 1 ELSE 0 END) AS AGENDADOS,
                SUM(CASE WHEN a.A27FK84COD_SITUACAO = 2 THEN 1 ELSE 0 END) AS NA_FILA,
                SUM(CASE WHEN a.A27FK84COD_SITUACAO = 11 THEN 1 ELSE 0 END) AS NAO_COMPARECEU,
                SUM(CASE WHEN a.A27FK84COD_SITUACAO = 6 THEN 1 ELSE 0 END) AS CANCELADOS
            FROM M27AGENDA a
            WHERE a.A27DATA = COALESCE(?, CURRENT_DATE)
              AND a.A27FK6COD_PACIENTE IS NOT NULL
        """, (data,))

        row = cursor.fetchone()
        cursor.close()
        if row:
            return {
                'total': row[0] or 0,
                'executados': row[1] or 0,
                'agendados': row[2] or 0,
                'na_fila': row[3] or 0,
                'nao_compareceu': row[4] or 0,
                'cancelados': row[5] or 0
            }
        return {'total': 0, 'executados': 0, 'agendados': 0, 'na_fila': 0, 'nao_compareceu': 0, 'cancelados': 0}

    def estatisticas_mensal(self, meses=6):
        """Consultas por mes - ultimos N meses"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                EXTRACT(YEAR FROM a.A27DATA) AS ANO,
                EXTRACT(MONTH FROM a.A27DATA) AS MES,
                COUNT(*) AS TOTAL,
                SUM(CASE WHEN a.A27FK84COD_SITUACAO = 4 THEN 1 ELSE 0 END) AS EXECUTADOS
            FROM M27AGENDA a
            WHERE a.A27DATA >= DATEADD(? MONTH TO CURRENT_DATE)
              AND a.A27FK6COD_PACIENTE IS NOT NULL
            GROUP BY EXTRACT(YEAR FROM a.A27DATA), EXTRACT(MONTH FROM a.A27DATA)
            ORDER BY 1, 2
        """, (-meses,))

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'ano': int(row[0]),
                'mes': int(row[1]),
                'total': row[2],
                'executados': row[3]
            })
        cursor.close()
        return resultado

    def proximos_agendados(self, limite=20):
        """Proximas consultas agendadas (futuras)"""
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT FIRST {int(limite)}
                a.A27DATA,
                a.A27HORA_INI_AGENDA,
                p.A6COD AS PACIENTE_ID,
                pc.A115NOME AS PACIENTE,
                uc.A115NOME AS PROFISSIONAL,
                (SELECT LIST(DISTINCT pr.A21ALIASES, ', ')
                 FROM M28PROCEDIMENTO_AGENDA pa
                 LEFT JOIN M21PROCEDIMENTO pr ON pa.A28FK21COD_PROCEDIMENTO = pr.A21COD
                 WHERE pa.A28FK27COD_AGENDA = a.A27COD
                 AND pr.A21ALIASES IS NOT NULL
                ) AS PROCEDIMENTO
            FROM M27AGENDA a
            INNER JOIN M6PACIENTE p ON a.A27FK6COD_PACIENTE = p.A6COD
            INNER JOIN I115CLIENTE_FORNENCEDOR pc ON p.A6FKI115COD = pc.A115COD
            LEFT JOIN M31USUARIO u ON a.A27FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            WHERE a.A27DATA >= CURRENT_DATE
              AND a.A27FK84COD_SITUACAO = 1
              AND a.A27FK6COD_PACIENTE IS NOT NULL
            ORDER BY a.A27DATA, a.A27HORA_INI_AGENDA
        """)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'data': row[0],
                'hora': row[1],
                'paciente_id': row[2],
                'paciente': row[3],
                'profissional': row[4],
                'procedimento': row[5]
            })
        cursor.close()
        return resultado

    def tempo_espera_medio(self, dias=30):
        """Tempo medio de espera por dia - ultimos N dias
        TEMPO_NA_FILA e TEMPO_ATENDIMENTO sao TIME, converter para minutos com EXTRACT"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                a.A27DATA,
                AVG(EXTRACT(HOUR FROM a.A27TEMPO_NA_FILA) * 60 + EXTRACT(MINUTE FROM a.A27TEMPO_NA_FILA)) AS TEMPO_MEDIO_FILA,
                AVG(EXTRACT(HOUR FROM a.A27TEMPO_ATENDIMENTO) * 60 + EXTRACT(MINUTE FROM a.A27TEMPO_ATENDIMENTO)) AS TEMPO_MEDIO_ATENDIMENTO,
                COUNT(*) AS TOTAL_PACIENTES
            FROM M27AGENDA a
            WHERE a.A27DATA >= DATEADD(? DAY TO CURRENT_DATE)
              AND a.A27FK84COD_SITUACAO = 4
              AND a.A27FK6COD_PACIENTE IS NOT NULL
              AND a.A27TEMPO_ATENDIMENTO IS NOT NULL
            GROUP BY a.A27DATA
            ORDER BY a.A27DATA
        """, (-dias,))

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'data': row[0],
                'tempo_medio_fila': float(row[1]) if row[1] else 0,
                'tempo_medio_atendimento': float(row[2]) if row[2] else 0,
                'total_pacientes': row[3]
            })
        cursor.close()
        return resultado

    def buscar_agenda(self, data_inicio, data_fim, profissional=None, situacao=None, limite=200):
        """Buscar agenda por range de datas com filtros"""
        cursor = self.conn.cursor()

        sql = f"""
            SELECT FIRST {int(limite)}
                a.A27DATA,
                a.A27HORA_INI_AGENDA,
                p.A6COD AS PACIENTE_ID,
                pc.A115NOME AS PACIENTE,
                uc.A115NOME AS PROFISSIONAL,
                s.A84NOME AS SITUACAO,
                a.A27FK84COD_SITUACAO AS SITUACAO_ID,
                a.A27OBSERVACAO,
                (SELECT LIST(DISTINCT pr.A21ALIASES, ', ')
                 FROM M28PROCEDIMENTO_AGENDA pa
                 LEFT JOIN M21PROCEDIMENTO pr ON pa.A28FK21COD_PROCEDIMENTO = pr.A21COD
                 WHERE pa.A28FK27COD_AGENDA = a.A27COD
                 AND pr.A21ALIASES IS NOT NULL
                ) AS PROCEDIMENTO
            FROM M27AGENDA a
            INNER JOIN M6PACIENTE p ON a.A27FK6COD_PACIENTE = p.A6COD
            INNER JOIN I115CLIENTE_FORNENCEDOR pc ON p.A6FKI115COD = pc.A115COD
            LEFT JOIN M31USUARIO u ON a.A27FK31COD_USUARIO = u.A31COD
            LEFT JOIN I115CLIENTE_FORNENCEDOR uc ON u.A31FKI115COD = uc.A115COD
            LEFT JOIN M84SITUACAO_PROCEDIMENTO s ON a.A27FK84COD_SITUACAO = s.A84COD
            WHERE a.A27DATA BETWEEN ? AND ?
              AND a.A27FK6COD_PACIENTE IS NOT NULL
        """
        params = [data_inicio, data_fim]

        if profissional:
            sql += " AND a.A27FK31COD_USUARIO = ?"
            params.append(profissional)

        if situacao:
            sql += " AND a.A27FK84COD_SITUACAO = ?"
            params.append(situacao)

        sql += " ORDER BY a.A27DATA, a.A27HORA_INI_AGENDA"

        cursor.execute(sql, params)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'data': row[0],
                'hora': row[1],
                'paciente_id': row[2],
                'paciente': row[3],
                'profissional': row[4],
                'situacao': row[5],
                'situacao_id': row[6],
                'observacao': row[7],
                'procedimento': row[8]
            })
        cursor.close()
        return resultado
