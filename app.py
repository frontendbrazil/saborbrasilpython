import json
import os
from flask import Flask, render_template, request, jsonify, session
from bcrypt import hashpw, checkpw, gensalt

app = Flask(__name__)
app.secret_key = "sabor_do_brasil_chave_secreta_2024"

ARQUIVO_DADOS = "usuarios.json"

def ler_dados() -> dict:
    with open(ARQUIVO_DADOS, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def salvar_dados(dados: dict) -> None:
    with open(ARQUIVO_DADOS, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, indent=2, ensure_ascii=False)

def hash_senha(senha_texto_puro: str) -> str:
    senha_bytes = senha_texto_puro.encode("utf-8")
    hash_bytes = hashpw(senha_bytes, gensalt())
    return hash_bytes.decode("utf-8")

def verificar_senha(senha_texto_puro: str, senha_hash: str) -> bool:
    senha_bytes = senha_texto_puro.encode("utf-8")
    hash_bytes = senha_hash.encode("utf-8")
    return checkpw(senha_bytes, hash_bytes)

def usuario_pode_editar(id_usuario_acao: int, id_autor_comentario: int) -> bool:
    dados = ler_dados()

    for usuario in dados["usuarios"]:
        if usuario["id"] == id_usuario_acao:
            if usuario["perfil"] == "admin":
                return True
            if id_usuario_acao == id_autor_comentario:
                return True

    return False

@app.route("/")
def home():
    dados = ler_dados()
    usuario_logado = session.get("usuario")
    return render_template("index.html", receitas=dados["receitas"], usuario=usuario_logado)

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    corpo = request.get_json()
    nickname = corpo.get("nickname", "").strip()
    senha = corpo.get("senha", "").strip()

    if not nickname or not senha:
        return jsonify({"erro": "Preencha todos os campos"}), 400

    dados = ler_dados()

    for usuario in dados["usuarios"]:
        if usuario["nickname"].lower() == nickname.lower():
            return jsonify({"erro": "Nickname já está em uso"}), 409

    senha_hash = hash_senha(senha)

    novo_usuario = {
        "id": dados["proximo_usuario_id"],
        "nickname": nickname,
        "senha": senha_hash,
        "perfil": "comum"
    }

    dados["usuarios"].append(novo_usuario)
    dados["proximo_usuario_id"] += 1

    salvar_dados(dados)

    return jsonify({"mensagem": "Cadastro realizado com sucesso!"})

@app.route("/login", methods=["POST"])
def login():
    corpo = request.get_json()
    nickname = corpo.get("nickname", "").strip()
    senha = corpo.get("senha", "").strip()

    if not nickname or not senha:
        return jsonify({"erro": "Preencha todos os campos"}), 400

    dados = ler_dados()
    usuario_encontrado = None

    for usuario in dados["usuarios"]:
        if usuario["nickname"].lower() == nickname.lower():
            usuario_encontrado = usuario
            break

    if not usuario_encontrado:
        return jsonify({"erro": "Usuário ou senha incorreto"}), 401

    if not verificar_senha(senha, usuario_encontrado["senha"]):
        return jsonify({"erro": "Usuário ou senha incorreto"}), 401

    session["usuario"] = {
        "id": usuario_encontrado["id"],
        "nickname": usuario_encontrado["nickname"],
        "perfil": usuario_encontrado["perfil"]
    }

    return jsonify({
        "mensagem": "Login realizado!",
        "usuario": session["usuario"]
    })

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("usuario", None)
    return jsonify({"mensagem": "Logout realizado com sucesso!"})

@app.route("/curtir/<int:receita_id>", methods=["POST"])
def curtir(receita_id: int):
    usuario = session.get("usuario")
    if not usuario:
        return jsonify({"erro": "Você precisa estar logado para curtir"}), 401

    dados = ler_dados()

    for receita in dados["receitas"]:
        if receita["id"] == receita_id:
            nickname = usuario["nickname"]
            if nickname in receita["curtidas"]:
                receita["curtidas"].remove(nickname)
            else:
                receita["curtidas"].append(nickname)

            salvar_dados(dados)

            return jsonify({
                "total_curtidas": len(receita["curtidas"]),
                "curtiu": nickname in receita["curtidas"]
            })

    return jsonify({"erro": "Receita não encontrada"}), 404

@app.route("/comentar/<int:receita_id>", methods=["POST"])
def comentar(receita_id: int):
    usuario = session.get("usuario")
    if not usuario:
        return jsonify({"erro": "Você precisa estar logado para comentar"}), 401

    corpo = request.get_json()
    texto = corpo.get("texto", "").strip()

    if not texto:
        return jsonify({"erro": "Comentário vazio"}), 400

    dados = ler_dados()

    for receita in dados["receitas"]:
        if receita["id"] == receita_id:
            novo_comentario = {
                "id": dados["proximo_comentario_id"],
                "autor_id": usuario["id"],
                "autor_nickname": usuario["nickname"],
                "texto": texto
            }

            receita["comentarios"].append(novo_comentario)
            dados["proximo_comentario_id"] += 1

            salvar_dados(dados)

            return jsonify({"comentario": novo_comentario})

    return jsonify({"erro": "Receita não encontrada"}), 404

@app.route("/comentario/<int:comentario_id>", methods=["DELETE"])
def excluir_comentario(comentario_id: int):
    usuario = session.get("usuario")
    if not usuario:
        return jsonify({"erro": "Você precisa estar logado"}), 401

    dados = ler_dados()

    for receita in dados["receitas"]:
        for comentario in receita["comentarios"]:
            if comentario["id"] == comentario_id:

                if not usuario_pode_editar(usuario["id"], comentario["autor_id"]):
                    return jsonify({"erro": "Sem permissão"}), 403

                receita["comentarios"].remove(comentario)
                salvar_dados(dados)

                return jsonify({"mensagem": "Comentário excluído"})

    return jsonify({"erro": "Comentário não encontrado"}), 404

@app.route("/status")
def status():
    return jsonify({"usuario_logado": session.get("usuario")})

if __name__ == "__main__":
    if not os.path.exists(ARQUIVO_DADOS):
        print("Arquivo usuarios.json não encontrado!")
    else:
        app.run(debug=True)