-- ORC_Ribb - Schema do banco de dados SQLite

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj_cpf TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    uf TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS segmentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    segmento_id INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (segmento_id) REFERENCES segmentos(id)
);

CREATE TABLE IF NOT EXISTS materias_primas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    nome_exibicao_orc TEXT,
    preco_compra REAL,
    custo REAL NOT NULL,
    ultima_atualizacao TEXT,
    observacoes TEXT
);

CREATE TABLE IF NOT EXISTS tubetes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    nome_exibicao_orc TEXT,
    preco_compra REAL,
    custo REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS caixas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    custo REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS facas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    tipo_faca TEXT NOT NULL,
    nome_exibicao_orc TEXT,
    largura REAL NOT NULL,
    altura REAL NOT NULL,
    gap_lateral REAL NOT NULL DEFAULT 0,
    gap_vertical REAL,
    area REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS suprimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    marca TEXT,
    descricao TEXT NOT NULL,
    nome_exibicao TEXT,
    preco_compra REAL,
    custo REAL NOT NULL,
    ativo INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS faturamento (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_nota TEXT,
    cliente_id INTEGER,
    cnpj_cpf TEXT,
    nome_cliente TEXT,
    data_emissao TEXT,
    situacao TEXT,
    uf TEXT,
    natureza TEXT,
    finalidade TEXT,
    descricao_item TEXT,
    codigo_item TEXT,
    unidade TEXT,
    quantidade REAL,
    valor_unitario REAL,
    valor_total REAL,
    ncm TEXT,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE INDEX IF NOT EXISTS idx_faturamento_cliente ON faturamento(cliente_id);
CREATE INDEX IF NOT EXISTS idx_faturamento_codigo_item ON faturamento(codigo_item);
CREATE INDEX IF NOT EXISTS idx_faturamento_cliente_codigo ON faturamento(cliente_id, codigo_item);
CREATE INDEX IF NOT EXISTS idx_faturamento_data ON faturamento(data_emissao);
CREATE INDEX IF NOT EXISTS idx_faturamento_numero ON faturamento(numero_nota);
CREATE INDEX IF NOT EXISTS idx_produtos_descricao ON produtos(descricao);

-- Configurações / valores nativos (chave-valor)
CREATE TABLE IF NOT EXISTS configuracoes (
    chave TEXT PRIMARY KEY,
    valor TEXT
);

CREATE TABLE IF NOT EXISTS orcamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT,
    cliente_id INTEGER,
    cliente_avulso_nome TEXT,
    cliente_avulso_documento TEXT,
    solicitante TEXT,
    status TEXT NOT NULL DEFAULT 'rascunho'
        CHECK (status IN ('rascunho', 'finalizado', 'cancelado')),
    validade_proposta TEXT,
    prazo_pagamento TEXT,
    prazo_entrega TEXT,
    frete_tipo TEXT,
    frete_taxa REAL,
    impostos TEXT,
    informacoes_adicionais TEXT,
    orcamentista_nome TEXT,
    orcamentista_cargo TEXT,
    orcamentista_telefone TEXT,
    orcamentista_email TEXT,
    lucro_total REAL DEFAULT 0,
    valor_total REAL DEFAULT 0,
    frete_total REAL DEFAULT 0,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS orcamento_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER NOT NULL,
    tipo_item TEXT NOT NULL CHECK (tipo_item IN ('etiqueta', 'suprimentos')),
    produto_id INTEGER,
    codigo_item TEXT,
    descricao TEXT NOT NULL,
    segmento TEXT,
    unidade TEXT,
    quantidade REAL NOT NULL DEFAULT 1,
    custo_unitario REAL,
    preco_unitario REAL,
    preco_total REAL,
    lucro_unitario REAL,
    lucro_total REAL,
    frete_item REAL DEFAULT 0,
    preco_ultima_venda REAL,
    data_ultima_venda TEXT,
    parametros_json TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

CREATE INDEX IF NOT EXISTS idx_orcamento_itens_orcamento ON orcamento_itens(orcamento_id);
