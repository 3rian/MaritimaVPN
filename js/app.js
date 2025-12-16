// ============================
// CONFIG
// ============================
const API_URL = "/api";
const TOKEN_KEY = "maritima_token";

// ============================
// UTIL
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

function authHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + getToken()
    };
}

function isLogged() {
    return !!getToken();
}

// ============================
// ON LOAD
// ============================
document.addEventListener("DOMContentLoaded", () => {
    updateNavbar();

    document.getElementById("loginForm").addEventListener("submit", login);
    document.getElementById("registerForm").addEventListener("submit", register);
});

// ============================
// NAVBAR
// ============================
function updateNavbar() {
    const logged = isLogged();

    document.getElementById("loginBtn").style.display = logged ? "none" : "inline-block";
    document.getElementById("logoutBtn").style.display = logged ? "inline-block" : "none";
    document.getElementById("myPlansBtn").style.display = logged ? "inline-block" : "none";
}

// ============================
// LOGIN
// ============================
async function login(e) {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value;
    const password = document.getElementById("loginPassword").value;

    const req = await fetch(API_URL + "/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
    });

    const res = await req.json();

    if (res.token) {
        setToken(res.token);
        updateNavbar();

        bootstrap.Modal.getInstance(
            document.getElementById("loginModal")
        ).hide();

        alert("Login realizado com sucesso!");
    } else {
        alert(res.detail || "Credenciais inválidas");
    }
}

// ============================
// REGISTER
// ============================
async function register(e) {
    e.preventDefault();

    const name = document.getElementById("regName").value;
    const email = document.getElementById("regEmail").value;
    const password = document.getElementById("regPassword").value;

    const req = await fetch(API_URL + "/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password })
    });

    const res = await req.json();

    alert(res.message || "Conta criada!");

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
// BUY PLAN
// ============================
async function buyPlan(days) {
    if (!isLogged()) {
        alert("Você precisa estar logado para comprar.");
        return;
    }

    const req = await fetch(API_URL + "/create-plan", {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({ plan_days: days })
    });

    const res = await req.json();

    if (req.ok) {
        alert("Plano criado com sucesso!");
        openPlans();
    } else {
        alert(res.detail || "Erro ao criar plano");
    }
}

// ============================
// OPEN PLANS
// ============================
async function openPlans() {
    if (!isLogged()) return;

    const req = await fetch(API_URL + "/get-plans", {
        headers: authHeaders()
    });

    const plans = await req.json();

    let html = "";

    if (!plans.length) {
        html = "<p>Nenhum plano ativo.</p>";
    }

    plans.forEach(p => {
        html += `
        <div class="p-3 mb-3" style="background:#14263f;border-radius:10px;">
            <h5>${p.plan} dias</h5>
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
// SWITCH LOGIN → REGISTER
// ============================
function showRegister() {
    bootstrap.Modal.getInstance(
        document.getElementById("loginModal")
    ).hide();

    new bootstrap.Modal(
        document.getElementById("registerModal")
    ).show();
}

function createTrial() {
    const user = JSON.parse(localStorage.getItem("user"));

    if (!user) {
        alert("Faça login para usar o teste grátis.");
        return;
    }

    fetch("/trial", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user_id: user.user_id
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert(data.error);
            return;
        }

        alert(
            "Teste grátis ativado!\n\n" +
            "Usuário: " + data.username + "\n" +
            "Senha: " + data.password + "\n" +
            "Expira em: " + data.expires
        );
    })
    .catch(() => {
        alert("Erro ao criar teste grátis.");
    });
}
