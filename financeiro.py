"""
Queries financeiras para o dashboard de fluxo de caixa - Medicine Dream
"""

import fdb
from paciente import CONFIG


class FinanceiroDB:
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

    def resumo_mensal(self, meses=12):
        """Totais mensais agrupados por C/D/T - ultimos N meses"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                EXTRACT(YEAR FROM l.A106DATA) AS ANO,
                EXTRACT(MONTH FROM l.A106DATA) AS MES,
                l.A106CATIPO,
                COUNT(*) AS QT,
                SUM(l.A106VALOR) AS TOTAL
            FROM I106LANCAMENTO l
            WHERE l.A106ELIMINADO = 'N'
              AND l.A106REALIZADO = 'S'
              AND l.A106DATA >= DATEADD(? MONTH TO CURRENT_DATE)
            GROUP BY EXTRACT(YEAR FROM l.A106DATA),
                     EXTRACT(MONTH FROM l.A106DATA),
                     l.A106CATIPO
            ORDER BY 1, 2, 3
        """, (-meses,))

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'ano': int(row[0]),
                'mes': int(row[1]),
                'tipo': row[2],
                'quantidade': row[3],
                'total': float(row[4]) if row[4] else 0
            })
        cursor.close()
        return resultado

    def saldo_contas(self):
        """Saldo atual por conta (creditos - debitos realizados)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                c.A104COD,
                c.A104NOME,
                c.A104TIPO,
                COALESCE(SUM(CASE WHEN l.A106CATIPO = 'C' THEN l.A106VALOR ELSE 0 END), 0) AS CREDITOS,
                COALESCE(SUM(CASE WHEN l.A106CATIPO = 'D' THEN l.A106VALOR ELSE 0 END), 0) AS DEBITOS,
                COALESCE(SUM(CASE WHEN l.A106CATIPO = 'T' THEN l.A106VALOR ELSE 0 END), 0) AS TRANSF
            FROM I104CONTAS c
            LEFT JOIN I106LANCAMENTO l ON l.A106FK104COD_CONTA = c.A104COD
                AND l.A106REALIZADO = 'S'
                AND l.A106ELIMINADO = 'N'
            GROUP BY c.A104COD, c.A104NOME, c.A104TIPO
            HAVING COALESCE(SUM(CASE WHEN l.A106CATIPO = 'C' THEN l.A106VALOR ELSE 0 END), 0)
                 + COALESCE(SUM(CASE WHEN l.A106CATIPO = 'D' THEN l.A106VALOR ELSE 0 END), 0) > 0
            ORDER BY COALESCE(SUM(CASE WHEN l.A106CATIPO = 'C' THEN l.A106VALOR ELSE 0 END), 0)
                   - COALESCE(SUM(CASE WHEN l.A106CATIPO = 'D' THEN l.A106VALOR ELSE 0 END), 0) DESC
        """)

        resultado = []
        for row in cursor.fetchall():
            creditos = float(row[3])
            debitos = float(row[4])
            resultado.append({
                'conta_id': row[0],
                'nome': row[1],
                'tipo_conta': row[2],
                'total_creditos': creditos,
                'total_debitos': debitos,
                'saldo': creditos - debitos
            })
        cursor.close()
        return resultado

    def fluxo_diario(self, dias=30):
        """Fluxo de caixa diario - ultimos N dias"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                l.A106DATA,
                l.A106CATIPO,
                COUNT(*) AS QT,
                SUM(l.A106VALOR) AS TOTAL
            FROM I106LANCAMENTO l
            WHERE l.A106ELIMINADO = 'N'
              AND l.A106REALIZADO = 'S'
              AND l.A106DATA >= DATEADD(? DAY TO CURRENT_DATE)
              AND l.A106CATIPO IN ('C', 'D')
            GROUP BY l.A106DATA, l.A106CATIPO
            ORDER BY l.A106DATA, l.A106CATIPO
        """, (-dias,))

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'data': row[0],
                'tipo': row[1],
                'quantidade': row[2],
                'total': float(row[3]) if row[3] else 0
            })
        cursor.close()
        return resultado

    def lancamentos_pendentes(self):
        """Recebiveis e pagaveis pendentes (nao realizados)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                l.A106COD,
                l.A106DATA,
                l.A106VALOR,
                l.A106TEXTO,
                l.A106CATIPO,
                cf.A115NOME,
                c.A104NOME
            FROM I106LANCAMENTO l
            LEFT JOIN I115CLIENTE_FORNENCEDOR cf ON l.A106FK115COD_CLI_FORN = cf.A115COD
            LEFT JOIN I104CONTAS c ON l.A106FK104COD_CONTA = c.A104COD
            WHERE l.A106REALIZADO = 'N'
              AND l.A106ELIMINADO = 'N'
            ORDER BY l.A106DATA
        """)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'id': row[0],
                'data': row[1],
                'valor': float(row[2]) if row[2] else 0,
                'texto': row[3],
                'tipo': row[4],
                'cliente': row[5],
                'conta': row[6]
            })
        cursor.close()
        return resultado

    def despesas_recorrentes(self):
        """Lista despesas ciclicas/recorrentes"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                ci.A107COD,
                ci.A107TEXTO,
                ci.A107VALOR,
                ci.A107TIPO_CREDITO_DEBITO,
                ci.A107ATIVO,
                cf.A115NOME,
                ci.A107FREQUENCIA
            FROM I107CICLICOS ci
            LEFT JOIN I115CLIENTE_FORNENCEDOR cf ON ci.A107FK115COD_FORNECEDOR = cf.A115COD
            ORDER BY ci.A107ATIVO DESC, ci.A107VALOR DESC
        """)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'id': row[0],
                'nome': row[1],
                'valor': float(row[2]) if row[2] else 0,
                'tipo': row[3],
                'ativo': row[4],
                'fornecedor': row[5],
                'frequencia': row[6]
            })
        cursor.close()
        return resultado

    def lancamentos_recentes(self, limite=50):
        """Ultimos lancamentos (todos os tipos)"""
        cursor = self.conn.cursor()
        cursor.execute(f"""
            SELECT FIRST {int(limite)}
                l.A106COD,
                l.A106DATA,
                l.A106VALOR,
                l.A106TEXTO,
                l.A106CATIPO,
                l.A106REALIZADO,
                cf.A115NOME,
                c.A104NOME,
                l.A106NUM_DOCUMENTO,
                l.A106OBSERVACAO,
                (SELECT LIST(DISTINCT f1.A1NOME, ', ')
                 FROM M28PROCEDIMENTO_AGENDA pa
                 INNER JOIN M27AGENDA a ON pa.A28FK27COD_AGENDA = a.A27COD
                 LEFT JOIN M21PROCEDIMENTO pr ON pa.A28FK21COD_PROCEDIMENTO = pr.A21COD
                 LEFT JOIN F1PRODUTO f1 ON pr.A21FKF1COD_PRODUTO = f1.A1COD
                 INNER JOIN M6PACIENTE p ON a.A27FK6COD_PACIENTE = p.A6COD
                 INNER JOIN I115CLIENTE_FORNENCEDOR pcf ON p.A6FKI115COD = pcf.A115COD
                 WHERE pcf.A115COD = l.A106FK115COD_CLI_FORN
                 AND a.A27DATA = l.A106DATA
                 AND f1.A1NOME IS NOT NULL
                ) AS PROCEDIMENTOS
            FROM I106LANCAMENTO l
            LEFT JOIN I115CLIENTE_FORNENCEDOR cf ON l.A106FK115COD_CLI_FORN = cf.A115COD
            LEFT JOIN I104CONTAS c ON l.A106FK104COD_CONTA = c.A104COD
            WHERE l.A106ELIMINADO = 'N'
            ORDER BY l.A106DATA DESC, l.A106COD DESC
        """)

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'id': row[0],
                'data': row[1],
                'valor': float(row[2]) if row[2] else 0,
                'texto': row[3],
                'tipo': row[4],
                'status': row[5],
                'cliente': row[6],
                'conta': row[7],
                'num_documento': row[8],
                'observacao': row[9],
                'procedimentos': row[10]
            })
        cursor.close()
        return resultado

    def top_clientes(self, meses=12):
        """Top 20 maiores pagadores"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT FIRST 20
                cf.A115NOME,
                SUM(l.A106VALOR) AS TOTAL,
                COUNT(*) AS QT
            FROM I106LANCAMENTO l
            INNER JOIN I115CLIENTE_FORNENCEDOR cf ON l.A106FK115COD_CLI_FORN = cf.A115COD
            WHERE l.A106CATIPO = 'C'
              AND l.A106REALIZADO = 'S'
              AND l.A106ELIMINADO = 'N'
              AND l.A106DATA >= DATEADD(? MONTH TO CURRENT_DATE)
              AND cf.A115NOME IS NOT NULL
            GROUP BY cf.A115NOME
            ORDER BY SUM(l.A106VALOR) DESC
        """, (-meses,))

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'nome': row[0],
                'total': float(row[1]) if row[1] else 0,
                'quantidade': row[2]
            })
        cursor.close()
        return resultado

    def top_despesas(self, meses=12):
        """Top 20 maiores despesas por descricao"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT FIRST 20
                l.A106TEXTO,
                SUM(l.A106VALOR) AS TOTAL,
                COUNT(*) AS QT
            FROM I106LANCAMENTO l
            WHERE l.A106CATIPO = 'D'
              AND l.A106REALIZADO = 'S'
              AND l.A106ELIMINADO = 'N'
              AND l.A106DATA >= DATEADD(? MONTH TO CURRENT_DATE)
              AND l.A106TEXTO IS NOT NULL
            GROUP BY l.A106TEXTO
            ORDER BY SUM(l.A106VALOR) DESC
        """, (-meses,))

        resultado = []
        for row in cursor.fetchall():
            resultado.append({
                'nome': row[0],
                'total': float(row[1]) if row[1] else 0,
                'quantidade': row[2]
            })
        cursor.close()
        return resultado
