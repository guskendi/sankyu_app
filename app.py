from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os, json

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///sankyu.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "sankyu-dev-secret")

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

    professor = db.relationship("Professor", backref="videos")

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

@app.route("/api/videos", methods=["GET"])
def list_videos():
    return jsonify([v.to_dict() for v in Video.query.order_by(Video.criado_em.desc()).all()])

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

with app.app_context():
    db.create_all()
    if Professor.query.count() == 0:
        for nome, instr in [("Kenji","Shamisen"),("Yuki","Koto"),("Hana","Shinobue"),
                            ("Taro","Shakuhachi"),("Mika","Taiko"),("Ren","Canto Minyo")]:
            db.session.add(Professor(nome=nome, instrumento=instr))
        db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
