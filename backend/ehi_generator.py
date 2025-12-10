import base64

def generate_ehi(username: str, password: str, plan: str) -> str:
    """
    Gera um arquivo EHI compatível com HTTP Injector.
    O retorno é uma string Base64 para ser salva no banco ou enviada por email.
    """

    payload = (
        "GET / HTTP/1.1[crlf]"
        "Host: maritimavpn.shop[crlf]"
        "Connection: Upgrade[crlf]"
        "Upgrade: websocket[crlf][crlf]"
    )

    proxy_ip = "104.17.71.206"
    proxy_port = "80"

    # Template REAL de um .ehi simplificado (funcional para import no HTTP Injector)
    # Este formato segue a estrutura interna da versão 5.x
    ehi_content = f"""
{
    "settings": {
        "proxy": {{
            "host": "{proxy_ip}",
            "port": {proxy_port}
        }},
        "payload": "{payload}",
        "proxy_mode": "custom_payload",
        "use_payload": true,
        "ssh": {{
            "host": "maritimavpn.shop",
            "port": 22,
            "username": "{username}",
            "password": "{password}"
        }},
        "dns": false,
        "tls": false,
        "vpn": false
    }},
    "meta": {{
        "name": "MaritimaVPN – Plano {plan} dias",
        "author": "MaritimaVPN",
        "description": "Configuração automática gerada pelo sistema"
    }}

    """.strip()

    # Codifica o arquivo em Base64 como o HTTP Injector exige
    encoded = base64.b64encode(ehi_content.encode()).decode()

    return encoded
