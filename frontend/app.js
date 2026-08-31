// API configuration: Set this to your backend service URL (e.g., "https://agentbridge-backend.onrender.com") when deploying on static hosts like GitHub Pages
// If left empty, it will default to relative URLs (useful for local development and Vercel deployments).
const API_BASE = "";

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Lucide Icons
    lucide.createIcons();

    // Global States
    let currentData = null;
    let simulationData = null;
    let isSimulating = false;
    let currentCurrency = "USD";

    // DOM Elements
    const intakeSection = document.getElementById("intake-section");
    const loadingSection = document.getElementById("loading-section");
    const resultsDashboard = document.getElementById("results-dashboard");
    const intakeForm = document.getElementById("intake-form");
    const loaderTitle = document.getElementById("loader-title");
    
    // New Editorial DOM Elements
    const homeSection = document.getElementById("home-section");
    const appWorkflowContainer = document.getElementById("app-workflow-container");
    const navBrandLogo = document.getElementById("nav-brand-logo");
    const startBlueprintBtns = document.querySelectorAll(".start-blueprint-btn");
    const navbarLinks = document.querySelectorAll(".navbar-link");
    
    // Tab Elements
    const tabButtons = document.querySelectorAll(".tab-btn[data-tab]");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const newStrategyBtn = document.getElementById("new-strategy-btn");
    const downloadReportBtn = document.getElementById("download-report-btn");

    // Loading agent configurations
    const agents = {
        profiler: {
            el: document.getElementById("agent-card-profiler"),
            activeText: "Extracting skills...",
            successText: "Extracted skills successfully",
            pendingText: "Extracting skills..."
        },
        country: {
            el: document.getElementById("agent-card-country"),
            activeText: "Comparing countries...",
            successText: "Compared destination countries",
            pendingText: "Comparing countries..."
        },
        funding: {
            el: document.getElementById("agent-card-funding"),
            activeText: "Searching scholarships...",
            successText: "Matched scholarships",
            pendingText: "Searching scholarships..."
        },
        strategy: {
            el: document.getElementById("agent-card-strategy"),
            activeText: "Building migration roadmap...",
            successText: "Optimized career & migration path",
            pendingText: "Building migration roadmap..."
        },
        blueprint: {
            el: document.getElementById("agent-card-blueprint"),
            activeText: "Preparing PDF blueprint...",
            successText: "Blueprint prepared successfully",
            pendingText: "Preparing PDF blueprint..."
        }
    };

    // Currency Formatting Helper
    function formatCurrency(val, isSalary = false, isMonthly = false) {
        if (currentCurrency === "INR") {
            const converted = val * 95;
            const formatted = Math.round(converted).toLocaleString('en-IN');
            if (isSalary) {
                return `₹${formatted} / yr`;
            } else if (isMonthly) {
                return `₹${formatted} / mo`;
            } else {
                return `₹${formatted}`;
            }
        } else {
            const formatted = Math.round(val).toLocaleString('en-US');
            if (isSalary) {
                return `$${formatted} / yr`;
            } else if (isMonthly) {
                return `$${formatted} / mo`;
            } else {
                return `$${formatted}`;
            }
        }
    }

    // Currency Toggle Event Listeners
    const currencyUsdBtn = document.getElementById("currency-usd");
    const currencyInrBtn = document.getElementById("currency-inr");

    if (currencyUsdBtn && currencyInrBtn) {
        currencyUsdBtn.addEventListener("click", () => updateCurrency("USD"));
        currencyInrBtn.addEventListener("click", () => updateCurrency("INR"));
    }

    function updateCurrency(currency) {
        currentCurrency = currency;
        
        if (currency === "USD") {
            currencyUsdBtn.classList.add("active");
            currencyInrBtn.classList.remove("active");
        } else {
            currencyInrBtn.classList.add("active");
            currencyUsdBtn.classList.remove("active");
        }

        if (currentData) {
            renderDashboard(currentData);
        }
        if (simulationData) {
            renderSimulation(simulationData);
        }
    }

    // --- Transition Handlers ---

    // Click Brand Logo to Return to Homepage
    navBrandLogo.addEventListener("click", (e) => {
        e.preventDefault();
        appWorkflowContainer.classList.add("hidden");
        homeSection.classList.remove("hidden");
        window.scrollTo({ top: 0, behavior: "smooth" });
    });

    // Click "Build My Blueprint" CTA to show Intake Form
    startBlueprintBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            homeSection.classList.add("hidden");
            appWorkflowContainer.classList.remove("hidden");
            intakeSection.classList.remove("hidden");
            loadingSection.classList.add("hidden");
            resultsDashboard.classList.add("hidden");
            window.scrollTo({ top: 0, behavior: "smooth" });
        });
    });

    // Navbar Navigation Smooth Scroll
    navbarLinks.forEach(link => {
        link.addEventListener("click", (e) => {
            const href = link.getAttribute("href");
            if (href.startsWith("#")) {
                e.preventDefault();
                // If in app workflow container, transition back to home
                if (homeSection.classList.contains("hidden")) {
                    appWorkflowContainer.classList.add("hidden");
                    homeSection.classList.remove("hidden");
                }
                const targetElement = document.querySelector(href);
                if (targetElement) {
                    targetElement.scrollIntoView({ behavior: "smooth" });
                }
            }
        });
    });

    // --- Sequential Agent Pulse Animation ---
    let currentFlowStep = 0;
    const flowchartNodes = document.querySelectorAll(".system-node");
    const flowchartConnectors = document.querySelectorAll(".system-connector");

    function animateAgentFlow() {
        // Reset all nodes and links
        flowchartNodes.forEach(node => node.classList.remove("active-node"));
        flowchartConnectors.forEach(conn => conn.classList.remove("active-link"));

        // Highlight current node
        const activeNode = document.querySelector(`.system-node[data-step="${currentFlowStep}"]`);
        if (activeNode) {
            activeNode.classList.add("active-node");
        }

        // Highlight following link
        const activeConn = document.querySelector(`.system-connector[data-link="${currentFlowStep}"]`);
        if (activeConn) {
            activeConn.classList.add("active-link");
        }

        // Increment step
        currentFlowStep = (currentFlowStep + 1) % 5;
    }

    // Run animation every 2.2 seconds
    if (flowchartNodes.length > 0) {
        animateAgentFlow();
        setInterval(animateAgentFlow, 2200);
    }

    // Form submission
    intakeForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const degreeLevel = document.getElementById("degree-level").value;
        const resumeText = document.getElementById("resume-text").value;
        const goalsText = document.getElementById("goals-text").value;

        // 1. Transition to loading state
        intakeSection.classList.add("hidden");
        loadingSection.classList.remove("hidden");
        
        // Hide any previous errors
        const errorContainer = document.getElementById("loading-error");
        if (errorContainer) errorContainer.classList.add("hidden");
        
        // Reset loading agent states
        Object.keys(agents).forEach(key => {
            updateAgentState(key, "pending");
        });
        
        // Reset progress bar
        const bar = document.getElementById("global-progress-bar");
        const text = document.getElementById("global-progress-percent");
        const timeVal = document.getElementById("time-remaining-value");
        if (bar) bar.style.width = "0%";
        if (text) text.textContent = "0%";
        if (timeVal) timeVal.textContent = "15 seconds";
        currentProgress = 0;

        try {
            // Start the backend API pipeline call immediately in parallel
            let apiDone = false;
            let apiData = null;
            let apiError = null;

            const apiPromise = fetch(`${API_BASE}/api/analyze`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    resume_text: resumeText,
                    goals: goalsText,
                    degree_level: degreeLevel
                })
            }).then(async res => {
                if (!res.ok) {
                    let errText = "Unable to process profile strategy";
                    try {
                        const err = await res.json();
                        errText = err.detail || errText;
                    } catch (jsonErr) {
                        try {
                            errText = await res.text();
                        } catch (txtErr) {}
                    }
                    throw new Error(errText);
                }
                return res.json();
            }).then(data => {
                apiData = data;
                apiDone = true;
            }).catch(err => {
                apiError = err;
                apiDone = true;
            });

            // 1. Resume Profiler (0% -> 20%)
            updateAgentState("profiler", "active");
            await setProgress(20, () => apiDone);
            if (apiError) throw apiError;
            
            let skillsText = "Extracted skills successfully";
            if (apiData && apiData.profile && apiData.profile.skills_identified) {
                skillsText = `Extracted ${apiData.profile.skills_identified.length} technical skills`;
            }
            updateAgentState("profiler", "success", skillsText);

            // 2. Country Intelligence (20% -> 45%)
            updateAgentState("country", "active");
            await setProgress(45, () => apiDone);
            if (apiError) throw apiError;
            
            let countriesText = "Compared destination countries";
            if (apiData && apiData.explorer && apiData.explorer.matched_countries) {
                countriesText = `Compared ${apiData.explorer.matched_countries.length} destination countries`;
            }
            updateAgentState("country", "success", countriesText);

            // 3. Funding Agent (45% -> 70%)
            updateAgentState("funding", "active");
            await setProgress(70, () => apiDone);
            if (apiError) throw apiError;
            
            let fundingText = "Matched scholarships";
            if (apiData && apiData.funding && apiData.funding.matching_scholarships) {
                fundingText = `Matched ${apiData.funding.matching_scholarships.length} scholarships`;
            }
            updateAgentState("funding", "success", fundingText);

            // 4. Strategy Planner (70% -> 90%)
            updateAgentState("strategy", "active");
            await setProgress(90, () => apiDone);
            if (apiError) throw apiError;
            
            updateAgentState("strategy", "success", "Optimized career & migration path");

            // 5. Blueprint Generator (90% -> 100%)
            updateAgentState("blueprint", "active");
            
            // Wait for backend to finish before completing final step
            while (!apiDone) {
                await sleep(100);
            }
            if (apiError) throw apiError;

            await setProgress(100, () => true);
            updateAgentState("blueprint", "success", "Blueprint prepared successfully");
            
            // Short visual pause for premium completion feedback
            await sleep(500);
            
            // 2. Render Results
            currentData = apiData;
            renderDashboard(apiData);
            
            // 3. Transition to Results Dashboard
            loadingSection.classList.add("hidden");
            resultsDashboard.classList.remove("hidden");
            const advisorWidget = document.getElementById("ai-advisor-widget");
            if (advisorWidget) advisorWidget.classList.remove("hidden");
            
        } catch (error) {
            console.error(error);
            
            const errDiv = document.getElementById("loading-error");
            const errMsgText = document.getElementById("error-message-text");
            const errRetryBtn = document.getElementById("error-retry-btn");
            
            if (errDiv && errMsgText) {
                let userFriendlyMessage = error.message || String(error);
                if (userFriendlyMessage.includes("NVIDIA_API_KEY") || userFriendlyMessage.includes("NVIDIA API key") || userFriendlyMessage.includes("Missing NVIDIA")) {
                    userFriendlyMessage = "The NVIDIA NIM API key is missing or invalid in the environment configurations. Please ensure it is correctly defined in 'backend/.env'.";
                } else if (userFriendlyMessage.includes("Failed to fetch") || userFriendlyMessage.includes("NetworkError") || userFriendlyMessage.includes("network")) {
                    userFriendlyMessage = "Unable to connect to the AI planning services. Please verify your internet connection or check if the backend server is running.";
                } else if (userFriendlyMessage.includes("Pipeline execution failed") || userFriendlyMessage.includes("500") || userFriendlyMessage.includes("Internal Server Error")) {
                    userFriendlyMessage = "The AI agents encountered an error while analyzing your profile. Please check that your inputs are descriptive and try again.";
                }
                errMsgText.textContent = userFriendlyMessage;
                errDiv.classList.remove("hidden");
                
                errRetryBtn.onclick = () => {
                    errDiv.classList.add("hidden");
                    loadingSection.classList.add("hidden");
                    intakeSection.classList.remove("hidden");
                };
            } else {
                let userFriendlyMessage = error.message || String(error);
                if (userFriendlyMessage.includes("NVIDIA_API_KEY") || userFriendlyMessage.includes("NVIDIA API key") || userFriendlyMessage.includes("Missing NVIDIA")) {
                    userFriendlyMessage = "The NVIDIA NIM API key is missing or invalid. Please check 'backend/.env'.";
                }
                alert(`Analysis failed: ${userFriendlyMessage}. Please retry.`);
                loadingSection.classList.add("hidden");
                intakeSection.classList.remove("hidden");
            }
        }
    });

    // Reset Dashboard
    newStrategyBtn.addEventListener("click", () => {
        resultsDashboard.classList.add("hidden");
        const advisorWidget = document.getElementById("ai-advisor-widget");
        if (advisorWidget) advisorWidget.classList.add("hidden");
        intakeSection.classList.remove("hidden");
        intakeForm.reset();
        currentData = null;
        simulationData = null;
        updateCurrency("USD");
    });

    // Tab switcher logic
    tabButtons.forEach(btn => {
        btn.addEventListener("click", async () => {
            const targetTab = btn.getAttribute("data-tab");
            
            // Active button swap
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            // Panel swap
            tabPanels.forEach(panel => {
                panel.classList.remove("active");
                if (panel.id === targetTab) {
                    panel.classList.add("active");
                }
            });

            // If simulator tab is clicked and not loaded, trigger simulation
            if (targetTab === "tab-simulator" && !simulationData && !isSimulating && currentData) {
                await runScenarioSimulation();
            }
        });
    });

    // Download strategic report
    downloadReportBtn.addEventListener("click", async () => {
        if (!currentData) return;
        try {
            downloadReportBtn.innerHTML = `<span class="spinner" style="width:14px;height:14px;border-width:2px;margin-bottom:0;display:inline-block;vertical-align:middle;margin-right:6px;"></span> Exporting PDF...`;
            lucide.createIcons();

            const response = await fetch(`${API_BASE}/api/report/download`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    profile: currentData.profile,
                    explorer: currentData.explorer,
                    funding: currentData.funding,
                    simulation: simulationData,
                    currency: currentCurrency
                })
            });

            if (!response.ok) {
                throw new Error("Failed to generate PDF document");
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = "AgentBridge_Global_Career_Blueprint.pdf";
            document.body.appendChild(a);
            a.click();
            a.remove();
            
            showToast("✓ Blueprint downloaded successfully", "success");
        } catch (err) {
            console.error(err);
            showToast(err.message || "Failed to export PDF blueprint. Please try again.", "error");
        } finally {
            downloadReportBtn.innerHTML = `<i data-lucide="file-text"></i> Download PDF Blueprint`;
            lucide.createIcons();
        }
    });

    // Run Scenario Simulator API
    async function runScenarioSimulation() {
        isSimulating = true;
        const container = document.getElementById("simulator-cards-container");
        container.innerHTML = `
            <div style="text-align: center; padding: 32px; grid-column: 1 / -1;">
                <div class="spinner" style="width: 32px; height: 32px; margin: 0 auto 12px;"></div>
                <p style="color: var(--text-secondary);">AI Scenario Planner simulating India, Japan, Germany, and Canada outcomes...</p>
            </div>
        `;
        
        // Read simulator input fields
        const budgetInput = document.getElementById("sim-budget");
        const expInput = document.getElementById("sim-experience");
        const scholInput = document.getElementById("sim-scholarship");
        
        let budget = budgetInput && budgetInput.value ? parseInt(budgetInput.value) : null;
        let experience = expInput && expInput.value ? expInput.value : null;
        let scholarship = scholInput ? scholInput.checked : false;

        try {
            const response = await fetch(`${API_BASE}/api/simulate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    profile_data: currentData.profile,
                    goals: document.getElementById("goals-text").value,
                    budget: budget,
                    experience_level: experience,
                    require_scholarship: scholarship
                })
            });

            if (!response.ok) {
                throw new Error("Simulation endpoint failed");
            }

            const result = await response.json();
            simulationData = result;
            renderSimulation(result);
        } catch (error) {
            console.error(error);
            container.innerHTML = `
                <div style="text-align: center; padding: 24px; color: var(--danger); grid-column: 1 / -1;">
                    <i data-lucide="alert-circle" style="width: 24px; height: 24px; margin: 0 auto 8px;"></i>
                    <p>Simulation failed due to API limits. Please toggle another tab and return to retry.</p>
                </div>
            `;
            lucide.createIcons();
        } finally {
            isSimulating = false;
        }
    }

    const simRecalcBtn = document.getElementById("sim-recalculate-btn");
    if (simRecalcBtn) {
        simRecalcBtn.addEventListener("click", () => {
            if (currentData) runScenarioSimulation();
        });
    }

    // Render Simulation Cards
    function renderSimulation(result) {
        const container = document.getElementById("simulator-cards-container");
        container.innerHTML = "";

        // Filter for Stay in India, Japan, Germany, Canada
        const targetCodes = ["IN", "JP", "DE", "CA"];
        const filteredScenarios = result.scenarios.filter(s => targetCodes.includes(s.country_code));

        filteredScenarios.forEach(item => {
            const card = document.createElement("div");
            const isIndia = item.country_code === "IN";
            card.className = `simulator-card fade-in ${isIndia ? 'stay-india' : ''}`;
            
            const costLabel = isIndia ? "Annual Living Cost" : "1st-Year Migration Cost";
            const timelineLabel = isIndia ? "Time to Target Role" : "Time to Job Post-Grad";

            const complexityBadgeClass = `badge-${(item.visa_complexity || 'Medium').toLowerCase()}`;
            const riskBadgeClass = `badge-${(item.risk_level || 'Low').toLowerCase()}`;

            card.innerHTML = `
                <div class="simulator-card-header">
                    <h3>${isIndia ? 'Stay in India' : 'Move to ' + item.country_name}</h3>
                    <span class="emp-badge">Index: ${item.employability_score}/10</span>
                </div>
                <div class="simulator-body">
                    <div class="simulator-row">
                        <span class="label">${costLabel}</span>
                        <span class="val">${formatCurrency(item.migration_cost_1yr_usd)}</span>
                    </div>
                    <div class="simulator-row">
                        <span class="label">Expected Starting Salary</span>
                        <span class="val">${formatCurrency(item.expected_salary_usd, true)}</span>
                    </div>
                    <div class="simulator-row">
                        <span class="label">${timelineLabel}</span>
                        <span class="val">${item.time_to_employment_months} Months</span>
                    </div>
                    <div class="simulator-row">
                        <span class="label">Visa Complexity</span>
                        <span class="badge ${complexityBadgeClass}">${item.visa_complexity}</span>
                    </div>
                    <div class="simulator-row">
                        <span class="label">Risk Level</span>
                        <span class="badge ${riskBadgeClass}">${item.risk_level}</span>
                    </div>
                    <div class="simulator-analysis">
                        <strong>Agent Impact Rating:</strong> ${item.analysis_summary}
                    </div>
                </div>
            `;
            container.appendChild(card);
        });
        lucide.createIcons();
    }

    // Global progress tracker
    let currentProgress = 0;

    // Smoothly animate progress bar
    function setProgress(target, checkApiDone) {
        return new Promise(resolve => {
            const start = currentProgress;
            const diff = target - start;
            const startTime = performance.now();
            
            function tick(now) {
                const isFast = checkApiDone && checkApiDone();
                const duration = isFast ? 150 : 800; // Fast-forward if API returns early
                
                const elapsed = now - startTime;
                const fraction = Math.min(elapsed / duration, 1);
                currentProgress = start + diff * fraction;
                
                const bar = document.getElementById("global-progress-bar");
                const text = document.getElementById("global-progress-percent");
                const timeVal = document.getElementById("time-remaining-value");

                if (bar) bar.style.width = `${currentProgress}%`;
                if (text) text.textContent = `${Math.round(currentProgress)}%`;
                
                if (timeVal) {
                    const sec = Math.max(1, Math.round(15 * (1 - currentProgress / 100)));
                    timeVal.textContent = `${sec} second${sec !== 1 ? 's' : ''}`;
                }

                if (fraction < 1) {
                    requestAnimationFrame(tick);
                } else {
                    resolve();
                }
            }
            requestAnimationFrame(tick);
        });
    }

    // Helper to update agent status states
    function updateAgentState(agentKey, state, dynamicVal = "") {
        const agent = agents[agentKey];
        if (!agent || !agent.el) return;
        
        agent.el.className = `agent-card ${state}`;
        const pill = agent.el.querySelector(".status-pill");
        const statusText = agent.el.querySelector(".dynamic-status");
        
        if (pill) {
            if (state === "active") pill.textContent = "In Progress";
            else if (state === "success") pill.textContent = "Completed";
            else pill.textContent = "Pending";
        }
        
        if (statusText) {
            if (state === "success") {
                statusText.textContent = dynamicVal || agent.successText;
            } else if (state === "active") {
                statusText.textContent = agent.activeText;
            } else {
                statusText.textContent = agent.pendingText;
            }
        }
        lucide.createIcons();
    }

    // Toast message helper
    function showToast(message, type = "success") {
        const container = document.getElementById("toast-container");
        if (!container) return;
        
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        
        const icon = type === "success" ? "check-circle" : "alert-circle";
        toast.innerHTML = `
            <i data-lucide="${icon}" class="toast-icon"></i>
            <span class="toast-message">${message}</span>
        `;
        
        container.appendChild(toast);
        lucide.createIcons();
        
        // Force reflow and transition show
        setTimeout(() => toast.classList.add("show"), 10);
        
        // Auto remove toast
        setTimeout(() => {
            toast.classList.remove("show");
            setTimeout(() => toast.remove(), 400);
        }, 4000);
    }

    // Smooth count up numbers
    function animateCountUp(elementId, targetValue, prefix = "", suffix = "", isInt = true) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        let startValue = 0;
        const duration = 1200;
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = progress * (2 - progress);
            const currentValue = startValue + (targetValue - startValue) * easeProgress;
            
            const displayVal = isInt ? Math.round(currentValue) : parseFloat(currentValue.toFixed(1));
            el.textContent = `${prefix}${displayVal.toLocaleString()}${suffix}`;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.textContent = `${prefix}${targetValue.toLocaleString()}${suffix}`;
            }
        }
        requestAnimationFrame(update);
    }

    // Smooth count up currency format
    function animateCurrencyCountUp(elementId, targetValue, isSalary = false, isMonthly = false, prefix = "", suffix = "") {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        const startValue = 0;
        const duration = 1200;
        const startTime = performance.now();
        
        function update(currentTime) {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easeProgress = progress * (2 - progress);
            const currentValue = startValue + (targetValue - startValue) * easeProgress;
            
            el.textContent = `${prefix}${formatCurrency(currentValue, isSalary, isMonthly)}${suffix}`;
            
            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.textContent = `${prefix}${formatCurrency(targetValue, isSalary, isMonthly)}${suffix}`;
            }
        }
        requestAnimationFrame(update);
    }

    // Animate progress bar widths once
    function animateProgressBarOnce(elementId, targetWidthPercent) {
        const bar = document.getElementById(elementId);
        if (!bar) return;
        bar.style.width = "0%";
        bar.offsetHeight; // Force layout recalculation
        bar.style.transition = "width 1.5s cubic-bezier(0.1, 0.8, 0.25, 1)";
        bar.style.width = `${targetWidthPercent}%`;
    }

    // Helper sleep timer
    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function calculateBudgetOptimizedPath(data) {
        const funding = data.funding;
        const explorer = data.explorer;
        
        let bestPath = null;
        let minOutOfPocket = Infinity;
        
        funding.cost_analysis.forEach(cost => {
            const code = cost.country_code;
            const countryInfo = explorer.matched_countries.find(c => c.country_code === code) || {};
            const countryName = countryInfo.country_name || code;
            
            const scholarships = funding.matching_scholarships.filter(s => s.country_code === code);
            const topScholarship = scholarships.reduce((max, s) => (!max || s.award_amount_usd > max.award_amount_usd) ? s : max, null);
            const scholarshipAmt = topScholarship ? topScholarship.award_amount_usd : 0;
            const scholarshipName = topScholarship ? topScholarship.name : "No matching merit scholarships";
            
            const univType = cost.annual_tuition_usd < 5000 ? "Public (Tuition Free / Low Fee)" : "Private / Institutional";
            
            let hourlyWage = 12;
            if (code === "DE") hourlyWage = 15;
            else if (code === "JP") hourlyWage = 8;
            else if (code === "NL") hourlyWage = 16;
            else if (code === "AU") hourlyWage = 15;
            else if (code === "CA") hourlyWage = 12;
            
            const partTimeEarnings = 960 * hourlyWage;
            const originalCost = cost.gross_first_year_cost_usd;
            
            const outOfPocket = Math.max(0, originalCost - scholarshipAmt - partTimeEarnings);
            const affordabilityScore = Math.max(1, Math.min(10, Math.round(10 - (outOfPocket / 5000))));
            
            if (outOfPocket < minOutOfPocket) {
                minOutOfPocket = outOfPocket;
                
                let explanation = "";
                if (code === "DE") {
                    explanation = "Germany offers tuition-free public university education, significantly lowering the upfront barrier. Combined with DAAD merit funding and student part-time work, the first-year out-of-pocket cost is fully offset, making it the most affordable strategic option.";
                } else if (code === "JP") {
                    explanation = "Japan offers very low tuition fees at public universities and a reasonable cost of living. Sourcing local institutional waivers and part-time teaching/assistant roles provides a highly cost-effective gateway with excellent ROI.";
                } else {
                    explanation = `Relocating to ${countryName} under this pathway utilizes high-value scholarship offsets combined with the maximum allowed part-time work hours, substantially reducing the initial cash-flow requirements while positioning you for premium local tech salaries.`;
                }
                
                bestPath = {
                    countryName,
                    countryCode: code,
                    univType,
                    scholarshipName,
                    scholarshipAmt,
                    partTimeEarnings,
                    originalCost,
                    outOfPocket,
                    expectedSalary: cost.expected_salary_usd,
                    roi: cost.financial_roi_score,
                    affordabilityScore,
                    explanation
                };
            }
        });
        
        return bestPath;
    }

    // Main Renderer
    function renderDashboard(data) {
        const profile = data.profile;
        const explorer = data.explorer;
        const funding = data.funding;

        // --- AI AGENT STATUS MINI CARD DYNAMIC UPDATES ---
        const updateMiniStatus = (elementId, name, isFallback) => {
            const el = document.getElementById(elementId);
            if (!el) return;
            if (isFallback) {
                el.className = "agent-status-mini-item fallback-active";
                el.innerHTML = `<span class="status-icon warning-icon">⚠</span> <span class="agent-name-label">${name} (Database Fallback)</span>`;
            } else {
                el.className = "agent-status-mini-item";
                el.innerHTML = `<span class="status-icon success-icon">✓</span> <span class="agent-name-label">${name}</span>`;
            }
        };

        updateMiniStatus("mini-status-profiler", "Resume Profiler", !!(profile && profile.is_fallback));
        updateMiniStatus("mini-status-country", "Country Intelligence", !!(explorer && explorer.is_fallback));
        updateMiniStatus("mini-status-funding", "Funding Agent", !!(funding && funding.is_fallback));
        updateMiniStatus("mini-status-strategy", "Strategy Planner", !!(data && data.is_strategy_fallback));
        updateMiniStatus("mini-status-blueprint", "Blueprint Generator", !!(data && data.is_blueprint_fallback));

        // --- SECTION 1: EXECUTIVE SUMMARY ---
        // Best match country
        const bestCountryCard = explorer.matched_countries.reduce((max, c) => c.match_score > max.match_score ? c : max, explorer.matched_countries[0]);
        document.getElementById("summary-best-country").textContent = bestCountryCard.country_name;
        animateCountUp("summary-best-country-sub", bestCountryCard.match_score, "", "% compatibility match");

        // Overall employability score (0-100)
        const overallEmpIndex = profile.employability_index_100 || (profile.employability_index * 10);
        animateCountUp("summary-employability-score", overallEmpIndex);
        animateProgressBarOnce("summary-employability-bar", overallEmpIndex);

        // Top scholarship opportunity (filtered by the best country)
        const bestCountryScholarships = funding.matching_scholarships.filter(s => s.country_code === bestCountryCard.country_code);
        const topScholarshipCard = bestCountryScholarships.reduce((max, s) => s.award_amount_usd > max.award_amount_usd ? s : max, bestCountryScholarships[0] || {});
        document.getElementById("summary-top-scholarship").textContent = topScholarshipCard.name || "No major scholarship matched";
        if (topScholarshipCard.award_amount_usd) {
            animateCurrencyCountUp("summary-top-scholarship-sub", topScholarshipCard.award_amount_usd, false, false, "Up to ", " funding");
        } else {
            document.getElementById("summary-top-scholarship-sub").textContent = `Institutional waivers available`;
        }

        // Estimated migration cost
        const bestCountryCostInfo = funding.cost_analysis.find(cost => cost.country_code === bestCountryCard.country_code) || {};
        const estMigrationCost = bestCountryCostInfo.gross_first_year_cost_usd || (bestCountryCard.country_code === 'NL' ? 38230 : 19180);
        animateCurrencyCountUp("summary-migration-cost", estMigrationCost);

        // Confidence score
        const confidenceScore = Math.min(98, Math.max(72, Math.round(bestCountryCard.match_score * 0.6 + overallEmpIndex * 0.4)));
        animateCountUp("summary-confidence-score", confidenceScore, "", "%");
        animateProgressBarOnce("summary-confidence-bar", confidenceScore);


        // --- SECTION 2: EMPLOYABILITY ANALYSIS ---
        animateCountUp("employability-score-large", overallEmpIndex);
        document.getElementById("profile-summary-text").textContent = profile.summary;
        document.getElementById("target-role-label").textContent = profile.target_role;

        // Render Strengths list
        const strengthsList = document.getElementById("profile-strengths-list");
        strengthsList.innerHTML = "";
        const strengths = profile.strengths || [];
        if (strengths.length === 0) {
            const li = document.createElement("li");
            li.style.color = "var(--text-secondary)";
            li.style.fontStyle = "italic";
            li.textContent = "No specific strengths identified yet.";
            strengthsList.appendChild(li);
        } else {
            strengths.forEach(str => {
                const li = document.createElement("li");
                li.textContent = str;
                strengthsList.appendChild(li);
            });
        }

        // Render skill tags
        const tagsContainer = document.getElementById("skills-tags");
        tagsContainer.innerHTML = "";
        const skillsIdentified = profile.skills_identified || [];
        if (skillsIdentified.length === 0) {
            tagsContainer.innerHTML = `<span style="color: var(--text-secondary); font-style: italic; font-size: 14px;">No technical skills identified.</span>`;
        } else {
            skillsIdentified.forEach(skill => {
                const tag = document.createElement("span");
                tag.className = "tag";
                tag.textContent = skill;
                tagsContainer.appendChild(tag);
            });
        }

        // Render skill gaps list
        const gapsList = document.getElementById("skill-gaps-list");
        gapsList.innerHTML = "";
        const skillGaps = profile.skill_gaps || [];
        if (skillGaps.length === 0) {
            const li = document.createElement("li");
            li.style.color = "var(--text-secondary)";
            li.style.fontStyle = "italic";
            li.textContent = "No critical skill gaps identified.";
            gapsList.appendChild(li);
        } else {
            skillGaps.forEach(gap => {
                const li = document.createElement("li");
                li.textContent = gap;
                gapsList.appendChild(li);
            });
        }

        // Render Certifications list
        const certsList = document.getElementById("recommended-certs-list");
        certsList.innerHTML = "";
        const recommendedCerts = profile.recommended_certifications || [];
        if (recommendedCerts.length === 0) {
            const li = document.createElement("li");
            li.style.color = "var(--text-secondary)";
            li.style.fontStyle = "italic";
            li.textContent = "No recommended certifications needed.";
            certsList.appendChild(li);
        } else {
            recommendedCerts.forEach(cert => {
                const li = document.createElement("li");
                li.textContent = cert;
                certsList.appendChild(li);
            });
        }

        // Render Projects list
        const projectsList = document.getElementById("recommended-projects-list");
        projectsList.innerHTML = "";
        const recommendedProjects = profile.recommended_projects || [];
        if (recommendedProjects.length === 0) {
            const li = document.createElement("li");
            li.style.color = "var(--text-secondary)";
            li.style.fontStyle = "italic";
            li.textContent = "No recommended projects needed.";
            projectsList.appendChild(li);
        } else {
            recommendedProjects.forEach(proj => {
                const li = document.createElement("li");
                li.textContent = proj;
                projectsList.appendChild(li);
            });
        }


        // --- SECTION 3: COUNTRY COMPARISON DASHBOARD ---
        const countryContainer = document.getElementById("country-cards-container");
        countryContainer.innerHTML = "";

        explorer.matched_countries.forEach(country => {
            const costInfo = funding.cost_analysis.find(cost => cost.country_code === country.country_code) || {};
            const totalCost = costInfo.gross_first_year_cost_usd ? formatCurrency(costInfo.gross_first_year_cost_usd) : "N/A";
            const salary = costInfo.expected_salary_usd ? formatCurrency(costInfo.expected_salary_usd, true) : "N/A";

            const complexityClass = `badge-${(country.visa_complexity || 'Medium').toLowerCase()}`;
            const barrierClass = `badge-${(country.language_barrier || 'Low').toLowerCase()}`;
            const riskClass = `badge-${(country.risk_level || 'Low').toLowerCase()}`;

            const flagMap = {
                "JP": "🇯🇵", "Japan": "🇯🇵",
                "DE": "🇩🇪", "Germany": "🇩🇪",
                "CA": "🇨🇦", "Canada": "🇨🇦",
                "AU": "🇦🇺", "Australia": "🇦🇺",
                "NL": "🇳🇱", "Netherlands": "🇳🇱",
                "IN": "🇮🇳", "India": "🇮🇳"
            };
            const flag = flagMap[country.country_code] || flagMap[country.country_name] || "🌐";

            let riskEmoji = "🟢";
            if ((country.risk_level || "").toLowerCase() === "medium") {
                riskEmoji = "🟡";
            } else if ((country.risk_level || "").toLowerCase() === "high") {
                riskEmoji = "🔴";
            }

            const card = document.createElement("div");
            card.className = "country-comparison-card fade-in";
            card.innerHTML = `
                <div class="country-card-header">
                    <h3><span class="country-flag">${flag}</span> ${country.country_name}</h3>
                    <span class="match-percentage">${country.match_score}% Match</span>
                </div>
                <div class="comparison-details">
                    <div class="metric-row">
                        <span class="label">Match Score</span>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width: ${country.match_score}%"></div>
                        </div>
                    </div>
                    <div class="metric-row">
                        <span class="label">Total Cost (1Yr)</span>
                        <span class="val">${totalCost}</span>
                    </div>
                    <div class="metric-row">
                        <span class="label">Visa Complexity</span>
                        <span class="badge ${complexityClass}">${country.visa_complexity || 'Medium'}</span>
                    </div>
                    <div class="metric-row">
                        <span class="label">Language Barrier</span>
                        <span class="badge ${barrierClass}">${country.language_barrier || 'Low'}</span>
                    </div>
                    <div class="metric-row">
                        <span class="label">Post-Study Work</span>
                        <span class="val">${country.post_study_work_months} Months</span>
                    </div>
                    <div class="metric-row">
                        <span class="label">Salary Potential</span>
                        <span class="val">${salary}</span>
                    </div>
                    <div class="metric-row">
                        <span class="label">Risk Level</span>
                        <span class="badge ${riskClass}">${riskEmoji} ${country.risk_level || 'Low'}</span>
                    </div>
                    ${country.positive_factors && country.positive_factors.length > 0 ? `
                    <div class="explainability-section" style="margin-top:16px; padding-top:16px; border-top:1px solid rgba(255,255,255,0.05);">
                        <h4 style="font-size:11px; text-transform:uppercase; color:var(--success); margin:0 0 8px 0; display:flex; align-items:center; gap:4px;"><i data-lucide="thumbs-up" style="width:12px;height:12px;"></i> Why this country?</h4>
                        <ul style="margin:0; padding-left:16px; font-size:12px; color:var(--text-secondary);">
                            ${country.positive_factors.map(f => `<li>${f}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                    ${country.drawbacks && country.drawbacks.length > 0 ? `
                    <div class="explainability-section" style="margin-top:12px;">
                        <h4 style="font-size:11px; text-transform:uppercase; color:var(--danger); margin:0 0 8px 0; display:flex; align-items:center; gap:4px;"><i data-lucide="thumbs-down" style="width:12px;height:12px;"></i> Drawbacks</h4>
                        <ul style="margin:0; padding-left:16px; font-size:12px; color:var(--text-secondary);">
                            ${country.drawbacks.map(f => `<li>${f}</li>`).join('')}
                        </ul>
                    </div>
                    ` : ''}
                    <div class="risk-alert" style="margin-top:16px;">
                        <span class="label"><i data-lucide="alert-triangle"></i> Strategic Risk Factors</span>
                        <p>${country.risk_analysis}</p>
                    </div>
                </div>
            `;
            countryContainer.appendChild(card);
        });


        // --- SECTION 4: FINANCIAL ANALYSIS ---
        const roiTableBody = document.getElementById("roi-table-body");
        roiTableBody.innerHTML = "";

        funding.cost_analysis.forEach(cost => {
            const countryInfo = explorer.matched_countries.find(c => c.country_code === cost.country_code) || {};
            const countryName = countryInfo.country_name || cost.country_code;

            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${countryName}</strong></td>
                <td>${formatCurrency(cost.annual_tuition_usd, true)}</td>
                <td>${formatCurrency(cost.annual_living_usd, true)}</td>
                <td>${formatCurrency(cost.visa_app_fee_usd)}</td>
                <td>${formatCurrency(cost.health_insurance_usd)}</td>
                <td>${formatCurrency(cost.first_year_setup_usd)}</td>
                <td><strong>${formatCurrency(cost.gross_first_year_cost_usd)}</strong></td>
                <td><span class="badge" style="background: rgba(16, 185, 129, 0.1); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2)">${cost.financial_roi_score}/10</span></td>
            `;
            roiTableBody.appendChild(tr);
        });


        // --- SECTION 5: SCHOLARSHIP CENTER ---
        const scholarshipsContainer = document.getElementById("scholarships-container");
        scholarshipsContainer.innerHTML = "";

        if (!funding.matching_scholarships || funding.matching_scholarships.length === 0) {
            scholarshipsContainer.innerHTML = `
                <div class="card interior-card" style="text-align: center; padding: 40px; grid-column: 1 / -1;">
                    <i data-lucide="award" style="width: 48px; height: 48px; color: var(--text-secondary); margin: 0 auto 16px;"></i>
                    <h3>No Direct Scholarships Found</h3>
                    <p style="color: var(--text-secondary); max-width: 400px; margin: 8px auto 0;">No matching merit scholarships were returned for this specific filter. We recommend checking individual university tuition fee waiver databases.</p>
                </div>
            `;
        } else {
            funding.matching_scholarships.forEach(sch => {
                const card = document.createElement("div");
                card.className = "card scholarship-card fade-in";
                card.innerHTML = `
                    <div class="scholarship-title">
                        <h3>${sch.name}</h3>
                        <span class="sponsor">${sch.sponsor}</span>
                    </div>
                    <div class="scholarship-amount">${formatCurrency(sch.award_amount_usd)}</div>
                    <p>${sch.eligibility_summary}</p>
                    <div class="scholarship-meta">
                        <span>Deadline: <strong>${sch.deadline}</strong></span>
                        <a href="${sch.application_link}" target="_blank" class="scholarship-link">
                            Apply Info <i data-lucide="external-link" style="width: 14px; height: 14px;"></i>
                        </a>
                    </div>
                `;
                scholarshipsContainer.appendChild(card);
            });
        }


        // --- SECTION 7: STRATEGIC ROADMAP ---
        const defaultCountry = explorer.matched_countries.find(c => c.country_code === bestCountryCard.country_code) || explorer.matched_countries[0] || { country_name: "Target Country", visa_route: "Student Visa" };

        // Bind Roadmap Summary Panel values
        const panelRole = document.getElementById("roadmap-panel-role");
        const panelSalary = document.getElementById("roadmap-panel-salary");
        const panelRisk = document.getElementById("roadmap-panel-risk");
        const panelRiskDesc = document.getElementById("roadmap-risk-description");

        if (panelRole) panelRole.textContent = profile.target_role;
        if (panelSalary) {
            const expectedSalaryVal = bestCountryCostInfo.expected_salary_usd || 75000;
            panelSalary.textContent = `${formatCurrency(expectedSalaryVal, true)}`;
        }
        if (panelRisk) {
            const riskVal = defaultCountry.risk_level || "Low";
            panelRisk.textContent = riskVal.toUpperCase();
            panelRisk.className = `risk-badge risk-${riskVal.toLowerCase()}`;
        }
        if (panelRiskDesc) {
            panelRiskDesc.textContent = defaultCountry.risk_analysis || "Ensure timely financial proof preparation and visa route verification.";
        }

        // Set up View Risk Mitigation Plan button click to route to Country Comparison Tab
        const viewRiskMitigationBtn = document.getElementById("view-risk-mitigation-btn");
        if (viewRiskMitigationBtn) {
            viewRiskMitigationBtn.onclick = () => {
                const countriesTabBtn = document.querySelector('[data-tab="tab-countries"]');
                if (countriesTabBtn) {
                    countriesTabBtn.click();
                    setTimeout(() => {
                        const container = document.getElementById("country-cards-container");
                        if (container) container.scrollIntoView({ behavior: "smooth", block: "start" });
                    }, 50);
                }
            };
        }

        const timelineItems = [
            {
                time: "Months 1 - 6",
                title: "Profile & Skill Upgrade",
                desc: `Focus on acquiring key skills identified as gaps: ${profile.skill_gaps.slice(0, 3).join(", ") || "Technical Stack"}. Build recommended portfolio project: ${profile.recommended_projects[0] || "Strategic Capstone"}.`,
                outcomes: [
                    "Technical capability gaps resolved",
                    "Github portfolio and certifications updated"
                ],
                icon: "user"
            },
            {
                time: "Months 7 - 12",
                title: "Applications & Standardized Prep",
                desc: `Acquire target certifications: ${profile.recommended_certifications.slice(0, 2).join(", ") || "Professional Certifications"}. Shortlist target universities and programs in ${defaultCountry.country_name}.`,
                outcomes: [
                    "Program shortlist finalized",
                    "Language/standardized prep completed"
                ],
                icon: "book-open"
            },
            {
                time: "Months 13 - 18",
                title: "Visa Processing & Financial Verification",
                desc: `Obtain official admission. Complete financial block requirements (approx ${formatCurrency(estMigrationCost)} budgeted) and apply for the ${defaultCountry.visa_route} pathway.`,
                outcomes: [
                    "Admission offer letter secured",
                    "Visa application file submitted"
                ],
                icon: "file-text"
            },
            {
                time: "Months 19 - 24",
                title: "Pre-Departure Preparation",
                desc: `Arrange overseas student housing and mandatory health insurance for ${defaultCountry.country_name}. Finalize travel plans and documentation.`,
                outcomes: [
                    "Student housing and insurance arranged",
                    "Pre-departure checklists completed"
                ],
                icon: "plane"
            },
            {
                time: "Months 25 - 36",
                title: "Post-Arrival & Job Sourcing",
                desc: `Relocate and start classes. Use post-study work routes (${defaultCountry.post_study_work_months} months permit) to transition into employment as an ${profile.target_role}.`,
                outcomes: [
                    "Campus onboarding & local registration done",
                    "Local tech internship & job sourcing active"
                ],
                icon: "briefcase"
            }
        ];

        const stepsContainer = document.getElementById("roadmap-steps-container");
        if (stepsContainer) {
            stepsContainer.innerHTML = "";
            timelineItems.forEach(item => {
                const stepDiv = document.createElement("div");
                stepDiv.className = "roadmap-step";
                stepDiv.innerHTML = `
                    <div class="roadmap-time-badge">
                        <span class="time-label">MONTHS</span>
                        <span class="time-range">${item.time.replace("Months ", "")}</span>
                    </div>
                    <div class="roadmap-node-point">
                        <div class="node-circle"></div>
                    </div>
                    <div class="roadmap-step-card card">
                        <div class="card-glow-bg"></div>
                        <div class="step-card-left">
                            <div class="step-icon-container">
                                <i data-lucide="${item.icon}"></i>
                            </div>
                            <div class="step-card-info">
                                <h4>${item.title}</h4>
                                <p>${item.desc}</p>
                            </div>
                        </div>
                        <div class="step-card-right">
                            <span class="outcomes-header">KEY OUTCOMES & TASKS</span>
                            <div class="outcomes-tasks" style="display:flex; flex-direction:column; gap:8px; margin-top:8px;">
                                ${item.outcomes.map(out => `
                                    <label style="display:flex; align-items:flex-start; gap:8px; font-size:12.5px; color:var(--text-primary); cursor:pointer;">
                                        <input type="checkbox" style="margin-top:3px; accent-color:var(--primary-color);"> 
                                        <span style="line-height:1.4;">${out}</span>
                                    </label>`).join("")}
                            </div>
                        </div>
                    </div>
                `;
                stepsContainer.appendChild(stepDiv);
            });
        }


        // --- BUDGET OPTIMIZED PATH ---
        const budgetPath = calculateBudgetOptimizedPath(data);
        if (budgetPath) {
            document.getElementById("budget-country").textContent = budgetPath.countryName;
            document.getElementById("budget-univ-type").textContent = budgetPath.univType;
            document.getElementById("budget-scholarship-name").textContent = budgetPath.scholarshipName;
            
            if (budgetPath.scholarshipAmt > 0) {
                animateCurrencyCountUp("budget-scholarship-amount", budgetPath.scholarshipAmt);
            } else {
                document.getElementById("budget-scholarship-amount").textContent = "N/A";
            }
            animateCurrencyCountUp("budget-part-time", budgetPath.partTimeEarnings);
            animateCurrencyCountUp("budget-salary", budgetPath.expectedSalary, true);
            
            animateCountUp("budget-roi", budgetPath.roi, "", "/10");
            animateCountUp("budget-affordability", budgetPath.affordabilityScore, "", "/10");
            
            animateCurrencyCountUp("breakdown-original-cost", budgetPath.originalCost);
            if (budgetPath.scholarshipAmt > 0) {
                animateCurrencyCountUp("breakdown-scholarship-savings", budgetPath.scholarshipAmt, false, false, "- ");
            } else {
                document.getElementById("breakdown-scholarship-savings").textContent = "N/A";
            }
            animateCurrencyCountUp("breakdown-part-time-earnings", budgetPath.partTimeEarnings, false, false, "- ");
            animateCurrencyCountUp("breakdown-remaining-cost", budgetPath.outOfPocket);
            
            document.getElementById("budget-explanation-text").textContent = budgetPath.explanation;

            // Interactive Budget Planner Logic
            const savingsInput = document.getElementById("current-savings");
            const monthlyInput = document.getElementById("monthly-contribution");
            const savingsResult = document.getElementById("savings-result");

            const updateSavingsGoal = () => {
                if (!savingsInput || !monthlyInput || !savingsResult) return;
                
                const targetCost = budgetPath.outOfPocket;
                const currentSavings = parseInt(savingsInput.value) || 0;
                const monthlyCont = parseInt(monthlyInput.value) || 0;
                
                if (currentSavings >= targetCost) {
                    savingsResult.style.display = "block";
                    savingsResult.style.color = "var(--success)";
                    savingsResult.innerHTML = `You already have enough saved to cover the optimal path's out-of-pocket cost (${formatCurrency(targetCost)})!`;
                } else if (monthlyCont > 0) {
                    const remaining = targetCost - currentSavings;
                    const months = Math.ceil(remaining / monthlyCont);
                    savingsResult.style.display = "block";
                    savingsResult.style.color = "var(--primary-color)";
                    savingsResult.innerHTML = `At ${formatCurrency(monthlyCont, false, true)}, you will save the remaining ${formatCurrency(remaining)} in <strong>${months} months</strong> to afford the optimal path.`;
                } else {
                    savingsResult.style.display = "none";
                }
            };

            if (savingsInput && monthlyInput) {
                savingsInput.addEventListener("input", updateSavingsGoal);
                monthlyInput.addEventListener("input", updateSavingsGoal);
                updateSavingsGoal(); // initial calculation
            }
        }

        // Set up AI Confidence Badge value
        const summaryBadgeVal = document.getElementById("summary-confidence-badge-val");
        if (summaryBadgeVal) {
            animateCountUp("summary-confidence-badge-val", confidenceScore, "", "%");
        }

        // Setup collapsible sections click handlers
        const setupCollapsible = (headerId, sectionId) => {
            const header = document.getElementById(headerId);
            const section = document.getElementById(sectionId);
            if (header && section) {
                header.onclick = () => {
                    section.classList.toggle("collapsed");
                };
            }
        };
        setupCollapsible("budget-toggle-header", "budget-optimized-section");
        setupCollapsible("roadmap-toggle-header", "strategic-roadmap-section");

        // Next Step Actions
        const nextDownload = document.getElementById("next-step-download-btn");
        const nextNew = document.getElementById("next-step-new-btn");
        const nextCompare = document.getElementById("next-step-compare-btn");
        
        if (nextDownload) {
            nextDownload.onclick = () => downloadReportBtn.click();
        }
        if (nextNew) {
            nextNew.onclick = () => newStrategyBtn.click();
        }
        if (nextCompare) {
            nextCompare.onclick = () => {
                const tabBtn = document.querySelector('[data-tab="tab-countries"]');
                if (tabBtn) tabBtn.click();
                setTimeout(() => {
                    const el = document.getElementById("country-cards-container");
                    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
                }, 50);
            };
        }

        // Recreate icons in parsed items
        lucide.createIcons();
    }

    // --- METRICS COUNTER ANIMATION ---
    const statsObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const counters = entry.target.querySelectorAll(".metric-number");
                counters.forEach(counter => {
                    const target = parseInt(counter.getAttribute("data-target"), 10);
                    const duration = 1500;
                    const startTime = performance.now();

                    const updateCounter = (currentTime) => {
                        const elapsed = currentTime - startTime;
                        const progress = Math.min(elapsed / duration, 1);
                        const easeProgress = progress * (2 - progress); // easeOutQuad
                        const currentValue = Math.floor(easeProgress * target);

                        counter.textContent = currentValue;

                        if (progress < 1) {
                            requestAnimationFrame(updateCounter);
                        } else {
                            counter.textContent = target;
                        }
                    };

                    requestAnimationFrame(updateCounter);
                });
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    const metricsSection = document.getElementById("metrics-section");
    if (metricsSection) {
        statsObserver.observe(metricsSection);
    }

    // --- AI Career Advisor Chat Logic ---
    const advisorWidget = document.getElementById("ai-advisor-widget");
    const advisorHeader = document.getElementById("advisor-header-toggle");
    const advisorBody = document.getElementById("advisor-body");
    const advisorIcon = document.getElementById("advisor-toggle-icon");
    const advisorMessages = document.getElementById("advisor-messages");
    const advisorInput = document.getElementById("advisor-input");
    const advisorSendBtn = document.getElementById("advisor-send-btn");

    let chatHistory = [];
    
    // Toggle Advisor Chat Panel
    if (advisorHeader) {
        advisorHeader.addEventListener("click", () => {
            const isHidden = advisorBody.style.display === "none";
            advisorBody.style.display = isHidden ? "flex" : "none";
            if (advisorIcon) advisorIcon.style.transform = isHidden ? "rotate(180deg)" : "rotate(0deg)";
        });
    }

    async function sendChatMessage() {
        if (!advisorInput || !advisorInput.value) return;
        const text = advisorInput.value.trim();
        if (!text || !currentData) return;
        
        // Add User message to UI
        const userDiv = document.createElement("div");
        userDiv.className = "advisor-message user";
        userDiv.innerHTML = `<div class="message-content">${text}</div>`;
        if (advisorMessages) advisorMessages.appendChild(userDiv);
        
        chatHistory.push({ role: "user", content: text });
        advisorInput.value = "";
        if (advisorMessages) advisorMessages.scrollTop = advisorMessages.scrollHeight;
        if(advisorSendBtn) advisorSendBtn.disabled = true;

        // Add loading indicator
        const loadingDiv = document.createElement("div");
        loadingDiv.className = "advisor-message system";
        loadingDiv.id = "chat-loading";
        loadingDiv.innerHTML = `<div class="message-content"><span class="spinner" style="width:14px;height:14px;border-width:2px;vertical-align:middle;display:inline-block;border-color:var(--primary-color);border-right-color:transparent;border-radius:50%;animation:spin 1s linear infinite;"></span></div>`;
        if (advisorMessages) {
            advisorMessages.appendChild(loadingDiv);
            advisorMessages.scrollTop = advisorMessages.scrollHeight;
        }

        try {
            const response = await fetch(`${API_BASE}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    chat_history: chatHistory.slice(-5), // Keep last 5 messages context
                    context_data: {
                        profile: currentData.profile,
                        countries: currentData.explorer.matched_countries,
                        funding: currentData.funding
                    }
                })
            });

            const loadingEl = document.getElementById("chat-loading");
            if (loadingEl) loadingEl.remove();

            if (!response.ok) throw new Error("Chat API failed");
            const result = await response.json();
            
            chatHistory.push({ role: "assistant", content: result.response });

            // Add Assistant message to UI
            const aiDiv = document.createElement("div");
            aiDiv.className = "advisor-message system";
            let formattedText = result.response
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n/g, '<br>');
            aiDiv.innerHTML = `<div class="message-content">${formattedText}</div>`;
            if (advisorMessages) advisorMessages.appendChild(aiDiv);

        } catch (error) {
            console.error(error);
            const loadingEl = document.getElementById("chat-loading");
            if (loadingEl) loadingEl.remove();
            
            const errDiv = document.createElement("div");
            errDiv.className = "advisor-message system";
            errDiv.style.color = "var(--danger)";
            errDiv.innerHTML = `<div class="message-content">Sorry, I couldn't process that right now. Please try again later.</div>`;
            if (advisorMessages) advisorMessages.appendChild(errDiv);
        } finally {
            if(advisorSendBtn) advisorSendBtn.disabled = false;
            if (advisorMessages) advisorMessages.scrollTop = advisorMessages.scrollHeight;
            if(window.lucide) window.lucide.createIcons();
        }
    }

    if (advisorSendBtn) {
        advisorSendBtn.addEventListener("click", sendChatMessage);
    }
    if (advisorInput) {
        advisorInput.addEventListener("keypress", (e) => {
            if (e.key === "Enter") sendChatMessage();
        });
    }

});
