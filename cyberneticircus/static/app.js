// CybernetiCircus Dashboard Controller
// Interacts with /api/ endpoints to run the game loop and render status.

document.addEventListener("DOMContentLoaded", () => {
    // D3 Graph Visualizer variables
    let svg, simulation, linkGroup, nodeGroup, labelGroup;
    const width = 600;
    const height = 300;

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
    drawGraph(null);

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

        // Render generic database graph when no identity is selected
        drawGraph(null);
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

            // Render Metrics (LLM stats replaced with dashes)
            statModel.innerText = "--";
            statFitness.innerText = "--";
            statTokens.innerText = "--";
            statCost.innerText = "--";

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

            // Draw active state machine graph
            await drawGraph(name);

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

        logToConsole("system", `Compiling and spawning Cybernet Core '${name}'...`);
        try {
            const res = await fetch("/api/create", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    name: name,
                    description: desc
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

    // D3 Graph Visualizer logic

    function initGraphVisualizer() {
        const container = document.getElementById("graph-visualizer");
        if (!container) return;
        
        container.innerHTML = "";
        
        svg = d3.select("#graph-visualizer")
            .append("svg")
            .attr("width", "100%")
            .attr("height", height)
            .attr("viewBox", `0 0 ${width} ${height}`)
            .style("overflow", "visible");

        // Add glow filters for active nodes
        const defs = svg.append("defs");
        
        // Active step glow
        const stepGlow = defs.append("filter")
            .attr("id", "step-glow")
            .attr("x", "-50%")
            .attr("y", "-50%")
            .attr("width", "200%")
            .attr("height", "200%");
        stepGlow.append("feGaussianBlur")
            .attr("stdDeviation", "4")
            .attr("result", "blur");
        stepGlow.append("feMerge")
            .selectAll("feMergeNode")
            .data(["blur", "SourceGraphic"])
            .enter().append("feMergeNode")
            .attr("in", d => d);

        // Define arrowhead marker
        defs.append("marker")
            .attr("id", "arrowhead")
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 18)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-4L8,0L0,4")
            .attr("fill", "hsla(0, 0%, 100%, 0.15)");

        linkGroup = svg.append("g").attr("class", "links");
        nodeGroup = svg.append("g").attr("class", "nodes");
        labelGroup = svg.append("g").attr("class", "labels");

        simulation = d3.forceSimulation()
            .force("link", d3.forceLink().id(d => d.id).distance(80))
            .force("charge", d3.forceManyBody().strength(-180))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(22));
    }

    async function drawGraph(name) {
        if (!svg) initGraphVisualizer();
        if (!svg) return; // Escape if DOM not loaded yet
        
        try {
            const url = name ? `/api/graph?name=${name}` : "/api/graph";
            const res = await fetch(url);
            const graph = await res.json();
            
            const nodes = graph.nodes;
            const links = graph.links;

            // Preserve positions of existing nodes in the simulation
            const existingNodes = new Map();
            if (simulation) {
                simulation.nodes().forEach(node => {
                    existingNodes.set(node.id, node);
                });
            }

            const mergedNodes = nodes.map(node => {
                const existing = existingNodes.get(node.id);
                if (existing) {
                    node.x = existing.x;
                    node.y = existing.y;
                    node.vx = existing.vx;
                    node.vy = existing.vy;
                    node.fx = existing.fx;
                    node.fy = existing.fy;
                }
                return node;
            });

            // Update links
            const link = linkGroup.selectAll("line")
                .data(links, d => `${d.source}-${d.target}-${d.type}`);

            link.exit().remove();

            const linkEnter = link.enter().append("line")
                .attr("stroke", "hsla(0, 0%, 100%, 0.15)")
                .attr("stroke-width", 1.5)
                .attr("marker-end", "url(#arrowhead)");

            const updatedLink = linkEnter.merge(link);

            // Update nodes
            const node = nodeGroup.selectAll("circle")
                .data(mergedNodes, d => d.id);

            node.exit().remove();

            const nodeEnter = node.enter().append("circle")
                .attr("r", d => {
                    if (d.label === "MetaShifter") return 11;
                    if (d.label === "StateMachine") return 9;
                    if (d.label === "TraversalStep") return 7;
                    return 6;
                })
                .attr("fill", d => {
                    if (d.active_tag === "shifter") return "var(--neon-green)";
                    if (d.active_tag === "step") return "var(--neon-cyan)";
                    if (d.active_tag === "state_machine") return "var(--neon-purple)";
                    
                    if (d.label === "MetaShifter") return "hsl(145, 60%, 40%)";
                    if (d.label === "StateMachine") return "hsl(270, 60%, 50%)";
                    if (d.label === "TraversalStep") return "hsl(190, 60%, 40%)";
                    if (d.label === "IdentityState") return "hsl(220, 60%, 45%)";
                    if (d.label === "SimulationRun") return "hsl(340, 60%, 45%)";
                    return "hsl(0, 0%, 50%)";
                })
                .attr("stroke", d => {
                    if (d.active_tag) return "#fff";
                    return "hsla(0, 0%, 100%, 0.2)";
                })
                .attr("stroke-width", d => d.active_tag ? 2 : 1)
                .style("filter", d => d.active_tag === "step" ? "url(#step-glow)" : "none")
                .call(d3.drag()
                    .on("start", dragstarted)
                    .on("drag", dragged)
                    .on("end", dragended));

            // Append tooltip element for entered nodes
            nodeEnter.append("title");

            // Pulse animation classes
            nodeGroup.selectAll("circle")
                .classed("pulsing-node", d => d.active_tag === "step");

            const updatedNode = nodeEnter.merge(node);

            // Hover tooltips (always update with the latest properties)
            updatedNode.select("title")
                .text(d => `${d.label}: ${d.name}\n${JSON.stringify(d.properties, null, 2)}`);

            // Update labels
            const label = labelGroup.selectAll("text")
                .data(mergedNodes, d => d.id);

            label.exit().remove();

            const labelEnter = label.enter().append("text")
                .attr("dy", 18)
                .attr("text-anchor", "middle")
                .attr("fill", "var(--text-secondary)")
                .style("font-size", "9px")
                .style("font-family", "Outfit, sans-serif")
                .style("pointer-events", "none")
                .text(d => d.name);

            const updatedLabel = labelEnter.merge(label);

            simulation.nodes(mergedNodes).on("tick", () => {
                updatedLink
                    .attr("x1", d => d.source.x)
                    .attr("y1", d => d.source.y)
                    .attr("x2", d => d.target.x)
                    .attr("y2", d => d.target.y);

                updatedNode
                    .attr("cx", d => d.x)
                    .attr("cy", d => d.y);

                updatedLabel
                    .attr("x", d => d.x)
                    .attr("y", d => d.y);
            });

            simulation.force("link").links(links);
            simulation.alpha(0.3).restart();

        } catch (e) {
            console.error("D3 Draw Error:", e);
        }
    }

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    // Real-time dashboard auto-refresh polling loop
    async function tickDashboard() {
        if (activeIdentity) {
            await updateIdentitySheet(activeIdentity);
        } else {
            await drawGraph(null);
        }
    }

    // Run polling every 1000ms
    const pollInterval = setInterval(tickDashboard, 1000);

    // Cleanup interval on window unload
    window.addEventListener("beforeunload", () => {
        clearInterval(pollInterval);
    });
});
