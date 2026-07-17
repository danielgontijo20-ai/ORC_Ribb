-- ORC_Ribb - Schema do banco de dados SQLite
-- Etapa 3: estrutura que recebe os dados da planilha Banco_RBT.xlsx

PRAGMA foreign_keys = ON;

-- Clientes extraídos do histórico de faturamento (CNPJ/CPF únicos)
CREATE TABLE IF NOT EXISTS clientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cnpj_cpf TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    uf TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Lista de nomes de segmento (Etiqueta Branca, Ribbon, etc.)
CREATE TABLE IF NOT EXISTS segmentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL UNIQUE
);

-- Produtos cadastrados (principalmente da aba Segmento)
CREATE TABLE IF NOT EXISTS produtos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    descricao TEXT NOT NULL,
    segmento_id INTEGER,
    ativo INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY (segmento_id) REFERENCES segmentos(id)
);

-- Matérias-primas (aba Materia_Prima)
CREATE TABLE IF NOT EXISTS materias_primas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    preco_compra REAL,
    custo REAL NOT NULL,
    ultima_atualizacao TEXT,
    observacoes TEXT
);

-- Tubetes (aba Tubetes)
CREATE TABLE IF NOT EXISTS tubetes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    preco_compra REAL,
    custo REAL NOT NULL
);

-- Caixas (aba Caixas)
CREATE TABLE IF NOT EXISTS caixas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    nome TEXT NOT NULL,
    custo REAL NOT NULL
);

-- Facas (aba Facas)
CREATE TABLE IF NOT EXISTS facas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo TEXT NOT NULL UNIQUE,
    tipo_faca TEXT NOT NULL,
    largura REAL NOT NULL,
    altura REAL NOT NULL,
    gap_lateral REAL NOT NULL DEFAULT 0,
    gap_vertical REAL,
    area REAL NOT NULL
);

-- Histórico de faturamento / NF-e (aba Faturamento)
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

CREATE INDEX IF NOT EXISTS idx_faturamento_cliente
    ON faturamento(cliente_id);

CREATE INDEX IF NOT EXISTS idx_faturamento_codigo_item
    ON faturamento(codigo_item);

CREATE INDEX IF NOT EXISTS idx_faturamento_cliente_codigo
    ON faturamento(cliente_id, codigo_item);

CREATE INDEX IF NOT EXISTS idx_faturamento_data
    ON faturamento(data_emissao);

CREATE INDEX IF NOT EXISTS idx_produtos_descricao
    ON produtos(descricao);

-- Orçamentos (usado nas próximas etapas)
CREATE TABLE IF NOT EXISTS orcamentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id INTEGER,
    cliente_avulso_nome TEXT,
    cliente_avulso_documento TEXT,
    tipo TEXT NOT NULL CHECK (tipo IN ('etiqueta', 'suprimentos')),
    status TEXT NOT NULL DEFAULT 'rascunho'
        CHECK (status IN ('rascunho', 'finalizado', 'cancelado')),
    observacoes TEXT,
    lucro_total REAL DEFAULT 0,
    valor_total REAL DEFAULT 0,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    atualizado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS orcamento_itens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    orcamento_id INTEGER NOT NULL,
    tipo_item TEXT NOT NULL CHECK (tipo_item IN ('etiqueta', 'suprimentos', 'avulso')),
    produto_id INTEGER,
    codigo_item TEXT,
    descricao TEXT NOT NULL,
    segmento TEXT,
    quantidade REAL NOT NULL DEFAULT 1,
    custo_unitario REAL,
    preco_unitario REAL,
    preco_total REAL,
    lucro_unitario REAL,
    lucro_total REAL,
    preco_ultima_venda REAL,
    data_ultima_venda TEXT,
    parametros_json TEXT,
    criado_em TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (orcamento_id) REFERENCES orcamentos(id) ON DELETE CASCADE,
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

CREATE INDEX IF NOT EXISTS idx_orcamento_itens_orcamento
    ON orcamento_itens(orcamento_id);
