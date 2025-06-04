from flask import Flask, request, jsonify, render_template
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import sqlite3

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'chave-secreta-segura'
jwt = JWTManager(app)

# Criação das tabelas do banco de dados
def criar_tabelas():
    conn = sqlite3.connect('transporte.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY,
                    nome TEXT,
                    email TEXT UNIQUE,
                    senha TEXT,
                    tipo TEXT)''')  # tipo = 'motorista' ou 'passageiro'

    c.execute('''CREATE TABLE IF NOT EXISTS corridas (
                    id INTEGER PRIMARY KEY,
                    passageiro_id INTEGER,
                    motorista_id INTEGER,
                    origem TEXT,
                    destino TEXT,
                    status TEXT,
                    preco REAL,
                    avaliacao INTEGER)''')
    conn.commit()
    conn.close()

criar_tabelas()

@app.route('/')
def index():
    print("Rota / foi acessada com sucesso")
    return render_template("index.html")

# Página de formulário de cadastro (GET)
@app.route('/cadastro', methods=['GET'])
def form_cadastro():
    return render_template("cadastro.html")

# Cadastro (POST)
@app.route('/cadastro', methods=['POST'])
def cadastro():
    dados = request.form
    conn = sqlite3.connect('transporte.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios (nome, email, senha, tipo) VALUES (?, ?, ?, ?)",
                  (dados['nome'], dados['email'], dados['senha'], dados['tipo']))
        conn.commit()
        return render_template("login.html", msg="Cadastro realizado com sucesso! Faça login.")
    except sqlite3.IntegrityError:
        return render_template("cadastro.html", msg="E-mail já cadastrado."), 400
    finally:
        conn.close()


# Página de formulário de login (GET)
@app.route('/login', methods=['GET'])
def form_login():
    return render_template("login.html")

# Login (POST)
@app.route('/login', methods=['POST'])
def login():
    dados = request.form
    conn = sqlite3.connect('transporte.db')
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE email = ? AND senha = ?", (dados['email'], dados['senha']))
    usuario = c.fetchone()
    conn.close()
    if usuario:
        token = create_access_token(identity=usuario[0])
        return render_template("login.html", msg="Login bem-sucedido! Token gerado: " + token)
    return render_template("login.html", msg="Credenciais inválidas."), 401

# perfil
@app.route('/perfil/<int:usuario_id>', methods=['GET'])
@jwt_required()
def perfil(usuario_id):
    conn = sqlite3.connect('transporte.db')
    c = conn.cursor()
    c.execute("SELECT id, nome, email, tipo FROM usuarios WHERE id = ?", (usuario_id,))
    usuario = c.fetchone()
    conn.close()

    if usuario:
        return render_template("perfil.html", usuario=usuario)
    else:
        return render_template("perfil.html", msg="Usuário não encontrado."), 404

# Solicitação de corrida
@app.route('/solicitar_corrida', methods=['POST'])
@jwt_required()
def solicitar_corrida():
    dados = request.get_json()
    conn = sqlite3.connect('transporte.db')
    c = conn.cursor()
    preco_estimado = 25.00  # Simulado
    c.execute('''INSERT INTO corridas (passageiro_id, motorista_id, origem, destino, status, preco, avaliacao)
                 VALUES (?, NULL, ?, ?, 'pendente', ?, NULL)''',
              (dados['passageiro_id'], dados['origem'], dados['destino'], preco_estimado))
    conn.commit()
    conn.close()
    return render_template("solicitar_corrida.html", msg="Corrida solicitada com sucesso.", preco_estimado=preco_estimado)

# Página de formulário de avaliação (GET)
@app.route('/avaliar_corrida', methods=['GET'])
def form_avaliar_corrida():
    return render_template("avaliar_corrida.html")

# Avaliação da corrida (POST)
@app.route('/avaliar_corrida', methods=['POST'])
@jwt_required()
def avaliar_corrida():
    corrida_id = request.form.get('corrida_id')
    avaliacao = request.form.get('avaliacao')
    conn = sqlite3.connect('transporte.db')
    c = conn.cursor()
    c.execute("UPDATE corridas SET avaliacao = ? WHERE id = ?", (avaliacao, corrida_id))
    conn.commit()
    conn.close()
    return render_template("avaliar_corrida.html", msg="Avaliação registrada.")

# Histórico do usuário
@app.route('/historico/<int:usuario_id>', methods=['GET'])
@jwt_required()
def historico(usuario_id):
    conn = sqlite3.connect('transporte.db')
    c = conn.cursor()
    c.execute("SELECT * FROM corridas WHERE passageiro_id = ? OR motorista_id = ?", (usuario_id, usuario_id))
    corridas = c.fetchall()
    conn.close()
    return render_template("historico.html", corridas=corridas)

if __name__ == '__main__':
    app.run(debug=True)
