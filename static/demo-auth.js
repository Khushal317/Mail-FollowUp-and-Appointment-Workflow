(function () {
    const LOGIN_KEY = "demo_login";
    const SESSION_KEY = "demo_session_id";
    const TWO_DAYS = 2 * 24 * 60 * 60 * 1000;

    function readLogin() {
        try {
            const login = JSON.parse(localStorage.getItem(LOGIN_KEY) || "null");
            if (!login || !login.id || !login.created_at) {
                return null;
            }
            if (Date.now() - Number(login.created_at) > TWO_DAYS) {
                clearLogin(login);
                return null;
            }
            localStorage.setItem(SESSION_KEY, login.id);
            return login;
        } catch (error) {
            clearLogin();
            return null;
        }
    }

    function saveLogin(name, email) {
        const login = {
            id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
            name: String(name || "").trim(),
            email: String(email || "").trim().toLowerCase(),
            created_at: Date.now()
        };
        localStorage.setItem(LOGIN_KEY, JSON.stringify(login));
        localStorage.setItem(SESSION_KEY, login.id);
        return login;
    }

    function clearLogin() {
        const login = arguments[0] || readLogin();
        if (login && login.id) {
            const body = JSON.stringify({ demo_session_id: login.id });
            if (navigator.sendBeacon) {
                navigator.sendBeacon("/api/demo-session/clear", new Blob([body], { type: "application/json" }));
            } else {
                fetch("/api/demo-session/clear", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body,
                    keepalive: true
                }).catch(() => {});
            }
            localStorage.removeItem(`demo_lead_ids_${login.id}`);
        }
        localStorage.removeItem(LOGIN_KEY);
        localStorage.removeItem(SESSION_KEY);
    }

    window.demoAuth = {
        getLogin: readLogin,
        saveLogin,
        logout: clearLogin,
        requireLogin() {
            const login = readLogin();
            if (!login) {
                window.location.href = `/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`;
                return null;
            }
            return login;
        },
        sessionId() {
            const login = readLogin();
            return login ? login.id : "";
        }
    };
})();
