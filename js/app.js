// ============================
// CONFIG
// ============================
const API_URL = "/api";
const TOKEN_KEY = "maritima_token";

// ============================
// TOKEN / AUTH
// ============================
function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function clearToken() {
    localStorage.removeItem(TOKEN_KEY);
}

function isLogged() {
    return !!getToken();
}

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + getToken()
    };
}

// ============================
// ON LOAD
// ============================
document.addEventListener("DOMContentLoaded", () => {
    updateNavbar();

    const loginForm = document.getElementById("loginForm");
    const registerForm = document.getElementById("registerForm");

    if (loginForm) loginForm.addEventListener("submit", login);
    if (registerForm) registerForm.addEventListener("submit", register);
});

// ============================
// NAVBAR
// ============================
function updateNavbar() {
    const logged = isLogged();

    const loginBtn = document.getElementById("loginBtn");
    const logoutBtn = document.getElementById("logoutBtn");
    const myPlansBtn = document.getElementById("myPlansBtn");

    if (loginBtn) loginBtn.style.display = logged ? "none" : "inline-block";
    if (logoutBtn) logoutBtn.style.display = logged ? "inline-block" : "none";
    if (myPlansBtn) myPlansBtn.style.display = logged ? "inline-block" : "none";
}

// ============================
// LOGIN
// ============================
async function login(e) {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    const res = await fetch(API_URL + "/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Credenciais inválidas");
        return;
    }

    setToken(data.token);
    updateNavbar();

    bootstrap.Modal.getInstance(
        document.getElementById("loginModal")
    ).hide();

    alert("Login realizado com sucesso!");
}

// ============================
// REGISTER
// ============================
async function register(e) {
    e.preventDefault();

    const name = document.getElementById("regName").value;
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;

    const res = await fetch(API_URL + "/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Erro ao criar conta");
        return;
    }

    alert("Conta criada com sucesso!");

    bootstrap.Modal.getInstance(
        document.getElementById("registerModal")
    ).hide();
}

// ============================
// LOGOUT
// ============================
function logout() {
    clearToken();
    updateNavbar();
    alert("Você saiu da conta.");
}

// ============================
// COMPRAR PLANO (PIX)
// ============================
async function buyPlan(days) {
    if (!isLogged()) {
        alert("Faça login para comprar um plano.");
        return;
    }

    const res = await fetch(API_URL + "/create-pix", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ plan_days: days })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Erro ao gerar PIX");
        return;
    }

    // Exibe QR Code PIX
    document.getElementById("pixQr").src =
        "data:image/png;base64," + data.qr_code_base64;

    document.getElementById("pixCode").value = data.qr_code;

    new bootstrap.Modal(
        document.getElementById("pixModal")
    ).show();
}

// ============================
// COPIAR PIX
// ============================
function copyPix() {
    const input = document.getElementById("pixCode");
    input.select();
    document.execCommand("copy");
    alert("Código PIX copiado!");
}

// ============================
// MEUS PLANOS
// ============================
async function openPlans() {
    if (!isLogged()) return;

    const res = await fetch(API_URL + "/get-plans", {
        headers: authHeaders()
    });

    if (!res.ok) {
        alert("Erro ao carregar planos");
        return;
    }

    const plans = await res.json();

    let html = "";

    if (!plans.length) {
        html = "<p>Nenhum plano ativo ainda.</p>";
    }

    plans.forEach(p => {
        html += `
        <div class="p-3 mb-3" style="background:#14263f;border-radius:10px;">
            <h5>Plano ${p.plan} dias</h5>
            <p>Usuário: <b>${p.username}</b></p>
            <p>Expira: <b>${p.expires}</b></p>

            <a class="btn btn-success btn-sm"
               href="/api/download-ehi/${p.id}"
               target="_blank">
               Download EHI
            </a>
        </div>
        `;
    });

    document.getElementById("plansList").innerHTML = html;

    new bootstrap.Modal(
        document.getElementById("plansModal")
    ).show();
}

// ============================
// MODAL SWITCH
// ============================
function showRegister() {
    bootstrap.Modal.getInstance(
        document.getElementById("loginModal")
    ).hide();

    new bootstrap.Modal(
        document.getElementById("registerModal")
    ).show();
}

async function openPix(days) {
    if (!isLogged()) {
        alert("Faça login para comprar um plano.");
        return;
    }

    const res = await fetch("/api/create-pix", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ plan_days: days })
    });

    const data = await res.json();

    if (!res.ok) {
        alert(data.detail || "Erro ao gerar PIX");
        return;
    }

    document.getElementById("pixQrImg").src =
        "data:image/png;base64," + data.qr_code_base64;
    document.getElementById("pixQrImg").style.display = "block";

    document.getElementById("pixCode").value = data.qr_code;
    document.getElementById("pixCode").style.display = "block";

    document.getElementById("copyPixBtn").style.display = "inline-block";

    new bootstrap.Modal(
        document.getElementById("pixModal")
    ).show();
}

// ============================
// TRIAL (TESTE GRÁTIS)
// ============================
async function createTrial() {

    // 🔒 Verifica se está logado
    if (!isLogged()) {
        alert("Você precisa estar logado para usar o teste grátis.");
        return;
    }

    try {
        const res = await fetch(API_URL + "/trial", {
            method: "POST",
            headers: authHeaders()
        });

        const data = await res.json();

        if (!res.ok) {
            alert(data.detail || "Erro ao ativar teste grátis.");
            return;
        }

        alert(
            "🎉 Teste grátis ativado!\n\n" +
            "Usuário: " + data.username + "\n" +
            "Senha: " + data.password + "\n" +
            "Expira em: " + data.expires
        );

        // Atualiza lista de planos
        updateNavbar();
        openPlans();

    } catch (err) {
        alert("Erro de conexão com o servidor.");
    }
}

