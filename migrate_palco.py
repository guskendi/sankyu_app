"""
Migração — adiciona coluna duracao em palco_musicas.
Execute uma única vez: python migrate_palco.py
"""
import os, sys

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///instance/sankyu.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

print(f"Banco: {DATABASE_URL[:40]}...")

if DATABASE_URL.startswith("sqlite"):
    import sqlite3, re
    path = re.sub(r"^sqlite:///", "", DATABASE_URL)
    if not os.path.exists(path):
        print(f"Arquivo não encontrado: {path}")
        sys.exit(1)
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(palco_musicas)")
    cols = [row[1] for row in cur.fetchall()]
    print(f"Colunas atuais: {cols}")
    if "duracao" not in cols:
        cur.execute("ALTER TABLE palco_musicas ADD COLUMN duracao INTEGER DEFAULT 0")
        conn.commit()
        print("✓ Coluna duracao adicionada!")
    else:
        print("✓ Coluna duracao já existe.")
    conn.close()
else:
    import psycopg2
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("""SELECT column_name FROM information_schema.columns
                   WHERE table_name='palco_musicas' AND column_name='duracao'""")
    if not cur.fetchone():
        cur.execute("ALTER TABLE palco_musicas ADD COLUMN duracao INTEGER DEFAULT 0")
        print("✓ Coluna duracao adicionada no PostgreSQL!")
    else:
        print("✓ Coluna duracao já existe.")
    cur.close(); conn.close()

# Also migrate scout_musicas
if DATABASE_URL.startswith("sqlite"):
    import sqlite3, re
    path = re.sub(r"^sqlite:///", "", DATABASE_URL)
    if os.path.exists(path):
        conn2 = sqlite3.connect(path)
        cur2 = conn2.cursor()
        cur2.execute("PRAGMA table_info(scout_musicas)")
        cols2 = [row[1] for row in cur2.fetchall()]
        if "duracao" not in cols2:
            cur2.execute("ALTER TABLE scout_musicas ADD COLUMN duracao INTEGER DEFAULT 0")
            conn2.commit()
            print("✓ Coluna duracao adicionada em scout_musicas!")
        else:
            print("✓ scout_musicas.duracao já existe.")
        conn2.close()
else:
    conn3 = psycopg2.connect(DATABASE_URL)
    conn3.autocommit = True
    cur3 = conn3.cursor()
    cur3.execute("""SELECT column_name FROM information_schema.columns
                    WHERE table_name='scout_musicas' AND column_name='duracao'""")
    if not cur3.fetchone():
        cur3.execute("ALTER TABLE scout_musicas ADD COLUMN duracao INTEGER DEFAULT 0")
        print("✓ Coluna duracao adicionada em scout_musicas (PostgreSQL)!")
    else:
        print("✓ scout_musicas.duracao já existe.")
    cur3.close(); conn3.close()

# Also migrate palco_pessoas.ativo
if DATABASE_URL.startswith("sqlite"):
    import sqlite3, re
    path = re.sub(r"^sqlite:///", "", DATABASE_URL)
    if os.path.exists(path):
        conn4 = sqlite3.connect(path)
        cur4 = conn4.cursor()
        cur4.execute("PRAGMA table_info(palco_pessoas)")
        cols4 = [row[1] for row in cur4.fetchall()]
        if "ativo" not in cols4:
            cur4.execute("ALTER TABLE palco_pessoas ADD COLUMN ativo INTEGER DEFAULT 1")
            conn4.commit()
            print("✓ Coluna ativo adicionada em palco_pessoas!")
        else:
            print("✓ palco_pessoas.ativo já existe.")
        conn4.close()
else:
    conn5 = psycopg2.connect(DATABASE_URL)
    conn5.autocommit = True
    cur5 = conn5.cursor()
    cur5.execute("""SELECT column_name FROM information_schema.columns
                    WHERE table_name='palco_pessoas' AND column_name='ativo'""")
    if not cur5.fetchone():
        cur5.execute("ALTER TABLE palco_pessoas ADD COLUMN ativo BOOLEAN DEFAULT TRUE")
        print("✓ Coluna ativo adicionada em palco_pessoas (PostgreSQL)!")
    else:
        print("✓ palco_pessoas.ativo já existe.")
    cur5.close(); conn5.close()

print("Migração concluída.")
