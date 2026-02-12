"""
Interface web para consulta de pacientes - Medicine Dream
Flask app com dark theme SPA
"""

import json
from decimal import Decimal
from datetime import datetime, date, time
from flask import Flask, jsonify, request, render_template_string, Response
from paciente import MedicineDB, SITUACOES_AGENDA, TIPOS_DOCUMENTO, TIPOS_TELEFONE
from financeiro import FinanceiroDB
from agenda import AgendaDB

app = Flask(__name__)

# Conexao global
db = MedicineDB()
db.conectar()

findb = FinanceiroDB()
findb.conectar()

agdb = AgendaDB()
agdb.conectar()


class MedicineEncoder(json.JSONEncoder):
    """Encoder customizado para datetime/date/time/bytes do Firebird"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%d/%m/%Y %H:%M')
        if isinstance(obj, date):
            return obj.strftime('%d/%m/%Y')
        if isinstance(obj, time):
            return obj.strftime('%H:%M')
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            try:
                return obj.decode('cp1252')
            except (UnicodeDecodeError, AttributeError):
                return obj.decode('latin-1')
        return super().default(obj)


app.json_provider_class = None  # desabilitar provider padrao


def json_response(data, status=200):
    """Retorna JSON com encoder customizado"""
    return Response(
        json.dumps(data, cls=MedicineEncoder, ensure_ascii=False),
        status=status,
        mimetype='application/json'
    )


# ==================== API ====================

@app.route('/api/pacientes/buscar')
def api_buscar_pacientes():
    q = request.args.get('q', '').strip()
    if not q:
        return json_response([])

    # Se for numero, buscar por ID
    if q.isdigit():
        paciente = db.buscar_paciente_por_id(int(q))
        if paciente:
            return json_response([{
                'id': paciente['id'],
                'nome': paciente['nome'],
                'data_nascimento': paciente['data_nascimento']
            }])
        return json_response([])

    resultados = db.buscar_paciente_por_nome(q)
    return json_response(resultados)


@app.route('/api/pacientes/recentes')
def api_pacientes_recentes():
    limite = request.args.get('limite', 15, type=int)
    resultados = db.listar_pacientes(limite)
    return json_response(resultados)


@app.route('/api/paciente/<int:id_paciente>')
def api_paciente(id_paciente):
    paciente = db.buscar_paciente_por_id(id_paciente)
    if not paciente:
        return json_response({'erro': 'Paciente nao encontrado'}, 404)

    # Enriquecer documentos com nomes legiveis
    docs_formatados = {}
    for tipo, valor in paciente.get('documentos', {}).items():
        tipo_limpo = tipo.replace('NUM_', '').replace('STR_', '')
        tipo_nome = TIPOS_DOCUMENTO.get(tipo_limpo, tipo_limpo)
        if tipo_nome == 'CPF' and valor:
            try:
                v = str(int(valor)).zfill(11)
                valor = f"{v[:3]}.{v[3:6]}.{v[6:9]}-{v[9:]}"
            except (ValueError, TypeError):
                pass
        docs_formatados[tipo_nome] = valor
    paciente['documentos_formatados'] = docs_formatados

    # Enriquecer telefones com nomes de tipo
    for tel in paciente.get('telefones', []):
        tel['tipo_nome'] = TIPOS_TELEFONE.get(str(tel.get('tipo', '')), '') if tel.get('tipo') else ''

    return json_response(paciente)


@app.route('/api/paciente/<int:id_paciente>/consultas')
def api_consultas(id_paciente):
    limite = request.args.get('limite', 30, type=int)
    consultas = db.buscar_consultas(id_paciente, limite)
    # Enriquecer com nome da situacao
    for c in consultas:
        c['situacao_nome'] = SITUACOES_AGENDA.get(c['situacao'], str(c['situacao']))
    return json_response(consultas)


@app.route('/api/paciente/<int:id_paciente>/evolucoes')
def api_evolucoes(id_paciente):
    limite = request.args.get('limite', 30, type=int)
    evolucoes = db.buscar_evolucoes(id_paciente, limite)
    return json_response(evolucoes)


@app.route('/api/paciente/<int:id_paciente>/preconsultas')
def api_preconsultas(id_paciente):
    limite = request.args.get('limite', 30, type=int)
    preconsultas = db.buscar_preconsultas(id_paciente, limite)
    return json_response(preconsultas)


@app.route('/api/paciente/<int:id_paciente>/receitas')
def api_receitas(id_paciente):
    limite = request.args.get('limite', 30, type=int)
    receitas = db.buscar_receitas(id_paciente, limite)
    return json_response(receitas)


@app.route('/api/paciente/<int:id_paciente>/documentos')
def api_documentos(id_paciente):
    limite = request.args.get('limite', 30, type=int)
    documentos = db.buscar_documentos(id_paciente, limite)
    return json_response(documentos)


@app.route('/api/paciente/<int:id_paciente>/procedimentos')
def api_procedimentos(id_paciente):
    limite = request.args.get('limite', 100, type=int)
    procedimentos = db.buscar_procedimentos(id_paciente, limite)
    return json_response(procedimentos)


@app.route('/api/paciente/<int:id_paciente>/financeiro')
def api_financeiro(id_paciente):
    limite = request.args.get('limite', 50, type=int)
    lancamentos = db.buscar_lancamentos(id_paciente, limite)
    return json_response(lancamentos)


@app.route('/api/paciente/<int:id_paciente>/pdfs')
def api_pdfs(id_paciente):
    limite = request.args.get('limite', 50, type=int)
    pdfs = db.buscar_pdfs(id_paciente, limite)
    return json_response(pdfs)


@app.route('/api/pdf/<int:blob_id>')
def api_pdf_blob(blob_id):
    try:
        pdf_bytes = db.buscar_blob_pdf(blob_id)
        if pdf_bytes:
            return Response(pdf_bytes, mimetype='application/pdf',
                            headers={'Content-Disposition': 'inline'})
        return json_response({'erro': 'PDF nao encontrado'}, 404)
    except Exception as e:
        return json_response({'erro': str(e)}, 500)


# ==================== INTERFACE ====================

HTML_PAGE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Medicine Dream</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --bg: #1a1a2e;
    --bg2: #16213e;
    --bg3: #0f3460;
    --accent: #e94560;
    --text: #eee;
    --text2: #aab;
    --text3: #778;
    --border: #2a2a4a;
    --success: #4ecca3;
    --warning: #f0c040;
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}

/* Header */
.header {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: sticky;
    top: 0;
    z-index: 100;
}

.header h1 {
    font-size: 18px;
    color: var(--accent);
    white-space: nowrap;
}

.search-box {
    flex: 1;
    max-width: 500px;
    position: relative;
}

.search-box input {
    width: 100%;
    padding: 10px 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    background: var(--bg);
    color: var(--text);
    font-size: 14px;
    outline: none;
    transition: border-color 0.2s;
}

.search-box input:focus {
    border-color: var(--accent);
}

.search-box input::placeholder {
    color: var(--text3);
}

/* Layout */
.container {
    display: flex;
    height: calc(100vh - 57px);
}

.sidebar {
    width: 350px;
    min-width: 350px;
    background: var(--bg2);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.sidebar-header {
    padding: 12px 16px;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
    color: var(--text2);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.sidebar-list {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
}

.patient-item {
    padding: 10px 16px;
    cursor: pointer;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    transition: background 0.15s;
}

.patient-item:hover {
    background: rgba(233, 69, 96, 0.08);
}

.patient-item.active {
    background: rgba(233, 69, 96, 0.15);
    border-left: 3px solid var(--accent);
}

.patient-item .name {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 2px;
}

.patient-item .info {
    font-size: 12px;
    color: var(--text3);
}

/* Main content */
.main {
    flex: 1;
    overflow-y: auto;
    padding: 0;
}

.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text3);
    font-size: 16px;
    gap: 8px;
}

.empty-state .icon {
    font-size: 48px;
    opacity: 0.3;
}

/* Patient card */
.patient-card {
    background: var(--bg2);
    padding: 20px 24px;
    border-bottom: 1px solid var(--border);
}

.patient-card .patient-name {
    font-size: 22px;
    font-weight: 600;
    margin-bottom: 4px;
}

.patient-card .patient-meta {
    display: flex;
    gap: 20px;
    font-size: 13px;
    color: var(--text2);
    flex-wrap: wrap;
}

.patient-card .patient-meta span {
    display: flex;
    align-items: center;
    gap: 4px;
}

/* Tabs */
.tabs {
    display: flex;
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 0 16px;
    overflow-x: auto;
}

.tab {
    padding: 12px 20px;
    font-size: 13px;
    color: var(--text2);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: color 0.2s, border-color 0.2s;
    user-select: none;
}

.tab:hover {
    color: var(--text);
}

.tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
}

/* Tab content */
.tab-content {
    padding: 20px 24px;
}

.loading {
    text-align: center;
    padding: 40px;
    color: var(--text3);
}

.loading::after {
    content: '';
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-left: 8px;
    vertical-align: middle;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* Info grid */
.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;
}

.info-section {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
}

.info-section h3 {
    font-size: 13px;
    color: var(--accent);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.info-row {
    display: flex;
    justify-content: space-between;
    padding: 4px 0;
    font-size: 13px;
}

.info-row .label {
    color: var(--text3);
}

.info-row .value {
    color: var(--text);
    text-align: right;
    max-width: 60%;
    word-break: break-word;
}

/* Cards list (consultas, receitas, etc) */
.card-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.record-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
}

.record-card .record-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    flex-wrap: wrap;
    gap: 8px;
}

.record-card .record-date {
    font-size: 14px;
    font-weight: 500;
    color: var(--accent);
}

.record-card .record-prof {
    font-size: 13px;
    color: var(--text2);
}

.record-card .record-body {
    font-size: 13px;
    line-height: 1.6;
    color: var(--text);
}

.record-card .record-body pre {
    white-space: pre-wrap;
    font-family: inherit;
    margin: 8px 0;
    padding: 10px;
    background: rgba(0,0,0,0.2);
    border-radius: 6px;
    font-size: 12px;
    line-height: 1.5;
}

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}

.badge-atendido { background: rgba(78, 204, 163, 0.2); color: var(--success); }
.badge-agendado { background: rgba(240, 192, 64, 0.2); color: var(--warning); }
.badge-cancelado { background: rgba(233, 69, 96, 0.2); color: var(--accent); }
.badge-default { background: rgba(170, 170, 187, 0.2); color: var(--text2); }

/* Vitais grid */
.vitais-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
    gap: 8px;
    margin-top: 8px;
}

.vital-item {
    text-align: center;
    padding: 8px;
    background: rgba(0,0,0,0.2);
    border-radius: 6px;
}

.vital-item .vital-label {
    font-size: 11px;
    color: var(--text3);
    margin-bottom: 2px;
}

.vital-item .vital-value {
    font-size: 16px;
    font-weight: 600;
    color: var(--success);
}

/* Medicamento */
.med-item {
    padding: 8px 12px;
    background: rgba(0,0,0,0.15);
    border-radius: 6px;
    margin: 4px 0;
}

.med-item .med-name {
    font-weight: 500;
    font-size: 13px;
}

.med-item .med-pos {
    font-size: 12px;
    color: var(--text2);
    margin-top: 2px;
}

/* PDF list */
.pdf-container {
    display: flex;
    gap: 16px;
    height: calc(100vh - 250px);
    min-height: 400px;
}

.pdf-list {
    width: 350px;
    min-width: 280px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.pdf-item {
    padding: 10px 12px;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    cursor: pointer;
    transition: border-color 0.2s;
}

.pdf-item:hover {
    border-color: var(--accent);
}

.pdf-item.active {
    border-color: var(--accent);
    background: rgba(233, 69, 96, 0.08);
}

.pdf-item .pdf-name {
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 2px;
    word-break: break-word;
}

.pdf-item .pdf-meta {
    font-size: 11px;
    color: var(--text3);
}

.pdf-viewer {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.pdf-viewer iframe {
    width: 100%;
    height: 100%;
    border: none;
}

.pdf-viewer .pdf-placeholder {
    color: var(--text3);
    font-size: 14px;
    text-align: center;
}

.no-data {
    text-align: center;
    padding: 40px;
    color: var(--text3);
    font-size: 14px;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }
</style>
</head>
<body>

<div class="header">
    <h1>Medicine Dream</h1>
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="Buscar paciente por nome ou ID..." autofocus>
    </div>
    <a href="/agenda" style="color:var(--warning);text-decoration:none;font-size:14px;white-space:nowrap;font-weight:500">Agenda</a>
    <a href="/financeiro" style="color:var(--success);text-decoration:none;font-size:14px;white-space:nowrap;font-weight:500">Financeiro</a>
</div>

<div class="container">
    <div class="sidebar">
        <div class="sidebar-header">
            <span id="sidebarTitle">Pacientes recentes</span>
            <span id="sidebarCount"></span>
        </div>
        <div class="sidebar-list" id="patientList"></div>
    </div>

    <div class="main" id="mainContent">
        <div class="empty-state">
            <div class="icon">&#9764;</div>
            <div>Selecione um paciente para visualizar</div>
        </div>
    </div>
</div>

<script>
const state = {
    currentPatient: null,
    currentTab: 'identificacao',
    tabCache: {}
};

// ==================== UTILS ====================

async function fetchJSON(url) {
    const res = await fetch(url);
    return res.json();
}

function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function badgeClass(situacao) {
    if (!situacao) return 'badge-default';
    const s = situacao.toLowerCase();
    if (s.includes('atendido') || s.includes('finalizado')) return 'badge-atendido';
    if (s.includes('agendado') || s.includes('confirmado') || s.includes('fila') || s.includes('aguardando')) return 'badge-agendado';
    if (s.includes('cancelado') || s.includes('faltou')) return 'badge-cancelado';
    return 'badge-default';
}

// ==================== SIDEBAR ====================

async function loadRecentes() {
    document.getElementById('sidebarTitle').textContent = 'Pacientes recentes';
    const data = await fetchJSON('/api/pacientes/recentes?limite=20');
    renderPatientList(data);
}

async function searchPatients(query) {
    if (!query.trim()) {
        loadRecentes();
        return;
    }
    document.getElementById('sidebarTitle').textContent = 'Resultados da busca';
    const data = await fetchJSON('/api/pacientes/buscar?q=' + encodeURIComponent(query));
    renderPatientList(data);
}

function renderPatientList(patients) {
    const list = document.getElementById('patientList');
    document.getElementById('sidebarCount').textContent = patients.length ? patients.length + ' encontrado(s)' : '';

    if (!patients.length) {
        list.innerHTML = '<div class="no-data">Nenhum paciente encontrado</div>';
        return;
    }

    list.innerHTML = patients.map(p => `
        <div class="patient-item ${state.currentPatient && state.currentPatient.id === p.id ? 'active' : ''}"
             onclick="selectPatient(${p.id})">
            <div class="name">${esc(p.nome)}</div>
            <div class="info">ID: ${p.id}${p.data_nascimento ? ' &middot; Nasc: ' + esc(p.data_nascimento) : ''}</div>
        </div>
    `).join('');
}

// ==================== PATIENT ====================

async function selectPatient(id) {
    state.tabCache = {};
    state.currentTab = 'identificacao';

    document.getElementById('mainContent').innerHTML = '<div class="loading">Carregando</div>';

    const paciente = await fetchJSON('/api/paciente/' + id);
    if (paciente.erro) {
        document.getElementById('mainContent').innerHTML = '<div class="no-data">' + esc(paciente.erro) + '</div>';
        return;
    }

    state.currentPatient = paciente;

    // Atualizar sidebar ativa
    document.querySelectorAll('.patient-item').forEach(el => {
        el.classList.toggle('active', el.querySelector('.info')?.textContent.includes('ID: ' + id));
    });

    renderPatient();
}

function renderPatient() {
    const p = state.currentPatient;
    if (!p) return;

    const main = document.getElementById('mainContent');
    main.innerHTML = `
        <div class="patient-card">
            <div class="patient-name">${esc(p.nome)}</div>
            <div class="patient-meta">
                <span>ID: ${p.id}</span>
                ${p.data_nascimento ? '<span>Nasc: ' + esc(p.data_nascimento) + '</span>' : ''}
                ${p.convenio ? '<span>Conv: ' + esc(p.convenio) + '</span>' : ''}
                ${p.tipo_sanguineo ? '<span>Sangue: ' + esc(p.tipo_sanguineo) + '</span>' : ''}
            </div>
        </div>

        <div class="tabs">
            <div class="tab ${state.currentTab === 'identificacao' ? 'active' : ''}" onclick="switchTab('identificacao')">Identificacao</div>
            <div class="tab ${state.currentTab === 'consultas' ? 'active' : ''}" onclick="switchTab('consultas')">Consultas</div>
            <div class="tab ${state.currentTab === 'evolucoes' ? 'active' : ''}" onclick="switchTab('evolucoes')">Evolucoes</div>
            <div class="tab ${state.currentTab === 'preconsultas' ? 'active' : ''}" onclick="switchTab('preconsultas')">Sinais Vitais</div>
            <div class="tab ${state.currentTab === 'receitas' ? 'active' : ''}" onclick="switchTab('receitas')">Receitas</div>
            <div class="tab ${state.currentTab === 'documentos' ? 'active' : ''}" onclick="switchTab('documentos')">Documentos</div>
            <div class="tab ${state.currentTab === 'procedimentos' ? 'active' : ''}" onclick="switchTab('procedimentos')">Procedimentos</div>
            <div class="tab ${state.currentTab === 'financeiro' ? 'active' : ''}" onclick="switchTab('financeiro')">Financeiro</div>
            <div class="tab ${state.currentTab === 'pdfs' ? 'active' : ''}" onclick="switchTab('pdfs')">PDFs</div>
        </div>

        <div id="tabContent"></div>
    `;

    loadTab(state.currentTab);
}

async function switchTab(tab) {
    state.currentTab = tab;
    // Atualizar tabs visuais
    document.querySelectorAll('.tab').forEach(t => {
        t.classList.toggle('active', t.textContent.toLowerCase().replace(/\\s/g, '') === tab ||
            (tab === 'identificacao' && t.textContent === 'Identificacao') ||
            (tab === 'evolucoes' && t.textContent === 'Evolucoes') ||
            (tab === 'preconsultas' && t.textContent === 'Sinais Vitais') ||
            (tab === 'procedimentos' && t.textContent === 'Procedimentos') ||
            (tab === 'pdfs' && t.textContent === 'PDFs'));
    });
    // Simpler approach: re-render tabs
    renderPatient();
}

async function loadTab(tab) {
    const container = document.getElementById('tabContent');
    const p = state.currentPatient;

    if (tab === 'identificacao') {
        renderIdentificacao(container, p);
        return;
    }

    // Lazy load com cache
    if (state.tabCache[tab]) {
        renderTabData(container, tab, state.tabCache[tab]);
        return;
    }

    container.innerHTML = '<div class="loading">Carregando</div>';

    const url = '/api/paciente/' + p.id + '/' + tab;
    const data = await fetchJSON(url);
    state.tabCache[tab] = data;
    renderTabData(container, tab, data);
}

// ==================== TAB RENDERERS ====================

function renderIdentificacao(container, p) {
    let html = '<div class="tab-content"><div class="info-grid">';

    // Dados pessoais
    html += '<div class="info-section"><h3>Dados Pessoais</h3>';
    html += infoRow('Nome', p.nome);
    html += infoRow('Apelido', p.apelido);
    html += infoRow('Nascimento', p.data_nascimento);
    html += infoRow('Mae', p.nome_mae);
    html += infoRow('Pai', p.nome_pai);
    html += infoRow('Tipo Sanguineo', p.tipo_sanguineo);
    html += infoRow('Matricula', p.matricula);
    html += '</div>';

    // Endereco
    const end = p.endereco || {};
    html += '<div class="info-section"><h3>Endereco</h3>';
    html += infoRow('Logradouro', end.logradouro);
    html += infoRow('Numero', end.numero);
    html += infoRow('Complemento', end.complemento);
    html += infoRow('Bairro', end.bairro);
    html += infoRow('CEP', end.cep);
    html += '</div>';

    // Contatos
    html += '<div class="info-section"><h3>Telefones</h3>';
    if (p.telefones && p.telefones.length) {
        p.telefones.forEach(t => {
            const tipo = t.tipo_nome ? ' (' + esc(t.tipo_nome) + ')' : '';
            html += infoRow(esc(t.numero), tipo);
        });
    } else {
        html += '<div class="no-data" style="padding:8px">Nenhum telefone</div>';
    }
    html += '</div>';

    // Emails
    html += '<div class="info-section"><h3>Emails</h3>';
    if (p.emails && p.emails.length) {
        p.emails.forEach(e => {
            html += infoRow(esc(e.endereco), e.tipo || '');
        });
    } else {
        html += '<div class="no-data" style="padding:8px">Nenhum email</div>';
    }
    html += '</div>';

    // Documentos
    html += '<div class="info-section"><h3>Documentos</h3>';
    const docs = p.documentos_formatados || {};
    if (Object.keys(docs).length) {
        for (const [tipo, valor] of Object.entries(docs)) {
            html += infoRow(tipo, valor);
        }
    } else {
        html += '<div class="no-data" style="padding:8px">Nenhum documento</div>';
    }
    html += '</div>';

    // Convenio
    html += '<div class="info-section"><h3>Convenio</h3>';
    html += infoRow('Convenio', p.convenio);
    html += infoRow('Cadastro', p.data_cadastro);
    html += '</div>';

    html += '</div></div>';
    container.innerHTML = html;
}

function infoRow(label, value) {
    if (!value && value !== 0) return '';
    return '<div class="info-row"><span class="label">' + esc(String(label)) + '</span><span class="value">' + esc(String(value)) + '</span></div>';
}

function renderTabData(container, tab, data) {
    if (!data || !data.length) {
        container.innerHTML = '<div class="no-data">Nenhum registro encontrado</div>';
        return;
    }

    const renderers = {
        consultas: renderConsultas,
        evolucoes: renderEvolucoes,
        preconsultas: renderPreconsultas,
        receitas: renderReceitas,
        documentos: renderDocumentos,
        procedimentos: renderProcedimentos,
        financeiro: renderFinanceiro,
        pdfs: renderPDFs
    };

    if (renderers[tab]) {
        renderers[tab](container, data);
    }
}

function renderConsultas(container, data) {
    let html = '<div class="tab-content"><div class="card-list">';
    data.forEach(c => {
        html += '<div class="record-card">';
        html += '<div class="record-header">';
        html += '<span class="record-date">' + esc(c.data) + ' ' + esc(c.hora || '') + '</span>';
        html += '<span class="record-prof">' + esc(c.profissional || '') + '</span>';
        html += '</div>';
        html += '<span class="badge ' + badgeClass(c.situacao_nome) + '">' + esc(c.situacao_nome) + '</span>';

        if (c.observacao) {
            html += '<div class="record-body" style="margin-top:8px"><strong>Obs:</strong> ' + esc(c.observacao) + '</div>';
        }

        if (c.textos && c.textos.length) {
            html += '<div class="record-body" style="margin-top:8px">';
            c.textos.forEach(t => {
                html += '<pre>' + esc(t.texto) + '</pre>';
            });
            html += '</div>';
        }

        html += '</div>';
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function renderEvolucoes(container, data) {
    let html = '<div class="tab-content"><div class="card-list">';
    data.forEach(e => {
        html += '<div class="record-card">';
        html += '<div class="record-header">';
        html += '<span class="record-date">' + esc(e.data) + ' ' + esc(e.hora || '') + '</span>';
        html += '<span class="record-prof">' + esc(e.profissional || '') + '</span>';
        html += '</div>';
        html += '<div class="record-body"><pre>' + esc(e.texto) + '</pre></div>';
        html += '</div>';
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function renderPreconsultas(container, data) {
    let html = '<div class="tab-content"><div class="card-list">';
    data.forEach(p => {
        html += '<div class="record-card">';
        html += '<div class="record-header">';
        html += '<span class="record-date">' + esc(p.data) + ' ' + esc(p.hora || '') + '</span>';
        html += '</div>';
        html += '<div class="vitais-grid">';

        if (p.pa_max && p.pa_min) html += vitalItem('PA', p.pa_max + 'x' + p.pa_min);
        if (p.freq_cardiaca) html += vitalItem('FC', p.freq_cardiaca + ' bpm');
        if (p.freq_respiratoria) html += vitalItem('FR', p.freq_respiratoria + ' irpm');
        if (p.peso) html += vitalItem('Peso', p.peso + ' kg');
        if (p.altura) html += vitalItem('Altura', p.altura + ' cm');
        if (p.imc) html += vitalItem('IMC', Number(p.imc).toFixed(1));
        if (p.temperatura) html += vitalItem('Temp', p.temperatura + ' C');
        if (p.saturacao) html += vitalItem('SpO2', p.saturacao + '%');
        if (p.hgt) html += vitalItem('HGT', p.hgt + ' mg/dL');

        html += '</div></div>';
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function vitalItem(label, value) {
    return '<div class="vital-item"><div class="vital-label">' + esc(label) + '</div><div class="vital-value">' + esc(String(value)) + '</div></div>';
}

function renderReceitas(container, data) {
    let html = '<div class="tab-content"><div class="card-list">';
    data.forEach(r => {
        html += '<div class="record-card">';
        html += '<div class="record-header">';
        html += '<span class="record-date">' + esc(r.data_hora) + '</span>';
        html += '<span class="record-prof">' + esc(r.profissional || '') + '</span>';
        html += '</div>';

        if (r.observacao) {
            html += '<div class="record-body" style="margin-bottom:8px"><strong>Obs:</strong> ' + esc(r.observacao) + '</div>';
        }

        if (r.itens && r.itens.length) {
            r.itens.forEach(item => {
                html += '<div class="med-item">';
                html += '<div class="med-name">' + esc(item.medicamento || '-') + '</div>';
                if (item.posologia) {
                    html += '<div class="med-pos">' + esc(item.posologia);
                    if (item.quantidade) html += ' (Qt: ' + esc(String(item.quantidade)) + ')';
                    html += '</div>';
                }
                html += '</div>';
            });
        }

        html += '</div>';
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function renderDocumentos(container, data) {
    let html = '<div class="tab-content"><div class="card-list">';
    data.forEach(d => {
        html += '<div class="record-card">';
        html += '<div class="record-header">';
        html += '<span class="record-date">' + esc(d.data_hora) + '</span>';
        html += '<span class="record-prof">' + esc(d.profissional || '') + '</span>';
        html += '</div>';
        if (d.conteudo) {
            html += '<div class="record-body"><pre>' + esc(d.conteudo) + '</pre></div>';
        }
        html += '</div>';
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function renderProcedimentos(container, data) {
    let html = '<div class="tab-content">';

    // Resumo
    let totalValor = 0, totalQt = 0;
    data.forEach(p => {
        if (p.valor) totalValor += p.valor;
        if (p.quantidade) totalQt += p.quantidade;
    });

    html += '<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">';
    html += '<div class="vital-item" style="flex:1;min-width:150px;padding:12px"><div class="vital-label">Total Procedimentos</div><div class="vital-value" style="color:var(--text)">' + data.length + '</div></div>';
    if (totalValor > 0) {
        html += '<div class="vital-item" style="flex:1;min-width:150px;padding:12px"><div class="vital-label">Valor Total</div><div class="vital-value" style="color:var(--success)">R$ ' + totalValor.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</div></div>';
    }
    html += '</div>';

    // Lista
    html += '<div class="card-list">';
    data.forEach(p => {
        html += '<div class="record-card">';
        html += '<div class="record-header">';
        html += '<span class="record-date">' + esc(p.data) + ' ' + esc(p.hora || '') + '</span>';
        html += '<span class="record-prof">' + esc(p.profissional || '') + '</span>';
        html += '</div>';

        html += '<div class="record-body" style="margin-bottom:6px">';
        html += '<strong style="font-size:14px">' + esc(p.procedimento || '-') + '</strong>';
        html += '</div>';

        let details = [];
        if (p.grupo) details.push('<span class="badge badge-agendado">' + esc(p.grupo) + '</span>');
        if (p.valor) details.push('<span style="color:var(--success);font-weight:500">R$ ' + p.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</span>');
        if (p.quantidade && p.quantidade > 1) details.push('<span style="color:var(--text3)">Qt: ' + p.quantidade + '</span>');
        if (details.length) {
            html += '<div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">' + details.join('') + '</div>';
        }

        html += '</div>';
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function renderFinanceiro(container, data) {
    // Calcular totais
    let totalCredito = 0, totalDebito = 0;
    data.forEach(l => {
        if (l.tipo === 'C') totalCredito += l.valor;
        else if (l.tipo === 'D') totalDebito += l.valor;
    });

    let html = '<div class="tab-content">';

    // Resumo
    html += '<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">';
    html += '<div class="vital-item" style="flex:1;min-width:150px;padding:12px"><div class="vital-label">Total Creditos</div><div class="vital-value" style="color:var(--success)">R$ ' + totalCredito.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</div></div>';
    html += '<div class="vital-item" style="flex:1;min-width:150px;padding:12px"><div class="vital-label">Total Debitos</div><div class="vital-value" style="color:var(--accent)">R$ ' + totalDebito.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</div></div>';
    html += '<div class="vital-item" style="flex:1;min-width:150px;padding:12px"><div class="vital-label">Lancamentos</div><div class="vital-value" style="color:var(--text)">' + data.length + '</div></div>';
    html += '</div>';

    // Lista
    html += '<div class="card-list">';
    data.forEach(l => {
        const tipoLabel = l.tipo === 'C' ? 'Credito' : l.tipo === 'D' ? 'Debito' : l.tipo === 'T' ? 'Transferencia' : l.tipo;
        const tipoClass = l.tipo === 'C' ? 'badge-atendido' : l.tipo === 'D' ? 'badge-cancelado' : 'badge-default';
        const valorColor = l.tipo === 'C' ? 'var(--success)' : l.tipo === 'D' ? 'var(--accent)' : 'var(--text)';

        html += '<div class="record-card">';
        html += '<div class="record-header">';
        html += '<span class="record-date">' + esc(l.data) + '</span>';
        html += '<span style="font-size:16px;font-weight:600;color:' + valorColor + '">R$ ' + l.valor.toLocaleString('pt-BR', {minimumFractionDigits: 2}) + '</span>';
        html += '</div>';

        html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">';
        html += '<span class="badge ' + tipoClass + '">' + esc(tipoLabel) + '</span>';
        if (l.conta) html += '<span style="font-size:12px;color:var(--text3)">' + esc(l.conta) + '</span>';
        html += '</div>';

        if (l.procedimentos) html += '<div class="record-body" style="margin-bottom:4px"><strong style="color:var(--success)">' + esc(l.procedimentos) + '</strong></div>';
        if (l.texto) html += '<div class="record-body">' + esc(l.texto) + '</div>';
        if (l.observacao) html += '<div class="record-body" style="color:var(--text3);margin-top:4px">' + esc(l.observacao) + '</div>';

        // Detalhes extras
        let extras = [];
        if (l.valor_realizado != null) extras.push('Realizado: R$ ' + l.valor_realizado.toLocaleString('pt-BR', {minimumFractionDigits: 2}));
        if (l.desconto) extras.push('Desc: R$ ' + l.desconto.toLocaleString('pt-BR', {minimumFractionDigits: 2}));
        if (l.acrescimo) extras.push('Acresc: R$ ' + l.acrescimo.toLocaleString('pt-BR', {minimumFractionDigits: 2}));
        if (l.num_documento) extras.push('Doc: ' + l.num_documento);
        if (l.data_realizado && l.data_realizado !== l.data) extras.push('Realiz: ' + l.data_realizado);
        if (extras.length) {
            html += '<div style="font-size:11px;color:var(--text3);margin-top:6px">' + esc(extras.join(' | ')) + '</div>';
        }

        html += '</div>';
    });
    html += '</div></div>';
    container.innerHTML = html;
}

function renderPDFs(container, data) {
    let html = '<div class="tab-content"><div class="pdf-container">';

    html += '<div class="pdf-list">';
    data.forEach((p, i) => {
        html += '<div class="pdf-item" onclick="viewPDF(' + p.blob_id + ', this)" data-blob="' + p.blob_id + '">';
        html += '<div class="pdf-name">' + esc(p.nome || 'Documento ' + (i + 1)) + '</div>';
        html += '<div class="pdf-meta">' + esc(p.data || '') + (p.tipo ? ' &middot; ' + esc(p.tipo) : '') + '</div>';
        html += '</div>';
    });
    html += '</div>';

    html += '<div class="pdf-viewer" id="pdfViewer">';
    html += '<div class="pdf-placeholder">Selecione um PDF para visualizar</div>';
    html += '</div>';

    html += '</div></div>';
    container.innerHTML = html;
}

function viewPDF(blobId, el) {
    // Marcar ativo
    document.querySelectorAll('.pdf-item').forEach(i => i.classList.remove('active'));
    if (el) el.classList.add('active');

    const viewer = document.getElementById('pdfViewer');
    viewer.innerHTML = '<iframe src="/api/pdf/' + blobId + '"></iframe>';
}

// ==================== EVENTS ====================

let searchTimeout;
document.getElementById('searchInput').addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const q = this.value;
    searchTimeout = setTimeout(() => searchPatients(q), 300);
});

document.getElementById('searchInput').addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        this.value = '';
        loadRecentes();
    }
});

// Inicializar
loadRecentes();
</script>

</body>
</html>
"""


@app.route('/')
def index():
    return render_template_string(HTML_PAGE)


# ==================== FINANCEIRO - API ====================

@app.route('/api/financeiro/resumo-mensal')
def api_fin_resumo_mensal():
    meses = request.args.get('meses', 12, type=int)
    return json_response(findb.resumo_mensal(meses))


@app.route('/api/financeiro/saldo-contas')
def api_fin_saldo_contas():
    return json_response(findb.saldo_contas())


@app.route('/api/financeiro/fluxo-diario')
def api_fin_fluxo_diario():
    dias = request.args.get('dias', 30, type=int)
    return json_response(findb.fluxo_diario(dias))


@app.route('/api/financeiro/pendentes')
def api_fin_pendentes():
    return json_response(findb.lancamentos_pendentes())


@app.route('/api/financeiro/recorrentes')
def api_fin_recorrentes():
    return json_response(findb.despesas_recorrentes())


@app.route('/api/financeiro/lancamentos')
def api_fin_lancamentos():
    limite = request.args.get('limite', 50, type=int)
    return json_response(findb.lancamentos_recentes(limite))


@app.route('/api/financeiro/top-clientes')
def api_fin_top_clientes():
    meses = request.args.get('meses', 12, type=int)
    return json_response(findb.top_clientes(meses))


@app.route('/api/financeiro/top-despesas')
def api_fin_top_despesas():
    meses = request.args.get('meses', 12, type=int)
    return json_response(findb.top_despesas(meses))


# ==================== FINANCEIRO - PAGINA ====================

HTML_PAGE_FINANCEIRO = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Medicine Dream - Financeiro</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --bg: #1a1a2e;
    --bg2: #16213e;
    --bg3: #0f3460;
    --accent: #e94560;
    --text: #eee;
    --text2: #aab;
    --text3: #778;
    --border: #2a2a4a;
    --success: #4ecca3;
    --warning: #f0c040;
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}

.header {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: sticky;
    top: 0;
    z-index: 100;
}

.header h1 {
    font-size: 18px;
    color: var(--accent);
    white-space: nowrap;
}

.header .subtitle {
    font-size: 14px;
    color: var(--text2);
}

.header .nav-link {
    margin-left: auto;
    color: var(--success);
    text-decoration: none;
    font-size: 14px;
    white-space: nowrap;
    font-weight: 500;
}

.header .nav-link:hover { text-decoration: underline; }

.content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px 24px;
}

/* Summary cards */
.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
}

.summary-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
}

.summary-card .card-label {
    font-size: 12px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.summary-card .card-value {
    font-size: 24px;
    font-weight: 700;
}

.card-value.credit { color: var(--success); }
.card-value.debit { color: var(--accent); }
.card-value.neutral { color: var(--text); }
.card-value.warning { color: var(--warning); }

.summary-card .card-detail {
    font-size: 11px;
    color: var(--text3);
    margin-top: 4px;
}

/* Chart area */
.section-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.chart-section {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 24px;
}

.bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 13px;
}

.bar-label {
    width: 70px;
    text-align: right;
    color: var(--text2);
    flex-shrink: 0;
    font-size: 12px;
}

.bar-track {
    flex: 1;
    display: flex;
    gap: 2px;
    align-items: center;
}

.bar-fill {
    height: 20px;
    border-radius: 3px;
    min-width: 2px;
    transition: width 0.3s;
}

.bar-fill.credit { background: var(--success); }
.bar-fill.debit { background: var(--accent); }

.bar-value {
    font-size: 11px;
    color: var(--text3);
    white-space: nowrap;
    min-width: 80px;
}

/* Two columns */
.two-cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 24px;
}

@media (max-width: 900px) {
    .two-cols { grid-template-columns: 1fr; }
}

.col-section {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
}

/* Account cards */
.account-card {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px;
    margin-bottom: 8px;
}

.account-card .acc-name {
    font-size: 14px;
    font-weight: 500;
    margin-bottom: 4px;
}

.account-card .acc-saldo {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 4px;
}

.account-card .acc-detail {
    font-size: 11px;
    color: var(--text3);
    display: flex;
    gap: 12px;
}

/* Recorrentes */
.recorrente-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 13px;
}

.recorrente-item:last-child { border-bottom: none; }

.recorrente-item .rec-nome {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.recorrente-item .rec-valor {
    font-weight: 600;
    margin-left: 12px;
    white-space: nowrap;
}

.recorrente-item .rec-forn {
    font-size: 11px;
    color: var(--text3);
    margin-left: 8px;
    white-space: nowrap;
}

/* Tabs */
.tabs {
    display: flex;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px 8px 0 0;
    border-bottom: none;
    overflow-x: auto;
}

.tab {
    padding: 12px 20px;
    font-size: 13px;
    color: var(--text2);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: color 0.2s, border-color 0.2s;
    user-select: none;
}

.tab:hover { color: var(--text); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.tab-body {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 20px;
    min-height: 200px;
}

/* Table */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.data-table th {
    text-align: left;
    padding: 8px 10px;
    font-size: 11px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
}

.data-table td {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    vertical-align: top;
}

.data-table tr:hover td {
    background: rgba(255,255,255,0.02);
}

.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
}

.badge-c { background: rgba(78,204,163,0.2); color: var(--success); }
.badge-d { background: rgba(233,69,96,0.2); color: var(--accent); }
.badge-t { background: rgba(240,192,64,0.2); color: var(--warning); }
.badge-o { background: rgba(170,170,187,0.2); color: var(--text2); }

.badge-s { background: rgba(78,204,163,0.15); color: var(--success); }
.badge-n { background: rgba(240,192,64,0.15); color: var(--warning); }
.badge-p { background: rgba(170,170,187,0.15); color: var(--text2); }

.text-credit { color: var(--success); }
.text-debit { color: var(--accent); }
.text-muted { color: var(--text3); font-size: 12px; }

/* Ranking */
.rank-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    font-size: 13px;
}

.rank-row:last-child { border-bottom: none; }

.rank-num {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--bg3);
    color: var(--text2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 600;
    flex-shrink: 0;
}

.rank-name {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.rank-bar {
    width: 120px;
    height: 6px;
    background: var(--bg);
    border-radius: 3px;
    overflow: hidden;
    flex-shrink: 0;
}

.rank-bar-fill {
    height: 100%;
    border-radius: 3px;
}

.rank-value {
    width: 100px;
    text-align: right;
    font-weight: 600;
    flex-shrink: 0;
}

.rank-qty {
    width: 40px;
    text-align: right;
    color: var(--text3);
    font-size: 11px;
    flex-shrink: 0;
}

.loading {
    text-align: center;
    padding: 40px;
    color: var(--text3);
}

.loading::after {
    content: '';
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-left: 8px;
    vertical-align: middle;
}

@keyframes spin { to { transform: rotate(360deg); } }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }
</style>
</head>
<body>

<div class="header">
    <h1>Medicine Dream</h1>
    <span class="subtitle">Financeiro</span>
    <a href="/" class="nav-link">&larr; Pacientes</a>
    <a href="/agenda" class="nav-link" style="margin-left:0">Agenda</a>
</div>

<div class="content">
    <div class="summary-cards" id="summaryCards">
        <div class="summary-card"><div class="card-label">Carregando...</div></div>
    </div>

    <div class="chart-section" id="chartSection">
        <div class="section-title">Receitas vs Despesas - Ultimos 12 meses</div>
        <div id="monthlyChart" class="loading">Carregando</div>
    </div>

    <div class="two-cols">
        <div class="col-section">
            <div class="section-title">Saldos por Conta</div>
            <div id="saldoContas" class="loading">Carregando</div>
        </div>
        <div class="col-section">
            <div class="section-title">Despesas Recorrentes</div>
            <div id="recorrentes" class="loading">Carregando</div>
        </div>
    </div>

    <div class="tabs" id="dataTabs">
        <div class="tab active" onclick="switchTab('lancamentos')">Lancamentos</div>
        <div class="tab" onclick="switchTab('pendentes')">Pendentes</div>
        <div class="tab" onclick="switchTab('fluxo')">Fluxo Diario</div>
        <div class="tab" onclick="switchTab('topClientes')">Top Clientes</div>
        <div class="tab" onclick="switchTab('topDespesas')">Top Despesas</div>
    </div>
    <div class="tab-body" id="tabBody">
        <div class="loading">Carregando</div>
    </div>
</div>

<script>
const MESES = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
let cache = {};
let currentTab = 'lancamentos';

function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

function fmtMoney(v) {
    return 'R$ ' + Number(v).toLocaleString('pt-BR', {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

async function fetchJSON(url) {
    const res = await fetch(url);
    return res.json();
}

// ==================== LOAD DATA ====================

async function loadAll() {
    const [resumo, saldos, recorrentes] = await Promise.all([
        fetchJSON('/api/financeiro/resumo-mensal'),
        fetchJSON('/api/financeiro/saldo-contas'),
        fetchJSON('/api/financeiro/recorrentes')
    ]);

    cache.resumo = resumo;
    cache.saldos = saldos;
    cache.recorrentes = recorrentes;

    renderSummaryCards(resumo);
    renderMonthlyChart(resumo);
    renderSaldoContas(saldos);
    renderRecorrentes(recorrentes);
    loadTab('lancamentos');
}

// ==================== SUMMARY CARDS ====================

function renderSummaryCards(resumo) {
    const now = new Date();
    const mesAtual = now.getMonth() + 1;
    const anoAtual = now.getFullYear();

    let receitaMes = 0, despesaMes = 0;
    resumo.forEach(r => {
        if (r.ano === anoAtual && r.mes === mesAtual) {
            if (r.tipo === 'C') receitaMes = r.total;
            else if (r.tipo === 'D') despesaMes = r.total;
        }
    });

    const saldoMes = receitaMes - despesaMes;

    // Pendentes serão carregados async
    let html = '';
    html += '<div class="summary-card"><div class="card-label">Receita do Mes</div><div class="card-value credit">' + fmtMoney(receitaMes) + '</div></div>';
    html += '<div class="summary-card"><div class="card-label">Despesas do Mes</div><div class="card-value debit">' + fmtMoney(despesaMes) + '</div></div>';
    html += '<div class="summary-card"><div class="card-label">Saldo do Mes</div><div class="card-value ' + (saldoMes >= 0 ? 'credit' : 'debit') + '">' + fmtMoney(saldoMes) + '</div></div>';
    html += '<div class="summary-card" id="cardPendentes"><div class="card-label">Pendentes</div><div class="card-value warning">...</div></div>';

    document.getElementById('summaryCards').innerHTML = html;

    // Load pendentes async
    fetchJSON('/api/financeiro/pendentes').then(pend => {
        cache.pendentes = pend;
        let receber = 0, pagar = 0;
        pend.forEach(p => {
            if (p.tipo === 'C') receber += p.valor;
            else if (p.tipo === 'D') pagar += p.valor;
        });
        const el = document.getElementById('cardPendentes');
        if (el) {
            el.innerHTML = '<div class="card-label">Pendentes</div>'
                + '<div class="card-value warning">' + fmtMoney(receber + pagar) + '</div>'
                + '<div class="card-detail">Receber: ' + fmtMoney(receber) + ' | Pagar: ' + fmtMoney(pagar) + '</div>';
        }
    });
}

// ==================== MONTHLY CHART ====================

function renderMonthlyChart(resumo) {
    // Agrupar por mes
    const meses = {};
    resumo.forEach(r => {
        const key = r.ano + '-' + String(r.mes).padStart(2, '0');
        if (!meses[key]) meses[key] = {ano: r.ano, mes: r.mes, C: 0, D: 0};
        if (r.tipo === 'C') meses[key].C = r.total;
        else if (r.tipo === 'D') meses[key].D = r.total;
    });

    const sorted = Object.values(meses).sort((a, b) => a.ano - b.ano || a.mes - b.mes);
    if (!sorted.length) {
        document.getElementById('monthlyChart').innerHTML = '<div style="color:var(--text3)">Sem dados</div>';
        return;
    }

    const maxVal = Math.max(...sorted.map(m => Math.max(m.C, m.D)));

    let html = '';
    sorted.forEach(m => {
        const label = MESES[m.mes] + '/' + String(m.ano).slice(2);
        const cPct = maxVal > 0 ? (m.C / maxVal * 100) : 0;
        const dPct = maxVal > 0 ? (m.D / maxVal * 100) : 0;

        html += '<div class="bar-row">';
        html += '<span class="bar-label">' + label + '</span>';
        html += '<div class="bar-track">';
        html += '<div class="bar-fill credit" style="width:' + cPct + '%"></div>';
        html += '</div>';
        html += '<span class="bar-value text-credit">' + fmtMoney(m.C) + '</span>';
        html += '</div>';

        html += '<div class="bar-row" style="margin-bottom:12px">';
        html += '<span class="bar-label"></span>';
        html += '<div class="bar-track">';
        html += '<div class="bar-fill debit" style="width:' + dPct + '%"></div>';
        html += '</div>';
        html += '<span class="bar-value text-debit">' + fmtMoney(m.D) + '</span>';
        html += '</div>';
    });

    document.getElementById('monthlyChart').innerHTML = html;
}

// ==================== SALDOS POR CONTA ====================

function renderSaldoContas(saldos) {
    if (!saldos.length) {
        document.getElementById('saldoContas').innerHTML = '<div style="color:var(--text3)">Sem dados</div>';
        return;
    }

    let html = '';
    saldos.forEach(s => {
        const saldoClass = s.saldo >= 0 ? 'text-credit' : 'text-debit';
        html += '<div class="account-card">';
        html += '<div class="acc-name">' + esc(s.nome) + '</div>';
        html += '<div class="acc-saldo ' + saldoClass + '">' + fmtMoney(s.saldo) + '</div>';
        html += '<div class="acc-detail">';
        html += '<span class="text-credit">Creditos: ' + fmtMoney(s.total_creditos) + '</span>';
        html += '<span class="text-debit">Debitos: ' + fmtMoney(s.total_debitos) + '</span>';
        html += '</div>';
        html += '</div>';
    });

    document.getElementById('saldoContas').innerHTML = html;
}

// ==================== RECORRENTES ====================

function renderRecorrentes(recorrentes) {
    if (!recorrentes.length) {
        document.getElementById('recorrentes').innerHTML = '<div style="color:var(--text3)">Sem dados</div>';
        return;
    }

    let html = '';
    recorrentes.forEach(r => {
        const tipoClass = r.tipo === 'D' ? 'text-debit' : r.tipo === 'C' ? 'text-credit' : '';
        const ativoLabel = r.ativo === 'S' ? '' : ' <span class="badge badge-o">Inativo</span>';
        html += '<div class="recorrente-item">';
        html += '<span class="rec-nome">' + esc(r.nome) + ativoLabel + '</span>';
        if (r.fornecedor) html += '<span class="rec-forn">' + esc(r.fornecedor) + '</span>';
        html += '<span class="rec-valor ' + tipoClass + '">' + fmtMoney(r.valor) + '</span>';
        html += '</div>';
    });

    document.getElementById('recorrentes').innerHTML = html;
}

// ==================== TABS ====================

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    const tabs = document.querySelectorAll('.tab');
    const tabMap = {'lancamentos': 0, 'pendentes': 1, 'fluxo': 2, 'topClientes': 3, 'topDespesas': 4};
    if (tabs[tabMap[tab]]) tabs[tabMap[tab]].classList.add('active');
    loadTab(tab);
}

async function loadTab(tab) {
    const body = document.getElementById('tabBody');

    if (tab === 'lancamentos') {
        if (cache.lancamentos) { renderLancamentos(cache.lancamentos); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.lancamentos = await fetchJSON('/api/financeiro/lancamentos?limite=100');
        renderLancamentos(cache.lancamentos);
    } else if (tab === 'pendentes') {
        if (cache.pendentes) { renderPendentes(cache.pendentes); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.pendentes = await fetchJSON('/api/financeiro/pendentes');
        renderPendentes(cache.pendentes);
    } else if (tab === 'fluxo') {
        if (cache.fluxo) { renderFluxoDiario(cache.fluxo); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.fluxo = await fetchJSON('/api/financeiro/fluxo-diario?dias=30');
        renderFluxoDiario(cache.fluxo);
    } else if (tab === 'topClientes') {
        if (cache.topClientes) { renderRanking(cache.topClientes, 'credit'); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.topClientes = await fetchJSON('/api/financeiro/top-clientes');
        renderRanking(cache.topClientes, 'credit');
    } else if (tab === 'topDespesas') {
        if (cache.topDespesas) { renderRanking(cache.topDespesas, 'debit'); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.topDespesas = await fetchJSON('/api/financeiro/top-despesas');
        renderRanking(cache.topDespesas, 'debit');
    }
}

// ==================== TAB RENDERERS ====================

function renderLancamentos(data) {
    const body = document.getElementById('tabBody');
    if (!data.length) { body.innerHTML = '<div style="color:var(--text3);padding:20px">Nenhum lancamento</div>'; return; }

    let html = '<div style="overflow-x:auto"><table class="data-table">';
    html += '<thead><tr><th>Data</th><th>Descricao</th><th>Procedimento</th><th>Valor</th><th>Tipo</th><th>Conta</th><th>Cliente</th><th>Status</th></tr></thead><tbody>';

    data.forEach(l => {
        const tipoBadge = l.tipo === 'C' ? 'badge-c' : l.tipo === 'D' ? 'badge-d' : l.tipo === 'T' ? 'badge-t' : 'badge-o';
        const tipoLabel = l.tipo === 'C' ? 'Credito' : l.tipo === 'D' ? 'Debito' : l.tipo === 'T' ? 'Transf' : l.tipo;
        const statusBadge = l.status === 'S' ? 'badge-s' : l.status === 'N' ? 'badge-n' : 'badge-p';
        const statusLabel = l.status === 'S' ? 'Realizado' : l.status === 'N' ? 'Pendente' : l.status === 'P' ? 'Programado' : l.status;
        const valorClass = l.tipo === 'C' ? 'text-credit' : l.tipo === 'D' ? 'text-debit' : '';

        html += '<tr>';
        html += '<td style="white-space:nowrap">' + esc(l.data) + '</td>';
        html += '<td>' + esc(l.texto || '') + '</td>';
        html += '<td style="color:var(--success)">' + esc(l.procedimentos || '') + '</td>';
        html += '<td class="' + valorClass + '" style="font-weight:600;white-space:nowrap">' + fmtMoney(l.valor) + '</td>';
        html += '<td><span class="badge ' + tipoBadge + '">' + tipoLabel + '</span></td>';
        html += '<td class="text-muted">' + esc(l.conta || '') + '</td>';
        html += '<td>' + esc(l.cliente || '') + '</td>';
        html += '<td><span class="badge ' + statusBadge + '">' + statusLabel + '</span></td>';
        html += '</tr>';
    });

    html += '</tbody></table></div>';
    body.innerHTML = html;
}

function renderPendentes(data) {
    const body = document.getElementById('tabBody');
    if (!data.length) { body.innerHTML = '<div style="color:var(--text3);padding:20px">Nenhum lancamento pendente</div>'; return; }

    const receber = data.filter(d => d.tipo === 'C');
    const pagar = data.filter(d => d.tipo === 'D');
    const outros = data.filter(d => d.tipo !== 'C' && d.tipo !== 'D');

    let html = '';

    if (receber.length) {
        const totalReceber = receber.reduce((s, r) => s + r.valor, 0);
        html += '<div style="margin-bottom:20px">';
        html += '<div class="section-title">A Receber <span class="text-credit">(' + fmtMoney(totalReceber) + ' - ' + receber.length + ' itens)</span></div>';
        html += renderPendentesTable(receber);
        html += '</div>';
    }

    if (pagar.length) {
        const totalPagar = pagar.reduce((s, r) => s + r.valor, 0);
        html += '<div style="margin-bottom:20px">';
        html += '<div class="section-title">A Pagar <span class="text-debit">(' + fmtMoney(totalPagar) + ' - ' + pagar.length + ' itens)</span></div>';
        html += renderPendentesTable(pagar);
        html += '</div>';
    }

    if (outros.length) {
        html += '<div style="margin-bottom:20px">';
        html += '<div class="section-title">Outros (' + outros.length + ' itens)</div>';
        html += renderPendentesTable(outros);
        html += '</div>';
    }

    body.innerHTML = html;
}

function renderPendentesTable(items) {
    let html = '<div style="overflow-x:auto"><table class="data-table">';
    html += '<thead><tr><th>Data</th><th>Descricao</th><th>Cliente/Fornecedor</th><th>Valor</th><th>Conta</th></tr></thead><tbody>';
    items.forEach(l => {
        const valorClass = l.tipo === 'C' ? 'text-credit' : l.tipo === 'D' ? 'text-debit' : '';
        html += '<tr>';
        html += '<td style="white-space:nowrap">' + esc(l.data) + '</td>';
        html += '<td>' + esc(l.texto || '') + '</td>';
        html += '<td>' + esc(l.cliente || '') + '</td>';
        html += '<td class="' + valorClass + '" style="font-weight:600;white-space:nowrap">' + fmtMoney(l.valor) + '</td>';
        html += '<td class="text-muted">' + esc(l.conta || '') + '</td>';
        html += '</tr>';
    });
    html += '</tbody></table></div>';
    return html;
}

function renderFluxoDiario(data) {
    const body = document.getElementById('tabBody');
    if (!data.length) { body.innerHTML = '<div style="color:var(--text3);padding:20px">Sem dados no periodo</div>'; return; }

    // Agrupar por dia
    const dias = {};
    data.forEach(d => {
        const key = d.data;
        if (!dias[key]) dias[key] = {data: d.data, C: 0, D: 0};
        if (d.tipo === 'C') dias[key].C = d.total;
        else if (d.tipo === 'D') dias[key].D = d.total;
    });

    const sorted = Object.values(dias).sort((a, b) => {
        if (a.data < b.data) return -1;
        if (a.data > b.data) return 1;
        return 0;
    });

    const maxVal = Math.max(...sorted.map(d => Math.max(d.C, d.D)));

    let html = '';
    sorted.forEach(d => {
        const cPct = maxVal > 0 ? (d.C / maxVal * 100) : 0;
        const dPct = maxVal > 0 ? (d.D / maxVal * 100) : 0;
        const saldo = d.C - d.D;
        const saldoClass = saldo >= 0 ? 'text-credit' : 'text-debit';

        html += '<div class="bar-row">';
        html += '<span class="bar-label">' + esc(d.data) + '</span>';
        html += '<div class="bar-track">';
        if (d.C > 0) html += '<div class="bar-fill credit" style="width:' + cPct + '%"></div>';
        html += '</div>';
        html += '<span class="bar-value text-credit">' + (d.C > 0 ? fmtMoney(d.C) : '') + '</span>';
        html += '</div>';

        html += '<div class="bar-row" style="margin-bottom:8px">';
        html += '<span class="bar-label"></span>';
        html += '<div class="bar-track">';
        if (d.D > 0) html += '<div class="bar-fill debit" style="width:' + dPct + '%"></div>';
        html += '</div>';
        html += '<span class="bar-value text-debit">' + (d.D > 0 ? fmtMoney(d.D) : '') + '</span>';
        html += '</div>';
    });

    body.innerHTML = html;
}

function renderRanking(data, type) {
    const body = document.getElementById('tabBody');
    if (!data.length) { body.innerHTML = '<div style="color:var(--text3);padding:20px">Sem dados</div>'; return; }

    const maxVal = data[0].total;
    const colorClass = type === 'credit' ? 'text-credit' : 'text-debit';
    const barColor = type === 'credit' ? 'var(--success)' : 'var(--accent)';

    let html = '';
    data.forEach((item, i) => {
        const pct = maxVal > 0 ? (item.total / maxVal * 100) : 0;
        html += '<div class="rank-row">';
        html += '<span class="rank-num">' + (i + 1) + '</span>';
        html += '<span class="rank-name">' + esc(item.nome) + '</span>';
        html += '<span class="rank-bar"><span class="rank-bar-fill" style="width:' + pct + '%;background:' + barColor + '"></span></span>';
        html += '<span class="rank-value ' + colorClass + '">' + fmtMoney(item.total) + '</span>';
        html += '<span class="rank-qty">' + item.quantidade + 'x</span>';
        html += '</div>';
    });

    body.innerHTML = html;
}

// Init
loadAll();
</script>

</body>
</html>
"""


@app.route('/financeiro')
def financeiro():
    return render_template_string(HTML_PAGE_FINANCEIRO)


# ==================== AGENDA - API ====================

@app.route('/api/agenda/dia')
def api_agenda_dia():
    data = request.args.get('data', None)
    prof = request.args.get('prof', None, type=int)
    return json_response(agdb.agenda_dia(data, prof))


@app.route('/api/agenda/profissionais')
def api_agenda_profissionais():
    return json_response(agdb.profissionais())


@app.route('/api/agenda/resumo')
def api_agenda_resumo():
    data = request.args.get('data', None)
    return json_response(agdb.resumo_dia(data))


@app.route('/api/agenda/estatisticas')
def api_agenda_estatisticas():
    meses = request.args.get('meses', 6, type=int)
    return json_response(agdb.estatisticas_mensal(meses))


@app.route('/api/agenda/proximos')
def api_agenda_proximos():
    limite = request.args.get('limite', 20, type=int)
    return json_response(agdb.proximos_agendados(limite))


@app.route('/api/agenda/tempo-espera')
def api_agenda_tempo_espera():
    dias = request.args.get('dias', 30, type=int)
    return json_response(agdb.tempo_espera_medio(dias))


@app.route('/api/agenda/semana')
def api_agenda_semana():
    data = request.args.get('data', None)
    prof = request.args.get('prof', None, type=int)
    return json_response(agdb.agenda_semana(data, prof))


@app.route('/api/agenda/buscar')
def api_agenda_buscar():
    inicio = request.args.get('inicio')
    fim = request.args.get('fim')
    if not inicio or not fim:
        return json_response({'erro': 'Parametros inicio e fim sao obrigatorios'}, 400)
    prof = request.args.get('prof', None, type=int)
    sit = request.args.get('sit', None, type=int)
    limite = request.args.get('limite', 200, type=int)
    return json_response(agdb.buscar_agenda(inicio, fim, prof, sit, limite))


# ==================== AGENDA - PAGINA ====================

HTML_PAGE_AGENDA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Medicine Dream - Agenda</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
    --bg: #1a1a2e;
    --bg2: #16213e;
    --bg3: #0f3460;
    --accent: #e94560;
    --text: #eee;
    --text2: #aab;
    --text3: #778;
    --border: #2a2a4a;
    --success: #4ecca3;
    --warning: #f0c040;
}

body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}

.header {
    background: var(--bg2);
    border-bottom: 1px solid var(--border);
    padding: 12px 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: sticky;
    top: 0;
    z-index: 100;
}

.header h1 { font-size: 18px; color: var(--accent); white-space: nowrap; }
.header .subtitle { font-size: 14px; color: var(--text2); }
.header .nav-link {
    color: var(--success);
    text-decoration: none;
    font-size: 14px;
    white-space: nowrap;
    font-weight: 500;
}
.header .nav-link:first-of-type { margin-left: auto; }
.header .nav-link:hover { text-decoration: underline; }

.content {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px 24px;
}

/* Controls */
.controls {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.controls input[type="date"],
.controls select {
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg2);
    color: var(--text);
    font-size: 14px;
    outline: none;
}

.controls input[type="date"]:focus,
.controls select:focus { border-color: var(--accent); }

.controls button {
    padding: 8px 14px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg2);
    color: var(--text);
    font-size: 14px;
    cursor: pointer;
    transition: background 0.15s;
}

.controls button:hover { background: var(--bg3); }
.controls button.active,
.controls button.btn-accent {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
    font-weight: 500;
}
.controls button.btn-accent:hover,
.controls button.active:hover { opacity: 0.85; }

.controls .day-label {
    font-size: 14px;
    color: var(--text2);
    margin-left: 8px;
}

.view-toggle {
    display: flex;
    gap: 0;
    margin-left: auto;
}

.view-toggle button {
    border-radius: 0;
    border-right-width: 0;
    font-size: 13px;
    padding: 8px 16px;
}
.view-toggle button:first-child { border-radius: 6px 0 0 6px; }
.view-toggle button:last-child { border-radius: 0 6px 6px 0; border-right-width: 1px; }

/* Summary cards */
.summary-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 12px;
    margin-bottom: 20px;
}

.summary-card {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
}

.summary-card .card-label {
    font-size: 11px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
}

.summary-card .card-value {
    font-size: 26px;
    font-weight: 700;
}

.card-value.v-total { color: var(--text); }
.card-value.v-exec { color: var(--success); }
.card-value.v-agend { color: var(--warning); }
.card-value.v-fila { color: #5dade2; }
.card-value.v-falta { color: var(--accent); }

/* Section */
.section {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 24px;
}

.section-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

/* Table */
.data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.data-table th {
    text-align: left;
    padding: 8px 10px;
    font-size: 11px;
    color: var(--text3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
}

.data-table td {
    padding: 8px 10px;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    vertical-align: middle;
}

.data-table tr:hover td { background: rgba(255,255,255,0.02); }

.data-table .link, a.link {
    color: var(--accent);
    text-decoration: none;
    cursor: pointer;
}
.data-table .link:hover, a.link:hover { text-decoration: underline; }

/* Badges */
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    font-weight: 500;
    white-space: nowrap;
}

.badge-exec { background: rgba(78,204,163,0.2); color: var(--success); }
.badge-agend { background: rgba(240,192,64,0.2); color: var(--warning); }
.badge-fila { background: rgba(93,173,226,0.2); color: #5dade2; }
.badge-atend { background: rgba(155,89,182,0.2); color: #bb8fce; }
.badge-cancel { background: rgba(233,69,96,0.2); color: var(--accent); }
.badge-falta { background: rgba(233,69,96,0.3); color: #f1948a; }
.badge-default { background: rgba(170,170,187,0.2); color: var(--text2); }

.text-muted { color: var(--text3); font-size: 12px; }

/* ==================== CALENDAR ==================== */
.cal-wrapper {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    margin-bottom: 24px;
    overflow: hidden;
}

.cal-header {
    display: grid;
    grid-template-columns: 50px repeat(var(--cal-cols, 6), 1fr);
    border-bottom: 1px solid var(--border);
}

.cal-header-cell {
    padding: 10px 6px;
    text-align: center;
    font-size: 12px;
    color: var(--text2);
    border-right: 1px solid var(--border);
}

.cal-header-cell:last-child { border-right: none; }
.cal-header-cell.today { color: var(--accent); font-weight: 600; }
.cal-header-cell .day-num { font-size: 18px; font-weight: 700; display: block; }

.cal-body {
    display: grid;
    grid-template-columns: 50px repeat(var(--cal-cols, 6), 1fr);
    position: relative;
    overflow-y: auto;
    max-height: 700px;
}

.cal-time-col {
    grid-column: 1;
}

.cal-time-label {
    height: 60px;
    display: flex;
    align-items: flex-start;
    justify-content: center;
    font-size: 11px;
    color: var(--text3);
    padding-top: 2px;
    border-right: 1px solid var(--border);
}

.cal-day-col {
    position: relative;
    border-right: 1px solid var(--border);
    min-height: 100%;
}

.cal-day-col:last-child { border-right: none; }

.cal-hour-line {
    position: absolute;
    left: 0;
    right: 0;
    border-top: 1px solid rgba(255,255,255,0.04);
    height: 60px;
}

.cal-half-line {
    position: absolute;
    left: 0;
    right: 0;
    border-top: 1px dotted rgba(255,255,255,0.02);
}

/* Appointment block */
.cal-block {
    position: absolute;
    left: 2px;
    right: 2px;
    border-radius: 4px;
    padding: 2px 4px;
    font-size: 10px;
    line-height: 1.3;
    overflow: hidden;
    cursor: pointer;
    transition: opacity 0.15s, transform 0.1s;
    z-index: 2;
    border-left: 3px solid;
}

.cal-block:hover {
    opacity: 0.9;
    transform: scale(1.02);
    z-index: 10;
}

.cal-block .cb-time {
    font-weight: 600;
    font-size: 9px;
    opacity: 0.8;
}

.cal-block .cb-name {
    font-weight: 600;
    font-size: 11px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.cal-block .cb-proc {
    font-size: 9px;
    opacity: 0.7;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

/* Block colors by status */
.cal-block.st-exec {
    background: rgba(78,204,163,0.2);
    border-left-color: var(--success);
    color: #c8efe1;
}
.cal-block.st-agend {
    background: rgba(240,192,64,0.18);
    border-left-color: var(--warning);
    color: #f5e6b8;
}
.cal-block.st-fila {
    background: rgba(93,173,226,0.2);
    border-left-color: #5dade2;
    color: #bee0f5;
}
.cal-block.st-atend {
    background: rgba(155,89,182,0.2);
    border-left-color: #bb8fce;
    color: #ddc8eb;
}
.cal-block.st-cancel {
    background: rgba(233,69,96,0.15);
    border-left-color: var(--accent);
    color: #f1a0b0;
}
.cal-block.st-falta {
    background: rgba(233,69,96,0.2);
    border-left-color: #f1948a;
    color: #f1a0b0;
}
.cal-block.st-default {
    background: rgba(170,170,187,0.15);
    border-left-color: var(--text3);
    color: var(--text2);
}

/* Tooltip */
.cal-tooltip {
    display: none;
    position: fixed;
    background: var(--bg3);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 16px;
    font-size: 13px;
    z-index: 200;
    max-width: 320px;
    min-width: 220px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    pointer-events: none;
}

.cal-tooltip.visible { display: block; }

.cal-tooltip .tt-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}
.cal-tooltip .tt-name { font-weight: 600; font-size: 14px; }
.cal-tooltip .tt-id { font-size: 11px; color: var(--text3); }
.cal-tooltip .tt-row { color: var(--text2); margin-bottom: 3px; font-size: 12px; display: flex; gap: 6px; }
.cal-tooltip .tt-label { color: var(--text3); min-width: 75px; flex-shrink: 0; }
.cal-tooltip .tt-val { color: var(--text); }
.cal-tooltip .tt-proc { color: var(--success); font-weight: 500; }
.cal-tooltip .tt-obs { color: var(--warning); font-style: italic; margin-top: 6px; padding-top: 6px; border-top: 1px solid var(--border); font-size: 11px; }

/* Day detail view */
.day-timeline {
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.day-card {
    display: grid;
    grid-template-columns: 70px 1fr;
    gap: 0;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    transition: border-color 0.15s;
}

.day-card:hover { border-color: var(--accent); }

.day-card-time {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 12px 8px;
    border-right: 3px solid var(--border);
    font-size: 13px;
    font-weight: 600;
}

.day-card-time .dc-hora { font-size: 16px; }
.day-card-time .dc-dur { font-size: 11px; color: var(--text3); font-weight: 400; }

.day-card.st-exec .day-card-time { border-right-color: var(--success); }
.day-card.st-agend .day-card-time { border-right-color: var(--warning); }
.day-card.st-fila .day-card-time { border-right-color: #5dade2; }
.day-card.st-atend .day-card-time { border-right-color: #bb8fce; }
.day-card.st-cancel .day-card-time { border-right-color: var(--accent); }
.day-card.st-falta .day-card-time { border-right-color: #f1948a; }

.day-card-body {
    padding: 10px 14px;
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.day-card-body .dc-top {
    display: flex;
    align-items: center;
    gap: 10px;
}

.day-card-body .dc-paciente {
    font-weight: 600;
    font-size: 14px;
    color: var(--text);
}

.day-card-body .dc-paciente a {
    color: var(--text);
    text-decoration: none;
}

.day-card-body .dc-paciente a:hover { color: var(--accent); }

.day-card-body .dc-id {
    font-size: 11px;
    color: var(--text3);
}

.day-card-body .dc-mid {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    font-size: 12px;
}

.day-card-body .dc-proc { color: var(--success); font-weight: 500; }
.day-card-body .dc-prof { color: var(--text2); }

.day-card-body .dc-bottom {
    display: flex;
    gap: 16px;
    font-size: 11px;
    color: var(--text3);
    flex-wrap: wrap;
}

.day-card-body .dc-obs {
    font-size: 11px;
    color: var(--warning);
    font-style: italic;
}

/* Now-line */
.cal-now-line {
    position: absolute;
    left: 0;
    right: 0;
    border-top: 2px solid var(--accent);
    z-index: 5;
    pointer-events: none;
}
.cal-now-line::before {
    content: '';
    position: absolute;
    left: -4px;
    top: -5px;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
}

/* Tabs */
.tabs {
    display: flex;
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 8px 8px 0 0;
    border-bottom: none;
    overflow-x: auto;
}

.tab {
    padding: 12px 20px;
    font-size: 13px;
    color: var(--text2);
    cursor: pointer;
    border-bottom: 2px solid transparent;
    white-space: nowrap;
    transition: color 0.2s, border-color 0.2s;
    user-select: none;
}

.tab:hover { color: var(--text); }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }

.tab-body {
    background: var(--bg2);
    border: 1px solid var(--border);
    border-top: none;
    border-radius: 0 0 8px 8px;
    padding: 20px;
    min-height: 200px;
}

/* Bars */
.bar-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
    font-size: 13px;
}

.bar-label {
    width: 70px;
    text-align: right;
    color: var(--text2);
    flex-shrink: 0;
    font-size: 12px;
}

.bar-track { flex: 1; display: flex; gap: 2px; align-items: center; }

.bar-fill {
    height: 20px;
    border-radius: 3px;
    min-width: 2px;
    transition: width 0.3s;
}

.bar-fill.fill-total { background: var(--text3); }
.bar-fill.fill-exec { background: var(--success); }
.bar-fill.fill-fila { background: #5dade2; }
.bar-fill.fill-atend { background: #bb8fce; }

.bar-value {
    font-size: 11px;
    color: var(--text3);
    white-space: nowrap;
    min-width: 50px;
}

/* Search form */
.search-form {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    flex-wrap: wrap;
    align-items: flex-end;
}

.form-group {
    display: flex;
    flex-direction: column;
    gap: 4px;
}

.form-group label {
    font-size: 11px;
    color: var(--text3);
    text-transform: uppercase;
}

.form-group input,
.form-group select {
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text);
    font-size: 13px;
    outline: none;
}

.form-group input:focus,
.form-group select:focus { border-color: var(--accent); }

.no-data {
    text-align: center;
    padding: 40px;
    color: var(--text3);
    font-size: 14px;
}

.loading {
    text-align: center;
    padding: 40px;
    color: var(--text3);
}

.loading::after {
    content: '';
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-left: 8px;
    vertical-align: middle;
}

@keyframes spin { to { transform: rotate(360deg); } }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }
</style>
</head>
<body>

<div class="header">
    <h1>Medicine Dream</h1>
    <span class="subtitle">Agenda</span>
    <a href="/" class="nav-link">&larr; Pacientes</a>
    <a href="/financeiro" class="nav-link">Financeiro</a>
</div>

<div class="content">
    <!-- Controls -->
    <div class="controls">
        <button onclick="changeNav(-1)">&larr;</button>
        <input type="date" id="dateInput">
        <button onclick="changeNav(1)">&rarr;</button>
        <button class="btn-accent" onclick="goToday()">Hoje</button>
        <select id="profSelect">
            <option value="">Todos os profissionais</option>
        </select>
        <span class="day-label" id="dayLabel"></span>
        <div class="view-toggle">
            <button id="btnSemana" class="active" onclick="setView('semana')">Semana</button>
            <button id="btnDia" onclick="setView('dia')">Dia</button>
        </div>
    </div>

    <!-- Summary cards -->
    <div class="summary-cards" id="summaryCards"></div>

    <!-- Main view area -->
    <div id="mainView">
        <div class="loading">Carregando</div>
    </div>

    <!-- Tabs -->
    <div class="tabs" id="dataTabs">
        <div class="tab active" onclick="switchTab('proximos')">Proximos</div>
        <div class="tab" onclick="switchTab('estatisticas')">Estatisticas</div>
        <div class="tab" onclick="switchTab('espera')">Tempo de Espera</div>
        <div class="tab" onclick="switchTab('buscar')">Buscar</div>
    </div>
    <div class="tab-body" id="tabBody">
        <div class="loading">Carregando</div>
    </div>
</div>

<!-- Tooltip -->
<div class="cal-tooltip" id="calTooltip"></div>

<script>
const MESES = ['', 'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'];
const DIAS_SEMANA = ['Domingo', 'Segunda', 'Terca', 'Quarta', 'Quinta', 'Sexta', 'Sabado'];
const DIAS_CURTO = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'];
const HOUR_START = 7;
const HOUR_END = 21;
const PX_PER_HOUR = 60;

let currentDate = new Date().toISOString().split('T')[0];
let currentProf = '';
let currentView = 'semana';
let currentTab = 'proximos';
let cache = {};
let tooltipData = [];

function esc(str) {
    if (!str) return '';
    const d = document.createElement('div');
    d.textContent = str;
    return d.innerHTML;
}

async function fetchJSON(url) {
    const res = await fetch(url);
    return res.json();
}

function parseDate(s) {
    const p = s.split('-');
    return new Date(parseInt(p[0]), parseInt(p[1]) - 1, parseInt(p[2]));
}

function fmtDate(d) {
    return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

function getMonday(dateStr) {
    const d = parseDate(dateStr);
    const day = d.getDay();
    const diff = day === 0 ? -6 : 1 - day;
    d.setDate(d.getDate() + diff);
    return d;
}

function blockClass(sitId, sitName) {
    const name = (sitName || '').toUpperCase();
    if (sitId === 4 || name.includes('EXECUTADO')) return 'st-exec';
    if (sitId === 1 || name.includes('AGENDADO')) return 'st-agend';
    if (sitId === 2 || name.includes('FILA')) return 'st-fila';
    if (sitId === 3 || name.includes('ATENDIMENTO')) return 'st-atend';
    if (sitId === 6 || name.includes('CANCELADO') || sitId === 8 || sitId === 10) return 'st-cancel';
    if (sitId === 11 || name.includes('COMPARECEU')) return 'st-falta';
    return 'st-default';
}

function badgeForSit(sitId, sitName) {
    const name = (sitName || '').toUpperCase();
    if (sitId === 4 || name.includes('EXECUTADO')) return 'badge-exec';
    if (sitId === 1 || name.includes('AGENDADO')) return 'badge-agend';
    if (sitId === 2 || name.includes('FILA')) return 'badge-fila';
    if (sitId === 3 || name.includes('ATENDIMENTO')) return 'badge-atend';
    if (sitId === 6 || name.includes('CANCELADO') || sitId === 8 || sitId === 10) return 'badge-cancel';
    if (sitId === 11 || name.includes('COMPARECEU')) return 'badge-falta';
    return 'badge-default';
}

function fmtMinutes(mins) {
    if (!mins && mins !== 0) return '-';
    const m = Math.round(mins);
    if (m < 60) return m + 'min';
    return Math.floor(m / 60) + 'h' + String(m % 60).padStart(2, '0');
}

function getInitials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\\s+/);
    if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function parseTime(timeStr) {
    if (!timeStr) return null;
    const parts = timeStr.split(':');
    return parseInt(parts[0]) * 60 + parseInt(parts[1]);
}

function updateLabel() {
    if (currentView === 'semana') {
        const mon = getMonday(currentDate);
        const sat2 = new Date(mon); sat2.setDate(mon.getDate() + 12);
        document.getElementById('dayLabel').textContent =
            String(mon.getDate()).padStart(2,'0') + '/' + String(mon.getMonth()+1).padStart(2,'0') +
            ' - ' +
            String(sat2.getDate()).padStart(2,'0') + '/' + String(sat2.getMonth()+1).padStart(2,'0') + '/' + sat2.getFullYear();
    } else {
        const d = parseDate(currentDate);
        document.getElementById('dayLabel').textContent =
            DIAS_SEMANA[d.getDay()] + ', ' + currentDate.split('-').reverse().join('/');
    }
}

// ==================== VIEW SWITCH ====================

function setView(v) {
    currentView = v;
    document.getElementById('btnSemana').classList.toggle('active', v === 'semana');
    document.getElementById('btnDia').classList.toggle('active', v === 'dia');
    loadMain();
}

function changeNav(delta) {
    const d = parseDate(currentDate);
    d.setDate(d.getDate() + (currentView === 'semana' ? delta * 7 : delta));
    currentDate = fmtDate(d);
    loadMain();
}

function goToday() {
    currentDate = new Date().toISOString().split('T')[0];
    loadMain();
}

// ==================== LOAD ====================

async function loadProfissionais() {
    const data = await fetchJSON('/api/agenda/profissionais');
    const sel = document.getElementById('profSelect');
    data.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.nome;
        sel.appendChild(opt);
    });
}

async function loadMain() {
    document.getElementById('dateInput').value = currentDate;
    updateLabel();
    cache = {};

    const profParam = currentProf ? '&prof=' + currentProf : '';

    if (currentView === 'semana') {
        const mon1 = getMonday(currentDate);
        const mon2 = new Date(mon1); mon2.setDate(mon1.getDate() + 7);
        const d1 = fmtDate(mon1);
        const d2 = fmtDate(mon2);
        const [semana1, semana2, resumo] = await Promise.all([
            fetchJSON('/api/agenda/semana?data=' + d1 + profParam),
            fetchJSON('/api/agenda/semana?data=' + d2 + profParam),
            fetchJSON('/api/agenda/resumo?data=' + currentDate)
        ]);
        renderSummary(resumo);
        renderCalendar2Weeks(semana1, semana2, mon1, mon2);
    } else {
        const [agenda, resumo] = await Promise.all([
            fetchJSON('/api/agenda/dia?data=' + currentDate + profParam),
            fetchJSON('/api/agenda/resumo?data=' + currentDate)
        ]);
        renderSummary(resumo);
        renderDayDetail(agenda);
    }

    loadTab(currentTab);
}

// ==================== SUMMARY ====================

function renderSummary(r) {
    let html = '';
    html += '<div class="summary-card"><div class="card-label">Total</div><div class="card-value v-total">' + r.total + '</div></div>';
    html += '<div class="summary-card"><div class="card-label">Executadas</div><div class="card-value v-exec">' + r.executados + '</div></div>';
    html += '<div class="summary-card"><div class="card-label">Agendadas</div><div class="card-value v-agend">' + r.agendados + '</div></div>';
    html += '<div class="summary-card"><div class="card-label">Na Fila</div><div class="card-value v-fila">' + r.na_fila + '</div></div>';
    html += '<div class="summary-card"><div class="card-label">Nao Compareceu</div><div class="card-value v-falta">' + r.nao_compareceu + '</div></div>';
    document.getElementById('summaryCards').innerHTML = html;
}

// ==================== WEEK CALENDAR ====================

function buildWeekGrid(data, monday) {
    const todayStr = new Date().toISOString().split('T')[0];
    const totalHours = HOUR_END - HOUR_START;
    const totalPx = totalHours * PX_PER_HOUR;
    const numCols = 6;

    // Group data by date string and store in tooltipData
    const byDay = {};
    data.forEach(a => {
        const dateStr = typeof a.data === 'string' ? a.data : '';
        let key = dateStr;
        if (dateStr.includes('/')) {
            const p = dateStr.split('/');
            key = p[2] + '-' + p[1] + '-' + p[0];
        }
        if (!byDay[key]) byDay[key] = [];
        byDay[key].push(a);
    });

    let html = '<div class="cal-wrapper" style="--cal-cols:' + numCols + '">';

    // Header (Mon-Sat)
    html += '<div class="cal-header"><div class="cal-header-cell"></div>';
    for (let i = 0; i < numCols; i++) {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        const ds = fmtDate(d);
        const isToday = ds === todayStr;
        const count = (byDay[ds] || []).length;
        html += '<div class="cal-header-cell' + (isToday ? ' today' : '') + '">';
        html += '<span class="day-num">' + d.getDate() + '</span>';
        html += DIAS_CURTO[d.getDay()];
        if (count > 0) html += ' <span style="opacity:0.5;font-size:10px">(' + count + ')</span>';
        html += '</div>';
    }
    html += '</div>';

    // Body
    html += '<div class="cal-body" style="height:' + totalPx + 'px">';

    // Time labels
    html += '<div class="cal-time-col">';
    for (let h = HOUR_START; h < HOUR_END; h++) {
        const top = (h - HOUR_START) * PX_PER_HOUR;
        html += '<div class="cal-time-label" style="position:absolute;top:' + top + 'px;width:50px;height:' + PX_PER_HOUR + 'px">';
        html += String(h).padStart(2, '0') + ':00</div>';
    }
    html += '</div>';

    // Day columns (Mon-Sat)
    for (let i = 0; i < numCols; i++) {
        const d = new Date(monday);
        d.setDate(monday.getDate() + i);
        const ds = fmtDate(d);
        const isToday = ds === todayStr;

        html += '<div class="cal-day-col" style="grid-column:' + (i + 2) + '">';

        for (let h = HOUR_START; h < HOUR_END; h++) {
            const top = (h - HOUR_START) * PX_PER_HOUR;
            html += '<div class="cal-hour-line" style="top:' + top + 'px"></div>';
            html += '<div class="cal-half-line" style="top:' + (top + 30) + 'px"></div>';
        }

        if (isToday) {
            const now = new Date();
            const nowMin = now.getHours() * 60 + now.getMinutes();
            const nowTop = (nowMin - HOUR_START * 60) * (PX_PER_HOUR / 60);
            if (nowTop >= 0 && nowTop <= totalPx) {
                html += '<div class="cal-now-line" style="top:' + nowTop + 'px"></div>';
            }
        }

        const dayData = byDay[ds] || [];
        dayData.forEach(a => {
            const startMin = parseTime(a.hora);
            if (startMin === null) return;
            const dur = a.duracao || 15;
            const top = (startMin - HOUR_START * 60) * (PX_PER_HOUR / 60);
            const height = Math.max(dur * (PX_PER_HOUR / 60), 14);
            const cls = blockClass(a.situacao_id, a.situacao);
            const initials = getInitials(a.paciente);
            const idx = tooltipData.length;
            tooltipData.push(a);

            html += '<div class="cal-block ' + cls + '" style="top:' + top + 'px;height:' + height + 'px"';
            html += ' data-idx="' + idx + '"';
            html += ' onmouseenter="showTooltip(event,this)"';
            html += ' onmousemove="moveTooltip(event)"';
            html += ' onmouseleave="hideTooltip()"';
            html += ' onclick="window.open(\\'/?pac=' + a.paciente_id + '\\',\\'_blank\\')">';

            if (height >= 30) {
                html += '<div class="cb-time">' + esc(a.hora) + '</div>';
                html += '<div class="cb-name">' + esc(initials) + ' ' + esc(a.paciente) + '</div>';
                if (height >= 42 && a.procedimento) {
                    html += '<div class="cb-proc">' + esc(a.procedimento) + '</div>';
                }
            } else {
                html += '<div class="cb-name" style="font-size:9px">' + esc(initials) + ' ' + esc(a.hora) + '</div>';
            }

            html += '</div>';
        });

        html += '</div>';
    }

    html += '</div></div>';
    return html;
}

function renderCalendar2Weeks(data1, data2, mon1, mon2) {
    tooltipData = [];
    const el = document.getElementById('mainView');
    el.innerHTML = buildWeekGrid(data1, mon1) + buildWeekGrid(data2, mon2);
}

// ==================== DAY DETAIL VIEW ====================

function renderDayDetail(data) {
    const el = document.getElementById('mainView');
    const d = parseDate(currentDate);
    const title = DIAS_SEMANA[d.getDay()] + ', ' + currentDate.split('-').reverse().join('/') + ' - ' + data.length + ' consulta(s)';

    if (!data.length) {
        el.innerHTML = '<div class="section"><div class="section-title">' + title + '</div><div class="no-data">Nenhuma consulta neste dia</div></div>';
        return;
    }

    let html = '<div class="section"><div class="section-title">' + title + '</div>';
    html += '<div class="day-timeline">';

    data.forEach(a => {
        const cls = blockClass(a.situacao_id, a.situacao);
        const badge = badgeForSit(a.situacao_id, a.situacao);

        html += '<div class="day-card ' + cls + '">';

        // Left: hora + duracao
        html += '<div class="day-card-time">';
        html += '<div class="dc-hora">' + esc(a.hora || '') + '</div>';
        html += '<div class="dc-dur">' + fmtMinutes(a.duracao) + '</div>';
        html += '</div>';

        // Right: detalhes
        html += '<div class="day-card-body">';

        // Linha 1: paciente + id + status
        html += '<div class="dc-top">';
        html += '<span class="dc-paciente"><a href="/?pac=' + a.paciente_id + '" target="_blank">' + esc(a.paciente) + '</a></span>';
        html += '<span class="dc-id">#' + a.paciente_id + '</span>';
        html += '<span class="badge ' + badge + '">' + esc(a.situacao || '') + '</span>';
        html += '</div>';

        // Linha 2: procedimento + profissional
        html += '<div class="dc-mid">';
        if (a.procedimento) html += '<span class="dc-proc">' + esc(a.procedimento) + '</span>';
        if (a.profissional) html += '<span class="dc-prof">' + esc(a.profissional) + '</span>';
        html += '</div>';

        // Linha 3: tempos (fila, atendimento)
        const tempos = [];
        if (a.hora_fila) tempos.push('Fila: ' + esc(a.hora_fila) + (a.tempo_fila ? ' (' + fmtMinutes(a.tempo_fila) + ')' : ''));
        if (a.hora_atendimento) tempos.push('Atend: ' + esc(a.hora_atendimento) + (a.tempo_atendimento ? ' (' + fmtMinutes(a.tempo_atendimento) + ')' : ''));
        if (tempos.length) {
            html += '<div class="dc-bottom">' + tempos.map(t => '<span>' + t + '</span>').join('') + '</div>';
        }

        // Linha 4: observacao
        if (a.observacao) {
            html += '<div class="dc-obs">' + esc(a.observacao) + '</div>';
        }

        html += '</div></div>';
    });

    html += '</div></div>';
    el.innerHTML = html;
}

// ==================== TOOLTIP ====================

function showTooltip(event, el) {
    const idx = parseInt(el.getAttribute('data-idx'));
    const a = tooltipData[idx];
    if (!a) return;
    const tt = document.getElementById('calTooltip');

    let html = '<div class="tt-header">';
    html += '<span class="tt-name">' + esc(a.paciente) + '</span>';
    html += '<span class="tt-id">#' + a.paciente_id + '</span>';
    html += '</div>';

    html += '<div class="tt-row"><span class="tt-label">Horario</span><span class="tt-val">' + esc(a.hora || '') + ' - ' + fmtMinutes(a.duracao) + '</span></div>';

    if (a.procedimento) {
        html += '<div class="tt-row"><span class="tt-label">Procedimento</span><span class="tt-val tt-proc">' + esc(a.procedimento) + '</span></div>';
    }
    if (a.profissional) {
        html += '<div class="tt-row"><span class="tt-label">Profissional</span><span class="tt-val">' + esc(a.profissional) + '</span></div>';
    }
    if (a.situacao) {
        html += '<div class="tt-row"><span class="tt-label">Status</span><span class="tt-val"><span class="badge ' + badgeForSit(a.situacao_id, a.situacao) + '">' + esc(a.situacao) + '</span></span></div>';
    }
    if (a.hora_fila) {
        html += '<div class="tt-row"><span class="tt-label">Entrou fila</span><span class="tt-val">' + esc(a.hora_fila);
        if (a.tempo_fila) html += ' (' + fmtMinutes(a.tempo_fila) + ' espera)';
        html += '</span></div>';
    }
    if (a.hora_atendimento) {
        html += '<div class="tt-row"><span class="tt-label">Atendimento</span><span class="tt-val">' + esc(a.hora_atendimento);
        if (a.tempo_atendimento) html += ' (' + fmtMinutes(a.tempo_atendimento) + ')';
        html += '</span></div>';
    }
    if (a.observacao) {
        html += '<div class="tt-obs">' + esc(a.observacao) + '</div>';
    }

    tt.innerHTML = html;
    tt.classList.add('visible');
    positionTooltip(event);
}

function moveTooltip(event) {
    positionTooltip(event);
}

function positionTooltip(event) {
    const tt = document.getElementById('calTooltip');
    const rect = tt.getBoundingClientRect();
    let x = event.clientX + 14;
    let y = event.clientY + 14;
    if (x + rect.width > window.innerWidth - 8) x = event.clientX - rect.width - 14;
    if (y + rect.height > window.innerHeight - 8) y = event.clientY - rect.height - 14;
    tt.style.left = x + 'px';
    tt.style.top = y + 'px';
}

function hideTooltip() {
    document.getElementById('calTooltip').classList.remove('visible');
}

// ==================== TABS ====================

function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('#dataTabs .tab').forEach((t, i) => {
        const tabMap = ['proximos', 'estatisticas', 'espera', 'buscar'];
        t.classList.toggle('active', tabMap[i] === tab);
    });
    loadTab(tab);
}

async function loadTab(tab) {
    const body = document.getElementById('tabBody');

    if (tab === 'proximos') {
        if (cache.proximos) { renderProximos(cache.proximos); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.proximos = await fetchJSON('/api/agenda/proximos?limite=30');
        renderProximos(cache.proximos);
    } else if (tab === 'estatisticas') {
        if (cache.estatisticas) { renderEstatisticas(cache.estatisticas); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.estatisticas = await fetchJSON('/api/agenda/estatisticas?meses=6');
        renderEstatisticas(cache.estatisticas);
    } else if (tab === 'espera') {
        if (cache.espera) { renderEspera(cache.espera); return; }
        body.innerHTML = '<div class="loading">Carregando</div>';
        cache.espera = await fetchJSON('/api/agenda/tempo-espera?dias=30');
        renderEspera(cache.espera);
    } else if (tab === 'buscar') {
        renderBuscarForm();
    }
}

function renderProximos(data) {
    const body = document.getElementById('tabBody');
    if (!data.length) { body.innerHTML = '<div class="no-data">Nenhuma consulta futura agendada</div>'; return; }

    let html = '<div style="overflow-x:auto"><table class="data-table">';
    html += '<thead><tr><th>Data</th><th>Hora</th><th>Paciente</th><th>Procedimento</th><th>Profissional</th></tr></thead><tbody>';
    data.forEach(a => {
        html += '<tr>';
        html += '<td style="white-space:nowrap">' + esc(a.data) + '</td>';
        html += '<td style="white-space:nowrap">' + esc(a.hora || '') + '</td>';
        html += '<td><a class="link" href="/?pac=' + a.paciente_id + '" target="_blank">' + esc(a.paciente) + '</a></td>';
        html += '<td style="color:var(--success)">' + esc(a.procedimento || '') + '</td>';
        html += '<td>' + esc(a.profissional || '') + '</td>';
        html += '</tr>';
    });
    html += '</tbody></table></div>';
    body.innerHTML = html;
}

function renderEstatisticas(data) {
    const body = document.getElementById('tabBody');
    if (!data.length) { body.innerHTML = '<div class="no-data">Sem dados no periodo</div>'; return; }
    const maxVal = Math.max(...data.map(m => m.total));
    let html = '';
    data.forEach(m => {
        const label = MESES[m.mes] + '/' + String(m.ano).slice(2);
        const execPct = maxVal > 0 ? (m.executados / maxVal * 100) : 0;
        const totalPct = maxVal > 0 ? (m.total / maxVal * 100) : 0;
        html += '<div class="bar-row"><span class="bar-label">' + label + '</span><div class="bar-track"><div class="bar-fill fill-exec" style="width:' + execPct + '%"></div></div><span class="bar-value" style="color:var(--success)">' + m.executados + ' exec</span></div>';
        html += '<div class="bar-row" style="margin-bottom:12px"><span class="bar-label"></span><div class="bar-track"><div class="bar-fill fill-total" style="width:' + totalPct + '%;opacity:0.4"></div></div><span class="bar-value">' + m.total + ' total</span></div>';
    });
    body.innerHTML = html;
}

function renderEspera(data) {
    const body = document.getElementById('tabBody');
    if (!data.length) { body.innerHTML = '<div class="no-data">Sem dados no periodo</div>'; return; }
    const maxVal = Math.max(...data.map(d => Math.max(d.tempo_medio_fila, d.tempo_medio_atendimento)), 1);
    let html = '<div style="margin-bottom:12px;font-size:12px;color:var(--text3)"><span style="display:inline-block;width:12px;height:12px;background:#5dade2;border-radius:2px;margin-right:4px;vertical-align:middle"></span> Fila <span style="display:inline-block;width:12px;height:12px;background:#bb8fce;border-radius:2px;margin-right:4px;margin-left:12px;vertical-align:middle"></span> Atendimento</div>';
    data.forEach(d => {
        const fPct = (d.tempo_medio_fila / maxVal * 100);
        const aPct = (d.tempo_medio_atendimento / maxVal * 100);
        html += '<div class="bar-row"><span class="bar-label">' + esc(d.data) + '</span><div class="bar-track"><div class="bar-fill fill-fila" style="width:' + fPct + '%"></div></div><span class="bar-value">' + fmtMinutes(d.tempo_medio_fila) + '</span></div>';
        html += '<div class="bar-row" style="margin-bottom:10px"><span class="bar-label"></span><div class="bar-track"><div class="bar-fill fill-atend" style="width:' + aPct + '%"></div></div><span class="bar-value">' + fmtMinutes(d.tempo_medio_atendimento) + ' (' + d.total_pacientes + ' pac)</span></div>';
    });
    body.innerHTML = html;
}

function renderBuscarForm() {
    const body = document.getElementById('tabBody');
    if (body.querySelector('.search-form')) return;
    const today = new Date().toISOString().split('T')[0];
    const weekAgo = new Date(Date.now() - 7 * 86400000).toISOString().split('T')[0];
    let html = '<div class="search-form">';
    html += '<div class="form-group"><label>Data Inicio</label><input type="date" id="buscaInicio" value="' + weekAgo + '"></div>';
    html += '<div class="form-group"><label>Data Fim</label><input type="date" id="buscaFim" value="' + today + '"></div>';
    html += '<div class="form-group"><label>Profissional</label><select id="buscaProf"><option value="">Todos</option></select></div>';
    html += '<div class="form-group"><label>Situacao</label><select id="buscaSit"><option value="">Todas</option><option value="1">Agendado</option><option value="2">Na Fila</option><option value="3">Em Atendimento</option><option value="4">Executado</option><option value="6">Cancelado</option><option value="11">Nao Compareceu</option></select></div>';
    html += '<div class="form-group"><label>&nbsp;</label><button class="btn-accent" style="padding:8px 20px;border:none;border-radius:6px;background:var(--accent);color:#fff;font-size:13px;cursor:pointer;font-weight:500" onclick="executarBusca()">Buscar</button></div>';
    html += '</div><div id="buscaResultados"></div>';
    body.innerHTML = html;
    const sel = document.getElementById('buscaProf');
    const mainSel = document.getElementById('profSelect');
    Array.from(mainSel.options).forEach((opt, i) => {
        if (i === 0) return;
        const o = document.createElement('option');
        o.value = opt.value;
        o.textContent = opt.textContent;
        sel.appendChild(o);
    });
}

async function executarBusca() {
    const inicio = document.getElementById('buscaInicio').value;
    const fim = document.getElementById('buscaFim').value;
    const prof = document.getElementById('buscaProf').value;
    const sit = document.getElementById('buscaSit').value;
    if (!inicio || !fim) { alert('Selecione data inicio e fim'); return; }
    const res = document.getElementById('buscaResultados');
    res.innerHTML = '<div class="loading">Carregando</div>';
    let url = '/api/agenda/buscar?inicio=' + inicio + '&fim=' + fim;
    if (prof) url += '&prof=' + prof;
    if (sit) url += '&sit=' + sit;
    const data = await fetchJSON(url);
    if (!data.length) { res.innerHTML = '<div class="no-data">Nenhum resultado encontrado</div>'; return; }
    let html = '<div style="margin-bottom:8px;font-size:12px;color:var(--text3)">' + data.length + ' resultado(s)</div>';
    html += '<div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Data</th><th>Hora</th><th>Paciente</th><th>Procedimento</th><th>Profissional</th><th>Situacao</th></tr></thead><tbody>';
    data.forEach(a => {
        const badge = badgeForSit(a.situacao_id, a.situacao);
        html += '<tr><td style="white-space:nowrap">' + esc(a.data) + '</td><td style="white-space:nowrap">' + esc(a.hora || '') + '</td><td><a class="link" href="/?pac=' + a.paciente_id + '" target="_blank">' + esc(a.paciente) + '</a></td><td style="color:var(--success)">' + esc(a.procedimento || '') + '</td><td>' + esc(a.profissional || '') + '</td><td><span class="badge ' + badge + '">' + esc(a.situacao || '') + '</span></td></tr>';
    });
    html += '</tbody></table></div>';
    res.innerHTML = html;
}

// ==================== INIT ====================

document.getElementById('dateInput').addEventListener('change', function() {
    currentDate = this.value;
    loadMain();
});

document.getElementById('profSelect').addEventListener('change', function() {
    currentProf = this.value;
    loadMain();
});

loadProfissionais();
loadMain();
</script>

</body>
</html>
"""


@app.route('/agenda')
def agenda():
    return render_template_string(HTML_PAGE_AGENDA)


if __name__ == '__main__':
    print("Medicine Dream - Interface Web")
    print("Acesse: http://localhost:5000")
    print("Agenda: http://localhost:5000/agenda")
    print("Financeiro: http://localhost:5000/financeiro")
    app.run(debug=True, host='0.0.0.0', port=5000)
