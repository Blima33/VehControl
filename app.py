from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta'  # Necessária para usar flash


# === Criação do banco e tabelas ===
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Tabela de veículos (movimentação)
    c.execute('''CREATE TABLE IF NOT EXISTS veiculos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        responsavel TEXT NOT NULL,
        placa TEXT NOT NULL,
        ano TEXT,
        modelo TEXT,
        entrada TEXT NOT NULL,
        saida TEXT
    )''')

    # Tabela de colaboradores (cadastro)
    c.execute('''
        CREATE TABLE IF NOT EXISTS colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_proprietario TEXT NOT NULL,
            veiculo TEXT,
            marca TEXT,
            modelo TEXT,
            ano_fabricacao INTEGER,
            placa TEXT UNIQUE NOT NULL
        )
    ''')

    conn.commit()
    conn.close()


init_db()


# === Função utilitária ===
def buscar_colaborador_por_placa(placa):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('SELECT nome_proprietario FROM colaboradores WHERE placa = ?', (placa.upper(),))
    resultado = c.fetchone()
    conn.close()
    return resultado[0] if resultado else None


# === Rotas ===

@app.route('/')
def index():
    return redirect(url_for('entrada'))


@app.route('/entrada', methods=['GET', 'POST'])
def entrada():
    if request.method == 'POST':
        placa = request.form['placa'].upper()

        responsavel = buscar_colaborador_por_placa(placa)

        if 'confirmar' in request.form:
            if not responsavel:
                responsavel = request.form['responsavel']

            entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn = sqlite3.connect('database.db')
            c = conn.cursor()
            c.execute("INSERT INTO veiculos (responsavel, placa, ano, modelo, entrada) VALUES (?, ?, ?, ?, ?)",
                      (responsavel, placa, None, None, entrada))
            conn.commit()
            conn.close()

            flash("Entrada registrada com sucesso!")
            return redirect(url_for('entrada'))
        else:
            if not responsavel:
                responsavel = request.form['responsavel']

            return render_template('confirmar_entrada.html', responsavel=responsavel, placa=placa)

    return render_template('entrada.html')


@app.route('/saida', methods=['GET', 'POST'])
def saida():
    if request.method == 'POST':
        placa = request.form['placa'].upper()

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("""SELECT id, responsavel, placa, entrada FROM veiculos 
                     WHERE placa=? AND saida IS NULL ORDER BY entrada DESC LIMIT 1""", (placa,))
        row = c.fetchone()
        conn.close()

        if row:
            veiculo = {
                'id': row[0],
                'responsavel': row[1],
                'placa': row[2],
                'entrada': row[3]
            }
            return render_template('saida.html', veiculo=veiculo)
        else:
            return render_template('saida.html', erro="Veículo não encontrado ou já saiu.")

    return render_template('saida.html')


@app.route('/confirmar_saida/<int:id>', methods=['POST'])
def confirmar_saida(id):
    saida = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("UPDATE veiculos SET saida=? WHERE id=?", (saida, id))
    conn.commit()
    conn.close()
    return render_template('sucesso.html', mensagem="Saída registrada com sucesso!")


# === Rota do Relatório com Filtro de Data ===
@app.route('/relatorio', methods=['GET', 'POST'])
def relatorio():
    registros = []
    data_inicio = request.form.get('data_inicio')
    data_fim = request.form.get('data_fim')

    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    query = "SELECT responsavel, placa, entrada, saida FROM veiculos WHERE 1=1"
    params = []

    # Filtros de data (intervalo)
    if data_inicio:
        data_inicio_dt = datetime.strptime(data_inicio, "%Y-%m-%d")
        query += " AND datetime(entrada) >= ?"
        params.append(data_inicio_dt.strftime("%Y-%m-%d 00:00:00"))

    if data_fim:
        data_fim_dt = datetime.strptime(data_fim, "%Y-%m-%d")
        query += " AND datetime(entrada) <= ?"
        params.append(data_fim_dt.strftime("%Y-%m-%d 23:59:59"))

    query += " ORDER BY datetime(entrada) DESC"
    c.execute(query, params)
    registros = c.fetchall()
    conn.close()

    # Função auxiliar para formatar data/hora
    def formatar_data(data_str):
        if not data_str:
            return "-"
        dt = datetime.strptime(data_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d/%m/%Y %H:%M")

    registros_formatados = [
        {
            "responsavel": r[0],
            "placa": r[1],
            "entrada": formatar_data(r[2]),
            "saida": formatar_data(r[3])
        }
        for r in registros
    ]

    return render_template(
        'relatorio.html',
        registros=registros_formatados,
        data_inicio=data_inicio,
        data_fim=data_fim
    )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
