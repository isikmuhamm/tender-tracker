document.addEventListener("DOMContentLoaded", () => {
    const API_BASE = "";

    // DOM Elements
    const loginContainer = document.getElementById("login-container");
    const setupContainer = document.getElementById("setup-container");
    const appContainer = document.getElementById("app-container");
    
    const loginForm = document.getElementById("login-form");
    const loginError = document.getElementById("login-error");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");

    const setupForm = document.getElementById("setup-form");
    const setupError = document.getElementById("setup-error");
    const setupUsernameInput = document.getElementById("setup-username");
    const setupPasswordInput = document.getElementById("setup-password");
    const setupPasswordConfirmInput = document.getElementById("setup-password-confirm");
    
    const sidebarItems = document.querySelectorAll(".nav-item");
    const panelSections = document.querySelectorAll(".panel-section");
    const btnLogout = document.getElementById("btn-logout");
    const headerTitle = document.getElementById("header-title");
    
    // Tenders elements
    const tendersGrid = document.getElementById("tenders-grid");
    const tenderCount = document.getElementById("tender-count");
    const filterSector = document.getElementById("filter-sector");
    const filterCustom = document.getElementById("filter-custom");
    const filterSource = document.getElementById("filter-source");
    const searchInput = document.getElementById("search-input");
    
    // Actions elements
    const btnTrigger = document.getElementById("btn-trigger");
    const syncIcon = document.getElementById("sync-icon");
    const toast = document.getElementById("toast");

    // Config Panel elements
    const configForm = document.getElementById("config-form");
    const configAlert = document.getElementById("config-alert");
    const tabButtons = document.querySelectorAll(".config-tab-btn");
    const tabContents = document.querySelectorAll(".config-tab-content");
    
    // Config Form Inputs
    const cfgServerPort = document.getElementById("cfg-server-port");
    const cfgCheckInterval = document.getElementById("cfg-check-interval");
    const cfgLlmProvider = document.getElementById("cfg-llm-provider");
    
    // Gemini Settings
    const cfgGeminiKey = document.getElementById("cfg-gemini-key");
    const cfgGeminiModel = document.getElementById("cfg-gemini-model");
    
    // OpenAI Settings
    const cfgOpenaiKey = document.getElementById("cfg-openai-key");
    const cfgOpenaiModel = document.getElementById("cfg-openai-model");
    const cfgOpenaiUrl = document.getElementById("cfg-openai-url");
    
    // Claude Settings
    const cfgClaudeKey = document.getElementById("cfg-claude-key");
    const cfgClaudeModel = document.getElementById("cfg-claude-model");
    
    // SMTP & Telegram
    const cfgSmtpServer = document.getElementById("cfg-smtp-server");
    const cfgSmtpPort = document.getElementById("cfg-smtp-port");
    const cfgSmtpUser = document.getElementById("cfg-smtp-user");
    const cfgSmtpPass = document.getElementById("cfg-smtp-pass");
    const cfgMailSender = document.getElementById("cfg-mail-sender");
    const cfgMailRecipients = document.getElementById("cfg-mail-recipients");
    const cfgTelegramToken = document.getElementById("cfg-telegram-token");
    const cfgTelegramChat = document.getElementById("cfg-telegram-chat");
    
    // Filters & Sectors
    const cfgExcludeKeywords = document.getElementById("cfg-exclude-keywords");
    const customFiltersList = document.getElementById("custom-filters-list");
    const btnAddFilter = document.getElementById("btn-add-filter");
    const sectorsAccordionContainer = document.getElementById("sectors-accordion-container");
    const btnAddSector = document.getElementById("btn-add-sector");
    
    // Security Tab
    const secOldPass = document.getElementById("sec-old-pass");
    const secNewPass = document.getElementById("sec-new-pass");
    const secConfirmPass = document.getElementById("sec-confirm-pass");
    const btnChangePassword = document.getElementById("btn-change-password");

    // Logs elements
    const logsViewer = document.getElementById("logs-viewer");
    const btnRefreshLogs = document.getElementById("btn-refresh-logs");
    
    // Local state variables
    let activePanel = "panel-tenders";
    let loadedConfig = null;
    let localCustomFilters = [];
    let localSectors = {};

    // =========================================================
    // STARTUP SETUP CHECK & AUTH FLOW
    // =========================================================
    async function checkSetupAndAuth() {
        try {
            const response = await fetch(`${API_BASE}/api/auth/setup-status`);
            if (response.ok) {
                const data = await response.json();
                if (data.setup_required) {
                    loginContainer.classList.add("d-none");
                    setupContainer.classList.remove("d-none");
                    appContainer.classList.add("d-none");
                } else {
                    setupContainer.classList.add("d-none");
                    checkAuth();
                }
            } else {
                checkAuth();
            }
        } catch (err) {
            showToast("Bağlantı kurulamadı!");
            checkAuth();
        }
    }

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
            setupContainer.classList.add("d-none");
            appContainer.classList.remove("d-none");
            initApp();
        } else {
            loginContainer.classList.remove("d-none");
            setupContainer.classList.add("d-none");
            appContainer.classList.add("d-none");
        }
    }

    // Setup Form Submit
    setupForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        setupError.classList.add("d-none");
        
        const username = setupUsernameInput.value.trim();
        const password = setupPasswordInput.value;
        const confirm = setupPasswordConfirmInput.value;
        
        if (password !== confirm) {
            setupError.textContent = "Şifreler uyuşmuyor!";
            setupError.classList.remove("d-none");
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/api/auth/setup`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password })
            });
            
            if (response.ok) {
                showToast("Yönetici hesabı oluşturuldu. Giriş yapabilirsiniz.");
                setupContainer.classList.add("d-none");
                loginContainer.classList.remove("d-none");
            } else {
                const data = await response.json();
                setupError.textContent = data.detail || "Kurulum başarısız!";
                setupError.classList.remove("d-none");
            }
        } catch (err) {
            showToast("Bağlantı hatası!");
        }
    });

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
                headers: { "Content-Type": "application/x-www-form-urlencoded" },
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
            showToast("Bağlantı hatası!");
        }
    });

    // Logout
    btnLogout.addEventListener("click", () => {
        removeToken();
        checkAuth();
    });

    function handleAuthError() {
        removeToken();
        checkAuth();
        showToast("Oturum süresi dolmuş. Giriş yapın.");
    }

    // API Helper
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
            showToast("Bağlantı hatası!");
            return null;
        }
    }

    function showToast(message) {
        toast.textContent = message;
        toast.classList.remove("d-none");
        setTimeout(() => { toast.classList.add("d-none"); }, 3000);
    }

    // =========================================================
    // SIDEBAR & TABS NAVIGATION
    // =========================================================
    sidebarItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            sidebarItems.forEach(i => i.classList.remove("active"));
            item.classList.add("active");
            
            const target = item.getAttribute("data-target");
            activePanel = target;
            
            panelSections.forEach(p => p.classList.add("d-none"));
            document.getElementById(target).classList.remove("d-none");
            
            headerTitle.textContent = item.textContent.trim();
            
            if (target === "panel-tenders") {
                loadTenders();
            } else if (target === "panel-config") {
                loadConfigFromServer();
            } else if (target === "panel-logs") {
                loadLogs();
            }
        });
    });

    // Configuration Tabs
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            const tabId = btn.getAttribute("data-tab");
            tabContents.forEach(content => {
                if (content.id === tabId) {
                    content.classList.remove("d-none");
                } else {
                    content.classList.add("d-none");
                }
            });
        });
    });

    // Toggle active provider config block
    cfgLlmProvider.addEventListener("change", () => {
        document.querySelectorAll(".provider-block").forEach(b => b.classList.add("d-none"));
        const provider = cfgLlmProvider.value;
        if (provider !== "none") {
            const block = document.getElementById(`provider-block-${provider}`);
            if (block) block.classList.remove("d-none");
        }
    });

    // =========================================================
    // PANEL: TENDERS
    // =========================================================
    async function loadTenders() {
        const sector = filterSector.value;
        const source = filterSource.value;
        const search = searchInput.value.trim();
        const customFilterVal = filterCustom.value;
        
        let url = `/api/tenders?limit=100`;
        if (sector) url += `&sector=${encodeURIComponent(sector)}`;
        if (source) url += `&source=${encodeURIComponent(source)}`;
        
        const response = await apiRequest(url);
        if (!response || !response.ok) return;
        
        const data = await response.json();
        let items = data.items;
        
        // Client-side Custom LLM Filter
        if (customFilterVal) {
            items = items.filter(t => 
                t.matched_custom_filters && 
                t.matched_custom_filters.split(",").includes(customFilterVal)
            );
        }
        
        // Client-side text search
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
                <div class="glass-card" style="padding: 40px; text-align: center; color: var(--text-secondary); grid-column: 1 / -1;">
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
            
            // Build custom badges if any
            let customBadgesHtml = "";
            if (t.matched_custom_filters) {
                const filterIds = t.matched_custom_filters.split(",");
                filterIds.forEach(fid => {
                    const filterName = getCustomFilterName(fid);
                    customBadgesHtml += `<span class="custom-badge"><i class="fa-solid fa-bolt"></i> ${filterName}</span>`;
                });
            }

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
                    <div class="custom-badges-container">${customBadgesHtml}</div>
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

    function getCustomFilterName(id) {
        if (!loadedConfig || !loadedConfig.config || !loadedConfig.config.filters) return id;
        const filters = loadedConfig.config.filters.custom_llm_filters || [];
        const match = filters.find(f => f.id === id);
        return match ? match.name : id;
    }

    filterSector.addEventListener("change", loadTenders);
    filterCustom.addEventListener("change", loadTenders);
    filterSource.addEventListener("change", loadTenders);
    searchInput.addEventListener("input", debounce(loadTenders, 300));

    // =========================================================
    // PANEL: CONFIGURATION
    // =========================================================
    async function loadConfigFromServer() {
        const response = await apiRequest("/api/config");
        if (!response || !response.ok) return;
        
        loadedConfig = await response.json();
        const config = loadedConfig.config || {};
        const settings = config.settings || {};
        const notifications = config.notifications || {};
        const email = notifications.email || {};
        const telegram = notifications.telegram || {};
        const filters = config.filters || {};
        const sectors = loadedConfig.sectors || {};
        
        localCustomFilters = filters.custom_llm_filters || [];
        localSectors = sectors;

        // Populate port & interval
        cfgServerPort.value = settings.server_port || 8000;
        cfgCheckInterval.value = settings.check_interval_minutes || 60;
        
        // Populate scrapers checkboxes
        const enabledScrapers = settings.enabled_scrapers || [];
        document.getElementById("cfg-scraper-yatirimlar").checked = enabledScrapers.includes("yatirimlar");
        document.getElementById("cfg-scraper-dmo").checked = enabledScrapers.includes("dmo");
        document.getElementById("cfg-scraper-ilan").checked = enabledScrapers.includes("ilan_gov_tr");
        document.getElementById("cfg-scraper-ekapv2").checked = enabledScrapers.includes("ekapv2");
        
        // Active LLM
        cfgLlmProvider.value = settings.active_llm_provider || "none";
        cfgLlmProvider.dispatchEvent(new Event("change"));
        
        // Providers keys
        const providers = settings.llm_providers || {};
        cfgGeminiKey.value = providers.gemini?.api_key || "";
        cfgGeminiModel.value = providers.gemini?.model || "gemini-1.5-flash";
        
        cfgOpenaiKey.value = providers.openai?.api_key || "";
        cfgOpenaiModel.value = providers.openai?.model || "gpt-4o-mini";
        cfgOpenaiUrl.value = providers.openai?.base_url || "https://api.openai.com/v1";
        
        cfgClaudeKey.value = providers.claude?.api_key || "";
        cfgClaudeModel.value = providers.claude?.model || "claude-3-5-sonnet-20241022";
        
        // SMTP & Telegram
        cfgSmtpServer.value = email.smtp_server || "";
        cfgSmtpPort.value = email.smtp_port || 587;
        cfgSmtpUser.value = email.username || "";
        cfgSmtpPass.value = email.password || "";
        cfgMailSender.value = email.sender || "";
        cfgMailRecipients.value = Array.isArray(email.recipients) ? email.recipients.join(", ") : (email.recipients || "");
        
        cfgTelegramToken.value = telegram.bot_token || "";
        cfgTelegramChat.value = telegram.chat_id || "";
        
        // Excluded
        cfgExcludeKeywords.value = Array.isArray(filters.exclude_keywords) ? filters.exclude_keywords.join(", ") : (filters.exclude_keywords || "");
        
        // Render dynamic parts
        renderCustomFiltersTable();
        renderSectorsAccordion();
        
        // Populate main filter dropdowns
        populateMainFilters();
    }

    function populateMainFilters() {
        // Broad sectors dropdown
        const currentSectorSel = filterSector.value;
        filterSector.innerHTML = '<option value="">Tümü</option>';
        Object.keys(localSectors).forEach(secName => {
            const opt = document.createElement("option");
            opt.value = secName;
            opt.textContent = secName;
            if (secName === currentSectorSel) opt.selected = true;
            filterSector.appendChild(opt);
        });

        // Smart custom filters dropdown
        const currentCustomSel = filterCustom.value;
        filterCustom.innerHTML = '<option value="">Tümü</option>';
        localCustomFilters.forEach(f => {
            if (f.enabled) {
                const opt = document.createElement("option");
                opt.value = f.id;
                opt.textContent = f.name;
                if (f.id === currentCustomSel) opt.selected = true;
                filterCustom.appendChild(opt);
            }
        });
    }

    // --- Custom Filters Sub-Module ---
    function renderCustomFiltersTable() {
        customFiltersList.innerHTML = "";
        if (localCustomFilters.length === 0) {
            customFiltersList.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-secondary);">Tanımlı süzgeç yok. Süzgeç ekle butonuyla ekleyin.</td></tr>';
            return;
        }

        localCustomFilters.forEach((f, idx) => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><input type="text" class="filter-row-name" data-index="${idx}" value="${f.name || ""}" required></td>
                <td><input type="text" class="filter-row-prompt" data-index="${idx}" value="${f.prompt_instruction || ""}" required></td>
                <td style="text-align: center;">
                    <label class="switch">
                        <input type="checkbox" class="filter-row-toggle" data-index="${idx}" ${f.enabled ? "checked" : ""}>
                        <span class="slider"></span>
                    </label>
                </td>
                <td style="text-align: center;">
                    <button type="button" class="btn-icon-red btn-delete-filter" data-index="${idx}"><i class="fa-solid fa-trash"></i></button>
                </td>
            `;
            customFiltersList.appendChild(tr);
        });

        // Add events for inputs inside dynamic list
        document.querySelectorAll(".filter-row-name").forEach(el => {
            el.addEventListener("input", (e) => {
                const idx = parseInt(e.target.getAttribute("data-index"));
                localCustomFilters[idx].name = e.target.value;
                // Generate a safe dynamic ID if new
                if (!localCustomFilters[idx].id) {
                    localCustomFilters[idx].id = "filter_" + Math.random().toString(36).substr(2, 6);
                }
            });
        });

        document.querySelectorAll(".filter-row-prompt").forEach(el => {
            el.addEventListener("input", (e) => {
                const idx = parseInt(e.target.getAttribute("data-index"));
                localCustomFilters[idx].prompt_instruction = e.target.value;
            });
        });

        document.querySelectorAll(".filter-row-toggle").forEach(el => {
            el.addEventListener("change", (e) => {
                const idx = parseInt(e.target.getAttribute("data-index"));
                localCustomFilters[idx].enabled = e.target.checked;
            });
        });

        document.querySelectorAll(".btn-delete-filter").forEach(el => {
            el.addEventListener("click", (e) => {
                const targetBtn = e.target.closest(".btn-delete-filter");
                const idx = parseInt(targetBtn.getAttribute("data-index"));
                localCustomFilters.splice(idx, 1);
                renderCustomFiltersTable();
            });
        });
    }

    btnAddFilter.addEventListener("click", () => {
        localCustomFilters.push({
            id: "filter_" + Math.random().toString(36).substr(2, 6),
            name: "Yeni Süzgeç",
            prompt_instruction: "",
            enabled: true
        });
        renderCustomFiltersTable();
    });

    // --- Sectors Accordion Sub-Module ---
    function renderSectorsAccordion() {
        sectorsAccordionContainer.innerHTML = "";
        const sectorNames = Object.keys(localSectors);
        
        if (sectorNames.length === 0) {
            sectorsAccordionContainer.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-secondary);">Tanımlı sektör yok. Sektör ekle butonuyla ekleyin.</div>';
            return;
        }

        sectorNames.forEach((name) => {
            const rules = localSectors[name] || {};
            const keywords = rules.keywords || [];
            const negativeKeywords = rules.negative_keywords || [];
            
            const card = document.createElement("div");
            card.className = "sector-acc-card";
            
            card.innerHTML = `
                <div class="sector-acc-header">
                    <div class="sector-acc-title">
                        <i class="fa-solid fa-chevron-right acc-arrow"></i>
                        <span>${name}</span>
                    </div>
                    <button type="button" class="btn-icon-red btn-delete-sector" data-name="${name}"><i class="fa-solid fa-trash"></i></button>
                </div>
                <div class="sector-acc-body d-none">
                    <div class="form-group" style="margin-top: 15px;">
                        <label>Pozitif Anahtar Kelimeler (Virgülle ayırın)</label>
                        <input type="text" class="sector-keywords-input" data-name="${name}" value="${keywords.join(", ")}">
                    </div>
                    <div class="form-group">
                        <label>Negatif Anahtar Kelimeler (Geri kalanları eler, virgülle ayırın)</label>
                        <input type="text" class="sector-negatives-input" data-name="${name}" value="${negativeKeywords.join(", ")}">
                    </div>
                </div>
            `;
            sectorsAccordionContainer.appendChild(card);
        });

        // Accordion Toggle
        document.querySelectorAll(".sector-acc-header").forEach(header => {
            header.addEventListener("click", (e) => {
                // If trash button is clicked, do not toggle accordion
                if (e.target.closest(".btn-delete-sector")) return;
                
                const body = header.nextElementSibling;
                const arrow = header.querySelector(".acc-arrow");
                
                if (body.classList.contains("d-none")) {
                    body.classList.remove("d-none");
                    arrow.className = "fa-solid fa-chevron-down acc-arrow";
                } else {
                    body.classList.add("d-none");
                    arrow.className = "fa-solid fa-chevron-right acc-arrow";
                }
            });
        });

        // Delete Sector
        document.querySelectorAll(".btn-delete-sector").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const targetBtn = btn.closest(".btn-delete-sector");
                const name = targetBtn.getAttribute("data-name");
                if (confirm(`"${name}" sektörünü silmek istediğinize emin misiniz?`)) {
                    delete localSectors[name];
                    renderSectorsAccordion();
                }
            });
        });

        // Keywords change events
        document.querySelectorAll(".sector-keywords-input").forEach(el => {
            el.addEventListener("change", (e) => {
                const name = e.target.getAttribute("data-name");
                localSectors[name].keywords = e.target.value.split(",").map(k => k.trim()).filter(k => k);
            });
        });

        document.querySelectorAll(".sector-negatives-input").forEach(el => {
            el.addEventListener("change", (e) => {
                const name = e.target.getAttribute("data-name");
                localSectors[name].negative_keywords = e.target.value.split(",").map(k => k.trim()).filter(k => k);
            });
        });
    }

    btnAddSector.addEventListener("click", () => {
        const name = prompt("Eklenecek Sektör Adı:");
        if (name && name.trim()) {
            const trimmed = name.trim();
            if (localSectors[trimmed]) {
                alert("Bu isimde bir sektör zaten tanımlı!");
                return;
            }
            localSectors[trimmed] = { keywords: [], negative_keywords: [] };
            renderSectorsAccordion();
        }
    });

    // Change Password submit
    btnChangePassword.addEventListener("click", async () => {
        const old_password = secOldPass.value;
        const new_password = secNewPass.value;
        const confirm = secConfirmPass.value;
        
        if (!old_password || !new_password) {
            showToast("Tüm şifre alanlarını doldurun!");
            return;
        }
        if (new_password !== confirm) {
            showToast("Yeni şifreler uyuşmuyor!");
            return;
        }
        
        const response = await apiRequest("/api/auth/change-password", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ old_password, new_password })
        });
        
        if (response && response.ok) {
            showToast("Şifreniz başarıyla değiştirildi.");
            secOldPass.value = "";
            secNewPass.value = "";
            secConfirmPass.value = "";
        } else if (response) {
            const data = await response.json();
            showToast(data.detail || "Şifre değiştirilemedi!");
        }
    });

    // Save Configuration Submit Form
    configForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        configAlert.classList.add("d-none");

        // Format email recipients back to list
        const recipientsList = cfgMailRecipients.value.split(",").map(r => r.trim()).filter(r => r);
        const excludeList = cfgExcludeKeywords.value.split(",").map(x => x.trim()).filter(x => x);

        // Gather scrapers list
        const scrapers = [];
        if (document.getElementById("cfg-scraper-yatirimlar").checked) scrapers.push("yatirimlar");
        if (document.getElementById("cfg-scraper-dmo").checked) scrapers.push("dmo");
        if (document.getElementById("cfg-scraper-ilan").checked) scrapers.push("ilan_gov_tr");
        if (document.getElementById("cfg-scraper-ekapv2").checked) scrapers.push("ekapv2");

        const payload = {
            config: {
                settings: {
                    enabled_scrapers: scrapers,
                    check_interval_minutes: parseInt(cfgCheckInterval.value) || 60,
                    server_port: parseInt(cfgServerPort.value) || 8000,
                    active_llm_provider: cfgLlmProvider.value,
                    llm_providers: {
                        gemini: {
                            api_key: cfgGeminiKey.value.trim(),
                            model: cfgGeminiModel.value.trim() || "gemini-1.5-flash"
                        },
                        openai: {
                            api_key: cfgOpenaiKey.value.trim(),
                            model: cfgOpenaiModel.value.trim() || "gpt-4o-mini",
                            base_url: cfgOpenaiUrl.value.trim() || "https://api.openai.com/v1"
                        },
                        claude: {
                            api_key: cfgClaudeKey.value.trim(),
                            model: cfgClaudeModel.value.trim() || "claude-3-5-sonnet-20241022"
                        }
                    }
                },
                notifications: {
                    email: {
                        smtp_server: cfgSmtpServer.value.trim(),
                        smtp_port: parseInt(cfgSmtpPort.value) || 587,
                        username: cfgSmtpUser.value.trim(),
                        password: cfgSmtpPass.value,
                        sender: cfgMailSender.value.trim(),
                        recipients: recipientsList
                    },
                    telegram: {
                        bot_token: cfgTelegramToken.value.trim(),
                        chat_id: cfgTelegramChat.value.trim()
                    }
                },
                filters: {
                    exclude_keywords: excludeList,
                    custom_llm_filters: localCustomFilters
                }
            },
            sectors: localSectors
        };

        const response = await apiRequest("/api/config", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (response && response.ok) {
            configAlert.textContent = "Ayarlar başarıyla kaydedildi. Değişikliklerin sunucuda aktifleşmesi için sunucu yeniden başlatılmalı veya tarama beklenmeli.";
            configAlert.className = "alert-msg success";
            configAlert.classList.remove("d-none");
            showToast("Ayarlar sunucuya kaydedildi.");
            
            // Reload local settings to ensure clean state
            loadConfigFromServer();
        } else if (response) {
            const errData = await response.json();
            configAlert.textContent = errData.detail || "Yapılandırma kaydedilemedi!";
            configAlert.className = "alert-msg error";
            configAlert.classList.remove("d-none");
        }
    });

    // =========================================================
    // PANEL: LOGS
    // =========================================================
    async function loadLogs() {
        logsViewer.textContent = "Loglar yükleniyor...";
        const response = await apiRequest("/api/logs");
        if (!response || !response.ok) return;
        
        const data = await response.json();
        logsViewer.textContent = data.logs;
        logsViewer.scrollTop = logsViewer.scrollHeight;
    }

    btnRefreshLogs.addEventListener("click", loadLogs);

    // =========================================================
    // TRIGGER BOT ACTION
    // =========================================================
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
        loadTenders();
        loadConfigFromServer();
    }

    function debounce(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    }

    // Startup check
    checkSetupAndAuth();
});
