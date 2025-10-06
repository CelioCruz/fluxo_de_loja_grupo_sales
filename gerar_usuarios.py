import bcrypt
import json
import os

def hash_senha(senha):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(senha.encode('utf-8'), salt).decode('utf-8')

def main():
    print("--- Adicionar Novo Usuário ---")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    caminho_arquivo = os.path.join(script_dir, "usuarios.json")
    
    print(f"📁 Arquivo será salvo em: {caminho_arquivo}\n")

    login = input("Digite o login do novo usuário: ").strip()
    if not login:
        print("❌ Login não pode ser vazio.")
        return

    senha_digitada = input("Digite a senha para o usuário: ").strip()
    if not senha_digitada:
        print("❌ Senha não pode ser vazia.")
        return

    novo_usuario = {
        "login": login,
        "senha_hash": hash_senha(senha_digitada)
    }

    # Carregar dados existentes
    if os.path.exists(caminho_arquivo):
        try:
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                dados = json.load(f)
            
            # Garantir que 'usuarios' seja uma lista
            if not isinstance(dados, dict) or "usuarios" not in dados:
                print("⚠️  Estrutura inválida no JSON. Reiniciando lista de usuários.")
                dados = {"usuarios": []}
            else:
                # Validar cada usuário: deve ter 'login'
                usuarios_validos = []
                for u in dados["usuarios"]:
                    if isinstance(u, dict) and "login" in u:
                        usuarios_validos.append(u)
                    else:
                        print(f"⚠️  Usuário inválido ignorado: {u}")
                dados["usuarios"] = usuarios_validos

        except (json.JSONDecodeError, ValueError) as e:
            print(f"❌ Arquivo JSON corrompido: {e}")
            print("➡️  Criando novo arquivo.")
            dados = {"usuarios": []}
    else:
        print("📝 Arquivo não encontrado. Criando novo.")
        dados = {"usuarios": []}

    # Verificar duplicidade com segurança
    logins_existentes = [u["login"] for u in dados["usuarios"] if isinstance(u, dict) and "login" in u]
    if login in logins_existentes:
        print(f"❌ O login '{login}' já existe.")
        return

    # Adicionar e salvar
    dados["usuarios"].append(novo_usuario)
    try:
        with open(caminho_arquivo, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=4, ensure_ascii=False)
        print(f"\n✅ Usuário '{login}' adicionado com sucesso!")
        print("🔒 Senha salva com hash seguro (bcrypt).")
    except Exception as e:
        print(f"\n❌ Erro ao salvar: {e}")

if __name__ == "__main__":
    main()