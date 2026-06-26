document.addEventListener("DOMContentLoaded", () => {
    const API_BASE = "";

    // DOM Elements
    const loginContainer = document.getElementById("login-container");
    const appContainer = document.getElementById("app-container");
    const loginForm = document.getElementById("login-form");
    const loginError = document.getElementById("login-error");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    
    const sidebarItems = document.querySelectorAll(".nav-item");
    const panelSections = document.querySelectorAll(".panel-section");
    const btnLogout = document.getElementById("btn-logout");
    const headerTitle = document.getElementById("header-title");
    
    // Tenders elements
    const tendersGrid = document.getElementById("tenders-grid");
    const tenderCount = document.getElementById("tender-count");
    const filterSector = document.getElementById("filter-sector");
    const filterSource = document.getElementById("filter-source");
    const searchInput = document.getElementById("search-input");
    
    // Config elements
    const editorConfig = document.getElementById("editor-config");
    const editorSectors = document.getElementById("editor-sectors");
    const btnSaveConfig = document.getElementById("btn-save-config");
    const configAlert = document.getElementById("config-alert");
    
    // Logs elements
    const logsViewer = document.getElementById("logs-viewer");
    const btnRefreshLogs = document.getElementById("btn-refresh-logs");
    
    // Actions elements
    const btnTrigger = document.getElementById("btn-trigger");
    const syncIcon = document.getElementById("sync-icon");
    const toast = document.getElementById("toast");

    let activePanel = "panel-tenders";

    // =========================================================
    // TOKEN MANAGEMENT & AUTH FLOW
    // =========================================================
    function getToken() {
        return localStorage.getItem("token");
    }

    function setToken(token) {
        localStorage.setItem("token", token);
    }

    function removeToken() {
        localStorage.removeItem("token");
    }

    function checkAuth() {
        const token = getToken();
        if (token) {
            loginContainer.classList.add("d-none");
            appContainer.classList.remove("d-none");
            initApp();
        } else {
            loginContainer.classList.remove("d-none");
            appContainer.classList.add("d-none");
        }
    }

    // Login Form Submit
    loginForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        loginError.classList.add("d-none");
        
        const username = usernameInput.value;
        const password = passwordInput.value;
        
        const formData = new URLSearchParams();
        formData.append("username", username);
        formData.append("password", password);
        
        try {
            const response = await fetch(`${API_BASE}/api/auth/login`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded"
                },
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                setToken(data.access_token);
                checkAuth();
            } else {
                loginError.classList.remove("d-none");
            }
        } catch (err) {
            showToast("Sunucuyla bağlantı kurulamadı!");
        }
    });

    // Logout Button
    btnLogout.addEventListener("click", () => {
        removeToken();
        checkAuth();
    });

    // Handle Unauthorized requests (Expired/invalid tokens)
    function handleAuthError() {
        removeToken();
        checkAuth();
        showToast("Oturum süresi dolmuş. Lütfen tekrar giriş yapın.");
    }

    // =========================================================
    // API CALLS (HELPER)
    // =========================================================
    async function apiRequest(endpoint, options = {}) {
        const token = getToken();
        if (!token) return null;
        
        options.headers = options.headers || {};
        options.headers["Authorization"] = `Bearer ${token}`;
        
        try {
            const response = await fetch(`${API_BASE}${endpoint}`, options);
            if (response.status === 401) {
                handleAuthError();
                return null;
            }
            return response;
        } catch (err) {
            logger.error("API hatası:", err);
            showToast("Bağlantı hatası oluştu!");
            return null;
        }
    }

    // =========================================================
    // TOAST NOTIFICATION
    // =========================================================
    function showToast(message) {
        toast.textContent = message;
        toast.classList.remove("d-none");
        setTimeout(() => {
            toast.classList.add("d-none");
        }, 3000);
    }

    // =========================================================
    // NAVIGATION & PANEL INITIALIZATION
    // =========================================================
    sidebarItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            
            // Sidebar Active Switch
            sidebarItems.forEach(i => i.classList.remove("active"));
            item.classList.add("active");
            
            // Panel Display Switch
            const target = item.getAttribute("data-target");
            activePanel = target;
            
            panelSections.forEach(p => p.classList.add("d-none"));
            document.getElementById(target).classList.remove("d-none");
            
            // Set Header Title
            headerTitle.textContent = item.textContent.trim();
            
            // Panel load hooks
            if (target === "panel-tenders") {
                loadTenders();
            } else if (target === "panel-config") {
                loadConfig();
            } else if (target === "panel-logs") {
                loadLogs();
            }
        });
    });

    // =========================================================
    // PANEL IMPLEMENTATIONS
    // =========================================================
    
    // --- PANEL: TENDERS ---
    async function loadTenders() {
        const sector = filterSector.value;
        const source = filterSource.value;
        const search = searchInput.value.trim();
        
        let url = `/api/tenders?limit=100`;
        if (sector) url += `&sector=${encodeURIComponent(sector)}`;
        if (source) url += `&source=${encodeURIComponent(source)}`;
        
        const response = await apiRequest(url);
        if (!response || !response.ok) return;
        
        const data = await response.json();
        
        // Front-end Search Filter (If search string provided)
        let items = data.items;
        if (search) {
            const q = search.toLowerCase();
            items = items.filter(t => 
                t.title.toLowerCase().includes(q) || 
                (t.summary && t.summary.toLowerCase().includes(q))
            );
        }
        
        tenderCount.textContent = items.length;
        renderTenders(items);
    }

    function renderTenders(items) {
        tendersGrid.innerHTML = "";
        
        if (items.length === 0) {
            tendersGrid.innerHTML = `
                <div class="glass-card" style="padding: 40px; text-align: center; color: var(--text-secondary);">
                    <i class="fa-solid fa-folder-open" style="font-size: 40px; margin-bottom: 15px; display: block; color: var(--primary-color);"></i>
                    Gösterilecek ihale bulunamadı.
                </div>
            `;
            return;
        }
        
        items.forEach(t => {
            const card = document.createElement("div");
            card.className = "tender-card glass-card";
            
            const formattedDate = t.first_seen ? new Date(t.first_seen).toLocaleDateString("tr-TR") : "-";
            
            card.innerHTML = `
                <div class="tender-card-header">
                    <h3>${t.title}</h3>
                    <div class="tender-badges">
                        <span class="badge badge-source">${t.source}</span>
                        ${t.sector ? `<span class="badge badge-sector">${t.sector}</span>` : ""}
                    </div>
                </div>
                <div class="tender-card-body">
                    <p>${t.summary || "Açıklama veya ek bilgi bulunmuyor."}</p>
                </div>
                <div class="tender-card-footer">
                    <div class="tender-meta">
                        <span><i class="fa-solid fa-calendar-days"></i> ${formattedDate}</span>
                        ${t.category ? `<span><i class="fa-solid fa-bookmark"></i> ${t.category}</span>` : ""}
                    </div>
                    <a href="${t.link}" target="_blank" class="btn-link">Detay <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>
            `;
            tendersGrid.appendChild(card);
        });
    }

    // Tenders event listeners
    filterSector.addEventListener("change", loadTenders);
    filterSource.addEventListener("change", loadTenders);
    searchInput.addEventListener("input", debounce(loadTenders, 300));

    // --- PANEL: CONFIGURATION ---
    async function loadConfig() {
        const response = await apiRequest("/api/config");
        if (!response || !response.ok) return;
        
        const data = await response.json();
        editorConfig.value = data.config_yaml;
        editorSectors.value = data.sectors_yaml;
        
        // Sektör dropdown'ını doldur
        populateSectorDropdown(data.sectors_yaml);
    }

    function populateSectorDropdown(sectorsYaml) {
        // Basitçe YAML parse etmeden satır bazlı sektör isimlerini bulalım
        const sectors = [""];
        const lines = sectorsYaml.split("\n");
        lines.forEach(line => {
            // "Demiryolu:" veya "Su Arıtma:" gibi anahtar kelimeleri yakalar
            const match = line.match(/^([a-zA-ZçğıöşüÇĞİÖŞÜ\s]+):/);
            if (match) {
                const name = match[1].trim();
                if (name && name !== "keywords" && name !== "negative_keywords") {
                    sectors.push(name);
                }
            }
        });
        
        const currentSelection = filterSector.value;
        filterSector.innerHTML = "";
        sectors.forEach(sec => {
            const opt = document.createElement("option");
            opt.value = sec;
            opt.textContent = sec === "" ? "Tümü" : sec;
            if (sec === currentSelection) opt.selected = true;
            filterSector.appendChild(opt);
        });
    }

    btnSaveConfig.addEventListener("click", async () => {
        configAlert.classList.add("d-none");
        
        const payload = {
            config_yaml: editorConfig.value,
            sectors_yaml: editorSectors.value
        };
        
        const response = await apiRequest("/api/config", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });
        
        if (response && response.ok) {
            configAlert.textContent = "Yapılandırma başarıyla kaydedildi.";
            configAlert.className = "alert-msg success";
            configAlert.classList.remove("d-none");
            populateSectorDropdown(editorSectors.value);
            showToast("Ayarlar kaydedildi.");
        } else if (response) {
            const errData = await response.json();
            configAlert.textContent = errData.detail || "Yapılandırma kaydedilemedi!";
            configAlert.className = "alert-msg error";
            configAlert.classList.remove("d-none");
        }
    });

    // --- PANEL: LOGS ---
    async function loadLogs() {
        logsViewer.textContent = "Loglar yükleniyor...";
        const response = await apiRequest("/api/logs");
        if (!response || !response.ok) return;
        
        const data = await response.json();
        logsViewer.textContent = data.logs;
        // En aşağıya kaydır
        logsViewer.scrollTop = logsViewer.scrollHeight;
    }

    btnRefreshLogs.addEventListener("click", loadLogs);

    // --- TRIGGER BOT ACTION ---
    btnTrigger.addEventListener("click", async () => {
        syncIcon.classList.add("spin");
        btnTrigger.disabled = true;
        
        const response = await apiRequest("/api/tenders/trigger", {
            method: "POST"
        });
        
        if (response && response.ok) {
            showToast("Tarama botu arka planda tetiklendi.");
            setTimeout(() => {
                syncIcon.classList.remove("spin");
                btnTrigger.disabled = false;
                if (activePanel === "panel-tenders") loadTenders();
                if (activePanel === "panel-logs") loadLogs();
            }, 3000);
        } else {
            syncIcon.classList.remove("spin");
            btnTrigger.disabled = false;
        }
    });

    // =========================================================
    // INITIALIZATION & UTIL
    // =========================================================
    function initApp() {
        // İlk açılışta ihaleleri yükle ve arka planda config'i çekerek filtre dropdown'ını besle
        loadTenders();
        loadConfig();
    }

    // Debounce helper for search filter input
    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // Uygulama girişi
    checkAuth();
});
