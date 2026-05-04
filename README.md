# Sankyu — Esteiras de Produção

App web para gerenciar as esteiras de produção de vídeo da Escola de Música Sankyu.

## Estrutura
```
sankyu_app/
├── app.py              ← servidor Flask + banco de dados
├── requirements.txt    ← dependências Python
├── Procfile            ← comando de start para deploy
├── templates/
│   └── index.html      ← toda a interface do app
└── static/
    └── sankyu_logo.png ← coloque a logo aqui (opcional)
```

## Como adicionar a logo

1. Salve a logo da Sankyu como `static/sankyu_logo.png`
2. Abra `templates/index.html`
3. Encontre o comentário `<!-- LOGO: ... -->` no header
4. Descomente a linha `<img src="/static/sankyu_logo.png" ...>`
5. Comente ou remova o bloco `<div class="logo-fallback">...</div>`


## Rodar localmente

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar o app
python app.py

# 3. Abrir no navegador
http://localhost:5000
```

O banco de dados SQLite (`sankyu.db`) é criado automaticamente na primeira execução.


## Deploy gratuito — Railway (recomendado)

Railway é a opção mais simples: deploy com Git, banco PostgreSQL gratuito e HTTPS automático.

### Passo a passo

1. Crie uma conta em https://railway.app (pode usar sua conta GitHub)

2. Crie um novo projeto:
   - Clique em "New Project" → "Deploy from GitHub repo"
   - Conecte o repositório com o código da Sankyu

3. Adicione um banco PostgreSQL:
   - No projeto, clique em "New Service" → "Database" → "PostgreSQL"
   - O Railway cria automaticamente a variável `DATABASE_URL`

4. Configure variáveis de ambiente:
   - Vá em "Variables" no serviço do app
   - Adicione: `SECRET_KEY` = qualquer string aleatória (ex: `sankyu-prod-2024`)

5. O Railway detecta o `Procfile` e faz o deploy automaticamente.

**Plano gratuito Railway:** US$ 5 de crédito mensal — suficiente para um app pequeno rodando o mês todo.


## Deploy alternativo — Render

Render também tem plano gratuito (o app "dorme" após 15 min sem uso, mas acorda sozinho).

1. Crie conta em https://render.com
2. "New Web Service" → conecte o repositório
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Adicione um PostgreSQL gratuito: "New PostgreSQL"
6. Cole a "Internal Database URL" na variável `DATABASE_URL` do serviço


## Variáveis de ambiente necessárias

| Variável       | Descrição                                      |
|----------------|------------------------------------------------|
| `DATABASE_URL` | URL do PostgreSQL (Railway/Render definem auto)|
| `SECRET_KEY`   | String secreta para sessões Flask              |
| `PORT`         | Porta (Railway/Render definem automaticamente) |
