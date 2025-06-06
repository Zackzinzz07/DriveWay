from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import sqlite3

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'chave-secreta-segura'
jwt = JWTManager(app)

# Conexão com o banco
def get_db_connection():
    conn = sqlite3.connect('transporte.db')
    conn.row_factory = sqlite3.Row
    return conn

# Criação das tabelas do banco de dados
def criar_tabelas():
    conn = get_db_connection()
    with conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            nome TEXT NOT NULL,
                            email TEXT UNIQUE NOT NULL,
                            senha TEXT NOT NULL,
                            tipo TEXT NOT NULL)''')

        conn.execute('''CREATE TABLE IF NOT EXISTS corridas (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            passageiro_id INTEGER NOT NULL,
                            motorista_id INTEGER,
                            origem TEXT NOT NULL,
                            destino TEXT NOT NULL,
                            status TEXT NOT NULL,
                            preco REAL NOT NULL,
                            avaliacao INTEGER)''')

criar_tabelas()

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        dados = request.form
        conn = get_db_connection()
        try:
            with conn:
                conn.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                             (dados['nome'], dados['email'], dados['senha'], dados['tipo']))
            return redirect(url_for('form_login', msg="Cadastro realizado com sucesso! Faça login."))
        except sqlite3.IntegrityError:
            return render_template("cadastro.html", msg="E-mail já cadastrado."), 400
    return render_template("cadastro.html")

@app.route('/login', methods=['GET', 'POST'])
def form_login():
    if request.method == 'POST':
        dados = request.form
        conn = get_db_connection()
        usuario = conn.execute(
            "SELECT * FROM usuarios WHERE email = ? AND senha = ?",
            (dados['email'], dados['senha'])
        ).fetchone()

        if usuario:
            token = create_access_token(identity=usuario['id'])

            # 👉 se for motorista, vai para o dashboard de corridas
            if usuario['tipo'] == 'motorista':
                return redirect(url_for('dashboard_motorista',
                                        usuario_id=usuario['id']))
            # passageiro continua indo para o perfil
            return redirect(url_for('perfil', usuario_id=usuario['id']))

        return render_template("login.html", msg="Credenciais inválidas."), 401

    msg = request.args.get('msg')
    return render_template("login.html", msg=msg)

@app.route('/dashboard_motorista/<int:usuario_id>')
def dashboard_motorista(usuario_id):
    conn = get_db_connection()
    corridas = conn.execute("SELECT * FROM corridas WHERE status = 'pendente'").fetchall()
    return render_template("dashboard_motorista.html", usuario_id=usuario_id, corridas=corridas)


@app.route('/aceitar_corrida/<int:corrida_id>/<int:motorista_id>', methods=['POST'])
def aceitar_corrida(corrida_id, motorista_id):
    conn = get_db_connection()
    with conn:
        conn.execute('UPDATE corridas SET motorista_id = ?, status = ? WHERE id = ?', 
                     (motorista_id, 'em andamento', corrida_id))
    return redirect(url_for('corrida_em_andamento', corrida_id=corrida_id, motorista_id=motorista_id))

    return render_template('corrida_aceita.html',
                           corrida=corrida,
                           usuario_id=motorista_id)   

@app.route('/corrida_em_andamento/<int:corrida_id>/<int:motorista_id>')
def corrida_em_andamento(corrida_id, motorista_id):
    conn = get_db_connection()
    corrida = conn.execute('SELECT * FROM corridas WHERE id = ?', (corrida_id,)).fetchone()
    return render_template('corrida_em_andamento.html', corrida=corrida, motorista_id=motorista_id)

@app.route('/perfil/<int:usuario_id>')
def perfil(usuario_id):
    conn = get_db_connection()
    usuario = conn.execute("SELECT id, nome, email, tipo FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
    if usuario:
        return render_template("perfil.html", usuario=usuario)
    return render_template("perfil.html", msg="Usuário não encontrado."), 404

from flask import redirect, url_for

@app.route('/finalizar_corrida/<int:corrida_id>/<int:motorista_id>', methods=['POST'])
def finalizar_corrida(corrida_id, motorista_id):
    conn = get_db_connection()
    with conn:
        # muda o status para “finalizada”
        conn.execute("UPDATE corridas SET status = 'finalizada' WHERE id = ?", (corrida_id,))
        # pega o passageiro para saber quem vai avaliar
        corrida = conn.execute("SELECT passageiro_id FROM corridas WHERE id = ?", (corrida_id,)).fetchone()

    # leva o passageiro para a tela de avaliação
    return redirect(url_for('avaliar_corrida',
                            corrida_id=corrida_id,
                            passageiro_id=corrida['passageiro_id']))


@app.route('/solicitar_corrida', methods=['POST'])
def solicitar_corrida():
    dados = request.form
    passageiro_id = dados.get('passageiro_id')
    origem = dados.get('origem')
    destino = dados.get('destino')
    preco_estimado = 25.00

    conn = get_db_connection()
    with conn:
        conn.execute('''INSERT INTO corridas (passageiro_id, motorista_id, origem, destino, status, preco, avaliacao)
                        VALUES (?, NULL, ?, ?, 'pendente', ?, NULL)''',
                     (passageiro_id, origem, destino, preco_estimado))

    # Redirecionar para a nova página após a solicitação
    return redirect(url_for('corrida_confirmada', usuario_id=passageiro_id))

@app.route('/corrida_confirmada/<int:usuario_id>')
def corrida_confirmada(usuario_id):
    return render_template('corrida_confirmada.html', usuario_id=usuario_id)

@app.route('/solicitar_corrida/<int:usuario_id>', methods=['GET'])
def pagina_solicitar_corrida(usuario_id):
    return render_template("solicitar_corrida.html", usuario_id=usuario_id)

@app.route('/avaliar_corrida/<int:corrida_id>/<int:passageiro_id>', methods=['GET', 'POST'])
def avaliar_corrida(corrida_id, passageiro_id):
    if request.method == 'POST':
        nota = request.form.get('avaliacao')
        conn = get_db_connection()
        with conn:
            conn.execute("UPDATE corridas SET avaliacao = ?, status = 'avaliada' WHERE id = ?",
                         (nota, corrida_id))
        # Redireciona ao perfil do usuário após avaliação
        return redirect(url_for('perfil', usuario_id=passageiro_id))

    # GET → mostra o formulário
    return render_template('avaliar_corrida.html',
                           corrida_id=corrida_id,
                           passageiro_id=passageiro_id)


@app.route('/historico/<int:usuario_id>')
@jwt_required()
def historico(usuario_id):
    conn = get_db_connection()
    corridas = conn.execute("SELECT * FROM corridas WHERE passageiro_id = ? OR motorista_id = ?",
                            (usuario_id, usuario_id)).fetchall()
    return render_template("historico.html", corridas=corridas)

if __name__ == '__main__':
    app.run(debug=True)