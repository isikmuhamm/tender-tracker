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

    // Modal elements
    const sectorModal = document.getElementById("sector-modal");
    const sectorModalForm = document.getElementById("sector-modal-form");
    const sectorModalTitle = document.getElementById("sector-modal-title");
    const modalSectorOrigName = document.getElementById("modal-sector-orig-name");
    const modalSectorName = document.getElementById("modal-sector-name");
    const modalSectorKeywords = document.getElementById("modal-sector-keywords");
    const modalSectorNegatives = document.getElementById("modal-sector-negatives");

    const filterModal = document.getElementById("filter-modal");
    const filterModalForm = document.getElementById("filter-modal-form");
    const filterModalTitle = document.getElementById("filter-modal-title");
    const modalFilterOrigId = document.getElementById("modal-filter-orig-id");
    const modalFilterId = document.getElementById("modal-filter-id");
    const modalFilterName = document.getElementById("modal-filter-name");
    const modalFilterPrompt = document.getElementById("modal-filter-prompt");
    
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
    // SIDEBAR & TABS NAVIGATION (Hash Routing)
    // =========================================================
    function handleRouting() {
        const hash = window.location.hash || "#/tenders";
        
        let targetPanelId = "panel-tenders";
        let targetNavItem = document.querySelector('.nav-item[data-target="panel-tenders"]');
        let activeConfigTab = "tab-general";
        
        if (hash.startsWith("#/config")) {
            targetPanelId = "panel-config";
            targetNavItem = document.querySelector('.nav-item[data-target="panel-config"]');
            
            const parts = hash.split("/");
            if (parts.length > 2) {
                const sub = parts[2];
                if (sub === "filters") activeConfigTab = "tab-filters";
                else if (sub === "notifications") activeConfigTab = "tab-notifications";
                else if (sub === "sectors") activeConfigTab = "tab-sectors";
                else if (sub === "security") activeConfigTab = "tab-security";
            }
        } else if (hash === "#/logs") {
            targetPanelId = "panel-logs";
            targetNavItem = document.querySelector('.nav-item[data-target="panel-logs"]');
        }
        
        // Update active class on nav items
        sidebarItems.forEach(i => i.classList.remove("active"));
        if (targetNavItem) targetNavItem.classList.add("active");
        
        // Switch visible panels
        panelSections.forEach(p => p.classList.add("d-none"));
        const targetPanel = document.getElementById(targetPanelId);
        if (targetPanel) targetPanel.classList.remove("d-none");
        
        // Update header title
        if (targetNavItem) {
            headerTitle.textContent = targetNavItem.textContent.trim();
        }
        
        // Handle config sub-tabs active styling and visibility
        if (targetPanelId === "panel-config") {
            tabButtons.forEach(btn => {
                const tabId = btn.getAttribute("data-tab");
                if (tabId === activeConfigTab) {
                    btn.classList.add("active");
                } else {
                    btn.classList.remove("active");
                }
            });
            tabContents.forEach(content => {
                if (content.id === activeConfigTab) {
                    content.classList.remove("d-none");
                } else {
                    content.classList.add("d-none");
                }
            });
        }
        
        // Trigger panel load actions
        activePanel = targetPanelId;
        if (targetPanelId === "panel-tenders") {
            loadTenders();
        } else if (targetPanelId === "panel-config") {
            loadConfigFromServer();
        } else if (targetPanelId === "panel-logs") {
            loadLogs();
        }
    }
    
    window.addEventListener("hashchange", handleRouting);

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
    // --- Central Sources configuration ---
    const ALL_SOURCES = {
        "yatirimlar": "Yatırımlar Dergisi",
        "dmo": "DMO",
        "ilan_gov_tr": "ilan.gov.tr",
        "ekapv2": "EKAPv2"
    };

    function populateSourcesFilter() {
        const currentSel = filterSource.value;
        filterSource.innerHTML = '<option value="">Tümü</option>';
        Object.entries(ALL_SOURCES).forEach(([val, name]) => {
            const opt = document.createElement("option");
            opt.value = val;
            opt.textContent = name;
            if (val === currentSel) opt.selected = true;
            filterSource.appendChild(opt);
        });
    }

    // --- Modal overlays helpers ---
    function openModal(modalEl) {
        modalEl.classList.remove("d-none");
        modalEl.offsetHeight; // force layout reflow
        modalEl.classList.add("active");
    }

    function closeModal(modalEl) {
        modalEl.classList.remove("active");
        setTimeout(() => {
            modalEl.classList.add("d-none");
        }, 300);
    }

    document.querySelectorAll(".modal-close-btn, .modal-cancel-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const openModalEl = e.target.closest(".modal-overlay");
            if (openModalEl) closeModal(openModalEl);
        });
    });

    // --- Dynamic LLM Model Loader ---
    async function loadLlmModels(provider, selectElement, currentModel, apiKey = "") {
        selectElement.innerHTML = "";
        
        let url = `${API_BASE}/api/models?provider=${provider}`;
        if (apiKey) {
            url += `&api_key=${encodeURIComponent(apiKey)}`;
        }
        
        const defaults = {
            "gemini": ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
            "openai": ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"],
            "claude": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]
        };
        
        let models = [];
        try {
            const response = await apiRequest(url);
            if (response && response.ok) {
                const data = await response.json();
                models = data.models || [];
            }
        } catch (err) {
            console.error("Modeller yüklenirken hata:", err);
        }
        
        if (models.length === 0) {
            models = defaults[provider] || [];
        }
        
        if (currentModel && !models.includes(currentModel)) {
            models.unshift(currentModel);
        }
        
        models.forEach(m => {
            const opt = document.createElement("option");
            opt.value = m;
            opt.textContent = m;
            selectElement.appendChild(opt);
        });
        
        if (currentModel) {
            selectElement.value = currentModel;
        } else if (models.length > 0) {
            selectElement.value = models[0];
        }
    }

    // Register refresh models listeners
    document.getElementById("btn-fetch-gemini-models").addEventListener("click", async () => {
        const btn = document.getElementById("btn-fetch-gemini-models");
        btn.disabled = true;
        const icon = btn.querySelector("i");
        icon.classList.add("spin");
        await loadLlmModels("gemini", cfgGeminiModel, cfgGeminiModel.value, cfgGeminiKey.value.trim());
        icon.classList.remove("spin");
        btn.disabled = false;
        showToast("Gemini model listesi güncellendi.");
    });
    
    document.getElementById("btn-fetch-openai-models").addEventListener("click", async () => {
        const btn = document.getElementById("btn-fetch-openai-models");
        btn.disabled = true;
        const icon = btn.querySelector("i");
        icon.classList.add("spin");
        await loadLlmModels("openai", cfgOpenaiModel, cfgOpenaiModel.value, cfgOpenaiKey.value.trim());
        icon.classList.remove("spin");
        btn.disabled = false;
        showToast("OpenAI model listesi güncellendi.");
    });
    
    document.getElementById("btn-fetch-claude-models").addEventListener("click", async () => {
        const btn = document.getElementById("btn-fetch-claude-models");
        btn.disabled = true;
        const icon = btn.querySelector("i");
        icon.classList.add("spin");
        await loadLlmModels("claude", cfgClaudeModel, cfgClaudeModel.value, cfgClaudeKey.value.trim());
        icon.classList.remove("spin");
        btn.disabled = false;
        showToast("Claude model listesi güncellendi.");
    });

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
        
        // Providers keys & models
        const providers = settings.llm_providers || {};
        cfgGeminiKey.value = providers.gemini?.api_key || "";
        await loadLlmModels("gemini", cfgGeminiModel, providers.gemini?.model || "gemini-1.5-flash", providers.gemini?.api_key);
        
        cfgOpenaiKey.value = providers.openai?.api_key || "";
        cfgOpenaiUrl.value = providers.openai?.base_url || "https://api.openai.com/v1";
        await loadLlmModels("openai", cfgOpenaiModel, providers.openai?.model || "gpt-4o-mini", providers.openai?.api_key);
        
        cfgClaudeKey.value = providers.claude?.api_key || "";
        await loadLlmModels("claude", cfgClaudeModel, providers.claude?.model || "claude-3-5-sonnet-20241022", providers.claude?.api_key);
        
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
            const secInfo = localSectors[secName] || {};
            if (secInfo.enabled !== false) {
                const opt = document.createElement("option");
                opt.value = secName;
                opt.textContent = secName;
                if (secName === currentSectorSel) opt.selected = true;
                filterSector.appendChild(opt);
            }
        });

        // Smart custom filters dropdown
        const currentCustomSel = filterCustom.value;
        filterCustom.innerHTML = '<option value="">Tümü</option>';
        localCustomFilters.forEach(f => {
            if (f.enabled !== false) {
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
                <td><strong>${f.name || ""}</strong><br><small style="color: var(--text-secondary)">ID: ${f.id}</small></td>
                <td>${f.prompt_instruction || ""}</td>
                <td style="text-align: center;">
                    <label class="switch">
                        <input type="checkbox" class="filter-row-toggle" data-index="${idx}" ${f.enabled !== false ? "checked" : ""}>
                        <span class="slider"></span>
                    </label>
                </td>
                <td style="text-align: center;">
                    <button type="button" class="btn-small btn-edit-filter" data-index="${idx}" style="margin-right: 5px;"><i class="fa-solid fa-edit"></i></button>
                    <button type="button" class="btn-icon-red btn-delete-filter" data-index="${idx}"><i class="fa-solid fa-trash"></i></button>
                </td>
            `;
            customFiltersList.appendChild(tr);
        });

        document.querySelectorAll(".filter-row-toggle").forEach(el => {
            el.addEventListener("change", (e) => {
                const idx = parseInt(el.getAttribute("data-index"));
                localCustomFilters[idx].enabled = el.checked;
            });
        });

        document.querySelectorAll(".btn-edit-filter").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const targetBtn = btn.closest(".btn-edit-filter");
                const idx = parseInt(targetBtn.getAttribute("data-index"));
                const f = localCustomFilters[idx];
                
                modalFilterOrigId.value = f.id;
                modalFilterId.value = f.id;
                modalFilterName.value = f.name;
                modalFilterPrompt.value = f.prompt_instruction || "";
                
                filterModalTitle.textContent = "Akıllı Süzgeç Düzenle";
                openModal(filterModal);
            });
        });

        document.querySelectorAll(".btn-delete-filter").forEach(el => {
            el.addEventListener("click", (e) => {
                const targetBtn = el.closest(".btn-delete-filter");
                const idx = parseInt(targetBtn.getAttribute("data-index"));
                localCustomFilters.splice(idx, 1);
                renderCustomFiltersTable();
            });
        });
    }

    btnAddFilter.addEventListener("click", () => {
        modalFilterOrigId.value = "";
        modalFilterId.value = "filter_" + Math.random().toString(36).substr(2, 6);
        modalFilterName.value = "";
        modalFilterPrompt.value = "";
        filterModalTitle.textContent = "Yeni Akıllı Süzgeç Ekle";
        openModal(filterModal);
    });

    filterModalForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const origId = modalFilterOrigId.value;
        const newId = modalFilterId.value.trim();
        const newName = modalFilterName.value.trim();
        const newPrompt = modalFilterPrompt.value.trim();
        
        if (!newId || !newName) return;
        
        if (newId !== origId && localCustomFilters.some(f => f.id === newId)) {
            alert("Bu ID değerine sahip başka bir süzgeç zaten tanımlı!");
            return;
        }
        
        if (origId) {
            const idx = localCustomFilters.findIndex(f => f.id === origId);
            if (idx !== -1) {
                localCustomFilters[idx].id = newId;
                localCustomFilters[idx].name = newName;
                localCustomFilters[idx].prompt_instruction = newPrompt;
            }
        } else {
            localCustomFilters.push({
                id: newId,
                name: newName,
                prompt_instruction: newPrompt,
                enabled: true
            });
        }
        
        closeModal(filterModal);
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
                    <div class="sector-acc-actions">
                        <label class="switch" title="Sektörü Etkinleştir / Devre Dışı Bırak">
                            <input type="checkbox" class="sector-row-toggle" data-name="${name}" ${rules.enabled !== false ? "checked" : ""}>
                            <span class="slider"></span>
                        </label>
                        <button type="button" class="btn-small-primary btn-edit-sector" data-name="${name}"><i class="fa-solid fa-edit"></i> Düzenle</button>
                        <button type="button" class="btn-icon-red btn-delete-sector" data-name="${name}"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
                <div class="sector-acc-body d-none">
                    <p style="margin-top: 15px; font-size: 13px;"><strong>Anahtar Kelimeler:</strong> ${keywords.length > 0 ? keywords.join(", ") : "<em>Tanımlanmamış</em>"}</p>
                    <p style="font-size: 13px;"><strong>Yasaklı Kelimeler:</strong> ${negativeKeywords.length > 0 ? negativeKeywords.join(", ") : "<em>Tanımlanmamış</em>"}</p>
                </div>
            `;
            sectorsAccordionContainer.appendChild(card);
        });

        // Accordion Toggle
        document.querySelectorAll(".sector-acc-header").forEach(header => {
            header.addEventListener("click", (e) => {
                if (e.target.closest(".sector-acc-actions")) return;
                
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

        // Sector row toggles
        document.querySelectorAll(".sector-row-toggle").forEach(el => {
            el.addEventListener("change", (e) => {
                const name = el.getAttribute("data-name");
                if (localSectors[name]) {
                    localSectors[name].enabled = el.checked;
                }
            });
        });

        // Edit Sector Modal trigger
        document.querySelectorAll(".btn-edit-sector").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const name = btn.getAttribute("data-name");
                const rules = localSectors[name] || {};
                const keywords = rules.keywords || [];
                const negativeKeywords = rules.negative_keywords || [];
                
                modalSectorOrigName.value = name;
                modalSectorName.value = name;
                modalSectorKeywords.value = keywords.join("\n");
                modalSectorNegatives.value = negativeKeywords.join("\n");
                
                sectorModalTitle.textContent = "Sektör Düzenle";
                openModal(sectorModal);
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
                    populateMainFilters();
                }
            });
        });
    }

    btnAddSector.addEventListener("click", () => {
        modalSectorOrigName.value = "";
        modalSectorName.value = "";
        modalSectorKeywords.value = "";
        modalSectorNegatives.value = "";
        sectorModalTitle.textContent = "Yeni Sektör Ekle";
        openModal(sectorModal);
    });

    sectorModalForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const origName = modalSectorOrigName.value;
        const newName = modalSectorName.value.trim();
        
        if (!newName) return;
        
        if (newName !== origName && localSectors[newName]) {
            alert("Bu isimde bir sektör zaten tanımlı!");
            return;
        }
        
        const keywords = modalSectorKeywords.value.split("\n").map(k => k.trim()).filter(k => k);
        const negatives = modalSectorNegatives.value.split("\n").map(k => k.trim()).filter(k => k);
        
        const enabled = origName ? (localSectors[origName].enabled !== false) : true;
        
        if (origName && newName !== origName) {
            delete localSectors[origName];
        }
        
        localSectors[newName] = {
            enabled: enabled,
            keywords: keywords,
            negative_keywords: negatives
        };
        
        closeModal(sectorModal);
        renderSectorsAccordion();
        populateMainFilters();
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
        populateSourcesFilter();
        handleRouting();
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
