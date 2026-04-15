/**
 * Sentinel Core - Main Application JavaScript
 * AI Contract Intelligence Platform
 */

// ==========================================
// IMMEDIATE SETUP
// ==========================================

// Force dismiss preloader after 3 seconds
setTimeout(function() {
    var preloader = document.getElementById('preloader');
    if (preloader && preloader.style.display !== 'none') {
        preloader.style.opacity = '0';
        setTimeout(function() {
            preloader.style.display = 'none';
        }, 500);
    }
}, 3000);

// ==========================================
// CONFIGURATION
// ==========================================

const CONFIG = {
    API_BASE_URL: window.location.origin + '/api/v1',
    SUPABASE_URL: 'https://kifkkdawmitxivosuncs.supabase.co',
    SUPABASE_ANON_KEY: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtpZmtrZGF3bWl0eGl2b3N1bmNzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzYyNjE0NDgsImV4cCI6MjA5MTgzNzQ0OH0.9ajeZpiUmf4-UEq7E90AQW3M-Tk0kzvH8dzZJIAu-5U'
};

// ==========================================
// STATE
// ==========================================

const state = {
    user: null,
    isAuthenticated: false,
    currentView: 'dashboard',
    currentDocumentId: null,
    analysisResult: null,
    history: []
};

// ==========================================
// SUPABASE
// ==========================================

let supabase = null;

function initSupabase() {
    try {
        if (window.supabase) {
            supabase = window.supabase.createClient(CONFIG.SUPABASE_URL, CONFIG.SUPABASE_ANON_KEY);
            console.log('Supabase initialized');
        }
    } catch (e) {
        console.warn('Supabase init failed:', e);
    }
}

// ==========================================
// INITIALIZATION
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded - initializing app');
    
    initSupabase();
    initPreloader();
    initButtons();
    loadHistory();
    
    console.log('App initialized successfully');
});

function initPreloader() {
    var preloader = document.getElementById('preloader');
    var progressBar = document.querySelector('.preloader-progress');
    
    if (progressBar) {
        progressBar.style.transition = 'width 2s ease';
        progressBar.style.width = '100%';
    }
    
    setTimeout(function() {
        if (preloader) {
            preloader.style.transition = 'opacity 0.5s ease';
            preloader.style.opacity = '0';
            setTimeout(function() {
                preloader.style.display = 'none';
            }, 500);
        }
    }, 2000);
}

// ==========================================
// BUTTON HANDLERS
// ==========================================

function initButtons() {
    // Sign In button
    var navLogin = document.getElementById('nav-login');
    if (navLogin) {
        navLogin.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Sign In clicked');
            showAuthModal('login');
        };
        console.log('nav-login bound');
    } else {
        console.warn('nav-login not found');
    }
    
    // Get Started button (nav)
    var navSignup = document.getElementById('nav-signup');
    if (navSignup) {
        navSignup.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Get Started clicked');
            showAuthModal('signup');
        };
        console.log('nav-signup bound');
    } else {
        console.warn('nav-signup not found');
    }
    
    // Hero CTA button
    var heroCta = document.getElementById('hero-cta');
    if (heroCta) {
        heroCta.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Hero CTA clicked');
            showAuthModal('signup');
        };
        console.log('hero-cta bound');
    } else {
        console.warn('hero-cta not found');
    }
    
    // Hero Demo button
    var heroDemo = document.getElementById('hero-demo');
    if (heroDemo) {
        heroDemo.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Watch Demo clicked');
            showToast('Demo video coming soon!', 'info');
        };
        console.log('hero-demo bound');
    }
    
    // Section CTA button
    var ctaButton = document.getElementById('cta-button');
    if (ctaButton) {
        ctaButton.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('CTA Button clicked');
            showAuthModal('signup');
        };
        console.log('cta-button bound');
    }
    
    // Auth modal close
    var authClose = document.getElementById('auth-close');
    if (authClose) {
        authClose.onclick = function() {
            hideAuthModal();
        };
    }
    
    // Auth toggle
    var authToggle = document.getElementById('auth-toggle');
    if (authToggle) {
        authToggle.onclick = function() {
            toggleAuthMode();
        };
    }
    
    // Auth form submit
    var authForm = document.getElementById('auth-form');
    if (authForm) {
        authForm.onsubmit = function(e) {
            e.preventDefault();
            handleAuth();
        };
    }
    
    // Google auth
    var googleAuth = document.getElementById('google-auth');
    if (googleAuth) {
        googleAuth.onclick = function() {
            handleGoogleAuth();
        };
    }
    
    // Modal background click to close
    var authModal = document.getElementById('auth-modal');
    if (authModal) {
        authModal.onclick = function(e) {
            if (e.target === authModal) {
                hideAuthModal();
            }
        };
    }
    
    // Logout
    var logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.onclick = function() {
            handleLogout();
        };
    }
    
    // Upload area
    var uploadArea = document.getElementById('upload-area');
    var fileInput = document.getElementById('file-input');
    if (uploadArea && fileInput) {
        uploadArea.onclick = function() {
            fileInput.click();
        };
        fileInput.onchange = function() {
            if (fileInput.files.length > 0) {
                processFile(fileInput.files[0]);
            }
        };
    }
    
    // New analysis button
    var newAnalysisBtn = document.getElementById('new-analysis-btn');
    if (newAnalysisBtn) {
        newAnalysisBtn.onclick = function() {
            resetToUpload();
        };
    }
    
    // Export button
    var exportBtn = document.getElementById('export-btn');
    if (exportBtn) {
        exportBtn.onclick = function() {
            exportReport();
        };
    }
    
    // Clear history
    var clearHistoryBtn = document.getElementById('clear-history-btn');
    if (clearHistoryBtn) {
        clearHistoryBtn.onclick = function() {
            clearHistory();
        };
    }
    
    // App nav links
    document.querySelectorAll('.app-nav-link').forEach(function(link) {
        link.onclick = function() {
            switchView(link.dataset.view);
        };
    });
    
    // User avatar dropdown
    var userAvatar = document.getElementById('user-avatar');
    if (userAvatar) {
        userAvatar.onclick = function() {
            var dropdown = document.getElementById('user-dropdown');
            if (dropdown) {
                dropdown.classList.toggle('hidden');
            }
        };
    }
    
    // Dropdown settings button
    var dropdownSettings = document.getElementById('dropdown-settings');
    if (dropdownSettings) {
        dropdownSettings.onclick = function() {
            var dropdown = document.getElementById('user-dropdown');
            if (dropdown) dropdown.classList.add('hidden');
            switchView('settings');
        };
    }
    
    // Tab buttons
    document.querySelectorAll('.tab').forEach(function(tab) {
        tab.onclick = function() {
            switchTab(tab.dataset.tab);
        };
    });
    
    // Modal close button
    var modalClose = document.getElementById('modal-close');
    if (modalClose) {
        modalClose.onclick = function() {
            closeClauseModal();
        };
    }
    
    // Clause modal background click
    var clauseModal = document.getElementById('clause-modal');
    if (clauseModal) {
        clauseModal.onclick = function(e) {
            if (e.target === clauseModal) {
                closeClauseModal();
            }
        };
    }
}

// ==========================================
// AUTH MODAL
// ==========================================

var authMode = 'login';

function showAuthModal(mode) {
    console.log('showAuthModal called:', mode);
    authMode = mode;
    
    var modal = document.getElementById('auth-modal');
    if (!modal) {
        console.error('Auth modal not found!');
        alert('Error: Could not find auth modal');
        return;
    }
    
    updateAuthUI();
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
    modal.style.opacity = '1';
    modal.style.visibility = 'visible';
    
    console.log('Auth modal should be visible now');
}

function hideAuthModal() {
    var modal = document.getElementById('auth-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
        
        var form = document.getElementById('auth-form');
        if (form) form.reset();
    }
}

function toggleAuthMode() {
    authMode = authMode === 'login' ? 'signup' : 'login';
    updateAuthUI();
}

function updateAuthUI() {
    var title = document.getElementById('auth-title');
    var subtitle = document.getElementById('auth-subtitle');
    var submitBtn = document.getElementById('auth-submit');
    var toggleText = document.getElementById('auth-toggle-text');
    var toggle = document.getElementById('auth-toggle');
    
    if (authMode === 'login') {
        if (title) title.textContent = 'Welcome Back';
        if (subtitle) subtitle.textContent = 'Sign in to your account';
        if (submitBtn) submitBtn.querySelector('span').textContent = 'Sign In';
        if (toggleText) toggleText.textContent = "Don't have an account?";
        if (toggle) toggle.textContent = 'Sign Up';
    } else {
        if (title) title.textContent = 'Create Account';
        if (subtitle) subtitle.textContent = 'Start your free trial today';
        if (submitBtn) submitBtn.querySelector('span').textContent = 'Sign Up';
        if (toggleText) toggleText.textContent = 'Already have an account?';
        if (toggle) toggle.textContent = 'Sign In';
    }
}

async function handleAuth() {
    var email = document.getElementById('auth-email').value;
    var password = document.getElementById('auth-password').value;
    
    if (!email || !password) {
        showToast('Please enter email and password', 'error');
        return;
    }
    
    // Demo mode - bypass auth if Supabase not available
    if (!supabase) {
        handleAuthSuccess({ email: email, id: 'demo-user' });
        return;
    }
    
    try {
        var result;
        if (authMode === 'login') {
            result = await supabase.auth.signInWithPassword({ email, password });
        } else {
            result = await supabase.auth.signUp({ email, password });
        }
        
        if (result.error) throw result.error;
        
        if (result.data.user) {
            handleAuthSuccess(result.data.user);
        }
    } catch (error) {
        showToast(error.message || 'Authentication failed', 'error');
    }
}

async function handleGoogleAuth() {
    if (!supabase) {
        showToast('Google auth requires Supabase', 'warning');
        return;
    }
    
    try {
        await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: { redirectTo: window.location.origin }
        });
    } catch (error) {
        showToast('Google auth failed', 'error');
    }
}

function handleAuthSuccess(user) {
    state.user = user;
    state.isAuthenticated = true;
    
    hideAuthModal();
    showApp();
    updateUserUI();
    showToast('Welcome to Sentinel Core!', 'success');
}

function handleLogout() {
    if (supabase) {
        supabase.auth.signOut();
    }
    
    state.user = null;
    state.isAuthenticated = false;
    
    hideApp();
    showToast('Signed out successfully', 'success');
}

function updateUserUI() {
    if (!state.user) return;
    
    var avatar = document.getElementById('user-avatar');
    var name = document.getElementById('dropdown-user-name');
    var email = document.getElementById('dropdown-user-email');
    var settingsEmail = document.getElementById('settings-email');
    
    var initial = state.user.email ? state.user.email.charAt(0).toUpperCase() : 'U';
    var displayName = state.user.email ? state.user.email.split('@')[0] : 'User';
    
    if (avatar) avatar.querySelector('span').textContent = initial;
    if (name) name.textContent = displayName;
    if (email) email.textContent = state.user.email || '';
    if (settingsEmail) settingsEmail.textContent = state.user.email || '';
}

// ==========================================
// VIEW MANAGEMENT
// ==========================================

function showApp() {
    var landing = document.getElementById('landing-page');
    var app = document.getElementById('app-container');
    
    if (landing) landing.classList.add('hidden');
    if (app) app.classList.remove('hidden');
}

function hideApp() {
    var landing = document.getElementById('landing-page');
    var app = document.getElementById('app-container');
    
    if (landing) landing.classList.remove('hidden');
    if (app) app.classList.add('hidden');
    
    window.scrollTo(0, 0);
}

function switchView(view) {
    state.currentView = view;
    
    // Update nav
    document.querySelectorAll('.app-nav-link').forEach(function(link) {
        link.classList.toggle('active', link.dataset.view === view);
    });
    
    // Update views
    var dashboard = document.getElementById('dashboard-view');
    var history = document.getElementById('history-view');
    var settings = document.getElementById('settings-view');
    
    if (dashboard) dashboard.classList.toggle('hidden', view !== 'dashboard');
    if (history) history.classList.toggle('hidden', view !== 'history');
    if (settings) settings.classList.toggle('hidden', view !== 'settings');
    
    if (view === 'history') {
        renderHistory();
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab').forEach(function(tab) {
        tab.classList.toggle('active', tab.dataset.tab === tabId);
    });
    
    document.querySelectorAll('.tab-panel').forEach(function(panel) {
        panel.classList.toggle('active', panel.id === tabId + '-panel');
    });
}

// ==========================================
// FILE UPLOAD
// ==========================================

async function processFile(file) {
    if (file.type !== 'application/pdf') {
        showToast('Please upload a PDF file', 'error');
        return;
    }
    
    if (file.size > 50 * 1024 * 1024) {
        showToast('File size must be under 50MB', 'error');
        return;
    }
    
    var uploadArea = document.getElementById('upload-area');
    var uploadProgress = document.getElementById('upload-progress');
    
    if (uploadArea) uploadArea.classList.add('hidden');
    if (uploadProgress) uploadProgress.classList.remove('hidden');
    
    try {
        updateProgress(10, 'Uploading document...');
        
        var formData = new FormData();
        formData.append('file', file);
        
        var uploadResponse = await fetch(CONFIG.API_BASE_URL + '/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!uploadResponse.ok) {
            var error = await uploadResponse.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        var uploadResult = await uploadResponse.json();
        state.currentDocumentId = uploadResult.document_id;
        
        updateProgress(30, 'Starting analysis...');
        showLoading('Analyzing contract with AI...');
        
        var analysisResponse = await fetch(
            CONFIG.API_BASE_URL + '/analyze/' + state.currentDocumentId,
            { method: 'POST' }
        );
        
        if (!analysisResponse.ok) {
            var error = await analysisResponse.json();
            throw new Error(error.detail || 'Analysis failed');
        }
        
        var analysisResult = await analysisResponse.json();
        state.analysisResult = analysisResult;
        
        hideLoading();
        displayResults(analysisResult, file.name);
        saveToHistory(file.name, analysisResult);
        showToast('Analysis complete!', 'success');
        
    } catch (error) {
        console.error('Error:', error);
        hideLoading();
        showToast(error.message || 'An error occurred', 'error');
        resetUploadUI();
    }
}

function updateProgress(percent, text) {
    var circle = document.getElementById('progress-circle');
    var percentEl = document.getElementById('progress-percent');
    var textEl = document.getElementById('progress-text');
    
    if (circle) {
        var circumference = 2 * Math.PI * 40;
        var offset = circumference - (percent / 100) * circumference;
        circle.style.strokeDashoffset = offset;
    }
    
    if (percentEl) percentEl.textContent = Math.round(percent) + '%';
    if (textEl) textEl.textContent = text;
}

function resetUploadUI() {
    var uploadArea = document.getElementById('upload-area');
    var uploadProgress = document.getElementById('upload-progress');
    var fileInput = document.getElementById('file-input');
    
    if (uploadArea) uploadArea.classList.remove('hidden');
    if (uploadProgress) uploadProgress.classList.add('hidden');
    if (fileInput) fileInput.value = '';
}

function resetToUpload() {
    var uploadSection = document.getElementById('upload-section');
    var resultsSection = document.getElementById('results-section');
    
    if (uploadSection) uploadSection.classList.remove('hidden');
    if (resultsSection) resultsSection.classList.add('hidden');
    
    resetUploadUI();
    state.currentDocumentId = null;
    state.analysisResult = null;
}

// ==========================================
// RESULTS DISPLAY
// ==========================================

function displayResults(result, filename) {
    var uploadSection = document.getElementById('upload-section');
    var resultsSection = document.getElementById('results-section');
    
    if (uploadSection) uploadSection.classList.add('hidden');
    if (resultsSection) resultsSection.classList.remove('hidden');
    
    // Header
    var filenameEl = document.getElementById('result-filename');
    var dateEl = document.getElementById('result-date');
    
    if (filenameEl) filenameEl.textContent = filename || 'Contract Analysis';
    if (dateEl) dateEl.textContent = new Date().toLocaleDateString('en-US', {
        year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    
    // Risk gauge
    animateRiskGauge(result.overall_risk_score || 0);
    
    // Risk summary
    var summaryEl = document.getElementById('risk-summary-text');
    if (summaryEl) summaryEl.textContent = result.risk_summary || 'Analysis complete.';
    
    // Risk breakdown
    var breakdown = (result.metadata && result.metadata.risk_breakdown) || {};
    var highEl = document.getElementById('high-risk-count');
    var medEl = document.getElementById('medium-risk-count');
    var lowEl = document.getElementById('low-risk-count');
    
    if (highEl) highEl.textContent = breakdown.high_risk_clauses || 0;
    if (medEl) medEl.textContent = breakdown.medium_risk_clauses || 0;
    if (lowEl) lowEl.textContent = breakdown.low_risk_clauses || 0;
    
    // Clauses
    renderClauses(result.clauses || []);
    renderNegotiation(result.negotiation_summary);
    renderImprovements(result.improvements || []);
}

function animateRiskGauge(score) {
    var progress = document.getElementById('gauge-progress');
    var value = document.getElementById('risk-value');
    
    if (progress) {
        var circumference = 2 * Math.PI * 80;
        var offset = circumference - (score / 100) * circumference;
        progress.style.strokeDashoffset = offset;
    }
    
    if (value) value.textContent = Math.round(score);
}

function renderClauses(clauses) {
    var grid = document.getElementById('clauses-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    clauses.forEach(function(clause) {
        var card = document.createElement('div');
        card.className = 'clause-card';
        card.dataset.type = clause.type || 'unknown';
        card.dataset.risk = clause.risk_level || 'medium';
        
        card.innerHTML = 
            '<div class="clause-header">' +
                '<span class="clause-type">' + formatClauseType(clause.type) + '</span>' +
                '<span class="clause-risk ' + (clause.risk_level || 'medium') + '">' + (clause.risk_level || 'Medium') + '</span>' +
            '</div>' +
            '<p class="clause-text">' + (clause.text || clause.clause_text || '') + '</p>' +
            '<div class="clause-footer">' +
                '<span class="clause-issue">' + (clause.issue ? '⚠ ' + truncate(clause.issue, 30) : '') + '</span>' +
                '<span class="clause-view">View Details →</span>' +
            '</div>';
        
        card.onclick = function() {
            showClauseModal(clause);
        };
        
        grid.appendChild(card);
    });
}

function renderNegotiation(summary) {
    var container = document.getElementById('negotiation-summary');
    if (!container) return;
    
    // Combine all priority levels
    var allItems = [];
    if (summary && summary.high_priority) {
        summary.high_priority.forEach(function(item) { item.priority = 'high'; allItems.push(item); });
    }
    if (summary && summary.medium_priority) {
        summary.medium_priority.forEach(function(item) { item.priority = 'medium'; allItems.push(item); });
    }
    if (summary && summary.low_priority) {
        summary.low_priority.forEach(function(item) { item.priority = 'low'; allItems.push(item); });
    }
    
    if (allItems.length === 0) {
        container.innerHTML = '<p class="empty-state">No negotiation strategies available.</p>';
        return;
    }
    
    var html = '';
    allItems.forEach(function(item) {
        var negotiation = item.negotiation || {};
        html += 
            '<div class="negotiation-card ' + (item.priority || 'medium') + '-priority">' +
                '<div class="negotiation-header">' +
                    '<span class="negotiation-title">' + formatClauseType(item.clause_type || 'Strategy') + '</span>' +
                    '<span class="negotiation-leverage ' + (negotiation.leverage || 'medium') + '">' + (negotiation.leverage || 'Medium') + ' Leverage</span>' +
                '</div>' +
                '<div class="negotiation-content">' +
                    '<p><strong>Issue:</strong> ' + (item.issue || 'Review recommended') + '</p>' +
                    '<p><strong>Objective:</strong> ' + (negotiation.objective || '') + '</p>' +
                    '<p><strong>Approach:</strong> ' + (negotiation.reason || '') + '</p>' +
                    (negotiation.suggested_change ? '<p><strong>Suggested Change:</strong> ' + negotiation.suggested_change + '</p>' : '') +
                '</div>' +
            '</div>';
    });
    
    container.innerHTML = html;
}

function renderImprovements(improvements) {
    var container = document.getElementById('improvements-list');
    if (!container) return;
    
    if (!improvements || improvements.length === 0) {
        container.innerHTML = '<p class="empty-state">No improvements suggested.</p>';
        return;
    }
    
    var html = '';
    improvements.forEach(function(item) {
        var title = 'Improvement';
        var description = '';
        
        if (typeof item === 'string') {
            // Parse string format: "[TYPE] Description"
            var match = item.match(/^\[([^\]]+)\]\s*(.*)$/);
            if (match) {
                title = formatClauseType(match[1].toLowerCase());
                description = match[2];
            } else {
                description = item;
            }
        } else {
            // Object format
            title = item.title || formatClauseType(item.clause_type) || 'Improvement';
            description = item.description || item.suggestion || '';
        }
        
        html += 
            '<div class="improvement-item">' +
                '<div class="improvement-icon">📈</div>' +
                '<div class="improvement-content">' +
                    '<h4>' + title + '</h4>' +
                    '<p>' + description + '</p>' +
                '</div>' +
            '</div>';
    });
    
    container.innerHTML = html;
}

// ==========================================
// CLAUSE MODAL
// ==========================================

function showClauseModal(clause) {
    var modal = document.getElementById('clause-modal');
    var badge = document.getElementById('modal-badge');
    var title = document.getElementById('modal-title');
    var body = document.getElementById('modal-body');
    
    if (!modal) return;
    
    if (badge) badge.textContent = formatClauseType(clause.type);
    if (title) title.textContent = formatClauseType(clause.type) + ' Clause';
    
    if (body) {
        body.innerHTML = 
            '<section><h4>Clause Text</h4><p>' + (clause.text || clause.clause_text || '') + '</p></section>' +
            '<section><h4>Risk Level</h4><p><span class="clause-risk ' + clause.risk_level + '">' + (clause.risk_level || 'Medium') + '</span></p></section>' +
            (clause.issue ? '<section><h4>Issue</h4><p>' + clause.issue + '</p></section>' : '') +
            (clause.suggestion ? '<section><h4>Recommendation</h4><p>' + clause.suggestion + '</p></section>' : '');
    }
    
    modal.classList.remove('hidden');
    modal.style.display = 'flex';
}

function closeClauseModal() {
    var modal = document.getElementById('clause-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
    }
}

// ==========================================
// HISTORY
// ==========================================

function loadHistory() {
    try {
        var saved = localStorage.getItem('sentinel_history');
        if (saved) {
            state.history = JSON.parse(saved);
        }
    } catch (e) {
        state.history = [];
    }
}

function saveToHistory(filename, result) {
    var item = {
        id: Date.now().toString(),
        filename: filename,
        date: new Date().toISOString(),
        riskScore: result.overall_risk_score || 0,
        clauseCount: (result.clauses && result.clauses.length) || 0,
        result: result
    };
    
    state.history.unshift(item);
    
    if (state.history.length > 50) {
        state.history = state.history.slice(0, 50);
    }
    
    localStorage.setItem('sentinel_history', JSON.stringify(state.history));
}

function renderHistory() {
    var list = document.getElementById('history-list');
    var empty = document.getElementById('history-empty');
    
    if (!list) return;
    
    // Clear existing items
    list.querySelectorAll('.history-item').forEach(function(item) {
        item.remove();
    });
    
    if (state.history.length === 0) {
        if (empty) empty.classList.remove('hidden');
        return;
    }
    
    if (empty) empty.classList.add('hidden');
    
    state.history.forEach(function(item) {
        var el = document.createElement('div');
        el.className = 'history-item';
        el.dataset.id = item.id;
        
        var date = new Date(item.date);
        var formattedDate = date.toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric'
        });
        
        el.innerHTML = 
            '<div class="history-icon">📄</div>' +
            '<div class="history-info">' +
                '<span class="history-name">' + item.filename + '</span>' +
                '<span class="history-meta">' + formattedDate + ' • ' + item.clauseCount + ' clauses</span>' +
            '</div>' +
            '<div class="history-score">' +
                '<span class="history-score-value">' + Math.round(item.riskScore) + '</span>' +
                '<span class="history-score-label">Risk</span>' +
            '</div>' +
            '<div class="history-actions">' +
                '<button class="history-action view" title="View">👁</button>' +
                '<button class="history-action delete" title="Delete">🗑</button>' +
            '</div>';
        
        el.querySelector('.view').onclick = function(e) {
            e.stopPropagation();
            loadHistoryItem(item);
        };
        
        el.querySelector('.delete').onclick = function(e) {
            e.stopPropagation();
            deleteHistoryItem(item.id);
        };
        
        el.onclick = function() {
            loadHistoryItem(item);
        };
        
        list.appendChild(el);
    });
}

function loadHistoryItem(item) {
    state.analysisResult = item.result;
    switchView('dashboard');
    displayResults(item.result, item.filename);
}

function deleteHistoryItem(id) {
    state.history = state.history.filter(function(item) {
        return item.id !== id;
    });
    localStorage.setItem('sentinel_history', JSON.stringify(state.history));
    renderHistory();
    showToast('Item deleted', 'success');
}

function clearHistory() {
    if (!confirm('Clear all history?')) return;
    
    state.history = [];
    localStorage.removeItem('sentinel_history');
    renderHistory();
    showToast('History cleared', 'success');
}

// ==========================================
// EXPORT
// ==========================================

function exportReport() {
    if (!state.analysisResult) {
        showToast('No analysis to export', 'error');
        return;
    }
    
    var result = state.analysisResult;
    
    var html = '<!DOCTYPE html><html><head><title>Contract Analysis Report</title>' +
        '<style>body{font-family:Arial,sans-serif;padding:40px;color:#333;}' +
        'h1{color:#1a365d;border-bottom:2px solid #3182ce;padding-bottom:10px;}' +
        'h2{color:#2c5282;margin-top:30px;}.risk-score{font-size:48px;font-weight:bold;color:#3182ce;}' +
        '.clause{background:#f7fafc;padding:15px;margin:10px 0;border-radius:8px;border-left:4px solid #3182ce;}' +
        '.high{border-left-color:#e53e3e;}.medium{border-left-color:#d69e2e;}.low{border-left-color:#38a169;}</style></head>' +
        '<body><h1>Contract Analysis Report</h1>' +
        '<p>Generated by Sentinel Core on ' + new Date().toLocaleString() + '</p>' +
        '<h2>Risk Assessment</h2><p class="risk-score">' + Math.round(result.overall_risk_score || 0) + '/100</p>' +
        '<p>' + (result.risk_summary || '') + '</p><h2>Clause Analysis</h2>';
    
    (result.clauses || []).forEach(function(c) {
        html += '<div class="clause ' + (c.risk_level || 'medium') + '">' +
            '<strong>' + formatClauseType(c.type) + '</strong> - ' + (c.risk_level || 'Medium') + ' Risk' +
            '<p>' + (c.text || c.clause_text || '') + '</p>' +
            (c.issue ? '<p><strong>Issue:</strong> ' + c.issue + '</p>' : '') +
            '</div>';
    });
    
    html += '</body></html>';
    
    var win = window.open('', '_blank');
    win.document.write(html);
    win.document.close();
    win.print();
}

// ==========================================
// UTILITIES
// ==========================================

function showLoading(text) {
    var overlay = document.getElementById('loading-overlay');
    var textEl = document.getElementById('loading-text');
    
    if (overlay) overlay.classList.remove('hidden');
    if (textEl) textEl.textContent = text || 'Loading...';
}

function hideLoading() {
    var overlay = document.getElementById('loading-overlay');
    if (overlay) overlay.classList.add('hidden');
}

function showToast(message, type) {
    var container = document.getElementById('toast-container');
    if (!container) return;
    
    var toast = document.createElement('div');
    toast.className = 'toast ' + (type || 'info');
    toast.innerHTML = '<span class="toast-message">' + message + '</span>';
    
    container.appendChild(toast);
    
    setTimeout(function() {
        toast.style.opacity = '0';
        setTimeout(function() {
            toast.remove();
        }, 300);
    }, 4000);
}

function formatClauseType(type) {
    if (!type) return 'Unknown';
    return type.replace(/_/g, ' ').replace(/\b\w/g, function(l) {
        return l.toUpperCase();
    });
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

