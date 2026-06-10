// CybernetiCircus Dashboard Controller
// Interacts with /api/ endpoints to run the game loop and render status.

document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const dbStatus = document.getElementById("db-status-indicator");
    const selectCybernet = document.getElementById("cybernet-select");
    const selectStateMachine = document.getElementById("state-machine-select");
    const activeStats = document.getElementById("active-stats-container");
    const placeholder = document.getElementById("no-identity-placeholder");
    const arenaContent = document.getElementById("arena-content");
    const terminalOutput = document.getElementById("terminal-output");
    
    // Stats elements
    const statModel = document.getElementById("stat-model");
    const statFitness = document.getElementById("stat-fitness");
    const tempVal = document.getElementById("temp-val");
    const tempProgress = document.getElementById("temp-progress");
    const toppVal = document.getElementById("topp-val");
    const toppProgress = document.getElementById("topp-progress");
    const mutationVal = document.getElementById("mutation-val");
    const mutationProgress = document.getElementById("mutation-progress");
    const pressureVal = document.getElementById("pressure-val");
    const pressureProgress = document.getElementById("pressure-progress");
    const statTokens = document.getElementById("stat-tokens");
    const statCost = document.getElementById("stat-cost");
    
    // Arena elements
    const activeSmName = document.getElementById("active-sm-name");
    const activeStepId = document.getElementById("active-step-id");
    const activeStepText = document.getElementById("active-step-text");
    const callStackContainer = document.getElementById("call-stack-container");
    const callStackFrames = document.getElementById("call-stack-frames");
    const phaseBadge = document.getElementById("phase-badge");
    const tickBtn = document.getElementById("tick-compiler-btn");
    
    // Simulation history elements
    const simulationPlaceholder = document.getElementById("no-simulation-placeholder");
    const simulationTableWrapper = document.getElementById("simulation-table-wrapper");
    const simulationHistoryList = document.getElementById("simulation-history-list");

    // Modal drawer elements
    const openCreateBtn = document.getElementById("open-create-btn");
    const closeCreateBtn = document.getElementById("close-create-btn");
    const cancelCreateBtn = document.getElementById("cancel-create-btn");
    const createModal = document.getElementById("create-modal");
    const createForm = document.getElementById("create-cybernet-form");

    // Trace buttons
    const clearTraceBtn = document.getElementById("clear-trace-btn");

    let activeIdentity = "";

    // Load initial data
    loadCybernets();
    loadStateMachines();

    // Helper: Add styled lines to the console
    function logToConsole(type, text) {
        const line = document.createElement("div");
        line.classList.add("terminal-line");
        
        if (type === "system") line.classList.add("system-line");
        else if (type === "action") line.classList.add("action-line");
        else if (type === "event") line.classList.add("event-line");
        else if (type === "error") line.classList.add("error-line");
        else if (type === "success") line.classList.add("success-line");
        
        // Add timestamp
        const time = new Date().toLocaleTimeString();
        line.innerText = `[${time}] ${text}`;
        
        terminalOutput.appendChild(line);
        terminalOutput.scrollTop = terminalOutput.scrollHeight;
    }

    // API: Load list of Cybernets
    async function loadCybernets() {
        try {
            const res = await fetch("/api/list");
            const data = await res.json();
            
            // Keep active selection if it still exists
            const currentSelection = selectCybernet.value;
            selectCybernet.innerHTML = '<option value="">-- No Active Identity --</option>';
            
            data.cybernets.forEach(name => {
                const opt = document.createElement("option");
                opt.value = name;
                opt.innerText = name;
                selectCybernet.appendChild(opt);
            });
            
            if (data.cybernets.includes(currentSelection)) {
                selectCybernet.value = currentSelection;
            } else if (activeIdentity) {
                // Active identity got reaped/deleted
                logToConsole("error", `Cybernet '${activeIdentity}' not found. Deselecting.`);
                deselectIdentity();
            }
        } catch (e) {
            logToConsole("error", `Failed to fetch Cybernet list: ${e}`);
        }
    }

    // API: Load list of State Machines
    async function loadStateMachines() {
        try {
            const res = await fetch("/api/state_machines");
            const data = await res.json();
            
            selectStateMachine.innerHTML = '<option value="">Load different State Machine...</option>';
            data.state_machines.forEach(sm => {
                const opt = document.createElement("option");
                opt.value = sm.id;
                opt.innerText = `${sm.name} (${sm.id})`;
                selectStateMachine.appendChild(opt);
            });
        } catch (e) {
            logToConsole("error", `Failed to fetch State Machines: ${e}`);
        }
    }

    // UI: Deselect active identity
    function deselectIdentity() {
        activeIdentity = "";
        selectCybernet.value = "";
        placeholder.classList.remove("hidden");
        arenaContent.classList.add("hidden");
        activeStats.classList.add("hidden");
        
        // Reset simulation history
        simulationPlaceholder.innerText = "Select a Cybernet core to view simulation logs";
        simulationPlaceholder.classList.remove("hidden");
        simulationTableWrapper.classList.add("hidden");
        simulationHistoryList.innerHTML = "";
    }

    // API: Fetch and display identity status sheet
    async function updateIdentitySheet(name) {
        if (!name) {
            deselectIdentity();
            return;
        }

        try {
            const res = await fetch(`/api/status/${name}`);
            if (res.status === 404) {
                logToConsole("error", `Cybernet '${name}' not found.`);
                loadCybernets();
                deselectIdentity();
                return;
            }
            
            const data = await res.json();
            activeIdentity = name;

            // Render Metrics
            statModel.innerText = data.model_name;
            statFitness.innerText = parseFloat(data.fitness_score).toFixed(2);
            
            // Adjust fitness color based on threshold
            if (data.fitness_score >= 0.8) {
                statFitness.className = "metric-value fitness-badge";
            } else if (data.fitness_score < 0.4) {
                statFitness.className = "metric-value error-line";
            } else {
                statFitness.className = "metric-value text-glow";
            }

            tempVal.innerText = data.temperature.toFixed(1);
            tempProgress.style.width = `${Math.min(100, (data.temperature / 2.0) * 100)}%`;

            toppVal.innerText = data.top_p.toFixed(2);
            toppProgress.style.width = `${data.top_p * 100}%`;

            mutationVal.innerText = data.mutation_rate.toFixed(2);
            mutationProgress.style.width = `${data.mutation_rate * 100}%`;

            pressureVal.innerText = data.selection_pressure.toFixed(1);
            pressureProgress.style.width = `${Math.min(100, (data.selection_pressure / 2.0) * 100)}%`;

            statTokens.innerText = data.total_tokens.toLocaleString();
            statCost.innerText = `$${parseFloat(data.accumulated_cost).toFixed(6)}`;

            // Render Arena Content
            if (data.equipped_sm_id) {
                placeholder.classList.add("hidden");
                arenaContent.classList.remove("hidden");
                
                activeSmName.innerText = data.equipped_sm_name || data.equipped_sm_id;
                activeStepId.innerText = data.current_step_id || "sh8_day_start";
                activeStepText.innerText = data.current_step_text || "Awaiting compilation...";
                
                // Show phase badge
                if (data.phase) {
                    phaseBadge.innerText = data.phase.toUpperCase();
                    phaseBadge.className = `active-badge ${data.phase.toLowerCase() === 'night' ? 'accent-badge' : ''}`;
                    phaseBadge.classList.remove("hidden");
                }

                // Render Call Stack frames
                const stack = JSON.parse(data.call_stack || "[]");
                if (stack && stack.length > 0) {
                    callStackContainer.classList.remove("hidden");
                    callStackFrames.innerHTML = "";
                    stack.forEach((frame, idx) => {
                        const frameEl = document.createElement("div");
                        frameEl.className = "stack-frame";
                        frameEl.innerHTML = `
                            <span class="frame-idx">L${idx+1}</span>
                            <span class="frame-sm">${frame.sm_id}</span>
                            <span class="frame-arrow">→</span>
                            <span class="frame-step">${frame.step_id}</span>
                        `;
                        callStackFrames.appendChild(frameEl);
                    });
                } else {
                    callStackContainer.classList.add("hidden");
                }
            } else {
                // Has identity but no state machine equipped yet
                placeholder.classList.add("hidden");
                arenaContent.classList.remove("hidden");
                
                activeSmName.innerText = "No State Machine Equipped";
                activeStepId.innerText = "LOCKED";
                activeStepText.innerText = "Please select a State Machine loadout in the dropdown menu to equip and initialize.";
                phaseBadge.classList.add("hidden");
                callStackContainer.classList.add("hidden");
            }

            activeStats.classList.remove("hidden");
            
            // Render Simulation History
            await updateSimulationHistory(name);

        } catch (e) {
            logToConsole("error", `Failed to fetch status for '${name}': ${e}`);
        }
    }

    // API: Fetch and display simulation runs for an identity
    async function updateSimulationHistory(name) {
        if (!name) {
            simulationPlaceholder.classList.remove("hidden");
            simulationTableWrapper.classList.add("hidden");
            simulationHistoryList.innerHTML = "";
            return;
        }

        try {
            const res = await fetch(`/api/simulations/${name}`);
            const data = await res.json();
            const sims = data.simulations || [];

            if (sims.length === 0) {
                simulationPlaceholder.innerText = "No simulation logs found for this identity core.";
                simulationPlaceholder.classList.remove("hidden");
                simulationTableWrapper.classList.add("hidden");
                simulationHistoryList.innerHTML = "";
            } else {
                simulationPlaceholder.classList.add("hidden");
                simulationTableWrapper.classList.remove("hidden");
                simulationHistoryList.innerHTML = "";

                sims.forEach(sim => {
                    const row = document.createElement("tr");
                    
                    // Format accuracy
                    const accVal = parseFloat(sim.accuracy);
                    let accClass = "accuracy-mid";
                    if (accVal >= 0.8) {
                        accClass = "accuracy-high";
                    } else if (accVal < 0.4) {
                        accClass = "accuracy-low";
                    }

                    // Format date
                    let dateStr = sim.created_at;
                    if (dateStr) {
                        try {
                            const d = new Date(dateStr);
                            dateStr = d.toLocaleString();
                        } catch (e) {
                            // Keep raw
                        }
                    } else {
                        dateStr = "N/A";
                    }

                    row.innerHTML = `
                        <td class="run-id-cell">${sim.run_id}</td>
                        <td><span class="accuracy-badge ${accClass}">${accVal.toFixed(4)}</span></td>
                        <td class="date-cell">${dateStr}</td>
                    `;
                    simulationHistoryList.appendChild(row);
                });
            }
        } catch (e) {
            logToConsole("error", `Failed to fetch simulation history: ${e}`);
        }
    }

    // Action: Select Cybernet Core
    selectCybernet.addEventListener("change", (e) => {
        const name = e.target.value;
        if (name) {
            logToConsole("system", `Swapping core loadout to Cybernet Identity: '${name}'`);
            updateIdentitySheet(name);
        } else {
            deselectIdentity();
        }
    });

    // Action: Equip State Machine
    selectStateMachine.addEventListener("change", async (e) => {
        const smId = e.target.value;
        if (!activeIdentity || !smId) return;

        logToConsole("system", `Compiling and equipping State Machine '${smId}' onto '${activeIdentity}'...`);
        try {
            const res = await fetch("/api/equip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ character_name: activeIdentity, state_machine_id: smId })
            });
            const data = await res.json();
            if (data.success) {
                logToConsole("success", data.message);
                updateIdentitySheet(activeIdentity);
            } else {
                logToConsole("error", data.detail || "Equip compilation error.");
            }
        } catch (e) {
            logToConsole("error", `Equip request failed: ${e}`);
        }
        selectStateMachine.value = ""; // Reset dropdown
    });

    // Action: Tick Compiler Turn
    tickBtn.addEventListener("click", async () => {
        if (!activeIdentity) return;

        tickBtn.classList.add("loading");
        tickBtn.disabled = true;
        logToConsole("system", `Ticking turn step for '${activeIdentity}'...`);

        try {
            const res = await fetch("/api/tick", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ character_name: activeIdentity })
            });
            const data = await res.json();
            
            if (res.status === 400 || res.status === 500) {
                logToConsole("error", data.detail || "Turn execution failed.");
            } else {
                logToConsole("action", `Action Query: ${data.action_taken}`);
                logToConsole("event", `Event logs: ${data.event_message}`);
                
                // Check if reaped
                if (data.event_message.includes("Reaped from DB")) {
                    logToConsole("error", `Evolution check: Cybernet was pruned from the database.`);
                    deselectIdentity();
                    loadCybernets();
                } else {
                    // Refresh sheets
                    await updateIdentitySheet(activeIdentity);
                    // Refresh list (in case clone reproduction spawned a V2 clone!)
                    if (data.event_message.includes("REPRODUCED")) {
                        logToConsole("success", `Reproduction triggered! Mutated child identity spawned in Cyberneticity.`);
                        loadCybernets();
                    }
                }
            }
        } catch (e) {
            logToConsole("error", `Tick request failed: ${e}`);
        } finally {
            tickBtn.classList.remove("loading");
            tickBtn.disabled = false;
        }
    });

    // Action: Spawn Cybernet Form Submit
    createForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const name = document.getElementById("input-name").value.trim();
        const desc = document.getElementById("input-desc").value.trim();
        const model = document.getElementById("input-model").value;
        const temp = parseFloat(document.getElementById("input-temp").value);
        const topp = parseFloat(document.getElementById("input-topp").value);
        const mutation = parseFloat(document.getElementById("input-mutation").value);
        const pressure = parseFloat(document.getElementById("input-pressure").value);

        logToConsole("system", `Compiling and spawning Cybernet Core '${name}'...`);
        try {
            const res = await fetch("/api/create", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name,
                    description: desc,
                    model_name: model,
                    temperature: temp,
                    top_p: topp,
                    mutation_rate: mutation,
                    selection_pressure: pressure
                })
            });
            const data = await res.json();
            if (res.status === 200 && data.success) {
                logToConsole("success", data.message);
                createModal.classList.add("hidden");
                createForm.reset();
                
                // Reload names and select this new core
                await loadCybernets();
                selectCybernet.value = name;
                updateIdentitySheet(name);
            } else {
                logToConsole("error", data.detail || "Failed to create identity.");
            }
        } catch (err) {
            logToConsole("error", `Create request failed: ${err}`);
        }
    });

    // Modal Drawer triggers
    openCreateBtn.addEventListener("click", () => {
        createModal.classList.remove("hidden");
    });
    
    closeCreateBtn.addEventListener("click", () => {
        createModal.classList.add("hidden");
    });
    
    cancelCreateBtn.addEventListener("click", () => {
        createModal.classList.add("hidden");
    });

    // Click outside drawer closes it
    createModal.addEventListener("click", (e) => {
        if (e.target === createModal) {
            createModal.classList.add("hidden");
        }
    });

    // Clear trace logs
    clearTraceBtn.addEventListener("click", () => {
        terminalOutput.innerHTML = '<div class="terminal-line system-line">[SYSTEM] Terminal logs cleared.</div>';
    });
});
