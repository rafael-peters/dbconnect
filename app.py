"""
Interface web para consulta de pacientes - Medicine Dream
Flask app com dark theme SPA
"""

import json
from datetime import datetime, date, time
from flask import Flask, jsonify, request, render_template_string, Response
from paciente import MedicineDB, SITUACOES_AGENDA, TIPOS_DOCUMENTO, TIPOS_TELEFONE

app = Flask(__name__)

# Conexao global
db = MedicineDB()
db.conectar()


class MedicineEncoder(json.JSONEncoder):
    """Encoder customizado para datetime/date/time/bytes do Firebird"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%d/%m/%Y %H:%M')
        if isinstance(obj, date):
            return obj.strftime('%d/%m/%Y')
        if isinstance(obj, time):
            return obj.strftime('%H:%M')
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


if __name__ == '__main__':
    print("Medicine Dream - Interface Web")
    print("Acesse: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
