"""
Script de migração — adiciona coluna aluno_id na tabela scout_presencas.
Execute uma única vez no ambiente local E no Neon (produção).

Uso:
    python migrate_presencas.py
"""

import os
import sys

# ── Detecta ambiente ──────────────────────────────────────────────────────────
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/sankyu.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Banco: {DATABASE_URL[:40]}...")

# ── Executa a migração ────────────────────────────────────────────────────────
if DATABASE_URL.startswith("sqlite"):
    import sqlite3, re
    # extrai o caminho do arquivo sqlite
    path = re.sub(r"^sqlite:///", "", DATABASE_URL)
    if not os.path.exists(path):
        print(f"Arquivo não encontrado: {path}")
        print("Verifique se o caminho está correto ou se o banco já existe.")
        sys.exit(1)

    conn = sqlite3.connect(path)
    cur = conn.cursor()

    # verifica se a coluna já existe
    cur.execute("PRAGMA table_info(scout_presencas)")
    cols = [row[1] for row in cur.fetchall()]
    print(f"Colunas atuais: {cols}")

    if "aluno_id" in cols:
        print("✓ Coluna aluno_id já existe. Nada a fazer.")
    else:
        cur.execute("ALTER TABLE scout_presencas ADD COLUMN aluno_id INTEGER REFERENCES scout_alunos(id)")
        conn.commit()
        print("✓ Coluna aluno_id adicionada com sucesso!")

    conn.close()

else:
    # PostgreSQL (Neon / produção)
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 não instalado. Execute: pip install psycopg2-binary")
        sys.exit(1)

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    # verifica se a coluna já existe
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'scout_presencas' AND column_name = 'aluno_id'
    """)
    exists = cur.fetchone()

    if exists:
        print("✓ Coluna aluno_id já existe no PostgreSQL. Nada a fazer.")
    else:
        cur.execute("""
            ALTER TABLE scout_presencas
            ADD COLUMN aluno_id INTEGER REFERENCES scout_alunos(id)
        """)
        print("✓ Coluna aluno_id adicionada no PostgreSQL com sucesso!")

    cur.close()
    conn.close()

print("Migração concluída.")
