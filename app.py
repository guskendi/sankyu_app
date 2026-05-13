from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import joinedload
from datetime import datetime
import os, json

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///sankyu.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "sankyu-dev-secret")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,       # verifica conexão antes de usar
    "pool_recycle": 280,         # recicla conexões a cada ~4.5 min (Neon fecha idle em 5min)
    "pool_size": 3,              # máximo 3 conexões simultâneas (free tier tem limite)
    "max_overflow": 2,           # até 2 conexões extras em pico
    "connect_args": {"connect_timeout": 10} if not DATABASE_URL.startswith("sqlite") else {},
}

db = SQLAlchemy(app)

# ── Modelos ───────────────────────────────────────────────────────────────────

class Professor(db.Model):
    __tablename__ = "professores"
    id          = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome        = db.Column(db.String(100), nullable=False)
    instrumento = db.Column(db.String(100), nullable=False)
    ativo       = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome, "instrumento": self.instrumento, "ativo": self.ativo}


class TipoProposito(db.Model):
    __tablename__ = "tipos_proposito"
    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(150), nullable=False, unique=True)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome}


class Video(db.Model):
    __tablename__ = "videos"

    id               = db.Column(db.String(20), primary_key=True)
    titulo           = db.Column(db.String(200), nullable=False)
    tipo             = db.Column(db.String(100), default="")
    professor_id     = db.Column(db.Integer, db.ForeignKey("professores.id"), nullable=True)
    obs              = db.Column(db.Text, default="")

    usa_roteiro      = db.Column(db.Boolean, default=True)
    usa_gravacao     = db.Column(db.Boolean, default=True)
    usa_edicao       = db.Column(db.Boolean, default=True)
    usa_publicacao   = db.Column(db.Boolean, default=True)

    status_roteiro   = db.Column(db.String(20), default="pendente")
    status_gravacao  = db.Column(db.String(20), default="pendente")
    status_edicao    = db.Column(db.String(20), default="pendente")
    status_publicacao = db.Column(db.String(20), default="pendente")

    roteiro_texto    = db.Column(db.Text, default="")
    gravacao_data    = db.Column(db.String(50), default="")
    gravacao_horario = db.Column(db.String(20), default="")
    gravacao_local   = db.Column(db.String(200), default="")
    edicao_caminho   = db.Column(db.Text, default="")
    pub_data         = db.Column(db.String(50), default="")
    pub_plataformas  = db.Column(db.String(300), default="[]")

    criado_em        = db.Column(db.DateTime, default=datetime.utcnow)
    roteiro_feito_em = db.Column(db.DateTime, nullable=True)
    gravacao_feita_em= db.Column(db.DateTime, nullable=True)
    edicao_feita_em  = db.Column(db.DateTime, nullable=True)
    publicado_em     = db.Column(db.DateTime, nullable=True)
    concluido_em     = db.Column(db.DateTime, nullable=True)

    professor = db.relationship("Professor", backref="videos", lazy="joined")

    def _active_stages(self):
        s = []
        if self.usa_roteiro:    s.append("roteiro")
        if self.usa_gravacao:   s.append("gravacao")
        if self.usa_edicao:     s.append("edicao")
        if self.usa_publicacao: s.append("publicacao")
        return s

    def _current_stage(self):
        for s in self._active_stages():
            if getattr(self, f"status_{s}") != "done":
                return s
        return None

    def is_concluido(self):
        stages = self._active_stages()
        return bool(stages) and all(getattr(self, f"status_{s}") == "done" for s in stages)

    def to_dict(self):
        try:
            plat = json.loads(self.pub_plataformas) if self.pub_plataformas else []
        except Exception:
            plat = []
        return {
            "id": self.id, "titulo": self.titulo, "tipo": self.tipo,
            "professor": self.professor.to_dict() if self.professor else None,
            "obs": self.obs,
            "esteiras": {"roteiro": self.usa_roteiro, "gravacao": self.usa_gravacao,
                         "edicao": self.usa_edicao, "publicacao": self.usa_publicacao},
            "statusRoteiro": self.status_roteiro, "statusGravacao": self.status_gravacao,
            "statusEdicao": self.status_edicao, "statusPublicacao": self.status_publicacao,
            "roteiroTexto": self.roteiro_texto,
            "gravacaoData": self.gravacao_data, "gravacaoHorario": self.gravacao_horario,
            "gravacaoLocal": self.gravacao_local, "edicaoCaminho": self.edicao_caminho,
            "pubData": self.pub_data, "pubPlataformas": plat,
            "currentStage": self._current_stage(), "activeStages": self._active_stages(),
            "criadoEm": self.criado_em.isoformat() if self.criado_em else None,
            "roteiroFeitoEm": self.roteiro_feito_em.isoformat() if self.roteiro_feito_em else None,
            "gravacaoFeitaEm": self.gravacao_feita_em.isoformat() if self.gravacao_feita_em else None,
            "edicaoFeitaEm": self.edicao_feita_em.isoformat() if self.edicao_feita_em else None,
            "publicadoEm": self.publicado_em.isoformat() if self.publicado_em else None,
            "concluídoEm": self.concluido_em.isoformat() if self.concluido_em else None,
        }

# ── Rotas ─────────────────────────────────────────────────────────────────────

@app.route("/")
@app.route("/producao")
def index():
    return render_template("index.html")

@app.route("/api/professores", methods=["GET"])
def list_professores():
    return jsonify([p.to_dict() for p in Professor.query.filter_by(ativo=True).order_by(Professor.nome).all()])

@app.route("/api/professores", methods=["POST"])
def create_professor():
    data = request.json
    p = Professor(nome=data["nome"].strip(), instrumento=data["instrumento"].strip())
    db.session.add(p); db.session.commit()
    return jsonify(p.to_dict()), 201

@app.route("/api/professores/<int:pid>", methods=["PUT"])
def update_professor(pid):
    p = Professor.query.get_or_404(pid); data = request.json
    if "nome" in data: p.nome = data["nome"].strip()
    if "instrumento" in data: p.instrumento = data["instrumento"].strip()
    db.session.commit(); return jsonify(p.to_dict())

@app.route("/api/professores/<int:pid>", methods=["DELETE"])
def delete_professor(pid):
    p = Professor.query.get_or_404(pid); p.ativo = False
    db.session.commit(); return jsonify({"ok": True})

@app.route("/api/tipos", methods=["GET"])
def list_tipos():
    return jsonify([t.to_dict() for t in TipoProposito.query.order_by(TipoProposito.nome).all()])

@app.route("/api/tipos", methods=["POST"])
def create_tipo():
    data = request.json
    nome = data.get("nome", "").strip()
    if not nome:
        return jsonify({"error": "Nome obrigatório"}), 400
    if TipoProposito.query.filter_by(nome=nome).first():
        return jsonify({"error": "Tipo já existe"}), 409
    t = TipoProposito(nome=nome)
    db.session.add(t); db.session.commit()
    return jsonify(t.to_dict()), 201

@app.route("/api/tipos/<int:tid>", methods=["PUT"])
def update_tipo(tid):
    t = TipoProposito.query.get_or_404(tid)
    nome = request.json.get("nome", "").strip()
    if not nome:
        return jsonify({"error": "Nome obrigatório"}), 400
    t.nome = nome; db.session.commit()
    return jsonify(t.to_dict())

@app.route("/api/tipos/<int:tid>", methods=["DELETE"])
def delete_tipo(tid):
    t = TipoProposito.query.get_or_404(tid)
    db.session.delete(t); db.session.commit()
    return jsonify({"ok": True})

@app.route("/api/videos", methods=["GET"])
def list_videos():
    videos = Video.query.options(
        joinedload(Video.professor)
    ).order_by(Video.criado_em.desc()).all()
    return jsonify([v.to_dict() for v in videos])

@app.route("/api/videos", methods=["POST"])
def create_video():
    data = request.json; e = data.get("esteiras", {})
    v = Video(
        id=str(int(datetime.utcnow().timestamp() * 1000)),
        titulo=data["titulo"].strip(), tipo=data.get("tipo", ""),
        professor_id=data.get("professor_id") or None, obs=data.get("obs", ""),
        usa_roteiro=e.get("roteiro", True), usa_gravacao=e.get("gravacao", True),
        usa_edicao=e.get("edicao", True), usa_publicacao=e.get("publicacao", True),
    )
    db.session.add(v); db.session.commit(); return jsonify(v.to_dict()), 201

@app.route("/api/videos/<vid_id>", methods=["PUT"])
def update_video(vid_id):
    v = Video.query.get_or_404(vid_id); data = request.json
    for f in ["titulo","tipo","obs","roteiro_texto","gravacao_data","gravacao_horario",
              "gravacao_local","edicao_caminho","pub_data"]:
        if f in data: setattr(v, f, data[f])
    if "professor_id" in data: v.professor_id = data["professor_id"] or None
    if "pub_plataformas" in data: v.pub_plataformas = json.dumps(data["pub_plataformas"])
    db.session.commit(); return jsonify(v.to_dict())

@app.route("/api/videos/<vid_id>/toggle", methods=["POST"])
def toggle_status(vid_id):
    v = Video.query.get_or_404(vid_id); esteira = request.json.get("esteira")
    if esteira not in {"roteiro","gravacao","edicao","publicacao"}:
        return jsonify({"error": "inválido"}), 400
    cur = getattr(v, f"status_{esteira}")
    ns = "done" if cur != "done" else "pendente"
    setattr(v, f"status_{esteira}", ns)
    ts = {"roteiro":"roteiro_feito_em","gravacao":"gravacao_feita_em",
          "edicao":"edicao_feita_em","publicacao":"publicado_em"}
    setattr(v, ts[esteira], datetime.utcnow() if ns == "done" else None)
    v.concluido_em = datetime.utcnow() if v.is_concluido() else None
    db.session.commit(); return jsonify(v.to_dict())

@app.route("/api/videos/<vid_id>", methods=["DELETE"])
def delete_video(vid_id):
    v = Video.query.get_or_404(vid_id); db.session.delete(v)
    db.session.commit(); return jsonify({"ok": True})

@app.route("/api/stats", methods=["GET"])
def stats():
    videos = Video.query.all()
    return jsonify([{
        "id": v.id, "tipo": v.tipo,
        "professor": v.professor.to_dict() if v.professor else None,
        "criadoEm": v.criado_em.isoformat() if v.criado_em else None,
        "roteiroFeitoEm": v.roteiro_feito_em.isoformat() if v.roteiro_feito_em else None,
        "gravacaoFeitaEm": v.gravacao_feita_em.isoformat() if v.gravacao_feita_em else None,
        "edicaoFeitaEm": v.edicao_feita_em.isoformat() if v.edicao_feita_em else None,
        "publicadoEm": v.publicado_em.isoformat() if v.publicado_em else None,
        "pubData": v.pub_data, "pubPlataformas": v.pub_plataformas,
    } for v in videos])


# ═══════════════════════════════════════════════════════════════════════════════
# MÓDULO SCOUT
# ═══════════════════════════════════════════════════════════════════════════════

SCOUT_SENHA = os.environ.get("SCOUT_SENHA", "S@nkyu2018")

INSTRUMENTOS_PADRAO = ["Shamisen","Taiko","Shinobue","Shakuhachi","Koto","Canto Minyo"]

MUSICAS_PADRAO = [
    "Soran Bushi","Tsugaru Jinku","Hanagasa Ondo","Tokyo Ondo","Hokkai Bon Uta",
    "Kuroda Bushi","Tanko Bushi","Kokiriko Bushi","Setsugekka","Nada no Sakazuri Iwai Uta",
    "Rokudan","Kyu Bushi","Shikisai 1.8","Saitaro Bushi","Sanpo","Binks no Sake",
    "Itsudemo Dareka Ga","Akita Ondo","Souma Bon Uta","Hobashira Okoshi Ondo","Otemoyan",
    "Donpan Bushi","Nambu Tawaratsumi","Aizu Baidasan","Shan shan uma douchuu",
    "Chakkiri Bushi","Owase Bushi","Mogamigawa","Tanto Bushi","Asa Branca","Anunciação",
    "Awa Odori","Kachou Fuugetsu","Hitohira","Senbonzakura","Sansa Odori",
    "Sanshin no Hana","Shimanchuu no Takara","Funakogi Nagashi uta","Shunpu",
]

NIVEIS = {0:"Ainda não sei",1:"Iniciante",2:"Em evolução",
          3:"Com acompanhamento",4:"Toca sozinho",5:"Proficiente"}

# ── Modelos Scout ──────────────────────────────────────────────────────────────

class Instrumento(db.Model):
    __tablename__ = "scout_instrumentos"
    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    def to_dict(self): return {"id":self.id,"nome":self.nome}

class Musica(db.Model):
    __tablename__ = "scout_musicas"
    id   = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome = db.Column(db.String(200), nullable=False, unique=True)
    def to_dict(self): return {"id":self.id,"nome":self.nome}

class Aluno(db.Model):
    __tablename__ = "scout_alunos"
    id         = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nome       = db.Column(db.String(150), nullable=False)
    contato    = db.Column(db.String(200), default="")
    obs        = db.Column(db.Text, default="")
    criado_em  = db.Column(db.DateTime, default=datetime.utcnow)
    fichas     = db.relationship("FichaAluno", backref="aluno", cascade="all,delete-orphan")

    def to_dict(self):
        return {"id":self.id,"nome":self.nome,"contato":self.contato,
                "obs":self.obs,"criadoEm":self.criado_em.isoformat() if self.criado_em else None}

class FichaAluno(db.Model):
    __tablename__ = "scout_fichas"
    id            = db.Column(db.Integer, primary_key=True, autoincrement=True)
    aluno_id      = db.Column(db.Integer, db.ForeignKey("scout_alunos.id"), nullable=False)
    instrumento_id= db.Column(db.Integer, db.ForeignKey("scout_instrumentos.id"), nullable=False)
    musica_id     = db.Column(db.Integer, db.ForeignKey("scout_musicas.id"), nullable=False)
    nivel         = db.Column(db.Integer, default=0)  # 0-5
    obs           = db.Column(db.String(300), default="")
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instrumento = db.relationship("Instrumento", lazy="joined")
    musica      = db.relationship("Musica", lazy="joined")

    def to_dict(self):
        return {"id":self.id,"alunoId":self.aluno_id,
                "instrumento":self.instrumento.to_dict() if self.instrumento else None,
                "musica":self.musica.to_dict() if self.musica else None,
                "nivel":self.nivel,"nivelLabel":NIVEIS.get(self.nivel,"—"),
                "obs":self.obs,
                "atualizadoEm":self.atualizado_em.isoformat() if self.atualizado_em else None}

class Evento(db.Model):
    __tablename__ = "scout_eventos"
    id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    tipo      = db.Column(db.String(20), nullable=False)  # 'treino' | 'apresentacao'
    titulo    = db.Column(db.String(200), nullable=False)
    data      = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    obs       = db.Column(db.Text, default="")
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    presencas = db.relationship("Presenca", backref="evento", cascade="all,delete-orphan")

    def to_dict(self):
        return {"id":self.id,"tipo":self.tipo,"titulo":self.titulo,
                "data":self.data.isoformat() if self.data else None,
                "obs":self.obs,"totalPresencas":len(self.presencas),
                "criadoEm":self.criado_em.isoformat() if self.criado_em else None}

class Presenca(db.Model):
    __tablename__ = "scout_presencas"
    id        = db.Column(db.Integer, primary_key=True, autoincrement=True)
    evento_id = db.Column(db.Integer, db.ForeignKey("scout_eventos.id"), nullable=False)
    nome      = db.Column(db.String(150), nullable=False)
    aluno_id  = db.Column(db.Integer, db.ForeignKey("scout_alunos.id"), nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    aluno = db.relationship("Aluno", lazy="joined")

    def to_dict(self):
        return {"id":self.id,"eventoId":self.evento_id,"nome":self.nome,
                "alunoId":self.aluno_id,
                "alunoNome":self.aluno.nome if self.aluno else None,
                "criadoEm":self.criado_em.isoformat() if self.criado_em else None}


# ── Rotas Scout — páginas ──────────────────────────────────────────────────────

@app.route("/scout")
def scout_index():
    senha = request.args.get("senha","")
    if senha != SCOUT_SENHA:
        return render_template("scout_login.html")
    return render_template("scout.html", senha=SCOUT_SENHA)

@app.route("/scout/login", methods=["POST"])
def scout_login():
    from flask import redirect, url_for
    senha = request.form.get("senha","")
    if senha == SCOUT_SENHA:
        return redirect(f"/scout?senha={SCOUT_SENHA}")
    return render_template("scout_login.html", erro=True)

@app.route("/cadastro")
def cadastro_index():
    return render_template("scout_cadastro.html")

@app.route("/checkin/<tipo>")
def checkin_page(tipo):
    if tipo not in ("treino","apresentacao"):
        return "Página não encontrada", 404
    return render_template("scout_checkin.html", tipo=tipo)


# ── Rotas Scout — API instrumentos ────────────────────────────────────────────

@app.route("/api/scout/instrumentos")
def scout_list_instrumentos():
    return jsonify([i.to_dict() for i in Instrumento.query.order_by(Instrumento.nome).all()])

@app.route("/api/scout/instrumentos", methods=["POST"])
def scout_create_instrumento():
    nome = request.json.get("nome","").strip()
    if not nome: return jsonify({"error":"Nome obrigatório"}),400
    if Instrumento.query.filter_by(nome=nome).first(): return jsonify({"error":"Já existe"}),409
    i = Instrumento(nome=nome); db.session.add(i); db.session.commit()
    return jsonify(i.to_dict()),201

@app.route("/api/scout/instrumentos/<int:iid>", methods=["PUT"])
def scout_update_instrumento(iid):
    i = Instrumento.query.get_or_404(iid)
    i.nome = request.json.get("nome",i.nome).strip()
    db.session.commit(); return jsonify(i.to_dict())

@app.route("/api/scout/instrumentos/<int:iid>", methods=["DELETE"])
def scout_delete_instrumento(iid):
    i = Instrumento.query.get_or_404(iid); db.session.delete(i)
    db.session.commit(); return jsonify({"ok":True})


# ── Rotas Scout — API músicas ──────────────────────────────────────────────────

@app.route("/api/scout/musicas")
def scout_list_musicas():
    return jsonify([m.to_dict() for m in Musica.query.order_by(Musica.nome).all()])

@app.route("/api/scout/musicas", methods=["POST"])
def scout_create_musica():
    nome = request.json.get("nome","").strip()
    if not nome: return jsonify({"error":"Nome obrigatório"}),400
    if Musica.query.filter_by(nome=nome).first(): return jsonify({"error":"Já existe"}),409
    m = Musica(nome=nome); db.session.add(m); db.session.commit()
    return jsonify(m.to_dict()),201

@app.route("/api/scout/musicas/<int:mid>", methods=["PUT"])
def scout_update_musica(mid):
    m = Musica.query.get_or_404(mid)
    m.nome = request.json.get("nome",m.nome).strip()
    db.session.commit(); return jsonify(m.to_dict())

@app.route("/api/scout/musicas/<int:mid>", methods=["DELETE"])
def scout_delete_musica(mid):
    m = Musica.query.get_or_404(mid); db.session.delete(m)
    db.session.commit(); return jsonify({"ok":True})


# ── Rotas Scout — API alunos ──────────────────────────────────────────────────

@app.route("/api/scout/alunos")
def scout_list_alunos():
    alunos = Aluno.query.order_by(Aluno.nome).all()
    return jsonify([a.to_dict() for a in alunos])

@app.route("/api/scout/alunos", methods=["POST"])
def scout_create_aluno():
    data = request.json
    nome = data.get("nome","").strip()
    if not nome: return jsonify({"error":"Nome obrigatório"}),400
    a = Aluno(nome=nome, contato=data.get("contato",""), obs=data.get("obs",""))
    db.session.add(a); db.session.commit()
    return jsonify(a.to_dict()),201

@app.route("/api/scout/alunos/<int:aid>", methods=["PUT"])
def scout_update_aluno(aid):
    a = Aluno.query.get_or_404(aid); data = request.json
    if "nome" in data: a.nome = data["nome"].strip()
    if "contato" in data: a.contato = data["contato"]
    if "obs" in data: a.obs = data["obs"]
    db.session.commit(); return jsonify(a.to_dict())

@app.route("/api/scout/alunos/<int:aid>", methods=["DELETE"])
def scout_delete_aluno(aid):
    a = Aluno.query.get_or_404(aid); db.session.delete(a)
    db.session.commit(); return jsonify({"ok":True})

@app.route("/api/scout/alunos/<int:aid>/fichas")
def scout_aluno_fichas(aid):
    fichas = FichaAluno.query.options(
        joinedload(FichaAluno.instrumento),
        joinedload(FichaAluno.musica)
    ).filter_by(aluno_id=aid).all()
    return jsonify([f.to_dict() for f in fichas])


# ── Rotas Scout — API fichas ──────────────────────────────────────────────────

@app.route("/api/scout/fichas", methods=["POST"])
def scout_create_ficha():
    data = request.json
    # upsert: se já existe aluno+instrumento+musica, atualiza o nível
    existing = FichaAluno.query.filter_by(
        aluno_id=data["aluno_id"],
        instrumento_id=data["instrumento_id"],
        musica_id=data["musica_id"]
    ).first()
    if existing:
        existing.nivel = int(data.get("nivel",0))
        existing.obs   = data.get("obs","")
        existing.atualizado_em = datetime.utcnow()
        db.session.commit(); return jsonify(existing.to_dict())
    f = FichaAluno(aluno_id=data["aluno_id"], instrumento_id=data["instrumento_id"],
                   musica_id=data["musica_id"], nivel=int(data.get("nivel",0)),
                   obs=data.get("obs",""))
    db.session.add(f); db.session.commit()
    return jsonify(f.to_dict()),201

@app.route("/api/scout/fichas/<int:fid>", methods=["PUT"])
def scout_update_ficha(fid):
    f = FichaAluno.query.get_or_404(fid); data = request.json
    if "nivel" in data: f.nivel = int(data["nivel"])
    if "obs" in data: f.obs = data["obs"]
    f.atualizado_em = datetime.utcnow()
    db.session.commit(); return jsonify(f.to_dict())

@app.route("/api/scout/fichas/<int:fid>", methods=["DELETE"])
def scout_delete_ficha(fid):
    f = FichaAluno.query.get_or_404(fid); db.session.delete(f)
    db.session.commit(); return jsonify({"ok":True})

@app.route("/api/scout/fichas/bulk", methods=["POST"])
def scout_bulk_fichas():
    """Salva múltiplas fichas de uma vez (usado no formulário de cadastro e ficha do scout)."""
    items = request.json.get("fichas",[])
    if not items:
        return jsonify({"ok":True,"count":0})
    count = 0
    for item in items:
        aluno_id      = item.get("aluno_id")
        instrumento_id= item.get("instrumento_id")
        musica_id     = item.get("musica_id")
        nivel         = int(item.get("nivel",0))
        if not all([aluno_id, instrumento_id, musica_id]):
            continue
        existing = FichaAluno.query.filter_by(
            aluno_id=aluno_id, instrumento_id=instrumento_id,
            musica_id=musica_id).first()
        if existing:
            existing.nivel = nivel
            existing.atualizado_em = datetime.utcnow()
        else:
            db.session.add(FichaAluno(
                aluno_id=aluno_id, instrumento_id=instrumento_id,
                musica_id=musica_id, nivel=nivel))
        count += 1
    db.session.commit()
    return jsonify({"ok":True,"count":count})


# ── Rotas Scout — API eventos ──────────────────────────────────────────────────

@app.route("/api/scout/eventos")
def scout_list_eventos():
    from sqlalchemy import func
    # Use a subquery to count presencas without loading them all
    presenca_count = db.session.query(
        Presenca.evento_id,
        func.count(Presenca.id).label("total")
    ).group_by(Presenca.evento_id).subquery()

    evts = db.session.query(Evento).order_by(Evento.data.desc()).all()
    counts = {row.evento_id: row.total for row in db.session.query(presenca_count).all()}

    result = []
    for e in evts:
        d = {"id":e.id,"tipo":e.tipo,"titulo":e.titulo,
             "data":e.data.isoformat() if e.data else None,
             "obs":e.obs,"totalPresencas":counts.get(e.id,0),
             "criadoEm":e.criado_em.isoformat() if e.criado_em else None}
        result.append(d)
    return jsonify(result)

@app.route("/api/scout/eventos/<int:eid>")
def scout_get_evento(eid):
    e = Evento.query.options(
        joinedload(Evento.presencas).joinedload(Presenca.aluno)
    ).get_or_404(eid)
    d = {"id":e.id,"tipo":e.tipo,"titulo":e.titulo,
         "data":e.data.isoformat() if e.data else None,
         "obs":e.obs,"totalPresencas":len(e.presencas),
         "criadoEm":e.criado_em.isoformat() if e.criado_em else None}
    d["presencas"] = [p.to_dict() for p in e.presencas]
    return jsonify(d)

@app.route("/api/scout/eventos", methods=["POST"])
def scout_create_evento():
    data = request.json
    e = Evento(tipo=data["tipo"], titulo=data["titulo"],
               data=datetime.strptime(data["data"],"%Y-%m-%d").date(),
               obs=data.get("obs",""))
    db.session.add(e); db.session.commit(); return jsonify(e.to_dict()),201

@app.route("/api/scout/eventos/<int:eid>", methods=["PUT"])
def scout_update_evento(eid):
    e = Evento.query.get_or_404(eid); data = request.json
    if "titulo" in data: e.titulo = data["titulo"]
    if "obs" in data: e.obs = data["obs"]
    db.session.commit(); return jsonify(e.to_dict())

@app.route("/api/scout/eventos/<int:eid>", methods=["DELETE"])
def scout_delete_evento(eid):
    e = Evento.query.get_or_404(eid); db.session.delete(e)
    db.session.commit(); return jsonify({"ok":True})


# ── Rotas Scout — API presenças ────────────────────────────────────────────────

@app.route("/api/scout/presencas/<int:eid>")
def scout_list_presencas(eid):
    ps = Presenca.query.filter_by(evento_id=eid).order_by(Presenca.criado_em).all()
    return jsonify([p.to_dict() for p in ps])

@app.route("/api/scout/presencas/<int:pid>", methods=["DELETE"])
def scout_delete_presenca(pid):
    p = Presenca.query.get_or_404(pid); db.session.delete(p)
    db.session.commit(); return jsonify({"ok":True})

@app.route("/api/scout/eventos/<int:eid>/presencas", methods=["POST"])
def scout_add_presenca_manual(eid):
    evt = Evento.query.get_or_404(eid)
    nome = request.json.get("nome","").strip()
    if not nome:
        return jsonify({"error":"Nome obrigatório"}),400
    # avoid duplicate
    ja = Presenca.query.filter_by(evento_id=eid, nome=nome).first()
    if ja:
        return jsonify({"ok":True,"msg":"Presença já registrada","presenca":ja.to_dict()})
    p = Presenca(evento_id=eid, nome=nome)
    db.session.add(p); db.session.commit()
    return jsonify({"ok":True,"presenca":p.to_dict()}),201

@app.route("/api/scout/presencas/<int:pid>/vincular", methods=["POST"])
def scout_vincular_presenca(pid):
    p = Presenca.query.get_or_404(pid)
    aluno_id = request.json.get("aluno_id")
    if aluno_id:
        Aluno.query.get_or_404(aluno_id)
        p.aluno_id = aluno_id
    else:
        p.aluno_id = None
    db.session.commit()
    return jsonify(p.to_dict())


# ── Rota pública — check-in via QR ────────────────────────────────────────────

@app.route("/api/checkin", methods=["POST"])
def checkin():
    data  = request.json
    tipo  = data.get("tipo")   # 'treino' | 'apresentacao'
    nome  = data.get("nome","").strip()
    if not nome or tipo not in ("treino","apresentacao"):
        return jsonify({"error":"Dados inválidos"}),400

    hoje  = datetime.utcnow().date()
    tipo_label = "Treino em Conjunto" if tipo=="treino" else "Apresentação"
    titulo = f"{tipo_label} — {hoje.strftime('%d/%m/%Y')}"

    # cria o evento do dia se ainda não existe
    evt = Evento.query.filter_by(tipo=tipo, data=hoje).first()
    if not evt:
        evt = Evento(tipo=tipo, titulo=titulo, data=hoje)
        db.session.add(evt); db.session.flush()

    # evita duplicata de nome no mesmo evento
    ja = Presenca.query.filter_by(evento_id=evt.id, nome=nome).first()
    if ja:
        return jsonify({"ok":True,"msg":"Presença já registrada!","evento":evt.to_dict()})

    p = Presenca(evento_id=evt.id, nome=nome)
    db.session.add(p); db.session.commit()
    return jsonify({"ok":True,"msg":"Presença confirmada!","evento":evt.to_dict()})


# ── Rota pública — cadastro de aluno ──────────────────────────────────────────

@app.route("/api/cadastro", methods=["POST"])
def cadastro_aluno():
    data   = request.json
    nome   = data.get("nome","").strip()
    if not nome: return jsonify({"error":"Nome obrigatório"}),400
    contato = data.get("contato","")
    a = Aluno(nome=nome, contato=contato)
    db.session.add(a); db.session.flush()
    fichas = data.get("fichas",[])
    for item in fichas:
        f = FichaAluno(aluno_id=a.id, instrumento_id=item["instrumento_id"],
                       musica_id=item["musica_id"], nivel=int(item.get("nivel",0)))
        db.session.add(f)
    db.session.commit()
    return jsonify({"ok":True,"alunoId":a.id}),201


# ── Rota — gerar QR codes ─────────────────────────────────────────────────────

@app.route("/api/scout/qrcode/<tipo>")
def gerar_qrcode(tipo):
    if tipo not in ("treino","apresentacao","cadastro"):
        return jsonify({"error":"Tipo inválido"}),400
    try:
        import qrcode
        base_url = request.host_url.rstrip("/")
        url = f"{base_url}/checkin/{tipo}" if tipo != "cadastro" else f"{base_url}/cadastro"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8, border=3)
        qr.add_data(url)
        qr.make(fit=True)

        # Build clean pixel-based SVG from matrix (no Pillow, no mm units)
        matrix = qr.get_matrix()
        box = 8
        border = 3
        dim = (len(matrix) + border * 2) * box
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{dim}" height="{dim}" viewBox="0 0 {dim} {dim}">',
                 f'<rect width="{dim}" height="{dim}" fill="white"/>']
        for r, row in enumerate(matrix):
            for c, val in enumerate(row):
                if val:
                    x = (c + border) * box
                    y = (r + border) * box
                    parts.append(f'<rect x="{x}" y="{y}" width="{box}" height="{box}" fill="black"/>')
        parts.append('</svg>')
        svg = ''.join(parts)
        return jsonify({"url": url, "svg": svg})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


with app.app_context():
    db.create_all()
    if Professor.query.count() == 0:
        for pnome, instr in [("Kenji","Shamisen"),("Yuki","Koto"),("Hana","Shinobue"),
                            ("Taro","Shakuhachi"),("Mika","Taiko"),("Ren","Canto Minyo")]:
            db.session.add(Professor(nome=pnome, instrumento=instr))
        db.session.commit()
    if TipoProposito.query.count() == 0:
        for tnome in ["Informativo","Chamada de evento","Chamada de aula experimental",
                     "Trecho de apresentação","Trecho de aula","Bastidores / treino"]:
            db.session.add(TipoProposito(nome=tnome))
        db.session.commit()
    if Instrumento.query.count() == 0:
        for inome in INSTRUMENTOS_PADRAO:
            db.session.add(Instrumento(nome=inome))
        db.session.commit()
    if Musica.query.count() == 0:
        for mnome in MUSICAS_PADRAO:
            db.session.add(Musica(nome=mnome))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
